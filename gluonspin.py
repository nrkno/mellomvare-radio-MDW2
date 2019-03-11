# -*- coding: utf-8 -*-

"""Støttemoduler for gluonspin"""

import xml.sax
from xml.sax import parseString
#from threading import Lock, Thread
#from urllib import urlencode
#from httplib import HTTPConnection

utverdier = {}
threads = []

class gluonspinError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class gluonTransmitters(xml.sax.handler.ContentHandler):
    """Henter ut transmitterne, og navnet på avsendersystemet."""
    def __init__(self):
        self.inTransmitters = None
        self.transmitters = []
        self.artID = None
        self.inHead = None
        self.inCreator = None
        self.Creator = None
        self.gotCreator = None

    def startElement (self,name, attrs ):

        if name=='gluon':
            self.artID = attrs['artID']
        elif name == 'head':
            self.inHead = 1
        elif name == 'creator':
            self.inCreator = 1
        elif name == 'transmitters' and self.inHead:
            self.inTransmitters = 1
        elif self.inHead and self.inCreator and not self.gotCreator:
            #Vi er inne i creator taget i head
            #Kan inneholde taget navn (gammel type) eller family_name (ny)
            if name == 'name' or name == 'family_name':
                self.Creator = "SET"
        if self.inTransmitters and name!="transmitters":
            #Dette er en transmitter som skal på listen
            if name == 'transmitter':
                #Dette er av den generelle transmittertypen
                #Verdien av quark attributet er det vi er ute etter her
                self.transmitters.append(attrs['quark'])
            else:
                #Dette er en vanlig transmitter det holder å legge til navnet
                self.transmitters.append(name)



    def endElement (self,name ):
        if name == 'transmitters':
            self.inTransmitters = None
        elif name == 'head':
            self.inHead = None
        elif name == 'creator':
            self.inCreator = None

    def characters (self,content ):
        if self.Creator == "SET":
            self.Creator = content
            #Siden vi bare skal ha den 1. creatoren...
            self.gotCreator = 1

class gluonPath(xml.sax.handler.ContentHandler):

    def __init__(self,path):
        if '=' in path:
            path,self.value = path.split('=')
        else:
            self.value = None
        #Fjerne / i begge ender
        path = path.rstrip('/').lstrip('/')
        self.path = path.split('/')

        if path == '*':
            self.pathInXml = 1
            self.finis = 1
        else:
            self.pathInXml = 0
            self.finis = None
        self.spool = None
        self.parent = None

    def startElement (self,name, attrs):
        if not self.finis or self.pathInXml:
            if self.path and not self.spool:
                if name==self.path[0]: #Her har vi et treff
                    self.parent = self.path.pop(0)
                    #Avslutter dersom dette kommer i endelement, samtidig som dette fjerner elementet fra pathlisten
                    if not self.path:
                        #Det er ikke flere krav i path, vi har en match
                        self.pathInXml = 1
                    else:
                        #Sjekke om dette er et attribut
                        if self.path[0][0]=='@':
                            #Dette er en attrribut, sjekk om den er sann
                            if attrs.has_key(self.path[0][1:]):
                                #Attributet er tilstede
                                if self.value:
                                    #Sjekk om verdien er OK
                                    if attrs[self.path[0][1:]]==self.value:
                                        #Alt stemmer
                                        self.pathInXml = 1
                                        self.finis = 1
                                else:
                                    self.pathInXml = 1
                else:
                    self.spool = name #spoler til dette taget er slutt


    def endElement (self,name ):
        if self.parent == name:
            self.finis = 1
        if self.spool == name:
            self.spool = None

    def characters (self,content ):
        if not self.finis and self.pathInXml:
            if self.value:
                #Man skal sjekke om dette stemmer
                if self.value != content:
                    #Dette er ikke en match alikevel
                    self.pathInXml = 0
            self.finis = 1



