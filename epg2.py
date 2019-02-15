#! /usr/local/bin/python
# -*- coding: UTF-8 -*-

"""Gluon til dab-epg"""

#TODO:
# Dato feil !!!!!!

#Endre genre

#Få natta på riktig dokument (databaseløsning)

#Sjekkke for & og andre entetyes, entety replace

#filtrere ut fjernsynskanaler

#longTitle<120
#MediumTitle<16!
#ShortTitle<

import time
from os import environ
from cgi import parse_qs
from sys import stdin, exc_info
import xml.dom.minidom
import xml.utils.iso8601 as iso
import traceback
import re
import MySQLdb as mdb
import sendTilDab
from epg import erDagerFram
from felles import kanalSW
from dbConn import database

#erDagerFram(dato,dager,ofset=0, kunSendedogn=0)

epgKey = 'epg2' 
localwrite = False #Skriver filene som sendes til dab også til filsystemet
storage = '/var/www/html/epg/'
#storage = ''

tvAnyTime = {
1: ('Undefined', None), 
2: ('3.1.1', 'Content.Non-fiction.News'),
3: ('3.1.1.16', 'Content.Non-fiction.News.Current Affairs'), 
4: ('1.2','Intention.Information'),  
5: ('3.2', 'Content.Sport'), 
6: ('3.1.3.6', 'Content.Non-fiction.General Non-fiction.Education'),  
7: ('3.4', 'Content.Fiction'), 
8: ('3.1.4', 'Content.Non-fiction.Arts & Media'), 
9: ('3.1.6', 'Content.Non-fiction.Sciences'), 
10: ('3.1', 'Content.Non-fiction'), 
11: ('3.6.4.1','Content.Music and Dance.Pop-rock.Pop'), 
12: ('3.6.4', 'Content.Music and Dance.Pop-rock'), 
13: ('3.6.3.2', 'Content.Music and Dance.Background Music.Easy Listening'),
14: ('3.6.1.5', 'Content.Music and Dance.Classical.Light Classical'),
15: ('3.6.1.2', 'Content.Music and Dance.Classical.Classical'),
16: ('3.6', 'Content.Music and Dance'),
17: ('3.1.1.13', 'Content.Non-fiction.News/Weather forecasts'),
18: ('3.1.3.5', 'Content.Non-fiction.General Non-fiction.Finance'),
19: ('4.2.1', 'Intended Audience.Age Groups.Children'),
20: ('3.1.3.2', 'Content.Non-fiction.General Non-fiction.Social'),
21: ('3.1.2.1', 'Content.Non-fiction.Philospphies of Life.Religious Philosophies'),
22: ('2.1.8', 'Format.Structured.Phone-in'),
23: ('3.3.5', 'Content.Leisure/Hobby.Travel/Tourism'),
24: ('3.3', 'Content.Leisure/Hobby'),
25: ('3.6.2', 'Content.Music and Dance.Jazz'),
26: ('3.6.6', 'Content.Music and Dance.Country and Western'),
27: ('3.6.9', 'Content.Music and Dance.World/Traditonal/Ethnic/Folk Music'),
28: ('3.6.3.5', 'Content.Music and Dance.Background Music.Oldies'),
29: ('3.6.9', 'Content.Music and Dance.World/Traditonal/Ethnic/Folk Music'),
30: ('2.1.4', 'Format.Structured.Documentary'),

}
 

keyMap = {	'N10':2,
			'N40':17,
			'N50':4,
			'E00':10,
			'B30':11,
			'B32':12,
			'R10':2,
			'R99':10,
			'K99':3,
			'H10':21,
			'S99':5,
			
			}

#def database(host = "160.68.118.48", user="tormodv", database="dab",passord="allmc21"):
#def database(host = "localhost", user="tormodv", database="dab",passord="allmc21"):
#	"Lager en databaseconnection."
#	d = mdb.connect(user=user,passwd=passord, host=host)
#	d.select_db(database)
#	return d

