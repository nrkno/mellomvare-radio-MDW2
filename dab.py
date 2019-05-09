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
import dls_ext # DLS ekstern streamingspartner
#import dlsExt_test # Vi venter med denne, det er bare utsendelses adressen som er annerledes.
#import winmedia # Nettradiomodul
#import winmediaDr # Modul for DR enkodere
import ut_gluon2

VERBOSE = environ['VERBOSE']
TRAADER = True # Kjører hver av utspillingsmodulene i tråder
TIMEOUT = 15 # Maks ventetid på utspillingsmodulene
QUARK_NAME = "dab:mdw2"

utenheter = {
    'dls_ext':dls_ext.lag_metadata,
    #'dlsExt_test':dlsExt_test.tilDab(kanal=kanal, datatype=datatype, id=id),
    #'winmediaDr':winmediaDr.lagMetadata(kanal=kanal,datatype=datatype, id=id),
    'ut_gluon2':ut_gluon2.lag_metadata,
    }

def OK(quarq, melding=""):
    if melding:
        return '<OK quark="%s">%s</OK>' % (quarq, melding)
    else:
        return '<OK quark="%s" />' % quarq

def error(errid, quarq, melding=""):
    if melding:
        return """<error quark="%s">
\t<errorMessage errorType="%s"><message>%s</message></errorMessage>
</error>""" % (quarq, errid, melding)

def start_utspiller(innstikk_navn=None, innstikk_funksjon=None, kanal='alle', retur_meldinger=None):
    "Enhet som startes som en trd og som laster riktig utspillingsenhet"
    try:
        msg = innstikk_funksjon(kanal=kanal)
        if not msg:
            msg = ''
        retur_meldinger.put({'innstikk_navn':innstikk_navn, 'status':'ok', 'msg':msg})
    except:
        type, val, tb = exc_info()
        msg = "".join(traceback.format_exception(type, val, tb))
        retur_meldinger.put({'innstikk_navn':innstikk_navn, 'status':'error', 'msg':msg})

def main(dok):
    # Hvis det ikke er noe dok her er det ønsket en oppdatering av utmodulene
    prosess_list = []
    # Finne riktig parser til dokumentet
    if dok:
        # Alt skal til iteminfo
        status = iteminfo.parser(dok)
    else:
        # Lager en kommando som oppdaterer alle
        status = {'status':1, 'kanal':'alle'}
    # Start utspillingstjeneste

    # Sjekke hva som er oppdatert
    s2 = []
    trd = []
    meldinger = Queue()
    warnings = []

    if status['status'] == 0:
        if VERBOSE:
            print("IGNORERES")
    else:
        # TODO: fortsett her
        kanal = status['kanal']
        print('Kanal: ', kanal)
        print(utenheter)
        for ut in utenheter:
            t = Thread(target=start_utspiller,
                    kwargs = {'innstikk_navn':ut, 'innstikk_funksjon':utenheter[ut], 'kanal':status['kanal'], 'retur_meldinger': meldinger}
                    )
            t.setName(ut)
            t.setDaemon(1)
            t.start()
            trd.append(t)

        # Samle trådene
        nu = time.time()
        warnings = ['Warnings:']
        for t in trd:
            vent = TIMEOUT - (time.time() - nu)
            t.join(vent)
            if t.isAlive():
                warnings.append("%s brukte mer en %s sekunder" % (t.getName(), TIMEOUT))
    # Dersom noe trenger opprydningsrutiner legges disse inn her etter alle utspillingsmodulene
    if dok:
        #Venter bare ved dok
        time.sleep(10)

    # Vi sjekker trdene enda en gang og lager en sluttrapport
    for t in trd:
        t.join(0.1)
        if t.isAlive():
            warnings.append("%s ble tvunget ned etter %s sekunder" % (t.getName(), TIMEOUT))
    # Sjekke meldingene
    totalStatus_ok = True
    totalMelding = []
    while not meldinger.empty():
        melding = meldinger.get()
        if melding['status'] == 'error':
            totalStatus_ok = False
        totalMelding.append("\n%(innstikk_navn)s\n%(status)s\n%(msg)s" % melding)
    # Legge til Warnings
    if len(warnings)>1:
        #Vi skal legge til warningsene
        totalMelding.extend(warnings)
    if totalStatus_ok:
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

if __name__ == '__main__':
    handler()