def parseDok(xmlstreng,fra,stopp = [], data_enc = None):
    #Dette er også prosedyren som setter i gang de forskjellige tråene
    s = []
    transmitterMode = 0
    oppquark = None
    #Sjekke om det er noen transmittertag, samt hente ut creator og artID:
    adresser = gluonTransmitters()
    try:
        parseString(xmlstreng, adresser)
    except xml.sax._exceptions.SAXParseException:
        #Dokumentet lar seg ikke parse
        s.extend(["""\t\t\t<error quark="%s">
        \t\t\t\t<errorMessage errorType="gl10"><message>%s sendte inn et dokument som ikke lot seg parse</message></errorMessage>
        \t\t\t</error>\n""" % (fra,fra)])
        return s,'0',fra #Artid settes til 0


    #hente gluon iden
    artID = adresser.artID
    oppquark = adresser.Creator

    #Sjekk for om fra er registrert
    if not transmittere.has_key(fra):
        #Kun IP adresse er ikke registrert:
        #Vi forsøker med ip:quark
        fra = "%s:%s" % (fra,oppquark)
        print(fra)
        if not transmittere.has_key(fra):
            s.extend(["""\t\t\t<error quark="%s">
\t\t\t\t<errorMessage errorType="gl13"><message>%s var ikke registrert</message></errorMessage>
\t\t\t</error>\n""" % (fra,fra)])
            return s,artID,fra

    #Dersom den ikke bryter her er enheten registrert.

    #Hente eventuelle transmittere. de skal normalt ikke være der.
    transmitters = adresser.transmitters
    # Dette er resend og testmodus

    for transmitter in transmitters:
        transmitterMode = 1
        if  transmitter in stopp:
            s.extend(["""\t\t\t<error quark="%s">
\t\t\t\t<errorMessage errorType="gl11"><message>%s var i testmodus</message></errorMessage>
\t\t\t</error>\n""" % ( transmitter, transmitter)])
            continue
        #Sjekke om den gitte transmitteren har et T flagg for senderen
        if sjekkForT(transmittere[fra],transmitter)==0:
            s.extend(["""\t\t\t<error quark="%s">
\t\t\t\t<errorMessage errorType="gl15"><message>%s var ikke i transmittermodus</message></errorMessage>
\t\t\t</error>\n""" % ( transmitter, transmitter)])
            continue

        try:
            url = system[transmitter][0]
            #Finne riktig enkoding:
            if system[transmitter][1]=='raw':
                argumenter = {'data_raw':xmlstreng,'tag':transmitter}
            elif system[transmitter][1]=='urlesc':
                if not data_enc:
                    #Lage en url- encodet versjon av xml dokumentet
                    data = {'dok':xmlstreng}
                    data_enc = urlencode(data)
                argumenter = {'data_enc':data_enc,'tag':transmitter}

            t = Thread(target=sendData,
                        args=(url,),
                        kwargs=argumenter)

            t.setDaemon(1)
            #Dette gjør at vi kan tvinge ned en forbindelse som henger.
            t.start()
            threads.extend([t])
        except:
            s.extend(["""\t\t\t<error quark="%s">
\t\t\t\t<errorMessage  errorType="gl12"><message>Kunne ikke sende til: %s</message></errorMessage>
\t\t\t</error>\n""" % ( transmitter, transmitter)])
            continue

    if not transmitterMode:
        #Vanlig modus, det var ingen transmittertags

        for transmitter in transmittere[fra]:
            #Vi må parse dersom vi ikke har artID, eller dersom krav != *
            #************* Nytt
            if transmitter['krav']=='*':
                skalSende = 1
            elif transmitter['krav'].lower()=='t':
                skalSende = 0
            else:
                iBane = gluonPath(transmitter['krav'])
                parseString(xmlstreng,iBane)
                skalSende = iBane.pathInXml

            #************ Nytt slutt
            if skalSende:
                #Dette sender moroa videre
                tag = transmitter['quark']
                try:
                    url = system[tag][0]
                except KeyError:
                    s.extend(["""\t\t\t<error quark="%s">
\t\t\t\t<errorMessage dataid="gl14"><message>Transmitter ukjent : %s. Feil konfigurasjon</message></errorMessage>
\t\t\t</error>\n""" % (tag,tag)])
                    continue

                #Finne riktig enkoding:
                if system[tag][1]=='raw':
                    argumenter = {'data_raw':xmlstreng,'tag':tag}
                elif system[tag][1]=='urlesc':
                    if not data_enc:
                        #Lage en url- encodet versjon av xml dokumentet
                        data = {'dok':xmlstreng}
                        data_enc = urlencode(data)
                    argumenter = {'data_enc':data_enc,'tag':tag}
                #Legge inn flere utsendelses metoder her

                try:
                        t = Thread(target=sendData,
                                    args=(url,),
                                    kwargs=argumenter)
                        t.setDaemon(1)
                        #Dette gjør at vi kan tvinge ned en forbindelse som henger.
                        t.start()
                        threads.extend([t])
                except:
                    s.extend(["""\t\t\t<error quark="%s">
\t\t\t\t<errorMessage dataid="gl12"><message>Kunne ikke sende til: %s</message></errorMessage>
\t\t\t</error>\n""" % (tag,tag)])
    return s, artID, fra

