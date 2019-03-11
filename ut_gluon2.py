# -*- coding: utf-8 -*-

"""Tjeneste som skriver data tilbake til gluon
"""

import xml.dom.minidom
import time
from random import choice
from urllib.request import urlopen#(url, data=None, [timeout, ]*,
import sys
from db_conn import database
from hashlib import md5

from annonser import *
from dabfilter import forkort_tittel

IKKE_DLS = ['nett'] #Legg inn bloknavn som ikke støtter dls teknologien, nettradioen f. eks.

GLUON_ADR = ['http://gluon/cgi-bin/karusell.py']
BILLEDMAPPE = ''
VERBOSE = True
LAGET_GRENSE = 1980

def bilde_fix(d, bilde, upid):
    "Henter bilderef fra kaleido"
    #upid = '124145CD0013'
    if bilde.startswith('http://'):#endre dette kriteriet
        #Alt vel
        return bilde
    #Da spør vi kaleido
    c = d.cursor()
    sql = """SELECT kaleidoRef FROM relKaleido WHERE musicId=%s and suborder=%s"""
    c.execute(sql, (
        upid[-12:],
        0
        )
        )

    if c.rowcount == 0:
        c.close()
        return ''
    bilde = c.fetchone()[0]
    c.close()
    return bilde.split('/')[-1]

def filter_artist(artistfelt):
    "Gjør opprenskinger i paranteser i artistfelt"
    if not artistfelt:
        return artistfelt
    artistfelt = artistfelt.replace(' + ', ', ')
    artistfelt = artistfelt.replace('(dirigent)', '(dir)')
    artistfelt = artistfelt.replace('(Dirigent)', '(dir)')
    return artistfelt

def ISOtilDato(dato, sekunder=False, sql=False):
    if not dato:
        return 0
    # FIXME: Denne trengs vel ikke, testes mot ny database
    if type(dato) != type(''):
        #Dette er en forel√∏pig patch for at en har begynt √• bruke datetime objekter
        dato = dato.isoformat()
    if 'T' in dato or sql:
        try:
            if sekunder:
                tid= time.mktime((int(dato[0:4]), int(dato[5:7]), int(dato[8:10]), int(dato[11:13]), int(dato[14:16])
                        , int(dato[17:19]), -1, -1, -1))
            else:
                tid= time.mktime((int(dato[0:4]), int(dato[5:7]), int(dato[8:10]), int(dato[11:13]), int(dato[14:16])
                        , 0, -1, -1, -1))
        except ValueError:
            tid = 0
    else:
        try:
            tid = int(dato)
        except:
            tid = 0
    return tid

def finn_kanaler(d, ikke_distrikt=False):
    "Returnerer alle kanalnavnene fra dab-databasen"
    c = d.cursor()
    if ikke_distrikt:
        sql = """SELECT DISTINCT navn FROM kanal WHERE foreldre_id=id;"""
    else:
        sql = """SELECT DISTINCT navn FROM kanal;"""
    s = []
    c.execute(sql)
    while 1:
        p = c.fetchone()
        if p:
            s.append(p[0].lower())
        else:
            break
    c.close()
    return s

def  distriktskanal(d, kanal):
    "Returnerer en liste av underkanaler på grunnlag av et kanalnavn"
    c = d.cursor()
    sql = """SELECT DISTINCT id FROM kanal WHERE navn =%s LIMIT 1;"""
    c.execute(sql,(kanal))
    row = c.fetchone()
    c.close()
    if row:
        kanal_id = row[0]
    else:
        kanal_id = 99
        print("UKJENT KANAL", kanal)

    #Finne så hvilke distriktskanaler vi har
    c = d.cursor()
    sql = """SELECT navn FROM kanal WHERE foreldre_id =%s ;"""
    s = []
    c.execute(sql,(kanal_id))
    while 1:
        p = c.fetchone()
        if p:
            s.append(p[0])
        else:
            break
    c.close()
    #Dersom denne ender i en null, sÂ har denne kanalen ingen avleggere, ikke en gang seg selv.
    #Derfor legger vi til kanalen selv som det ene punktet i en liste
    if s == []:
        c = d.cursor()
        sql = """SELECT navn FROM kanal WHERE ID =%s LIMIT 1;"""
        s = []
        c.execute(sql,(kanal_id))
        while 1:
            p = c.fetchone()
            if p:
                s.append(p[0])
            else:
                break
        c.close()
    return s

def finn_hovedkanal(d, kanal):
    "Returnerer navnet på hovedkanalen eller kanalnavn på grunnlag av kanalnavn"
    c = d.cursor()
    sql = """SELECT DISTINCT foreldre_id FROM kanal WHERE navn =%s LIMIT 1;"""
    c.execute(sql, (kanal))
    row = c.fetchone()
    c.close()
    if row:
        hoved_id = row[0]
    else:
        hoved_id = 99
        print("UKJENT KANAL", kanal)
    #Finne hva hovedkanalen heter
    c = d.cursor()
    sql = """SELECT navn FROM kanal WHERE id =%s LIMIT 1;"""
    c.execute(sql, (hoved_id))
    row = c.fetchone()
    c.close()
    if row:
        return row[0]

