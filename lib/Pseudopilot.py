#!/usr/bin/python
#-*- coding:iso8859-15 -*-
# $Id$
# (c) 2005 CrujiMaster (crujisim@crujisim.cable.nu)
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
"""Classes used by the pseudopilot interface of Crujisim"""

from RaDisplay import *
from MathUtil import get_h_m_s
import avion

SNDDIR='./snd/'

class PpDisplay(RaDisplay):
    """Radar display with a pseudopilot interface"""
    
    def __init__(self,flights,title,icon_path,fir,sector,mode='pp'):
        """Instantiate a Pseudopilot Radar Display
        
        title - window title
        icon_path - path to the windows task bar icon
        fir -- fir object
        sector -- name of the sector to work with
        """
        self.toolbar_height = 60  # Pseudopilot display toolbar height
        self._flights_tracks = {}
        self._tracks_flights = {}
        RaDisplay.__init__(self,title,icon_path,fir,sector, self.toolbar_height)
        self.flights = flights
        self.mode = mode
        
        # Create the list of tracks from the flights
        for f in flights:
            vt = VisTrack(self.c,self.vt_handler,self.do_scale,self.undo_scale)
            vt.l_font_size=self.label_font_size
            if mode=='atc':
                vt.mode='atc'
                vt.cfl=f.cfl
                vt.pfl=f.pfl
            self.tracks.append(vt)
            self._flights_tracks[f] = vt
            self._tracks_flights[vt] = f
        
        self.routes = []  # List of tracks whose routes are displayed
        self.waypoints = []  # List of tracks whose waypoints are displayed 
        
        self.speed_vector_var = IntVar()
        self.speed_vector_var.set(0)
        self.clock_speed_var = DoubleVar()
        self.clock_speed_var.set(1.0)
            
        self.update_tracks()
        self.toolbar = ventana_auxiliar(self)
        self.toolbar.redraw()
        
        self.t=0
        self.clock=RaClock(self.c)
        self.clock.configure(time='%02d:%02d:%02d' % get_h_m_s(self.t))
        
        self.print_tabular = RaTabular(self.c, position=(800,10), anchor=NW,
                                       label="Fichas",closebuttonhides=True)
        self.print_tabular.adjust()
        # self.print_tabular.hide()
        self.dep_tabular = DepTabular(self, self.c)
        # self.dep_tabular.hide()
        
        self.redraw()
        self.separate_labels()
        
    def process_message(self, m):
        
        def update_flight(new):
            try: old = [old for old in self.flights if new.name==old.name][0]
            except:
                logging.warning("Unable to update %s. No local flight so named"%(new.name))
                return
            for name, value in new.__dict__.items():
                setattr(old, name, value)
            return old
        
        if m['message']=='time':
            t = m['data']
            self.update_clock(t)

        if m['message']=='update':
            flights = m['flights']
            for f in flights: update_flight(f)
            self.wind = m['wind']
            self.stop_separating = True

            self.print_tabular.list.delete(0,self.print_tabular.list.size())
            for cs in m['print_list']:
                self.print_tabular.insert(END,cs)
            self.print_tabular.adjust()
            self.dep_tabular.update(m['dep_list'])

            self.update()


        if m['message']=='update_flight':
            f = update_flight(m['flight'])  # Returns the updated flight
            self.update_track(f)

    def delete_routes(self,e=None):
        for track in self.tracks:
            self.c.delete(track.cs+'fpr')
            self.c.delete(track.cs+'wp')
            self.routes=[]
            self.waypoints=[]
            
    def draw_fpr(self,track):
        canvas=self.c
        line=()
        if track.vfp:
            line=line+self.do_scale(track.pos)
        for a in track.route:
            pto=self.do_scale(a[0])
            if a[1][0] <> '_' or a[1] in self.fir.proc_app.keys():
                canvas.create_text(pto,text=a[1],fill='orange',tag=track.name+'fpr',anchor=SE,font='-*-Helvetica-*--*-10-*-')
                canvas.create_text(pto,text=a[2],fill='orange',tag=track.name+'fpr',anchor=NE,font='-*-Helvetica-*--*-10-*-')
            line=line+pto
        if len(line)>3: canvas.create_line(line,fill='orange',tags=track.name+'fpr')
        self.routes.append(track)
        self.c.lift(track.name+'fpr')
        self.c.lift('track')

    def show_hide_fpr(self,track):
        canvas=self.c
        if canvas.itemcget(track.name+'fpr',"fill")=='orange':
            canvas.delete(track.name+'fpr')
            self.routes.remove(track)
        else:
            self.draw_fpr(track)
    
    def draw_way_point(self,track):
        canvas=self.c
        do_scale=self.do_scale

        canvas.delete(track.name+'fpr')
        canvas.delete(track.name+'wp')
        line=()
        if track.vfp:
            line=line+do_scale(track.pos)
        for a in track.route:
            pto=do_scale(a[0])
            if a[1][0] <> '_':
                canvas.create_text(pto,text=a[1],fill='yellow',tag=track.name+'wp',anchor=SE,font='-*-Helvetica-*--*-10-*-')
                canvas.create_text(pto,text=a[2],fill='yellow',tag=track.name+'wp',anchor=NE,font='-*-Helvetica-*--*-10-*-')
            line=line+pto
        if len(line)>3: canvas.create_line(line,fill='yellow',tags=track.name+'wp')
        size=2
        for a in track.route:
            (rect_x, rect_y) = do_scale(a[0])
            point_ident = canvas.create_rectangle(rect_x-size, rect_y-size, rect_x+size, rect_y+size,fill='yellow',outline='yellow',tags=track.name+'wp')
            def clicked_on_waypoint(e, point_coord=a[0],point_name=a[1]):
                # Display window offering "Direct to..." and "Cancel" options.
                track.last_lad = e.serial
                win = Frame(canvas)
                id_avo = Label(win,text=track.name)
                id_avo.pack(side=TOP)                
                id_pto = Entry (win,width=8)
                id_pto.insert(0,point_name)
                id_pto.pack(side=TOP)
                but_direct = Button(win, text="Dar directo")
                but_cancel = Button(win, text="Cancelar")
                but_direct.pack(side=TOP)
                but_cancel.pack(side=TOP)
                win_identifier = canvas.create_window(e.x, e.y, window=win)
                def close_win(ident=win_identifier):
                    canvas.delete(ident)
                def direct_to():
                    pto=id_pto.get()
                    self.sendMessage({"message":"route_direct", "cs":track.name, "fix":pto})
                    track.route_direct(pto)  # Only to give an immediate appearance
                    canvas.delete(track.name+'wp')
                    self.waypoints.remove(track)
                    close_win()
                but_cancel['command'] = close_win
                but_direct['command'] = direct_to
            canvas.tag_bind(point_ident, "<1>", clicked_on_waypoint)
        self.waypoints.append(track)
        self.c.lift(track.name+'wp')
        self.c.lift('track')
        
            
    def show_hide_way_point(self,track):
        canvas=self.c
        do_scale=self.do_scale
        
        if canvas.itemcget(track.name+'wp',"fill")=='yellow':
            canvas.delete(track.name+'wp')
            self.waypoints.remove(track)
            return
        
        self.draw_way_point(track)   

    def change_size(self,e):
        RaDisplay.change_size(self,e)
        self.toolbar.redraw()
            
    def update(self):
        self.update_tracks()
        self.update_clock()
        RaDisplay.update(self)
                            
    def update_clock(self,t=None):
        if t==None: t=self.t
        else: self.t=t
        self.clock.configure(time='%02d:%02d:%02d' % get_h_m_s(t))
            
    def update_tracks(self):
        for f in self.flights:
            self.update_track(f)
            
    def update_track(self, f):
        vt = self._flights_tracks[f]
        vt.alt=f.alt
        vt.cs=f.name
        vt.wake=f.estela
        vt.echo=f.campo_eco
        vt.gs=f.ground_spd
        vt.mach=f.get_mach()
        vt.hdg=f.hdg
        vt.track=f.track
        vt.rate=f.get_rate_descend()
        vt.ias=f.get_ias()
        vt.ias_max=f.get_ias_max()
        vt.visible=f.se_pinta
        vt.orig = f.origen
        vt.dest = f.destino
        vt.type = f.tipo
        vt.radio_cs = f.radio_callsign
        vt.rfl = f.rfl
        vt.cfl=f.cfl
        vt.pfl=f.pfl
        if f.pp_pos!=None and f.pp_pos==self.pos_number:
            vt.assumed = True
        else:
            vt.assumed = False
        
        [x0,y0]=self.do_scale(f.pos)
        vt.coords(x0,y0,f.t)
        self.c.lift(str(vt)+'track')
            
    def vt_handler(self,vt,item,action,value,e=None):
        RaDisplay.vt_handler(self,vt,item,action,value,e)
        f=self._tracks_flights[vt]
        if item=='plot':
            if action=='<Button-1>': self.show_hide_fpr(f)
        if item=='pfl':
            if action=='update':
                self.sendMessage({"message":"set_pfl", "cs": f.name, "pfl":int(value)})
        if item=='cfl':
            if action=='update':
                self.sendMessage({"message":"set_cfl", "cs": f.name, "cfl":int(value)})
                #flag=self.set_cfl(int(value))
                #if flag: self.redraw(canvas)
                #return flag
                return True  # Suppose the update was valid
        if item=='rate':
            if action=='update':
                #if value=='std':
                #    self.set_std_rate()
                #else:
                #    return self.set_rate_descend(int(value))
                self.sendMessage({"message":"set_rate", "cs": f.name, "rate":value})
                return True  # Suppose the update was valid
        if item=='hdg':
            if action=='update':
                (hdg,opt)=value
                self.sendMessage({"message":"set_hdg", "cs": f.name, "hdg":int(hdg), "opt":opt})
        if item=='ias':
            if action=='update':
                (spd,force_speed)=value
        #        if spd=='std':
        #            self.set_std_spd()
        #        else:
        #            return self.set_spd(spd, force=force_speed)
                self.sendMessage({"message":"set_ias", "cs": f.name,
                                  "ias":spd, "force_speed":force_speed})
                return True  # Suppose the update was valid
        if item=='mach':
            if action=='update':
                (spd,force_speed)=value
        #        if spd=='std':
        #            self.set_std_spd()
        #        else:
        #            return self.set_spd(spd, force=force_speed)
                self.sendMessage({"message":"set_mach", "cs": f.name,
                                  "mach":spd, "force_speed":force_speed})
                return True  # Suppose the update was valid
        if item=='echo':
            if action=='<Button-3>':
                self.show_hide_way_point(f)
                
    def reposition(self):
        RaDisplay.reposition(self)
        r=self.routes[:]
        w=self.waypoints[:]
        self.delete_routes()
        for track in r:
            self.draw_fpr(track)
        for track in w:
            self.draw_way_point(track)

    def redraw(self):
        RaDisplay.redraw(self)
        self.update_tracks()

    def b1_cb(self,e):
        RaDisplay.b1_cb(self,e)
        self.toolbar.close_windows()
    
    def b2_cb(self,e):
        RaDisplay.b2_cb(self,e)
        self.toolbar.close_windows()
    
    def b3_cb(self,e):
        RaDisplay.b3_cb(self,e)
        self.toolbar.close_windows()
        
    def exit(self):
        self.clock.close()
        # Avoid memory leaks due to circular references preventing
        # the garbage collector from discarding this object
        del (self.clock)
        del(self.toolbar.master)
        del(self.dep_tabular.master)
        RaDisplay.exit(self)
        
    def __del__(self):
        logging.debug("PpDisplay.__del__")
    
