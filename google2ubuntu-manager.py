#!/usr/bin/env python
# -*- coding: utf-8 -*-  
from gi.repository import Gtk
from gi.repository import Notify
from gi.repository import Gdk
from gi.repository import Gio
from os.path import expanduser
import os
import sys
import subprocess
import gettext

gettext.install('google2ubuntu',os.path.dirname(os.path.abspath(__file__))+'/i18n/')

TARGET_TYPE_URI_LIST = 80
dnd_list = [Gtk.TargetEntry.new('text/uri-list', 0, TARGET_TYPE_URI_LIST )]

# Classe MyWindow gere l'apparition de la fenêtre principale
class MyWindow(Gtk.ApplicationWindow):
    def __init__(self,app):
        Gtk.Window.__init__(self, title="google2ubuntu-manager",application=app)
        self.set_default_size(700, 500)  
        self.set_resizable(True)     
        self.set_border_width(0)
        self.get_focus()
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_default_icon_from_file(os.path.dirname(os.path.abspath(__file__))+'/icons.png')
        
        # Gtk.ListStore will hold data for the TreeView
        # Only the first two columns will be displayed
        # The third one is for sorting file sizes as numbers
        store = Gtk.ListStore(str, str)
        # Get the data - see below
        self.populate_store(store)

        # use a filter in order to filtering the data
        self.tree_filter = store.filter_new()

        # create the treeview
        treeview = Gtk.TreeView(self.tree_filter)
        treeview.set_tooltip_text(_('list of commands'))
        treeview.set_headers_visible(False)
        treeview.set_enable_search(True)
        treeview.set_search_column(1)
        treeview.set_hexpand(True)
        treeview.set_vexpand(True)

        # The first TreeView column displays the data from
        # the first ListStore column (text=0), which contains
        # file names
        renderer_1 = Gtk.CellRendererText()        
        renderer_1.set_property("editable", True)
        renderer_1.connect("edited", self.key_edited,store)
        column_1 = Gtk.TreeViewColumn(_('Keys'), renderer_1, text=0)
        # Calling set_sort_column_id makes the treeViewColumn sortable
        # by clicking on its header. The column is sorted by
        # the ListStore column index passed to it 
        # (in this case 0 - the first ListStore column) 
        column_1.set_sort_column_id(0)        
        treeview.append_column(column_1)
        
        # xalign=1 right-aligns the file sizes in the second column
        renderer_2 = Gtk.CellRendererText(xalign=1)
        renderer_2.set_property("editable", True)
        renderer_2.connect("edited", self.command_edited,store)
        # text=1 pulls the data from the second ListStore column
        # which contains filesizes in bytes formatted as strings
        # with thousand separators
        column_2 = Gtk.TreeViewColumn(_('Commands'), renderer_2, text=1)
        # Mak the Treeview column sortable by the third ListStore column
        # which contains the actual file sizes
        column_2.set_sort_column_id(1)
        treeview.append_column(column_2)
        
        # the label we use to show the selection
        self.labelState = Gtk.Label()
        self.labelState.set_text(_("Ready"))
        self.labelState.set_justify(Gtk.Justification.LEFT) 
        self.labelState.set_halign(Gtk.Align.START) 

        # when a row of the treeview is selected, it emits a signal
        self.selection = treeview.get_selection()
        self.selection.connect("changed", self.on_changed)
        
        # Use ScrolledWindow to make the TreeView scrollable
        # Otherwise the TreeView would expand to show all items
        # Only allow vertical scrollbar
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.add(treeview)
        scrolled_window.set_min_content_width(200)
        scrolled_window.set_min_content_height(200)        
        scrolled_window.connect('drag_data_received', self.on_drag_data_received,store)
        scrolled_window.drag_dest_set( Gtk.DestDefaults.MOTION | Gtk.DestDefaults.HIGHLIGHT | Gtk.DestDefaults.DROP, dnd_list, Gdk.DragAction.COPY)
        
        # a toolbar created in the method create_toolbar (see below)
        toolbar = self.create_toolbar(store)
        toolbar.set_hexpand(True)
        toolbar.show()

        # Use a grid to add all item
        self.grid = Gtk.Grid()
        self.grid.set_row_spacing(2);
        self.grid.attach(toolbar,0,0,1,1)
        self.grid.attach(scrolled_window, 0, 1, 1, 1)    
        self.grid.attach(self.labelState,0,2,1,1)
        
        # define the visible func toolbar should be create
        self.tree_filter.set_visible_func(self.match_func)
        
        # show
        self.add(self.grid)
        self.show_all()
    
    def on_drag_data_received(self,widget, context, x, y, Selection, target_type, timestamp,store):
        if target_type == TARGET_TYPE_URI_LIST:
            uri= Selection.get_uris()[0]
            uri = uri.strip('\r\n\x00')
            uris= uri.split('://')
            if len(uris) >= 1 :
                path = uris[1]
                print 'path', path
                if os.path.isfile(path):
                    self.addModule(store,path)
                elif os.path.isdir(path):
                    store.append([_('key sentence'),'xdg-open '+path])

    def show_label(self,action):
        etat = self.labelState.get_parent()
        if action == 'show' and etat == None:
            self.grid.attach(self.labelState,0,2,2,1)
        elif action == 'hide' and etat != None:
            self.grid.remove(self.labelState)

    def command_edited(self, widget, path, text,store):
        iters = self.tree_filter.get_iter(path)
        path = self.tree_filter.convert_iter_to_child_iter(iters)
        store[path][1] = text
        self.saveTree(store)

    def key_edited(self, widget, path, text,store):
        iters = self.tree_filter.get_iter(path)
        path = self.tree_filter.convert_iter_to_child_iter(iters)        
        store[path][0] = text
        self.saveTree(store)

    def on_changed(self, selection):
        # get the model and the iterator that points at the data in the model
        (model, iter) = selection.get_selected()
        if iter is not None:
            self.show_label('hide')          
         
        return True

    # a method to create the toolbar
    def create_toolbar(self,store):
        # a toolbar
        toolbar = Gtk.Toolbar()
        # which is the primary toolbar of the application
        toolbar.set_icon_size(Gtk.IconSize.LARGE_TOOLBAR)    
        toolbar.set_style(Gtk.ToolbarStyle.BOTH_HORIZ)

        # create a menu
        menu = Gtk.Menu()
        externe = Gtk.MenuItem(label=_("External commands"))
        externe.connect("activate",self.add_clicked,store,'externe')
        externe.show()
        menu.append(externe)
        interne = Gtk.MenuItem(label=_("Internal commands"))
        interne.connect("activate",self.add_clicked,store,'interne')
        interne.show()
        menu.append(interne)        
        module = Gtk.MenuItem(label=_("Module"))
        module.connect("activate",self.add_clicked,store,'module')
        module.show()
        menu.append(module)

        # create a button for the "add" action, with a stock image
        add_button = Gtk.MenuToolButton.new_from_stock(Gtk.STOCK_ADD)
        add_button.set_label(_("Add"))
        add_button.set_menu(menu)
        image = Gtk.Image()
        image.set_from_stock(Gtk.STOCK_ADD, Gtk.IconSize.BUTTON)
        # label is shown
        add_button.set_is_important(True)
        # insert the button at position in the toolbar
        toolbar.insert(add_button, 0)
        # show the button
        add_button.connect("clicked", self.add_clicked,store,'externe')
        add_button.set_tooltip_text(_('Add a new command'))
        add_button.show()
 
        # create a button for the "try" action
        try_button = Gtk.ToolButton.new_from_stock(Gtk.STOCK_MEDIA_PLAY)
        try_button.set_label(_("Try"))
        try_button.set_is_important(True)
        toolbar.insert(try_button,1)
        try_button.connect("clicked",self.try_command,store)
        try_button.set_tooltip_text(_('Try this command'))
        try_button.show() 
         
        # create a button for the "remove" action
        remove_button = Gtk.ToolButton.new_from_stock(Gtk.STOCK_REMOVE)
        remove_button.set_label(_("Remove"))
        remove_button.set_is_important(True)
        toolbar.insert(remove_button,2)
        remove_button.connect("clicked",self.remove_clicked,store)
        remove_button.set_tooltip_text(_('Remove this command'))
        remove_button.show()
        
        # create a button for the "remove all" action
        all_button = Gtk.ToolButton.new_from_stock(Gtk.STOCK_STOP)
        all_button.set_label(_("Clean up"))
        all_button.set_is_important(True)
        toolbar.insert(all_button,3)
        all_button.connect("clicked",self.removeall_clicked,store)
        all_button.set_tooltip_text(_('Remove all commands'))
        all_button.show() 

        # create a button for the "Help" action
        help_button = Gtk.ToolButton.new_from_stock(Gtk.STOCK_HELP)
        help_button.set_label(_("Help"))
        help_button.set_is_important(True)
        toolbar.insert(help_button,4)
        help_button.connect("clicked",self.help_clicked )
        help_button.set_tooltip_text(_("Display help message"))
        help_button.show() 
        
        # add a separator
        separator = Gtk.ToolItem()
        separator.set_expand(True)
        toolbar.insert(separator,5)
        
        # create a combobox to store user choice
        self.combo = self.get_combobox()
        toolcombo = Gtk.ToolItem()
        toolcombo.add(self.combo)
        toolcombo.show()
        toolbar.insert(toolcombo,6)

        # return the complete toolbar
        return toolbar

    # return a combobox to add to the toolbar
    def get_combobox(self):
        # the data in the model, of type string
        listmodel = Gtk.ListStore(str)
        # append the data in the model
        listmodel.append([_('All')])
        listmodel.append([_('External')])
        listmodel.append([_('Internal')])
        listmodel.append([_('Modules')])
                        
        # a combobox to see the data stored in the model
        combobox = Gtk.ComboBox(model=listmodel)
        combobox.set_tooltip_text(_("What type of command to add")+'?')

        # a cellrenderer to render the text
        cell = Gtk.CellRendererText()

        # pack the cell into the beginning of the combobox, allocating
        # no more space than needed
        combobox.pack_start(cell, False)
        # associate a property ("text") of the cellrenderer (cell) to a column (column 0)
        # in the model used by the combobox
        combobox.add_attribute(cell, "text", 0)

        # the first row is the active one by default at the beginning
        combobox.set_active(0)

        # connect the signal emitted when a row is selected to the callback function
        combobox.connect("changed", self.on_combochanged)
        return combobox
    
    # callback function attach to the combobox   
    def on_combochanged(self,combo):
        self.tree_filter.refilter()

    # filter function
    def match_func(self, model, iterr, data=None):
        query = self.combo.get_active()
        value = model.get_value(iterr, 1)
        field=value.split('/')
        
        if query == 0:
            return True
        elif query == 1 and _('modules') not in field and _('internal') not in field:
            return True
        elif query == 2 and _('internal') in field:
            return True
        elif query == 3 and _('modules') in field:
            return True
        else:
            return False

    def add_clicked(self,button,store,add_type):
        if add_type == 'externe':
            store.append([_('key sentence'),_('your command')])
        elif add_type == 'interne':
            store.append([_('key sentence'),_('internal')+'/'+_('word')])
        elif add_type == 'module':
            mo = moduleSelection()
            module = mo.getModule()
            if module != '-1':
                self.addModule(store,module)
            else:
                self.show_label('show')
                self.labelState.set_text(_("Error, you must choose a file"))


    def addModule(self,store,module):
        # ex: recup de weather.sh
        name = module.split('/')[-1]
        # ex: ~/.config/google2ubuntu/weather
        module=module.strip(name)
        print module+"args"
        # ex: recherche du fichier args
        if os.path.exists(module+'args'):
            # ex: récupération de weather
            path = module.split('/')[-2]
            store.append([_('key sentence'),'/modules/'+path+'/'+name])
            # si le dossier de modules n'existe pas
            module_path=expanduser('~')+'/.config/google2ubuntu/modules/'
            if not os.path.exists(module_path):
                os.makedirs(os.path.dirname(module_path))
                # on copie le dossier du module    
                os.system('cp -r '+module+' '+module_path)
        else:
            self.show_label('show')
            self.labelState.set_text(_("Error, args file missing"))
            win = ArgsWindow(module,name,store)        
    
    def remove_clicked(self,button,store):
        if len(store) != 0:
            (model, iters) = self.selection.get_selected()
            iter = self.tree_filter.convert_iter_to_child_iter(iters)
            if iter is not None:
                self.show_label('show')
                self.labelState.set_text(_('Remove')+': '+store[iter][0]+' '+store[iter][1]) 
                store.remove(iter)
                self.saveTree(store)
            else:
                print "Select a title to remove"
        else:
            print "Empty list"

    def removeall_clicked(self,button,store):
        # if there is still an entry in the model
        old = expanduser('~') +'/.config/google2ubuntu/google2ubuntu.conf'
        new = expanduser('~') +'/.config/google2ubuntu/.google2ubuntu.bak'
        if os.path.exists(old):
            os.rename(old,new)

        if len(store) != 0:
            # remove all the entries in the model
            self.labelState.set_text(_('Remove all commands'))               
            for i in range(len(store)):   
                iter = store.get_iter(0)
                store.remove(iter)
            
            self.saveTree(store)   
        print "Empty list"        

    def try_command(self,button,store):
        (model, iter) = self.selection.get_selected()
        if iter is not None:
            command = model[iter][1]
            if _('internal') not in command and _('modules') not in command:
                process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                output,error  = process.communicate() 
                self.show_label('show')       
                self.labelState.set_text(output+'\n'+error)
    
    def help_clicked(self,button):
        win = HelpWindow()

    def populate_store(self, store):
        config = expanduser('~') +'/.config/google2ubuntu/google2ubuntu.conf'
        default = os.path.dirname(os.path.abspath(__file__))+'/default.conf'
        try:
            if os.path.exists(config) :        
                f = open(config,"r")
            else:
                if os.path.exists(expanduser('~') +'/.config/google2ubuntu') == False:
                    os.makedirs(expanduser('~') +'/.config/google2ubuntu')
                    os.system('cp -r /usr/share/google2ubuntu/modules '+expanduser('~') +'/.config/google2ubuntu')    
                
                # utilisation du fichier de config par défaut
                f = open(default,"r")
                
            for line in f:
                if len(line.split('=')) == 2:
                    line = line.rstrip('\n\r') 
                    store.append([line.split('=')[0], line.split('=')[1]])       
                    
            f.close()
        except IOError:
            print "Le fichier de config et le fichier default n'existent pas"

    def saveTree(self,store):
        # if there is still an entry in the model
        model = self.tree_filter.get_model()
        config = expanduser('~') +'/.config/google2ubuntu/google2ubuntu.conf'          
        try:
            if not os.path.exists(os.path.dirname(config)):
                os.makedirs(os.path.dirname(config))
            
            f = open(config,"w") 
            if len(store) != 0:
                for i in range(len(store)):
                    iter = store.get_iter(i)
                    if model[iter][0] != '' and model[iter][1] != '':
                        f.write(model[iter][0]+'='+model[iter][1]+'\n')
                
                self.show_label('show')
                self.labelState.set_text(_('Save commands'))            

            f.close()
        except IOError:    
            print "Unable to write the file"