def hentVisningsvalg(d,kanal, blokk_id, datatype=None, oppdatering=False):
    "Henter ut visningsvalg og verdier for filterfunksjonen"
    c = d.cursor()
    sql = """SELECT id FROM kanal WHERE navn = %s LIMIT 1
;
"""
    c.execute(sql, (kanal))
    row = c.fetchone()
    c.close()
    if row:
        kanal_id = row[0]
    else:
        kanal_id = 99

    #SÂ sjekke om denne datatypen skal vÊre breaking for den gitte kanalen
    #Dette kan vÊre bestemt av datatypen ogsÂ
    if ':' in datatype:
        return datatype.split(':',1) # Gir en [datatype, 'breaking'] type
    c = d.cursor()
    sql = """SELECT breaking from datatyper
INNER JOIN dataikanal ON dataikanal.datatype_id=datatyper.id
WHERE kanal_id=%s AND blokk_id=%s AND tittel=%s LIMIT 1;"""
    c.execute(sql, (kanal_id, blokk_id, datatype))
    row = c.fetchone()
    c.close()
    try:
        if row[0] == 'Y':
            return [datatype, 'breaking']
    except:
        #Dette kan feile dersom datatypen/kanalen ikke er registrert -> skal da ikke vise noe
        pass

    if oppdatering:
        c= d.cursor()
        sql = """SELECT DISTINCT
                alias
                FROM datatyper
                INNER JOIN dataikanal ON datatyper.id=dataikanal.datatype_id
                WHERE dataikanal.kanal_id = %s AND dataikanal.blokk_id = %s;"""
        s = []
        c.execute(sql, (kanal_id, blokk_id))
        while 1:
            p = c.fetchone()
            if p:
                s.append(p[0])
            else:
                break

        #Legge over til navn i steden for id
        if not s:
            return []

        if len(s)==1:
            s=s[0]
            sql = """SELECT tittel from datatyper
                    WHERE id=%s;"""
        else:
            sql = """SELECT tittel from datatyper
                    WHERE id in %s;"""
        s1 = []
        c.execute(sql,(s,))

        while 1:
            p = c.fetchone()
            if p:

                s1.append(p[0])
            else:
                break
        c.close()

        return s1

    else:
        c= d.cursor()
        sql = """SELECT datatyper.tittel FROM datatyper
        INNER JOIN dataikanal ON datatyper.id=dataikanal.datatype_id
        WHERE kanal_id=%s AND blokk_id = %s;"""
        s = []
        c.execute(sql, (kanal_id, blokk_id))
        while 1:
            p = c.fetchone()
            if p:
                s.append(p[0])
            else:
                break
        c.close()
        return s

def hentPgrinfo(d,kanal,hovedkanal):
    "Henter kanalnavn og kanalbeskrivelse. Returnerer en liste de kanalnavn er 1. element og beskrivelsen 2."
    c= d.cursor()
    sql = """SELECT tittel, beskrivelse FROM iteminfo WHERE kanal=%s AND type='pgr' LIMIT 1;"""

    c.execute(sql, (kanal, ))
    try:
        try:
            tittel, beskrivelse = c.fetchone()
        finally:
            c.close()
    except TypeError:

        return []
    return [tittel, beskrivelse]


def hentProgrammeinfo(d,kanal,hovedkanal,distriktssending=False, har_distrikter = False, forceDistrikt = True):
    """Henter informasjon om programmet som er pÂ lufta, returnerer dette som en tuple. Ved distriktssendinger kan flagget
    for distriktssendinger settes."""
    #Sjekke om programmet er utl¯pt i kanalen
    c= d.cursor()
    sql = """select tittel, beskrivelse, artist, tid FROM iteminfo
    WHERE kanal=%s AND type='programme' AND localid = '1' AND
    UNIX_TIMESTAMP(tid) + lengde >= UNIX_TIMESTAMP(now()) AND not(UNIX_TIMESTAMP(tid)>UNIX_TIMESTAMP(now())) AND
    progId !='DUMMY_PROD_NR'
    LIMIT 1;"""
    #Denne gir og PI sendeflatetype
    c.execute(sql,(kanal,))
    if c.rowcount:
        iProgramme = True
        if VERBOSE:
            print("I PROGRAMMET")
    else:
        iProgramme = False
        if VERBOSE:
            print("IKKE I PROGRAMMET")

    if iProgramme and har_distrikter:
        #Vi har med Â gj¯re en distriktskanal som har eget program, da skal hele dls-en ignoreres. Den skal genereres ut ifra kanalens egen oppkall
        c.close()
        if VERBOSE:
            print('VOID - har eget program')
        return '', '', '', '', '', '', '', '', False, True
        # Sjekke på denne verdien om kanalen skal hoppes over i

    #Vi må sjekke om hovedkanalen har en distriktsflate

    sql = """SELECT digastype FROM iteminfo WHERE kanal=%s AND type='programme' AND localid = '1' LIMIT 1;"""
    #Denne gir og PI sendeflatetype
    c.execute(sql,(hovedkanal,))
    try:
        try:
            digastype, = c.fetchone()
        finally:
            c.close()
    except TypeError:
        digastype = ''
        #Sjekke omo denne egentlig vil kunne feile
    #Finne alternativ mÂte for Â tenne distriktsflagg
    if iProgramme and (kanal != hovedkanal):
        #Kanalen har et aktivt program, og den har en mor, dvs hovedkanl er ikke seg selv.
        distriktssending = True
        tittel_sufix = ''


    elif digastype == '50' and (kanal != hovedkanal):
        #Vi har en distriktssending av den gamle typen
        distriktssending = True
        #Vi har ennÂ ikke distriktsvise programme info
        #Vi henter f¯rst ut navnet "Brandet" pÂ kanalen
        c= d.cursor()

        sql = """SELECT branding FROM kanal WHERE navn=%s LIMIT 1;"""
        c.execute(sql,(kanal,))
        try:
            try:
                branding, = c.fetchone()
            finally:
                c.close()
        except TypeError:
            pass
            #Sjekke omo denne egentlig vil kunne feile
        if branding:
            tittel_sufix = ' fra ' + branding
        else:
            tittel_sufix = ''

        kanal = hovedkanal #Dette gj¯r at vi aldri henter programdata fra distriktsflaten

    else:
        #Hovedkanalen er ikke registrert med en distriktsflate, sjekke om vi skal la underkanalen ta styringen
        #Vi skal ikke har regionvise resultater
        if forceDistrikt and iProgramme:
            #Vi bytter ikke kanaler, men stryker sufix
            tittel_sufix = ''
        else:
            kanal = hovedkanal
            tittel_sufix = ''

    c= d.cursor()
    sql = """SELECT tittel, progId, beskrivelse, artist, tid, lengde, digastype, nettype FROM iteminfo WHERE kanal=%s AND type='programme' AND localid = '1' LIMIT 1;"""

    c.execute(sql,(kanal,))
    try:
        try:
            tittel, prog_Id, beskrivelse, artist, sendetid, lengde, digastype, nettype = c.fetchone()
        finally:
            c.close()
    except TypeError:
        #Dersom vi ikke har noe her, kan det hende det er en distriktskanal som ikke har egne metadata
        if hovedkanal and not distriktssending:
            return hentProgrammeinfo(d,hovedkanal,None)
        else:
            return '', '', '', '', '', '', '', '', False, False

    if type(sendetid)!=type(''):
        #Dette er en forel√∏pig patch for at en har begynt √• bruke datetime objekter
        sendetid = sendetid.isoformat()

    if sendetid:
        sendetid = sendetid.replace(' ', 'T')

    tittel = tittel + tittel_sufix #Legger pÂ f. eks. "fra NRK Tr¯ndelag" pÂ dirstriksflater

    return prog_Id, tittel, beskrivelse, artist, sendetid, int(lengde), digastype, nettype, distriktssending, False


