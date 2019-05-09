# -*- coding: utf-8 -*-

"Hjelpemodul for å sende ting inn i dab systemet"

import time
import socket

TESTLISTE = {'multiplex':'Nasjonal',
             'kanal':'p9',
             'listetype':'1',
             'start':'12.03.03 12:43:05',
             'stopp':'12.03.03 17:43:05',
             'varighet':'10',
             'tekster':['et felt', 'felt to']
             }

class FileUploadRequestException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

def isodato(ticks, time_format='datetime'):
    "Lager dato for bruk mot DLS og lignende for icecast"
    year, month, day, hour, minute, second = time.localtime(ticks)[:6]
    if time_format == 'datetime':
        return "%04d-%02d-%02dT%02d:%02d:%02d" % (year, month, day, hour, minute, second)
    if time_format == 'date':
        return "%02d.%02d.%02d" % (day, month, year % 100)
    return "%02d:%02d:%02d" % (hour, minute, second)

def send_data(uri, kanal='kanal', blokk='blokk', start=None, stop=None, liste=None):
    """Sender en liste av data"""
    if liste is None:
        liste = []
    # Vi lager listen
    xml_liste = ''
    for rad in liste:
        xml_liste += '  <rad data="%s" visningstid="%s" />\n' % rad
    # FIXME: Her må vi ha utf-8
    #Så lager vi XML dataene
    xml_mal = """<?xml version="1.0" encoding="iso-8859-1"?>
<dls kanal="%s" blokk="%s" start="%s" stop="%s">
%s</dls>
    """

    data = xml_mal % (
        kanal,
        blokk,
        start,
        stop,
        xml_liste
        )
        
    print(7878778, data)
    """
    # Dele opp uri til hostname og url
    host, port = uri.split(':', 1)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect((host, int(port)))
    s.send(data)
    s.close()
    """
