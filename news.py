#! /usr/bin/python
# -*- coding: iso-8859-1 -*-

"""News tjenester"""

import xml.dom.minidom
import MySQLdb as mdb
import time

#prioritet for newswire
#newswire som ikke er nevnt i tabellen blir ikke med
newsPriority = {'nwr481':[4,4,3,3,3,2,2,2,2,2,2],
				'nwr482':[4,4,3,3,3,2,2,2,2,2,2],
				'nwr68':[3,3,2,2,2,]
				}

def database(host="160.68.118.48", user="tormodv", database="dab",passord="allmc21"):
#def database(host="localhost", user="tormodv", database="dab",passord=""):
	d = mdb.connect(user=user,passwd=passord, host=host)
	d.select_db(database)
	return d
	
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
	
def slettTabell(artID,d):
	c = d.cursor()
	sql = """DELETE FROM nyheter WHERE fraArtID = %s;"""
	
	c.execute(sql,(artID,)) 
	c.close()
	
def skrivTilDB(nyhet,prioritet,lagetDato,artID,d):
	"Standard parser for nyhetstjenester"
	tittel =  finnVerdi(nyhet,'headline').encode('iso-8859-1')
	sammendrag = finnVerdi(nyhet,'lead').encode('iso-8859-1')
	if not sammendrag:
		prioritet -= 1
	itemLaget = finnVerdi(nyhet,'metadata_DC/dates/date_created')
	if itemLaget:
		lagetDato = itemLaget
	#Oversette til sql-dato
	lagetDato = mdb.TimestampFromTicks(ISOtilDato(lagetDato,sekunder=1))
	c = d.cursor()
	sql = """INSERT INTO nyheter(tittel,sammendrag,oppdatert,prioritering,fraArtID) VALUES 
				(%s,%s,%s,%s,%s)
				""" 
	c.execute(sql,(
			tittel[:150],
			sammendrag[:255],
			lagetDato,
			prioritet,
			artID
			)
		)
	c.close()

def parser(dok):
	#print "NEWS PARSER"
	#Status er 0 for ikke prossesert, 1 for oppdatert info,  2 for ny, 3 for "force breaking"?
	return {'status':0, 'kanal':'alle', 'datatype':'news'}
	
def newswire(dok):
	"Leser for newswiretypen - enkel type"
	status = 0
	
	#Lager en database forbindelse
	d=database()
	
	pars = xml.dom.minidom.parseString(dok)
	lagetDato = finnVerdi(pars,'/gluon/head/metadata_DC/dates/date_created')
	kropp = pars.getElementsByTagName('body')
	prioritet = finnVerdi(pars,'gluon/@priority')
	artID =  finnVerdi(pars,'gluon/@artID')
	if not artID in newsPriority:
		return {'status':0, 'kanal':'alle', 'datatype':'news'}
	
	#stop
	tabeller = pars.getElementsByTagName('tables')
	for tabell in tabeller:
		if tabell.getAttribute('type')!='newswire':
			continue
		
		nyheter = tabell.getElementsByTagName('news')
		#Vi trenger å slette tabellen
		if nyheter:
			slettTabell(artID,d)
		for nyhet in nyheter:
			try:
				prioritet = newsPriority[artID].pop(0)
			except IndexError:
				break
			skrivTilDB(nyhet,prioritet,lagetDato,artID,d)
			status = 1
		
		

	
	
	
	return {'status':status, 'kanal':'alle', 'datatype':'news'}