# gère l'apparition de la fenêtre d'assistance de création de module
class ArgsWindow():
    def __init__(self,module,name,store):
        self.w = Gtk.Window()
        self.w.set_title(_("Module setup"))
        self.w.set_resizable(False)     
        self.w.get_focus()
        self.w.set_position(Gtk.WindowPosition.CENTER)      
        self.w.set_default_size(300,300)  
        self.w.set_border_width(5)
        
        grid = Gtk.Grid()
        label1 = Gtk.Label(_("Linking word"))
        label1.set_justify(Gtk.Justification.LEFT) 
        label1.set_halign(Gtk.Align.START) 
        self.entry1 = Gtk.Entry()
        self.entry1.set_tooltip_text(_("Word to separate call and parameter"))
        self.checkbutton = Gtk.CheckButton()
        self.checkbutton.set_label(_("Replace space by plus"))
        self.checkbutton.set_tooltip_text(_("Replace space by plus"))
        button = Gtk.Button()
        button.set_label(_("Go"))
        button.set_tooltip_text(_("Go"))
        image = Gtk.Image()
        image.set_from_stock(Gtk.STOCK_APPLY, Gtk.IconSize.BUTTON)
        button.set_image(image)
        button.connect("clicked",self.do_clicked,module,name,store)
        
        grid.attach(label1,0,0,4,1)
        grid.attach(self.entry1,0,1,4,1)
        grid.attach(self.checkbutton,0,2,4,1) 
        grid.attach(button,3,3,1,1)                
        self.w.add(grid)
        self.w.show_all()
        
    def do_clicked(self,button,module,name,store):
        linker = self.entry1.get_text()
        if self.checkbutton.get_active():
            spacebyplus='1' 
        else:
            spacebyplus='0'
        
        if linker is not '':
            try:
                folder = name.split('.')[0]
                module_path=expanduser('~')+'/.config/google2ubuntu/modules/'+folder

                if not os.path.exists(module_path):
                    os.makedirs(module_path)    
                                
                f = open(module_path+'/args',"w")
                f.write('linker='+linker+'\n')
                f.write('spacebyplus='+spacebyplus+'\n')
                f.close()
                
                os.system('cp '+module+name+' '+module_path)
                store.append(['<phrase clé>','/modules/'+folder+'/'+name])    
            except IOError:
                "Unable to open the file"
        
        self.w.destroy()
    
    def getEtat(self):
        return self.etat