def hent_programme_next(d,kanal,hovedkanal,distriktssending=0):
    "Henter informasjon om det neste programmet som skal pÂ lufta, returnerer en liste med et element."
    c= d.cursor()
    sql = """SELECT tittel, progId, beskrivelse, artist, tid, lengde, digastype FROM iteminfo WHERE kanal=%s AND type='programme' AND localid = '2' LIMIT 1;"""

    c.execute(sql,(kanal,))
    try:
        try:

            tittel, prog_Id, beskrivelse, artist, tid, lengde, digastype = c.fetchone()
        finally:
            c.close()
    except TypeError:
        if hovedkanal and not distriktssending:
            return hent_programme_next(d,hovedkanal,None)
        else:
            return '', '', '', '', '', '', ''
    if type(tid)!=type(''):
        #Dette er en forel√∏pig patch for at en har begynt √• bruke datetime objekter
        tid = tid.isoformat()
    if tid:
                tid = tid.replace(' ', 'T')
    return prog_Id, tittel, beskrivelse, artist, tid, int(lengde), digastype



def hent_iteminfo_forrige(d,kanal,hovedkanal,distriktssending=0, item=False, info=False):
    "Henter informasjon om innslaget som er pÂ lufta, returnerer en liste med et element."
    c= d.cursor()
    #samsending?
    sql = """SELECT kildekanal FROM iteminfo WHERE kanal=%s AND type='programme'  AND localid = '1' LIMIT 1 ;"""
    c.execute(sql,(kanal,))
    row =  c.fetchone()
    if row:
        kildekanal = row[0]
    else:
        kildekanal = False
    if kildekanal:
        #Da henter vi verdiene fra denne isteden
        kanal = kildekanal

    sql = """SELECT progId, tittel, ExtractValue(element, 'element/metadata_DC/titles/title'), artist,  ExtractValue(element, 'element/metadata_DC/creators/creator[role="Composer"]/family_name'), beskrivelse, digastype, bildeID, tid, lengde FROM iteminfo WHERE kanal=%s AND type='item'  AND localid = '5' LIMIT 1 ;"""

    c.execute(sql,(kanal,))
    try:
        try:
            dataid, tittel, kort_tittel, artist, komponist, album, digastype, bilde, tid, lengde = c.fetchone()
        finally:
            c.close()
    except TypeError:
        if hovedkanal and not distriktssending:
            return hent_iteminfo_forrige(d,hovedkanal,None, item=item, info=info)
        else:
            return '', '', '', '', '', '', '', '', '', ''

    if digastype !='Music':
        return '', '', '', '', '', '', '', '', '', ''

    if type(tid)!=type(''):
        # FIXME: isttid?
        #Dette er en forel√∏pig patch for at en har begynt √• bruke datetime objekter
        tid = tid.isoformat()
    if tid:
                tid = tid.replace(' ', 'T')
    #Artist feltet mÂ endres litt
    if artist:
        artist = artist.replace('|', ' ')
        artist = artist.lstrip('. ')
        artist = artist[0].upper() + artist[1:]

    #Vi finner opptaksdato
    c= d.cursor()
    sql = """SELECT YEAR(laget) FROM iteminfo WHERE kanal=%s AND type='item'  AND localid = '5' LIMIT 1 ;"""
    c.execute(sql,(kanal,))
    try:
        try:
            laget, = c.fetchone()
        finally:
            c.close()
    except :
        laget = 0
    else:
        if laget<LAGET_GRENSE:
            tittel = "%s, innspilt %s," % (tittel,laget)

    return dataid, tittel, kort_tittel, artist, komponist, album, bilde, tid, int(lengde), digastype

