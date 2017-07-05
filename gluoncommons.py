#! /usr/bin/env python
# -*- coding: utf-8 -*-

"Felles funksjoner som ofte er brukt"
from os import popen
import smtplib
import re
import time
from urllib.parse import urlencode
from http.client import HTTPConnection, HTTPSConnection
import sys
import base64

#Todo:

notPerformers = ['Produsent', 'Producer', 'Lydtekniker'] #Roller som ikke er utøvende, støttefunksjoner som produsenter o.l.

class tidsFeil(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
    pass

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

#Debugg funksjon
def logg(msg):
    f=open('/DMA/logen.log','a')
    f.write(msg)
    f.write('\n')
    f.close()

def sendData(uri, method="POST", data_raw = None, data_enc = None, svar_fra_mottager = 1,tag='karusell', reqursivLevel=1, multipefaktor=1, add_headers=None):
    """Sender gluoner til de forskjellige transmitterne.
    Denne brukes av trådmodulen og blir kjørt en gang pr. transmitter"""
    ret_svar = {}
    utverdier={}
    #Lager midlertidig svar som ev. oversktives senere
    #Lock og skriv

    ret_svar['status']='0'
    ret_svar['reason']='Starter utsendelse'
    start = time.time()

    utverdier[tag] = ret_svar
    #start = time.time()
    #Sett opp headers
    if data_raw:
        headers = {"Content-type": "application/xml",
            "Accept": "*/*",
            "User-Agent":"Gluon 0.5.0 [no] (%s; U)"%sys.platform}
        if add_headers:
            headers.update(add_headers)
        data = data_raw
    else:
        headers = {"Content-type": "application/x-www-form-urlencoded",
            "Accept": "*/*",
            "User-Agent":"Gluon 0.5.0 [no] (%s; U)"%sys.platform}
        data = data_enc
    #Dele opp uri til protokoll, hostname, authentisering og url
    protokol, rest = uri.split('://', 1)
    if '@' in rest:
        aut, rest = rest.split('@', 1)
        token = base64.urlsafe_b64encode(aut)
        headers['Authorization'] = 'Basic ' + token

    host,url = rest.split('/',1)
    #print protokol,headers,host,url
    try:
        if protokol == 'https':
            conn = HTTPSConnection(host)
        else:
            conn = HTTPConnection(host)
        conn.request("POST", '/' + url,data, headers)

        ret_svar['reason'] = 'Sendt data - transmitter svarer ikke.'
        time.sleep(0.005)
    except:
        #Legge inn forskjellige verdier her
        ret_svar['reason'] = 'Kunne ikke lage forbindelse'
    else:
        if svar_fra_mottager:
            svar = conn.getresponse()
            #print dir(svar)
            ret_svar['status'] = svar.status
            ret_svar['reason'] = svar.reason
            ret_svar['location'] = svar.getheader('Location')
            if method == 'HEAD':
                ret_svar['msg'] = ''
            else:
                ret_svar['msg'] = svar.read()
            ret_svar['duration'] = "PT%sS" % (time.time() - start)

        else:
            tid = time.time() - start
            ret_svar['msg']='TID: %s HVEM: %s' % (tid,tag)
        conn.close()
    #Sjekk om vi har en 302
    if ret_svar['status']==302:
        #Vi sender videre i denne omgang
        if reqursivLevel<maxReqursivLevel:
            nyUrl = svar.getheader('Location')
            nytransmitter = tag + ":redirekt_%s" % reqursivLevel
            sendData(nyUrl,
            data_raw = data_raw,
            svar_fra_mottager = svar_fra_mottager,
            tag=nytransmitter,
            reqursivLevel = reqursivLevel + 1)
        #ret_svar['msg'] = nyUrl
    #Lock og skriv

    utverdier[tag]= ret_svar
    return utverdier


def sendMail(til, fra, emne, melding, alvorlighetsgrad = 2):
    "Sender en mail fra NRKs postsystem"
    # Lage melding
    # Men først lage et knep for emnefeltet.
    emne_enc = '=?utf-8?B?%s?=' % base64.b64encode(emne.encode('utf-8'))
    headers = 'From: %s\r\nTo: %s\r\nX-Priority: %s\r\nSubject: %s\r\n\Content-Type: text/plain; charset="UTF-8"r\n\r\n' % (fra, ", ".join(til),alvorlighetsgrad, emne_enc)
    msg = headers + melding
    #maexchowa01.nrk.no
    try:
        server = smtplib.SMTP('internsmtp.felles.ds.nrk.no')
        #server.set_debuglevel(1)
        server.sendmail(fra,til, msg.encode('utf-8'))
        server.quit()
    except:
        return msg

def checkProcess(processName):
    "Sjekker om prosesser er oppe eller ikke"
    f=popen('/bin/ps -A | /usr/bin/grep -c "%s"' % processName)
    result = f.read()
    f.close()
    i = int(result)
    #Siden grep er en prosess ved kjøringen trenger vi å trekke fra denne prosessen:
    return i-1

def returnTimezone():
    if time.localtime()[8]:
        return '+02:00'
    else:
        return '+01:00'

def ISOtilLengde(isoTid, error='tilgi'):
    tidsFeil = "Feil i konvertering fra ISO 8601 format."
    tid = 0.0
    if not isoTid:
        if not error == 'tilgi':
            raise tidsFeil("Begynner ikke med P")
        else:
            return tid

    if isoTid[0]!='P':
        if not error == 'tilgi':
            raise tidsFeil("Begynner ikke med P")
        else:
            return tid
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

def ISOtilDato(dato,sekunder=0, sql=0):
    offsett = 0
    if not dato:
        return 0
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

def hentVerdier(noder, lim=''):
    s = ''
    for node in noder:
        if node.nodeType == node.TEXT_NODE:
            s += node.data + lim
    return s

def finnVerdi(xmlobjekt,path, entity=False, nodetre=False):
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
                return xmlobjekt.getAttribute(node[1:])

    except IndexError:
        if nodetre:
            return []
        else:
            return ''
    if nodetre:
        return xmlobjekt
    if not entity:
        return hentVerdier(xmlobjekt.childNodes)
    else:
        return entetyReplace(hentVerdier(xmlobjekt.childNodes))

def lagBiografi(contributor, format = 'enkel'):
    "parser for dates grenen av navnetypen"
    hendelser = finnVerdi(contributor, 'events/+event', nodetre=True)
    f=''
    d=''
    for hendelse in hendelser:
        hendelsetittel =  finnVerdi(hendelse, 'metadata_DC/titles/title', nodetre=False)
        if format == 'enkel':
            if hendelsetittel.lower() == 'fødsel':
                f = finnFuzzyDate(hendelse, 'metadata_DC/dates/+fuzzy_date', filter='event', dictOutput = False, output = ['year'])
            if hendelsetittel.lower() == 'død':
                d = finnFuzzyDate(hendelse, 'metadata_DC/dates/+fuzzy_date', filter='event', dictOutput = False, output = ['year'])

        else:
            pass
            #Legg inn kode for en samla biografi her

    if format == 'enkel':
        if f and d:
            return '(%s-%s)' % (f,d)
        elif f:
            return '(%s-)' % f
        elif d:
            return '(?-%s)' % f
    return ''

def unique(list):
    "returnerer en kopi av liste i normalisert utgave"
    s =[]
    for i in list:
        if i not in s:
            s.append(i)
    return s



def finnNorsk(node, path, log=[]):
    "Returnerer en dictionary med Norsk på norsk argumenter, tar en komplett gluonmetadatanode. Returnerer og en begrunnelse for analysen"
    #Creator
    composerRoles = ['Komponist', 'Samplet', 'Del-bidragsyter musikk', 'Sitert musikk']
    lyricistRoles = ['Tekstforfatter', 'Librettist', 'Oversetter', 'Bearbeidelse tekst', 'Del-bidragsyter tekst', 'Sitert tekst', u'Redaktør']
    performerRoles = [u'Utøver','Solist','Musiker', 'Tale', 'Vokalist', 'Kor', 'Band', 'Dirigent', 'leder','Ensemble', 'Korps', 'Storband']
    norskKoder = ['NOR']
    """
    Vedtektene sier:
Minst 35 pst. av musikken som spilles skal være norsk, med vekt på norskspråklig og/eller norskkomponert musikk.

Dette betyr at minst ett av følgende kriterier må være oppfylt for at det skal kategoriseres som ”norsk musikk”: norsk utøver, norsk språk, norsk opphavsperson.
Internt trenger vi å registrere ett tall pr kriterium – til sammen tre tall. Disse slås sammen, og summen utgjør det vi rapporterer som ”spilt norsk musikk.

”Med vekt på” betyr at over halvparten av musikken som registreres som ”norsk” må ha enten norsk språk eller norsk opphavsperson. Vi må altså rapportere utad et totaltall på ”norsk musikk”, og et tall som omfatter andelen ”norsk språk og/eller norsk opphavsperson”.

For vår egen del vil det være nyttig å registrere hvilke sanger/stykker som har ”delvis norsk” språk/utøver/opphavsperson – så må vi vurdere om det er behov for å ta med disse tallene i totaltallet, eller om det ikke skal omfattes av terminologien ”norsk musikk” hvis bare ett av kriteriene (for eksempel opphavsperson) er delvis oppfylt.
 """
    reson = ''
    #Først finne opphavsmenn
    #**** Tilpasse seg det over
    #Nullstille tellere
    cc = 0
    tc = 0
    cl = 0
    tl = 0
    cp = 0
    tp = 0

    contributors = finnVerdi(node, path, nodetre=True)
    for contributor in contributors:
        fp = False
        fl = False
        fc = False
        navn = finnVerdi(contributor, 'name', nodetre=False)
        nasjon = finnVerdi(contributor, 'nationality', nodetre=False)
        roles = finnVerdi(contributor,'+role',entity = False, nodetre=True)
        for r in roles:
            rolePart = finnVerdi(r,'',entity = 0).strip()
            if rolePart in composerRoles and not fc:
                fc = True
                if nasjon in norskKoder:
                    cc += 1
                    log.append("%s er norsk %s." % (navn, rolePart))
                else:
                    log.append("%s er utenlandsk %s." % (navn, rolePart))
                tc +=1

            if rolePart in lyricistRoles and not fl:
                fl = True
                if nasjon in norskKoder:
                    cl += 1
                    log.append("%s er norsk %s." % (navn, rolePart))
                else:
                    log.append("%s er utenlandsk %s." % (navn, rolePart))
                tl +=1

            if rolePart in performerRoles and not fp:
                fp = True
                if nasjon in norskKoder:
                    cp += 1
                    log.append("%s er norsk %s." % (navn, rolePart))
                else:
                    log.append("%s er utenlandsk %s." % (navn, rolePart))
                tp +=1

    if tc == 0:
        tc = 1
    if tl == 0:
        tl = 1
    if tp == 0:
        tp = 1
    log.append("%s, %s, %s:%s/%s" % (float(cc)/tc, float(cl)/tl, float(cp)/tp, cp, tp))
    return float(cc)/tc, float(cl)/tl, float(cp)/tp



def finnNasjon(node, path, filter=None):
    "Returnerer en liste med nasjonaliteter funnet i en node, og disses underelementer"

    s=[]
    contributors = finnVerdi(node, path, nodetre=True)
    for contributor in contributors:
        nasjon = finnVerdi(contributor, 'nationality', nodetre=False)
        if filter:
            roles = finnVerdi(contributor,'+role',entity = False, nodetre=True)
            for r in roles:
                rolePart = finnVerdi(r,'',entity = 0).strip()
                if rolePart in filter:
                    #Vi har en match
                    s.append(nasjon)
        else:
            #Vi legger til alt
            s.append(nasjon)


    return s


def finnRoller(node, path, entity=False, filter=None, filter2=None, filter3=None, filter4=None,
    kunEtternavn=False, navnSkille=False, etterNavn_forNavn=False, alias=False, aliasSufix=False,
    vaskWS=True, medRolle=False, setSufix='', setPrefix='',
    roleSufix=False, biroller=False, alleroller=False, nasjonalitet=False, landliste=None, biografi=False, dictOutput=False, targetLength=1000, req=None, aldriRolle=None, kunPersoner=False):
    """Returnerer en diktionary med roller
    Støtter flere roller pr. person
    filter - kun personer med denne rollen kommer med, spesialtilfelle ved Utøver, tar da bare med roller som ikke er med i notPerformerslisten
    filter2 - kun personer som har denne rollen også, dvs filter AND filter
    filter3 - tar ikke med folk som har denne rollen
    filter4 - tar ikke med folk som bare har denne rollen(e)
    kunEtternavn - undertrykker fornavnene
    navneskille - Beholder for og etternavn i hver sin variabel, ellers settes disse sammen
    aliasSufix - Setter navnevariant i qutes etter navnet.
    vaskWs - Vasker unødvendige mellomrom
    medRolle - gir et formatert liste med hovedrollene foran person(ene)
    setSufix - setter denne verdien  etter navnet, hvis det ikke er noen rolle generert
    setPrefix - setter denne verdien  før navnet , hvis det ikke er noen rolle generert
    roleSufix - legger på paranteser med rollene
    biroller - leggere bare birollene i parantesene (Filter må være satt)
    nasjonalitet - legger ut nasjonalitet i klammer
    landliste - oppslagshashobjekt som kan brukes ved ekspandering av ISO koder
    biografi - legger ut fødsel og dødsår i parentes
    dictOutput - sender fra seg resultatet som en dictionary
    targetLength - prøver å holde seg under den opgitte lenge for dataene"""
    #TODO legge inn støtte for at det bare er roller fra en hvis rolleliste som skal ut i rolle betegnelsene
    #Støtte for å filtere der birolle er den samme som hovedrolle

    #Rydde opp dersom vi spesifikt spør etter en rolle som står på aldriRolle listen


    #Legge inn en funksjon som gjør at en tar vekk støtterollene og stryker persjonen dersom dette var den eneste rollen.

    if not aldriRolle:
        aldriRolle = ['Bidragsyter','Opphavsmann','Solist']

    try:
        if filter in aldriRolle:
            aldriRolle.remove(filter)
    except:
        pass
    try:
        if filter2 in aldriRolle:
            aldriRolle.remove(filter2)
    except:
        pass

    #Dersom filter er satt til Utøver, så skal alle støtteroller ignoreres

    if filter == u'Utøver':
        aldriRolle.extend(notPerformers)

    s = {}
    l = []
    contributors = finnVerdi(node, path, nodetre=True)
    for contributor in contributors:
        if finnVerdi(contributor, 'name') == '/Diverse/':
            continue
        if kunPersoner:
            if finnVerdi(contributor, 'name/@person').lower()=='false':
                continue
        solist = False
        if nasjonalitet or dictOutput:
            nasjon = finnVerdi(contributor, 'nationality', nodetre=False)
            if nasjon and landliste:
                try:
                    nasjon = landliste[nasjon]
                except:
                    pass
            if nasjon:
                nasjonsklamme = ' {%s}' % nasjon
            else:
                nasjonsklamme = ''
        else:
            nasjonsklamme = ''
            nasjon = ''
        role = ''
        totalRoles = []
        #sjekke om vi har flere roller:
        roles = finnVerdi(contributor,'+role',entity = False, nodetre=True)
        filtrert = False
        for r in roles:
            rolePart = finnVerdi(r,'',entity = 0).strip()
            #En liten fix for inkonsikvens i DMA
            #vokal står til vokalist som bass står til vokalist
            if rolePart.lower() == 'vokalist':
                rolePart = 'vokal'

            #Ny patch

            if len(roles)<5 and filter==u'Utøver' and rolePart=='Musiker':
                #Da har vi en situasjon der vi bare skal betrakte musikeren som utøver
                rolePart = u'Utøver'

            try:
                if rolePart in filter4:
                    continue

            except:
                pass

            try:
                if rolePart in filter3:
                    filtrert = True
                    #Da skal ikke denne personen være med
            except:
                #Vil feile dersom filteret ikke er satt
                pass
            if rolePart in aldriRolle:
                if rolePart.lower() == 'solist':
                    solist = True
                continue
            if filter and filter != u'Utøver':
                #Filteret vil altid settte dette til hovedrollen
                #req.write(repr(rolePart))
                if rolePart in filter:
                    role = rolePart
                #role = rolePart
            else:
                #Vi skal bruke første rollen, rollen er ikke satt i utgangspunktet, derfor vil dette virke:
                if not role:
                    role = rolePart
            totalRoles.append(rolePart)
        if filtrert:
            continue
        if filter2:
            if not filter2 in totalRoles:
                continue

        #Dersom vi nå har filter og ingen rolle så kan vi likesågodt gi oss
        if filter and not role:
            continue
        #Finne første rolle bruke denne som key, såfremt restriktivflagget ikke er satt
        if not role:
            role = 'ingenRolle'
        person = finnVerdi(contributor, 'name/@person', entity = entity)
        fornavn =  finnVerdi(contributor, 'given_name', entity = entity)
        #Finne ev. alias
        otherNames = finnVerdi(contributor, '+other_name', entity = entity, nodetre=True)
        aliasNavn = ''
        for otherName in otherNames:
            otherNameType = finnVerdi(otherName, '@label')
            if otherNameType in ['ALIAS', 'BRUKT NAVN', 'TIDLIGERE NAVN', 'Alias', 'Brukt navn', 'Tidligere navn']:
                #da har vi et alias
                #Sjekke om aliaset er i riktig kontekst
                #F. eks kan en ha et alias som utøver og et som produsent

                aliasRoles = finnVerdi(otherName, '+role', entity = entity, nodetre=True)#***Sjekke for flere roller

                for aliasRoleNode in aliasRoles:
                    aliasRole = finnVerdi(aliasRoleNode, '')

                    if aliasRole == filter:
                        aliasNavn = finnVerdi(otherName, 'name')
                        if otherNameType in ['BRUKT NAVN', 'TIDLIGERE NAVN', 'Brukt navn', 'Tidligere navn'] and ', ' in aliasNavn:
                            #Vi trenger å snu for og etternavn
                            Aetternavn, Afornavn = aliasNavn.split(', ')
                            aliasNavn = "%s %s" % (Afornavn, Aetternavn)
                #break - går igjennom hele lista uansett

        if kunEtternavn:
            fornavn = ''
        navn = finnVerdi(contributor, 'family_name', entity = entity)
        if not navn:
            navn = finnVerdi(contributor, 'name', entity = entity)
            if finnVerdi(contributor, 'name/@person').lower()=='true':
                if ',' in navn:
                    ettern, forn = navn.split(',',1)
                    navn = forn + ' ' + ettern
                    fornavn = ''

        if not navn:
            navn = finnVerdi(contributor, 'family_name/@reference', entity = entity)
        if biografi:
            biografiParantes = " %s" % lagBiografi(contributor, format = 'enkel')
        else:
            biografiParantes = ''
        #Legge på endringer i navn og alias
        if alias and aliasNavn:
            fornavn = ''
            navn = aliasNavn
        if aliasSufix and aliasNavn and aliasNavn != navn:
            aliasHerme = ' "%s"' % aliasNavn
        else:
            aliasHerme = ''
        rolleParantes = ''
        if roleSufix or (dictOutput and biroller):
            if biroller and filter:
                try:
                    totalRoles.remove(filter)
                except:
                    #Filter er lik utøver som er litt spesielt, vi bare ignorerer
                    pass
                if filter2:
                    totalRoles.remove(filter2)
                #Egen regel for vokalister og ny visning
                if 'vokal' in totalRoles:
                    if len(totalRoles)==2:
                        if totalRoles[1] in ['sopran','mezzosopran','mezzo','alt','tenor','kontratenor','bass']:
                            totalRoles.remove('vokal')
                if len(totalRoles)==0:
                    rolleParantes = ''
                else:
                    rolleParantes = ' (' + ', '.join(totalRoles) + ')'
            else:
                rolleParantes = ' (' + ', '.join(totalRoles) + ')'
        if 'Dirigent' in rolleParantes and ',' in rolleParantes and not dictOutput and not alleroller:
            rolleParantes = ' (Leder)'
        if 'Dirigent' in rolleParantes and ',' in rolleParantes and not dictOutput and alleroller:
            rolleParantes = rolleParantes.replace('Dirigent','Leder')

        if not roleSufix:
            rolleParantes = ''
        #For rolleparanteser som settes fra oppkallet
        if setSufix and not rolleParantes:
            rolleParantes = setSufix
        if vaskWS:
            fornavn = fornavn.rstrip()
            navn = navn.rstrip()
        #Dersom vi skal ha biroller og dictOutput så bruker vi birollene som rolle
        if dictOutput and biroller:
            if totalRoles:
                #Prioritere dirigentrollen, og finne ut om dirigent også har en musikker rolle
                #Vi bruker rollen Leder for slike tilfeller
                if "Dirigent" in totalRoles:
                    if len(totalRoles)>1:
                        #En instrumentalist leder orkesteret
                        role = "Leder"
                        totalRoles.remove("Dirigent")
                    else:
                        role = "Dirigent"
                        totalRoles.remove("Dirigent")
                else:
                    role = totalRoles[0]
                    totalRoles.remove(role)

        if dictOutput:
            #Endre roller
            if person=='false' and role == u'Utøver':
                #Sjekke ulike tilstander
                role = 'Ensemble'



            if not navnSkille:
                if fornavn:
                    navn = fornavn + ' ' + navn
                    fornavn = ''

            if fornavn:
                if role in s:
                    s[role].append({'fornavn':fornavn,'navn':navn, 'nasjon':nasjon, 'solist':solist, 'person':person})
                else:
                    s[role] = [{'fornavn':fornavn,'navn':navn, 'nasjon':nasjon, 'solist':solist, 'person':person}]
            else:
                if role in s:
                    s[role].append({'navn':navn, 'nasjon':nasjon, 'solist':solist, 'person':person})
                else:
                    s[role] = [{'navn':navn, 'nasjon':nasjon, 'solist':solist, 'person':person}]
            #Nå vil rollen være registrert, vi legger på alle rollene:
            if totalRoles:
                #Legger på ekstraroller hvis de fremdeles finnes
                s[role][-1]['extraRoles'] = totalRoles

        else:
            if fornavn:
                if role in s:
                    if etterNavn_forNavn:
                        s[role].append(setPrefix + navn + ', ' + fornavn + aliasHerme + rolleParantes.lower() + biografiParantes + nasjonsklamme)
                    else:
                        s[role].append(setPrefix + fornavn + ' ' + navn + aliasHerme + rolleParantes.lower() +  biografiParantes + nasjonsklamme)
                else:
                    if etterNavn_forNavn:
                        s[role] = [setPrefix + navn + ', ' + fornavn + aliasHerme + rolleParantes.lower() +  biografiParantes + nasjonsklamme]
                    else:
                        s[role] = [setPrefix + fornavn + ' ' + navn + aliasHerme + rolleParantes.lower() +  biografiParantes + nasjonsklamme]

                if etterNavn_forNavn:
                    l.append(setPrefix + navn + ', ' + fornavn + aliasHerme + rolleParantes.lower() + biografiParantes + nasjonsklamme)
                else:
                    l.append(setPrefix + fornavn + ' ' + navn + aliasHerme + rolleParantes.lower() +  biografiParantes + nasjonsklamme)

            else:
                if role in s:
                    s[role].append(setPrefix + navn + aliasHerme + rolleParantes.lower() +  biografiParantes + nasjonsklamme)
                else:
                    s[role] = [setPrefix + navn + aliasHerme + rolleParantes.lower() +  biografiParantes + nasjonsklamme]
                l.append(navn + aliasHerme + rolleParantes.lower() +  biografiParantes + nasjonsklamme)

    if dictOutput:
        return s

    if filter:
        if filter in s or filter == u'Utøver':
            if medRolle:
                returverdi = {filter:s[filter]}#Filteret er en rolleverdi her, derfor merker vi bare resultatet med rollen her
                if len(''.join(returverdi)) > targetLength:
                    #Vi for prøve å spare litt
                    return  finnRoller(node, path, filter=filter, filter2=filter2, kunEtternavn=True, navnSkille=navnSkille, etterNavn_forNavn=etterNavn_forNavn, vaskWS=vaskWS, medRolle=medRolle,
    roleSufix=False, biroller=False, nasjonalitet=False, biografi=False, dictOutput=dictOutput, targetLength=targetLength + 25)
                else:
                    return returverdi
            else:
                if filter == u'Utøver':
                    returverdi =  l
                else:
                    returverdi =  s[filter]
                if len(''.join(returverdi)) > targetLength:
                    return  finnRoller(node, path, filter = filter, filter2 = filter2, kunEtternavn = True, navnSkille = navnSkille, etterNavn_forNavn = etterNavn_forNavn, vaskWS = vaskWS, medRolle = medRolle,
    roleSufix = False, biroller = False, nasjonalitet = False, biografi = False, dictOutput = dictOutput, targetLength = targetLength + 25)
                else:
                    return returverdi
        else:
            return []

def finnFuzzyDate(node, path, filter=None, dictOutput = True, output = []):
    """Behandler gluonklassen fuzzydate.
    Begrensning: Returnerer bare første datoobjektet som er argument

    TODO: Bygg ut med flere formaterings muligheter  19?? f. eks."""
    s = {}
    datoen = None
    datoer =  finnVerdi(node, path, nodetre=True)

    for dato in datoer:
        label = finnVerdi(dato,'@label', entity = 0)
        if label == filter:
            #Vi har funnet riktig datoobjekt
            datoen = dato
            break
    if not datoen:
        #Vi har ikke datoen som det søkes etter
        if dictOutput:
            return {}
        else:
            return ''
    yearInterval = (finnVerdi(datoen,'start/@startYear', entity = 0), finnVerdi(datoen,'end/@startYear', entity = 0))
    if yearInterval != ('', ''):
        s['year'] = yearInterval
    monthInterval = (finnVerdi(datoen,'start/@startMonth', entity = 0), finnVerdi(datoen,'end/@startMonth', entity = 0))
    if monthInterval != ('', ''):
        s['month'] = monthInterval
    dayInterval = (finnVerdi(datoen,'start/@startDay', entity = 0), finnVerdi(datoen,'end/@startDay', entity = 0))
    if dayInterval != ('', ''):
        s['day'] = dayInterval

    if dictOutput:
        return s

    if 'year' in output and 'year' in s:
        return s['year'][0]

    if 'digasdate' in output:
        #Endres til også å støtte sluttdatoene
        if 'year' in s:
            year = s['year'][0]
        else:
            year = '????'

        if 'month' in s:
            month = s['month'][0]
            if len(month)==1:month='0'+month
        else:
            month = '??'

        if 'day' in s:
            day = s['day'][0]
            if len(day)==1:day='0'+day
        else:
            day = '??'

        return "%s-%s-%s" % (year, month, day)
    #otherwise
    return ''

def finnDestinasjoner(node, path='gluon/head/transmitters/+transmitter'):
    "Returnerer en liste med destinasjoner"
    s = []
    transmitters = finnVerdi(node, path, nodetre=True)
    for transmitter in transmitters:
        ref = finnVerdi(transmitter,'@quark', entity=0)
        if ref:
            s.append(ref)
    return s

def finnTyper(node, path, filter=None, navnSkille=False):
    "Returnerer en diktionary med typer, eller en liste"
    s = {}
    typer = finnVerdi(node, path, nodetre=True)

    for type in typer:
        #Finne rolle bruke denne som key
        ref = finnVerdi(type, '@reference', entity=0)
        if not ref:
            ref = 'ingenRef'
        typebetegnelse =  finnVerdi(type, '', entity=1)

        if ref in s:
            s[ref].append(typebetegnelse)
        else:
            s[ref] = [typebetegnelse]


    if filter:
        if filter in s:
            return s[filter]
        else:
            return []
    else:
        return s


def finnBeskrivelse(node, path, filter = None, filterFelt='@label'):
    """Returnerer en liste av dictionaries som gjenspeiler et "description" felt."""
    s = {}
    relasjoner = finnVerdi(node, path, nodetre = True)

    for relasjon in relasjoner:
        #Finne rolle bruke denne som key
        ref = finnVerdi(relasjon, filterFelt, entity = 0)
        if not ref:
            ref = 'ingenLabel'
        relasjonsbetegnelse =  finnVerdi(relasjon,'', entity=1)

        if ref in s:
            s[ref].append(relasjonsbetegnelse)
        else:
            s[ref] = [relasjonsbetegnelse]


    if filter:
        if filter in s:
            return s[filter]
        else:

            return []
    else:
        return s
    return "kommentar"

def finnRelasjoner(node, path, filter = None):
    """Returnerer en liste av dictionaries som gjenspeiler en relasjonsnode."""
    s = {}
    relasjoner = finnVerdi(node, path, nodetre=True)

    for relasjon in relasjoner:
        #Finne rolle bruke denne som key
        ref = finnVerdi(relasjon,'@label', entity = 0)
        if not ref:
            ref = 'ingenLabel'
        relasjonsbetegnelse =  finnVerdi(relasjon,'', entity = 0)

        if ref in s:
            s[ref].append(relasjonsbetegnelse)
        else:
            s[ref] = [relasjonsbetegnelse]


    if filter:
        if filter in s:
            return s[filter]
        else:

            return []
    else:
        return s

def finnTitler(node, path, filter=None):
    """Returnerer en liste av dictionaries som gjenspeiler en relasjonsnode."""
    s = {}
    titler = finnVerdi(node, path, nodetre=True)

    for tittel in titler:
        #Finne rolle bruke denne som key
        ref = finnVerdi(tittel,'@label', entity=0)
        if not ref:
            ref = 'ingenLabel'
        relasjonsbetegnelse =  finnVerdi(tittel,'', entity=0)

        if ref in s:
            s[ref].append(relasjonsbetegnelse)
        else:
            s[ref] = [relasjonsbetegnelse]


    if filter:
        if filter in s:
            return s[filter]
        else:

            return []
    else:
        return s


def entetyReplace(s):
    s = s.replace('&','&amp;')

    return s


def finnUnger(noder,tag,kunEn=0):
    s=[]
    for node in noder:
        if node.nodeType == node.ELEMENT_NODE:
            if node.tagName == tag:
                s.append(node)
                if kunEn: return s

    return s

if __name__=='__main__':
        print('Syntax ok')