programmeTemplate = u"""      <programme shortId="%(shortId)s" id="%(progId)s">
%(names)s
         <epg:location>
            <epg:time time="%(publishedTime)s" duration="%(duration)s" actualTime="%(publishedTime)s" actualDuration="%(duration)s"/>
            <epg:bearer id="%(bearerId)s"/>
         </epg:location>
         <epg:mediaDescription>
            <epg:shortDescription><![CDATA[%(abstract)s]]></epg:shortDescription>
         </epg:mediaDescription>
%(genre)s
      </programme>
"""
#shortDescription max 180 tegn

longNameTemplate = "         <epg:longName><![CDATA[%s]]></epg:longName>"
mediumNameTemplate = "         <epg:mediumName><![CDATA[%s]]></epg:mediumName>"

siDocumentTemplate = """<?xml version="1.0" encoding="UTF-8"?> 
<serviceInformation xmlns:epg="http://www.worlddab.org/schemas/epg"  
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"  
xsi:schemaLocation="http://www.worlddab.org/schemas/epgSI/14 epgSI_14.xsd"  
 version="1"  
 creationTime="%(created)s"  
 originator="NRK"  
 serviceProvider="NRK"   
 system="DAB"> 
 <ensemble id="%(ensID)s"> 
  <epg:shortName xml:lang="no">NRK</epg:shortName> 
  <epg:mediumName xml:lang="no">%(blokknavn)s</epg:mediumName>
  %(services)s
  </ensemble> 
</serviceInformation>
  """ #Justere ensamble navnene
  
serviceTemplate = """ 
  <service> 
   <serviceID id="%(serviceID)s"/> 
   <epg:shortName xml:lang="no">%(kanalNavn)s</epg:shortName> 
   <epg:mediumName xml:lang="no">%(kanalNavnLang)s</epg:mediumName>
  </service> 
"""

documentTemplate = u"""<?xml version="1.0" encoding="UTF-8"?>
<epg xmlns:epg="http://www.worlddab.org/schemas/epg" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.worlddab.org/schemas/epgSI/14 epgSI_14.xsd" system="DAB">
   <schedule version="1" creationTime="%(created)s" originator="NRK">
      <scope startTime="%(startTime)s" stopTime="%(stopTime)s">
         <serviceScope id="%(bearerId)s"/>
      </scope >
      %(programmes)s
   </schedule>
</epg>
"""

verbose = False
fjernsyn = ['NRK1','NRK2']

quark = "dab:epg"



allow = ['10.0.1.17','*'] # Egentlig karuselladressene, eller *

def logg(txt):
	f=open(storage + 'logg.txt', 'a')
	f.write(txt + "\n")
	f.close()

def finnBlokker(d):
	"Returnerer alle blokkene fra dab-databasen, med eld"
	
	c = d.cursor()
	sql = """SELECT DISTINCT id, eld, navn FROM blokk;"""
	s = {}
	c.execute(sql)
	while 1:
		p = c.fetchone()
		if p:
			if p[1]:
				s[int(p[0])] = (p[1],p[2])
		else:
			break
	c.close()
	return s

def distriktskanal(d, kanal):
	"Returnerer en liste av underkanaler på grunnlag av et kanalnavn"
	#Finne først intern ideen på kanalen
	c = d.cursor()
	sql = """SELECT DISTINCT id FROM kanal WHERE navn =%s LIMIT 1;"""
	c.execute(sql,(kanal))
	row = c.fetchone()
	c.close()
	if row:
		kanalId = row[0]
	else:
		kanalId = 99
		if verbose:print "UKJENT KANAL", kanal.encode('latin-1')
		
	#Finne så hvilke distriktskanaler vi har
	
	c = d.cursor()
	sql = """SELECT navn FROM kanal WHERE foreldre_id =%s ;"""
	s = []
	c.execute(sql,(kanalId))
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
		c.execute(sql,(kanalId))
		while 1:
			p = c.fetchone()
			if p:
				s.append(p[0]) 
			else:
				break
		c.close()
	return s