class ventana_auxiliar:
    def __init__(self,master):
        self.master=master
        self.opened_windows=[]
        self.vr = IntVar()
        self.vr.set(master.draw_routes)
        self.vf = IntVar()
        self.vf.set(master.draw_point)
        self.vfn = IntVar()
        self.vfn.set(master.draw_point_names)
        self.vs = IntVar()
        self.vs.set(master.draw_sector)
        self.vsl = IntVar()
        self.vsl.set(master.draw_lim_sector)
        self.vt = IntVar()
        self.vt.set(master.draw_tmas)
        self.vd = IntVar()
        self.vd.set(master.draw_deltas)
        self.var_ver_localmap = {}
        
        for map_name in master.fir.local_maps:
            self.var_ver_localmap[map_name] = IntVar()
            self.var_ver_localmap[map_name].set(0)
        
        self.auto_sep = IntVar()
        self.auto_sep.set(self.master.auto_separation)
        self.speed_vector_var = IntVar()
        self.speed_vector_var.set(0)
        self.clock_speed_var = DoubleVar()
        self.clock_speed_var.set(1.0)        
        self.toolbar_id = None
    
    def close_windows(self):
        for w in self.opened_windows[:]:
            self.master.c.delete(w)
            self.opened_windows.remove(w)
        
    def redraw(self):
        master=self.master
        w=master.c
        ancho=master.width
        alto=master.height
        scale=master.scale
        
        w.delete(self.toolbar_id)


        MINIMUM_DISPLACEMENT = 80
        NORMAL_DISPLACEMENT = 10
        MAXIMUM_DISPLACEMENT = 3
        
        def set_displacement(mouse_pressed_button):
            if mouse_pressed_button == 1:
                return NORMAL_DISPLACEMENT
            elif mouse_pressed_button == 2:
                return MAXIMUM_DISPLACEMENT
            elif mouse_pressed_button == 3:
                return MINIMUM_DISPLACEMENT
        
        def b_izquierda(event):
            master.x0 -= ancho/set_displacement(event.num)/scale
            master.reposition()
            
        def b_derecha(event):
            master.x0 += ancho/set_displacement(event.num)/scale
            master.reposition()
            
        def b_arriba(event):
            master.y0 += ancho/set_displacement(event.num)/scale
            master.reposition()
            
        def b_abajo(event):
            master.y0 -= ancho/set_displacement(event.num)/scale
            master.reposition()
            
        MINIMUM_SCALE_FACTOR = 1.01
        NORMAL_SCALE_FACTOR = 1.1
        MAXIMUM_SCALE_FACTOR = 1.5
        
        LABEL_MIN_FONT_SIZE = 7
        LABEL_MAX_FONT_SIZE = 11
        LABEL_SIZE_STEP = 1

        def set_zoom_scale_on_event (event_number=1):
            if event_number==3:
                return MINIMUM_SCALE_FACTOR
            elif event_number==2:
                return MAXIMUM_SCALE_FACTOR
            elif event_number==1:
                return NORMAL_SCALE_FACTOR
            
        def b_zoom_mas(event):
            master.scale *= set_zoom_scale_on_event(event.num)
            master.reposition()
            
        def b_zoom_menos(event):
            master.scale /= set_zoom_scale_on_event(event.num)
            master.reposition()
            
        def b_standard():
            master.center_x=ancho/2
            master.center_y=(alto-40.)/2
            master.get_scale()
            master.reposition()
            
        def b_inicio():
            master.sendMessage({"message": "play"})
                
        def b_parar():
            master.sendMessage({"message": "pause"})
                
        def b_tamano_etiquetas(event):
            if event.num == 1:
                step_increment = LABEL_SIZE_STEP
            elif event.num == 3:
                step_increment = -LABEL_SIZE_STEP
            elif event.num == 2:
                step_increment = LABEL_MIN_FONT_SIZE
                
            font_size = master.label_font_size
            font_size += step_increment
            if font_size > LABEL_MAX_FONT_SIZE:
                font_size = LABEL_MIN_FONT_SIZE
            elif font_size < LABEL_MIN_FONT_SIZE:
                font_size = LABEL_MAX_FONT_SIZE
            master.label_font_size = font_size
            
            for vt in self.master.tracks:
                vt.l_font_size = font_size
            master.label_font.configure(size=master.label_font_size)
                        
        def b_show_hide_localmaps():
            master.local_maps_shown = []
            for map_name in master.fir.local_maps:
                if self.var_ver_localmap[map_name].get() != 0:
                    master.local_maps_shown.append(map_name)
            master.redraw_maps()
            
        def b_auto_separationaration():
            global auto_separation
            auto_separation = not auto_separation

        def get_selected(label=''):
            if master.selected_track==None:
                RaDialog(master.c, label=label,
                    text='No hay ning�n vuelo seleccionado')
            return master.selected_track

        def kill_acft():
            self.close_windows()
            if (get_selected('Matar vuelo')==None): return
            a = master.selected_track
            def kill():
                master.sendMessage({"message": "kill", "cs": a.cs})
                a.visible=False
            RaDialog(master.c,label=str(a.cs)+': Matar vuelo',
                       text='Matar '+str(a.cs),ok_callback=kill,
                       position=(a.x, a.y))
                    
        def quitar_fpr():
            for a in ejercicio:
                if w.itemcget(a.name+'fpr','fill')=='orange':
                    w.delete(a.name+'fpr')
                    
        def quitar_lads():
            global all_lads, superlad
            for lad_to_remove in all_lads:
                if lad_to_remove.line_id != None: w.delete(lad_to_remove.line_id)
                if lad_to_remove.text_id1 != None: w.delete(lad_to_remove.text_id1)
                if lad_to_remove.text_id2 != None: w.delete(lad_to_remove.text_id2)
                if lad_to_remove.text_id3 != None: w.delete(lad_to_remove.text_id3)
                if lad_to_remove.text_id4 != None: w.delete(lad_to_remove.text_id4)
                #     all_lads.remove(lad_to_remove)
                #     lad_to_remove.destroy()
                if superlad == lad_to_remove: superlad = None
            all_lads = []  
        win_identifier=None
        
        #def quitar_tormentas():
        #    for s in storms[:]:
        #        s.delete()
        #        storms.remove(s)
        
                        
        def define_holding():
            """Show a dialog to set the selected aircraft in a holding pattern over the selected fix"""
            self.close_windows()
            if (get_selected('Poner en espera')==None): return
            sel = master._tracks_flights[master.selected_track]
                
            def set_holding(e=None,entries=None):
                error = True
                ent_hold=entries['Fijo Principal:']
                ent_side=entries['Virajes (I/D):']
                fijo = ent_hold.get().upper()
                lado = ent_side.get().upper()
                auxiliar = ''
                # Si la espera est� publicada, los datos de la espera
                for [fijo_pub,rumbo,tiempo,lado_pub] in master.fir.holds:
                    if fijo_pub == fijo:
                        lado = lado_pub.upper()
                        derrota_acerc = rumbo
                        tiempo_alej = tiempo/60.0
                        for i in range(len(sel.route)):
                            [a,b,c,d] = sel.route[i]
                            if b == fijo:
                                auxiliar = [a,b,c,d]
                                error = False
                                break
                                # En caso contrario, TRK acerc = TRK de llegada y tiempo = 1 min
                if auxiliar == '':
                    for i in range(len(sel.route)):
                        [a,b,c,d] = sel.route[i]
                        if b == fijo:
                            if i == 0: # La espera se inicia en el siguiente punto del avi�n
                                auxi = sel.pos
                            else:
                                auxi = sel.route[i-1][0]
                            aux1 = r(a,auxi)
                            derrota_acerc = rp(aux1)[1]
                            auxiliar = [a,b,c,d]
                            error = False
                            tiempo_alej = 1.0/60.0
                            break
                if error:
                    ent_hold['bg'] = 'red'
                    ent_hold.focus_set()
                if lado == 'I':
                    giro = -1.0
                elif lado == 'D':
                    giro = +1.0
                else:
                    ent_side['bg'] = 'red'
                    ent_side.focus_set()
                    error=True
                if error:
                    return False  # Not validated correctly
                
                master.sendMessage({"message":"hold", "cs":sel.name,
                                    "fix":auxiliar,"inbound_track":derrota_acerc,
                                    "outbound_time":tiempo_alej,
                                    "turn_direction":giro})
                
            # Build the GUI Dialog
            entries=[]
            entries.append({'label':'Fijo Principal:','width':5,'def_value':sel.route[0][1]})
            entries.append({'label':'Virajes (I/D):','width':1,'def_value':'D'})
            RaDialog(w,label=sel.get_callsign()+': Poner en espera',ok_callback=set_holding,entries=entries)    
            
        def nueva_ruta():
            """Ask the user to set a new route and destination airdrome for the currently selected aircraft"""
            self.close_windows()
            if (get_selected('Nueva ruta')==None): return
            sel = master._tracks_flights[master.selected_track]

            def change_fpr(e=None,entries=None):
                ent_route,ent_destino=entries['Ruta:'],entries['Destino:']
                pts=ent_route.get().split(' ')
                logging.debug ('Input route points: '+str(pts))
                aux=[]
                fallo=False
                for a in pts:
                    hay_pto=False
                    for b in master.fir.points:
                        if a.upper() == b[0]:
                            aux.append([b[1],b[0],'',0])
                            hay_pto=True
                    if not hay_pto:
                        fallo=True
                if fallo:
                    ent_route['bg'] = 'red'
                    ent_route.focus_set()
                    return False  # Validation failed
                sel.destino = ent_destino.get().upper()

                master.sendMessage({"message":"change_fpr",
                                    "cs":sel.name,
                                    "route":aux})
            # Build the GUI Dialog
            entries=[]
            entries.append({'label':'Ruta:','width':50})
            entries.append({'label':'Destino:','width':5,'def_value':sel.destino})
            RaDialog(w,label=sel.get_callsign()+': Nueva ruta',
                                  ok_callback=change_fpr,entries=entries)    
            
        def cambiar_viento():
            """Show a dialog to allow the user to change the wind in real time"""
            self.close_windows()
            wind = master.wind
            def change_wind(e=None,entries=None):
                ent_dir=entries['Direcci�n:']
                ent_int=entries['Intensidad (kts):']
                int=ent_int.get()
                dir=ent_dir.get()
                fallo = False
                if dir.isdigit():
                    rumbo = (float(dir)+180.0) % 360.0
                else:
                    ent_dir['bg'] = 'red'
                    ent_dir.focus_set()
                    fallo = True
                if int.isdigit():
                    intensidad = float(int)
                else:
                    ent_int['bg'] = 'red'
                    ent_int.focus_set()
                    fallo = True
                if fallo:
                    return False  # Validation failed
                
                master.sendMessage({"message":"wind",
                                    "wind":[intensidad,rumbo]})
                master.wind = [intensidad, rumbo]
                
            # Build the GUI Dialog
            entries=[]
            entries.append({'label':'Direcci�n:','width':3,'def_value':int((wind[1]+180.0)%360.0)})
            entries.append({'label':'Intensidad (kts):','width':2,'def_value':int(wind[0])})
            RaDialog(w,label='Definir viento',
                    ok_callback=change_wind,entries=entries)    
            
            
        def hdg_after_fix():
            """Show a dialog to command the selected aircraft to follow a heading after a certain fix"""
            self.close_windows()
            if (get_selected('Rumbo despu�s de fijo')==None): return
            sel = master._tracks_flights[master.selected_track]
                
            def set_fix_hdg(e=None,entries=None):
                error = True
                ent_fix=entries['Fijo:']
                ent_hdg=entries['Rumbo:']
                fijo = ent_fix.get().upper()
                hdg = ent_hdg.get().upper()
                for i in range(len(sel.route)):
                    [a,b,c,d] = sel.route[i]
                    if b == fijo:
                        auxiliar = [a,b,c,d]
                        error = False
                        break
                if error:
                    ent_fix['bg'] = 'red'
                    ent_fix.focus_set()
                if not hdg.isdigit():
                    ent_hdg['bg'] = 'red'
                    ent_hdg.focus_set()
                    error = True
                else: 
                    hdg = float(hdg)
                if error:
                    return False  # Validation failed
                
                master.sendMessage({"message":"hdg_after_fix",
                                    "cs":sel.name,
                                    "aux":auxiliar,
                                    "hdg":hdg})

            # Build the GUI Dialog
            entries=[]
            entries.append({'label':'Fijo:','width':5,'def_value':str(sel.route[0][1])})
            entries.append({'label':'Rumbo:','width':3})
            RaDialog(w,label=sel.get_callsign()+': Rumbo despu�s de fijo',
                    ok_callback=set_fix_hdg,entries=entries)    
            
        def int_rdl():
            """Show a dialog to command the selected aircraft to intercept a radial"""
            self.close_windows()
            if (get_selected('Interceptar radial')==None): return
            sel = master._tracks_flights[master.selected_track]
            def set_rdl(e=None,entries=None):
                error = True
                ent_fix=entries['Fijo:']
                ent_rdl=entries['Radial:']
                ent_d_h=entries['Desde/Hacia (D/H)']
                fijo = ent_fix.get().upper()
                rdl = ent_rdl.get().upper()
                d_h = ent_d_h.get().upper()
                for [nombre,coord] in master.fir.points:
                    if nombre == fijo:
                        auxiliar = coord
                        error = False
                        break
                if error:
                    ent_fix['bg'] = 'red'
                    ent_fix.focus_set()
                if not rdl.isdigit():
                    ent_rdl['bg'] = 'red'
                    ent_rdl.focus_set()
                    error = True
                else: 
                    rdl = float(rdl)
                if d_h == 'H':
                    correccion = 180.
                elif d_h == 'D':
                    correccion = 0.
                else:
                    ent_d_h['bg'] = 'red'
                    ent_d_h.focus_set()
                    error = True
                if error:
                    return False  # Validation failed
                
                master.sendMessage({"message":"int_rdl",
                                    "cs":sel.name,
                                    "aux":auxiliar,
                                    "track":(rdl + correccion)% 360.})
                
            # Build the GUI Dialog
            entries=[]
            entries.append({'label':'Fijo:','width':5,'def_value':str(sel.route[0][1])})
            entries.append({'label':'Radial:','width':3})
            entries.append({'label':'Desde/Hacia (D/H)','width':1,'def_value':'D'})
            RaDialog(w,label=sel.get_callsign()+': Interceptar radial',
                    ok_callback=set_rdl,entries=entries)    
            
        def b_execute_map():
            """Show a dialog to command the selected aircraft to miss the approach"""
            self.close_windows()
            if (get_selected('Ejectuar MAP')==None): return
            sel = master._tracks_flights[master.selected_track]
            if sel.destino not in master.fir.rwys.keys():
                RaDialog(w, label='Ejecutar MAP',
                         text='Aeropuerto de destino sin procedimientos de APP')
                return                
            def exe_map(e=None):
                master.sendMessage({"message":"execute_map", "cs":sel.name})
            RaDialog(w,label=sel.get_callsign()+': Ejecutar MAP',
                     text='Ejecutar MAP', ok_callback=exe_map)
            
        def b_int_ils():
            """Show a dialog to command the selected aircraft to intercept and follow the ILS"""
            self.close_windows()
            if (get_selected('Interceptar ILS')==None): return
            sel = master._tracks_flights[master.selected_track]
            if sel.destino not in master.fir.rwys.keys():
                RaDialog(w, label=sel.get_callsign()+': Interceptar ILS',
                         text='Aeropuerto de destino sin procedimientos de APP')
                return
            elif sel.fijo_app == 'N/A':
                RaDialog(w,label=sel.get_callsign()+': Interceptar ILS',
                         text='Vuelo sin IAF. A�ada la ruta hasta el IAF y reintente')
                return
                
            def int_ils(e=None):
                master.sendMessage({"message":"int_ils", "cs":sel.name})
            RaDialog(w,label=sel.get_callsign()+': Interceptar ILS',
                     text='Interceptar ILS', ok_callback=int_ils)
            
        def b_llz():
            """Show a dialog to command the selected aircraft to intercept and follow \
            the LLZ (not the GP)"""
            self.close_windows()
            if (get_selected('Interceptar LLZ')==None): return
            sel = master._tracks_flights[master.selected_track]
            if sel.destino not in master.fir.rwys.keys():
                RaDialog(w, label=sel.get_callsign()+': Interceptar LLZ',
                         text='Aeropuerto de destino sin procedimientos de APP')
                return
            elif sel.fijo_app == 'N/A':
                RaDialog(w,label=sel.get_callsign()+': Interceptar LLZ',
                         text='Vuelo sin IAF. A�ada la ruta hasta el IAF y reintente')
                return
            def int_llz(e=None):
                master.sendMessage({"message":"int_llz", "cs":sel.name})
            RaDialog(w,label=sel.get_callsign()+': Interceptar LLZ',
                     text='Interceptar LLZ', ok_callback=int_llz)
            
        def ver_detalles():
            """Show a dialog to view details of the selected flight"""
            self.close_windows()
            if (get_selected('Ver Detalles')==None): return
            sel = self.master.selected_track
            # TODO The RaDialog should probably export the contents frame
            # and we could use it here to build the contents using a proper grid
            RaDialog(self.master.c, label=sel.cs+': Detalles',
                     text='Origen: '+sel.orig+
                     '\tDestino: '+sel.dest+
                     '\nTipo:   '+sel.type.ljust(4)+
                     '\tRFL:     '+str(int(sel.rfl))+
                     '\nCallsign: '+sel.radio_cs)
            
        def b_orbitar():
            """Show a dialog to command the selected aircraft to make orbits"""    
            self.close_windows()
            if (get_selected('�rbita inmediata')==None): return
            sel = master._tracks_flights[master.selected_track]
            def set_orbit(e=None,sel=sel,entries=None):
                side_aux = entries['Orbitar hacia:']['value']
                if side_aux.upper() == 'IZDA':
                    dir = avion.LEFT  # Constant defined in avion.py
                else:
                    dir = avion.RIGHT
                master.sendMessage({"message":"orbit", "cs":sel.name, "direction":dir})
            entries=[]
            entries.append({'label':'Orbitar hacia:',
                            'values':('IZDA','DCHA'),
                            'def_value':'IZDA'})
            RaDialog(w,label=sel.get_callsign()+': Orbitar',
                     ok_callback=set_orbit, entries=entries)      
            
        def b_rwy_change():
            # TODO THIS IS PROBABLY NOT WORKING!!
            # Needs to be retested and probably rethought
            self.close_windows()
            global win_identifier
            if win_identifier<>None:
                w.delete(win_identifier)
                win_identifier=None
                return
            rwy_chg = Frame(w)
            txt_titulo = Label (rwy_chg, text = 'Nuevas pistas en uso')
            txt_titulo.grid(column=0,row=0,columnspan=2)
            line = 1
            com_airp=[['',0]]
            for airp in rwys.keys():
                com_airp.append([airp,0.0])
                txt_airp = Label (rwy_chg, text = airp.upper())
                txt_airp.grid(column=0,row=line,sticky=W)
                com_airp[line][1] = ComboBox (rwy_chg, bg = 'white',editable = True)
                num = 0
                for pista in rwys[airp].split(','):
                    com_airp[line][1].insert(num,pista)
                    if pista == rwyInUse[airp]:
                        com_airp[line][1].pick(num)
                    num=num+1
                com_airp[line][1].grid(column=1,row=line,sticky=W)
                line=line+1
            but_acept = Button(rwy_chg,text='Hecho')
            but_acept.grid(column=0,row=line)
            win_identifier = w.create_window(400,400,window=rwy_chg)
            def close_rwy_chg(e=None,ident = win_identifier):
                global rwyInUse
                com_airp.pop(0)
                for [airp,num] in com_airp:
                    print 'Pista en uso de ',airp,' es ahora: ',num.cget('value'),'. Cambiando los procedimientos'
                    rwyInUse[airp] = num.cget('value')
                    for avo in ejercicio:
                        complete_flight_plan(avo)
                        if avo.origen in rwys.keys() and not avo.is_flying():
                            avo.route.pop(0)
                        avo.set_app_fix()   
                w.delete(ident)
            but_acept['command']= close_rwy_chg
            
            but_cancel = Button(rwy_chg,text='Descartar')
            but_cancel.grid(column=1,row=line)
            def discard_rwy_chg(e=None,ident = win_identifier):
                w.delete(ident)
            but_cancel['command']= discard_rwy_chg
            
        def b_auth_approach():
            self.close_windows()
            if (get_selected('Autorizar a Aproximaci�n')==None): return
            sel = master._tracks_flights[master.selected_track]
            if sel.destino not in master.fir.rwys.keys():
                RaDialog(w, label=sel.get_callsign()+': Autorizar a aproximaci�n',
                         text='Aeropuerto de destino sin procedimientos de APP')
                return
                
            def auth_app(e=None,avo=sel, entries=None):
                master.sendMessage({"message":"execute_app", "cs":sel.name,
                                    "dest": entries['Destino:'].get().upper(),
                                    "iaf": entries['IAF:'].get().upper()})
            # Build entries
            for i in range(len(sel.route),0,-1):
                if sel.route[i-1][1] in master.fir.proc_app.keys():
                    fijo_app = sel.route[i-1][1]
                    break
            entries=[]
            entries.append({'label':'Destino:', 'width':4, 'def_value':sel.destino})
            entries.append({'label':'IAF:', 'width':5, 'def_value':fijo_app})
            RaDialog(w,label=sel.get_callsign()+': Autorizar a Aproximaci�n',
                     ok_callback=auth_app, entries=entries)      

        ventana=Frame(w,bg='gray',width=ancho)
        self.but_inicio = Button(ventana,bitmap='@'+IMGDIR+'start.xbm',command=b_inicio)
        self.but_inicio.pack(side=LEFT,expand=1,fill=X)
        self.but_parar = Button(ventana,bitmap='@'+IMGDIR+'pause.xbm',command=b_parar)
        self.but_parar.pack(side=LEFT,expand=1,fill=X)
        
        self.but_izq = Button(ventana,bitmap='@'+IMGDIR+'left.xbm')
        self.but_izq.pack(side=LEFT,expand=1,fill=X)
        self.but_izq.bind("<Button-1>",b_izquierda)
        self.but_izq.bind("<Button-2>",b_izquierda)
        self.but_izq.bind("<Button-3>",b_izquierda)

        self.but_arriba = Button(ventana,bitmap='@'+IMGDIR+'up.xbm')
        self.but_arriba.pack(side=LEFT,expand=1,fill=X)
        self.but_arriba.bind("<Button-1>",b_arriba)
        self.but_arriba.bind("<Button-2>",b_arriba)
        self.but_arriba.bind("<Button-3>",b_arriba)            
        
        self.but_abajo = Button(ventana,bitmap='@'+IMGDIR+'down.xbm')
        self.but_abajo.pack(side=LEFT,expand=1,fill=X)
        self.but_abajo.bind("<Button-1>",b_abajo)
        self.but_abajo.bind("<Button-2>",b_abajo)
        self.but_abajo.bind("<Button-3>",b_abajo)            
    
        self.but_derecha = Button(ventana,bitmap='@'+IMGDIR+'right.xbm')
        self.but_derecha.pack(side=LEFT,expand=1,fill=X)
        self.but_derecha.bind("<Button-1>",b_derecha)
        self.but_derecha.bind("<Button-2>",b_derecha)
        self.but_derecha.bind("<Button-3>",b_derecha)            
        
