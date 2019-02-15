#! /usr/bin/env python
# -*- coding: utf-8 -*-

import xml.dom.minidom
import string
import urllib
import os
import time
import cgi
import sys
import MySQLdb as mdb
import re
from threading import Lock, Thread
from urllib import urlencode
from httplib import HTTPConnection
from dbConn import database


xmlMal = u"""<?xml version="1.0" encoding="utf-8"?>
<gluon priority="3" artID="df#progId" xmlns="http://gluon.nrk.no/gluon2" xmlns:gluonDict="http://gluon.nrk.no/gluonDict" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://gluon.nrk.no/gluon2 http://gluon.nrk.no/gluon2.xsd">
	<head>
		<metadata>
			<creators>
				<creator>
					<name>digasFake</name>
				</creator>
			</creators>
		</metadata>
	</head>
	<objects>
		<object objecttype="programme" dataid="#progId">
			<metadata>
				<titles>
					<title>#Progtittel</title>
				</titles>
				<subjects>
					<subject reference="Digas" link="http://gluon.nrk.no/dataordbok.xml#tags" label="what">Blod</subject>
					<subject reference="Digas" link="http://gluon.nrk.no/dataordbok.xml#tags" label="what">Svette</subject>
					<subject reference="Digas" link="http://gluon.nrk.no/dataordbok.xml#tags" label="what">Tårer</subject>
					<subject reference="Digas" link="http://gluon.nrk.no/dataordbok.xml#mentioned" label="who">Petter Smart</subject>
				</subjects>
				<description>
					<abstract restriction="public" link="http://gluon.nrk.no/dataordbok.xml#standfirst" reference="nrkDataordbok" label="standFirst" purpose="shortDescription">#ingress</abstract>
				</description>
				<contributors>
					<contributor id="n123456" link="t9bk7PHI5al4LS1UGwLSKQ;DWdppirHK92aBTgb8_WDwg;0eyMlTx9-XrXIiFqRq4noA;-0udJK_3ip4ba_zPeCX0HA;">
						<givenName>Jon</givenName>
						<familyName>Almaas</familyName>
						<name>Jon Almaas</name>
						<role link="http://gluon.nrk.no/nrkRoller.xml#V40">Programleder</role>
					</contributor>
					<contributor>
						<name>Jon Blund</name>
						<role link="http://gluon.nrk.no/nrkRoller.xml#N02">Bidragsyter</role>
					</contributor>
				</contributors>
				<types>
					<type reference="Digas" label="avviklingsform">Hel fil</type>
				</types>
				<format>
					<formatExtent>PT#sekunderS</formatExtent>
				</format>
				<identifier link="http://gluon.nrk.no/dataordbok.xml#upid" reference="PI.PROGRAM" label="uniqueIdentifier">#progId</identifier>
				<relations>
					<relationReferences label="illustration" reference="kaleido">t9bk7PHI5al4LS1UGwLSKQ;DWdppirHK92aBTgb8_WDwg;0eyMlTx9-XrXIiFqRq4noA;-0udJK_3ip4ba_zPeCX0HA;</relationReferences>
					<relationReferences label="illustrationCaption" reference="kaleido">Vakkert bilde av elg i solnedgang eller annen passende billedtekst</relationReferences>
				</relations>
				<coverage>
					<coverageSpatial>
						<location type="position" longitude="999.99999" latitude="999.99999">
							<name>Sorperoa</name>
						</location>
					</coverageSpatial>
				</coverage>
			</metadata>
		</object>
	</objects>
</gluon>
"""


iDrift = True
macTest = True
verbose = True



kanalSW = {'nrk p1':'p1','nrk p2':'p2','nrk p3':'p3','petre':'p3','nrk petre':'p3','p3':'p3','alltid klassisk':'ak','ak':'ak','nrk ak':'ak','nrk mpetre':'mpetre','nrk an':'an','an':'an'}
kanalAlow = ['p1','p2','p3','ak','an','mpetre','barn','gull','fmk']
fjernsyn = ['nrk 1','nrk 2','nrk 3']
		



crlf = chr(10) + chr(13)
crlf =  chr(10)

