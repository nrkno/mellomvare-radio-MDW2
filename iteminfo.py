# -*- coding: utf-8 -*-
"""iteminfo tjenester
Versjon som sjekker lengden på programmet utifra avstanden i sendetid mellom program 1 og 2, dersom
programtiden oppgis til å være null"""

import re
import time
import xml.dom.minidom
from random import choice

import pymysql as mdb

from db_conn import database

from roller import rolleliste, rollerelasjon, ikkeRolle

KANAL_NAVN = {'nrk jazz':'jazz', 'nrk sport':'sport', 'sport':'sport', 'nrk gull':'gull',
              'nrk p1pluss':'p1pluss', 'nrk barn':'barn', 'p1_ndst':'p1st', 'nrk p1':'p1', 'p1':'p1', 'nrk p2':'p2', 'p2':'p2',
              'nrk p3':'p3', 'petre':'p3', 'nrk petre':'p3', 'p3':'p3', 'nrk ak':'ak', 'alltid klassisk':'ak', 'ak':'ak',
              'nrk mpetre':'mpetre', 'mpetre':'mpetre', 'nrk alltid nyheter':'an', 'nrk an':'an', 'an':'an',
              'nrk alltid folkemusikk':'fmk', 'fmk':'fmk', 'p3urort':'urort', 'urort':'urort',
              'nrk p1 oslofjord':'p1of', 'p1of':'p1of', 'sami dab':'sami', 'lzu':'sami'}
FJERNSYN = ['nrk 1', 'nrk 2', 'nrk 3_super']
VERBOSE = False
LOGGING_ITEM = False

FJERNROLLERFOR = ['Conductor', 'Leader']
DIRIGERT = [' under ledelse av ', ' DIRIGERT av ', ', dirigent ']
LEDET = ['LEDET av']

ORD_SOM_IKKE_BESKRIVER = ['fortsetter', 'samsending', 'også sendt i går']

EGEN_PROD = 'EBU-NONRK' # Label for EGEN_PRODuksjon

def sjekk_program_lengde(d, kanal):
    "Sjekker om programmet som er på lufta nå, har fått lengde 0, i så fall rettes den til tiden frem til neste program. Har ingen definert returverdi."
    #Sjekk programme lengde
    c = d.cursor()
    sql = """SELECT lengde FROM iteminfo WHERE kanal=%s and localid = 1;"""
    c.execute(sql, (kanal))
    try:
        lengde = int(c.fetchone()[0])
    except TypeError:
        lengde = 0
    except ValueError:
        lengde = 0
    #Dersom lengden ikke er null nå kan vi returnere uten å gjøre noe mer
    if lengde != 0:
        c.close()
        return
    #Hvis ikke for vi finne lengden
    sql = """select
             MAX(UNIX_TIMESTAMP(tid)) - MIN(UNIX_TIMESTAMP(tid))
             FROM iteminfo WHERE kanal = %s; """
    c.execute(sql, (kanal))
    try:
        beregnet_lengde = int(c.fetchone()[0])
    except TypeError:
        beregnet_lengde = 0
    except ValueError:
        beregnet_lengde = 0
    #Hvis lengden er null nå også er vi like kloke og må returnere
    if beregnet_lengde == 0:
        c.close()
        return
    sql = """UPDATE iteminfo SET
                    lengde=%s
                    WHERE kanal=%s and localid = 1;"""
    c.execute(sql, (beregnet_lengde, kanal))
    c.close()
    if VERBOSE:
        print("Rettet lengde på programm", lengde, beregnet_lengde)

def flush_program_data(d, kanal):
    "Renserutine for programskift"
    #1 Stryk innslag/neste program
    c2 = d.cursor()
    sql = """DELETE FROM iteminfo
    WHERE kanal=%s and localid !=0;"""
    c2.execute(sql, (kanal))

    # Stryk ev textinfo på programmnivå (eller lavere)
    sql = """DELETE FROM textinfo
    WHERE kanal=%s and type = 'programme';"""
    c2.execute(sql, (kanal))
    c2.close()

def iso_til_lengde(isoTid):
    "Leser en iso lengde og setter om til sekunder"
    tid = 0.0
    #Split dager fra timer
    dager, timer = isoTid[1:].split('T')
    #Finn sekunder osv.
    p = re.search(r'(\d+|\d+\.\d+)S', timer)
    if p:
        tid += float(p.group(1))
    p = re.search(r'(\d+|\d+\.\d+)M', timer)
    if p:
        tid += float(p.group(1)) * 60
    p = re.search(r'(\d+|\d+\.\d+)H', timer)
    if p:
        tid += float(p.group(1)) * 3600
    # dager o.l.
    p = re.search(r'(\d+|\d+\.\d+)D', dager)
    if p:
        tid += float(p.group(1)) * 3600 * 24
    p = re.search(r'(\d+|\d+\.\d+)M', dager)
    if p:
        tid += float(p.group(1)) * 3600 * 24 * 30
    p = re.search(r'(\d+|\d+\.\d+)Y', dager)
    if p:
        tid += float(p.group(1)) * 3600 * 24 * 365
    return tid