#            self.but_zoom_mas = Button(ventana,bitmap='@'+IMGDIR+'zoom.xbm',command=b_zoom_mas)
        self.but_zoom_mas = Button(ventana,bitmap='@'+IMGDIR+'zoom.xbm')
        self.but_zoom_mas.pack(side=LEFT,expand=1,fill=X)
        self.but_zoom_mas.bind("<Button-1>",b_zoom_mas)
        self.but_zoom_mas.bind("<Button-2>",b_zoom_mas)
        self.but_zoom_mas.bind("<Button-3>",b_zoom_mas)
        
#            self.but_zoom_menos = Button(ventana,bitmap='@'+IMGDIR+'unzoom.xbm',command=b_zoom_menos)
        self.but_zoom_menos = Button(ventana,bitmap='@'+IMGDIR+'unzoom.xbm')
        self.but_zoom_menos.pack(side=LEFT,expand=1,fill=X)
        self.but_zoom_menos.bind("<Button-1>",b_zoom_menos)
        self.but_zoom_menos.bind("<Button-2>",b_zoom_menos)
        self.but_zoom_menos.bind("<Button-3>",b_zoom_menos)
        
        self.but_standard = Button(ventana,bitmap='@'+IMGDIR+'center.xbm',command=b_standard)
        self.but_standard.pack(side=LEFT,expand=1,fill=X)
        
        self.but_tamano_etiq = Button(ventana,bitmap='@'+IMGDIR+'labelsize.xbm')
        self.but_tamano_etiq.pack(side=LEFT,expand=1,fill=X)
        self.but_tamano_etiq.bind("<Button-1>",b_tamano_etiquetas)
        self.but_tamano_etiq.bind("<Button-2>",b_tamano_etiquetas)
        self.but_tamano_etiq.bind("<Button-3>",b_tamano_etiquetas)
        
        self.but_term = Button(ventana,text='Kill',command=kill_acft)
        self.but_term.pack(side=LEFT,expand=1,fill=X)
        self.but_ruta = Button(ventana,text='Ruta',command=nueva_ruta)
        self.but_ruta.pack(side=LEFT,expand=1,fill=X)
        self.but_datos = Button(ventana,text='Datos',command=ver_detalles)
        self.but_datos.pack(side=LEFT,expand=1,fill=X)
        self.but_quitar_lads = Button(ventana,text='LADs', fg = 'red',command = self.master.delete_lads)
        self.but_quitar_lads.pack(side=LEFT,expand=1,fill=X)
        self.but_quitar_fpr = Button(ventana,text='Rutas', fg = 'red',command = self.master.delete_routes)
        self.but_quitar_fpr.pack(side=LEFT,expand=1,fill=X)
        #self.but_quitar_tormentas = Button(ventana,text='TS', fg = 'red',command = self.master.quitar_tormentas)
        #self.but_quitar_tormentas.pack(side=LEFT,expand=1,fill=X)
        self.but_ver_proc = Button(ventana, text = 'PROCs')
        self.but_ver_proc.pack(side=LEFT,expand=1,fill=X)
        def procs_buttons():
            self.close_windows()
            ventana_procs = Frame(w,bg='gray')
            self.but_espera = Button(ventana_procs, text='Esperas', command = define_holding)
            self.but_espera.grid(column=0,row=0,sticky=E+W)
            self.but_hdg_fix = Button(ventana_procs, text = 'HDG despues fijo', command = hdg_after_fix)
            self.but_hdg_fix.grid(column=0,row=1,sticky=E+W)
            self.but_int_rdl = Button(ventana_procs, text = 'Int. RDL', command = int_rdl)
            self.but_int_rdl.grid(column=0,row=2,sticky=E+W)
            self.but_chg_rwy = Button(ventana_procs, text = 'Cambio RWY', command = b_rwy_change)
            self.but_chg_rwy.grid(column=0,row=3,sticky=E+W)
            self.but_orbit = Button(ventana_procs, text = 'Orbitar aqu�', command = b_orbitar)
            self.but_orbit.grid(column=0,row=4,sticky=E+W)
            self.but_wind = Button(ventana_procs, text = 'Cambiar viento', command = cambiar_viento)
            self.but_wind.grid(column=0,row=5,sticky=E+W)
            i=w.create_window(ventana.winfo_x()+self.but_ver_proc.winfo_x(),alto-ventana.winfo_height(),window=ventana_procs,anchor='sw')
            self.opened_windows.append(i)
        self.but_ver_proc['command'] = procs_buttons
        self.but_ver_app = Button(ventana, text = 'APP')
        self.but_ver_app.pack(side=LEFT,expand=1,fill=X)
        def maps_buttons():
            self.close_windows()
            ventana_maps = Frame(w,bg='gray')
            self.but_app_proc = Button(ventana_maps, text = 'APP PROC.', command = b_auth_approach)
            self.but_app_proc.grid(column=0,row=0,sticky=E+W)
            self.but_ils_vec = Button(ventana_maps, text = 'ILS (vectores)', command = b_int_ils)
            self.but_ils_vec.grid(column=0,row=1,sticky=E+W)
            self.but_loc = Button(ventana_maps, text = 'LOCALIZADOR', command = b_llz)
            self.but_loc.grid(column=0,row=2,sticky=E+W)
            self.but_exe_map = Button(ventana_maps, text = 'EJECUTAR MAP', command = b_execute_map)
            self.but_exe_map.grid(column=0,row=3,sticky=E+W)
            i=w.create_window(ventana.winfo_x()+self.but_ver_app.winfo_x(),alto-ventana.winfo_height(),window=ventana_maps,anchor='sw')
            self.opened_windows.append(i)
        self.but_ver_app['command'] = maps_buttons

        self.but_auto_separation = Checkbutton(ventana, text = 'SEP', variable = self.auto_sep, command=lambda: master.toggle_auto_separation())
        self.but_auto_separation.pack(side=LEFT,expand=1,fill=X)

        self.but_ver_maps = Button(ventana, text = 'MAPAS')
        self.but_ver_maps.pack(side=LEFT,expand=1,fill=X)
        def mapas_buttons():
            self.close_windows()
            ventana_mapas = Frame(w)
            myrow = 0
            self.but_ver_nombrs_ptos = Checkbutton(ventana_mapas, text = 'Nombres Fijos', variable=self.vfn, command=self.master.toggle_point_names)
            self.but_ver_nombrs_ptos.grid(column=0,row=myrow,sticky=W)
            myrow+= 1
            self.but_ver_ptos = Checkbutton(ventana_mapas, text = 'Fijos', variable=self.vf, command=self.master.toggle_point)
            self.but_ver_ptos.grid(column=0,row=myrow,sticky=W)
            myrow+= 1
            self.but_ver_routes = Checkbutton(ventana_mapas, text = 'Aerovias', variable=self.vr, command=self.master.toggle_routes)
            self.but_ver_routes.grid(column=0,row=myrow,sticky=W)
            myrow+= 1
            self.but_ver_sector = Checkbutton(ventana_mapas, text = 'Sector', variable=self.vs, command=self.master.toggle_sector)
            self.but_ver_sector.grid(column=0,row=myrow,sticky=W)
            myrow+= 1
            self.but_ver_lim_sector = Checkbutton(ventana_mapas, text = 'Lim. Sector', variable=self.vsl, command=self.master.toggle_lim_sector)
            self.but_ver_lim_sector.grid(column=0,row=myrow,sticky=W)
            myrow+= 1
            self.but_ver_tmas = Checkbutton(ventana_mapas, text = 'TMAs',  variable=self.vt, command=self.master.toggle_tmas)
            self.but_ver_tmas.grid(column=0,row=myrow,sticky=W)
            myrow+= 1
            self.but_ver_deltas = Checkbutton(ventana_mapas, text = 'Deltas', variable=self.vd, command=self.master.toggle_deltas)
            self.but_ver_deltas.grid(column=0,row=myrow,sticky=W)
            
            myrow += 1
            #map_name_list = master.fir.local_maps.keys()
            #map_name_list.sort()
            
            for map_name in self.master.fir.local_maps_order:#map_name_list:
                self.but_ver_local_map = Checkbutton(ventana_mapas, text = map_name, variable = self.var_ver_localmap[map_name], command=b_show_hide_localmaps)
                self.but_ver_local_map.grid(column=0,row=myrow,sticky=W)
                myrow += 1

            i=w.create_window(ventana.winfo_x()+self.but_ver_maps.winfo_x(),alto-ventana.winfo_height(),window=ventana_mapas,anchor='sw')
            self.opened_windows.append(i)
        self.but_ver_maps['command'] = mapas_buttons

        self.but_ver_tabs = Button(ventana, text = 'TABs')
        self.but_ver_tabs.pack(side=LEFT,expand=1,fill=X)
        def tabs_buttons():
            self.close_windows()
            ventana_tabs = Frame(w,bg='gray')
            #self.but_reports = Button(ventana_tabs, text='Notificaciones',
            #                     command = acftnotices.show, state=DISABLED)
            #self.but_reports.grid(column=0,row=0,sticky=E+W)
            self.but_departures = Button(ventana_tabs, text='Salidas',
                                 command = master.dep_tabular.show)
            self.but_departures.grid(column=0,row=1,sticky=E+W)
            self.but_printlist = Button(ventana_tabs, text='Fichas',
                                 command = master.print_tabular.show)
            self.but_printlist.grid(column=0,row=2,sticky=E+W)
            i=w.create_window(ventana.winfo_x()+self.but_ver_tabs.winfo_x(),alto-ventana.winfo_height(),window=ventana_tabs,anchor='sw')
            self.opened_windows.append(i)
        self.but_ver_tabs['command'] = tabs_buttons
        def cambia_vect_vel(e=None):
            master.change_speed_vector(self.speed_vector_var.get()/60.)
        cnt_vect_vel = Control(ventana, label="Vel:", min=0, max=5, integer=1, command=cambia_vect_vel, variable=self.speed_vector_var)
        cnt_vect_vel.pack(side=LEFT,expand=1,fill=X)
        def cambia_vel_reloj(e=None):
            try:
                master.sendMessage({"message":"clock_speed",
                                    "data": float(master.clock_speed_var.get())})
            except:
                # TODO Tkinter will call this function at interface build time
                # before the sendMessage function has been created
                # and thus will always fail at first
                logging.debug("Unable to send clock_speed command", exc_info=True)
        cnt_vel_reloj = Control(ventana, label="Clock X:", min=0.5, max=99.0, step=0.1, command=cambia_vel_reloj, variable=master.clock_speed_var)
        cnt_vel_reloj.pack(side=LEFT,expand=1,fill=X)
        
        self.toolbar_id=w.create_window(0,alto,width=ancho,window=ventana,anchor='sw')
        ventana.update_idletasks()
        logging.debug ('Auxiliary window width: '+str(ventana.winfo_width()))

