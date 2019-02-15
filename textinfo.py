#! /usr/bin/python
# -*- coding: iso-8859-1 -*-


"""textinfo tjenester"""



# TODO
# Alt


# BUGS
#Oppdaterer ikke tabellen, skriver bare videre på den, det blir feil


import xml.dom.minidom
import MySQLdb as mdb
import re
import time
from random import choice
from dbConn import database

from roller import rolleliste, rollerelasjon, ikkeRolle
from felles import kanalAlow, kanalSW
verbose = 0

#kanalSW = {'p1':'p1','p2':'p2','nrk p3':'petre','petre':'petre','nrk petre':'petre','alltid klassisk':'ak','ak':'ak','mpetre':'mpetre','nrk an':'an','an':'an'}
#kanalAlow = ['p1','p2','petre','ak','an','mpetre']



#def database(host="160.68.118.48", user="tormodv", database="dab",passord="allmc21"):
#def database(host="localhost", user="tormodv", database="dab",passord=""):
#	d = mdb.connect(user=user,passwd=passord, host=host)
#	d.select_db(database)
#	return d
	


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
	
def ISOtilDato(dato,sekunder=0, sql=0):
	if not dato:
		return 0
	if type(dato)!=type(''):
		#Dette er en forelÃ¸pig patch for at en har begynt Ã¥ bruke datetime objekter
		dato = dato.isoformat()
	if 'T' in dato or sql:
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
	#path til nodeliste
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
		
