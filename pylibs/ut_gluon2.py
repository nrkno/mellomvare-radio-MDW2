# -*- coding: utf-8 -*-

"""Tjeneste som skriver data tilbake til gluon
"""

import xml.dom.minidom
import time
import sys
from urllib.request import urlopen
from db_conn import database
from hashlib import md5

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
    c.execute(sql, (kanal))
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
    c.execute(sql, (kanal_id))
    while 1:
        p = c.fetchone()
        if p:
            s.append(p[0])
        else:
            break
    c.close()
    #Dersom denne ender i en null, så har denne kanalen ingen avleggere, ikke en gang seg selv.
    #Derfor legger vi til kanalen selv som det ene punktet i en liste
    if s == []:
        c = d.cursor()
        sql = """SELECT navn FROM kanal WHERE ID =%s LIMIT 1;"""
        s = []
        c.execute(sql, (kanal_id))
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

def hent_programmeinfo(d, kanal, hovedkanal, distriktssending=False, har_distrikter=False, force_distrikt=True):
    """Henter informasjon om programmet som er pÂ lufta, returnerer dette som en tuple. Ved distriktssendinger kan flagget
    for distriktssendinger settes."""
    #Sjekke om programmet er utl¯pt i kanalen
    c = d.cursor()
    sql = """select tittel, beskrivelse, artist, tid FROM iteminfo
    WHERE kanal=%s AND type='programme' AND localid = '1' AND
    UNIX_TIMESTAMP(tid) + lengde >= UNIX_TIMESTAMP(now()) AND not(UNIX_TIMESTAMP(tid)>UNIX_TIMESTAMP(now())) AND
    progId !='DUMMY_PROD_NR'
    LIMIT 1;"""
    #Denne gir og PI sendeflatetype
    c.execute(sql, (kanal,))
    if c.rowcount:
        i_programme = True
        if VERBOSE:
            print("I PROGRAMMET")
    else:
        i_programme = False
        if VERBOSE:
            print("IKKE I PROGRAMMET")

    if i_programme and har_distrikter:
        #Vi har med Â gj¯re en distriktskanal som har eget program, da skal hele dls-en ignoreres. Den skal genereres ut ifra kanalens egen oppkall
        c.close()
        if VERBOSE:
            print('VOID - har eget program')
        return '', '', '', '', '', '', '', '', False, True
        # Sjekke på denne verdien om kanalen skal hoppes over i

    #Vi må sjekke om hovedkanalen har en distriktsflate

    sql = """SELECT digastype FROM iteminfo WHERE kanal=%s AND type='programme' AND localid = '1' LIMIT 1;"""
    #Denne gir og PI sendeflatetype
    c.execute(sql, (hovedkanal,))
    try:
        try:
            digastype, = c.fetchone()
        finally:
            c.close()
    except TypeError:
        digastype = ''
        #Sjekke omo denne egentlig vil kunne feile
    #Finne alternativ mÂte for Â tenne distriktsflagg
    if i_programme and (kanal != hovedkanal):
        #Kanalen har et aktivt program, og den har en mor, dvs hovedkanl er ikke seg selv.
        distriktssending = True
        tittel_sufix = ''

    elif digastype == '50' and (kanal != hovedkanal):
        #Vi har en distriktssending av den gamle typen
        distriktssending = True
        #Vi har ennÂ ikke distriktsvise programme info
        #Vi henter f¯rst ut navnet "Brandet" pÂ kanalen
        c = d.cursor()

        sql = """SELECT branding FROM kanal WHERE navn=%s LIMIT 1;"""
        c.execute(sql, (kanal,))
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
        if force_distrikt and i_programme:
            #Vi bytter ikke kanaler, men stryker sufix
            tittel_sufix = ''
        else:
            kanal = hovedkanal
            tittel_sufix = ''

    c = d.cursor()
    sql = """SELECT tittel, progId, beskrivelse, artist, tid, lengde, digastype, nettype FROM iteminfo WHERE kanal=%s AND type='programme' AND localid = '1' LIMIT 1;"""

    c.execute(sql, (kanal,))
    try:
        try:
            tittel, prog_Id, beskrivelse, artist, sendetid, lengde, digastype, nettype = c.fetchone()
        finally:
            c.close()
    except TypeError:
        #Dersom vi ikke har noe her, kan det hende det er en distriktskanal som ikke har egne metadata
        if hovedkanal and not distriktssending:
            return hent_programmeinfo(d, hovedkanal, None)
        else:
            return '', '', '', '', '', '', '', '', False, False

    sendetid = sendetid.isoformat()
    tittel = tittel + tittel_sufix #Legger på f. eks. "fra NRK Trøndelag" på dirstriksflater
    return prog_Id, tittel, beskrivelse, artist, sendetid, int(lengde), digastype, nettype, distriktssending, False

