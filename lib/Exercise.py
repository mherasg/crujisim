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
"""Classes useful for dealing with Exercise files"""

import logging
import os
from stat import *
import cPickle
import zlib
from ConfigParser import ConfigParser

# CONSTANTS
CACHE_VERSION = 6
MAPPING_FILE_NAME = "exercises-passes.dat"

def load_exercises(path, reload=False):
    
    exercises = []
    
    # Walk each subdirectory looking for cached information. If stale,
    # recalculate statistics
    for d in os.listdir(path):
        d = os.path.join(path,d)
        mode = os.stat(d)[ST_MODE]
        if not S_ISDIR(mode) or d[-4:]==".svn": continue
        exercises += load_exercises(d,reload)

    # Find the date of the oldest .eje file in the directory
    d = path
    logging.debug("Searching for exercises in directory "+str(d))
    recent = 0
    for f in os.listdir(d):
        if f[-4:]!=".eje" and f!=MAPPING_FILE_NAME: continue
        date = os.stat(os.path.join(d,f))[ST_MTIME]
        if date>recent:
            recent=date

    # Find whether a cache file exists or if it's older than the most recent exercise
    cache = os.path.join(d,".cache")
    if not reload and os.access(cache,os.F_OK|os.R_OK) and os.stat(cache)[ST_MTIME]>recent:
        try:
            c = open(cache,"rb")
            version,le = cPickle.loads(zlib.decompress(c.read()))
            if version==CACHE_VERSION:
                exercises += le
                return exercises
            else:
                logging.info("Cache file "+cache+" is version "+str(version)+", different than currently supported version "+str(CACHE_VERSION))
        except:
            logging.warning("Unable to load cache file: "+cache)
    else:
        logging.info("Cache file "+cache+" not found, not readable or stale")

    # Load data for all excercises in the directory
    logging.info("Rebuilding cache file...")
    le = []  #
    
    # Load the mapping file for the directory in case it exists
    mapping = Mapping(os.path.join(d,MAPPING_FILE_NAME))
    
    for f in [f for f in os.listdir(d) if f[-4:]==".eje"]:
        f = os.path.join(d,f)
        try:
            e=Exercise(f)
        except:
            logging.warning("Unable to read exercise "+f)
            continue
        
        # If we have DA,U,E data, then we can use the mapping file
        # to add all the actual passes implemented by this exercise
        try:
            for (course,phase,day,pass_no) in mapping.exercises[(e.da,e.usu,e.ejer)]:
                ne=e.copy()
                del(ne.file)  # The copy is not based on any file
                ne.course,ne.phase,ne.day,ne.pass_no=course,phase,day,pass_no
                del(ne.flights)
                le.append(ne)
            if (e.course,e.phase,e.day,e.pass_no) not in mapping.exercises[(e.da,e.usu,e.ejer)]:
                logging.error("The exercise reported to be C-P-D-P "+str((e.course,e.phase,e.day,e.pass_no))+\
                              " but it's not shown on the mappings for DA-U-E "+str((e.da,e.usu,e.ejer)))
        except:
            # Since we didn't find mappings, we use the exercises own.
            del(e.flights)
            le.append(e)
        
    exercises += le
    cache = open(cache,'wb')  # Cache used to be the file name, now the file object
    cache.write(zlib.compress(cPickle.dumps((CACHE_VERSION,le))))
    cache.close
            
    return exercises    
    
