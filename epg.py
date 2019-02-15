#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
######################################################################
#   Versjon som støtter epg i dls
#	
######################################################################
#import cgitb; cgitb.enable(display=1, logdir="/var/log/gluon")



import xml.dom.minidom
import string
import urllib
import os
import time
import cgi
import sys
import MySQLdb as mdb
import re
from dbConn import database

iDrift = True
macTest = True
verbose = False
DELETEOLDDAYS = False

ECC = 'E2' #Landaskode for Norge
Eld =  {'riks':'FF20','region':'FF30'}
SidSufix = {'p1':'1',
        'p2':'2',
        'p3':'3',
        'ak':'4',
        'sami':'5',
        'an':'6',
        'storting':'7',
        'mpetre':'8'}

kanalSW = {'nrk sport':'sport', 'nrk barn':'barn', 'nrk p1':'p1','nrk p2':'p2','nrk p3':'p3','petre':'p3','nrk petre':'p3','p3':'p3', 'nrk p13':'p13', 'nrk p1pluss':'p1pluss','nrk samidab':'sami','alltid klassisk':'ak','ak':'ak','nrk ak':'ak','nrk mpetre':'mpetre','nrk an':'an','an':'an', 'nrk p1os':'p1os', 'nrk p1mr':'p1mr', 'nrk p1ho':'p1ho','nrk p1bu':'p1bu', 'nrk p1fi':'p1fi', 'nrk p1he':'p1he', 'nrk p1no':'p1no', 'nrk p1oa':'p1oa', 'nrk p1ro':'p1ro', 'nrk p1sf':'p1sf', 'nrk p1sl':'p1sl', 'nrk p1st':'p1st', 'nrk p1te':'p1te', 'nrk p1tr':'p1tr', 'nrk p1ve':'p1ve'}
kanalAlow = ['p1','p2','p3','ak','an','mpetre','barn','gull','fmk']
fjernsyn = ['nrk 1','nrk 2','nrk 3']
        

#Dette kan ev leses ut fra databasen

dokumentmal = """<?xml version="1.0" encoding="iso-8859-1"?>
<!DOCTYPE gluon PUBLIC "-//DTD Identifier" "http://homepage.mac.com/tormodv/gluonDC.dtd">
<gluon priority="%s" artID="%s">
   <head>
      <creator date="%s">
         <name>gluon.tilrettelegger.canaldigital</name>
      </creator>
   </head>
   <body>
      <tables type="epg">
%s      </tables>
   </body>
</gluon>"""

dokumentmal = '''<?xml version="1.0" encoding="UTF-8"?>
<epg xmlns:epg="http://www.worlddab.org/schemas/epg" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="C:\Documents and Settings\Administrator\My Documents\dab\epg.xsd" system="DAB">
    
        %s
    
</epg>'''


crlf = chr(10) + chr(13)
crlf =  chr(10)

#def database(host="160.68.118.48", user="tormodv", database="dab",passord="allmc21"):
#def database(host="127.0.0.1", user="tormodv", database="dab",passord=""):
#	d = mdb.connect(user=user,passwd=passord, host=host)
#	d.select_db(database)
#	return d

def ServiceScope(ensemble='riks',kanal='p1'):
    id = ECC
    
    
    
    
    return id

    