def iso_til_dato(dato, sekunder=False, sql=False):
    "Tar en datostreng og gjør om til et tidsobjekt"
    #TODO: Hva brukes egentlig denne til
    offsett = 0
    if not dato:
        return 0
    dato = dato.isoformat()
    if 'T' in dato or sql:
        aar = int(dato[0:4])
        if aar < 1970:
            #Da har vi et problem
            aar = aar + 60
            offsett = 1893456000.0
        try:
            if sekunder:
                tid = time.mktime((aar, int(dato[5:7]), int(dato[8:10]), int(dato[11:13]), int(dato[14:16]),
                                   int(dato[17:19]), -1, -1, -1))
            else:
                tid = time.mktime((aar, int(dato[5:7]), int(dato[8:10]), int(dato[11:13]), int(dato[14:16]),
                                   0, -1, -1, -1))
        except ValueError:
            tid = 0
    else:
        try:
            tid = int(dato)
        except:
            tid = 0
    return tid - offsett

def finn_unger(noder, tag, kun_en=False):
    "Kryper et lag ned i eet nodetre"
    nodeliste = []
    for node in noder:
        if node.nodeType == node.ELEMENT_NODE:
            if node.tagName == tag:
                nodeliste.append(node)
                if kun_en:
                    return nodeliste
    return nodeliste

def hent_verdier(noder, lim=''):
    "Henter ut tekstnoder fra et nodetre"
    text_nodes = ''
    for node in noder:
        if node.nodeType == node.TEXT_NODE:
            text_nodes += node.data + lim
        text_nodes.replace('\u2019', "'")
    return text_nodes

def finn_verdi(xmlobjekt, path, entity=False, nodetre=False):
    "Henter en serie av noder på grunnlag av et xpath lignende utrykk"
    #path til nodeliste
    nodeliste = path.split('/')
    try:
        for node in nodeliste:
            if node == '':
                continue
            if not node.startswith('@'):
                if  node.startswith('+') and nodetre is True:
                    xmlobjekt = finn_unger(xmlobjekt.childNodes, node[1:], kun_en=False)
                    #Siden dette kun er gyldig i siste node:
                    break
                    #Så fortsetter vi under
                else:
                    xmlobjekt = finn_unger(xmlobjekt.childNodes, node, kun_en=True)[0]
            else:
                #returnere attributverdi
                return xmlobjekt.getAttribute(node[1:])
    except IndexError:
        if nodetre:
            return []
        else:
            return ''
    if nodetre:
        return xmlobjekt
    if not entity:
        return hent_verdier(xmlobjekt.childNodes)
    else:
        return entety_replace(hent_verdier(xmlobjekt.childNodes))

def entety_replace(streng):
    return streng.replace('&amp;', '&')

def samsendinglexer(setning):
    "Finner og forstår variasjoner over setningen: 'I sammmesending med kulturkanalen'"
    stoppord = ['den', 'det', 'den', 'med', 'for', 'i']
    pynt = ['radioens', 'fjernsynets', 'tvens', 'NRK']
    samsendingsbegreper = ['sammsending', 'samssending', 'samsending', 'sams']
    samsending = False
    for enkeltord in setning.split():
        if enkeltord.lower() in stoppord:
            continue
        if enkeltord.lower() in pynt:
            continue
        if enkeltord.lower() in samsendingsbegreper:
            samsending = True
            continue
        #I og med at vi tar bort alle stoppord og pynt er det neste som kommer nå kanalbetegnelsen
        # TODO bruke kanal SW til å bekrefte kanal
        if samsending:
            return enkeltord

def finn_kildekanal(d, beskrivelse):
    "Returnerer kanalkode dersom vi detekterer i beskrivelsen at vi har en samsending ellers returnerer den None, dvs ingen samsending"
    #Dele opp beskrivelsen i setninger, så analysere disse.
    #Vi deler på punktum
    if '.' in beskrivelse:
        setninger = beskrivelse.split('.')
    else:
        setninger = [beskrivelse]
    if len(setninger) > 1:
        #Vi har mer en en en setning, og punktum, men disse punktummene kan skyldes forkortelser.
        setninger2 = []
        flush = False
        for setnum, setning in enumerate(setninger):
            if flush:
                flush = False
                continue #Slik at vi hopper over setningen som er lagt til - mÃ¥ slettes
            if (setnum +1) < len(setninger):
                #Vi har minst en setning til
                neste_setning = setninger[setnum + 1].lstrip()
                if neste_setning:
                    if neste_setning[0].isupper():
                        #Neste starter med stor forbokstav, det er sansynlig at dette er en ny setning
                        setninger2.append(setning)
                        flush = False
                        continue
                    else:
                        # Vi har en forkortelse
                        setninger2.append(setning + '.' + setninger[setnum + 1])
                        flush = True
                setninger2.append(setning)
            else:
                #Dette er siste setning som bare skal legges til
                setninger2.append(setning)
        setninger = setninger2

    for setning in setninger:
        kanaltoken = samsendinglexer(setning)
        if kanaltoken:
            break # TODO: Bedre sikringen at det er et kanalnavn vi finner

    c1 = d.cursor()
    sql = """SELECT navn FROM kanal
    WHERE alias=%s or navn=%s;"""
    c1.execute(sql, (kanaltoken, kanaltoken))

    result = c1.fetchone()
    if result:
        return result[0]
    else:
        return None