def hent_iteminfo(d, kanal, hovedkanal, distriktssending=False, item=False, info=False):
    "Henter informasjon om innslaget som er pÂ lufta, returnerer en liste med et element."
    c = d.cursor()
    #samsending?
    sql = """SELECT kildekanal FROM iteminfo WHERE kanal=%s AND type='programme'  AND localid = '1' LIMIT 1 ;"""
    c.execute(sql, (kanal,))
    row = c.fetchone()
    if row:
        kildekanal = row[0]
    else:
        kildekanal = False
    if kildekanal:
        #Da henter vi verdiene fra denne isteden
        kanal = kildekanal

    sql = """SELECT progId, tittel, ExtractValue(element, 'element/metadata_DC/titles/title'), artist,  ExtractValue(element, 'element/metadata_DC/contributors/contributor[role="Performer"]/family_name'), ExtractValue(element, 'element/metadata_DC/creators/creator[role="Composer"]/family_name'), beskrivelse, digastype, bildeID, tid, lengde FROM iteminfo WHERE kanal=%s AND type='item'  AND localid = '3' LIMIT 1 ;"""
    c.execute(sql, (kanal,))
    try:
        try:
            dataid, tittel, kort_tittel, artist, artist_short, komponist, album, digastype, bilde, tid, lengde = c.fetchone()
        finally:
            c.close()

    except TypeError:
        if hovedkanal and not distriktssending:
            return hent_iteminfo(d,hovedkanal,None, item = item, info = info)

        return '', '', '', '', '', '', '', '', '', '', ''

    if digastype != 'Music':
        return '', '', '', '', '', '', '', '', '', '', ''
    # FIXME: Denne kan vel fikses nå
    if type(tid) != type(''):
        #Dette er en foreløig patch for at en har begynt å bruke datetime objekter
        tid = tid.isoformat()
    if tid:
            tid = tid.replace(' ', 'T')
    #Artist feltet må endres litt
    if artist:
        artist = artist.replace('|', ' ')
        artist = artist.lstrip('. ')
        artist = artist[0].upper() + artist[1:]

    #Vi finner opptaksdato
    c = d.cursor()
    sql = """SELECT YEAR(laget) FROM iteminfo WHERE kanal=%s AND type='item'  AND localid = '3' LIMIT 1 ;"""
    c.execute(sql, (kanal,))
    try:
        try:
            laget, = c.fetchone()
        finally:
            c.close()
    except :
        laget = 0
    else:
        if laget < LAGET_GRENSE:
            tittel = "%s, innspilt %s," % (tittel, laget)

    return dataid, tittel, kort_tittel, artist, artist_short, komponist, album, bilde, tid, int(lengde), digastype

def hent_news_item_forrige(d, kanal, hovedkanal, distriktssending=0, news=False, info=False):
    "Henter informasjon om innslaget som er pÂ lufta, returnerer en liste med et element."
    c = d.cursor()
    #samsending?

    sql = """SELECT kildekanal FROM iteminfo WHERE kanal=%s AND type='programme'  AND localid = '1' LIMIT 1 ;"""
    c.execute(sql, (kanal, ))
    row = c.fetchone()
    if row:
        kildekanal = row[0]
    else:
        kildekanal = False
    if kildekanal:
        #Da henter vi verdiene fra denne isteden
        kanal = kildekanal

    sql = """SELECT progId, tittel, artist, beskrivelse, digastype, bildeID, tid, lengde FROM iteminfo WHERE kanal=%s AND type='item'  AND localid = '5' LIMIT 1 ;"""

    c.execute(sql,(kanal,))
    try:
        try:
            dataid, tittel, artist, beskrivelse, digastype, bilde, tid, lengde = c.fetchone()
        finally:
            c.close()
    except TypeError:
        if hovedkanal and not distriktssending:
            return  hent_news_item(d, hovedkanal, None, news=news, info=info)
        else:
            return '', '', '', '', '', '', '', ''

    if digastype !='News':
        return '', '', '', '', '', '', '', ''

    album = '' #Denne informasjonen finnes ikke foreløpig
    if bilde != '':
        bilde = BILLEDMAPPE + bilde

    if type(tid) != type(''):
        #Dette er en forel√∏pig patch for at en har begynt √• bruke datetime objekter
        tid = tid.isoformat()
    if tid:
                tid = tid.replace(' ', 'T')

    #Artist feltet må endres litt
    if artist:
        artist = artist.replace('|', ' ')
        artist = artist.lstrip('. ')
        artist = artist[0].upper() + artist[1:]

    #Vi finner opptaksdato
    c= d.cursor()
    sql = """SELECT YEAR(laget) FROM iteminfo WHERE kanal=%s AND type='item'  AND localid = '5' LIMIT 1 ;"""
    c.execute(sql,(kanal,))
    try:
        try:
            laget, = c.fetchone()
        finally:
            c.close()
    except :
        laget = 0
    else:
        if laget<LAGET_GRENSE:
            tittel = "%s, innspilt %s," % (tittel,laget)
    #Hack for IBSEN
    if beskrivelse:
        album = beskrivelse
        #S√• et nytt hack
    if kanal in ['nrk_5_1', 'gull', 'barn']:
        #Vi skal ikke ha med artist
        artist = ''
    if not news:
        tittel = ''
        artist = ''
    if not info:
        album = ''

    return dataid, tittel, artist, beskrivelse, bilde, tid, int(lengde), digastype