class Exercise:
    """All data representing a single exercise"""
    def __init__(self,file=None):
        if file: self.load(file)
        
    def load(self,file):
        import re

        self.file=file
        exc = ConfigParser()
        exc.readfp(open(file,"r"))
        self.fir=exc.get('datos','fir')
        self.sector=exc.get('datos','sector')
        self.start_time=exc.get('datos','hora_inicio')
        try: self.da = exc.getint('datos','da')
        except: self.da = None
        try: self.usu = exc.getint('datos','usu')
        except: self.usu = None
        try: self.ejer = exc.getint('datos','ejer')
        except: self.ejer = None
        try: self.course = exc.getint('datos','course')
        except: self.course = None
        try: self.phase = exc.getint('datos','phase')
        except: self.phase = None
        try: self.day = exc.getint('datos','day')
        except: self.day = None
        try: self.pass_no = exc.getint('datos','pass_no')
        except: self.pass_no = None
        try: self.shift = exc.get('datos','shift')
        except: self.shift = ""
        try: (self.wind_azimuth,self.wind_knots) = [int(x) for x in exc.get('datos','viento').split(",")]
        except: self.wind_azimuth,self.wind_knots=0,0
        
        # The old comment format was in fact used to present exercises
        # in the old MainMenu.py, so we need to maintain it
        # It actually has more information than a real comment
        try: self.oldcomment = exc.get('datos','comentario')
        except: self.oldcomment = os.path.basename(file)
        # If the file doesn't have an actual new comment attr yet, use the old one.
        try: self.comment = exc.get('datos','comment')
        except: self.comment = self.oldcomment
        
        flightops = ()
        try:
            self.n_flights = len(exc.options('vuelos'))        
            flightopts = exc.options('vuelos')
        except:
            logging.warning("Unable to read any flights from "+file)
        self.flights={}
        i=0
        for flightopt in flightopts:
            try:
                self.flights[i]=Flight(flightopt,exc.get('vuelos',flightopt))
                i += 1
            except:
                logging.warning("Unable to read flight "+flightopt+" from "+file)
        
        # Attempt to calculate course,phase,day,pass_no,and shift
        if self.course==self.phase==self.day==self.pass_no==None and self.shift=="":
            formats = []
            file = os.path.basename(file)
            # fr=format regular expression, fm=format mapping
            fr = "(\d+)-Fase-(\d+)-D.a-(\d+)-Pasada-(\d+)-([mtMT])-(.*).eje"
            fm = {"course":1,"phase":2,"day":3,"pass_no":4,"shift":5}
            formats.append((fr,fm))
            fr = "(\d+)-Fase-(\d+)-D.a-(\d+)-([mtMT])-([^-]+)-(\d+).eje"
            fm = {"course":1,"phase":2,"day":3,"shift":4,"pass_no":6}
            formats.append((fr,fm))
            #20-Fase-3-D�a-04-M-Domingo-4-2055h.ej
            fr = "(\d+)-Fase-(\d+)-D.a-(\d+)-([mtMT])-([^-]+)-(\d+)-(\d+)h.*.eje"
            fm = {"course":1,"phase":2,"day":3,"shift":4,"pass_no":6}
            formats.append((fr,fm))
            for r,m in formats:
                match=re.match(r,file)
                try:
                    for attrib,index in m.items():
                        if attrib in ["course","phase","day","pass_no"]:
                            self.__dict__[attrib]=int(match.group(index))
                        elif attrib in ["shift"]:
                            self.__dict__[attrib]=match.group(index).upper()
                except:
                    continue

        # Attempt to extract only the useful comment:
        # Attempt to calculate course,phase,day,pass_no,and shift
        formats = []
        comment = self.comment
        #20-Fase-1-D�a-02-T-Toledo-1-1020h(29)
        fr = "\d+-Fase-\d+-D.a-\d+-[mtMT]-[^-]+-\d+-\d+h(.*?)(\(.*\))*$"
        fm = {"comment":1}
        formats.append((fr,fm))
        #20-Fase-1-D�a-02-T-Toledo-1(29
        fr = "\d+-Fase-\d+-D.a-\d+-[mtMT]-[^-]+-\d+(.*?)(\(.*\))*$"
        fm = {"comment":1}
        formats.append((fr,fm))
        #23-Fase-2-Dia-3-Pasada-2-M DA33U1E42(29)
        fr = "\d+-Fase-\d+-D.a-\d+-Pasada-\d+-[mtMT] *DA(\d+)US*U*(\d+)EJ*E*(\d+)(.*)\(.*\)"
        fm = {"da":1,"usu":2,"ejer":3,"comment":4}
        formats.append((fr,fm))
        #23-Fase-2-Dia-3-Pasada-2-M (29)
        fr = "\d+ *- *Fase[- ]\d+ *- *D.a[- ]\d+ *- *Pasada[- ]\d+ *- *[mtMT](.*?)(\(.*\))*$"
        fm = {"comment":1}
        formats.append((fr,fm))
        #22 - Fase 1 - Dia 7 - T -Pasada 4(30)
        fr = "\d+ *- *Fase[- ]\d+ *- *D.a[- ]\d+ *- *[mtMT] *- *Pasada[- ]\d+(.*?)(\(.*\))*$"
        fm = {"comment":1}
        formats.append((fr,fm))
        for r,m in formats:
            match=re.match(r,comment)
            try:
                for attrib,index in m.items():
                    if attrib in ("da","usu","eje") and self.__dict__[attrib]!=None:
                        self.__dict__[attrib]=int(match.group(index))
                    else:
                        self.__dict__[attrib]=match.group(index).strip()
                break
            except:
                continue
            
    def copy(self):
        e = Exercise()
        e.__dict__=self.__dict__.copy()
        return e