def parseDok(xmlstreng,alle=0):	
    #Plukker ytterste element fra listen
    s=[]
    
    pars = xml.dom.minidom.parseString(xmlstreng)
    priority = pars.documentElement.getAttribute('priority')
    artID = pars.documentElement.getAttribute('artID').encode('iso-8859-1')
    kropp = pars.getElementsByTagName('body')
    vedlikehold = pars.getElementsByTagName('maintenance')
    
    if kropp:
        tabeller = kropp[0].getElementsByTagName('tables')
        for tabell in tabeller:
            if tabell.getAttribute('type')!='epg':
                continue
            
            kampObj={}
            kampObj['type'] = 'epg'
            
            kampObj['element'] = finnUnger(tabell.childNodes,"element")
            kampObj['kanal'] = kampObj['element'][0].getAttribute( 'channel')
            kampObj['priority'] = priority
            kampObj['artID'] = artID
            
            if alle or ny:
                s += [kampObj]
    """		
    if vedlikehold:	
        sidevisningsdirektiv = vedlikehold[0].getElementsByTagName('publishingDirectives')
        if sidevisningsdirektiv:
            kampObj={}
            kampObj['type'] = 'sidevisningsdirektiv'
            kampObj['direktiver'] = sidevisningsdirektiv[0].getElementsByTagName('arrangement')
            
            
            s += [kampObj]
            
    """
    
    
    return s
    

    
def finnUnger(noder,tag,kunEn=0):
    s=[]
    for node in noder:
        if node.nodeType == node.ELEMENT_NODE:
            if node.tagName == tag:
                s.append(node)
                if kunEn: return s
    return s
    
def hentVerdier(noder,lim=''):
    s=''
    for node in noder:
        if node.nodeType == node.TEXT_NODE:
            s+=node.data + lim
    return s
    
def finnVerdi(xmlobjekt,path,entity = 0):
    #Gjøre om krav til liste over noder

    nodeliste = path.split('/')
    
    try:
        for node in nodeliste:
            if node=='':
                continue
            if node[0]!='@':
                xmlobjekt = finnUnger(xmlobjekt.childNodes,node,kunEn=1)[0]
            else:
                #returnere attributverdi
                return xmlobjekt.getAttribute(node[1:])
                
    except IndexError:
        return ''
    if not entity:
        return hentVerdier(xmlobjekt.childNodes)
    else:
        return entetyReplace(hentVerdier(xmlobjekt.childNodes))
    
def entetyReplace(s):
    s = s.replace('&','&amp;')
    
    return s

def patchName(name):
    "Endre fra PI navn til de navnene vi har avtalt med Zonavi"
    if name =="NRK P3":
        return "NRK Petre"
    elif name =="PETRE":
        return "NRK Petre"
    elif name =="P1":
        return "NRK P1"
    elif name =="P2":
        return "NRK P2"
    elif name =="NRK1":
        return "NRK 1"
    elif name =="NRK2":
        return "NRK 2"
    else:
        return name
        
def forkortTittel(streng,lengde):
    return streng[:lengde]
    

        