def hent_programme_next(d, kanal, hovedkanal, distriktssending=False):
    "Henter informasjon om det neste programmet som skal på lufta, returnerer en liste med et element."
    c = d.cursor()
    sql = """SELECT tittel, progId, beskrivelse, artist, tid, lengde, digastype FROM iteminfo WHERE kanal=%s AND type='programme' AND localid = '2' LIMIT 1;"""

    c.execute(sql, (kanal, ))
    try:
        try:
            tittel, prog_Id, beskrivelse, artist, tid, lengde, digastype = c.fetchone()
        finally:
            c.close()
    except TypeError:
        if hovedkanal and not distriktssending:
            return hent_programme_next(d, hovedkanal, None)
        else:
            return '', '', '', '', '', '', ''
    tid = tid.isoformat()
    return prog_Id, tittel, beskrivelse, artist, tid, int(lengde), digastype

def hent_iteminfo_forrige(d, kanal, hovedkanal, distriktssending=False, item=False, info=False):
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

    sql = """SELECT progId, tittel, ExtractValue(element, 'element/metadata_DC/titles/title'), artist,  ExtractValue(element, 'element/metadata_DC/creators/creator[role="Composer"]/family_name'), beskrivelse, digastype, bildeID, tid, lengde FROM iteminfo WHERE kanal=%s AND type='item'  AND localid = '5' LIMIT 1 ;"""

    c.execute(sql, (kanal,))
    try:
        try:
            dataid, tittel, kort_tittel, artist, komponist, album, digastype, bilde, tid, lengde = c.fetchone()
        finally:
            c.close()
    except TypeError:
        if hovedkanal and not distriktssending:
            return hent_iteminfo_forrige(d, hovedkanal, None)
        return '', '', '', '', '', '', '', '', '', '', ''

    tid = tid.isoformat()

    #Artist feltet må endres litt
    if artist:
        artist = artist.replace('|', ' ')
        artist = artist.lstrip('. ')
        artist = artist[0].upper() + artist[1:]

    # Sammenslåing av news og musik utrekk
    if digastype == 'Music':
        medvirkende = ''
    else:
        medvirkende = artist
        artist = ''

    #Vi finner opptaksdato
    c = d.cursor()
    sql = """SELECT YEAR(laget) FROM iteminfo WHERE kanal=%s AND type='item' AND localid = '5' LIMIT 1 ;"""
    c.execute(sql, (kanal,))
    try:
        try:
            laget, = c.fetchone()
        finally:
            c.close()
    except:
        laget = 0
    else:
        if laget<LAGET_GRENSE:
            tittel = "%s, innspilt %s," % (tittel,laget)

    return dataid, tittel, kort_tittel, artist, medvirkende, komponist, album, bilde, tid, int(lengde), digastype

