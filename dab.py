#! /usr/local/bin/python3
# -*- coding: utf-8-*-

"""Tilrettelegger modul for DAB og nettradio"""

# TODO: Lage grensesnitt for oppdateringer, dvs. at en GET til dette skriptet (ALT != POST) starter utspillings enhetene i oppdateringsmodus.
# Status er 0 for ikke prossesert, 1 for oppdatert info,  2 for ny, 3 for "force breaking"

import time
now = time.time()
from os import environ
from cgi import parse_qs
from sys import stdin, exc_info
from threading import Thread
from Queue import Queue
import gluonspin
import traceback

# Importer parsermoduler
import iteminfo
import digasEkstra

# Importer utspillingsmoduler
import dlsInt #DLS egen streaming
import dlsExt #DLS ekstern streamingspartner
import dlsExt_test
import winmedia #Nettradiomodul
import winmediaDr#Modul for DR enkodere
import utGluon2

verbose = False
testFil = False
traader = True #Kj¿rer hver av utspillingsmodulene i trŒder
maxVent = 55 #Maks ventetid på utspillingsmodulene
quark = "dab:mdw2"

allow = ['10.0.1.17','*'] # Egentlig karuselladressene, eller *

parsere = {
    '/gluon/body/tables/@type=iteminfo':'iteminfo.parser(dok)',
    '/gluon/objects/object/':'digasEkstra.parser(dok)',
    }

utenheter = {
    #'dls':'dls.tilDab(kanal=kanal,datatype=datatype,id=id)',
    #'dlsHiof':'dlsHiof.tilDab(kanal=kanal,datatype=datatype,id=id)',
    'dlsInt':'dlsInt.tilDab(kanal=kanal,datatype=datatype,id=id)',
    'dlsExt':'dlsExt.tilDab(kanal=kanal,datatype=datatype,id=id)',
    'dlsExt_test':'dlsExt_test.tilDab(kanal=kanal,datatype=datatype,id=id)',
    #'winmedia':'winmedia.lagMetadata(kanal=kanal,datatype=datatype,id=id)',
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

def startUtspiller(innstikk_navn=None, innstikk_type=None, parametre={}, returMeldinger=None):
    "Enhet som startes som en trŒd og som laster riktig utspillingsenhet"
    
    #Setter riktige variabler for eval funksjonen
    kanal = parametre['kanal']
    datatype = parametre['datatype']
    if 'id' in parametre:
        id = parametre['id']
    else:
        id = ''
    try:
        msg = eval(innstikk_type)
        if not msg:
            msg=''
        returMeldinger.put({'innstikk_navn':innstikk_navn, 'status':'ok','msg':msg})
    except:
        type, val, tb = exc_info()
        msg = "".join(traceback.format_exception(type, val, tb))
        returMeldinger.put({'innstikk_navn':innstikk_navn, 'status':'error','msg':msg})
    
def main(dok):
    #Hvis det ikke er noe dok her er det ønsket en oppdatering
    s=[]
    p=[]
    #Finne riktig parser til dokumentet
    if dok:
        for krav in parsere:
            iBane = gluonspin.gluonPath(krav)
            gluonspin.parseString(dok,iBane)
            if iBane.pathInXml:
                p.append(parsere[krav])
                #Todo kan vi gj¿re dette uten eval
                s.append(eval(parsere[krav]))
                #Siden vi aldri fŒr match pŒ mer en en type kan vi avbryte nŒ
                break
    else:
        #Lager proforma liste for å oppdatere alle
        s=[{'status':1,'kanal':'alle','datatype':'iteminfo'}]
    #Start utspillingstjeneste
    
    if verbose:
        print ("Start utspilling:",time.time() - now)
    #Innstikkstyper for hver av tjenestetypene i dab, dls, mot o.l.
    
    #Sjekke hva som er oppdatert
    s2 = []
    trd = []
    meldinger = Queue()
    warnings = []
    for i in s:
        if not i['status']:
            if verbose:
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
                        kwargs = {'innstikk_navn':ut, 'innstikk_type':utenheter[ut], 'parametre':i, 'returMeldinger': meldinger}
                        )
                t.setName(ut)
                t.setDaemon(1) 
                t.start()
                trd.append(t)
            else:
                s2.append(eval(utenheter[ut]))
            if verbose:
                print("UTg:",ut,time.time()-now)
        #Samle trŒdene
        nu = time.time()
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
        if verbose:
            print(n,i)
        if '.' in i:
            modul = i.split('.')[0]
            #TODO: Denne er neppe i bruk nŒ
            if 'opprensk' in dir(eval(modul)):
                #kall riktig modul, med resultatet fra parsingen
                eval(modul+'.opprensk(s[n])')
                if verbose:
                    print('VI RYDDER')
    #Vi sjekker trŒdene enda en gang og lager en sluttrapport
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
        totalMelding.append("\n%(innstikk_navn)s\n%(status)s\n%(msg)s" % melding)
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

    
def handler():
    "Modul for CGI, henter ut dok"

    print("Content-type: text/html")
    print()
    if 'CONTENT_LENGTH' in environ:
        lengde=int(environ['CONTENT_LENGTH'])
    else:
        lengde = 0
        xmldokument = ''
    if lengde > 0:
        f = stdin
        xmldokument = f.read(lengde)
    try:
        respons = main(xmldokument)
    except:
        type, val, tb = exc_info()
        msg = "".join(traceback.format_exception(type, val, tb))
        print(error("dab10",quark, melding=msg))
    else:
        #Svar til sender
        print(respons)

if (__name__=='__main__'):
        handler()