class AcftNotices(RaTabular):
    """A tabular window showing reports and requests from aircraft"""
    def __init__(self, master=None, flights=None):
        """Create a tabular showing aircraft reports and requests"""
        RaTabular.__init__(self, master, label='Notificaciones',
                           position=(120,200), closebuttonhides=True)
        self._last_updated=0.
        self._flights=flights
        
    def update(self,t):
        """Check whether any new message should be printed"""
        # We need only update this tabular at most once a second
        if t-self._last_updated<1/60./60.:
            return
            
        # Check whether the pilots have anything to report.
        for acft in self._flights:
            for i,report in enumerate(acft.reports):
                if t>report['time']:
                    h=int(t)
                    m=int(60*(t-h))
                    report='%02d:%02d %s %s'%(h,m,acft.name,report['text'])
                    self.insert(END, report)
                    self.notify()
                    del acft.reports[i]
        self._last_updated=t
        
    def notify(self):
        """Make it obvious to the user that there has been a new notification"""
        import sys
        if sys.platform=='win32':
            import winsound
            try:
                winsound.PlaySound(SNDDIR+'/chime.wav', winsound.SND_NOSTOP|winsound.SND_ASYNC)
            except:
                pass


class DepTabular(RaTabular):
    """A tabular window showing departure aircraft"""
    # TODO
    # On second thought the DepTabular should feed from the master's flights
    # list, as the master should have all the information about the state
    # of the departing aircraft
    def __init__(self, radisplay, canvas=None, flights=None):
        """Create a tabular showing aircraft reports and requests"""
        RaTabular.__init__(self, canvas, label='Salidas',
                           position=(10,300), closebuttonhides=True,
                           anchor = NW)
        self.canvas = canvas
        self.master = radisplay
        self.list.configure(font="Courier 8", selectmode=SINGLE)
        self.adjust()
        ra_bind(radisplay, self.list, "<Button-1>", self.clicked)
        self.deps=[]

    def update(self, dep_list):
        """Update the tabular using the given departure list"""
        self.list.delete(0,self.list.size())
        self.deps=[]
        i=0
        for dep in dep_list:
            self.deps.append(dep)
            eobt = '%02d:%02d:%02d'%get_h_m_s(dep['eobt']*3600)
            t = dep['ad']+' '+dep['cs'].ljust(7)+' '+eobt[0:5]+' '+dep['sid']
            self.list.insert(i, t)
            if dep['state']==avion.READY:
                self.list.itemconfig(i, background="green", foreground="black")
            i+=1
        self.adjust()
        if len([dep for dep in self.deps if dep['state']==avion.READY])>0:
            self.show()
                
    def clicked(self, e=None):
        lb = self.list
        if lb.nearest(e.y)<0:  # No items
            return
        index = lb.nearest(e.y)
        if e.y<lb.bbox(index)[1] or e.y>(lb.bbox(index)[3]+lb.bbox(index)[1]):
            return  # Not really clicked within the item
        dep=self.deps[index]
        if dep['state']==avion.READY:
            self.depart_dialog(dep, index)

    def depart_dialog(self, dep, index):
        """Show a dialog to allow the user to depart an aircraft"""
        def depart(e=None,entries=None):
            ent_sid=entries['SID:']
            ent_cfl=entries['CFL:']
            sid=ent_sid.get()
            cfl=ent_cfl.get()
            fallo = False
            if cfl.isdigit():
                cfl = float(cfl)
            else:
                ent_cfl['bg'] = 'red'
                ent_cfl.focus_set()
                fallo = True
            # TODO this should really test the SID, and should show a
            # dropdown, but I'm leaving it like it is until
            # the aircraft object is redesigned
            if fallo:
                return False  # Validation failed
            
            self.master.sendMessage({"message":"depart",
                                "cs":dep['cs'],"sid":sid, "cfl":cfl})
            del self.deps[index]
            self.list.delete(index)
            
        # Build the GUI Dialog
        entries=[]
        entries.append({'label':'SID:','width':5,'def_value':dep['sid']})
        entries.append({'label':'CFL:','width':3,'def_value':int(dep['cfl'])})
        RaDialog(self.canvas,label=dep['cs']+': Despegar',
                    ok_callback=depart,entries=entries)    