def lagXML(element,rendertype=['container','programme'], level=1,annTid = 1,fra = None, til = None, slutt = None):
    
    #Forst sjekke om elementet skal rendres
    if (element.getAttribute( 'objecttype') in rendertype) == 0:
        return ''
    s=u''
    s1=u''
    
    
    #Vi finner vi om det er noen subelementer
    subelements = finnUnger(element.childNodes,'subelements')
    if subelements:
        
        for subelement in finnUnger(subelements[0].childNodes,'element'):
            xmlelement, fra , til, lengde, slutt =lagXML(subelement,level= level+1,annTid = annTid, fra= fra, til=til, slutt= slutt)
            s1 += xmlelement
    
    #Finne om elementet innebærer et program eller en liste
    
    if element.getAttribute( 'objecttype') == 'container':
        
        sendedato =  finnVerdi( element,'metadata_DC/dates/date_issued',  entity = 1)
        s += u"""<schedule creationTime="%s" originator="NRK" version="1">
        <scope startTime="%s" stopTime="%s">
            <serviceScope id="e1.d229.0"/>
        </scope>
        """ % (sendedato,
            ISOdatetime(fra),
            ISOdatetime(slutt)
                )
                
        
        sluttag='</schedule>\n'
    else:
        
        #Hent ut verdiene for elementet
        s+='<programme id="crid://dab.nrk.no/%s" version="1" recommendation="no" bitrate="128" broadcast="on-air">\n' % (
                element.getAttribute( 'dataid'),
            )
        tittel =  finnVerdi( element,'metadata_DC/titles/title', entity = 1)
        sendedato =  finnVerdi( element,'metadata_DC/dates/date_issued',  entity = 1)
        sluttid = finnVerdi( element,'programmeSpecials/endOfTransmission')
        
        delta= ISOtilDato(sendedato)
        deltaslutt = ISOtilDato(sluttid)
        if fra==None:
            fra = delta
            #Forutsetter at programmene er kronologisk
        if til < delta:
            til = delta
        if slutt < deltaslutt:
            slutt = deltaslutt
            
            
        #Sjekke om denne er langt fram i tid
        if  not erDagerFram(sendedato,2):
            return None
        #Finne ut om det finnes en annonsert verdi for tidspunkt
        
        annonTid = finnVerdi( element,'programmeSpecials/plannedTimeOfIissue',  entity = 1)
        
        lengde = finnVerdi( element,'metadata_DC/format/format_extent',  entity = 1)
        
        #Legge inn titlene
        s+=u"""<epg:mediumName>%s</epg:mediumName>
                <epg:longName>%s</epg:longName>""" % (forkortTittel(tittel,16),tittel)
                
        #Legge til posisjon
        if annonTid:
            s +=u"""<epg:location>
                    <epg:time time="%s" duration="%s" actualDuration="%s" actualTime="%s"/>
                    <epg:bearer id="e1.d229.0" trigger="d345f567"/>
                </epg:location>""" % (	sendedato,
                                lengde,
                                lengde,
                                annonTid,
                                #Legge inn for id og trigger
                                )
        else:
            s +=u"""<epg:location>
                    <epg:time time="%s" duration="%s"/>
                    <epg:bearer id="e1.d229.0" trigger="d345f567"/>
                </epg:location>""" % (	sendedato,
                                lengde,
                                #Legge inn for id og trigger
                                )
                                    
                
        sluttag = '</programme>\n'		
        
    
    s+=s1
    #Lag bunn
    s += sluttag
    if level == 1:
        n = 9
    else:
        n = 6
        
    s2 = ''
    for linje in  s.splitlines(1):
        s2 += ' ' * n + linje 
    
    return s2, fra , til, lengde, slutt

def isoTilLengde(isoTid):
    tid = 0.0
    tidsFeil = "Feil i konvertering fra ISO 8601 format."
    if isoTid[0]!='P':
        raise tidsFeil,"Begynner ikke med P"
    #Split dager fra timer
    dager,timer = isoTid[1:].split('T')
    #Finn sekunder osv.
    p=re.search('(\d+|\d+\.\d+)S',timer)
    if p:
        tid += float(p.group(1))
    p=re.search('(\d+|\d+\.\d+)M',timer)
    if p:
        tid += float(p.group(1)) * 60
    p=re.search('(\d+|\d+\.\d+)H',timer)
    if p:
        tid += float(p.group(1)) * 3600
    # dager o.l.
    p=re.search('(\d+|\d+\.\d+)D',dager)
    if p:
        tid += float(p.group(1)) * 3600 * 24
    p=re.search('(\d+|\d+\.\d+)M',dager)
    if p:
        tid += float(p.group(1)) * 3600 * 24 * 30
    p=re.search('(\d+|\d+\.\d+)Y',dager)
    if p:
        tid += float(p.group(1)) * 3600 * 24 * 365
    return tid

    