def hent_iteminfo(d, kanal, hovedkanal, distriktssending=False):
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
            return hent_iteminfo(d, hovedkanal, None)

        return '', '', '', '', '', '', '', '', '', '', '', ''

    tid = tid.isoformat()
    #Artist feltet må endres litt
    if artist:
        artist = artist.replace('|', ' ')
        artist = artist.lstrip('. ')
        artist = artist[0].upper() + artist[1:]
    if digastype == 'Music':
        medvirkende = ''
    else:
        medvirkende = artist
        artist = ''

    #Vi finner opptaksdato
    c = d.cursor()
    sql = """SELECT YEAR(laget) FROM iteminfo WHERE kanal=%s AND type='item'  AND localid = '3' LIMIT 1 ;"""
    c.execute(sql, (kanal,))
    try:
        try:
            laget, = c.fetchone()
        finally:
            c.close()
    except:
        laget = 0
    else:
        if laget < LAGET_GRENSE:
            tittel = "%s, innspilt %s," % (tittel, laget)

    return dataid, tittel, kort_tittel, artist, artist_short, medvirkende, komponist, album, bilde, tid, int(lengde), digastype

def hent_item_next(d, kanal, hovedkanal, distriktssending=False):
    "Henter informasjon om det neste innslaget som skal på lufta, returnerer en liste med et element."
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

    #Ellers viser vi nesteinformasjon
    sql = """SELECT progId, tittel, ExtractValue(element, 'element/metadata_DC/titles/title'),
     artist,  ExtractValue(element, 'element/metadata_DC/creators/creator[role="Composer"]/family_name'),
      beskrivelse, digastype, bildeID, tid, lengde FROM iteminfo WHERE kanal=%s AND type='item' AND localid = '4' LIMIT 1;"""
    c.execute(sql, (kanal, ))
    try:
        try:
            dataid, tittel, kort_tittel, artist, komponist, beskrivelse, digastype, bilde, tid, lengde = c.fetchone()
        finally:
            c.close()
    except TypeError:
        if hovedkanal and not distriktssending:
            return hent_item_next(d, hovedkanal, None)
        return '', '', '', '', '', '', '', '', '', '', ''

    tid = tid.isoformat()
    #Artist feltet må endres litt
    if artist:
        artist = artist.replace('|', ' ')
        artist = artist.lstrip('. ')
        artist = artist[0].upper() + artist[1:]
    if digastype == 'Music':
        medvirkende = ''
    else:
        medvirkende = artist
        artist = ''

    return dataid, tittel, kort_tittel, artist, medvirkende, komponist, beskrivelse, bilde, tid, int(lengde), digastype

def send_data_web(data,uri, svar_fra_mottager = True):
    "Sender inn til gluon"
    # TODO: Bytt denne til noe enklere
    headers = {"Content-type": "application/xml",
        "Accept": "*/*",
        "User-Agent":"MDW 1.0 [no] (%s; U)"%sys.platform}
    #Splitte protokoll og uri
    protokol, uri = uri.split(':', 1)
    uri = uri.lstrip('/')
    #Dele opp uri til hostname og url
    host, url = uri.split('/', 1)

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
            svar = 'Sendt'
        conn.close()
    return svar

def return_timezone():
    "Legger på timezone sufix"
    if time.localtime()[8]:
        return '+02:00'
    return '+01:00'

