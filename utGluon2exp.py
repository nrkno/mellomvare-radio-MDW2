#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""Tjeneste som skriver data tilbake til gluon
"""
#! /usr/local/bin/python

# TODO
"""
*** Rette antall parameter returnert fra musikk (iteminfo) funksjonene


lage en python dict for programmet, en for nå og en for neste, nå og forrige

<element objecttype="item" dataid="M3TY_071560CS0001" runorder="present">


hentNewsItemForrige

***Lage funksjon som løser opp en dictionary url til vanlige data

"""


# BUGS

#from gluoncommons import finnVerdi, finnRelasjoner, finnRoller, finnFuzzyDate, finnBeskrivelse, ISOtilLengde
import MySQLdb as mdb
import re
import xml.dom.minidom
import time
from random import choice, sample
import math
import urllib
from httplib import HTTPConnection #importer heller sendrutinen til gluon, her trenger vi timeout
import sys
from dbConn import database
from hashlib import md5

import lagTestWebNett
from annonser import *

ikkeDls = ['nett'] #Legg inn bloknavn som ikke støtter dls teknologien, nettradioen f. eks.
webUrl = 'http://www2.nrk.no/tjenester/transformering/websrv/ReceiveXml.asmx/InternalXml'

gluonAdr = ['http://gluon/cgi-bin/karusell.py']
#gluonAdr = ['http://mamcdma01/cgi-bin/karusell.py']
billedmappe = ''
egenProd = 'EBU-NONRK' #Label for egenproduksjon
maxLevetid = 2
verbose = False
iDrift = 1
testum = 0

kanalAlow = ['p1','P2','NRK Petre','PETRE','NRK P3','Alltid Klassisk','mPetre','P3','p3']
kanalAlow = ['fmk','p3urort']
kanalAlow = ['p1','p2','p3','ak','an','mpetre','fmk','p3urort','p1of','ev1','ev2','nrk_5_1']
lagetGrense = 1980

#kanalAlow = ['mpetre']

#def database(host = "160.68.118.48", user="tormodv", database="dab",passord="allmc21"):
#def database(host = "127.0.0.1", user="tormodv", database="dab",passord=""):
#	"Lager en databaseconnection."
#	d = mdb.connect(user=user,passwd=passord, host=host)
#	d.select_db(database)
#	return d

crlf = chr(10) + chr(13)
crlf =  chr(10)

def minimumLevetid(d,kanal):
	"Finner den laveste gjenværende tid på en kanal"
	#Denne mÂ modifiseres for Â ta hensyn til alle dls'ene i kanalen
	#Kanskje heller ta vare pÂ alle stoptidene slik at vi kan legge de pÂ en stak som regenererer dls,ene?
	c = d.cursor()
	sql = """select
UNIX_TIMESTAMP(tid) + lengde - UNIX_TIMESTAMP()
 as tid_igjen
from iteminfo
where
 kanal=%s
order by tid_igjen
Limit 1
;"""
	c.execute(sql,(kanal))
	try:
		try:
			p = int(c.fetchone()[0])
		finally:
			c.close()
	except TypeError:
		return 0
	if kanal != 'ak':
		p += 600
	return p


def sjekkStatus(bilde):
	"Funksjon som skal sjekke om fila eksisterer"

	return True

def bildeFix(d, bilde, upid):
	"Henter bilderef fra kaleido"
	#upid = '124145CD0013'
	if bilde.startswith('http://'):#endre dette kriteriet
		#Alt vel
		return bilde
	#Da spør vi kaleido
	c = d.cursor()
	sql="""SELECT kaleidoRef FROM relKaleido WHERE musicId=%s and suborder=%s"""
	c.execute(sql,(
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

def sammenlignTittler(tittel1,tittel2):
	"Sammenligner om titler er nesten like, f. eks. to satser av et verk, returnerer True hvis vi synes det er likt"
	#Vi finner forskjellen, Vi forutsetter at Verktittel begynner likt, dersom dette er et problem
	try:
		for i in range(len(tittel1)):
			if tittel1[i]!=tittel2[i]:break

	except:
		pass
	#Vi tar ut forskjellene
	likheten = tittel1[:i].rstrip(':.;, ')
	forskjell = tittel1[i:]

	#Vi gj¯r en enkel test i f¯rste omgang, siden kan dette brukes til noe ala : ... sats 1. fulgt av sats 2.

	if len(likheten)>3 * len(forskjell) and 'sats' in forskjell:
		return True
	else:
		return False

def ISOtilDato(dato,sekunder=0, sql=0):
	if not dato:
		return 0
	if type(dato)!=type(''):
		#Dette er en forel√∏pig patch for at en har begynt √• bruke datetime objekter
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

def  distriktskanal(d, kanal):
	"Returnerer en liste av underkanaler pÂ grunnlag av et kanalnavn"
	#Finne f¯rst intern ideen pÂ kanalen
	c = d.cursor()
	sql = """SELECT DISTINCT id FROM kanal WHERE navn =%s LIMIT 1;"""
	c.execute(sql,(kanal))
	row = c.fetchone()
	c.close()
	if row:
		kanalId = row[0]
	else:
		kanalId = 99
		print "UKJENT KANAL", kanal

	#Finne sÂ hvilke distriktskanaler vi har

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
	#Dersom denne ender i en null, sÂ har denne kanalen ingen avleggere, ikke en gang seg selv.
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

def finnHovedkanal(d, kanal):
	"Returnerer navnet p√• hovedkanalen eller kanalnavn p√• grunnlag av kanalnavn"
	#Finne f√∏rst intern ideen p√• morkanalen
	c = d.cursor()
	sql = """SELECT DISTINCT foreldre_id FROM kanal WHERE navn =%s LIMIT 1;"""
	c.execute(sql,(kanal))
	row = c.fetchone()
	c.close()
	if row:
		hovedId = row[0]
	else:
		hovedId = 99
		print "UKJENT KANAL", kanal

	#Finne hva hovedkanalen heter

	c = d.cursor()
	sql = """SELECT navn FROM kanal WHERE id =%s LIMIT 1;"""
	s = []
	c.execute(sql,(hovedId))
	row = c.fetchone()
	c.close()
	if row:
		return row[0]
	else:

		print "FEIL I SQL"

def finnBlokker(d):
	"Returnerer alle blokkene fra dab-databasen"

	c = d.cursor()
	sql = """SELECT DISTINCT id, navn FROM blokk;"""
	s = {}
	c.execute(sql)
	while 1:
		p = c.fetchone()
		if p:
			s[int(p[0])] = p[1]
		else:
			break
	c.close()
	return s


def hentVisningsvalg(d,kanal, blokkId, datatype=None, oppdatering = 0):
	"Henter ut visningsvalg og verdier for filterfunksjonen"
	#F¯rst finner vi kanal_ID pÂ kanalen.
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

	#SÂ sjekke om denne datatypen skal vÊre breaking for den gitte kanalen
	#Dette kan vÊre bestemt av datatypen ogsÂ
	if ':' in datatype:
		return datatype.split(':',1) # Gir en [datatype,'breaking'] type

	c= d.cursor()
	sql="""SELECT breaking from datatyper