def lagTekst(element,rendertype=['container','programme'], level=1,annTid = 1):
    #Forst sjekke om elementet skal rendres
    if (element.getAttribute( 'objecttype') in rendertype)==0:
        return ''
    s=u''
    #Hent ut verdiene for elementet
    tittel =  finnVerdi( element,'metadata_DC/titles/title')
    sendedato =  finnVerdi( element,'metadata_DC/dates/date_issued')
    #Finne ut om det finnes en annonsert verdi for tidspunkt
    if annTid:
        nyTid = finnVerdi( element,'programmeSpecials/plannedTimeOfIissue')
        if nyTid:
            sendedato = nyTid
    lengde = finnVerdi( element,'metadata_DC/format/format_extent')
    if level ==1:
        #dvs toppen av listen
        #s += "%s %s\n" % (tittel, pendato(sendedato,format = 'dato'))
        s += tittel + '\n'
    else:
        s += "%s %s\n" % (pendato(sendedato, format = 'klokke'), tittel)
        
    
    #Eventuelt sluttid
    if finnVerdi( element,'programmeSpecials/endOfTransmission/@display')=='1':
        s += "(Slutt %s)\n" %  pendato(finnVerdi( element,'programmeSpecials/endOfTransmission'), format = 'klokke')
    
    #Saa finner vi om det er noen subelementer
    subelements = finnUnger(element.childNodes,'subelements')
    if subelements:
        
        for element in finnUnger(subelements[0].childNodes,'element'):
            s+=lagTekst(element,level= level+1,annTid=annTid)
        
    
    #Lag bunn
    
    if level == 1:
        n = 1
    else:
        n = 2
        
    s2 = ''
    for linje in  s.splitlines(1):
        s2 += ' ' * n + linje 
    
    return s2
    
    
    return s

def lagTekstListe(element,rendertype=['container','programme'], level=1,annTid = 1):
    #Forst sjekke om elementet skal rendres
    if (element.getAttribute( 'objecttype') in rendertype)==0:
        return None
    sl=[]
    s=u''
    kanal = finnVerdi( element,'@channel')
    
    #Rette kanalnavn
    if kanal.lower() in kanalSW:
        kanal = kanalSW[kanal.lower()].lower()
            
    if not kanal.lower() in kanalAlow:
        return 0, kanal
    
    #Hent ut verdiene for elementet
    tittel =  finnVerdi( element,'metadata_DC/titles/title')
    
    if 'Dagsnytt' in tittel:
        return None
    sendedato =  finnVerdi( element,'metadata_DC/dates/date_issued')
    #Finne ut om det finnes en annonsert verdi for tidspunkt
    if annTid:
        nyTid = finnVerdi( element,'programmeSpecials/plannedTimeOfIissue')
        if nyTid:
            sendedato = nyTid
    lengde = finnVerdi( element,'metadata_DC/format/format_extent')
    if level ==1:
        #dvs toppen av listen
        #s += "%s %s\n" % (tittel, pendato(sendedato,format = 'dato'))
        s += tittel
    else:
        s += "%s %s" % (pendato(sendedato, format = 'klokke'), tittel)
        
    
        
    #Saa finner vi om det er noen subelementer
    subelements = finnUnger(element.childNodes,'subelements')
    if subelements:
        
        for element in finnUnger(subelements[0].childNodes,'element'):
            subelement = lagTekstListe(element,level= level+1,annTid=annTid)
            if subelement:
                sl.append(subelement)
        
    
    
    if level==1:
        return sl,kanal
    else:
        return s
        