def  hent_news_item(d,kanal,hovedkanal,distriktssending=0, news = False, info = False):
    "Henter informasjon om innslaget som er pÂ lufta, returnerer en liste med et element."
    c= d.cursor()
    #samsending?

    sql = """SELECT kildekanal FROM iteminfo WHERE kanal=%s AND type='programme'  AND localid = '1' LIMIT 1 ;"""
    c.execute(sql,(kanal,))
    row =  c.fetchone()
    if row:
        kildekanal = row[0]
    else:
        kildekanal = False
    if kildekanal:
        #Da henter vi verdiene fra denne isteden
        kanal = kildekanal

    sql = """SELECT progId, tittel, artist, beskrivelse, digastype, bildeID, tid, lengde FROM iteminfo WHERE kanal=%s AND type='item'  AND localid = '3' LIMIT 1 ;"""

    c.execute(sql,(kanal,))

    try:
        try:
            dataid, tittel, artist, beskrivelse, digastype, bilde, tid, lengde = c.fetchone()
        finally:
            c.close()
    except TypeError:
        if hovedkanal and not distriktssending:
            return  hent_news_item(d,hovedkanal,None, news = news, info = info)
        else:
            return '', '', '', '', '', '', '', ''

    if digastype == '':digastype = 'Music' #Lex BMS
    if digastype !='News':
        return '', '', '', '', '', '', '', ''


    album = '' #Denne informasjonen finnes ikke forel¯pig
    if bilde !='':
        if not sjekkStatus(bilde):
            bilde =''
        else:
            bilde = BILLEDMAPPE + bilde

    #Artist feltet mÂ endres litt
    if artist:
        artist = artist.replace('|', ' ')
        artist = artist.lstrip('. ')
        artist = artist[0].upper() + artist[1:]

    if type(tid)!=type(''):
        #Dette er en forel√∏pig patch for at en har begynt √• bruke datetime objekter
        tid = tid.isoformat()
    if tid:
                tid = tid.replace(' ', 'T')
    #Vi finner opptaksdato
    c= d.cursor()
    sql = """SELECT YEAR(laget) FROM iteminfo WHERE kanal=%s AND type='item'  AND localid = '3' LIMIT 1 ;"""
    c.execute(sql,(kanal,))
    try:
        try:
            laget, = c.fetchone()
        finally:
            c.close()
    except :
        laget = 0
    else:
        if laget < LAGET_GRENSE:
            tittel = "%s, innspilt %s," % (tittel,laget)
    #Hack for IBSEN
    if beskrivelse:
        album = beskrivelse
        #S√• et nytt hack
    if kanal in ['nrk_5_1', 'gull', 'barn']:
        #Vi skal ikke ha med artist
        artist = ''
    if not news:
        tittel = ''
        artist = ''
    if not info:
        album = ''

    return dataid, tittel, artist, beskrivelse, bilde, tid, int(lengde), digastype


def hent_item_next(d,kanal,hovedkanal,distriktssending=0, musikk=False, news = False):
    "Henter informasjon om det neste innslaget som skal pÂ lufta, returnerer en liste med et element."
    c= d.cursor()
    #samsending?

    sql = """SELECT kildekanal FROM iteminfo WHERE kanal=%s AND type='programme'  AND localid = '1' LIMIT 1 ;"""
    c.execute(sql,(kanal,))
    row =  c.fetchone()
    if row:
        kildekanal = row[0]
    else:
        kildekanal = False
    if kildekanal:
        #Da henter vi verdiene fra denne isteden
        kanal = kildekanal

    #F¯rst finne ut om vi har to like titler. Dersom denne feiler har vi i alle fall ikke noen like titler.
    try:
        sql = """SELECT tittel FROM iteminfo WHERE kanal=%s AND type='item' AND (localid = '4' OR localid = '3')  LIMIT 2;"""
        c.execute(sql,(kanal,))

        tittel1 = c.fetchone()[0]
        tittel2 = c.fetchone()[0]
    except:
        pass

    #Ellers viser vi nesteinformasjon
    sql = """SELECT progId, tittel, ExtractValue(element, 'element/metadata_DC/titles/title'),
     artist,  ExtractValue(element, 'element/metadata_DC/creators/creator[role="Composer"]/family_name'),
      beskrivelse, digastype, bildeID, tid, lengde FROM iteminfo WHERE kanal=%s AND type='item' AND localid = '4' LIMIT 1;"""

    c.execute(sql, (kanal, ))
    try:
        try:
            dataid, tittel, kort_tittel,artist, komponist, beskrivelse, digastype, bilde, tid, lengde = c.fetchone()
        finally:
            c.close()
    except TypeError:
        if hovedkanal and not distriktssending:
            return hent_item_next(d, hovedkanal, None, musikk=musikk, news=news)
        else:
            return '', '', '', '', '', '', '', '', '', ''
    if digastype == '':
        digastype = 'Music' #Lex BMS

    if digastype == 'Music' and not musikk:
        #Vi skal ikke vise
        return '', '', '', '', '', '', '', '', '', ''
    if digastype == 'News' and not news:
        #Vi skal ikke vise
                return '', '', '', '', '', '', '', '', '', ''

    if type(tid)!=type(''):
        #Dette er en foreløpig patch for at en har begynt å bruke datetime objekter
        tid = tid.isoformat()
    if tid:
                tid = tid.replace(' ', 'T')
    album = ''
    #Artist feltet må endres litt
    if artist:
        artist = artist.replace('|', ' ')
        artist = artist.lstrip('. ')
        artist = artist[0].upper() + artist[1:]

    #Aldri infofelt paa neste, og ikke artis paa news
    if musikk:
        #kutte beskrivelse
        beskrivelse = ''
    return dataid, tittel, kort_tittel, artist, komponist, beskrivelse, bilde, tid, int(lengde), digastype


def send_data_web(data,uri, svar_fra_mottager = True):
    "Sender inn til gluon"
    # TODO: Bytt denne til noe enklere
    headers = {"Content-type": "application/xml",
        "Accept": "*/*",
        "User-Agent":"MDW 1.0 [no] (%s; U)"%sys.platform}
    #Splitte protokoll og uri
    protokol, uri = uri.split(':',1)
    uri = uri.lstrip('/')
    #Dele opp uri til hostname og url
    host, url = uri.split('/',1)

    try:
        conn = HTTPConnection(host)
        conn.request("POST", '/' + url, data, headers)
    except:
        #Legge inn forskjellige verdier her
        print('Kunne ikke lage forbindelse')
    else:
        if svar_fra_mottager:
            svar = conn.getresponse().read()

        else:
            svar ='Sendt'
        conn.close()
    return svar


def returnTimezone():
    if time.localtime()[8]:
        return '+02:00'
    else:
        return '+01:00'