def lagBearerId(d, kanal,ECC='e2', eld='f201', SCIdS = '0'):
	"""Leverer en liste med en eller flere serviceIDer, avhengig av valg i admin grensesnitt"""
	
	s = []
	#Vi må utvide distriktskanalene
	kanalene =  distriktskanal(d, kanal)
	for kanal in kanalene:
	
	
		#Finne sld for kanal
		sld = finnSld(d, kanal)
		blokker = finnBlokker(d)
		#Blokker gir oss alle blokkene som er registrert som dab-blokker
		for blokkId in blokker:
			eld, blokkNavn = blokker[blokkId]
			#Hente visningsvalg
			visningsvalg = hentVisningsvalg(d, kanal, blokkId, datatype=epgKey, oppdatering = 1)
			if not epgKey in visningsvalg:
				logg(epgKey)
				logg(repr(visningsvalg))
				logg(kanal)
				logg('')
				continue
			s.append(("%s.%s.%s.%s" % (ECC, eld, sld,SCIdS), blokkNavn))
		
	return s


def lagServiceDesccription(d,blokkId, SCIdS='0'):
	"Lager en service description for alle kanalene som har epgKey"
	s=u''
	for kanal in finnKanaler(d):
		visningsvalg = hentVisningsvalg(d, kanal, blokkId, datatype=epgKey, oppdatering = 1)
		if not epgKey in visningsvalg:
			continue
		s += serviceTemplate % {'serviceID':"%s.%s" % (finnSld(d, kanal),SCIdS),
									'kanalNavn':kanal.upper(),
									'kanalNavnLang':finnKanalLabel(d, kanal, forceunicode=True)[:16]}
	
	return s

def finnKanaler(d, ikkeDistrikt = 0):
	"Returnerer alle kanalnavnene fra dab-databasen"
	c = d.cursor()
	if ikkeDistrikt:
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
	

	
def finnSld(d, kanal):
	"Henter ut sld for kanal med navn..."
	c= d.cursor()
	sql="""SELECT sld FROM kanal WHERE navn =%s LIMIT 1
;
"""
	c.execute(sql,(kanal))
	row = c.fetchone()
	c.close()
	if row:
		return row[0]
		
def finnKanalLabel(d, kanal, forceunicode=False):
	"Henter ut Langt kanalnavn for kanal med navn..."
	c= d.cursor()
	sql="""SELECT alias FROM kanal WHERE navn =%s LIMIT 1
;
"""
	c.execute(sql,(kanal))
	row = c.fetchone()
	c.close()
	if row:
		if forceunicode:
			return unicode(row[0],'iso-8859-1')
		else:
			return row[0]

def finnBlokknavn(d,blokkId, forceunicode=True):
	"Henter ut blokknavn ..."
	c= d.cursor()
	sql="""SELECT utbredelse FROM blokk WHERE id =%s LIMIT 1
;
"""
	c.execute(sql,(blokkId))
	row = c.fetchone()
	c.close()
	if row:
		if forceunicode:
			return unicode(row[0],'iso-8859-1')
		else:
			return row[0]


	
def hentVisningsvalg(d,kanal, blokkId, datatype=None, oppdatering = 0):
	"Henter ut visningsvalg og verdier for filterfunksjonen"
	#Først finner vi kanal_ID på kanalen.
	c= d.cursor()
	sql="""SELECT id FROM kanal WHERE navn =%s LIMIT 1
;
"""
	c.execute(sql,(kanal))
	row = c.fetchone()
	c.close()
	if row:
		kanalId = row[0]
	else:
		kanalId = 99
		print "UKJENT KANAL", kanal
		
	#Så sjekke om denne datatypen skal være breaking for den gitte kanalen
	#Dette kan være bestemt av datatypen også
	#if ':' in datatype:
	#	return datatype.split(':',1) # Gir en [datatype,'breaking'] type
		
	c= d.cursor()
	sql="""SELECT breaking from datatyper
INNER JOIN dataikanal ON dataikanal.datatype_id=datatyper.id
WHERE kanal_id=%s AND blokk_id=%s AND tittel=%s LIMIT 1;"""
	c.execute(sql,(kanalId,blokkId,datatype))
	row = c.fetchone()
	c.close()
	#print row, datatype, kanal
	try:
		if row[0]=='Y':
			return [datatype,'breaking']
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
		c.execute(sql,(kanalId,blokkId))
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
		c.execute(sql,(kanalId,blokkId))
		while 1:
			p = c.fetchone()
			if p:
				s.append(p[0])
			else:
				break
		c.close()
		return s
		
