# -*- coding: utf-8 -*-
"""iteminfo tjenester
Versjon som sjekker lengden på programmet utifra avstanden i sendetid mellom program 1 og 2, dersom
programtiden oppgis til å være null"""

import re
import time
import xml.dom.minidom
import pymysql as mdb
from random import choice
from db_conn import database

from roller import rolleliste, rollerelasjon, ikkeRolle

kanal_sw = {'nrk jazz':'jazz', 'nrk sport':'sport', 'sport':'sport', 'nrk gull':'gull',
            'nrk p1pluss':'p1pluss', 'nrk barn':'barn', 'p1_ndst':'p1st', 'nrk p1':'p1', 'p1':'p1', 'nrk p2':'p2', 'p2':'p2',
            'nrk p3':'p3', 'petre':'p3', 'nrk petre':'p3', 'p3':'p3', 'nrk ak':'ak', 'alltid klassisk':'ak', 'ak':'ak',
            'nrk mpetre':'mpetre', 'mpetre':'mpetre', 'nrk alltid nyheter':'an', 'nrk an':'an', 'an':'an',
            'nrk alltid folkemusikk':'fmk', 'fmk':'fmk', 'p3urort':'urort', 'urort':'urort',
            'nrk p1 oslofjord':'p1of', 'p1of':'p1of', 'sami dab':'sami', 'lzu':'sami'}


fjernsyn = ['nrk 1', 'nrk 2', 'nrk 3_super']
newsItem = ['p1', 'p3']

VERBOSE = False
logging_item = False

FJERNROLLERFOR = ['Conductor', 'Leader']
DIRIGERT = [' under ledelse av ',' DIRIGERT av ', ', dirigent ']
LEDET = ['LEDET av']

ORD_SOM_IKKE_BESKRIVER = ['fortsetter', 'samsending', 'også sendt i går']

EGEN_PROD = 'EBU-NONRK' #Label for EGEN_PRODuksjon

#def database(host="160.68.118.48", user="tormodv", database="dab",passord="allmc21"):
#def database(host="localhost", user="tormodv", database="dab",passord=""):
#	d = mdb.connect(user=user,passwd=passord, host=host)
#	d.select_db(database)
#	return d