def lagGluon(artID="test"):
    "Lager et gluon rotdokument, og returnerer dette og en pointer til stedet hvor elementene skal inn"
    impl = xml.dom.minidom.getDOMImplementation()
    utdok = impl.createDocument('http://www.w3.org/2001/XMLSchema', 'gluon', None)
    utdok.documentElement.setAttribute('priority', '3')
    utdok.documentElement.setAttribute('artID', artID)
    utdok.documentElement.setAttribute('xmlns', "http://gluon.nrk.no/gluon2")
    utdok.documentElement.setAttribute('xmlns:gluonDict', "http://gluon.nrk.no/gluonDict")
    utdok.documentElement.setAttribute('xmlns:xsi', "http://www.w3.org/2001/XMLSchema-instance")
    utdok.documentElement.setAttribute('xsi:schemaLocation', "http://gluon.nrk.no/gluon2 http://gluon.nrk.no/gluon2.xsd")
    #head
    metadata = utdok.documentElement.appendChild(utdok.createElement('head')).appendChild(utdok.createElement('metadata'))
    navn = metadata.appendChild(utdok.createElement('creators')).appendChild(utdok.createElement('creator')).appendChild(utdok.createElement('name'))
    navn.setAttribute('person', 'false')
    navn.appendChild(utdok.createTextNode('MDW:gluon2'))
    metadata.appendChild(utdok.createElement('dates')).appendChild(utdok.createElement('dateIssued')).appendChild(utdok.createTextNode(time.strftime("%Y-%m-%dT%H:%M:%S") + returnTimezone()))
    #body
    tables = utdok.documentElement.appendChild(utdok.createElement('objects'))

    return utdok, tables



def sette_dataid(tittel):
    "Fattigmans id generator"
    m = md5(tittel.encode('utf-8'))
    return 'MDW:%s' % m.hexdigest()


def add_name(utdok, tag, roleId='', name='', ):
    famname = tag.appendChild(utdok.createElement('name'))
    famname.appendChild(utdok.createTextNode(name))
    #famname.setAttribute('person', 'true') #Bruke bare visningsnavnet for dette, kunne vel egentlig brukt abstract
    roleTag = tag.appendChild(utdok.createElement('role'))
    if roleId:
        roleTag.setAttribute('link', 'http://gluon.nrk.no/nrkRoller.xml#' + roleId)

def addObject(utdok, pointer,
              sub_elements = False,
              objecttype='',
              subjects='',
              dataid='',
              channel='',
              runorder='',
              tittel = '',
              kort_tittel = '',
              creator = '',
              abstract = '',
              partisipant_description = '',
              partisipant_short_description='',
              contributor = '',
              gluon_type = '',
              issued = '',
              duration = '',
              bilde = ''
              ):
    "Legger på et element til et objekttre, returnerer en peker til subelement-elementet"
    #Ordne elementet
    if not dataid:
        dataid = "noID"
    #print channel
    channel = channel.replace('ko ', 'ko_')#lex toten
    #print 77, channel
    element = pointer.appendChild(utdok.createElement('object'))
    element.setAttribute('objecttype', objecttype)
    element.setAttribute('dataid', dataid)
    element.setAttribute('channel', channel)
    if runorder: element.setAttribute('runorder', runorder)
    #Har to underelementer, metadata og subelements
    metadata = element.appendChild(utdok.createElement('metadata'))

    #Legge til de ulike elementene
    if tittel:
        titler = metadata.appendChild(utdok.createElement('titles'))
        titler.appendChild(utdok.createElement('title')).appendChild(utdok.createTextNode(tittel))
        # Legge til kort tittel for DAB
        if objecttype=='item':
            try:
                publishing_title = forkort_tittel(tittel)
            except:
                publishing_title = tittel
            titAlt2 = titler.appendChild(utdok.createElement('titleAlternative'))
            titAlt2.appendChild(utdok.createTextNode(publishing_title))
            titAlt2.setAttribute('gluonDict:titlesGroupType', 'publishingTitle')

        if kort_tittel:
            titAlt = titler.appendChild(utdok.createElement('titleAlternative'))
            titAlt.appendChild(utdok.createTextNode(kort_tittel))
            titAlt.setAttribute('gluonDict:titlesGroupType', 'intellectualWorkTitle')

    if creator:
        if type(creator) == type({}):
            creators = metadata.appendChild(utdok.createElement('creators'))
            for role in creator:
                navnene = creator[role]
                if type(navnene) != type([]):
                    navnene = [navnene]
                for navn in navnene:
                    creatorTag = creators.appendChild(utdok.createElement('creator'))
                    add_name(utdok, creatorTag, roleId = role, name = navn)
        else:
            metadata.appendChild(creator)
    #Subjects

    if subjects:
        subjectelement = metadata.appendChild(utdok.createElement('subjects'))
        for subject in subjects:
            st = subjectelement.appendChild(utdok.createElement('subject'))
            if 'value' in subject:
                st.appendChild(utdok.createTextNode(subject['value']))
            if 'label' in subject:
                st.setAttribute('label', subject['label'])
            if 'reference' in subject:
                st.setAttribute('reference', subject['reference'])
     # TODO: hente denne fra base sammen med resten, så filtrere
    partisipant_short_description = filter_artist(partisipant_short_description)

    if abstract or partisipant_description or partisipant_short_description:
        desc = metadata.appendChild(utdok.createElement('description'))
        if abstract:
            absSF = desc.appendChild(utdok.createElement('abstract'))
            absSF.setAttribute('restriction', 'public')
            absSF.setAttribute('link', 'http://gluon.nrk.no/dataordbok.xml#standFirst')
            absSF.setAttribute('purpose', 'shortDescription')
            absSF.appendChild(utdok.createTextNode(abstract))
        if partisipant_description:
            absSF = desc.appendChild(utdok.createElement('abstract'))
            absSF.setAttribute('restriction', 'public')
            absSF.setAttribute('link', 'http://gluon.nrk.no/dataordbok.xml#presentation')
            absSF.setAttribute('purpose', 'presentation2')
            absSF.appendChild(utdok.createTextNode(partisipant_description))
        if partisipant_short_description:
            absSF = desc.appendChild(utdok.createElement('abstract'))
            absSF.setAttribute('restriction', 'public')
            absSF.setAttribute('link', 'http://gluon.nrk.no/dataordbok.xml#presentation')
            absSF.setAttribute('purpose', 'presentationShort')
            absSF.appendChild(utdok.createTextNode(partisipant_short_description))

    if contributor:
        if type(contributor) == type({}):
            contributors = metadata.appendChild(utdok.createElement('contributors'))
            for roleId in contributor:
                navnene = contributor[roleId]
                if type(navnene) != type([]):
                    navnene = [navnene]
                for navn in navnene:
                    contributor_tag = contributors.appendChild(utdok.createElement('contributor'))
                    add_name(utdok, contributor_tag, roleId=roleId, name=navn)
        else:
            metadata.appendChild(contributor)
    if gluon_type:
        gluon_types = metadata.appendChild(utdok.createElement('types'))
        for gts in gluon_type:
            gt = gluon_types.appendChild(utdok.createElement('type'))
            if 'value' in gts:
                gt.appendChild(utdok.createTextNode(gts['value']))
            if 'label' in gts:
                gt.setAttribute('label', gts['label'])
            if 'reference' in gts:
                gt.setAttribute('reference', gts['reference'])

    if issued:
        metadata.appendChild(utdok.createElement('dates')).appendChild(utdok.createElement('dateIssued')).appendChild(utdok.createTextNode(issued))

    if duration:
        metadata.appendChild(utdok.createElement('format')).appendChild(utdok.createElement('formatExtent')).appendChild(utdok.createTextNode("PT%sS" % duration))

    if bilde:
        relations = metadata.appendChild(utdok.createElement('relations'))
        oldRef = relations.appendChild(utdok.createElement('relationReferences'))
        oldRef.setAttribute('label', 'illustration')
        oldRef.setAttribute('reference', 'DMA')
        oldRef.appendChild(utdok.createTextNode(bilde))
        bildeRel = relations.appendChild(utdok.createElement('relationIsDescribedBy'))
        bildeRel.setAttribute('reference', 'DMA')
        bildeRel.appendChild(utdok.createTextNode(bilde))

    if sub_elements:
        return element.appendChild(utdok.createElement('subelements'))
    else:
        return None