def lagreTV(element,rendertype=['container','programme'], level=1, annTid = 1, c=None, sort = 0, tabell='epgHK'):
    #Forst sjekke om elementet skal rendres
    if (element.getAttribute( 'objecttype') in rendertype)==0:
        return None
    kanal = finnVerdi( element,'@channel')
    #Rette kanalnavn
    if kanal.lower() in kanalSW:
        kanal = kanalSW[kanal.lower()].lower()
            
    if not kanal.lower() in fjernsyn:
        return 0, kanal
    
    #Hent ut verdiene for elementet
    tittel =  finnVerdi( element,'metadata_DC/titles/title').replace('&','&amp;').replace('"','&quot;')
    
    sendedato =  finnVerdi( element,'metadata_DC/dates/date_issued')
    #Finne ut om det finnes en annonsert verdi for tidspunkt
    if annTid:
        nyTid = finnVerdi( element,'programmeSpecials/plannedTimeOfissue').replace('Z','')
        if nyTid:
            sendedato = nyTid
    lengde = finnVerdi( element,'metadata_DC/format/format_extent')
    #if level ==1:
        #dvs toppen av listen
        #s += "%s %s\n" % (tittel, pendato(sendedato,format = 'dato'))
        #s += tittel
    #else:
        #s += "%s %s" % (pendato(sendedato, format = 'klokke'), tittel)
    subtitles = finnVerdi( element,'programmeSpecials/subtitles/subtitle/@type')
    tid =  pendato(sendedato, format = 'klokke')#.replace(':','.')
    
    #Databaseting
    
    if level == 1:
        #Vi stryker dataene før vi setter inn nye
        #Først fjerne i databasen
        d = database()
        c = d.cursor()
        sql = """DELETE FROM %s
                WHERE kanal=%%s;""" % tabell
        c.execute(sql,(kanal,))
    else:
        #Vi har noe å sette inn
        sort += 1
        sql = """INSERT INTO %s(kanal, sort, sendedato, tid, tittel, tekstekode) VALUES
                (%%s,%%s,%%s,%%s,%%s,%%s)""" % tabell
                
        c.execute(sql,(
                    kanal,
                    sort,
                    mdb.TimestampFromTicks(ISOtilDato(sendedato)),
                    tid,
                    tittel.encode('latin-1'),
                    subtitles,
                    )
                )	
    
    if verbose:print  tid, tittel.encode('utf-8'), subtitles, level, tabell
        
    #Saa finner vi om det er noen subelementer
    subelements = finnUnger(element.childNodes,'subelements')
    if subelements:
        
        for element in finnUnger(subelements[0].childNodes,'element'):
            sort = lagreTV(element,level= level+1, annTid=annTid, c = c, sort = sort, tabell = tabell)
            #if subelement:
            #	sl.append(subelement)
        
    #Rydde opp
    if level ==1 : 
        c.close()
        d.close()
    
    return sort