def sendDocument(dok, multiplex, type='epg', maxLevetid = 24, SendAtOnce = 1, EncodeEPG = 1, IncludeOldEpgFiles = 1):

	kanal_dab = 'epg1' #Vet ikke om denne er riktig
	listetype = 1
	#Send data til DAB
	
	start= sendTilDab.dabdato(time.time()) #DVS vi sender en liste som gjelder fra nå
	#Dersom vi har iteminfo er levetiden på listen lik den gjenværende tiden på det korteste innslaget
	levetid = 60 * 60 * maxLevetid #dvs i hele timer regnet om til sekunder
	
	stop = sendTilDab.dabdato(time.time() + levetid + 5 )  #5 sekunder ofset slik at infoen heller henger enn forsvinner like før en oppdatering
	
	#Lag kommando
	
	
	kommando = "SendDataEPG;%s;%s;%s;%s;%s;%s;%s;%s" % (
		multiplex,
		kanal_dab,
		listetype,#listetype Single=0,Loop=1,Background loop=2
		start,
		stop,
		SendAtOnce, #tells DGW to transmit the files at once. Possible values 0 = False, 1 = True. 
		EncodeEPG, #tells DGW to binary encode the files. Possible values 0 = False, 1 = True. 
		IncludeOldEpgFiles #tells DGW to binary encode the files. Possible values 0 = False, 1 = True. 
		)
		
	if verbose:print kommando
	
	#sendData(uri, kommando = None, feltListe = {}, liste = [], data_enc = None, mimetype = 'Content-Type: dab/datadls' ):
	svar = sendTilDab.sendData(
	'http://160.68.105.26:8888/api',
	#'http://localhost/cgi-bin/mimetest.py',
	kommando = kommando,
	feltListe = dok,
	mimetype = 'Content-Type: dab/dataepg'
	)['msg']
	
	return svar

def forkort(string,limit):
	"Forkorter en streng"
	#Kutte ved første ord
	if ' ' in string:
		string = string.split(' ')[0]
	return string[:limit]
		
def dictAdd(a,b):
	"Adderer postene i en dictionary"
	a.update(b)
	return a

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

def superfloat(streng):
	if not streng:
		return 0.0
	else:
		return float(streng)


def ISOtilLengde(isoTid, error='tilgi'):
	tidsFeil = "Feil i konvertering fra ISO 8601 format."
	tid = 0.0
	if not isoTid:
		if not error == 'tilgi':
			raise tidsFeil,"Begynner ikke med P"
		else:
			return tid
	
	if isoTid[0]!='P':
		if not error == 'tilgi':
			raise tidsFeil,"Begynner ikke med P"
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

def hentVerdier(noder,lim='', unicode = False):
	s=''
	for node in noder:
		if node.nodeType == node.TEXT_NODE:
			s+=node.data + lim
	if unicode:
		return s
	else:
		return s.encode('iso-8859-1','replace')
	
def finnVerdi(xmlobjekt,path,entity = False, nodetre = False, unicode = True):
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
				if unicode:
					return xmlobjekt.getAttribute(node[1:])
				else:
					return xmlobjekt.getAttribute(node[1:]).encode('iso-8859-1','replace')
				
	except IndexError:
		return ''
	if nodetre:
		return xmlobjekt
	if not entity:
		return hentVerdier(xmlobjekt.childNodes, unicode = unicode)
	else:
		return entetyReplace(hentVerdier(xmlobjekt.childNodes, unicode = unicode))

