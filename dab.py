#! /opt/local/bin/python3
# -*- coding: utf-8 -*-
"""Tilrettelegger for metadata - """

#TODO:

# Status er 0 for ikke prossesert, 1 for oppdatert info,  2 for ny, 3 for "force breaking"?

import time
now = time.time()
from os import environ
from cgi import parse_qs
from sys import stdin, exc_info
from threading import Thread
from queue import Queue
#import gluonspin
import traceback
from os import environ as env

# Importer parsermoduler
import iteminfo
import digasEkstra
import epg



# Importer utspillingsmoduler
#import dls
import dlsInt #DLS egen streaming
import dlsExt #DLS ekstern streamingspartner
import dlsExt_test
import winmedia #Nettradiomodul
import webplugin #Modul for blaa bokser
import webplugin2 #Modul for blaa bokser
import winmediaDr#Modul for DR enkodere
import utGluon2


VERBOSE = env['VERBOSE']
TESTFIL = False
traader = True # Kj/oslash/rer hver av utspillingsmodulene i tr/aring/der
maxVent = 55 # Timeout tid p/aring/ tr/aring/dene
quark = "dab:ny"

#print "Importtid:",time.time()-now

allow = ['10.0.1.17','*'] # Egentlig karuselladressene, eller *

parsere = {
            '/gluon/body/tables/@type=iteminfo':'iteminfo.parser(dok)',
            '/gluon/objects/object/':'digasEkstra.parser(dok)',
            '/gluon/body/tables/@type=epg':'epg.parser(dok)',
            '/gluon/body/tables/@type=newswire':'news.newswire(dok)',
            }

utenheter = {
    'dlsInt':'dlsInt.tilDab(kanal=kanal,datatype=datatype,id=id)',
    'dlsExt':'dlsExt.tilDab(kanal=kanal,datatype=datatype,id=id)',
    'dlsExt_test':'dlsExt_test.tilDab(kanal=kanal,datatype=datatype,id=id)',
    'winmediaDr':'winmediaDr.lagMetadata(kanal=kanal,datatype=datatype,id=id)',
    'utGluon2':'utGluon2.lagMetadata(kanal=kanal,datatype=datatype,id=id)',
    }


def OK(quark, melding=""):
    if melding:
        return '<OK quark="%s">%s</OK>' % (quark,melding)
    else:
        return '<OK quark="%s" />' % quark

def error(errid,quark, melding=""):
    if melding:
        return """<error quark="%s">
\t<errorMessage errorType="%s"><message>%s</message></errorMessage>
</error>""" % (quark,errid,melding)

def start_utspiller(innstikkNavn=None, innstikkType=None, parametre = {}, returMeldinger = None):
    "Enhet som startes som en tr/aring/d og som laster riktig utspillingsenhet"
    
    #Setter riktige variabler for eval funksjonen
    kanal = parametre['kanal']
    datatype = parametre['datatype']
    if 'id' in parametre:
        id = parametre['id']
    else:
        id = ''
    try:
        msg = eval(innstikkType)
        if not msg:
            msg=''
        returMeldinger.put({'innstikkNavn':innstikkNavn, 'status':'ok','msg':msg})
    except:
        type, val, tb = exc_info()
        msg = "".join(traceback.format_exception(type, val, tb))
        returMeldinger.put({'innstikkNavn':innstikkNavn, 'status':'error','msg':msg})
    