def parser(xmlstreng):
	status = 0
	flushItems = 0
	
	#Lager en database forbindelse
	d=database()
	
	pars = xml.dom.minidom.parseString(xmlstreng)

	kropp = pars.getElementsByTagName('body')
	lagetDato = finnVerdi(pars,'gluon/head/creator/@date')
	tabeller = pars.getElementsByTagName('tables')
	for tabell in tabeller:
		if tabell.getAttribute('type')!='textinfo' or tabell.getAttribute('name')!='studioflash':
			continue
			#Det er textinfo og studioflash som er foreløpig den eneste tekstinformasjonen som støttes
		
		
		
		kanal = finnVerdi(tabell,'element/@channel')
		#Rette kanalnavn
		if kanal.lower() in kanalSW:
			kanal = kanalSW[kanal.lower()].lower()
		if pars.documentElement.getAttribute('priority') =='0':
			
			c2= d.cursor()
			sql = """DELETE FROM textinfo 
			WHERE kanal=%s ;"""
			c2.execute(sql,(kanal,)) 
			c2.close()

			#Tekstinfo breaking går det nesten ikke ann å stryke, sendt er sendt :-)
			
			
			
			#return "Settet er strøket"
			return {'status':2, 'kanal':kanal, 'datatype':'textinfo'}
		
			
		#if not kanal.lower() in kanalAlow:
		#	return {'status':0, 'kanal':kanal, 'datatype':'textinfo'}
 		#Vi sjekker ikke for kanal, alt er lov

		elementer = tabell.getElementsByTagName("element")
		sendingItem = 0
		sendingProgramme = 0
		rydd = [1,2,3,4]
		localids = [1,2,3,4]
		#Opdatere db
		localid=0
		for element in elementer:
			
			xmlElement=element.toxml().encode('latin-1')
			
			#Finne tekniske parametre
			
			elementtype =  finnVerdi( element,'@objecttype', entity = 0).encode('iso-8859-1')
			
			
			if elementtype=='programme' :
				sendingProgramme +=1
				localprogid = 0
				localid = sendingProgramme
			if elementtype=='item':
				localprogid = sendingProgramme
				sendingItem += 1
				localid = sendingItem + 2
			detaljering = finnVerdi( element,'@type', entity = 0).encode('iso-8859-1')
						
			#Tittel
			tittel = finnVerdi( element,'metadata_DC/titles/title', entity = 0).encode('iso-8859-1')
			#Justere titler o.l.
			
			komponist = ''
			#Kuttes ut
						
			#Beskrivelse
			beskrivelse = finnVerdi( element,'metadata_DC/description/abstract', entity = 0).encode('iso-8859-1')
			
			
			#Saa sendetidspunktet
			sendetidspunkt = finnVerdi( element,'metadata_DC/dates/date_issued',  entity = 0).encode('iso-8859-1')
			tid = mdb.TimestampFromTicks(ISOtilDato(sendetidspunkt,sekunder=1))
			
			
			#Finne tiden i sekunder
			lengde = int ( isoTilLengde(finnVerdi( element,'metadata_DC/format/format_extent',  entity = 0).upper()))
			if lengde < 11:
				#DVS det er mindre en 10 sekunder, vi skal bruke flash lista (breaking)
				datType = 'textinfo:breaking'
				tabelType = 'textinfo_breaking' #Dette fordi en gang og tidsstyrt skal gÃ¥ uavhengige av hverandre
			else:
				datType = 'textinfo'
				tabelType = 'textinfo' #Dette fordi en gang og tidsstyrt skal gÃ¥ uavhengige av hverandre
			#Finne tekstinholdet
			#Kunn kortteksten
			innhold = finnVerdi( element,'longDescription/abstract',  entity = 0).encode('iso-8859-1')
			
			#Sjekke om programmet skal oppdateres (summary sjekk)
			
			if verbose:print (kanal,elementtype)
			#Oppdatere databasen
			c= d.cursor()
			#Sjekke først om dataene er registrert
			sql = "SELECT id FROM %s WHERE kanal=%s and localid=%s;" % (tabelType,'%s','%s')
			
			c.execute(sql,(kanal,localid)) 
			if verbose:print c.rowcount
			if c.rowcount== 1:
				status = 1
				if tabelType == 'textinfo_breaking':
					sql = """UPDATE textinfo_breaking SET 
						tittel=%s,
						type=%s,
						localprogid=%s,
						tid=%s,
						lengde=%s,
						beskrivelse=%s,
						innhold=%s,
						element=%s
						WHERE kanal=%s and localid=%s;""" 
				else:
					sql = """UPDATE textinfo SET 
						tittel=%s,
						type=%s,
						localprogid=%s,
						tid=%s,
						lengde=%s,
						beskrivelse=%s,
						innhold=%s,
						element=%s
						WHERE kanal=%s and localid=%s;""" 
				
				c.execute(sql,( 
					tittel,
					elementtype,
					localprogid,
					tid,
					lengde,
					beskrivelse[:128],
					innhold,
					xmlElement,
					kanal,
					localid
					)
				) 
			else:
				#Det er ingen felter som er oppdatert
				
				status = 2
				if tabelType == 'textinfo_breaking':
					sql = """INSERT INTO textinfo_breaking(tittel,type,localprogid,tid,lengde,beskrivelse,innhold,element,kanal,localid) VALUES 
					(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
					""" 
				else:
					sql = """INSERT INTO textinfo(tittel,type,localprogid,tid,lengde,beskrivelse,innhold,element,kanal,localid) VALUES 
					(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
					""" 
				c.execute(sql,(
					tittel,
					elementtype,
					localprogid,
					tid,
					lengde,
					beskrivelse[:128],
					innhold,
					xmlElement,
					kanal,
					localid
					)
				) 
			c.close()
			
		#Rydde opp manglende elementer, dvs det er ferre en 4 elementer i settet.
		
		for localid in localids:
			
			#Er elementet utgÃ¥tt pÃ¥ tid?
			c1= d.cursor()
			sql = """SELECT tid, lengde FROM textinfo 
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
			nu = time.time()
			#print time.ctime(slutttid1), time.ctime(ISOtilDato(sendetidspunkt,sekunder=1)), nu>=slutttid1, lengde1
			
			if nu >= slutttid1 or (localid%2==0 and localid in rydd) or (flushItems and localid==3 and localid in rydd):
				#print "utg %s" % localid
				c2= d.cursor()
				sql = """DELETE FROM textinfo 
				WHERE kanal=%s and localid=%s;"""
				c2.execute(sql,(kanal,localid)) 
				c2.close()
						
			
		
			
	#Lukke database
	d.commit()
	d.close()
	
	return {'status':status, 'kanal':kanal, 'datatype':datType}

def opprensk(idpakke):
	"Opprydningsrutiner som kjøres etter alle utspillings rutiner"
	#Vi må stryke i databasen
	kanal = idpakke['kanal']
	datatype = idpakke['datatype']
	if datatype == 'textinfo:breaking':
		d=database()
		c=d.cursor()
		c.execute('DELETE FROM textinfo_breaking WHERE kanal=%s;',(kanal,))
		c.close()
		d.close()
	