def begrens(tekst, lengde=128):
    "Prøver å begrense en streng ved et punktum."
    if "." in tekst:
        s = ''
        for setning in  tekst.split('.'):
            if len(s) + len(setning) + 1 <= lengde:
                s += setning + '.'
            else:
                break
        return s

    return tekst[:128]

def tell_artister(artister):
    "Teller antall artister ved å gå gjennom alle rollene"
    artist_ant = 0
    for rolle in artister:
        artist_ant += len(artister[rolle])
    return artist_ant

def lag_artistfelt(artister, solister=False):
    "Lager deler eller hele artistfeltet, kan kalles flere ganger"
    artistfelt = ''
    artisttall = tell_artister(artister)
    if solister:
        if artisttall == 1:
            solistfelt = " er solist "
        else:
            solistfelt = " er solister"
    else:
        solistfelt = ''
    if artisttall == 1:
        if 'Utøver' in artister:
            if solister:
                return '. ' + artister['Utøver'][0][0].upper() + (artister['Utøver'][0] + solistfelt)[1:]
            return artister['Utøver'][0]

        elif artister.keys()[0] in rolleliste:
            rolle = artister.keys()[0]
            if rolle in ikkeRolle:
                if solister:
                    return '. ' + artister[rolle][0][0].upper() + (artister[rolle][0] + ' på ' + rolle + solistfelt)[1:]
                return artister[rolle][0] + ' på ' + rolle
            else:
                if solister:
                    return '. ' + rolleliste[rolle]['tittel'][0].upper() + (rolleliste[rolle]['tittel'] + ' ' + artister[rolle][0] + solistfelt)[1:]
                return rolleliste[rolle]['tittel'] + ' ' + artister[rolle][0]
        else:
            #Vi finner ikke rollen, dette viol normali ikke skje, vi retunerer da bare navnene
            return artister[artister.keys()[0]][0]

    elif artisttall == 2 and not solister:
        #Finne forholdet mellom roller, dersom det er solister vi skal bare liste opp. Noen roller er underordnet andre
        if 'Utøver' in artister:
            # Da må vi gjøre noe spesielt, da kan det fremdeles være (rolle)
            if len(artister) == 1:
                #Vi har to ukjente roller og kan gjøre det enkelt.
                return artistfelt + ' og '.join(artister['Utøver'])
            else:
                #Vi har en ukjent og en kjent, for å få dette pent setter vi rollen over i () igjen. Fram og tilbake er like langt.
                i, j = artister.keys()
                if j == 'Utøver':
                    #SWAP, dette gir oss den 'eksotiske' først.
                    i, j = j, i
                return artistfelt + artister[i][0] + ' og ' + artister[j][0] + ' (' + j + ')'

        #Så derspm vi bare har kjente artister
        if len(artister) == 1:
            i, = artister.keys()
            #Dersom disse er like -> vi bruker og, og har rollen i flertall
            return rolleliste[i]['tittel'] + 'e ' + ' og '.join(artister[i]) + solistfelt
        #Så sjekke gruppene og relasjonene mellom disse
        i, j = artister.keys()
        ir = rollerelasjon[rolleliste[i]['gruppe']]
        jr = rollerelasjon[rolleliste[j]['gruppe']]
        #Sjekke slik at mest dominerende gruppe kommer først
        if jr > ir:
            #swap
            i, ir, j, jr = j, jr, i, ir
        # if rolle in ikkeRolle:
        artistfelt += rolleliste[i]['tittel'] + ' ' + artister[i][0]

        #Finne konjuksjon
        if ir == jr or jr != 0:
            #Vi bruker og...
            return artistfelt + ' og ' + rolleliste[j]['tittel'] + ' ' + artister[j][0] + solistfelt
        #Vi bruker passiv form
        return artistfelt + ' ' + rolleliste[j]['passiv'] + ' ' + rolleliste[j]['tittel'] + ' ' + artister[j][0] + solistfelt


    while 1:
        rolle, navneliste = artister.popitem()
        if rolle != "Utøver":
            if len(navneliste) != 1:
                artistfelt += rolleliste[rolle]['tittel'] + 'e ' + ', '.join(navneliste)
            else:
                artistfelt += rolleliste[rolle]['tittel'] + ' ' + ', '.join(navneliste)
        else:
            artistfelt += ', '.join(navneliste)
        if not artister:
            break
        if len(artister) > 1:
            artistfelt += ', '
        else:
            artistfelt += ' og '
    if solister:
        return '. ' + artistfelt[0].upper() + (artistfelt + solistfelt)[1:]
    return artistfelt + solistfelt