def lag_gluon(art_id="test"):
    "Lager et gluon rotdokument, og returnerer dette og en pointer til stedet hvor elementene skal inn"
    impl = xml.dom.minidom.getDOMImplementation()
    utdok = impl.createDocument('http://www.w3.org/2001/XMLSchema', 'gluon', None)
    utdok.documentElement.setAttribute('priority', '3')
    utdok.documentElement.setAttribute('artID', art_id)
    utdok.documentElement.setAttribute('xmlns', "http://gluon.nrk.no/gluon2")
    utdok.documentElement.setAttribute('xmlns:gluonDict', "http://gluon.nrk.no/gluonDict")
    utdok.documentElement.setAttribute('xmlns:xsi', "http://www.w3.org/2001/XMLSchema-instance")
    utdok.documentElement.setAttribute('xsi:schemaLocation', "http://gluon.nrk.no/gluon2 http://gluon.nrk.no/gluon2.xsd")
    #head
    metadata = utdok.documentElement.appendChild(utdok.createElement('head')).appendChild(utdok.createElement('metadata'))
    navn = metadata.appendChild(utdok.createElement('creators')).appendChild(utdok.createElement('creator')).appendChild(utdok.createElement('name'))
    navn.setAttribute('person', 'false')
    navn.appendChild(utdok.createTextNode('MDW:gluon2'))
    metadata.appendChild(utdok.createElement('dates')).appendChild(
                         utdok.createElement('dateIssued')).appendChild(utdok.createTextNode(
                         time.strftime("%Y-%m-%dT%H:%M:%S") + return_timezone()))
    #body
    tables = utdok.documentElement.appendChild(utdok.createElement('objects'))

    return utdok, tables

def sette_dataid(tittel):
    "Fattigmans id generator"
    m = md5(tittel.encode('utf-8'))
    return 'MDW:%s' % m.hexdigest()

def add_name(utdok, tag, roleId='', name=''):
    "Legger på en gluon navnetype"
    famname = tag.appendChild(utdok.createElement('name'))
    famname.appendChild(utdok.createTextNode(name))
    role_tag = tag.appendChild(utdok.createElement('role'))
    if roleId:
        role_tag.setAttribute('link', 'http://gluon.nrk.no/nrkRoller.xml#' + roleId)

def add_object(utdok, pointer,
               sub_elements=False,
               objecttype='',
               subjects='',
               dataid='',
               channel='',
               runorder='',
               tittel='',
               kort_tittel='',
               creator='',
               abstract='',
               partisipant_description='',
               partisipant_short_description='',
               contributor='',
               gluon_type='',
               issued='',
               duration='',
               bilde=''
               ):
    "Legger på et element til et objekttre, returnerer en peker til subelement-elementet"
    #Ordne elementet
    if not dataid:
        dataid = "noID"
    channel = channel.replace('ko ', 'ko_')#lex toten
    element = pointer.appendChild(utdok.createElement('object'))
    element.setAttribute('objecttype', objecttype)
    element.setAttribute('dataid', dataid)
    element.setAttribute('channel', channel)
    if runorder:
        element.setAttribute('runorder', runorder)
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
            tittel_alternat_2 = titler.appendChild(utdok.createElement('titleAlternative'))
            tittel_alternat_2.appendChild(utdok.createTextNode(publishing_title))
            tittel_alternat_2.setAttribute('gluonDict:titlesGroupType', 'publishingTitle')

        if kort_tittel:
            titAlt = titler.appendChild(utdok.createElement('titleAlternative'))
            titAlt.appendChild(utdok.createTextNode(kort_tittel))
            titAlt.setAttribute('gluonDict:titlesGroupType', 'intellectualWorkTitle')

    if creator:
        if isinstance(creator, dict):
            creators = metadata.appendChild(utdok.createElement('creators'))
            for role in creator:
                navnene = creator[role]
                if isinstance(navnene, list):
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
        old_ref = relations.appendChild(utdok.createElement('relationReferences'))
        old_ref.setAttribute('label', 'illustration')
        old_ref.setAttribute('reference', 'DMA')
        old_ref.appendChild(utdok.createTextNode(bilde))
        bilde_rel = relations.appendChild(utdok.createElement('relationIsDescribedBy'))
        bilde_rel.setAttribute('reference', 'DMA')
        bilde_rel.appendChild(utdok.createTextNode(bilde))
    if sub_elements:
        return element.appendChild(utdok.createElement('subelements'))
    return None

