#!/usr/bin/env python
#-*- coding:iso8859-15 -*-
from twisted.internet import reactor, tksupport
from twisted.internet.protocol import ClientCreator
from twisted.protocols.basic import NetstringReceiver
from Tix import *
from Pseudopilot import PpDisplay
from FIR import *
import pickle
import logging

class GTA_Client_Protocol(NetstringReceiver):
    
    def __init__(self):
        self.data = ''
                    
    def stringReceived(self, line):
        try:
            m=pickle.loads(line)
        except:
            print "Unable to unpickle"
            return

        if m['message']=='init':
            fir_file=m['data']['fir_file']
            sector=m['data']['sector']
            self.flights = m['data']['flights']
            fir=FIR(fir_file)
            self.display=PpDisplay(self.flights,'testing','./img/crujisim.ico',fir,sector,mode='atc')
            self.display.top_level.protocol("WM_DELETE_WINDOW",reactor.stop)
        if m['message']=='flights':
            flights = m['data']
            for (old,new) in zip(self.flights,flights):
                for name,value in new.__dict__.items():
                    old.__dict__[name]=value
            self.display.update()
        if m['message']=='time':
            t = m['data']
            self.display.update_clock(t)
        
    def connectionLost(self,reason):
        try: reactor.stop()
        except: pass

def main():
        
    def gotProtocol(p):
        print "Got protocol!"
    
    root = Tk()
    root.withdraw()
    
    c = ClientCreator(reactor, GTA_Client_Protocol)
    
    dialog = Toplevel(root)
    txt_titulo = Label (dialog, text = 'Introduzca la direcci�n IP del servidor')
    entry = Entry(dialog, width = 50, bg = 'white')
    def start_client(e=None):
        s=entry.get()
        host_port=s.split(":")
        ip=host_port[0]
        try:
            port=int(host_port[1])
        except:
            port=20123
        c.connectTCP(ip, port).addCallback(gotProtocol)
        dialog.destroy()
    but_acept = Button (dialog, text = 'Aceptar',command = start_client)
    dialog.bind('<Return>',start_client)
    dialog.bind('<KP_Enter>',start_client)
    txt_titulo.pack(side='top')
    entry.pack(side='top')
    entry.focus_set()
    but_acept.pack()
    def set_window_size():
        window_width = root.winfo_reqwidth()
        window_height = root.winfo_reqheight()
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        px = (screen_width - window_width) / 2
        py = (screen_height - window_height) / 2
        dialog.wm_geometry("+%d+%d" % (px,py))
    dialog.after_idle(set_window_size)
    dialog.wait_window()
    dialog.destroy()
    
    tksupport.install(root)
    reactor.run()
    
if __name__ == "__main__":
    main()

    