INNER JOIN dataikanal ON dataikanal.datatype_id=datatyper.id
WHERE kanal_id=%s AND blokk_id=%s AND tittel=%s LIMIT 1;"""
	c.execute(sql,(kanalId,blokkId,datatype))
	row = c.fetchone()
	c.close()
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

def hentPgrinfo(d,kanal,hovedkanal):
	"Henter kanalnavn og kanalbeskrivelse. Returnerer en liste de kanalnavn er 1. element og beskrivelsen 2."
	c= d.cursor()
	sql = """SELECT tittel, beskrivelse FROM iteminfo WHERE kanal=%s AND type='pgr' LIMIT 1;"""

	c.execute(sql,(kanal,))
	try:
		try:
			tittel, beskrivelse = c.fetchone()
		finally:
			c.close()
	except TypeError:

		return []
	return [tittel, beskrivelse]

def hentNyheter(d,kanal, max=None):
	"Henter nyheter fra databasen, ev begrenset til max stykker"
	c= d.cursor()
	if not max:
		sql = """SELECT tittel, sammendrag FROM nyheter ORDER BY id;"""
		c.execute(sql)
	else:
		sql = """SELECT tittel, sammendrag FROM nyheter ORDER BY id LIMIT %s;"""
		c.execute(sql,(max,))


	while 1:
		row = c.fetchone()
		if not row:
			c.close()
			break

		item = "%s. %s" % row
		if len(item)>128:
			item = row[1]
		if len(item)>128:
			item = item[:120] + '...'
		yield [item]


	c.close()


def hentProgrammeinfo(d,kanal,hovedkanal,distriktssending=False, harDistrikter = False, forceDistrikt = True):
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
		if verbose:print "I PROGRAMMET"
	else:
		iProgramme = False
		if verbose:print "IKKE I PROGRAMMET"

	if iProgramme and harDistrikter:
		#Vi har med Â gj¯re en distriktskanal som har eget program, da skal hele dls-en ignoreres. Den skal genereres ut ifra kanalens egen oppkall
		c.close()
		if verbose:print 'VOID - har eget program'
		return '','','','','','','','', False, True
		# Sjekke pÂ denne verdien om kanalen skal hoppes over i

	#Vi mÂ sjekke om hovedkanalen har en distriktsflate

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
		tittelSufix = ''


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
			tittelSufix = ' fra ' + branding
		else:
			tittelSufix = ''

		kanal = hovedkanal #Dette gj¯r at vi aldri henter programdata fra distriktsflaten

	else:
		#Hovedkanalen er ikke registrert med en distriktsflate, sjekke om vi skal la underkanalen ta styringen
		#Vi skal ikke har regionvise resultater
		if forceDistrikt and iProgramme:
			#Vi bytter ikke kanaler, men stryker sufix
			tittelSufix = ''
		else:
			kanal = hovedkanal
			tittelSufix = ''

	c= d.cursor()
	sql = """SELECT tittel, progId, beskrivelse, artist, tid, lengde, digastype, nettype FROM iteminfo WHERE kanal=%s AND type='programme' AND localid = '1' LIMIT 1;"""

	c.execute(sql,(kanal,))
	try:
		try:
			tittel, progId, beskrivelse, artist, sendetid, lengde, digastype, nettype = c.fetchone()
		finally:
			c.close()
	except TypeError:
		#Dersom vi ikke har noe her, kan det hende det er en distriktskanal som ikke har egne metadata
		if hovedkanal and not distriktssending:
			return hentProgrammeinfo(d,hovedkanal,None)
		else:
			return '','','','','','','', '', False, False

	if type(sendetid)!=type(''):
		#Dette er en forel√∏pig patch for at en har begynt √• bruke datetime objekter
		sendetid = sendetid.isoformat()

	if sendetid:
		sendetid = sendetid.replace(' ','T')

	tittel = tittel + tittelSufix #Legger pÂ f. eks. "fra NRK Tr¯ndelag" pÂ dirstriksflater

	return progId, tittel, beskrivelse, artist, sendetid, int(lengde), digastype, nettype, distriktssending, False


def hentProgrammeNext(d,kanal,hovedkanal,distriktssending=0):
	"Henter informasjon om det neste programmet som skal pÂ lufta, returnerer en liste med et element."
	c= d.cursor()
	sql = """SELECT tittel, progId, beskrivelse, artist, tid, lengde, digastype FROM iteminfo WHERE kanal=%s AND type='programme' AND localid = '2' LIMIT 1;"""

	c.execute(sql,(kanal,))
	try:
		try:

			tittel, progId, beskrivelse, artist, tid, lengde, digastype = c.fetchone()
		finally:
			c.close()
	except TypeError:
		if hovedkanal and not distriktssending:
			return hentProgrammeNext(d,hovedkanal,None)
		else:
			return '','','','','','',''
	if type(tid)!=type(''):
		#Dette er en forel√∏pig patch for at en har begynt √• bruke datetime objekter
		tid = tid.isoformat()
	if tid:
                tid = tid.replace(' ','T')
	return progId, tittel, beskrivelse, artist, tid, int(lengde), digastype

def hentEpg(d,kanal,hovedkanal,distriktssending=0):
	"Henter informasjon om programmene utover dagen og kvelden, returnerer en liste med et element."

	#F¯rst finne klokka
	timen = time.localtime()[3]
	#Sikring for gamle data
	c= d.cursor()
	sql = """select TO_DAYS(NOW()) - TO_DAYS(date)  from epg_light_gyldighet WHERE kanal = %s LIMIT 1;"""

	c.execute(sql,(kanal,))

	try:
		try:
			dagerGammel = c.fetchone()[0]
		finally:
			c.close()

	except TypeError:

		if hovedkanal and not distriktssending:
			#Vi har en ukjent kanal, uten epg, vi pr¯ver Â gÂ opp et hakk
			return hentEpg(d,hovedkanal,None)
		else:
			return []

	if not (dagerGammel ==0 or (dagerGammel==1 and timen<6)):
		if verbose:print "EPG er GAMMEL"
		return []



	#Her er det vel ingen hensikt Â dele pÂ distrikter, der alle distriktene nÂ er like, med henhold til sendetidspunkter, eller?

	c= d.cursor()
	sql = """SELECT id, info FROM epg_light WHERE kanal=%s AND time=%s LIMIT 1;"""

	c.execute(sql,(kanal,timen))
	try:
		try:

			id, info = c.fetchone()
		finally:
			c.close()
	except TypeError:
		if hovedkanal and not distriktssending:
			return hentEpg(d,hovedkanal,None)
		else:
			return []


	item = "%s" % info #Legge inn PÂ P1 i kveld...

	return [item]

def hentTextinfo(d,kanal,hovedkanal,distriktssending=0):
	"Henter informasjon og flashmeldinger om sendingen, st¯tter forel¯pig kunn programnivÂet"

	c= d.cursor()
	sql = """SELECT tid, lengde, innhold FROM textinfo WHERE kanal=%s AND type='programme'  AND localid = '1' LIMIT 1;"""

	c.execute(sql,(kanal,))
	try:
		try:
			tid, lengde, innhold = c.fetchone()
		finally:
			c.close()
	except TypeError:
		if hovedkanal and not distriktssending:
			return hentTextinfo(d,hovedkanal,None)
		else:
			return ''



	#Rutine som sjekker om elementet er utl¯pt.

	oppdatere = 0 #?
	c1= d.cursor()
	sql = """SELECT tid, lengde FROM textinfo
	WHERE kanal=%s and localid='1';"""

	c1.execute(sql,(kanal,))
	try:
		tid1, lengde1 = c1.fetchone()
	except TypeError:
		#Raden eksisterer ikke

		c1.close()
		#Skal ikke ut
		return ''
	else:
		c1.close()

		slutttid1 = ISOtilDato(tid1,sekunder=1,sql=1) + lengde

		if time.time()>=slutttid1:


			return ''



	return innhold

def hentIteminfoForrige(d,kanal,hovedkanal,distriktssending=0, item = False, info = False):
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
			dataid, tittel, kortTittel, artist, komponist, album, digastype, bilde, tid, lengde = c.fetchone()
		finally:
			c.close()
	except TypeError:
		if hovedkanal and not distriktssending:
			return hentIteminfoForrige(d,hovedkanal,None, item = item, info = info)
		else:
			return '','','','','','','','','',''
	if digastype == '':digastype = 'Music' #Lex BMS
	if digastype !='Music':
		return '','','','','','','','','',''


	if type(tid)!=type(''):
		#Dette er en forel√∏pig patch for at en har begynt √• bruke datetime objekter
		tid = tid.isoformat()
	if tid:
                tid = tid.replace(' ','T')
	#Artist feltet mÂ endres litt
	if artist:
		artist = artist.replace('|',' ')
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
		if laget<lagetGrense:
			tittel = "%s, innspilt %s," % (tittel,laget)

	if info and beskrivelse:
		album = beskrivelse
	else:
		album = ''



	return dataid, tittel, kortTittel, artist, komponist, album, bilde, tid, int(lengde), digastype


def hentIteminfo(d,kanal,hovedkanal,distriktssending=0, item = False, info = False):
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

	sql = """SELECT progId, tittel, ExtractValue(element, 'element/metadata_DC/titles/title'), artist,  ExtractValue(element, 'element/metadata_DC/creators/creator[role="Composer"]/family_name'), beskrivelse, digastype, bildeID, tid, lengde FROM iteminfo WHERE kanal=%s AND type='item'  AND localid = '3' LIMIT 1 ;"""

	c.execute(sql,(kanal,))
	try:
		try:
			dataid, tittel, kortTittel, artist, komponist, album, digastype, bilde, tid, lengde = c.fetchone()
		finally:
			c.close()
	except TypeError:
		if hovedkanal and not distriktssending:
			return hentIteminfo(d,hovedkanal,None, item = item, info = info)
		else:
			return '','','','','','','','','',''
	if digastype == '':digastype = 'Music' #Lex BMS
	if digastype !='Music':
		return '','','','','','','','','',''


	if type(tid)!=type(''):
		#Dette er en foreløig patch for at en har begynt å bruke datetime objekter
		tid = tid.isoformat()
	if tid:
                tid = tid.replace(' ','T')
	#Artist feltet må endres litt
	if artist:
		artist = artist.replace('|',' ')
		artist = artist.lstrip('. ')
		artist = artist[0].upper() + artist[1:]

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
		if laget<lagetGrense:
			tittel = "%s, innspilt %s," % (tittel,laget)

	if info and beskrivelse:
		album = beskrivelse
	else:
		album = ''



	return dataid, tittel, kortTittel, artist, komponist, album, bilde, tid, int(lengde), digastype

def hentNewsItemForrige(d,kanal,hovedkanal,distriktssending=0, news = False, info = False):
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

	sql = """SELECT progId, tittel, artist, beskrivelse, digastype, bildeID, tid, lengde FROM iteminfo WHERE kanal=%s AND type='item'  AND localid = '5' LIMIT 1 ;"""

	c.execute(sql,(kanal,))
	try:
		try:
			dataid, tittel, artist, beskrivelse, digastype, bilde, tid, lengde = c.fetchone()
		finally:
			c.close()
	except TypeError:
		if hovedkanal and not distriktssending:
			return hentNewsItem(d,hovedkanal,None, news = news, info = info)
		else:
			return '','','','','','','',''

	if digastype == '':digastype = 'Music' #Lex BMS
	if digastype !='News':
		return '','','','','','','',''


	album = '' #Denne informasjonen finnes ikke forel¯pig
	if bilde !='':
		if not sjekkStatus(bilde):
			bilde =''
		else:
			bilde = billedmappe + bilde

	if type(tid)!=type(''):
		#Dette er en forel√∏pig patch for at en har begynt √• bruke datetime objekter
		tid = tid.isoformat()
	if tid:
                tid = tid.replace(' ','T')

	#Artist feltet må endres litt
	if artist:
		artist = artist.replace('|',' ')
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
		if laget<lagetGrense:
			tittel = "%s, innspilt %s," % (tittel,laget)
	#Hack for IBSEN
	if beskrivelse:
		album = beskrivelse
		#S√• et nytt hack
	if kanal in ['nrk_5_1','gull','barn']:
		#Vi skal ikke ha med artist
		artist = ''
	if not news:
		tittel = ''
		artist = ''
	if not info:
		album = ''

	return dataid, tittel, artist, beskrivelse, bilde, tid, int(lengde), digastype




def hentNewsItem(d,kanal,hovedkanal,distriktssending=0, news = False, info = False):
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
			return hentNewsItem(d,hovedkanal,None, news = news, info = info)
		else:
			return '','','','','','','',''

	if digastype == '':digastype = 'Music' #Lex BMS
	if digastype !='News':
		return '','','','','','','',''


	album = '' #Denne informasjonen finnes ikke forel¯pig
	if bilde !='':
		if not sjekkStatus(bilde):
			bilde =''
		else:
			bilde = billedmappe + bilde

	#Artist feltet mÂ endres litt
	if artist:
		artist = artist.replace('|',' ')
		artist = artist.lstrip('. ')
		artist = artist[0].upper() + artist[1:]

	if type(tid)!=type(''):
		#Dette er en forel√∏pig patch for at en har begynt √• bruke datetime objekter
		tid = tid.isoformat()
	if tid:
                tid = tid.replace(' ','T')
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
		if laget<lagetGrense:
			tittel = "%s, innspilt %s," % (tittel,laget)
	#Hack for IBSEN
	if beskrivelse:
		album = beskrivelse
		#S√• et nytt hack
	if kanal in ['nrk_5_1','gull','barn']:
		#Vi skal ikke ha med artist
		artist = ''
	if not news:
		tittel = ''
		artist = ''
	if not info:
		album = ''

	return dataid, tittel, artist, beskrivelse, bilde, tid, int(lengde), digastype


def hentItemNext(d,kanal,hovedkanal,distriktssending=0, musikk=False, news = False):
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

	#Dersom titlene er like med untak av satsbetegnelsene viser vi ingenting
	else:
		if sammenlignTittler(tittel1,tittel2):
			return '','','','','','','',''

	#Ellers viser vi nesteinformasjon
	sql = """SELECT progId, tittel, ExtractValue(element, 'element/metadata_DC/titles/title'), artist,  ExtractValue(element, 'element/metadata_DC/creators/creator[role="Composer"]/family_name'), beskrivelse, digastype, bildeID, tid, lengde FROM iteminfo WHERE kanal=%s AND type='item' AND localid = '4' LIMIT 1;"""


	c.execute(sql,(kanal,))
	try:
		try:
			dataid, tittel, kortTittel,artist, komponist, beskrivelse, digastype, bilde, tid, lengde = c.fetchone()
		finally:
			c.close()
	except TypeError:
		if hovedkanal and not distriktssending:
			return hentItemNext(d,hovedkanal,None, musikk=musikk, news=news)
		else:
			return '','','','','','','','','',''
	if digastype == '':
		digastype = 'Music' #Lex BMS

	#print 'Music?' , musikk, 'News?' , news, digastype, digastype == 'Music' and not musikk
	if digastype == 'Music' and not musikk:
		#Vi skal ikke vise
		return '','','','','','','','','',''
	if digastype == 'News' and not news:
		#Vi skal ikke vise
                return '','','','','','','','','',''

	if type(tid)!=type(''):
		#Dette er en foreløpig patch for at en har begynt å bruke datetime objekter
		tid = tid.isoformat()
	if tid:
                tid = tid.replace(' ','T')
	album = ''

	#Artist feltet mÂ endres litt
	if artist:
		artist = artist.replace('|',' ')
		artist = artist.lstrip('. ')
		artist = artist[0].upper() + artist[1:]

	#Aldri infofelt paa neste, og ikke artis paa news
	if musikk:
		#kutte beskrivelse
		beskrivelse = ''

	return dataid, tittel, kortTittel,artist, komponist, beskrivelse, bilde, tid, int(lengde), digastype


def storForbokstav(item):
	return item[0].upper() + item[1:]

def sendDataWeb(data,uri, svar_fra_mottager = True):
	#For at den ikke skal sende noe noe

	headers = {"Content-type": "application/xml",
		"Accept": "*/*",
		"User-Agent":"MDW 1.0 [no] (%s; U)"%sys.platform}
	#Splitte protokoll og uri
	protokol, uri = uri.split(':',1)
	uri=uri.lstrip('/')
	#Dele opp uri til hostname og url
	host,url = uri.split('/',1)

	try:
		conn = HTTPConnection(host)
		conn.request("POST", '/' + url,data, headers)
	except 0:
		#Legge inn forskjellige verdier her
		print 'Kunne ikke lage forbindelse'
	else:
		if svar_fra_mottager:
			svar = conn.getresponse().read()

		else:
			svar ='Sendt'
		conn.close()
	return svar

def sendDataGet(url, navn, kanal):
	tilogData = url + '?' + urllib.urlencode({'name':navn,'channel':kanal})
	msg = "Ikke svar"

	u=urllib.urlopen(tilogData)
	try:

		msg =u.read(2048)


	finally:
		u.close()
	return msg

def returnTimezone():
	if time.localtime()[8]:
		return '+02:00'
	else:
		return '+01:00'


def lagGluon(artID="test"):
	"Lager et gluon rotdokument, og returnerer dette og en pointer til stedet hvor elementene skal inn"
	impl = xml.dom.minidom.getDOMImplementation()
	utdok = impl.createDocument('http://www.w3.org/2001/XMLSchema','gluon', None)
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
	tables = utdok.documentElement.appendChild(utdok.createElement('objects'))#.appendChild(utdok.createElement('objects'))
	#tables.setAttribute('type', 'iteminfo')
	#print utdok.toprettyxml('  ','\n','utf-8')
	#print utdok.toxml('utf-8')

	return utdok, tables

def getRole(roleId):

	return ''


def setteDataid(tittel):
	m = md5(tittel)
	return 'MDW:%s' % m.hexdigest()


def addName(utdok, tag, roleId='', name='', ):
	famname = tag.appendChild(utdok.createElement('name'))
	famname.appendChild(utdok.createTextNode(unicode(name,'iso-8859-1')))
	#famname.setAttribute('person', 'true') #Bruke bare visningsnavnet for dette, kunne vel egentlig brukt abstract
	roleTag = tag.appendChild(utdok.createElement('role'))
	if roleId:
		roleTag.setAttribute('link', 'http://gluon.nrk.no/nrkRoller.xml#' + roleId)
	#roleTag.appendChild(utdok.createTextNode(getRole(roleId)))

def addObject(utdok, pointer,
				subElements = False,
				objecttype='',
				subjects='',
				dataid='',
				channel='',
				runorder='',
				tittel = '',
				kortTittel = '',
				creator = '',
				abstract = '',
				partisipantDescription = '',
				contributor = '',
				gluonType = '',
				issued = '',
				duration = '',
				bilde = ''
				):
	"Legger pÂ et element til et objekttre, returnerer en peker til subelement-elementet"
	#Ordne elementet
	if not dataid:
		dataid = "noID"
	#print channel
	channel = channel.replace('ko ', 'ko_')#lex toten
	#print 77, channel
	element = pointer.appendChild(utdok.createElement('object'))
	element.setAttribute('objecttype', objecttype)
	element.setAttribute('dataid', unicode(dataid,'iso-8859-1'))
	element.setAttribute('channel', channel)
	if runorder: element.setAttribute('runorder', runorder)
	#Har to underelementer, metadata og subelements
	metadata = element.appendChild(utdok.createElement('metadata'))



	#Legge til de ulike elementene
	if tittel:
		titler = metadata.appendChild(utdok.createElement('titles'))
		titler.appendChild(utdok.createElement('title')).appendChild(utdok.createTextNode(unicode(tittel,'iso-8859-1')))
		if kortTittel:
			titAlt = titler.appendChild(utdok.createElement('titleAlternative'))
			titAlt.appendChild(utdok.createTextNode(unicode(kortTittel,'iso-8859-1')))
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
					addName(utdok, creatorTag, roleId = role, name = navn)
		else:
			metadata.appendChild(creator)
	#Subjects

	if subjects:
		subjectelement = metadata.appendChild(utdok.createElement('subjects'))
		for subject in subjects:
			st = subjectelement.appendChild(utdok.createElement('subject'))
			if 'value' in subject:
				st.appendChild(utdok.createTextNode(unicode(subject['value'],'iso-8859-1')))
			if 'label' in subject:
				st.setAttribute('label', subject['label'])
			if 'reference' in subject:
				st.setAttribute('reference', subject['reference'])



	if abstract or partisipantDescription:
		desc = metadata.appendChild(utdok.createElement('description'))
		if abstract:
			absSF = desc.appendChild(utdok.createElement('abstract'))
			absSF.setAttribute('restriction','public')
			absSF.setAttribute('link','http://gluon.nrk.no/dataordbok.xml#standFirst')
			absSF.setAttribute('purpose','shortDescription')
			absSF.appendChild(utdok.createTextNode(unicode(abstract,'iso-8859-1')))
		if partisipantDescription:
			absSF = desc.appendChild(utdok.createElement('abstract'))
			absSF.setAttribute('restriction','public')
			absSF.setAttribute('link','http://gluon.nrk.no/dataordbok.xml#presentation')
			absSF.setAttribute('purpose','presentation2')
			absSF.appendChild(utdok.createTextNode(unicode(partisipantDescription,'iso-8859-1')))


	if contributor:
		if type(contributor) == type({}):
			contributors = metadata.appendChild(utdok.createElement('contributors'))
			for roleId in contributor:
				navnene = contributor[roleId]
				if type(navnene) != type([]):
					navnene = [navnene]
				for navn in navnene:
					contributorTag = contributors.appendChild(utdok.createElement('contributor'))
					addName(utdok, contributorTag, roleId = roleId, name = navn)
		else:
			metadata.appendChild(contributor)

	if gluonType:
		gluonTypes = metadata.appendChild(utdok.createElement('types'))
		for gts in gluonType:
			gt = gluonTypes.appendChild(utdok.createElement('type'))
			if 'value' in gts:
				gt.appendChild(utdok.createTextNode(unicode(gts['value'],'iso-8859-1')))
			if 'label' in gts:
				gt.setAttribute('label', gts['label'])
			if 'reference' in gts:
				gt.setAttribute('reference', gts['reference'])

	if issued:
		metadata.appendChild(utdok.createElement('dates')).appendChild(utdok.createElement('dateIssued')).appendChild(utdok.createTextNode(unicode(issued,'iso-8859-1')))

	if duration:
		metadata.appendChild(utdok.createElement('format')).appendChild(utdok.createElement('formatExtent')).appendChild(utdok.createTextNode(unicode("PT%sS" % duration,'iso-8859-1')))

	if bilde:
		relations = metadata.appendChild(utdok.createElement('relations'))
		oldRef = relations.appendChild(utdok.createElement('relationReferences'))
		oldRef.setAttribute('label','illustration')
		oldRef.setAttribute('reference','DMA')
		oldRef.appendChild(utdok.createTextNode(unicode(bilde,'iso-8859-1')))
		bildeRel = relations.appendChild(utdok.createElement('relationIsDescribedBy'))
		bildeRel.setAttribute('reference','DMA')
		bildeRel.appendChild(utdok.createTextNode(unicode(bilde,'iso-8859-1')))

	if subElements:
		return element.appendChild(utdok.createElement('subelements'))
	else:
		return None

def lagMetadata(kanal='alle',datatype=None,id='' , testModus=False):
	"Henter data for en gitt kanal ut i fra de forskjellige databasene og setter sammen til en DLS som sendes videre som et mimemultipartdokument."
	utdata = {}
	#kanal='alle'
	#return 0
	#Fange opp at jeg skal kunne generere nytt pÂ alle kanaler.
	d = database()
	if kanal == 'alle':
		kanaler = finnKanaler(d,ikkeDistrikt = 0)
	else:
		kanaler = [kanal]
		#Det kan hende at kanalene er delt opp i distrikter - eks. p1oslo

	#Finne blokker
	blokker = finnBlokker(d)

	for kanal in kanaler:
		#For inf¯ringsfasen kan vi filtrere hvilke kanaler som skal fra denne applikasjonen

		#Det kan hende at kanalene er delt opp i distrikter - eks. p1oslo
		#utvid kanaler
		distriktskanaler = distriktskanal(d, kanal)
		if len(distriktskanaler) == 1:
			#Vi har kunn en kanal, distrikskanal eller kanalen selv, vi m√• finne moderkanalen
			hovedkanal = finnHovedkanal(d, kanal)
			harDistrikter = False
		else:
			#Vi har en kanal med barn, ergo er hovedkanalen kanalen selv.
			hovedkanal = kanal
			harDistrikter = True

		for kanal in distriktskanaler:
			for blokkId in blokker:
				#print blokkId
				if blokker[blokkId] not in ikkeDls:
					if verbose:print "Ikke vis som DLS på %s" % blokker[blokkId]
					continue
					#dvs denne bruker instillingene for NETT

				if verbose:print "Viser på %s" % blokker[blokkId]

				#Lage nytt dokument
				xmldom, tablePointer = lagGluon(artID="iteminfo_NRK_%s" % kanal)


				#Bygge opp visningslista
				#Hente visningsvalg
				visningsvalg = hentVisningsvalg(d, kanal, blokkId, datatype=datatype)
				oppdateres = hentVisningsvalg(d, kanal, blokkId, datatype=datatype, oppdatering = 1)

				if verbose:print "Visningsvalg:", visningsvalg
				if verbose:print "Opdateringskriterie;", oppdateres

				#Sjekke om det er nødvendig Â oppdatere
				if not datatype in oppdateres:
					if verbose:print "SKAL IKKE VISES", kanal,blokkId
					continue

				s=[]

				#SÂ til tjenestegruppene

				#Hente programinfo, alltid

				progId, tittel, info, programleder, issued, duration, digastype, nettype, distriktssending, egenKanal = hentProgrammeinfo(d,kanal,hovedkanal, harDistrikter = harDistrikter)
				if egenKanal:
					if verbose:print "Har egen sending"
					continue

				if programleder:
					programleder = {'V40':programleder}


				if nettype:
					subjects = [{'reference':'Nettkategori', 'value' : nettype}]
				else:
					subjects = ''

				#Legge inn som objekt
				#print tablePointer
				innslag = addObject(xmldom, tablePointer,
					subElements = True,
					objecttype="programme",
					channel = kanal,
					dataid = progId,
					tittel = tittel,
					abstract = info,
					contributor = programleder,
					duration = duration,
					issued = issued,
					gluonType = [{'reference':'NRK-Escort', 'value' : digastype}],
					subjects = subjects
					)

				if 'iteminfo' in visningsvalg or 'musicInfo' in visningsvalg:
					#Da skal vi ogsÂ ha med forige

					dataid, tittel, kortTittel, artist, komponist, info, bilde, issued, duration, gluonType = hentIteminfoForrige(d,kanal,hovedkanal, item = 'iteminfo' in visningsvalg, info = 'musicInfo' in visningsvalg, distriktssending = distriktssending)
					if not dataid:
						dataid = setteDataid(tittel)
					if not komponist:
						creator = ''
					else:
						creator = {'V34':komponist}
					bilde = bildeFix(d, bilde, dataid)
					#if artist:
					#	artist = {'Utøver':artist}
					if tittel:
						#Dersom vi ikke har en tittel skal vi ikke ha noe objekt heller
						addObject(xmldom, innslag,
						runorder = "past",
						subElements = False,
						objecttype="item",
						channel = kanal,
						dataid = dataid,
						tittel = tittel,
						kortTittel= kortTittel,
						abstract = info,
						creator = creator,
						partisipantDescription = artist,
						duration = duration,
						issued = issued,
						gluonType = [{'label':'class', 'reference':'Digas', 'value' : gluonType}],
						bilde = bilde
						)

					#Musikkobjekter
					#print hentIteminfo(d,kanal,hovedkanal, item = 'iteminfo' in visningsvalg, info = 'musicInfo' in visningsvalg)
					dataid, tittel, kortTittel, artist, komponist, info, bilde, issued, duration, gluonType = hentIteminfo(d,kanal,hovedkanal, item = 'iteminfo' in visningsvalg, info = 'musicInfo' in visningsvalg, distriktssending = distriktssending)
					if not dataid:
						dataid = setteDataid(tittel)
					if not komponist:
						creator = ''
					else:
						creator = {'V34':komponist}
					#if artist:
					#	artist = {'Utøver':artist}
					if tittel:
						#Dersom vi ikke har en tittel skal vi ikke ha noe objekt heller
						bilde = bildeFix(d, bilde, dataid)
						addObject(xmldom, innslag,
						runorder = "present",
						subElements = False,
						channel = kanal,
						objecttype="item",
						dataid = dataid,
						tittel = tittel,
						kortTittel= kortTittel,
						abstract = info,
						creator = creator,
						partisipantDescription = artist,
						duration = duration,
						issued = issued,
						gluonType = [{'label':'class', 'reference':'Digas', 'value' : gluonType}],
						bilde = bilde
						)
						#SEtte inn innslags objekt her
				if 'newsItem' in visningsvalg or 'newsInfo' in visningsvalg or True:
					#Andre innslag
					#Da skal vi ogsÂ ha med forige
					#print visningsvalg
					dataid, tittel, artist, info, bilde, issued, duration, gluonType = hentNewsItemForrige(d,kanal,hovedkanal, news = 'newsItem' in visningsvalg, info = 'newsInfo' in visningsvalg, distriktssending = distriktssending)
					if not dataid:
						dataid = setteDataid(tittel)
					#Sette inn innslags objekt her
					if tittel:
						#Dersom vi ikke har en tittel skal vi ikke ha noe objekt heller
						bilde = bildeFix(d, bilde, dataid)
						addObject(xmldom, innslag,
						runorder = "past",
						channel = kanal,
						subElements = False,
						objecttype="item",
						dataid = dataid,
						tittel = tittel,
						abstract = info,
						contributor = {'V36':artist},
						duration = duration,
						issued = issued,
						gluonType = [{'label':'class', 'reference':'Digas', 'value' : gluonType}],
						bilde = bilde
						)



					dataid, tittel, artist, info, bilde, issued, duration, gluonType = hentNewsItem(d,kanal,hovedkanal, news = 'newsItem' in visningsvalg, info = 'newsInfo' in visningsvalg)
					if not dataid:
						dataid = setteDataid(tittel)
					#Sette inn innslags objekt her
					if tittel:
						#Dersom vi ikke har en tittel skal vi ikke ha noe objekt heller
						bilde = bildeFix(d, bilde, dataid)
						addObject(xmldom, innslag,
						runorder = "present",
						channel = kanal,
						subElements = False,
						objecttype="item",
						dataid = dataid,
						tittel = tittel,
						abstract = info,
						contributor = {'V36':artist},
						duration = duration,
						issued = issued,
						gluonType = [{'label':'class', 'reference':'Digas', 'value' : gluonType}],
						bilde = bilde
						)



				if ('itemNext' in visningsvalg):
					#**** Rette denne
					dataid, tittel, kortTittel, artist, komponist, info, bilde, issued, duration, gluonType = hentItemNext(d,kanal,hovedkanal,musikk = 'itemNext' in visningsvalg, news = False)
					if not dataid:
						dataid = setteDataid(tittel)
					if not komponist:
						creator = ''
					else:
						creator = {'V34':komponist}

					#Sette inn innslags objekt her
					if tittel:
						#Dersom vi ikke har en tittel skal vi ikke ha noe objekt heller
						bilde = bildeFix(d, bilde, dataid)
						addObject(xmldom, innslag,
						runorder = "future",
						channel = kanal,
						subElements = False,
						objecttype="item",
						dataid = dataid,
						tittel = tittel,
						kortTittel = kortTittel,
						abstract = info,
						creator = creator,
						partisipantDescription = artist,
						duration = duration,
						issued = issued,
						gluonType = [{'label':'class', 'reference':'Digas', 'value' : gluonType}],
						bilde = bilde
						)
				if ('newsItemNext' in visningsvalg):
					dataid, tittel, kortTittel, artist, komponist, info, bilde, issued, duration, gluonType = hentItemNext(d,kanal,hovedkanal,musikk = False, news = 'newsItemNext' in visningsvalg)
					if not dataid:
						dataid = setteDataid(tittel)
					#Sette inn innslags objekt her
					if tittel:
						#Dersom vi ikke har en tittel skal vi ikke ha noe objekt heller
						bilde = bildeFix(d, bilde, dataid)
						addObject(xmldom, innslag,
						runorder = "future",
						channel = kanal,
						subElements = False,
						objecttype="item",
						dataid = dataid,
						tittel = tittel,
						abstract = info,
						contributor = {'V36':artist},
						duration = duration,
						issued = issued,
						gluonType = [{'label':'class', 'reference':'Digas', 'value' : gluonType}],
						bilde = bilde
						)

				try:
					#print tablePointer
					if 'programmeNext' in visningsvalg:

						progId, tittel, info, programleder, issued, duration, digastype = hentProgrammeNext(d,kanal,hovedkanal)
						if programleder:
							programleder = {'V40':programleder}
						#print 	progId, tittel, info, programleder, issued, duration, digastype
						#Legge inn som objekt
						if tittel:
							addObject(xmldom, tablePointer,
								subElements = False,
								objecttype="programme",
								channel = kanal,
								dataid = progId,
								tittel = tittel,
								abstract = info,
								contributor = programleder,
								duration = duration,
								issued = issued,
								gluonType = [{'reference':'NRK-Escort', 'value' : digastype}]
								)

						#Sette inn object


				except 0:
					pass


				if testModus:
					print kanal

				#print xmldom.toprettyxml('  ','\n','utf-8')
				#print xmldom.toxml('utf-8')
				data = xmldom.toxml('utf-8')
				#pars = xml.dom.minidom.parseString(xmldom.toprettyxml('  ','\n','utf-8'))


				#SÂ sender vi til gluon

				#Hele denne er i en trxad med timeout, vi trenger ikke noe timeout
				if testModus:
					print (kanal, tittel)
					#print
					print xmldom.toprettyxml('  ','\n','utf-8')
					continue

				for adr in gluonAdr:

					if 'OK' in sendDataWeb(data,adr):
						break



				#return error("nr11",quark, melding="Kunne ikke sende til Webplugg")



	#Lukke databasen

	d.close()

if __name__=='__main__':
	#application/xml

	print "Content-type: text/html"
	print
	lagMetadata(kanal='barn',datatype='iteminfo', testModus=True)