#TODO: Forsett her
def finn_komponist(element, kun_etternavn=False, aars_tall=False):
    creators = element.getElementsByTagName('creator')
    for creator in creators:
        role = finn_verdi(creator, 'role', entity=False)
        if role.lower() == "composer" or role.lower() == "komponist":
            komponist_fornavn = finn_verdi(creator, 'given_name', entity=True)
            komponist = finn_verdi(creator, 'family_name', entity=True)
            if kun_etternavn:
                if komponist_fornavn:
                    #Da er dette av rik datatype og vi kan sende etternavnet
                    return komponist

                #Finne etternavnet, fjerne paranteser
                try:
                    return komponist.split('(')[0].rstrip().split().pop()
                except:
                    return ""
            else:
                if komponist_fornavn:
                    if aars_tall:
                        #Da er dette av rik datatype og vi kan sende etternavnet
                        return "%s %s"  % (komponist_fornavn, komponist)
                    return "%s %s"  % (komponist_fornavn.split('(')[0].rstrip(), komponist.split('(')[0].rstrip())
                if aars_tall:
                    return komponist
                return komponist.split('(')[0].rstrip()

def finn_medvirkende(element, klasse=''):
    contributor_list = {}
    soloist_list = {}

    metadata = finn_unger(element.childNodes, "metadata_DC", kun_en=True)[0]
    contributors = metadata.getElementsByTagName('contributor')
    for contributor in contributors:
        solist = False
        #Finne rolle bruke denne som key
        role = finn_verdi(contributor, 'role', entity=False)
        #Fiks for tvilsommedata
        if klasse != 'News' and role == 'Reporter':
            continue
        if not role:
            role = 'contributor'
        fornavn = finn_verdi(contributor, 'given_name', entity=True)
        navn = finn_verdi(contributor, 'family_name', entity=True)
        if not navn:
            continue

        #Flytte parantes
        if '(' in fornavn:
            #flytte parantes til etternavn
            fornavn, parantes = fornavn.split('(',1)
            navn = "%s (%s)" % (navn, parantes.rstrip(')'))
            #Trimme fornavn
            fornavn = fornavn.strip()
        #Dersom rollen er 'Orchestra' og navnet inneholder en '(' da kan vi sjekke om vi skal endre rollen
        #Dette skyldes AK sin misbruk av databasen sin, dette kan fjernes etterhvert.
        if role == 'Orchestra':

            try:
                nyrolle = navn.split('(')[1].rstrip(')')
            except:
                nyrolle = False
            if nyrolle in rolleliste:
                #Rettes til if nyrollen er i dab rollelisten

                role = nyrolle
                navn = navn.split('(')[0].rstrip()
            else:
                #Vi beholder rollen og beholde parantes
                pass
        if role == 'Choir':
            try:
                nyrolle = navn.split('(')[1].rstrip(')')
            except:
                nyrolle = False
            if nyrolle in rolleliste:
                #Rettes til if nyrollen er i dab rollelisten
                role = nyrolle
                navn = navn.split('(')[0].rstrip()
            else:
                #Vi beholder rollen og parantes
                pass
        #Fjerne rolleparanteser
        #Dersom rollen er 'Performer' og navnet inneholder en '(' da kan vi sjekke om vi skal endre rollen
        if role == 'Performer':
            try:
                nyrolle = navn.split('(')[1].rstrip(')')
                if ',' in nyrolle:
                    nyrolle = nyrolle.split(',')[0].rstrip()
            except:
                nyrolle = False
            if nyrolle in rolleliste:
                #Rettes til if nyrollen er i dab rollelisten
                role = nyrolle
                navn = navn.split('(')[0].rstrip()
            else:
                #Vi må skifte rolle og beholde parantes
                role="Utøver"

        #Vi gjør samme øvelsen med Conductor:
        #Dette skyldes AK sin misbruk av databasen sin, dette kan fjernes etterhvert, gjelder ikke Digas dataene.
        if role == 'Conductor':
            try:
                nyrolle = navn.split('(')[1].rstrip(')')
                if ',' in nyrolle:
                    nyrolle = nyrolle.split(',')[0].rstrip()
            except:
                nyrolle = False
            if nyrolle in rolleliste:
                #Rettes til if nyrollen er i dab rollelisten
                role = nyrolle
                navn = navn.split('(')[0].rstrip()
            else:
                #Vi kan ha en orkesterleder som ikk er dirigent, f. eks "Steh'geiger"
                if nyrolle in ('leder', 'Leder'):
                    role = "Leader"
                    navn = navn.split('(')[0].rstrip()
        if role == 'Soloist':
            try:
                nyrolle = navn.split('(')[1].rstrip(')')
                if ',' in nyrolle:
                    nyrolle = nyrolle.split(',')[0].rstrip()
            except:
                nyrolle = False
            if nyrolle in rolleliste:
                #Rettes til if nyrollen er i dab rollelisten
                role = nyrolle
                navn = navn.split('(')[0].rstrip()

            solist = True
        #Fjerne rolleparanteser
        if role in FJERNROLLERFOR:
            navn = navn.split('(')[0].rstrip()

        if solist:
            if fornavn:
                if role in soloist_list:
                    soloist_list[role] = soloist_list[role].append(fornavn + ' ' + navn)
                else:
                    soloist_list[role] = [fornavn + ' ' + navn]
            else:
                if role in contributor_list:
                    soloist_list[role].append(navn)
                else:
                    soloist_list[role] = [navn]
        else:

            if fornavn:
                if role in contributor_list:
                    contributor_list[role] = contributor_list[role].append(fornavn + ' ' + navn)
                else:
                    contributor_list[role] = [fornavn + ' ' + navn]
            else:
                if role in contributor_list:
                    contributor_list[role].append(navn)
                else:
                    contributor_list[role] = [navn]

    return contributor_list, soloist_list

