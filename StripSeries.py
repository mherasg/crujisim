#!/usr/bin/env python
#-*- coding:iso8859-15 -*-

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

#Constants


import warnings
warnings.filterwarnings('ignore','.*',DeprecationWarning)
import sys
sys.path.insert(0, 'strips.zip')
import strips.stringformat
from strips.colors import *
from strips.pid import Font
from strips.PDF import PDFCanvas

STRIPS_PER_PAGE = 11

STRIP_X_SIZE=560    #define el tama�o horizontal de la ficha
STRIP_Y_SIZE=70     #define el tama�o vertical de la ficha


class StripSeries:

        filename=''
    
	def __init__(self, exercise_name="", date="", output_file="strips.pdf"):
		self.canvas = PDFCanvas(size=(560,815), name=output_file)
		strips.stringformat.drawString(self.canvas, "Ejercicio:  "+str(exercise_name), 40, 40)
		self.canvas.clear()
		self.num_strips = 0
		self.filename=output_file
		
	def draw_blank_strip(self, x, y):
		canvas = self.canvas
                #Dibuja el contorno de la ficha
		canvas.drawLine(x, y, x+STRIP_X_SIZE, y, color=dimgray)
		canvas.drawLine(x, y+STRIP_Y_SIZE, x+STRIP_X_SIZE, y+STRIP_Y_SIZE, color=dimgray)
		canvas.drawLine(x, y, x, y+STRIP_Y_SIZE, color=dimgray)
		canvas.drawLine(x+STRIP_X_SIZE, y, x+STRIP_X_SIZE, y+STRIP_Y_SIZE, color=dimgray)

##		Primera linea horizontal: hacia arriba est� el indicativo
		canvas.drawLine(x+11, y+23, x+410, y+23)
##		Segunda linea horizontal: hacia abajo est� la ruta
		canvas.drawLine(x+5, y+52, x+550, y+52)
##		Seis Lineas verticales principales: hora 1 comunicaci�n,respondedor,fijo anterior,fijo,fijo siguiente,instrucciones
		canvas.drawLine(x+145, y+11, x+145, y+52)
		canvas.drawLine(x+187, y+12, x+187, y+52)
		canvas.drawLine(x+227, y+12, x+227, y+52)
		canvas.drawLine(x+286, y+12, x+286, y+52)
		canvas.drawLine(x+345, y+12, x+345, y+52)
		canvas.drawLine(x+404, y+12, x+404, y+52)
##		Linea diagonal casilla primera comunicaci�n
		canvas.drawLine(x+144, y+52, x+187, y+23)
##		Linea horizontal divisoria casilla respondedor
		canvas.drawLine(x+187, y+37, x+227, y+37)
##		Lineas verticales y diagonales para las casillas de estimada piloto/hora de paso por el fijo
		canvas.drawLine(x+257, y+23, x+257, y+52)
		canvas.drawLine(x+257, y+52, x+286, y+23)
		canvas.drawLine(x+316, y+23, x+316, y+52)
		canvas.drawLine(x+316, y+52, x+345, y+23)
		canvas.drawLine(x+375, y+23, x+375, y+52)
		canvas.drawLine(x+375, y+52, x+404, y+23)
##		Lineas Minuto de transferencia de comunicaciones		
		canvas.drawLine(x+529, y+8, x+529, y+17,width=3)
		canvas.drawLine(x+531, y+19, x+550, y+19)
	
#	def draw_callsign(canvas, x, y, callsign):
#		strips.stringformat.drawString(canvas, callsign, x+33, y+20, Font(face="monospaced", size=18, bold=1))

	def draw_flight_data(self, exercice_name="",callsign="",ciacallsign="", model="", wake="", responder="", speed="", cssr="", origin="", destination="", fl="", cfl="", route="", rules="", prev_fix="", fix="", next_fix="", prev_fix_est="", fix_est="", next_fix_est=""):
		x = 25
		y = 40 + STRIP_Y_SIZE * (self.num_strips % STRIPS_PER_PAGE)
		canvas = self.canvas
		if (self.num_strips > 0) and (self.num_strips % STRIPS_PER_PAGE) == 0:
			canvas.flush()
			canvas.clear()
		self.draw_blank_strip(x, y)
		if len(model) < 6: model = model + " "*(6-len(model))
		elif len(model) > 6: model = model[:6]
		if wake=="": wake = " "
		if responder == "": responder = " "
		if speed == "": speed = "    "
		else: speed = "%04d" % int(speed)
		if ciacallsign=="": ciacallsign = " "
		if exercice_name=="": exercice_name= " "
		strips.stringformat.drawString(canvas, callsign, x+30, y+22, Font(face="monospaced", size=20, bold=1))
		strips.stringformat.drawString(canvas, ciacallsign, x+15, y+10, Font(face="monospaced", size=8, bold=1))
		firstline = model + "/" + wake + "/" + responder + "/" + speed
		strips.stringformat.drawString(canvas, firstline, x+16, y+35, Font(face="monospaced", size=9, bold=1))
		secondline = origin + "      "+destination+"/"+fl
		strips.stringformat.drawString(canvas, secondline, x+16, y+49, Font(face="monospaced", size=10, bold=1))
		strips.stringformat.drawString(canvas, cssr, x+190, y+50, Font(face="monospaced", size=8, bold=1))
		strips.stringformat.drawString(canvas, route, x+16, y+61, Font(face="monospaced", size=10, bold=1))
		strips.stringformat.drawString(canvas, rules, x+200, y+22, Font(face="monospaced", size=10, bold=1))

		strips.stringformat.drawString(canvas, prev_fix, x+240, y+22, Font(face="monospaced", size=10, bold=1))
		strips.stringformat.drawString(canvas, prev_fix_est, x+230, y+35, Font(face="monospaced", size=9, bold=1))
		
		strips.stringformat.drawString(canvas, fix, x+300, y+22, Font(face="monospaced", size=12, bold=1))
		strips.stringformat.drawString(canvas, fix_est, x+286, y+50, Font(face="monospaced", size=12, bold=1))
		
		strips.stringformat.drawString(canvas, next_fix, x+358, y+22, Font(face="monospaced", size=10, bold=1))
		strips.stringformat.drawString(canvas, next_fix_est, x+348, y+35, Font(face="monospaced", size=9, bold=1))
                
                strips.stringformat.drawString(canvas,cfl,x+405,y+22, Font(face="monospaced", size=12, bold=1))
                strips.stringformat.drawString(canvas,exercice_name,x+5,y+68, Font(face="monospaced", size=6, bold=0))
		self.num_strips += 1

	def save(self):
                #We try to open the file for writing and throw an exception if unable
                try:
                    f=open(self.filename,'wb')
                    f.close()
                    self.canvas.save()
                    return True
                except:
                    print 'Failed printing flight strips. Unable to open '+self.filename+' for writing'
                    return False