class Flight:
    """All data related to a specific flight within an Exercise"""
    def __init__(self, callsign=None, data=None):
        """Construct a flight instance
        
        Instantiation arguments:
        callsign -- Flight code (eg: IBE231)
        data -- The flight data as is on the Exercise file
        """
        
        if callsign and data:
            self.callsign=callsign.upper()
            self._data=data
            self.orig=self.orig()
            self.dest=self.dest()
            self.route=self.route()
            self.fix,self.eto,self.firstlevel,self.tas = self.fix_eto_firstlevel_tas()
            self.wtc=self.wtc()
            self.rfl=self.rfl()
            self.cfl=self.cfl()
            self.type=self.type()
        else:
            self.callsign=""
            self.orig=""
            self.dest=""
            self.route=""
            self.fix=""
            self.eto=""
            self.wtc=""
            self.tas=""
            self.rfl=""
            self.firstlevel=""
            self.cfl=""
            self.type=""
        
    def orig(self):
        """Return the departing aerodrome"""
        data=self._data.split(',')
        return data[2]
        
    def dest(self):
        """Return the destination aerodrome"""
        data=self._data.split(',')
        return data[3]
        
    def route(self):
        """Return a list of route points"""
        data=self._data.split(',')
        route = ''
        for fix in data[6:]:
            if len(fix)<7:
                route = route + fix.upper() + ','
        route = route[:-1]
        return route

    def fix_eto_firstlevel_tas(self):
        """Return the fix for which the eto is valid"""
        data=self._data.split(',')
        route=data[6:]
        for fix,i in zip(route,range(len(route)-1)):
            if len(route[i+1])==15:
                break
        s = route[i+1]
        eto = s[1:7]
        firstlevel = s[8:11]
        tas = s[12:]
        
        return fix,eto,firstlevel,tas
        
    def wtc(self):
        """Return the wake turbulence cat"""
        data=self._data.split(',')
        return data[1]
        
    def rfl(self):
        """Return the RFL"""
        data=self._data.split(',')
        return data[4]
        
    def cfl(self):
        """Return the CFL"""
        data=self._data.split(',')
        return data[5]
        
    def type(self):
        """Return the type"""
        data=self._data.split(',')
        return data[0]

class Mapping:
    """Deals with the relationship between the unique exercises and on which day they were scheduled"""
    def __init__(self,mapping_file,exercise_file=None):
        mapping = ConfigParser()
        #dir=os.path.dirname(exercise_file)
        #f=self.mapping_file=os.path.join(dir,)
        f=mapping_file
        try:
            mapping.readfp(open(f))
        except:
            logging.info("Mapping file "+f+" does not exist")
        self.exercises={}
        try:
            for opt in mapping.options('Mappings'):
                try:
                    (da,u,e)=(int(opt[2:4]),int(opt[5:7]),int(opt[8:11]))
                    self.exercises[(da,u,e)]=[]
                    for s in mapping.get('Mappings',opt).split(","):                        
                        (course,phase,day,pass_no)=(int(s[1:3]),int(s[4:5]),int(s[6:8]),int(s[9:10]))
                        self.exercises[(da,u,e)].append((course,phase,day,pass_no))
                except:
                    logging.warning("Unable to read mapping for excercise "+opt+" in "+f)
        except:
            logging.warning("Section Mappings not found in mapping file "+f)
            
        

def hhmmss_to_hhmm(s):
    """Given a string formated as hhmmss return a string formated to hhmm correctly rounded"""
    import datetime
    dt=datetime.datetime.today()    
    dt=dt.replace(hour=int(s[0:2]),minute=int(s[2:4]),second=int(s[4:]))
    dt+=datetime.timedelta(seconds=30)
    return dt.strftime("%H%M")

if __name__=='__main__':
    #Exercise("../pasadas\APP-RadarBasico\21-phase-1-D�a-01-M-TMA Madrid-1.eje"
    logging.getLogger('').setLevel(logging.DEBUG)
    e=load_exercises("../pasadas/Ruta-FIRMadrid", reload=True)
    #print str(e)
    
    
    