def finnRoller(node, path, filter = None, filter2 = None, navnSkille = False, vaskWS = True, medRolle = False, roleSufix = False, dictOutput = False):
	"""Returnerer en diktionary med roller
	Støtter flere roller pr. person
	filter - kun personer med denne rollen kommer med
	filter2 - kun personer som har denne rollen også, dvs filter AND filter
	navneskille - Beholder for og etternavn i hver sin variabel, ellers settes disse sammen
	vaskWs - Vasker unødvendige mellomrom
	medRolle - gir et formatert liste med hovedrollene foran person(ene)
	roleSufix - legger på paranteser med rollene
	dictOutput - sender fra seg resultatet som en dictionary"""
	s = {}
	contributors = finnVerdi(node, path, nodetre=True)
	for contributor in contributors:
		role = ''
		totalRoles = []
		#sjekke om vi har flere roller:
		roles = finnVerdi(contributor,'+role',entity = 0, nodetre=True)
		for r in roles:
			rolePart = finnVerdi(r,'',entity = 0)
			if filter:
				#Filteret vil altid settte dette til hovedrollen
				if rolePart in filter:
					role = rolePart
				
			else:
				#Vi skal bruke første rollen, rollen er ikke satt i utgangspunktet, derfor vil dette virke:
				if not role:
					role = rolePart
			totalRoles.append(rolePart)
		if filter2:
			if not filter2 in totalRoles:
				continue
				
		#Dersom vi nå har filter og ingen rolle så kan vi likesågodt gi oss
		if filter and not role:
			continue
		#Finne første rolle bruke denne som key, såfremt restriktivflagget ikke er satt
		if not role:
			role = 'ingenRolle'
		fornavn =  finnVerdi( contributor,'given_name', entity = 1)
		navn = finnVerdi( contributor,'family_name', entity = 1)
		if roleSufix:
			rolleParantes = ' (' + ','.join(totalRoles) + ')'
		else:
			rolleParantes = ''
		if vaskWS:
			fornavn = fornavn.rstrip()
			navn = navn.rstrip()
		if navnSkille:
		
			if fornavn:
				if role in s:
					s[role].append({'fornavn':fornavn,'navn':navn})
				else:
					s[role] = [{'fornavn':fornavn,'navn':navn}]
			else:
				if role in s:
					s[role].append({'navn':navn})
				else:
					s[role] = [{'navn':navn}]
			#Nå vil rollen være registrert, vi legger på alle rollene:
			s[role][:-1]['totalRoles'] = totalRoles
			
		else:
			if fornavn:
				if role in s:
					s[role].append(fornavn + ' ' + navn + rolleParantes)
					
				else:
					s[role] = [fornavn + ' ' + navn + rolleParantes]
			else:
				if role in s:
					s[role].append(navn + rolleParantes)
				else:
					s[role] = [navn + rolleParantes]
		
	if dictOutput:
		return s
		
	if filter:
		if filter in s:
			if medRolle:
				return {filter:s[filter]}#Filteret er en rolleverdi her, derfor merker vi bare resultatet med rollen her
			else:
				return s[filter]
		else:
			return []
	
		
def finnTyper(node, path, filter = None, navnSkille = False):
	"Returnerer en diktionary med typer, eller en liste"
	s = {}
	typer = finnVerdi(node, path, nodetre=True)
	
	for type in typer:
		#Finne rolle bruke denne som key
		ref = finnVerdi(type,'@reference', entity = 0)
		if not ref:
			ref = 'ingenRef'
		typebetegnelse =  finnVerdi(type,'', entity = 1)
		
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


def finnRelasjoner(node, path, filter = None):
	"""Returnerer en liste av dictionaries som gjenspeiler en relasjonsnode."""
	s = {}
	relasjoner = finnVerdi(node, path, nodetre=True)
	
	for relasjon in relasjoner:
		#Finne rolle bruke denne som key
		ref = finnVerdi(relasjon,'@label', entity = 0)
		if not ref:
			ref = 'ingenLabel'
		relasjonsbetegnelse =  finnVerdi(relasjon,'', entity = 1)
		
		if ref in s:
			s[ref].append(relasjonsbetegnelse)
		else:
			s[ref] = [relasjonsbetegnelse]
		
	
	#feil		
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