def sjekkProgramLengde(d,kanal):
    "Sjekker om programmet som er på lufta nå, har fått lengde 0, i så fall rettes den til tiden frem til neste program. Har ingen definert returverdi."
    #Sjekk programme lengde
    c =  d.cursor()
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
MAX(UNIX_TIMESTAMP(tid))
-
MIN(UNIX_TIMESTAMP(tid))
from 
iteminfo
where kanal = %s; """
    c.execute(sql, (kanal))
    try:
        beregnetLengde = int(c.fetchone()[0])
    except TypeError:
        beregnetLengde = 0
    except ValueError:
        beregnetLengde = 0
    #Hvis lengden er null nå også er vi like kloke og må returnere
    if beregnetLengde == 0:
        c.close()
        return
    sql = """UPDATE iteminfo SET 
                    lengde=%s
                    WHERE kanal=%s and localid = 1;"""
    c.execute(sql,(beregnetLengde, kanal))
    c.close()
    if VERBOSE:
        print("Rettet lengde på programm",lengde, beregnetLengde)
    


def flush_program_data(d,kanal):
    "Renserutine for programskift"
    #1 Stryk innslag/neste program
    c2= d.cursor()
    sql = """DELETE FROM iteminfo 
    WHERE kanal=%s and localid !=0;"""
    c2.execute(sql, (kanal))
    
    #2 Stryk ev textinfo på programmnivå (eller lavere)
    sql = """DELETE FROM textinfo 
    WHERE kanal=%s and type = 'programme';"""
    c2.execute(sql, (kanal))
    c2.close()

def iso_til_lengde(isoTid):
    tid = 0.0
    tidsFeil = "Feil i konvertering fra ISO 8601 format."
    if isoTid[0]!='P':
        raise(tidsFeil,"Begynner ikke med P")
    #Split dager fra timer
    dager,timer = isoTid[1:].split('T')
    #Finn sekunder osv.
    p=re.search(r'(\d+|\d+\.\d+)S',timer)
    if p:
        tid += float(p.group(1))
    p=re.search(r'(\d+|\d+\.\d+)M',timer)
    if p:
        tid += float(p.group(1)) * 60
    p=re.search(r'(\d+|\d+\.\d+)H',timer)
    if p:
        tid += float(p.group(1)) * 3600
    # dager o.l.
    p=re.search(r'(\d+|\d+\.\d+)D',dager)
    if p:
        tid += float(p.group(1)) * 3600 * 24
    p=re.search(r'(\d+|\d+\.\d+)M',dager)
    if p:
        tid += float(p.group(1)) * 3600 * 24 * 30
    p=re.search(r'(\d+|\d+\.\d+)Y',dager)
    if p:
        tid += float(p.group(1)) * 3600 * 24 * 365
    
    return tid

def ISOtilDato(dato,sekunder=0, sql=0):
    offsett = 0
    if not dato:
        return 0
    if type(dato)!=type(''):
                #Dette er en forelÃ¸pig patch for at en har begynt Ã¥ bruke datetime objekter
                dato = dato.isoformat()
    if 'T' in dato or sql:
        aar = int(dato[0:4])
        if aar < 1970:
            #Da har vi et problem
            aar = aar + 60
            offsett = 1893456000.0
            
        try:
            if sekunder:
                tid= time.mktime ((aar,int(dato[5:7]), int(dato[8:10]),int(dato[11:13]),int(dato[14:16])
                        ,int(dato[17:19]),-1,-1,-1))
            else:
                tid= time.mktime ((aar,int(dato[5:7]), int(dato[8:10]),int(dato[11:13]),int(dato[14:16])
                        ,0,-1,-1,-1))
        except ValueError:
            tid = 0
            
    else:
        try:
            tid = int(dato)
        except:
            tid=0

    return tid - offsett
    

def finnUnger(noder,tag,kunEn=0):
    s=[]
    for node in noder:
        if node.nodeType == node.ELEMENT_NODE:
            if node.tagName == tag:
                s.append(node)
                if kunEn: return s
                
    return s

def hentVerdier(noder,lim='', encoding = 'utf-8'):
    s=''
    for node in noder:
        if node.nodeType == node.TEXT_NODE:
            s+=node.data + lim
        s.replace(u'\u2019', "'")
    return s.encode(encoding,'replace')
    
def finnVerdi(xmlobjekt,path, entity = False, nodetre = False, encoding = 'iso-8859-1'):
    #path til nodeliste
    nodeliste = path.split('/')
    try:
        for node in nodeliste:
            if node=='':
                continue
            if node[0]!='@':
                if  node[0]=='+' and nodetre:
                    xmlobjekt = finnUnger(xmlobjekt.childNodes,node[1:],kunEn=0)
                    #Siden dette kun er gyldig i siste node:
                    break
                    #Så fortsetter vi under
                else:
                    xmlobjekt = finnUnger(xmlobjekt.childNodes,node,kunEn=1)[0]
            else:
                #returnere attributverdi
                return xmlobjekt.getAttribute(node[1:]).encode(encoding,'replace')
                
    except IndexError:
        if nodetre:
            return []
        else:
            return ''
    if nodetre:
        return xmlobjekt
    if not entity:
        return hentVerdier(xmlobjekt.childNodes, encoding = encoding)
    else:
        return entetyReplace(hentVerdier(xmlobjekt.childNodes, encoding = encoding))
        
    
def entetyReplace(s):
    s = s.replace('&amp;','&')
    
    return s

def samsendinglexer(setning):
    "Finner og forstÃ¥r variasjoner over setningen: 'I sammmesending med kulturkanalen'"
    stoppord = ['den','det','den','med','for','i']
    pynt = ['radioens','fjernsynets','tvens','NRK']
    samsendingsbegreper = ['sammsending','samssending','samsending','sams']
    samsending = False
    
    for ord in setning.split():
        
        if ord.lower() in stoppord:continue
        if ord.lower() in pynt:continue
        if ord.lower() in samsendingsbegreper:
            samsending=True
            
            continue
        #I og med at vi tar bort alle stoppord og pynt er det neste som kommer nÃ¥ kanalbetegnelsen
        if samsending:
            return ord
        
        

def finnKildekanal(d,beskrivelse,kanal):
    "returnerer kanalkode dersom vi detekterer i beskrivelsen at vi har en samsending ellers returnerer den None, dvs ingen samsending"
    #Dele opp beskrivelsen i setninger, sÃ¥ analysere disse.
    #Vi deler pÃ¥ punktum
    
    if '.' in beskrivelse:
        setninger = beskrivelse.split('.')
    else:
        setninger = [beskrivelse]
    
    if len(setninger) !=1:
        #Vi har mer en en en setning, op punktum, men disse punktummene kan skyldes forkortelser.
        setninger2=[]
        flush = False
        for setnum, setning in enumerate(setninger):
            if flush:
                flush = False
                continue #Slik at vi hopper over setningen som er lagt til - mÃ¥ slettes
            if (setnum +1) <len(setninger):
                #Vi har minst en setning til
                nesteSetning = setninger[setnum+1].lstrip()
                if nesteSetning:
                    if nesteSetning[0].isupper():
                        #Neste starter med stor forbokstav, det er sansynlig at dette er en ny setning
                        setninger2.append(setning)
                        flush = False
                        continue	
                    else:
                        #Vi har en forkortelse ****
                        setninger2.append(setning + '.' + setninger[setnum+1])
                        flush = True
                setninger2.append(setning)
            else:
                #Dette er siste setning som bare skal legges til
                setninger2.append(setning)
                
                    
        setninger = setninger2
    
    for setning in setninger:
        kanaltoken = samsendinglexer(setning)
        if kanaltoken:break #Har vi fÃ¸rst funnet en kanal leter vi ikke lenger
    
    
    oppdatere = 0 
    c1= d.cursor()
    sql = """SELECT navn FROM kanal 
    WHERE alias=%s or navn=%s;"""
    
    c1.execute(sql,(kanaltoken,kanaltoken)) 

    result = c1.fetchone()
    if result:
        return result[0]
        
    else:
        return None


    
def begrens(tekst,lengde):
    if "." in tekst:
        s=''
        for setning in  tekst.split('.'):
            if len(s) + len(setning) + 1 <=128:
                s += setning + '.'
            else:
                break
        return s
    else:
        return tekst[:128]
        
def tellArtister(artister):
    s=0
    for rolle in artister:
        s+=len(artister[rolle])
    return s
    
def lagArtistfelt(artister,solister=0):
    "Lager deler eller hele artistfeltet, kan kalles flere ganger"
    artistfelt = ''
    artisttall = tellArtister(artister)
    if solister:
        if artisttall == 1:
            solistfelt = " er solist "
        else:
            solistfelt = " er solister"
    else:
        solistfelt = ''
    if artisttall==1:
        if 'Utøver' in artister:
            if solister:
                return '. ' + artister['Utøver'][0][0].upper() + (artister['Utøver'][0] + solistfelt)[1:]
            else:
                return artister['Utøver'][0]
        elif artister.keys()[0] in rolleliste:
            rolle = artister.keys()[0]
            if rolle in ikkeRolle:
                if solister:
                    return '. ' + artister[rolle][0][0].upper() + (artister[rolle][0] + ' på ' + rolle + solistfelt)[1:]
                else:
                    return artister[rolle][0] + ' på ' + rolle
            else:
                if solister:
                    return '. ' + rolleliste[rolle]['tittel'][0].upper() + (rolleliste[rolle]['tittel'] + ' ' + artister[rolle][0] + solistfelt)[1:]
                else:
                    return rolleliste[rolle]['tittel'] + ' ' + artister[rolle][0] 
        else:
            #Vi finner ikke rollen, dette viol normali ikke skje, vi retunerer da bare navnene
            return artister[artister.keys()[0]][0]
            
    elif artisttall==2 and not solister:
        #Finne forholdet mellom roller, dersom det er solister vi skal bare liste opp
        if 'Utøver' in artister:
            # Da må vi gjøre noe spesielt, da kan det fremdeles være (rolle)
            if len(artister)==1:
                #Vi har to ukjente roller og kan gjøre det enkelt.
                return artistfelt + ' og '.join(artister['Utøver']) 
            else:
                #Vi har en ukjent og en kjent, for å få dette pent setter vi rollen over i () igjen. Fram og tilbake er like langt.
                i,j = artister.keys()
                if j == 'Utøver':
                    #SWAP, dette gir oss den 'eksotiske' først.
                    i,j = j,i
                return artistfelt + artister[i][0] + ' og ' + artister[j][0] + ' (' + j + ')' 
            
        #Så derspm vi bare har kjente artister	
        if len(artister)==1:
            i, = artister.keys()
            #Dersom disse er like -> vi bruker og, og har rollen i flertall
            return rolleliste[i]['tittel'] + 'e ' + ' og '.join(artister[i]) + solistfelt
        #Så sjekke gruppene og relasjonene mellom disse
        i,j = artister.keys()
        ir = rollerelasjon[rolleliste[i]['gruppe']]
        jr = rollerelasjon[rolleliste[j]['gruppe']]
        #Sjekke slik at mest dominerende gruppe kommer først
        if jr>ir:
            #swap
            i,ir,j,jr = j,jr,i,ir
        # **** if rolle in ikkeRolle:
        artistfelt += rolleliste[i]['tittel'] + ' ' + artister[i][0] 
        
        #Finne konjuksjon
        if ir == jr or jr != 0:
            #Vi bruker og...
            return artistfelt + ' og ' + rolleliste[j]['tittel'] + ' ' + artister[j][0] + solistfelt
        else:
            #Vi bruker passiv form 
            return artistfelt + ' ' + rolleliste[j]['passiv'] + ' ' + rolleliste[j]['tittel'] + ' ' + artister[j][0] + solistfelt
        
        #print(i,ir, j,jr)
        
        #print(artister.keys())
        return artistfelt + solistfelt
    else:
        #Dersom det er tre eller fler, eller at det er to eller flere solister havner vi her.
        pass
    
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
    else:
        return artistfelt + solistfelt
        
        
def finnKomponist(element, kunEtternavn = 0, aarsTall = 0):
    creators = element.getElementsByTagName('creator')
    for creator in creators:
        role = finnVerdi(creator,'role',entity=0)
        if role.lower() == "composer" or role.lower() == "komponist":
            komponist_fornavn = finnVerdi(creator,'given_name',entity = 1)
            komponist = finnVerdi(creator,'family_name',entity = 1)
            
            if kunEtternavn:
                if komponist_fornavn:
                    #Da er dette av rik datatype og vi kan sende etternavnet
                    return komponist
                else:
                    #Finne etternavnet, fjerne paranteser
                    try:
                        return komponist.split('(')[0].rstrip().split().pop()
                    except:
                        return ""
            else:
                if komponist_fornavn:
                    if aarsTall:
                        #Da er dette av rik datatype og vi kan sende etternavnet
                        return "%s %s"  % (komponist_fornavn, komponist)
                    else:
                        return "%s %s"  % (komponist_fornavn.split('(')[0].rstrip(), komponist.split('(')[0].rstrip())
                else : 
                    if aarsTall:
                        return komponist
                    else:
                        return komponist.split('(')[0].rstrip()
    

def finnMedvirkende(element, lagreIbase=0, klasse=''):
    s = {} #Utøver liste
    ss = {} #Solist liste
    
    metadata = finnUnger(element.childNodes,"metadata_DC", kunEn=1)[0]
    contributors = metadata.getElementsByTagName('contributor')
    for contributor in contributors:
        solist = False
        #Finne rolle bruke denne som key
        role = finnVerdi(contributor,'role',entity=0)
        #Fiks for tvilsommedata
        if (klasse !='News' and role=='Reporter'):
            continue
        #print role
        if not role:
            role = 'contributor'
        fornavn =  finnVerdi(contributor,'given_name', entity = 1)
        navn = finnVerdi(contributor,'family_name', entity = 1)
        if not navn:continue		
    
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
                if nyrolle == 'leder' or nyrolle == 'Leder':
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
            else:
                #Vi må skifte rolle og beholde parantes
                pass
                #role="Utøver"
                
            solist = True
        
        #Fjerne rolleparanteser
        
        if role in FJERNROLLERFOR:
            navn = navn.split('(')[0].rstrip()
        
        if solist:
        
            if fornavn:
                if role in ss:
                    ss[role] = ss[role].append(fornavn + ' ' + navn)
                else:
                    ss[role] = [fornavn + ' ' + navn]
            else:
                if role in s:
                    ss[role].append(navn)
                else:
                    ss[role] = [navn]
        else:
                
            if fornavn:
                if role in s:
                    s[role] = s[role].append(fornavn + ' ' + navn)
                else:
                    s[role] = [fornavn + ' ' + navn]
            else:
                if role in s:
                    s[role].append(navn)
                else:
                    s[role] = [navn]
    
    return s,ss

def parser(xmlstreng):
    status = 0
    flushItems = 0
    
    #Lager en database forbindelse
    d=database()
    #d2=database2()
    
    pars = xml.dom.minidom.parseString(xmlstreng)

    kropp = pars.getElementsByTagName('body')
    lagetDato = finnVerdi(pars,'gluon/head/creator/@date')
    
    tabeller = pars.getElementsByTagName('tables')
    for tabell in tabeller:
        if tabell.getAttribute('type')!='iteminfo':
            continue
        
        
        
        #kampObj['lagetDato'] = lagetDato
        kanal = finnVerdi(tabell,'element/@channel')
        #Rette kanalnavn
        if kanal.lower() in kanal_sw:
            kanal = kanal_sw[kanal.lower()].lower()
        else:
            kanal = kanal.lower()
        #Fjerne NRK fra kanlnavn
        if kanal.startswith('nrk ') and not kanal in fjernsyn:
            kanal = kanal.split(' ')[1]

        #Rette kanalnavn for ev kanaler
        if '-' in kanal:
            kanal,label = kanal.split('-')
            
        if pars.documentElement.getAttribute('priority') =='0':
            #Lage strykefunksjon ******
            #return "Settet er strøket"
            return {'status':2, 'kanal':kanal, 'datatype':'iteminfo'}
        

        elementer = tabell.getElementsByTagName("element")
        sendingItem = 0
        sendingProgramme = 0
        rydd = [1,2,3,4,5]
        localids = [1,2,3,4,5]
        stryk = []
        #Opdatere db
        localid=0
        digastype=''
        nettype=''
        for element in elementer[:4]:
            #Vil aldri inneholde mer enn 4 elementer, som oftest mindre
            #Dersom dette er av den nye Digastypen, så vil vi ha et runorder parameter som viser om dette er
            #past, present eller future.
            #Past hopper vi foreløpig over, dette er mer nyttig i statistikksammenheng, da dette vil være det som er 
            #Riktig spilletid på innslaget.
            
            runorder = finnVerdi( element,'@runorder', entity=0)
                        
            xmlElement=element.toxml().encode('latin-1', 'replace')
            
            #Finne tekniske parametre
            
            elementtype =  finnVerdi( element,'@objecttype', entity=0)
            if elementtype=='programme':
                sendingProgramme +=1
                localprogid = 0
                localid = sendingProgramme
            if elementtype=='item':
                if runorder =='present':
                    localprogid = sendingProgramme
                    localid = 3
                    # present
                elif runorder == 'future':
                    localprogid = sendingProgramme
                    localid = 4
                    # future
                elif runorder == 'future1':
                    localprogid = sendingProgramme
                    localid = 4
                    # future
                elif runorder == 'past':
                    localprogid = 0 #Vil altid tilordnes det lopende programmet

                    localid = 5
                else:
                    #Da er det bare fremtidige elementer, future2 etc
                    continue


            #Dette gir oss rekefølgen programme,programme,item,item,item(past)
            
            detaljering = finnVerdi( element,'@type', entity=0)
            # **** Dersom det er summary skal vi ikke ta hensyn til at det er et nytt program
            dataid = finnVerdi( element,'@dataid', entity=0)
            
            #Tittel
            tittel = finnVerdi( element,'metadata_DC/titles/title', entity=0)
            plateselskap = finnVerdi( element,'metadata_DC/source/@label', entity=0)
            platenummer = finnVerdi( element,'metadata_DC/source/@reference', entity=0)
            if plateselskap:
                label =  plateselskap + ':' + platenummer
            else:
                label = ''
            #Justere titler o.l.
            komponist = finnKomponist(element)
            
            if label.startswith(EGEN_PROD):
                tittel = finnVerdi( element,'metadata_DC/titles/title', entity=0)
            else:
                if komponist and kanal == 'ak' and elementtype=='item':
                    tittel= komponist + ': ' + tittel
                    if len(tittel) > 128:
                        tittel= finnKomponist(element, kunEtternavn = 1) + ': ' + finnVerdi( element,'metadata_DC/titles/title', entity=0)
            
            #Beskrivelse
            beskrivelse = ''
            beskrivelseAlt = ''
            annonsering1 = ''
            annonsering2 = ''
            
            beskrivelser = finnVerdi(element,'metadata_DC/description/+abstract', nodetre = True, entity=0)
            for abstract in beskrivelser:
                absLabel = finnVerdi(abstract, '@label')
                if not absLabel:
                    beskrivelse = finnVerdi(abstract, '')
                elif absLabel == 'annonsering1':
                    annonsering1 = finnVerdi(abstract, '')
                elif absLabel == 'annonsering2':
                    annonsering2 = finnVerdi(abstract, '')

            
            #Dersom denne er tom konsulter nettradiodatabasen, dersom det gjelder et program
            if elementtype=='programme':
            
                
                #Før vi renske pidataene må vi finne ut om det er en samsending
                #Vi oppdaterer kildekanal
                kildekanal = finnKildekanal(d, beskrivelse,kanal)
                kildekanal = ''	
                
                #Rensker pidata
                if beskrivelse.lower().rstrip(' .,;') in ORD_SOM_IKKE_BESKRIVER:
                    beskrivelse = ''
                
                if beskrivelse.lower().startswith("ved ") or beskrivelse.lower().startswith("programleder "):
                    programleder = beskrivelse
                    beskrivelse = ''
                else:
                    programleder = ''

                if len(beskrivelse) >128:
                    beskrivelse = begrens(beskrivelse,128)
                #Så må vi legge inn en test for om den er for lang, og prøve å kutte fornuftig.
                #Splitte på punktum og Addere oppover til vi nermer oss 128 tegn.
                
                #Hente mer info fra dette prodnummeret, dersom det ikke er en summary(digas)
                if detaljering != 'summary':
                    #Hente ut merdata fra sigma, beskrivelse og etterhvert også programleder
                    cs = d.cursor()
                    sql="""select  from sigma
                    
                    where
                    progID=%s
                    """
                    #beskrivelseAlt
                    cs.close()
                #***
                
            #Finne digasklasse
            digastype =  finnVerdi( element,'metadata_DC/types/type',  entity=0)
            #Finne medarbeidere, utøvere o.l.
            try:
                medvirkende, solistene = finnMedvirkende(element, klasse = digastype)
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
                    artist = lagArtistfelt(medvirkende,solister=1) + '|med ' + artist
                    

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
                    
                    artist = lagArtistfelt(medvirkende,solister=1) + '|sammen med ' + artist
                    #artist = artist + '. ' + lagArtistfelt(medvirkende,solister=1)
            
            elif 'Conductor' in medvirkende: #FOR DIGAS
                # Vi har en dirigent, ergo er utøveren et orkester eller noe annet som kan ledes
                dirigentnavn = medvirkende.pop('Conductor')[0]
                artist = lagArtistfelt(medvirkende,solister=0)
                artist = artist.rstrip(" ,.;") + choice(DIRIGERT) + dirigentnavn
                if solistene:
                    #Funksjon som henter ut solistene.
                    artist = lagArtistfelt(solistene, solister = 1) + '|med ' + artist
                
            elif 'Leader' in medvirkende: #FOR DIGAS
                # Vi har en leder av en gruppe
                dirigentnavn = medvirkende.pop('Leader')[0]
                artist = lagArtistfelt(medvirkende,solister=0)
                artist = artist.rstrip(" ,.;") + choice(LEDET) + dirigentnavn
                if solistene:
                    #Funksjon som henter ut solistene.
                    artist = lagArtistfelt(solistene, solister = 1) + '|med ' + artist
                                            
                            
            elif 'Performer' in medvirkende:
                artist = ', '.join(medvirkende['Performer'])
                #Da kan det forekomme all kaps:-)
                if artist.isupper():
                    artist = " ".join([ord.capitalize() for ord in artist.split()])
                    
            elif 'Programleder' in medvirkende:
                artist = ', '.join(medvirkende['Programleder'])
            elif 'Host' in medvirkende:
                artist = ', '.join(medvirkende['Host'])
            elif len(medvirkende):
                artist = lagArtistfelt(medvirkende)
                if solistene:
                    #Funksjon som henter ut solistene.
                    artist = lagArtistfelt(solistene, solister=1) + '|med ' + artist
            else:
                artist = ''
            #Dersom dette er et program og vi ikke har funnet noen...
            if elementtype == 'programme' and programleder:
                artist = programleder
            if VERBOSE:
                print(artist)
    
            #Saa sendetidspunktet
            sendetidspunkt = finnVerdi(element, 'metadata_DC/dates/date_issued', entity=0)
            tid = mdb.TimestampFromTicks(ISOtilDato(sendetidspunkt,sekunder=1))
            
            #Finne opptaksdato, dersom dette finnes.
            opptaksdato = finnVerdi(element, 'metadata_DC/dates/date_created', entity=0)
            if opptaksdato:
                laget = mdb.TimestampFromTicks(ISOtilDato(opptaksdato, sekunder=1))
            else:
                #** Mulig denne må endres til en nullverdi
                laget = tid	
            
            #Finne tiden i sekunder
            lengde = int(iso_til_lengde(finnVerdi(element,'metadata_DC/format/format_extent',  entity=0)))
            
            #Hente ut albumillustrasjon, dersom denne finnes.
            bilde = finnVerdi( element,'musicSpecials/albumIllustration/origin/file',  entity=0) #*** Endre path
            if len(bilde)<11:bilde=''
                   
            #Sjekke om programmet skal oppdateres (summary sjekk)
            if detaljering == 'summary':
                
                #Sjekke om det er programmet som er på lufta og at det ikke er utløpt
                # Vi har å gjøre med en programinformasjon som ikke er utfyllende, skal bare brukes dersom annen informasjon (fra PI) er tilgjengelig.
                if localid !=1:
                    #Det er bare på nivå 1 vi står over for denne summary tagen, derfor kan vi ignorere denne
                    continue
                #Sjekke om det gjeldene programmet er utløpt
                #Gjeldene sendetid
                oppdatere = 0 
                c1= d.cursor()
                sql = """SELECT tid, lengde FROM iteminfo 
                WHERE kanal=%s and localid=%s;"""
                
                c1.execute(sql,(kanal,localid)) 
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
                    slutttid1 = ISOtilDato(tid1,sekunder=1,sql=1) + lengde
                    if ISOtilDato(sendetidspunkt,sekunder=1)>=slutttid1:
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
                c1= d.cursor()
                sql = """SELECT tittel,tid, lengde, progId FROM iteminfo 
                WHERE kanal=%s and localid=%s;"""
                
                c1.execute(sql,(kanal,localid)) 
                
                try:
                    tittel2, tid2, lengde2, curProgId = c1.fetchone()
                except TypeError:
                    #Raden eksisterer ikke
                    #Dette er i alle fall et nytt program
                    flushItems = 1
                    #Vi flusher
                    c1.close()
                else:
                    if (tittel2, tid2, lengde2) == (tittel, tid, lengde):
                        if VERBOSE:
                            print("SAMMA GREIENE JO")
                        #Vi flusher ikke 
                        flushItems = 0
                    else:
                        #Det er et nytt programm
                
                        flushItems = 1
                # Det er ikke snakk om at det er summary, og vi har et nytt program, vi må starte opprydingsrutinene
                # Gamle innslag må renskes ut og meldinger fra programlederen må tas.
                if flushItems:
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
            tittel=tittel[:128]
            
            #Oppdatere databasen
            c= d.cursor()
            #Sjekke fÃ¸rst om dataene er registrert
            sql = """SELECT id FROM iteminfo 
                WHERE kanal=%s and localid=%s;"""
            c.execute(sql,(kanal,localid)) 
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
                    #xmlElement,
                    label,
                    kanal,
                    localid
                    ))
            if c.rowcount == 1:
                status = 1
                if VERBOSE:
                    print("UPDATE",repr(tittel))
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
                    xmlElement,
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
                    print("INSERT",repr(tittel))
                sql = """INSERT INTO iteminfo(tittel,kildekanal,type,localprogid,progID,laget,tid,lengde,beskrivelse,artist,element,label,bildeID,kanal,localid,digastype) VALUES 
                (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """ 
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
                    xmlElement,
                    label,
                    bilde,
                    kanal,
                    localid,
                    digastype
                    )
                )
            if logging_item:
                #Sette inn i loggtabell
                if localid == 1 or localid == 3:
                    sql = """INSERT INTO iteminfoLogg(tittel,kildekanal,type,laget,tid,lengde,beskrivelse,artist,element,label,bildeID,kanal,digastype,insatt) VALUES 
                    (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
                    """ 
                    c.execute(sql,(
                    tittel,
                    kildekanal,
                    elementtype,
                    laget,
                    tid,
                    lengde,
                    beskrivelse,
                    artist,
                    xmlElement,
                    label,
                    bilde,
                    kanal,
                    digastype
                    )
                ) 
            


                    
 
            c.close()
            
        #I noen tilfeller har vi situasjonen der et program feilaktig har blitt satt til lengde 0
        #Vi må sjekke dette
        sjekkProgramLengde(d,kanal)	
        #Rydde opp manglende elementer, dvs det er ferre en 4 elementer i settet.
        if VERBOSE:
            print('flushItems, rydd,stryk:',flushItems, rydd,stryk)
        for localid in localids:
            
            #Er elementet utgått på tid?
            #Past elementet skal jo være utgått
            c1= d.cursor()
            sql = """SELECT tid, lengde FROM iteminfo 
            WHERE kanal=%s and localid=%s;"""
            
            c1.execute(sql,(kanal,localid)) 
            try:
                tid1, lengde1 = c1.fetchone()
            except:
                #Raden eksisterer ikke
                continue
            
            c1.close()
            
            #Finne slutttidspunkt
            slutttid1 = ISOtilDato(tid1,sekunder=1,sql=1) + float(lengde1)
            #Forige innslag eldre enn en time er neppe relevante
            if localid == 5:
                #Vi har det utløående elementet
                #Aldri rydde fortiden
                continue
            nu = time.time()

            #Vi sjekker om vi har data av den nye typen
            if runorder!='':
                #Vi har den nye typen
                if 3 in rydd:
                    stryk.append(3)
                if 4 in rydd:
                    stryk.append(4)
                    
                #Vi rydder aldri nummer 5, den vil jo være utløpt uansett
            



            #print time.ctime(slutttid1), time.ctime(ISOtilDato(sendetidspunkt,sekunder=1)), nu>=slutttid1, lengde1
            #Stryker noe hvis:
            #  Tiden på inslaget er utløpt og ikke null
            #  De andre valgene fjerner innslag ved programskifte
            #Sjekke hvordan denne reagerer på past, noden
            if (nu >= slutttid1 and lengde1 !=0 ) or (localid%2==0 and localid in rydd) or (flushItems and localid==3 and localid in rydd) or localid in stryk:
                #print "utg %s" % localid
                status=1
                c2= d.cursor()
                sql = """DELETE FROM iteminfo 
                WHERE kanal=%s and localid=%s;"""
                c2.execute(sql,(kanal,localid)) 
                c2.close()
                
                if VERBOSE:
                    print(localid,'SLETTET, fordi den var utløpt, eller skulle strykes')
        
            
    #Lukke database
    d.commit()
    d.close()
    return {'status':status, 'kanal':kanal, 'datatype':'iteminfo'}
    