def lagreSigma(element,rendertype=['container','programme'], level=1, annTid = 0, c=None, sort = 0, tabell='sigma'):

    #Forst sjekke om elementet skal rendres
    if (element.getAttribute( 'objecttype') in rendertype)==0:
        return None
    kanal = finnVerdi( element,'@channel')
    #Rette kanalnavn
    if kanal.lower() in kanalSW:
        kanal = kanalSW[kanal.lower()].lower()
            
    #if kanal.lower() in fjernsyn:
    #	return 0, kanal
    
    #Hent ut verdiene for elementet
    tittel =  finnVerdi( element,'metadata_DC/titles/title')#.replace('&','&amp;').replace('"','&quot;')
    ingress = finnVerdi( element,'metadata_DC/description/abstract')#.replace('&','&amp;').replace('"','&quot;')
    progID =  finnVerdi( element,'@dataid')
    fragment = finnVerdi( element,'@fragment')
    sendedato =  finnVerdi( element,'metadata_DC/dates/date_issued')
    #Finne ut om det finnes en annonsert verdi for tidspunkt
    if annTid:
        nyTid = finnVerdi( element,'programmeSpecials/plannedTimeOfissue').replace('Z','')
        if nyTid:
            sendedato = nyTid
    try:
        lengde = isoTilLengde(finnVerdi( element,'metadata_DC/format/format_extent'))
    except:

        lengde = finnVerdi( element,'metadata_DC/format/format_extent')
    #if level ==1:
        #dvs toppen av listen
        #s += "%s %s\n" % (tittel, pendato(sendedato,format = 'dato'))
        #s += tittel
    #else:
        #s += "%s %s" % (pendato(sendedato, format = 'klokke'), tittel)
    subtitles = finnVerdi( element,'programmeSpecials/subtitles/subtitle/@type')
    tid =  pendato(sendedato, format = 'klokke')#.replace(':','.')
    
    #Databaseting

    if level == 1:

        #Vi stryker dataene før vi setter inn nye
        #Først fjerne i databasen, ting fra 7 dager siden
        d = database()
        c = d.cursor()
        if DELETEOLDDAYS:
            sql = """DELETE FROM %s
                    WHERE kanal=%%s and to_days(sendedato) < to_days(now())-7;""" % tabell
            c.execute(sql,(kanal,))
            c.execute('COMMIT')
            sql = """DELETE FROM %s
                    WHERE kanal=%%s and to_days(sendedato) < to_days(now())-21;""" % 'sigmaDMAL'
            c.execute(sql,(kanal,))
            c.execute('COMMIT')
    else:
        #Vi har noe å sette inn

        #Sjekke om sending er laast
        sql = """SELECT done, tid, tekstekode  FROM %s WHERE kanal=%%s and progid=%%s and fragment=%%s""" % tabell
        c.execute(sql,(
                kanal,
                progID,
                fragment
                )
            )
        if c.rowcount != 0:
            #Denne finnes allerede
            done, eksisterendeTid, tekstekode = c.fetchone()
            if tekstekode !='':
                #Fredet innhold
                return 0
            else:
                #Strykes
             
                sql = """DELETE FROM %s WHERE kanal=%%s and progid=%%s and fragment=%%s and date(sendedato)=date(%%s)""" % tabell
                c.execute(sql,(
                            kanal,
                            progID,
                            fragment,
                            mdb.TimestampFromTicks(ISOtilDato(sendedato))
                            )
                    )

                sql = """DELETE FROM %s WHERE kanal=%%s and progid=%%s and fragment=%%s and date(sendedato)=date(%%s)""" % 'sigmaDMAL'
                c.execute(sql,(
                            kanal,
                            progID,
                            fragment,
                            mdb.TimestampFromTicks(ISOtilDato(sendedato))
                            )
                    )
                c.execute('COMMIT')

        #Sendeflater skal ikke registreres, de har ikke progid, men de inneholder ting som er og
        if progID:
            
            sort += 1
            sql = """INSERT INTO %s(kanal, sendedato, tid, lengde, progid, fragment,  tittel, ingress, tekstekode) VALUES
                    (%%s,%%s,%%s,%%s,%%s,%%s,%%s, %%s, %%s)""" % tabell
                    
            c.execute(sql,(
                        kanal,
                        mdb.TimestampFromTicks(ISOtilDato(sendedato)),
                        tid,
                        lengde,
                        progID,
                        fragment,
                        tittel.encode('latin-1'),
                        ingress.encode('latin-1'),
                        '',
                        )
                    )
            c.execute('COMMIT')
                    
            sql = """INSERT INTO %s(kanal, sendedato, tid, lengde, progid, fragment,  tittel, ingress, tekstekode) VALUES
                    (%%s,%%s,%%s,%%s,%%s,%%s,%%s, %%s, %%s)""" % 'sigmaDMAL'
                    
            c.execute(sql,(
                        kanal,
                        mdb.TimestampFromTicks(ISOtilDato(sendedato)),
                        tid,
                        lengde,
                        progID,
                        fragment,
                        tittel.encode('latin-1'),
                        ingress.encode('latin-1'),
                        '',
                        )
                    )	
            c.execute('COMMIT')
            if verbose:print  tid, lengde, progID, tittel.encode('utf-8'), subtitles, level, tabell
        else:
            if verbose:print "Sendeflate:", tid, lengde, progID, tittel.encode('utf-8'), subtitles, level, tabell
            
    #Saa finner vi om det er noen subelementer
    subelements = finnUnger(element.childNodes,'subelements')
    if subelements:
        elementer = finnUnger(subelements[0].childNodes,'element')
        elementer.reverse()#yngste sist, tidlig sending overskriver og fjerner reprise
        for element in elementer:
            sort = lagreSigma(element,level= level+1, annTid=annTid, c = c, sort = sort, tabell = tabell)
            #if subelement:
            #	sl.append(subelement)
            
    #Rydde opp
    if level ==1 : 
        c.close()
        d.close()
    
    return sort
        
        