def formatProdnummer(prodnummer):
	"Tar og skifter format på prodnumrene, PI lagrer dette i en kompprimert form"
	if not prodnummer:
		return ''
	
	return "%s %s/%s" % (prodnummer[:4],prodnummer[4:10],prodnummer[10:])

def finnUnger(noder,tag,kunEn=0):
	s=[]
	for node in noder:
		if node.nodeType == node.ELEMENT_NODE:
			if node.tagName == tag:
				s.append(node)
				if kunEn: return s
				
	return s
	
def siftDato(dato, ofset=0,format='', timezone='auto', sendedag=False):
	"""Formaterer datoobjekter til diverse SIFT formater,
format parameteret kan enten ha verdien:
tid ->          20051212:160000
TC ->			16:00:00:00
klokke - >      160000
klokke-kort ->  1600
defult ->       20051212
En ofset kan flytte tidspunktet
Timezone kan settes til gmt eller utc for TC verdier (der løpende lengde er nødvendig)
Timezone satt til auto vil bruke localtime dersom ikke datoen er 0
Sendedag satt til True gir korreksjon for sendedøgnets fra 0600: til 0600 regime.
"""
	if timezone == 'auto' and not dato:
		timezone = 'utc'
	if ofset:
		dato = dato + ofset
	if sendedag:	
		#Finner ut om det er natt og slikt
		if time.localtime(dato)[3]<6:
			dato = dato - 86400 # 86400 er sekunder i et døgn
		
	if format=='tid':
		return "%04i%02i%02i:%02i%02i%02i" % time.localtime(dato)[:6]
	elif format=='TC':
		if timezone == 'gmt' or timezone == 'utc':
			return "%02i:%02i:%02i:00" % time.gmtime(dato)[3:6]
		else:
			return "%02i:%02i:%02i:00" % time.localtime(dato)[3:6]
	elif format == 'klokke':
		return "%02i%02i%02i" % time.localtime(dato)[3:6]
	elif format == 'klokke-kort':
		return "%02i%02i" % time.localtime(dato)[3:5]
	else:
		return "%04i%02i%02i" % time.localtime(dato)[:3]


def siftLengde(sekund,format=''):
	"""Formaterer tider i sekunder til enten hmmss, mmmss, mmss m's" eller TC format"""
	#if not sekund:
	#	return ''
	if format=='hmmss':
		return "%01i%02i%02i" % (sekund/3600,(sekund % 3600) / 60, sekund % 60)
	elif format =='mmmss':
		return "%03i%02i" % ((sekund) / 60, sekund % 60)
	elif format =='mmss':
		return "%02i%02i" % ((sekund) / 60, sekund % 60)
	elif format == 'TC':
		return "%02i:%02i:%02i:%02i" % (sekund/3600,(sekund % 3600) / 60, sekund % 60, (sekund % 1) * 25)
	else:
		return "%4i'%02i\"" % ((sekund % 3600) / 60, sekund % 60)

def ISOdato(dato, tidssoneStreng):

	isodato =  "%04i-%02i-%02iT%02i:%02i:%02i" % time.localtime(dato)[:6]		
	if tidssoneStreng:
		return isodato + tidssoneStreng
	else:
		return isodato + 'Z'


def lagShortId(crid):	
	d=database()
	c=d.cursor()
	sql = """INSERT INTO shortcrid(crid, date)
			VALUES(
			%s,
			now()
			);"""
	c.execute(sql,(crid,))
	id = c.lastrowid
	c.close()
	d.close()
	return id % 16777215

		
