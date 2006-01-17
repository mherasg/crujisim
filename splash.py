#!/usr/bin/python
#-*- coding:iso8859-15 -*-
# $Id$
# (c) 2005 CrujiMaster (crujisim@yahoo.com)
#
# This file is part of CrujiSim.
#
# CrujiSim is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# CrujiSim is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CrujiSim; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import sys
sys.path.append("lib")
import logging
import random
import locale
import os
from stat import *

try: 
    import pygtk 
    pygtk.require("2.0") 
except:
    logging.error("Unable to load pygtk")
try: 
    import gtk
    import gtk.glade
    import gobject
except:
    logging.error("unable to load gtk")
    sys.exit(1)
from banner import *
from Exercise import *
import ConfMgr
conf = ConfMgr.CrujiConfig()

encoding = locale.getpreferredencoding()
utf8conv = lambda x : unicode(x, encoding).encode('utf8')

# CONSTANTS
EX_DIR = "pasadas"
JOKES = "jokes.txt"

# Define which logging level messages will be output
logging.getLogger('').setLevel(logging.DEBUG)

class Crujisim:
    
    def __init__(self): 
        gladefile = "glade/crujisim.glade" 
        self.windowname = "splash" 

        splash = self.splash = gtk.glade.XML(gladefile, "Splash") 
        splash.signal_autoconnect(self)

        gui = self.gui = gtk.glade.XML(gladefile, "MainWindow") 
        gui.signal_autoconnect(self)

        # Place the joke
        lines = open(JOKES, 'rt').readlines()
        try:
            j = random.choice(lines)
        except:
            j = ''
        joke = ""
        for l in j.split("|"): joke += l+"\n"
        joke = joke[:-1]
        splash.get_widget('jokelabel').set_text(utf8conv(joke))
        splash.get_widget("Splash").set_position(gtk.WIN_POS_CENTER)
        
        #splash.get_widget('Splash').idle_add(self.load)
        splash.get_widget("progressbar").set_text("Obteniendo lista de ejercicios")
        gobject.idle_add(self.load)        
                
    def load(self):
        splash, gui = self.splash, self.gui
        
        # Create the model for the excercise list
        # FIR, Sector, Promocion, Fase, D�a, Pasada, Turno, Aviones
        #exc_list = gtk.ListStore(str,str,int,int,int,int,str,int)
        exc_list = self.exc_list = gtk.ListStore(str,str,str,str,str)
        
        pb = splash.get_widget("progressbar")
        pb.set_text('Cargando ejercicios')
        dirs = [dir for dir in os.listdir(EX_DIR) if dir[-4:]!=".svn"
                and S_ISDIR(os.stat(os.path.join(EX_DIR,dir))[ST_MODE])]
        n_dirs = len(dirs)
        i=0.
        for dir in dirs:  # File includes the path, filename doesn't
            pb.set_text(dir)
            i += 1./n_dirs
            dir = os.path.join(EX_DIR,dir)
            pb.set_fraction(i)
            while gtk.events_pending():
                gtk.main_iteration()
            for e in load_exercises(dir):
                exc_list.append((e["file"],utf8conv(e["fir"]),utf8conv(e["sector"]),
                                 utf8conv(e["comment"]),utf8conv(e["file"])))
                
        splash.get_widget("Splash").destroy()
        gui.get_widget("MainWindow").present()
      
        self.exc_filter = exc_filter = exc_list.filter_new()
        self.filters = {"FIR":"---","Sector":"---","Promocion":"---"}
        exc_filter.set_visible_func(self.exc_is_visible)
        self.update_combos()
        exc_view = self.exc_view = gui.get_widget("exercises")
        exc_view.set_model(gtk.TreeModelSort(exc_filter))
        exc_view.get_selection().set_mode(gtk.SELECTION_SINGLE)
        renderer = gtk.CellRendererText()
        for i,name in zip(range(1,4),('FIR','Sector','Pasada')):
            column = gtk.TreeViewColumn(name, renderer, text=i) 
            column.set_clickable(True) 
            column.set_sort_column_id(i) 
            column.set_resizable(True) 
            exc_view.append_column(column)
            
        # Fill up the FIRs combo with the unique FIRs available
        firs = {}
        for fir in [row[1] for row in self.exc_list]:
            firs[fir]=0
        fircombo=gui.get_widget("fircombo")
        for f in firs.keys():
            fircombo.append_text(f)
        self._updating_combos = True            
        fircombo.set_active(0)
        self._updating_combos = False
    
    def update_combos(self):
        self._updating_combos = True
        
        # Find unique FIRs, Sectors and promociones
        sectors = {}
        for row in self.exc_filter:
            sectors[row[2]]=0
        gui = self.gui

        def update_combo(combo,values):
            old_value=self.get_active_text(combo)
            self.blank_combo(combo)
            combo.append_text("---")
            combo.set_active(0)
            i=1
            for value in values:
                combo.append_text(value)
                if value==old_value:
                    combo.set_active(i)
                i += 1
            
        update_combo(gui.get_widget("sectorcombo"),sectors.keys())
        self.filters["FIR"]=self.get_active_text(gui.get_widget("fircombo"))
        self.filters["Sector"]=self.get_active_text(gui.get_widget("sectorcombo"))
        self._updating_combos = False

    def get_active_text(self,combobox):
        model = combobox.get_model()
        active = combobox.get_active()
        if active < 0:
            return None
        return model[active][0]
    
    def blank_combo(self,combo):
        while len(combo.get_model())>0:
            combo.remove_text(0)

    def set_filter(self,combo):
        try:
            if self._updating_combos: return
        except: pass
        gui=self.gui
        self.filters["FIR"]=self.get_active_text(gui.get_widget("fircombo"))
        self.filters["Sector"]=self.get_active_text(gui.get_widget("sectorcombo"))
        self.exc_filter.refilter()
        self.update_combos()
        
    def set_fir(self,combo):
        try:
            if self._updating_combos: return
        except: pass
        gui=self.gui
        self.filters["FIR"]=self.get_active_text(gui.get_widget("fircombo"))
        self.filters["Sector"]="---"
        self.exc_filter.refilter()
        self.update_combos()
        
            
    def exc_is_visible(self,model,iter,user_data=None):
        f = self.filters
        if (model.get_value(iter,1) == f["FIR"] or f["FIR"]=="---") \
          and (model.get_value(iter,2) == f["Sector"] or f["Sector"]=="---"):
            return True
        else:
            return False
        
    def gtk_main_quit(self,w=None,e=None):
        
        gtk.main_quit()
        
    def list_clicked(self,widget=None,event=None):
        if event.type == gtk.gdk._2BUTTON_PRESS:
            self.begin_simulation()
        
    def begin_simulation(self,button=None):
        print "Button clicked"
        sel = self.exc_view.get_selection()
        (model, iter) = sel.get_selected()
        
        fir_name = model.get_value(iter,1)
        for (fir,fir_file) in get_fires():
            if fir_name==fir:
                fir_elegido=(fir, fir_file)
                break
        sector_name = model.get_value(iter,2)
        for (sector, section) in get_sectores(fir_name):
            if sector==sector_name:
                sector_elegido=(sector,section)
                break            
        ejercicio_elegido = model.get(iter,3,0)
        if "tpv" in sys.modules:
            sys.modules.pop('tpv')
        
        import tpv
        print "importing tpv"
        #import tpv
        tpv.set_seleccion_usuario([fir_elegido , sector_elegido , ejercicio_elegido , 1])

        self.gui.get_widget("MainWindow").hide()
        while gtk.events_pending():
            gtk.main_iteration()
        if "Simulador" in sys.modules:
            sys.modules.pop('Simulador')
        import Simulador
        self.gui.get_widget("MainWindow").present()

Crujisim()
gtk.main()