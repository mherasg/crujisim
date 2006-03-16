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
"""Information regarding a Flight Information Region"""

import logging
import os
from stat import *
from MathUtil import *

class FIR:
    """FIR information and processess"""    
    
    def __init__(self, fir_file):
        """Create a FIR instance"""
        
        self.file = fir_file
        self.points=[]   # List of geo coordinates of points
        self.rel_points={}#Dictionary of points relative to another. Format: [RELATIVE_POINT NAME]:[POINT_NAME],[RADIAL],[DISTANCE]
        self.routes=[]   # List of points defining standard routes within the FIR
        self.airways=[] #List of airways... just for displaying on map
        self.tmas=[]     # List of points defining TMAs
        self.local_maps={}  # Dictionary of local maps
        self.aerodromes=[]  # List of aerodrome codes
        self.ad_elevations={} #List of AD elevations
        self.holds=[]    # List of published holds [fix,hdg,time,turns]   
        self.rwys={}     # IFR rwys of each AD
        self.rwyInUse={} # Rwy in use at each AD
        self.procedimientos={}  # Standard procedures (SIDs and STARs)
        self.proc_app={}
        self.deltas=[]
        self.sectors=[]  # List of sector names
        self._sector_sections={}  # Section name of each sector
        self.boundaries={}  # List of boundary points for each sector
        self.min_sep={}  # Minimum radar separation for each sector
        self.auto_departures={}  # Whether there are autodepartures for each sector
        self.fijos_impresion={}
        self.fijos_impresion_secundarios={}
        self.local_maps_order=[]
        # TODO: ADs should be a class on its own, with attributes
        # like elevation, rwys, which sector has to approve a departure if any,
        # etc.
        self.local_ads={}
        self.release_required_ads={}
        
        import ConfigParser
        self._firdef = ConfigParser.ConfigParser()
        self._firdef.readfp(open(fir_file,'r'))

        # FIR name
        self.name = self._firdef.get('datos','nombre')
        
        # Puntos del FIR
        logging.debug('Points')
        lista=self._firdef.items('puntos')
        for (nombre,coord) in lista:
            coord_lista=coord.split(',')
            if len(coord_lista)==2:
                (x,y)=coord.split(',')
                x=float(x)
                y=float(y)
                self.points.append([nombre.upper(),(x,y)])
            elif len(coord_lista)==3:                              #if len coord is 3, the point is defined referenced to another
                (nombre_base,x,y)=coord.split(',')
                x=float(x)
                y=float(y)
                self.rel_points[nombre.upper()]=[nombre_base.upper(),(x,y)]
        if len(self.rel_points)>0:
            #If at least one relative point has been read we should try to convert it to
            #cartessian coordinates
            scan_again = True
            while scan_again:
                scan_again = False
                for relative_point_name in self.rel_points:
                    #First check if the new relative point already exists
                    dummy = [p[0] for p in self.points if p[0]==relative_point_name]
                    if len(dummy) == 0:
                    #The point does not exist, lets try if I can ad it
                    #To do so I have to check if the base points exists
                        base_point_name = self.rel_points[relative_point_name][0]
                        base_point_coordinates = [p[1] for p in self.points if p[0]==base_point_name]
                        if len(base_point_coordinates)>0:
                            #Exists, so lets make the conversion to cartesian's and add the point to the list
                            (x,y)=pr(self.rel_points[relative_point_name][1])
                            (x,y)=(x+base_point_coordinates[0][0],y+base_point_coordinates[0][1])
                            self.points.append([relative_point_name,(x,y)])
                            scan_again = True

            # FIR Routes
        lista=self._firdef.items('rutas')
        for (num,aux) in lista:
            linea=aux.split(',')
            aux2=()
            for p in linea:
                for q in self.points:
                    if p==q[0]:
                        aux2=aux2+q[1]
            self.routes.append([aux2])
            
        #FIR Airways   
        lista=self._firdef.items('aerovias')
        for (num,aux) in lista:
            linea=aux.split(',')
            aux2=()
            for p in linea:
                for q in self.points:
                    if p==q[0]:
                        aux2=aux2+q[1]
            self.airways.append([aux2])
            # FIR TMAs
        if self._firdef.has_section('tmas'):
            lista=self._firdef.items('tmas')
            for (num,aux) in lista:
                linea=aux.split(',')
                aux2=()
                for p in linea:
                    for q in self.points:
                        if p==q[0]:
                            aux2=aux2+q[1]
                self.tmas.append([aux2])
                # Local maps
        if self._firdef.has_section('mapas_locales'):
            local_map_string = self._firdef.get('mapas_locales', 'mapas')
            local_map_sections = local_map_string.split(',')
            for map_section in local_map_sections:
                if self._firdef.has_section(map_section):
                    map_name = self._firdef.get(map_section, 'nombre')
                    map_items = self._firdef.items(map_section)
                    self.local_maps_order.append(map_name)
                    # Store map name and graphical objects in local_maps
                    # dictionary (key: map name)
                    map_objects = []
                    for item in map_items:
                        logging.debug (item[0].lower())
                        if item[0].lower() != 'nombre':
                            map_objects.append(item[1].split(','))
                    self.local_maps[map_name] = map_objects
                    # FIR aerodromes
        if self._firdef.has_section('aeropuertos'):
            lista=self._firdef.items('aeropuertos')
            for (num,aux) in lista:
                for a in aux.split(','):
                    self.aerodromes.append(a)
                    # Published holding patterns
        if self._firdef.has_section('elevaciones'):
            elev_list=self._firdef.items('elevaciones')[0][1].split(",")
            for ad,elev in zip(self.aerodromes, elev_list):
                self.ad_elevations[ad]=int(elev)
        if self._firdef.has_section('esperas_publicadas'):
            lista=self._firdef.items('esperas_publicadas')
            for (fijo,datos) in lista:
                (rumbo,tiempo_alej,lado) = datos.split(',')
                rumbo,tiempo_alej,lado = float(rumbo),float(tiempo_alej),lado.upper()
                self.holds.append([fijo.upper(),rumbo,tiempo_alej,lado])
                # IFR Runways
        if self._firdef.has_section('aeropuertos_con_procedimientos'):
            lista=self._firdef.items('aeropuertos_con_procedimientos')
            for (airp,total_rwys) in lista:
                self.rwys[airp.upper()] = total_rwys
                # First runway if the preferential
                self.rwyInUse[airp.upper()] = total_rwys.split(',')[0]
        # SID and STAR procedures
        for aerop in self.rwys.keys():
            for pista in self.rwys[aerop].split(','):
                # SID
                sid = {}
                lista = self._firdef.items('sid_'+pista)
                for (nombre_sid,puntos_sid) in lista:
                    last_point = puntos_sid.split(',')[-1]
                    # Cambiamos el formato de puntos para que se pueda a�adir directamente al plan de vuelo
                    points_sid = []
                    for nombre_punto in puntos_sid.split(','):
                        punto_esta=False
                        for q in self.points:
                            if nombre_punto==q[0]:
                                points_sid.append([q[1],q[0],'00:00'])
                                punto_esta=True
                        if not punto_esta:
                            incidencias.append('Punto ' + nombre_punto + ' no encontrado en procedimiento '+ nombre_sid)
                            logging.debug ('Punto ' + nombre_punto + ' no encontrado en procedimiento '+ nombre_sid)
                    sid[last_point] = (nombre_sid,points_sid)
                # Procedimientos STAR
                star = {}
                lista = self._firdef.items('star_'+pista)
                for (nombre_star,puntos_star) in lista:
                    last_point = puntos_star.split(',')[0]
                    # Cambiamos el formato de puntos para que se pueda a�adir directamente al plan de vuelo
                    points_star = []
                    for nombre_punto in puntos_star.split(','):
                        punto_esta=False
                        for q in self.points:
                            if nombre_punto==q[0]:
                                points_star.append([q[1],q[0],'00:00'])
                                punto_esta=True
                        if not punto_esta:
                            incidencias.append('Punto ' + nombre_punto + ' no encontrado en procedimiento '+ nombre_star)
                            logging.debug ('Punto ',nombre_punto,' no encontrado en procedimiento ', nombre_star)
                            #        points_star.pop(-1)
                    star[last_point] = (nombre_star,points_star)
                self.procedimientos[pista] = (sid,star)
        logging.debug ('Lista de procedimientos'+ str(self.procedimientos))
        logging.debug ('Pistas: '+ str(self.rwys))
        logging.debug ('Pistas en uso:' + str(self.rwyInUse))
        # Procedimientos de aproximaci�n
        for aerop in self.rwys.keys():
            for pista in self.rwys[aerop].split(','):
                # Procedimientos aproximaci�n
                procs_app=self._firdef.items('app_'+pista)
                for [fijo,lista] in procs_app:
                    lista = lista.split(',')
                    logging.debug (str(pista)+'Datos APP '+str(fijo)+' son '+str(lista))
                    points_app = []
                    for i in range(0,len(lista),2):
                        dato = lista[i]
                        altitud=lista[i+1]
                        if dato == 'LLZ':
                            break
                        else:
                            punto_esta=False
                            for q in self.points:
                                if dato==q[0]:
                                    points_app.append([q[1],q[0],'',float(altitud)])
                                    punto_esta=True
                            if not punto_esta:
                                incidencias.append('Punto ' + dato + ' no encontrado en procedimiento app_'+pista+' APP')
                                logging.debug ('Punto ' + dato + ' no encontrado en procedimiento app_'+pista+' APP')
                    llz_data = []
                    nombre_ayuda = lista[i+1]
                    rdl_ayuda = float(lista[i+2])
                    dist_ayuda = float(lista[i+3])
                    pdte_ayuda = float(lista[i+4])
                    alt_pista = float(lista[i+5])
                    for q in self.points:
                        if lista[i+1]==q[0]:
                            llz_data = [q[1],(rdl_ayuda + 180.)%360.,dist_ayuda,pdte_ayuda,alt_pista]
                            break
                    if llz_data == []:
                        incidencias.append('Localizador no encontrado en procedimiento app_'+pista+' APP')
                        logging.debug ('Localizador no encontrado en procedimiento app_'+pista+' APP')
                        # Ahora vamos a por los puntos de la frustrada        
                    points_map = []
                    lista = lista [i+7:]
                    logging.debug ('Resto para MAp: '+str(lista))
                    for i in range(0,len(lista),2):
                        dato = lista[i]
                        altitud=lista[i+1]
                        punto_esta=False
                        for q in self.points:
                            if dato==q[0]:
                                points_map.append([q[1],q[0],'',float(altitud)])
                                punto_esta=True
                        if not punto_esta:
                            incidencias.append('Punto ' + dato + ' no encontrado en procedimiento app_'+pista+' MAP')
                            logging.debug ('Punto ' + dato + ' no encontrado en procedimiento app_'+pista+' MAP')
                            # Guardamos los procedimientos
                    self.proc_app[fijo.upper()]=(points_app,llz_data,points_map)
        logging.debug ('Lista de procedimientos de aproximaci�n'+str(self.proc_app))
        
        # Deltas del FIR
        if self._firdef.has_section('deltas'):
            lista=self._firdef.items('deltas')
            for (num,aux) in lista:
                logging.debug ('Leyendo delta '+str(num))
                linea=aux.split(',')
                aux2=()
                for p in linea:
                    for q in self.points:
                        if p==q[0]:
                            aux2=aux2+q[1]
                self.deltas.append([aux2])
                
        # Sector characteristics
                
        for section in self._firdef.sections():
            if section[0:6]=='sector':
                sector_name=self._firdef.get(section,'nombre')
                self.sectors.append(sector_name)
                self._sector_sections[sector_name]=section
                self.boundaries[sector_name]=[]
                self.fijos_impresion[sector_name]=[]
                self.fijos_impresion_secundarios[sector_name]=[]
                self.local_ads[sector_name]=[]
                self.release_required_ads[sector_name]=[]
                
        # Load data for each of the sectors
        for (sector,section) in self._sector_sections.items():
        
            # L�mites del sector
            aux2=self._firdef.get(section,'limites').split(',')
            for a in aux2:
                auxi=True
                for q in self.points:
                    if a==q[0]:
                        self.boundaries[sector].append(q[1])
                        auxi=False
                if auxi:
                    incidencias.append(('En el l�mite de sector no encontrado el self.points '+a))
                    logging.debug ('En l�mite de sector no encontrado el self.points '+a)
             
             #Build TWO LOCAL MAPS: One with sectors limits, and the other with the transparency
                    # Separaci�n m�nima del sector
            if self._firdef.has_option(section,'min_sep'):
                self.min_sep[sector]=float(self._firdef.get(section,'min_sep'))
            else:
                incidencias.append(('No encontrada separaci�n en sector '+sector+'. Se asumen 8 NM de separaci�n m�nima.'))
                logging.debug ('No encontrada separaci�n en sector '+sector+'. Se asumen 8 NM de separaci�n m�nima.')
                self.min_sep[sector] = 8.0
                
            # Despegues autom�ticos o manuales
            if self._firdef.has_option(section,'auto_departure'):
                aux2=self._firdef.get(section,'auto_departure').upper()
                if aux2 == 'AUTO':
                    self.auto_departures[sector] = True
                elif aux2 == 'MANUAL':
                    self.auto_departures[sector] = False
                else:
                    incidencias.append(('Valor para despegues manual/autom�tico para sector '+sector+' debe ser "AUTO" o "MANUAL". Se asume autom�tico'))
                    logging.debug ('Valor para despegues manual/autom�tico para sector '+sector+' debe ser "AUTO" o "MANUAL". Se asume autom�tico')                    
                    self.auto_departures[sector] = True
            else:
                incidencias.append(('Valor para despegues manual/autom�tico para sector '+sector+' no encontrado. Se asume autom�tico'))
                logging.debug ('Valor para despegues manual/autom�tico para sector '+sector+' no encontrado. Se asume autom�tico')
                auto_departures[sector] = True
                
            # Fijos de impresi�n primarios
            fijos_impresion=[]
            aux2=self._firdef.get(section,'fijos_de_impresion').split(',')
            for a in aux2:
                auxi=True
                for q in self.points:
                    if a==q[0]:
                        self.fijos_impresion[sector].append(q[0])
                        auxi=False
                if auxi:
                    incidencias.append(('No encontrado fijo de impresi�n '+a))
                    logging.debug ('No encontrado el fijo de impresi�n '+a)
            logging.debug
            # Fijos de impresi�n secundarios
            if self._firdef.has_option(section,'fijos_de_impresion_secundarios'):
                aux2=self._firdef.get(section,'fijos_de_impresion_secundarios').split(',')
                for a in aux2:
                    auxi=True
                    for q in self.points:
                        if a==q[0]:
                            self.fijos_impresion_secundarios[sector].append(q[0])
                            auxi=False
                    if auxi:
                        incidencias.append(('No encontrado fijo secundario de impresi�n '+a))
                        logging.debug ('No encontrado el fijo secundario de impresi�n '+a)
            else:
                logging.debug ('No hay fijos de impresi�n secundarios (no hay problema)')
                
            # Local ADs
            try: ads=self._firdef.get(section,'local_ads').split(',')
            except: ads=[]
            self.local_ads[sector]=ads
        
            # Release required ADs
            try: ads=self._firdef.get(section,'release_required_ads').split(',')
            except: ads=[]
            self.release_required_ads[sector]=ads

        # Load the route database which correspond to this FIR
        import Exercise
        try:
            self.routedb=Exercise.load_routedb(os.path.dirname(self.file))
        except:
            logging.warning("Unable to load route database from "+os.path.dirname(self.file)+". Using blank db")
            
    def get_point_coordinates(self,point_name):
        try:
            return [p[1] for p in self.points if p[0]==point_name][0]
        except:
            pass
            login.error('No existe el punto'+point_name)
            
def load_firs(path):
    import ConfigParser
    
    firs = []
    
    # Walk each subdirectory looking for cached information. If stale,
    # recalculate statistics
    for d in os.listdir(path):
        d = os.path.join(path,d)
        mode = os.stat(d)[ST_MODE]
        if not S_ISDIR(mode) or d[-4:]==".svn": continue
        firs += load_firs(d)
    
    for f in [f for f in os.listdir(path) if f[-4:]==".fir"]:
        f = os.path.join(path,f)
        try:
            fir=FIR(f)
        except:
            logging.warning("Unable to read FIR file"+f,exc_info=True)
            continue
                
        firs.append(fir)
            
    return firs

if __name__ == "__main__":
    #FIR('/temp/radisplay/pasadas/Ruta-Convencional/Ruta-Convencional.fir')
    print [fir.file for fir in load_firs('..')]