def sorterProgram(programliste, kanal, gyldighet, d, offset = 0):
    "Lager programlisten og får denne inn i databasen"
    
    #Først fjerne i databasen
    c = d.cursor()
    sql = """DELETE FROM epg_light
                WHERE kanal=%s;"""
    c.execute(sql,(kanal,)) 
    sql = """DELETE FROM epg_light_gyldighet
                WHERE kanal=%s;"""
    c.execute(sql,(kanal,))
    c.execute('COMMIT')
    c.close()
    for t in range(24):
        #t = (t + offset)%24
        t = (t + offset)
        linje = ''
        for program in programliste:
            
            if linje.endswith(program[6:]):
                continue
            sendetime = int(program[:2])
            #if sendetime<6:
            #	sendetime += 24
                
            
            if sendetime>t:
                #Programmet skal være med
                if (len(linje) + len(program))<80:
                    linje = "%s %s" % (linje, program)
                else:
                    break
            else:
                programliste.remove(program)
                #print '***', program.encode('latin-1')
        #Skrive til xmlbasen
        c = d.cursor()
        sql = """INSERT INTO epg_light(kanal,time,info) VALUES 
                (%s,%s,%s)
                """ 
        c.execute(sql,(
                kanal,
                t%24,
                linje.encode('latin-1')
                )
            )
        c.execute('COMMIT')
        #print '>>>',linje.encode('latin-1')
        #print t%24
        c.close()
    #Oppgradere gyldighetsdato
    tid = mdb.TimestampFromTicks(ISOtilDato(gyldighet,sekunder=1))
    c = d.cursor()
    sql = """INSERT INTO epg_light_gyldighet(kanal,date) VALUES 
                (%s,%s)
                """ 
    c.execute(sql,(
            kanal,
            tid
                )
            )

    
    c.execute('COMMIT')
    c.close()


def pendato(tid,format=None):
    
    try:
        ar= tid[:4]
        mnd = int(tid[5:7])
        dag = int(tid[8:10])
        klokke = tid[11:16]
        if format=='kort':
            return "%i.%i. %s" % (dag,mnd,klokke)
        elif format=='klokke':
            return klokke
        elif format=='dato':
            return "%i.%i." % (dag,mnd)
        else:
            return "%s/%s-%s %s" %pendato (dag,mnd,ar,klokke)
    except:
        return  "tid---------------"
    
def sendData(dok,baseUrl,channel,artID):
    sendUrl = baseUrl 
    data = {'dok':dok, 'channel':channel, 'artID':artID}
    data_enc = urllib.urlencode(data)
    a=urllib.urlopen(sendUrl,data_enc)
    svar = a.read(1000)
    a.close()
    return svar
    
def getText(nodelist,ws=0):
    rc = ""
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            if ws:
                rc += node.data.strip() + ' '
            else:
                rc += node.data.strip()
    return rc

def ISOdatetime(t):
    return ("%04d-%02d-%02dT%02d:%02d:%02d+%02d:00" % ((time.localtime(t)[:6])+(time.altzone/-3600,)))

        
def ISOtilDato(dato,sekunder=0):
    if not dato:
        return 0
    if 'T' in dato:
        try:
            if sekunder:
                tid= time.mktime ((int(dato[0:4]),int(dato[5:7]), int(dato[8:10]),int(dato[11:13]),int(dato[14:16])
                        ,int(dato[17:19]),-1,-1,-1))
            else:
                tid= time.mktime ((int(dato[0:4]),int(dato[5:7]), int(dato[8:10]),int(dato[11:13]),int(dato[14:16])
                        ,0,-1,-1,-1))
        except ValueError:
            tid = 0
            
    else:
        try:
            tid = int(dato)
        except:
            tid=0
    return tid

    
         