def mapGenre(escortVerdier):
	"Mapper escortverdier til tilsvarende tty kode for bruk på dab"
	
	mal = """       <epg:genre href="urn:tva:metadata:cs:ContentCS:2002:%s">
	   <epg:name><![CDATA[%s]]></epg:name> 
	</epg:genre>
	"""
	s=''
	for escort in escortVerdier:
		escortKey = escort.split(' ')[0]
		try:
			pty = keyMap[escortKey]
		except KeyError:
			continue
			#Vi forbigår ukjente genre i stillhet
		s += mal % tvAnyTime[pty]
	
	return s

def lagProgramRadio(program, bearerId = 'bearer'):
	"""Formaterer PI programmer for dab epg"""
	#Header for nytt program
	s={}
	#ProgID
	identifier = finnVerdi(program,'metadata_DC/identifier')
	if not identifier:
		identifier = finnVerdi(program,'@dataid')
	s['progId'] = 'crid://nrk.no/%s' % identifier
	s['shortId'] = lagShortId(identifier)
	#title
	titleContent = finnVerdi(program,'metadata_DC/titles/title')
	if len(titleContent) <=16:
		s['names'] = mediumNameTemplate % titleContent
	else:
		s['names'] = mediumNameTemplate % forkort(titleContent,16) + "\n" + longNameTemplate % titleContent
		
	#Tid og lengde
	s['publishedTime'] = finnVerdi(program,'metadata_DC/dates/date_issued')
	s['duration'] = finnVerdi(program,'metadata_DC/format/format_extent')
	#ansambleID
	s['bearerId'] = bearerId
	#abstrakt
	s['abstract'] = finnVerdi(program,'metadata_DC/description/abstract')[:180] #Sette inn en sikkelig forkorte funksjon
	#Genre
	#s['genre'] = finnTyper(program,'metadata_DC/types/+type', filter = 'NRK-Escort') #mapGenre(
	#print finnTyper(program,'metadata_DC/subjects/+subject', filter = 'ESCORT')
	#print mapGenre(finnTyper(program,'metadata_DC/subjects/+subject', filter = 'ESCORT')) 
	s['genre'] = mapGenre(finnTyper(program,'metadata_DC/subjects/+subject', filter = 'ESCORT')) 
	
	
	return programmeTemplate % s


def parser(xmlstreng):
	"Returnerer en liste med programmer, samt vitale data som sendedato, kanal o.l."
	sendeplan = {}
	programmer = []
	pars = xml.dom.minidom.parseString(xmlstreng)
	lagetDato = finnVerdi(pars,'gluon/head/metadata_DC/dates/date_issued')
	if not lagetDato:
		lagetDato = finnVerdi(pars,'gluon/head/creator/@date')
		
	artID = finnVerdi(pars,'gluon/@artID')
	
	tabeller = pars.getElementsByTagName('tables')
	for tabell in tabeller:
	
		#Hente ut data om sendeplanen
		sendeplan['rapportDato'] = ISOtilDato(lagetDato)
		sendeplan['sendedagsdato'] = finnVerdi(tabell,'element/metadata_DC/dates/date_issued')
		kanal = finnVerdi(tabell,'element/@channel')
		if kanal.lower() in kanalSW:
			kanal = kanalSW[kanal.lower()]
		sendeplan['kanal'] = kanal
		#Hente ut hvert av programmene
		#print sendeplan['sendedagsdato']
		programmer = finnVerdi(tabell,'element/subelements/+element', nodetre = True)
		
	return artID, sendeplan, programmer

	