def parser(xmlstreng):
    "Parser et XML-dokument og legger innholdet inn i databasen."
    status = 0
    flush_items = 0
    #Lager en database forbindelse
    d = database()
    pars = xml.dom.minidom.parseString(xmlstreng)
    tabeller = pars.getElementsByTagName('tables')
    for tabell in tabeller:
        if tabell.getAttribute('type') != 'iteminfo':
            continue

        kanal = finn_verdi(tabell, 'element/@channel')
        #Rette kanalnavn
        if kanal.lower() in KANAL_NAVN:
            kanal = KANAL_NAVN[kanal.lower()].lower()
        else:
            kanal = kanal.lower()
        #Fjerne NRK fra kanlnavn
        if kanal.startswith('nrk ') and not kanal in FJERNSYN:
            kanal = kanal.split(' ')[1]
        #Rette kanalnavn for ev kanaler
        if '-' in kanal:
            kanal, label = kanal.split('-')

        if pars.documentElement.getAttribute('priority') == '0':

            return {'status':2, 'kanal':kanal, 'datatype':'iteminfo'}

        elementer = tabell.getElementsByTagName("element")
        sending_programme = 0
        rydd = [1, 2, 3, 4, 5]
        localids = [1, 2, 3, 4, 5]
        stryk = []
        #Opdatere db
        localid = 0
        digastype = ''
        for element in elementer[:4]:
            # Vil aldri inneholde mer enn 4 elementer, som oftest mindre
            # Dersom dette er av den nye Digastypen, så vil vi ha et runorder parameter som viser om dette er
            # past, present eller future.
            # Past hopper vi foreløpig over, dette er mer nyttig i statistikksammenheng, da dette vil være det som er
            # Riktig spilletid på innslaget.

            runorder = finn_verdi(element, '@runorder', entity=False)

            xml_element = element.toxml()

            #Finne tekniske parametre

            elementtype = finn_verdi(element, '@objecttype', entity=False)
            if elementtype == 'programme':
                sending_programme += 1
                localprogid = 0
                localid = sending_programme
            if elementtype == 'item':
                if runorder == 'present':
                    localprogid = sending_programme
                    localid = 3
                    # present
                elif runorder == 'future':
                    localprogid = sending_programme
                    localid = 4
                    # future
                elif runorder == 'future1':
                    localprogid = sending_programme
                    localid = 4
                    # future 1
                elif runorder == 'past':
                    localprogid = 0 #Vil altid tilordnes det lopende programmet
                    localid = 5

            #Dette gir oss rekefølgen programme,programme,item,item,item(past)

            detaljering = finn_verdi(element, '@type', entity=False)
            # Dersom det er summary skal vi ikke ta hensyn til at det er et nytt program
            dataid = finn_verdi(element, '@dataid', entity=False)

            #Tittel
            tittel = finn_verdi(element, 'metadata_DC/titles/title', entity=False)
            plateselskap = finn_verdi(element, 'metadata_DC/source/@label', entity=False)
            platenummer = finn_verdi(element, 'metadata_DC/source/@reference', entity=False)
            if plateselskap:
                label = plateselskap + ':' + platenummer
            else:
                label = ''
            #Justere titler o.l.
            komponist = finn_komponist(element)

            if label.startswith(EGEN_PROD):
                tittel = finn_verdi(element, 'metadata_DC/titles/title', entity=False)
            else:
                if komponist and kanal == 'ak' and elementtype == 'item':
                    tittel = komponist + ': ' + tittel
                    if len(tittel) > 128:
                        tittel = finn_komponist(element, kun_etternavn=True) + ': ' + finn_verdi(element, 'metadata_DC/titles/title', entity=False)
            #Beskrivelse
            beskrivelse = ''
            annonsering1 = ''
            annonsering2 = ''

            beskrivelser = finn_verdi(element, 'metadata_DC/description/+abstract', nodetre=True, entity=False)
            for abstract in beskrivelser:
                abs_label = finn_verdi(abstract, '@label')
                if not abs_label:
                    beskrivelse = finn_verdi(abstract, '')
                elif abs_label == 'annonsering1':
                    annonsering1 = finn_verdi(abstract, '')
                elif abs_label == 'annonsering2':
                    annonsering2 = finn_verdi(abstract, '')


            #Dersom denne er tom konsulter nettradiodatabasen, dersom det gjelder et program
            if elementtype == 'programme':


                #Før vi renske pidataene må vi finne ut om det er en samsending
                #Vi oppdaterer kildekanal
                kildekanal = finn_kildekanal(d, beskrivelse)
                kildekanal = ''

                #Rensker pidata
                if beskrivelse.lower().rstrip(' .,;') in ORD_SOM_IKKE_BESKRIVER:
                    beskrivelse = ''

                if beskrivelse.lower().startswith("ved ") or beskrivelse.lower().startswith("programleder "):
                    programleder = beskrivelse
                    beskrivelse = ''
                else:
                    programleder = ''

                if len(beskrivelse) > 128:
                    beskrivelse = begrens(beskrivelse)
                #Så må vi legge inn en test for om den er for lang, og prøve å kutte fornuftig.
                #Splitte på punktum og Addere oppover til vi nermer oss 128 tegn.

            #Finne digasklasse
            digastype =  finn_verdi(element, 'metadata_DC/types/type', entity=False)
            #Finne medarbeidere, utøvere o.l.
            try:
                medvirkende, solistene = finn_medvirkende(element, klasse=digastype)
            except IndexError:
                #Det finnes ingen medvirkende
                medvirkende = {}
                solistene = {}
            #Artister...

            if VERBOSE:
                print(medvirkende, solistene)

            if 'Orchestra' in medvirkende: #UTGÅR MED BMS
                artist = medvirkende['Orchestra'][0]
                medvirkende.pop('Orchestra')
                if 'Conductor' in medvirkende:
                    artist = artist.rstrip(" ,.;") + choice(DIRIGERT) + medvirkende['Conductor'][0]
                    medvirkende.pop('Conductor')
                if 'Performer' in medvirkende:
                    artist = artist + ', ' + ', '.join(medvirkende['Performer'])
                elif medvirkende:
                    #Funksjon som henter ut solistene.
                    artist = lag_artistfelt(medvirkende, solister=True) + '|med ' + artist

            elif 'Choir' in medvirkende: #UTGÅR MED BMS
                artist = medvirkende['Choir'][0]
                medvirkende.pop('Choir')
                if 'Conductor' in medvirkende:
                    artist = artist.rstrip(" ,.;") + choice(DIRIGERT) + medvirkende['Conductor'][0]
                    medvirkende.pop('Conductor')
                if 'Performer' in medvirkende:
                    artist = artist + ', ' + ', '.join(medvirkende['Performer'])
                elif medvirkende:
                    #Funksjon som henter ut solistene.
                    artist = lag_artistfelt(medvirkende, solister=True) + '|sammen med ' + artist

            elif 'Conductor' in medvirkende: #FOR DIGAS
                # Vi har en dirigent, ergo er utøveren et orkester eller noe annet som kan ledes
                dirigentnavn = medvirkende.pop('Conductor')[0]
                artist = lag_artistfelt(medvirkende,solister=False)
                artist = artist.rstrip(" ,.;") + choice(DIRIGERT) + dirigentnavn
                if solistene:
                    #Funksjon som henter ut solistene.
                    artist = lag_artistfelt(solistene, solister=True) + '|med ' + artist

            elif 'Leader' in medvirkende: #FOR DIGAS
                # Vi har en leder av en gruppe
                dirigentnavn = medvirkende.pop('Leader')[0]
                artist = lag_artistfelt(medvirkende,solister=False)
                artist = artist.rstrip(" ,.;") + choice(LEDET) + dirigentnavn
                if solistene:
                    #Funksjon som henter ut solistene.
                    artist = lag_artistfelt(solistene, solister=True) + '|med ' + artist

            elif 'Performer' in medvirkende:
                artist = ', '.join(medvirkende['Performer'])
                #Da kan det forekomme all kaps:-)
                if artist.isupper():
                    artist = " ".join([ord.capitalize() for ord in artist.split()])

            elif 'Programleder' in medvirkende:
                artist = ', '.join(medvirkende['Programleder'])
            elif 'Host' in medvirkende:
                artist = ', '.join(medvirkende['Host'])
            elif medvirkende:
                artist = lag_artistfelt(medvirkende)
                if solistene:
                    #Funksjon som henter ut solistene.
                    artist = lag_artistfelt(solistene, solister=True) + '|med ' + artist
            else:
                artist = ''
            #Dersom dette er et program og vi ikke har funnet noen...
            if elementtype == 'programme' and programleder:
                artist = programleder
            if VERBOSE:
                print('Artist: ', artist)

            #Saa sendetidspunktet
            sendetidspunkt = finn_verdi(element, 'metadata_DC/dates/date_issued', entity=False)
            tid = mdb.TimestampFromTicks(iso_til_dato(sendetidspunkt, sekunder=True))

            #Finne opptaksdato, dersom dette finnes.
            opptaksdato = finn_verdi(element, 'metadata_DC/dates/date_created', entity=False)
            if opptaksdato:
                laget = mdb.TimestampFromTicks(iso_til_dato(opptaksdato, sekunder=True))
            else:
                #** Mulig denne må endres til en nullverdi
                laget = tid

            #Finne tiden i sekunder
            lengde = int(iso_til_lengde(finn_verdi(element,'metadata_DC/format/format_extent', entity=False)))

            #Hente ut albumillustrasjon, dersom denne finnes.
            bilde = finn_verdi(element, 'musicSpecials/albumIllustration/origin/file', entity=False) #*** Endre path
            if len(bilde) < 11:
                bilde=''

            #Sjekke om programmet skal oppdateres (summary sjekk)
            if detaljering == 'summary':

                #Sjekke om det er programmet som er på lufta og at det ikke er utløpt
                # Vi har å gjøre med en programinformasjon som ikke er utfyllende, skal bare brukes dersom annen informasjon (fra PI) er tilgjengelig.
                if localid != 1:
                    #Det er bare på nivå 1 vi står over for denne summary tagen, derfor kan vi ignorere denne
                    continue
                #Sjekke om det gjeldene programmet er utløpt
                #Gjeldene sendetid
                oppdatere = 0
                c1 = d.cursor()
                sql = """SELECT tid, lengde FROM iteminfo
                WHERE kanal=%s and localid=%s;"""

                c1.execute(sql, (kanal, localid))
                try:
                    tid1, lengde1 = c1.fetchone()
                except TypeError:
                    #Raden eksisterer ikke
                    #print "I FEILLØKKE %s - raden eksisterer antagelig ikke" % localid
                    oppdatere = 1
                    #Da kan man oppdatere
                    c1.close()
                else:
                    c1.close()
                    #Finne slutttidspunkt
                    slutttid1 = iso_til_dato(tid1,sekunder=True, sql=True) + lengde
                    if iso_til_dato(sendetidspunkt,sekunder=True) >= slutttid1:
                        oppdatere = 1

                if not oppdatere:
                    #print "IKKE oppdatere sendings info"
                    #Vi kan ikke rydde neste heller da
                    try:
                        rydd.remove(2)
                    except:
                        pass
                    continue
            elif localid == 1:

                #Sjekke om tittel er lik, sendetidspunkt er likt og lengde er likt, da har vi en oppdatering av det samme programmet og vi skal ikke flushe!!!
                c1 = d.cursor()
                sql = """SELECT tittel,tid, lengde FROM iteminfo
                WHERE kanal=%s and localid=%s;"""

                c1.execute(sql, (kanal, localid))
                try:
                    tittel2, tid2, lengde2 = c1.fetchone()
                except TypeError:
                    #Raden eksisterer ikke
                    #Dette er i alle fall et nytt program
                    flush_items = 1
                    #Vi flusher
                    c1.close()
                else:
                    if (tittel2, tid2, lengde2) == (tittel, tid, lengde):
                        if VERBOSE:
                            print("SAMMA GREIENE JO")
                        #Vi flusher ikke
                        flush_items = 0
                    else:
                        #Det er et nytt programm
                        flush_items = 1
                # Det er ikke snakk om at det er summary, og vi har et nytt program, vi må starte opprydingsrutinene
                # Gamle innslag må renskes ut og meldinger fra programlederen må tas.
                if flush_items:
                    flush_program_data(d, kanal)
                    if VERBOSE:
                        print("FLUSH - programdata kjørt")

            #Vi har komplett datasett, denne skal ikke ryddes
            try:
                rydd.remove(localid)
            except:
                #to present noder?
                pass
            #Tilpasse for annonsering
            if annonsering1:
                tittel = annonsering1
            if annonsering2:
                artist = annonsering2

            #Barbere for makslengde for å hindre "warnings"
            tittel = tittel[:128]

            #Oppdatere databasen
            c = d.cursor()
            #Sjekke først om dataene er registrert
            sql = """SELECT id FROM iteminfo
                WHERE kanal=%s and localid=%s;"""
            c.execute(sql, (kanal, localid))
            if VERBOSE:
                print((
                    tittel,
                    elementtype,
                    localprogid,
                    dataid,
                    laget,
                    tid,
                    lengde,
                    beskrivelse,
                    artist,
                    #xml_element,
                    label,
                    kanal,
                    localid
                    ))
            if c.rowcount == 1:
                status = 1
                if VERBOSE:
                    print("UPDATE", repr(tittel))
                sql = """UPDATE iteminfo SET
                    tittel=%s,
                    kildekanal=%s,
                    type=%s,
                    localprogid=%s,
                    progID=%s,
                    laget=%s,
                    tid=%s,
                    lengde=%s,
                    beskrivelse=%s,
                    artist=%s,
                    element=%s,
                    label=%s,
                    bildeID=%s,
                    digastype=%s
                    WHERE kanal=%s and localid=%s;"""

                c.execute(sql,(
                    tittel,
                    kildekanal,
                    elementtype,
                    localprogid,
                    dataid,
                    laget,
                    tid,
                    lengde,
                    beskrivelse,
                    artist,
                    xml_element,
                    label,
                    bilde,
                    digastype,
                    kanal,
                    localid
                    )
                )
            else:
                #Det er ingen felter som er oppdatert
                status = 2
                if VERBOSE:
                    print("INSERT", repr(tittel))
                sql = """INSERT INTO iteminfo(tittel,kildekanal,type,localprogid,progID,laget,tid,lengde,beskrivelse,artist,element,label,bildeID,kanal,localid,digastype) VALUES
                (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """
                c.execute(sql, (
                    tittel,
                    kildekanal,
                    elementtype,
                    localprogid,
                    dataid,
                    laget,
                    tid,
                    lengde,
                    beskrivelse,
                    artist,
                    xml_element,
                    label,
                    bilde,
                    kanal,
                    localid,
                    digastype
                    )
                )
            if LOGGING_ITEM:
                #Sette inn i loggtabell
                if localid in (1, 3):
                    sql = """INSERT INTO iteminfoLogg(tittel,kildekanal,type,laget,tid,lengde,beskrivelse,artist,element,label,bildeID,kanal,digastype,insatt) VALUES
                    (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
                    """
                    c.execute(sql, (
                        tittel,
                        kildekanal,
                        elementtype,
                        laget,
                        tid,
                        lengde,
                        beskrivelse,
                        artist,
                        xml_element,
                        label,
                        bilde,
                        kanal,
                        digastype
                        )
                )

            c.close()
        #I noen tilfeller har vi situasjonen der et program feilaktig har blitt satt til lengde 0
        #Vi må sjekke dette
        sjekk_program_lengde(d, kanal)
        #Rydde opp manglende elementer, dvs det er ferre en 4 elementer i settet.
        if VERBOSE:
            print('flush_items, rydd,stryk:', flush_items, rydd,stryk)
        for localid in localids:
            #Er elementet utgått på tid?
            #Past elementet skal jo være utgått
            c1= d.cursor()
            sql = """SELECT tid, lengde FROM iteminfo
            WHERE kanal=%s and localid=%s;"""
            c1.execute(sql, (kanal, localid))
            try:
                tid1, lengde1 = c1.fetchone()
            except:
                #Raden eksisterer ikke
                continue
            c1.close()

            #Finne slutttidspunkt
            slutttid1 = iso_til_dato(tid1, sekunder=True, sql=True) + float(lengde1)
            #Forige innslag eldre enn en time er neppe relevante
            if localid == 5:
                #Vi har det utlgående elementet
                #Aldri rydde fortiden
                continue
            nu = time.time()

            #Vi sjekker om vi har data av den nye typen
            if runorder != '':
                #Vi har den nye typen
                if 3 in rydd:
                    stryk.append(3)
                if 4 in rydd:
                    stryk.append(4)
                #Vi rydder aldri nummer 5, den vil jo være utløpt uansett

            #Stryker noe hvis:
            #  Tiden på inslaget er utløpt og ikke null
            #  De andre valgene fjerner innslag ved programskifte
            #Sjekke hvordan denne reagerer på past, noden
            if (nu >= slutttid1 and lengde1 != 0) or (localid % 2 == 0 and localid in rydd) or (flush_items and localid == 3 and localid in rydd) or localid in stryk:
                #print "utg %s" % localid
                status = 1
                c2 = d.cursor()
                sql = """DELETE FROM iteminfo
                WHERE kanal=%s and localid=%s;"""
                c2.execute(sql, (kanal, localid))
                c2.close()
                if VERBOSE:
                    print(localid, 'SLETTET, fordi den var utløpt, eller skulle strykes')

    #Lukke database
    d.commit()
    d.close()
    return {'status':status, 'kanal':kanal, 'datatype':'iteminfo'}