def lag_metadata(kanal='alle', test_modus=False):
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
            #Vi har kunn en kanal, distrikskanal eller kanalen selv, vi må finne moderkanalen
            hovedkanal = finn_hovedkanal(d, kanal)
            har_distrikter = False
        else:
            #Vi har en kanal med barn, ergo er hovedkanalen kanalen selv.
            hovedkanal = kanal
            har_distrikter = True

        for kanal in distriktskanaler:
            #Lage nytt dokument
            xmldom, tablePointer = lag_gluon(art_id="iteminfo_NRK_%s" % kanal)

            # Hente programinfo, data om sendingen
            prog_Id, tittel, info, programleder, issued, duration, digastype, nettype, distriktssending, egenKanal = hent_programmeinfo(d, kanal, hovedkanal, har_distrikter=har_distrikter)
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
            innslag = add_object(xmldom, tablePointer,
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
            dataid, tittel, kort_tittel, artist, medvirkende, komponist, info, bilde, issued, duration, gluon_type = hent_iteminfo_forrige(
                                                                d, kanal, hovedkanal, distriktssending=distriktssending)
            if not dataid:
                dataid = sette_dataid(tittel)
            if not komponist:
                creator = ''
            else:
                creator = {'V34':komponist}
            if medvirkende:
                medvirkende = {'V36':medvirkende}
            bilde = bilde_fix(d, bilde, dataid)
            if tittel:
                #Dersom vi ikke har en tittel skal vi ikke ha noe objekt heller
                add_object(xmldom, innslag,
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
                           contributor=medvirkende,
                           duration=duration,
                           issued=issued,
                           gluon_type=[{'label':'class', 'reference':'Digas', 'value' : gluon_type}],
                           bilde=bilde
                           )

            #På lufta nå
            dataid, tittel, kort_tittel, artist, artist_short, medvirkende, komponist, info, bilde, issued, duration, gluon_type = hent_iteminfo(d, kanal, hovedkanal, distriktssending=distriktssending)
            if not dataid:
                dataid = sette_dataid(tittel)
            if not komponist:
                creator = ''
            else:
                creator = {'V34':komponist}
            if medvirkende:
                medvirkende = {'V36':medvirkende}
            if tittel:
                #Dersom vi ikke har en tittel skal vi ikke ha noe objekt heller
                bilde = bilde_fix(d, bilde, dataid)
                add_object(xmldom, innslag,
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
                           contributor=medvirkende,
                           partisipant_short_description=artist_short,
                           duration=duration,
                           issued=issued,
                           gluon_type=[{'label':'class', 'reference':'Digas', 'value' : gluon_type}],
                           bilde=bilde
                           )

            #Hente neste inslagsinfo
            dataid, tittel, kort_tittel, artist, medvirkende, komponist, info, bilde, issued, duration, gluon_type = hent_item_next(d, kanal, hovedkanal)
            if not dataid:
                dataid = sette_dataid(tittel)
            if not komponist:
                creator = ''
            else:
                creator = {'V34':komponist}
            if medvirkende:
                medvirkende = {'V36':medvirkende}
            if tittel:
                #Dersom vi ikke har en tittel skal vi ikke ha noe objekt heller
                bilde = bilde_fix(d, bilde, dataid)
                add_object(xmldom, innslag,
                           runorder="future",
                           channel=kanal,
                           sub_elements=False,
                           objecttype="item",
                           dataid=dataid,
                           tittel=tittel,
                           kort_tittel=kort_tittel,
                           abstract=info,
                           creator=creator,
                           contributor=medvirkende,
                           partisipant_description=artist,
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
                    add_object(xmldom, tablePointer,
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


            if test_modus:
                print(kanal, tittel)
                print()
                print(xmldom.toprettyxml('  ', '\n', 'utf-8'))
                f = open('/Users/n12327/Desktop/filex.xml', 'w')
                f.write(xmldom.toprettyxml('  ', '\n'))
                f.close()
                continue

            for adr in GLUON_ADR:
                assert (urlopen(adr, data=data, timeout=5).status) == 200
    #Lukke databasen
    d.close()