def erDagerFram(dato,dager,ofset=0, kunSendedogn=0, interval=True):
    "Finner ut om en gitt dato er intil dager/døgn unna"
    dag = 60*60*24
    t = ISOtilDato(dato,sekunder=1)
    n = time.time()
    if kunSendedogn:
        #Vi runner av n(å) til nermeste sendedøgnsstart
        naa= ISOdatetime(n)
        sendedato = naa[:11]+'06:00:00Z'
        n = ISOtilDato(sendedato,sekunder=1)
        #Fåreløpig må vi gjøre det samme med dato
        dato = dato[:11]+'06:00:00Z'
        #***
        t = ISOtilDato(dato,sekunder=1)
        
        if t<n:
            #Fortid
            return -1
        if( n + dager * dag) >= t:
            #Innenfor intervallet
            if interval:
                return 1
            else:
                #Sjekke om i er innenfor det sendedøgnet som er antall dager fram
                if ( t - n) / dag == dager:
                    return 1
                else:
                    return None
        else:
            #utenfor
            return None
    else:
        if t<n:
            #Fortid
            return -1
        if( n + dager * dag) >= t:
            #Innenfor intervallet
            return 1
        else:
            #utenfor
            return None

def parser(dok):
    status = 0
    d=database()
    resultatListe = parseDok(dok,alle=1) 
    kanal = 'alle' #Denne vil normalt overskrives.
    
    for resultat in resultatListe:
        if resultat['type']=='epg':
            """
            #Denne viten må vi lage på nytt
            #Men den er allerede modifisert, men her skal da epg transporten ut
            s = lagXML(resultat['element'][0])[0]
            if not s:
                return "Avvist"
            #legge inn i dok mal
            s = dokumentmal % (
                    #Dato for utsendelse
                    #Start og sluttdato for listen
                    s
                    )
            """
            #Svitsj for epg i tekst:
            
            
            
            #Så sjekker vi epg-dls biten, dersom vi ender med en endring her settes status til 1
            
            #Sjekke forst om epg-en er fra idag.
            gyldighetsdato = finnVerdi( resultat['element'][0],'metadata_DC/dates/date_issued')
            
            if verbose:print erDagerFram(gyldighetsdato,2,kunSendedogn=1)
            if erDagerFram(gyldighetsdato,1,kunSendedogn=1, interval=False):
                lagreTV(resultat['element'][0], tabell = 'epgHKmorgen')
                #lagre sigma data
                lagreSigma(resultat['element'][0])
                                
            if erDagerFram(gyldighetsdato,0,kunSendedogn=1)<5 or True:
                #lagre sigma data
                lagreSigma(resultat['element'][0])

            if erDagerFram(gyldighetsdato,0,kunSendedogn=1)==1:
                #Lagre fjernsysnsdata
                lagreTV(resultat['element'][0])
                
                #Lage epg light 
            
                programliste, kanal =lagTekstListe(resultat['element'][0])
                if programliste:
                    sorterProgram(programliste, kanal, gyldighetsdato, d)
                    status = 1
            
    
    
    #print ServiceScope()
    d.close()
    return {'status':status, 'kanal':kanal, 'datatype':'epg'}

    
def lesFil(filNavn):
    r = open(filNavn)
    dok = r.read(1000000)
    r.close()
    return dok
    
def test(tekst):
    f=open('c:\\testum.txt','w')
    f.write(tekst)
    f.close()
    
def test2(tekst,filnavn):
    f=open(''+filnavn,'w')
    f.write(tekst)
    f.close()




if __name__=='__main__':
    
    print "Content-type: text/html"
    print
    n = time.time()
    if not macTest:
        skjema = cgi.FieldStorage()
        xmldokument = skjema['dok'].value
    else:
        xmldokument = lesFil('epgtest.XML')
        
    alfa= parser(xmldokument)
    print alfa
    
                