def lag_metadata(kanal='alle', datatype=None, id='', test_modus=False):
    "Henter data for en gitt kanal ut i fra de forskjellige databasene og setter sammen til en DLS som sendes videre som et mimemultipartdokument."
    utdata = {}
    #kanal='alle'
    #Fange opp at jeg skal kunne generere nytt på alle kanaler.
    d = database()
    if kanal == 'alle':
        kanaler = finn_kanaler(d, ikke_distrikt=False)
    else:
        kanaler = [kanal]

    for kanal in kanaler:
        #Det kan hende at kanalene er delt opp i distrikter - eks. p1oslo
        #utvid kanaler
        distriktskanaler = distriktskanal(d, kanal)
        if len(distriktskanaler) == 1:
            #Vi har kunn en kanal, distrikskanal eller kanalen selv, vi m√• finne moderkanalen
            hovedkanal = finn_hovedkanal(d, kanal)
            har_distrikter = False
        else:
            #Vi har en kanal med barn, ergo er hovedkanalen kanalen selv.
            hovedkanal = kanal
            har_distrikter = True

        for kanal in distriktskanaler:
            #Lage nytt dokument
            xmldom, tablePointer = lagGluon(artID="iteminfo_NRK_%s" % kanal)

            # Hente programinfo, data om sendingen
            prog_Id, tittel, info, programleder, issued, duration, digastype, nettype, distriktssending, egenKanal = hentProgrammeinfo(d, kanal,hovedkanal, har_distrikter = har_distrikter)
            if egenKanal:
                if VERBOSE:
                    print("Har egen sending")
                continue

            if programleder:
                programleder = {'V40':programleder}

            if nettype:
                subjects = [{'reference':'Nettkategori', 'value' : nettype}]
            else:
                subjects = ''

            #Legge inn som objekt
            innslag = addObject(xmldom, tablePointer,
                                sub_elements=True,
                                objecttype="programme",
                                channel=kanal,
                                dataid=prog_Id,
                                tittel=tittel,
                                abstract=info,
                                contributor=programleder,
                                duration=duration,
                                issued=issued,
                                gluon_type=[{'reference':'NRK-Escort', 'value' : digastype}],
                                subjects=subjects
                                )

            # Hente info om forige element
            dataid, tittel, kort_tittel, artist, komponist, info, bilde, issued, duration, gluon_type = hent_iteminfo_forrige(
                                                                d, kanal, hovedkanal, item=True, info=True, distriktssending=distriktssending)
            if not dataid:
                dataid = sette_dataid(tittel)
            if not komponist:
                creator = ''
            else:
                creator = {'V34':komponist}
            bilde = bilde_fix(d, bilde, dataid)

            if tittel:
                #Dersom vi ikke har en tittel skal vi ikke ha noe objekt heller
                addObject(xmldom, innslag,
                runorder="past",
                sub_elements=False,
                objecttype="item",
                channel=kanal,
                dataid=dataid,
                tittel=tittel,
                kort_tittel=kort_tittel,
                abstract=info,
                creator=creator,
                partisipant_description = artist,
                duration=duration,
                issued=issued,
                gluon_type=[{'label':'class', 'reference':'Digas', 'value' : gluon_type}],
                bilde=bilde
                )

            #Musikkobjekter
            dataid, tittel, kort_tittel, artist, artist_short, komponist, info, bilde, issued, duration, gluon_type = hent_iteminfo(d, kanal, hovedkanal, item=True, info=True, distriktssending=distriktssending)
            if not dataid:
                dataid = sette_dataid(tittel)
            if not komponist:
                creator = ''
            else:
                creator = {'V34':komponist}
            if tittel:
                #Dersom vi ikke har en tittel skal vi ikke ha noe objekt heller
                bilde = bilde_fix(d, bilde, dataid)
                addObject(xmldom, innslag,
                runorder="present",
                sub_elements=False,
                channel=kanal,
                objecttype="item",
                dataid=dataid,
                tittel=tittel,
                kort_tittel=kort_tittel,
                abstract=info,
                creator=creator,
                partisipant_description=artist,
                partisipant_short_description=artist_short,
                duration=duration,
                issued=issued,
                gluon_type=[{'label':'class', 'reference':'Digas', 'value' : gluon_type}],
                bilde=bilde
                )

            dataid, tittel, artist, info, bilde, issued, duration, gluon_type = hent_news_item_forrige(d, kanal, hovedkanal, news=True, info=True, distriktssending=distriktssending)
            if not dataid:
                dataid = sette_dataid(tittel)
            #Sette inn innslags objekt her
            if tittel:
                #Dersom vi ikke har en tittel skal vi ikke ha noe objekt heller
                bilde = bilde_fix(d, bilde, dataid)
                addObject(xmldom, innslag,
                runorder="past",
                channel=kanal,
                sub_elements=False,
                objecttype="item",
                dataid=dataid,
                tittel=tittel,
                abstract=info,
                contributor={'V36':artist},
                duration=duration,
                issued=issued,
                gluon_type=[{'label':'class', 'reference':'Digas', 'value' : gluon_type}],
                bilde=bilde
                )

            dataid, tittel, artist, info, bilde, issued, duration, gluon_type =  hent_news_item(d, kanal, hovedkanal, news=True, info=True)
            if not dataid:
                dataid = sette_dataid(tittel)
            #Sette inn innslags objekt her
            if tittel:
                #Dersom vi ikke har en tittel skal vi ikke ha noe objekt heller
                bilde = bilde_fix(d, bilde, dataid)
                addObject(xmldom, innslag,
                runorder="present",
                channel=kanal,
                sub_elements=False,
                objecttype="item",
                dataid=dataid,
                tittel=tittel,
                abstract=info,
                contributor={'V36':artist},
                duration=duration,
                issued=issued,
                gluon_type=[{'label':'class', 'reference':'Digas', 'value' : gluon_type}],
                bilde=bilde
                )

            dataid, tittel, kort_tittel, artist, komponist, info, bilde, issued, duration, gluon_type = hent_item_next(d, kanal, hovedkanal, musikk=True, news=False)
            if not dataid:
                dataid = sette_dataid(tittel)
            if not komponist:
                creator = ''
            else:
                creator = {'V34':komponist}
            #Sette inn innslags objekt her
            if tittel:
                #Dersom vi ikke har en tittel skal vi ikke ha noe objekt heller
                bilde = bilde_fix(d, bilde, dataid)
                addObject(xmldom, innslag,
                          runorder="future",
                          channel=kanal,
                          sub_elements=False,
                          objecttype="item",
                          dataid=dataid,
                          tittel=tittel,
                          kort_tittel=kort_tittel,
                          abstract=info,
                          creator=creator,
                          partisipant_description=artist,
                          duration=duration,
                          issued=issued,
                          gluon_type=[{'label':'class', 'reference':'Digas', 'value' : gluon_type}],
                          bilde=bilde
                          )

            dataid, tittel, kort_tittel, artist, komponist, info, bilde, issued, duration, gluon_type = hent_item_next(d, kanal, hovedkanal, musikk=False, news=True)
            if not dataid:
                dataid = sette_dataid(tittel)
            #Sette inn innslags objekt her
            if tittel:
                #Dersom vi ikke har en tittel skal vi ikke ha noe objekt heller
                bilde=bilde_fix(d, bilde, dataid)
                addObject(xmldom, innslag,
                          runorder="future",
                          channel=kanal,
                          sub_elements=False,
                          objecttype="item",
                          dataid=dataid,
                          tittel=tittel,
                          abstract=info,
                          contributor={'V36': artist},
                          duration=duration,
                          issued=issued,
                          gluon_type=[{'label':'class', 'reference':'Digas', 'value' : gluon_type}],
                          bilde=bilde
                          )

            try:
                prog_Id, tittel, info, programleder, issued, duration, digastype = hent_programme_next(d, kanal, hovedkanal)
                if programleder:
                    programleder = {'V40':programleder}
                #Legge inn som objekt
                if tittel:
                    addObject(xmldom, tablePointer,
                              sub_elements=False,
                              objecttype="programme",
                              channel=kanal,
                              dataid=prog_Id,
                              tittel=tittel,
                              abstract=info,
                              contributor=programleder,
                              duration=duration,
                              issued=issued,
                              gluon_type=[{'reference':'NRK-Escort', 'value' : digastype}]
                              )

            except:
                pass

            data = xmldom.toxml('utf-8')
            #pars = xml.dom.minidom.parseString(xmldom.toprettyxml('  ','\n','utf-8'))


            #Hele denne er i en trxad med timeout, vi trenger ikke noe timeout
            if test_modus:
                print(kanal, tittel)
                print()
                print(xmldom.toprettyxml('  ', '\n', 'utf-8'))
                f = open('/Users/n12327/Desktop/filex.xml', 'w')
                f.write(xmldom.toprettyxml('  ', '\n'))
                f.close()
                continue

            #for adr in GLUON_ADR:

            #    if 'OK' in send_data_web(data,adr):
            #        break

    #Lukke databasen
    d.close()

