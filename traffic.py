#! /usr/bin/python
# -*- coding: iso-8859-1 -*-

"""News tjenester"""

import xml.dom.minidom
import MySQLdb as mdb
import time
from dbConn import database

verbose = 1


#def database(host="160.68.118.48", user="tormodv", database="dab",passord="allmc21"):
#def database(host="localhost", user="tormodv", database="dab",passord=""):
#	d = mdb.connect(user=user,passwd=passord, host=host)
#	d.select_db(database)
#	return d
	

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
	
def finnVerdi(xmlobjekt,path,entity = False, nodetre = False):
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
	if nodetre:
		return xmlobjekt
	if not entity:
		return hentVerdier(xmlobjekt.childNodes)
	else:
		return entetyReplace(hentVerdier(xmlobjekt.childNodes))
		
	
def entetyReplace(s):
	s = s.replace('&','&amp;')
	
	return s
	
def slettTabell(d):
	c = d.cursor()
	sql = """DELETE FROM nyheter;"""
	
	c.execute(sql,) 
	c.close()
	
def finnSted(stedNode,type = 'county'):
	"Finner sted på grunnlag av stedsnode"
	#Finne første stedsnode type
	stedstype = finnVerdi(stedNode, '@type')
	
	if stedstype ==type:
		#Vi har et likhet og det er bare og returnere navnet
		return  finnVerdi(stedNode, 'name')
	else:
		#Vi finner ut om om vi har noen etterkommere
		divisjon =  finnVerdi(stedNode, 'division/location', nodetre = True)
		if divisjon:
			return finnSted(divisjon,type = type)
		else:
			return ''
	
def skrivTilDB(nyhet,prioritet,lagetDato,d):
	"Standard parser for nyhetstjenester"
	tittel =  finnVerdi(nyhet,'metadata_DC/titles/title').encode('iso-8859-1')
	sammendrag = finnVerdi(nyhet,'abstract').encode('iso-8859-1')
	itemLaget = finnVerdi(nyhet,'metadata_DC/dates/date_created')
	if itemLaget:
		lagetDato = itemLaget
		
	#print tittel, sammendrag, prioritet, lagetDato
	c = d.cursor()
	sql = """INSERT INTO nyheter(tittel,sammendrag,oppdatert,prioritering) VALUES 
				(%s,%s,%s,%s)
				""" 
	c.execute(sql,(
			tittel[:50],
			sammendrag[:128],
			lagetDato,
			prioritet
			)
		)
	c.close()

def parser(dok):
	if verbose:print "TRAFFIC PARSER"
	
	status = 0
	flushItems = 0
	
	pars = xml.dom.minidom.parseString(dok)
	meldingstype = finnVerdi(pars,'gluon/body/traffic/@type/')
	id = 'heimdall' + finnVerdi(pars,'gluon/@artID')
	viktighet = int(finnVerdi(pars,'gluon/@priority/'))
	if viktighet == 0:
		#Vi må stryke i databasen
		d=database()
		c=d.cursor()
		c.execute('DELETE FROM traffic WHERE id=%s;',(id,))
		c.close()
		d.close()
		#Vi returnerer med status 1 her for dette kan komme til nytte i BWS, i dls vil dette alerede være sendt.
		return {'status':1, 'kanal':'alle', 'datatype':'traffic'}
		
	#Ta vare paa meldingset
	if meldingstype.lower() !='trafikkforhold':
		f=open('/var/www/html/trafikk.xml','w')
		f.write(dok)
		f.close()
	if meldingstype.lower() !='trafikkforhold' or viktighet<4:
		return {'status':0, 'kanal':'alle', 'datatype':'traffic'}
	lagetDato = finnVerdi(pars,'gluon/head/metadata_DC/dates/date_created/')
	stedNode = finnVerdi(pars,'gluon/body/traffic/incidentDescription/metadata_DC/coverage/coverage_spatial/location/', nodetre = True)
	tittel = finnVerdi(pars,'gluon/body/traffic/incidentDescription/headline/')
	tekst = finnVerdi(pars,'gluon/body/traffic/incidentDescription/lead/')
	
	tpegNode = pars.getElementsByTagNameNS('http://gluon.nrk.no/tpeg','tpeg_document')[0] #Denne fikser ikke entetyene, dette må fikses
	
	tpegXml = tpegNode.toxml(encoding='latin-1')
	#Vi trenger å få ut oversikt over geografien
	fylke = finnSted(stedNode, type = 'county')
			
	#Lager en database forbindelse
	d=database()
	c=d.cursor()

	#Sjekke om kampideen finnes fra før
	sql = """SELECT id FROM traffic
		WHERE id=%s;"""
	c.execute(sql,(id,)) 
	
	if c.rowcount== 1:
		status = 1
		
		sql = """UPDATE traffic SET 
			id=%s,
			oppdatert=%s,
			viktighet=%s,
			kortmelding=%s,
			langmelding=%s,
			fylke=%s,
			tpeg=%s
			WHERE id=%s;""" 
		
		c.execute(sql,(
			id,
			mdb.TimestampFromTicks(time.time()),
			viktighet,
			tittel,
			tekst,
			fylke,
			tpegXml,
			id
			)
		) 
	else:
		#Det er ingen felter som er oppdatert
		
		status = 2
		sql = """INSERT INTO traffic(id,oppdatert,viktighet,kortmelding,langmelding,fylke,tpeg) VALUES 
		(%s,%s,%s,%s,%s,%s,%s)
		""" 
		c.execute(sql,(
			id,
			mdb.TimestampFromTicks(time.time()),
			viktighet,
			tittel,
			tekst,
			fylke,
			tpegXml
			)
		) 
	c.close()
	d.close()



	#Status er 0 for ikke prossesert, 1 for oppdatert info,  2 for ny, 3 for "force breaking"?
	return {'status':status, 'kanal':'alle', 'datatype':'traffic','id':id}
	
def opprensk(idpakke):
	#Vi må stryke i databasen
	return
	id = idpakke['id']
	d=database()
	c=d.cursor()
	c.execute('DELETE FROM traffic WHERE id=%s;',(id,))
	c.close()
	d.close()

