#! /usr/local/bin/python3
# -*- coding: utf-8 -*-

"""Tilrettelegger modul for DAB og nettradio"""

# TODO: Lage grensesnitt for oppdateringer, dvs. at en GET til dette skriptet (ALT != POST) starter utspillings enhetene i oppdateringsmodus.
# Status er 0 for ikke prossesert, 1 for oppdatert info,  2 for ny, 3 for "force breaking"

import time
import traceback
from os import environ
from sys import stdin, exc_info
from threading import Thread
from queue import Queue

import gluonspin

# Importer parsermoduler
import iteminfo

# Importer utspillingsmoduler
#TODO: Sjekk om denne er reell.
# import dlsInt # DLS egen streaming
import dlsExt # DLS ekstern streamingspartner
import dlsExt_test
import winmedia # Nettradiomodul
import winmediaDr # Modul for DR enkodere
import ut_gluon2

VERBOSE = False
TRAADER = True # Kjører hver av utspillingsmodulene i tråder
TIMEOUT = 15 # Maks ventetid på utspillingsmodulene
QUARK_NAME = "dab:mdw2"

utenheter = {
    #'dls':'dls.tilDab(kanal=kanal,datatype=datatype,id=id)',
    #'dlsHiof':'dlsHiof.tilDab(kanal=kanal,datatype=datatype,id=id)',
    'dlsInt':dlsInt.tilDab(kanal=kanal,datatype=datatype,id=id),
    'dlsExt':'dlsExt.tilDab(kanal=kanal,datatype=datatype,id=id)',
    'dlsExt_test':'dlsExt_test.tilDab(kanal=kanal,datatype=datatype,id=id)',
    'winmediaDr':'winmediaDr.lagMetadata(kanal=kanal,datatype=datatype,id=id)',
    'ut_gluon2':'ut_gluon2.lagMetadata(kanal=kanal,datatype=datatype,id=id)',
    }
    

def OK(QUARK_NAME, melding=""):
    if melding:
        return '<OK quark="%s">%s</OK>' % (QUARK_NAME, melding)
    else:
        return '<OK quark="%s" />' % QUARK_NAME


def error(errid, QUARK_NAME, melding=""):
    if melding:
        return """<error quark="%s">
\t<errorMessage errorType="%s"><message>%s</message></errorMessage>
</error>""" % (QUARK_NAME, errid, melding)

def startUtspiller(innstikk_navn=None, innstikk_type=None, parametre={}, retur_meldinger=None):
    "Enhet som startes som en trd og som laster riktig utspillingsenhet"
    # Setter riktige variabler for eval funksjonen
    kanal = parametre['kanal']
    datatype = parametre['datatype']
    if 'id' in parametre:
        id = parametre['id']
    else:
        id = ''
    try:
        msg = eval(innstikk_type)
        if not msg:
            msg = ''
        retur_meldinger.put({'innstikk_navn':innstikk_navn, 'status':'ok','msg':msg})
    except:
        type, val, tb = exc_info()
        msg = "".join(traceback.format_exception(type, val, tb))
        retur_meldinger.put({'innstikk_navn':innstikk_navn, 'status':'error','msg':msg})
    
def main(dok):
    # Hvis det ikke er noe dok her er det ønsket en oppdatering av utmodulene
    status_list = []
    prosess_list = []
    # Finne riktig parser til dokumentet
    if dok:
        # Alt skal til iteminfo
        status_list.append(iteminfo.parser(dok))
    else:
        # Lager proforma liste for  oppdatere alle
        status_list = [{'status':1,'kanal':'alle','datatype':'iteminfo'}]
    # Start utspillingstjeneste
    
    if VERBOSE:
        print ("Start utspilling:",time.time() - now)
    # Innstikkstyper for hver av tjenestetypene i dab, dls, mot o.l.
    
    # Sjekke hva som er oppdatert
    s2 = []
    trd = []
    meldinger = Queue()
    warnings = []
    for i in status_list:
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
            if TRAADER:
                t = Thread(target=startUtspiller,
                        kwargs = {'innstikk_navn':ut, 'innstikk_type':utenheter[ut], 'parametre':i, 'returMeldinger': meldinger}
                        )
                t.setName(ut)
                t.setDaemon(1) 
                t.start()
                trd.append(t)
            else:
                s2.append(eval(utenheter[ut]))
            if VERBOSE:
                print("UTG:",ut,time.time()-now)
        # Samle trådene
        nu = time.time()
        warnings = ['Warnings:']
        for t in trd:
            vent = TIMEOUT - (time.time() -nu)
            t.join(vent)
            if t.isAlive():
                warnings.append("%s brukte mer en %s sekunder" % (t.getName(), TIMEOUT))
    # Dersom noe trenger opprydningsrutiner legges disse inn her etter alle utspillingsmodulene
    if dok:
        #Venter bare ved dok
        time.sleep(20)
    for n,i in enumerate(p):
        if VERBOSE:
            print(n,i)
    # Vi sjekker trdene enda en gang og lager en sluttrapport
    for t in trd:
        t.join(0.1)
        if t.isAlive():
            warnings.append("%s ble tvunget ned etter %s sekunder" % (t.getName(), TIMEOUT))
    # Sjekke meldingene
    totalStatusOK = True
    totalMelding = []
    while not meldinger.empty():
        melding = meldinger.get()
        if melding['status']=='error':
            totalStatusOK = False
        totalMelding.append("\n%(innstikk_navn)s\n%(status)s\n%(msg)s" % melding)
    # Legge til Warnings
    if len(warnings)>1:
        #Vi skal legge til warningsene
        totalMelding.extend(warnings)
    if totalStatusOK:
        #Vi skal returnere OK
        return OK(QUARK_NAME, melding="\n".join(totalMelding))
    else:
        # Vi fyrer feilmelding
        return error('dab11', QUARK_NAME, melding="\n".join(totalMelding))

    
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
        print(error("dab10", QUARK_NAME, melding=msg))
    else:
        #Svar til sender
        print(respons)

if (__name__=='__main__'):
        handler()