def main(dok):
    #Hvis det ikke er noe dok her er det ¯nsket en oppdatering
    s=[]
    p=[]
    #Finne riktig parser til dokumentet
    if dok:
        for krav in parsere:
            iBane = gluonspin.gluonPath(krav)
            gluonspin.parseString(dok,iBane)
            if iBane.pathInXml:
                p.append(parsere[krav])
                s.append(eval(parsere[krav]))
                # Siden vi aldri f/aring/r match p/aring/ mer en en type kan vi avbryte n/aring/
                break

    else:
        # Lager proforma liste for /aring/ oppdatere alle
        s=[{'status':1,'kanal':'alle','datatype':'iteminfo'}]
    # Start utspillingstjeneste
    
    if VERBOSE:
        print ("Start utspilling:", time.time()-now)
    # Innstikkstyper for hver av tjenestetypene i dab, dls, mot o.l.
    
    # Sjekke hva som er oppdatert
    s2 = []
    trd = []
    meldinger = Queue()
    warnings = []
    for i in s:
        if not i['status']:
            if VERBOSE:
                print("IGNORERES")
            continue
        kanal=i['kanal']
        datatype =i['datatype']
        if 'id' in i:
            id = i['id']
        else:
            id = ''
        
        
        for ut in utenheter:
            if traader:
                t = Thread(target=startUtspiller,
                        kwargs = {'innstikkNavn':ut, 'innstikkType':utenheter[ut], 'parametre':i, 'returMeldinger': meldinger}
                        )
                t.setName(ut)
                t.setDaemon(1) 
                t.start()
                trd.append(t)
            else:
                s2.append(eval(utenheter[ut]))
                
            if VERBOSE:
                print("Utg:", ut, time.time()-now)
        #Samle tr/aring/dene
        nu=time.time()
        warnings = ['Warnings:']
        for t in trd:
            vent = maxVent - (time.time() -nu)
            t.join(vent)
            if t.isAlive():
                warnings.append("%s brukte mer en %s sekunder" % (t.getName(), maxVent))
            
    
    #Dersom noe trenger opprydningsrutiner legges disse inn her etter alle utspillingsmodulene
    if dok:
        #Venter bare ved dok
        time.sleep(20)
    for n,i in enumerate(p):
        if VERBOSE:
            print(n,i)
        if '.' in i:
            modul = i.split('.')[0]
            if 'opprensk' in dir(eval(modul)):
                #kall riktig modul, med resultatet fra parsingen
                eval(modul+'.opprensk(s[n])')
                if VERBOSE:
                    print('VI RYDDER')
    #Vi sjekker trÂdene enda en gang og lager en sluttrapport
    for t in trd:
        t.join(0.1)
        if t.isAlive():
            warnings.append("%s ble tvunget ned etter %s sekunder" % (t.getName(), maxVent))
    #Sjekke meldingene
    totalStatusOK = True
    totalMelding = []
    while not meldinger.empty():
        melding = meldinger.get()
        if melding['status']=='error':
            totalStatusOK = False
        totalMelding.append("\n%(innstikkNavn)s\n%(status)s\n%(msg)s" % melding)
    #Legge til Warnings
    if len(warnings)>1:
        #Vi skal legge til warningsene
        totalMelding.extend(warnings)
    if totalStatusOK:
        #Vi skal returnere OK
        return OK(quark,melding="\n".join(totalMelding))
    else:
        #Vi fyrer feilmelding
        return error('dab11',quark,melding="\n".join(totalMelding))

if (__name__=='__main__'):
        # CGI
                
        print("Content-type: text/html")
        print()

        if 'HTTP_PC_REMOTE_ADDR' in environ:
            fra = environ['HTTP_PC_REMOTE_ADDR']
        elif 'REMOTE_ADDR' in environ:
            fra = environ['REMOTE_ADDR']
        else:
            fra = ''	
        # Sjekke for gyldige adresser
        if not ('*' in allow or fra in allow):
            # dette er en feil
            print("Uautorisert tilgang!!!")
        else:
        
            try:
                    lengde=int(environ['CONTENT_LENGTH'])
            except:

                    lengde = 0
                    xmldokument = ''
                    if testFil:
                        f=open("item.xml")
                        
                        xmldokument = ''
                        while 1:
                            try:
                                    blokk = f.read(8024)
                                    if blokk:
                                            xmldokument += blokk
                                    else:
                                            break
                            except:
                                    break
                        if len(xmldokument)<lengde:
                            print("Fikk ikke lest hele dokumentet")
                        f.close()
                    # Dette maa vaere hovedmeldingen til klienter i systemet.
            if lengde > 0:
                    
                    f = stdin
                    xmldokument = f.read(lengde)
                    if xmldokument[:6]!='<?xml version='[:6]:
                            xmldokument = parse_qs(xmldokument)['dok'][0] #['dok'] ender i en liste....
                            # M/aring/ endre lengden ogs/aring/ da
                            lengde = len(xmldokument)  
            try:				
                alfa = main(xmldokument)
        
            except:
                type, val, tb = exc_info()
                msg = "".join(traceback.format_exception(type, val, tb))
                print(error("dab10",quark, melding=msg))
    
    

            else:
                # Alfa kan enten v/aelig/re en OK eller en feilmelding som er h/aring/ndtert av systemet
                
                print(alfa)

    