def main(dok):
	
	d = database()
	documentData = {}
	
	artID, sendeplan, programmer = parser(dok)
	#print artID, sendeplan, programmer
	#Vi lager en epg, med en placeholder for SID
	
	#Vi skal bare ha en hvis antall dager fram i tid
	
	#print erDagerFram(sendeplan['sendedagsdato'],3,  kunSendedogn= 1)
	if erDagerFram(sendeplan['sendedagsdato'],1,  kunSendedogn= 1) != 1:
		print OK(quark,melding="Sendeplan utenfor intervallet")
		return
	  
	documentData['bearerId'] = '%(bearerId)s' #Fiktiv verdi, som erstattes.
	programmes = ''
	for program in programmer:
	
		
		programmes += lagProgramRadio(program, bearerId= documentData['bearerId'])
		
		
	#Sette inn i programmal
	documentData['created'] = ISOdato(sendeplan['rapportDato'], False)
	documentData['programmes'] = programmes
	documentData['startTime'] = sendeplan['sendedagsdato']
	documentData['stopTime'] = ISOdato(ISOtilDato(sendeplan['sendedagsdato']) + 24*3600, sendeplan['sendedagsdato'][19:])
	
	document = documentTemplate % documentData
	
	#print document
	
	#Finne riktig bærerId
	#print 9999, sendeplan['kanal'], lagBearerId(d, sendeplan['kanal'])
	for sid, multiplex in lagBearerId(d, sendeplan['kanal']):
		document = document % {'bearerId':sid}
		
		documentName = siftDato(ISOtilDato(sendeplan['sendedagsdato'])) +'_'+ sid.replace('.','_') + '_PI.xml'
		#Sende over til dabsystemet
		
		
		sendDocument({'File0"; filename="%s' % documentName : document.encode('utf-8')}, multiplex)
		
		if localwrite:
			f = open(storage + documentName,'w')
			f.write(document.encode('utf-8'))
			f.close()
		
	
	#Lage service dokumenter for hver av blokkene
	
	blokker = finnBlokker(d)
	
	for blokkId in blokker:
		s = {}
		s['ensID'] = "e2.%s" % blokker[blokkId][0]
		s['created'] = ISOdato(sendeplan['rapportDato'], False)
		s['blokknavn'] = ("NRK %s" % finnBlokknavn(d,blokkId, forceunicode=True))[:16]
		s['services'] = lagServiceDesccription(d,blokkId, SCIdS='0')
		#print blokker
		document = siDocumentTemplate % s
		documentName = siftDato(ISOtilDato(sendeplan['sendedagsdato'])) + '_' + blokker[blokkId][0] + '_SI.xml'
		multiplex = blokker[blokkId][1]
		sendDocument({'File0"; filename="%s' % documentName : document.encode('utf-8')}, multiplex)
		
		if localwrite:
			f = open(storage + documentName,'w')
			f.write(document.encode('utf-8'))
			f.close()

	
	print OK(quark)
				
	
	
if (__name__=='__main__'):
		#Dette skal vaere et cgi skript
				
		print "Content-type: text/html"
		print
		
		if 'HTTP_PC_REMOTE_ADDR' in environ:
			fra = environ['HTTP_PC_REMOTE_ADDR']
		elif 'REMOTE_ADDR' in environ:
			fra = environ['REMOTE_ADDR']
		else:
			fra = ''	
		#Sjekke for gyldige adresser
		if not ('*' in allow or fra in allow):
			#dette er en feil
			print "Uautorisert tilgang!!!"
		else:
		
			try:
					lengde=int(environ['CONTENT_LENGTH'])
			except:
					print "Ingen POST argumenter"
					lengde =0
					
					f=open("item2.xml")
					#f=open("dok_iso.xml")
					xmldokument = ''
					while 1:
						
						try:
								blokk = f.read(8024)
								if blokk:
										xmldokument += blokk
								else:
										break
						except:
								break
			
					if len(xmldokument)<lengde:
							print ("Fikk ikke lest hele dokumentet")
			

					f.close()

					#Dette maa vaere hovedmeldingen til klienter i systemet.
			if lengde > 0:
					
					f = stdin
					xmldokument = f.read(lengde)
					if xmldokument[:6]!='<?xml version='[:6]:
							xmldokument = parse_qs(xmldokument)['dok'][0] #['dok'] ender i en liste....
							#Må endre lengden også da
							lengde = len(xmldokument)  
			try:				
				alfa = main(xmldokument)
		
			except:
				type, val, tb = exc_info()
				msg = "".join(traceback.format_exception(type, val, tb))
				print error("nr10",quark, melding=msg)
	
	
			else:
			
				pass
		
				#print OK(quark)

		