# gère l'apparition de le fenêtre d'aide
class HelpWindow():
    # constructor for a window (the parent window)
    def __init__(self):
        #a  Gtk.AboutDialog
        self.aboutdialog = Gtk.AboutDialog()

        # lists of authors and documenters (will be used later)
        authors = ["Franquet Benoit"]
        documenters = ["Franquet Benoit"]

        # we fill in the aboutdialog
        self.aboutdialog.set_program_name(_("Help Google2Ubuntu"))
        self.aboutdialog.set_copyright("Copyright \xc2\xa9 2014 Franquet Benoit")
        self.aboutdialog.set_authors(authors)
        self.aboutdialog.set_documenters(documenters)
        self.aboutdialog.set_website("http://forum.ubuntu-fr.org/viewtopic.php?id=804211&p=1")
        self.aboutdialog.set_website_label("http://forum.ubuntu-fr.org/viewtopic.php?id=804211&p=1")

        # we do not want to show the title, which by default would be "About AboutDialog Example"
        # we have to reset the title of the messagedialog window after setting the program name
        self.aboutdialog.set_title("")

        # to close the aboutdialog when "close" is clicked we connect the
        # "response" signal to on_close
        self.aboutdialog.connect("response", self.on_close)
        # show the aboutdialog
        self.aboutdialog.show()
        
    # destroy the aboutdialog
    def on_close(self, action, parameter):
        action.destroy()

# gère l'apparition de la fenêtre de choix du module
class moduleSelection():
    def __init__(self):
        w=Gtk.Window()
        dialog = Gtk.FileChooserDialog(_("Choose a file"), w,Gtk.FileChooserAction.OPEN,(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,Gtk.STOCK_OPEN, Gtk.ResponseType.OK))        
        dialog.set_default_size(800, 400)

        response = dialog.run()
        self.module = '-1'
        if response == Gtk.ResponseType.OK:
            self.module=dialog.get_filename()
        elif response == Gtk.ResponseType.CANCEL:
            print("Cancel clicked")

        dialog.destroy()
    
    def getModule(self):
        return self.module

# application principale
class MyApplication(Gtk.Application):
    def __init__(self):
        Gtk.Application.__init__(self)

    def do_activate(self):
        win = MyWindow(self)
        win.show_all()

    def do_startup(self):
        Gtk.Application.do_startup(self)
            

app = MyApplication()
exit_status = app.run(sys.argv)
sys.exit(exit_status)