#def database(host="160.68.118.48", user="tormodv", database="dab",passord="allmc21"):
#def database(host="127.0.0.1", user="tormodv", database="dab",passord=""):
#	d = mdb.connect(user=user,passwd=passord, host=host)
#	d.select_db(database)
#	return d


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
	#GjØre om krav til liste over noder

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
	tittel =  finnVerdi( element,'metadata_DC/titles/title').replace('&','&amp;').replace('"','&quot;')
	ingress = finnVerdi( element,'metadata_DC/description/abstract').replace('&','&amp;').replace('"','&quot;')
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
		pass
	else:
		#Vi lagerXML
		#Sendeflater skal ikke registreres, de har ikke progid, men de inneholder ting som er og
		if progID and (tittel in ['Nitimen'] or True):
			
			utDok = xmlMal.replace('#ingress',ingress).replace('#Progtittel',tittel).replace('#progId',progID).replace('#sekunder',str(lengde)).encode('utf-8')
			if verbose:print utDok
			f=open('test.xml','w')
			f.write(utDok)
			f.close()
			response = sendData('http://vmaodastage01/sigmaservice/sigmagranittadapterservice.svc/sigmaanddigas', method = 'POST', data_raw = utDok)
			if verbose:print response
			"""
						kanal,
						mdb.TimestampFromTicks(ISOtilDato(sendedato)),
						tid,
						lengde,
						progID,
						fragment,
						tittel.encode('latin-1'),
						ingress.encode('latin-1'),
						"""
					
			if verbose:print  tid, lengde, progID, tittel.encode('utf-8'), subtitles, level, tabell
			
	#Saa finner vi om det er noen subelementer
	subelements = finnUnger(element.childNodes,'subelements')
	if subelements:
		elementer = finnUnger(subelements[0].childNodes,'element')
		elementer.reverse()#yngste sist, tidlig sending overskriver og fjerner reprise
		for element in elementer:
			sort = lagreSigma(element,level= level+1, annTid=annTid, c = c, sort = sort, tabell = tabell)
			#if subelement:
			#	sl.append(subelement)
		
	
	
	return sort
		
		
def sorterProgram(programliste, kanal, gyldighet, d, offset = 0):
	"Lager programlisten og f¬r denne inn i databasen"
	
	#FØrst fjerne i databasen
	c = d.cursor()
	sql = """DELETE FROM epg_light
				WHERE kanal=%s;"""
	c.execute(sql,(kanal,)) 
	sql = """DELETE FROM epg_light_gyldighet
				WHERE kanal=%s;"""
	c.execute(sql,(kanal,)) 
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
				#Programmet skal v re med
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
	
def sendData(uri, method="POST", data_raw = None, data_enc = None, svar_fra_mottager = 1,tag='karusell', reqursivLevel = 1, multipefaktor = 1):
	"""Sender gluoner til de forskjellige transmitterne.
	Denne brukes av tr¬dmodulen og blir kjØrt en gang pr. transmitter"""
	ret_svar = {}
	utverdier={}
	#Lager midlertidig svar som ev. oversktives senere
	#Lock og skriv
	
	ret_svar['status']='0'
	ret_svar['reason']='Starter utsendelse'
	
	
	utverdier[tag] = ret_svar
	#start = time.time()
	#Sett opp headers
	if data_raw:
		headers = {"Content-type": "application/xml",
			"Accept": "*/*",
			"User-Agent":"Gluon 0.5.0 [no] (%s; U)"%sys.platform}
		data = data_raw
	else:
		headers = {"Content-type": "application/x-www-form-urlencoded",
			"Accept": "*/*",
			"User-Agent":"Gluon 0.5.0 [no] (%s; U)"%sys.platform}
		data = data_enc
	#Dele opp uri til hostname og url
	host,url = uri[7:].split('/',1)
	start = time.time()
	try:
		conn = HTTPConnection(host)
		conn.request(method, '/' + url,data, headers)
		
		ret_svar['status']='3'
		ret_svar['reason'] = 'Sendt data - transmitter svarer ikke. Ting er sansynlighvis OK'
		#Dette skyldes som regel en treg mottaker og er ikke nØdvendighvis en feil
		time.sleep(0.003)
	except 0:
		#Legge inn forskjellige verdier her
		#Ev. legge inn rutine for automatisk forsØk igjen
		ret_svar['status']='1'
		ret_svar['reason'] = 'Kunne ikke lage forbindelse'
	else:
		if svar_fra_mottager:
			svar = conn.getresponse()
			#print dir(svar)
			ret_svar['status'] = svar.status
			ret_svar['reason'] = svar.reason
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
	"Finner ut om en gitt dato er intil dager/dØgn unna"
	dag = 60*60*24
	t = ISOtilDato(dato,sekunder=1)
	n = time.time()
	if kunSendedogn:
		#Vi runner av n(¬) til nermeste sendedØgnsstart
		naa= ISOdatetime(n)
		sendedato = naa[:11]+'06:00:00Z'
		n = ISOtilDato(sendedato,sekunder=1)
		#F¬relØpig m¬ vi gjØre det samme med dato
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
				#Sjekke om i er innenfor det sendedØgnet som er antall dager fram
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
			#Denne viten m¬ vi lage p¬ nytt
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
			
			
			
			#S¬ sjekker vi epg-dls biten, dersom vi ender med en endring her settes status til 1
			
			#Sjekke forst om epg-en er fra idag.
			gyldighetsdato = finnVerdi( resultat['element'][0],'metadata_DC/dates/date_issued')
			
			if verbose:print erDagerFram(gyldighetsdato,2,kunSendedogn=1)
			if erDagerFram(gyldighetsdato,1,kunSendedogn=1, interval=False):
				#lagre sigma data
				lagreSigma(resultat['element'][0])

			if erDagerFram(gyldighetsdato,0,kunSendedogn=1)==1:
				
				#lagre sigma data
				lagreSigma(resultat['element'][0])
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
	
	xmldokument = lesFil('item.xml')
	alfa= parser(xmldokument)
	print alfa
	
				
