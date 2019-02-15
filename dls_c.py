#! /usr/local/bin/python
# -*- coding: iso-8859-1 -*-

"""dls tjenester
utspillingsmodul.
Henter data fra databasen, sjekker utvalget fra sidevisningsmodulen, sjekker item som er på utspillingsmodulen
roterer så listen deretter.
"""


# TODO

#Sjekke endringer i konfigurasjon etter en utsendelse for så å sende igjen ev.
#
#****Sjekke distrikskanaler om det er en distriksflate på p1?
#Hva skal trigge distriktsflatene
#
#Levetiden på listene:
#Det må legges inn flere kriterier, kanskje skal vi regenerere listen ved utløp? Slik det er nå vil det IKKE fungere ved blandet informasjon.
#
#Lage rutine som deler på ord 
#Legge inn manglende mellomrom




# BUGS
#None ?

import MySQLdb as mdb
import re
import time
from random import choice, sample

import sendTilDab
import lagTestWeb
import spillUtBreaking
from annonser import *
from dbConn import database

ikkeDls = ['nett'] #Legg inn bloknavn som ikke støtter dls teknologien, nettradioen f. eks.

egenProd = 'EBU-NONRK' #Label for egenproduksjon
maxLevetid = 2
verbose = False
testModus = False 
lagetGrense = 1980 #Årstall for når vi skal markere at eldre er arkivopptak

#def database(host = "160.68.118.48", user="tormodv", database="dab",passord="allmc21"):
#def database(host = "localhost", user="tormodv", database="dab",passord=""):
#	"Lager en databaseconnection."
#	d = mdb.connect(user=user,passwd=passord, host=host)
#	d.select_db(database)
#	return d

def minimumLevetid(d,kanal):
	"Finner den laveste gjenværende tid på en kanal"
	#Denne må modifiseres for å ta hensyn til alle dls'ene i kanalen
	#Kanskje heller ta vare på alle stoptidene slik at vi kan legge de på en stak som regenererer dls,ene?
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
	
	#Vi gjør en enkel test i første omgang, siden kan dette brukes til noe ala : ... sats 1. fulgt av sats 2.
	
	if len(likheten)>3 * len(forskjell) and 'sats' in forskjell:
		return True
	else:
		return False
		

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


def finnHovedkanal(d, kanal):
	"Returnerer navnet pÃ¥ hovedkanalen eller kanalnavn pÃ¥ grunnlag av kanalnavn"
	#Finne fÃ¸rst intern ideen pÃ¥ morkanalen
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

	
def hentVisningsvalg_old(d,kanal, blokkId, datatype=None, oppdatering = 0):
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
		print "UKJENT KANAL", [kanal]
		
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

def hentVisningsvalg(d,kanal, datatype=None, oppdatering = 0):
	"Henter ut visningsvalg og verdier for filterfunksjonen"
	#FÃ¸rst finner vi kanal_ID pÃ¥ kanalen.
		
	
	blk = {}
	als = {}
	c= d.cursor()
	
	sql = """SELECT DISTINCT
			datatyper.tittel,datatyper.alias, blokk.navn
			FROM datatyper  
			INNER JOIN dataikanal ON datatyper.id=dataikanal.datatype_id
			INNER JOIN blokk ON dataikanal.blokk_id=blokk.id
			INNER JOIN kanal ON kanal.id=dataikanal.kanal_id
			
			WHERE kanal.navn = %s;"""
			
	c.execute(sql,(kanal,))
	
	for row in c.fetchall():
		tittel, alias, blokk = row
			
		if not blokk in blk:
			blk[blokk] = [tittel]
			als[blokk] = [alias]
		else:
			blk[blokk].append(tittel)
			als[blokk].append(alias)
	if verbose:print blk, als
	#SÃ¥ er det vake blokker
	#Hvis ikke typen er i alias skal vi ikke ut pÃ¥ den blokken
	#finne typenummer
	sql = """SELECT alias 
			FROM datatyper  
			WHERE tittel = %s LIMIT 1"""
	c.execute(sql,(datatype,))
	if c.rowcount ==1:
		optType = c.fetchone()[0]
	else:
		optType = 0
	
	c.close()
	for vblk in als:
		if not optType in als[vblk]:
			blk.pop(vblk)
	
	return blk

	
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

def hentNyheter(d,kanal, max=None, headlines = True):
	"Henter nyheter fra databasen, ev begrenset til max stykker"
	c= d.cursor()
	if not max:
		sql = """SELECT DISTINCT tittel, sammendrag FROM nyheter ORDER BY prioritering DESC,oppdatert DESC;"""
		c.execute(sql)
	else:
		sql = """SELECT DISTINCT tittel, sammendrag FROM nyheter ORDER BY prioritering DESC,oppdatert DESC LIMIT %s;"""
		c.execute(sql,(max,))
	
		
	while 1:
		row = c.fetchone()
		
		if not row:
			c.close()
			break
		if headlines:
			item = row[0]
		else:
			item = "%s. %s" % row
		if len(item)>128:
			item = row[1]
		if len(item)>128:
			yield [item[:120] + '...','...' + item[120:240]]
		else:
			yield [item]
		

	c.close()
	
def hentProgrammeinfo(d, kanal, hovedkanal, distriktssending  =False, style='enkel', useTimeLimit = True, harDistrikter = False, forceDistrikt = True):	
	"""Henter informasjon om programmet som er på lufta, returnerer en liste med et element. Ved distriktssendinger kan flagget
	for distriktssendinger settes.
	Finner ut om det gjeldenede programmet er paa lufta akkurat naa, dersom ikke finner ut om hovedkanalen har data
	Dersom forceDistrikt flagget er satt, saa vil et program i en distriktskanal komme paa lufta uten at det er definert dirstriktskana"""
	#Skal returnere lista og distriktsflagg
	#Endres når det ikke blir vanlig å legge inn programleder i beskrivelsesfeltet
	
	c= d.cursor()

	#Sjekke om programmet er utlÃ¸pt i kanalen
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
		#Vi har med Ã¥ gjÃ¸re en distriktskanal som har eget program, da skal hele dls-en ignoreres. Den skal genereres ut ifra kanalens egen oppkall
		c.close()
		if verbose:print 'VOID - har eget program'
		return ['VOID'], False	
		# Sjekke pÃ¥ denne verdien om kanalen skal hoppes over i 
	
	#Finne alternativ mÃ¥te for Ã¥ tenne distriktsflagg
	if iProgramme and (kanal != hovedkanal):
		#Kanalen har et aktivt program, og den har en mor, dvs hovedkanl er ikke seg selv.
		distriktssending = True
	

	#Vi må sjekke om hovedkanalen har en distriktsflate
	
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
	if digastype == '50' and (kanal != hovedkanal):
		#Vi har en distriktssending av den gamle typen
		distriktssending = True
		#Vi har ennå ikke distriktsvise programme info
		#Vi henter først ut navnet "Brandet" på kanalen
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
			
		kanal = hovedkanal #Dette gjør at vi aldri henter programdata fra distriktsflaten
		
	else:
		#Vi skal ikke har regionvise resultater
		if forceDistrikt and iProgramme:
			#Vi bytter ikke kanaler, men stryker sufix
			tittelSufix = ''
		else:
			kanal = hovedkanal
			tittelSufix = ''
		

	c= d.cursor()
	sql = """SELECT tittel, beskrivelse, artist, tid FROM iteminfo WHERE kanal=%s AND type='programme' AND localid = '1' 
	LIMIT 1;"""			
	c.execute(sql,(kanal,))
	try:
		try:
			tittel, beskrivelse, artist, tid = c.fetchone()
		finally:
			c.close()
	except TypeError:
		#Dersom vi ikke har noe her, kan det hende det er en distriktskanal som ikke har egne metadata, 
		# *** ENDRING sjekke om programdataene er utløpt
		if hovedkanal and not distriktssending:
			return hentProgrammeinfo(d,hovedkanal,None, distriktssending=distriktssending, style=style, useTimeLimit= useTimeLimit)
		else:
			return [''], distriktssending
	
	
	tittel = tittel + tittelSufix #Legger på f. eks. "fra NRK Trøndelag" på dirstriksflater 
	
	#Dersom vi ikke er i en sending, skal vi jo ikke vise noe program
	
	#if not iProgramme:
	#	return ['Ingen sending'], distriktssending
	
	#Dersom vi er mer enn fem minutter, 300 sekunder inn i et program viser vi bare programmet
	
	sekunderSiden = time.time() - ISOtilDato(tid,sekunder=1, sql=1)
	#Tar bort programomtale litt ut i programmet.
	
	if sekunderSiden>600 and useTimeLimit:
		if style=='enkel':
			return [tittel], distriktssending
		else:
			return [choice(lytter) + ' ' + tittel], distriktssending
	

	if artist:
		if style=='enkel':
			item = tittel + '. ' + artist
	                if len(item) > 128:
                        	return [tittel, artist], distriktssending
                	else:
                        	return [item], distriktssending
		else:
			item = choice(lytter) + ' ' + tittel + '. ' + artist
			if len(item) > 128:
				return [choice(lytter) + ' ' + tittel, artist], distriktssending
			else:
				return [item], distriktssending

	else:
		if style=='enkel':
			item = tittel + '. ' + beskrivelse
                	if len(item) > 128:
                        	return [tittel, beskrivelse], distriktssending
                	else:
                	        return [item], distriktssending
		else:
			item = choice(lytter) + ' ' + tittel + '. ' + beskrivelse
			if len(item) > 128:
				return [choice(lytter) + ' ' + tittel, beskrivelse], distriktssending
			else:
				return [item], distriktssending
	
def hentProgrammeNext(d,kanal,hovedkanal,distriktssending=0):
	"Henter informasjon om det neste programmet som skal på lufta, returnerer en liste med et element."
	c= d.cursor()
	sql = """SELECT tittel, tid FROM iteminfo WHERE kanal=%s AND type='programme' AND localid = '2' AND ((UNIX_TIMESTAMP(tid) - UNIX_TIMESTAMP(now())) < 435) LIMIT 1;"""
	
	c.execute(sql,(kanal,))
	try:
		try:
			
			tittel, tid = c.fetchone()
		finally:
			c.close()
	except TypeError:
		if hovedkanal and not distriktssending:
			return hentProgrammeNext(d,hovedkanal,None)
		else:
			return []

	if type(tid)!=type(''):
		#Dette er en forelÃ¸pig patch for at en har begynt Ã¥ bruke datetime objekter
		tid = tid.isoformat()
	#print tid,tittel
	#item = "Klokka " + tid[11:16] + ' kommer ' + tittel 
	item = tid[11:16] + '- ' + tittel	
	return [item]
	
def hentEpg(d,kanal,hovedkanal,distriktssending=0):
	"Henter informasjon om programmene utover dagen og kvelden, returnerer en liste med et element."
	
	#Først finne klokka
	timen = time.localtime()[3]
	if timen<6:
		#Vi har gamle data om natta
		return []
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
			#Vi har en ukjent kanal, uten epg, vi prøver å gå opp et hakk
			return hentEpg(d,hovedkanal,None)
		else:
			return []
		
	if not (dagerGammel ==0 or (dagerGammel==1 and timen<6)):
		if verbose:print "EPG er GAMMEL"
		return []
	
	

	#Her er det vel ingen hensikt å dele på distrikter, der alle distriktene nå er like, med henhold til sendetidspunkter, eller?
	
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

	
	item = "%s" % info #Legge inn På P1 i kveld...
	
	return [item]


def hentTextinfo(d,kanal,blokk,hovedkanal,datatype,distriktssending=0, breaking = False):
	"Henter informasjon og flashmeldinger om sendingen, støtter foreløpig kunn programnivået"
	if breaking and datatype == 'textinfo':
		#Vi legger flashmeldingen fra tabellen ut til breaking køen
		
		c= d.cursor()
		sql = """SELECT innhold FROM textinfo_breaking WHERE kanal=%s AND type='programme'  AND localid = '1' LIMIT 1;"""
	
		c.execute(sql,(kanal,))
		try:
			try:
				innhold, = c.fetchone()
			finally:
				c.close()
		except TypeError:
			#Vi har ikke data for distrikskanalen, vi spør igjen på hovedkanalen
			if hovedkanal and not distriktssending:
				c= d.cursor()
				sql = """SELECT innhold FROM textinfo_breaking WHERE kanal=%s AND type='programme'  AND localid = '1' LIMIT 1;"""
	
				c.execute(sql,(hovedkanal,))
				try:
					try:
						innhold, = c.fetchone()
					finally:
						c.close()
				except TypeError:
					#Vi har vel ingenting
					innhold = ''
		#Dersom vi har fått tak i noe spiller vi dette ut
		#print 7878,kanal,blokk
		if innhold:
			c=d.cursor()

		
			sql = """INSERT INTO breaking(id,kanal,blokk,visningslengde,tid,tekst) VALUES
										(%s,%s,%s,%s,NOW(),%s)
										"""
			c.execute(sql,(
												id,
												kanal,
												blokk,
												15,
												innhold
												)
										)
			c.close()
			#Vi har lagt til noe i køen, kjør oppdatereren

			spillUtBreaking.main(kanal)
	
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
			#Flash breaking meldingene skal bare gå ut på dden kanalen de er kalt på , der for ingen arving
			return hentTextinfo(d,hovedkanal,blokk,None,datatype)
		else:
			return []

	
	
	#Rutine som sjekker om elementet er utløpt.
	
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
		return []
	else:
		c1.close()
		
		slutttid1 = ISOtilDato(tid1,sekunder=1,sql=1) + lengde
		
		if time.time()>=slutttid1:
		
			
			return []
			

	
	return [innhold]



def hentTextinfo2(d,kanal,hovedkanal,distriktssending=0):
	"Henter informasjon og flashmeldinger om sendingen, støtter foreløpig kunn programnivået"
	
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
			return []

	
	
	#Rutine som sjekker om elementet er utløpt.
	
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
		return []
	else:
		c1.close()
		
		slutttid1 = ISOtilDato(tid1,sekunder=1,sql=1) + lengde
		
		if time.time()>=slutttid1:
		
			
			return []
			

	
	return [innhold]
	
	
			
def hentIteminfo(d,kanal,hovedkanal,distriktssending=0):
	"Henter informasjon om musikkinnslaget som er på lufta, returnerer en liste med et element."
	
	
	#Dersom vi ikke har en distriktssending, skal vi gå til hovedkanalen for metadata:
	
	if not distriktssending:
		kanal = hovedkanal


	c= d.cursor()
	#Først må vi finne ut om vi har en samsending
	
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
	
	sql = """SELECT tittel,artist, beskrivelse, digastype, label FROM iteminfo WHERE kanal=%s AND type='item'  AND localid = '3' LIMIT 1 ;"""
	
	c.execute(sql,(kanal,))
	try:
		try:
			tittel,artist, beskrivelse, digastype, label = c.fetchone()
		finally:
			c.close()
	except TypeError:
		if hovedkanal and not distriktssending:
			return hentIteminfo(d,hovedkanal,None)
		else:
			return []
	#Stotte for BMS som ikke har digastyper, default er musikk		
	if digastype:
		if digastype !='Music':
			return []

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
		

		
	if kanal in itemtittel:
		if not artist:
			item = tittel
		elif artist[0]=='.':
			#Dette er en type som ikke kan bindes med verk, ved hjelp av "spiller" verbet.
			#Vi velger derfor egen annonseringstype for dette.
			try:
				item = eval(choice(itemtittel[kanal+'_S']))
			except KeyError:
				#Dersom det ikke er laget egen maltype for dette faller vi tilbake på originalen
				item = eval(choice(itemtittel[kanal]))
		else:
			item = eval(choice(itemtittel[kanal]))
	else:
		item = eval(choice(itemtittel['nrk']))
	
	if label.startswith(egenProd):
		#Vi tar den enkle utvegen, det er snakk om en ann. av et program, denne er det vel snart ikke brukt for lenger men vi beholder den litt til. ***
		item = tittel+ '.|'+ artist
	
	
	s=[]
	#Sette sammen dls til så få linjer som mulig
	part = ''
	deler = item.split('|')
	for delen in deler:
		
		
		if part:
			if len(part) + len(delen) < 125:
				part = part + ' ' + delen
			elif len(delen) < 125:
				#Vi legger den ferdige dls fragmentet til listen
				s.append(part + '...')
				part = '...' + delen
			else:
				#Dls frqagmentet er for langt
				#Vi deler det på punktum, dersom det finnes
				
				if '.' in delen:
					del1,del2 = delen.split('.',1)
					if len(part) + len(del1) < 125:
						s.append(part + ' ' + del1 + '...')
						part = '...' + del2
					else:
						#Vi må dytte part i listen
						s.append(part + '...')
						s.append('...'+del1 + '...')
						part = '...' + del2
				else:
					pass
					print "#HER SKULLE VI IKKE HA VÆRT#"
					#eg krise
					#Lage rutine som deler på ord 
		else:
		
			part = delen
	#Opprydding vi må uansett legge til den siste part
	s.append(part)
	#Dersom det er ønskelig legge til platemerke
	if kanal == 'ak' and label:
		if not label.startswith('EBU-'):
			s.append(label)
	return s
	
def hentIteminfoExtra(d,kanal,hovedkanal,distriktssending=0):
	"Henter informasjon om ekstra musikkinformasjon om innslaget som er på lufta, returnerer en liste med et element."
	
	#Dersom vi ikke har en distriktssending, skal vi gå til hovedkanalen for metadata:
	
	if not distriktssending:
		kanal = hovedkanal


	c= d.cursor()
	#Først må vi finne ut om vi har en samsending
	
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
	



	sql = """SELECT tittel,artist, beskrivelse, digastype, label FROM iteminfo WHERE kanal=%s AND type='item'  AND localid = '3' LIMIT 1 ;"""
	#print 777
	c.execute(sql,(kanal,))
	try:
		try:
			tittel,artist, beskrivelse, digastype, label = c.fetchone()
		finally:
			c.close()
	except TypeError:
		if hovedkanal and not distriktssending:
			return hentIteminfoExtra(d,hovedkanal,None)
		else:
			return []
	#print beskrivelse
	#print 888
	#For å få kompabilitet med BMS
	if digastype:
		if digastype !='Music':
			return []
	#Siden vi bare skal ha Extrainfo her
	if beskrivelse:
		item = beskrivelse
	else:
		return []
		
	s=[]
	#Sette sammen dls til så få linjer som mulig
	part = ''
	deler = item.split('|')
	for delen in deler:
		
		
		if part:
			if len(part) + len(delen) < 125:
				part = part + ' ' + delen
			elif len(delen) < 125:
				#Vi legger den ferdige dls fragmentet til listen
				s.append(part + '...')
				part = '...' + delen
			else:
				#Dls frqagmentet er for langt
				#Vi deler det på punktum, dersom det finnes
				
				if '.' in delen:
					del1,del2 = delen.split('.',1)
					if len(part) + len(del1) < 125:
						s.append(part + ' ' + del1 + '...')
						part = '...' + del2
					else:
						#Vi må dytte part i listen
						s.append(part + '...')
						s.append('...'+del1 + '...')
						part = '...' + del2
				else:
					pass
					print "#HER SKULLE VI IKKE HA VÆRT#"
					#eg krise
					#Lage rutine som deler på ord 
		else:
		
			part = delen
	#Opprydding vi må uansett legge til den siste part
	s.append(part)
	#print s
	return s
		
def hentNewsItem(d,kanal,hovedkanal,distriktssending=0):
	"Henter informasjon om innslaget som er på lufta, dersom det er et news innslag; returnerer en liste med et element."
	
	#Dersom vi ikke har en distriktssending, skal vi gå til hovedkanalen for metadata:
	if not distriktssending:
		kanal = hovedkanal


	c= d.cursor()
	#Først må vi finne ut om vi har en samsending
	
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

	sql = """SELECT tittel,artist, beskrivelse, digastype, label FROM iteminfo WHERE kanal=%s AND type='item'  AND localid = '3' LIMIT 1 ;"""
	
	c.execute(sql,(kanal,))
	try:
		try:
			tittel,artist, beskrivelse, digastype, label = c.fetchone()
		finally:
			c.close()
	except TypeError:
		if hovedkanal and not distriktssending:
			return hentIteminfo(d,hovedkanal,None)
		else:
			return []
	
	if digastype !='News':
		return []
		
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
		

		
	if kanal in newstittel:
		if not artist:
			item = tittel
			
		elif artist[0]=='.':
			#Dette er en type som ikke kan bindes med verk, ved hjelp av "spiller" verbet.
			#Vi velger derfor egen annonseringstype for dette.
			try:
				item = eval(choice(newstittel[kanal+'_S']))
			except KeyError:
				#Dersom det ikke er laget egen maltype for dette faller vi tilbake på originalen
				item = eval(choice(newstittel[kanal]))
		else:
			item = eval(choice(newstittel[kanal]))
	else:
		item = eval(choice(newstittel['nrk']))
	
	s=[]
	#Sette sammen dls til så få linjer som mulig
	part = ''
	deler = item.split('|')
	for delen in deler:
		
		
		if part:
			if len(part) + len(delen) < 125:
				part = part + ' ' + delen
			elif len(delen) < 125:
				#Vi legger den ferdige dls fragmentet til listen
				s.append(part + '...')
				part = '...' + delen
			else:
				#Dls frqagmentet er for langt
				#Vi deler det på punktum, dersom det finnes
				
				if '.' in delen:
					del1,del2 = delen.split('.',1)
					if len(part) + len(del1) < 125:
						s.append(part + ' ' + del1 + '...')
						part = '...' + del2
					else:
						#Vi må dytte part i listen
						s.append(part + '...')
						s.append('...'+del1 + '...')
						part = '...' + del2
				else:
					pass
					print "#HER SKULLE VI IKKE HA VÆRT#"
					#eg krise
					#Lage rutine som deler på ord 
		else:
		
			part = delen
	#Opprydding vi må uansett legge til den siste part
	s.append(part)
	
	return s

def hentNewsInfo(d,kanal,hovedkanal,distriktssending=0):
	"Henter extra informasjon om nyhetsinnslag som er på lufta, returnerer en liste med et element."
	
	#Dersom vi ikke har en distriktssending, skal vi gå til hovedkanalen for metadata:
	if not distriktssending:
		kanal = hovedkanal


	c= d.cursor()
	#Først må vi finne ut om vi har en samsending
	
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
	



	sql = """SELECT tittel,artist, beskrivelse, digastype, label FROM iteminfo WHERE kanal=%s AND type='item'  AND localid = '3' LIMIT 1 ;"""
	
	c.execute(sql,(kanal,))
	try:
		try:
			tittel,artist, beskrivelse, digastype, label = c.fetchone()
		finally:
			c.close()
	except TypeError:
		if hovedkanal and not distriktssending:
			return hentNewsInfo(d,hovedkanal,None)
		else:
			return []

	if digastype !='News':
		return []
		
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
		

	if beskrivelse:	
		item = beskrivelse
	else:
		return []
		
	s=[]
	#Sette sammen dls til så få linjer som mulig
	part = ''
	deler = item.split('|')
	for delen in deler:
		
		
		if part:
			if len(part) + len(delen) < 125:
				part = part + ' ' + delen
			elif len(delen) < 125:
				#Vi legger den ferdige dls fragmentet til listen
				s.append(part + '...')
				part = '...' + delen
			else:
				#Dls frqagmentet er for langt
				#Vi deler det på punktum, dersom det finnes
				
				if '.' in delen:
					del1,del2 = delen.split('.',1)
					if len(part) + len(del1) < 125:
						s.append(part + ' ' + del1 + '...')
						part = '...' + del2
					else:
						#Vi må dytte part i listen
						s.append(part + '...')
						s.append('...'+del1 + '...')
						part = '...' + del2
				else:
					pass
					print "#HER SKULLE VI IKKE HA VÆRT#"
					#eg krise
					#Lage rutine som deler på ord 
		else:
		
			part = delen
	#Opprydding vi må uansett legge til den siste part
	s.append(part)

	return s

def hentItemNext(d,kanal,hovedkanal,distriktssending=0):
	"Henter informasjon om det neste innslaget som skal på lufta, returnerer en liste med et element."
	#Dersom vi ikke har en distriktssending, skal vi gå til hovedkanalen for metadata:
	#******
	distriktssending = 0	
	if not distriktssending:
		kanal = hovedkanal


	
	c= d.cursor()
	#Først må vi finne ut om vi har en samsending
	
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
	

	#Først finne ut om vi har to like titler. Dersom denne feiler har vi i alle fall ikke noen like titler.
	try:
		sql = """SELECT tittel FROM iteminfo WHERE kanal=%s AND type='item' AND (localid = '4' OR localid = '3')  LIMIT 2;"""
		c.execute(sql,(kanal,))
		
		tittel1 = c.fetchone()[0]
		tittel2 = c.fetchone()[0]
	except:
		tittel1 = 'x'
		tittel2 = 'y'
		
	#Dersom titlene er like med untak av satsbetegnelsene viser vi ingenting
	else:
		if sammenlignTittler(tittel1,tittel2):
			return []
		
	#Ellers viser vi nesteinformasjon
	sql = """SELECT tittel, artist, digastype, tid  FROM iteminfo WHERE kanal=%s AND type='item' AND localid = '4' LIMIT 1;"""
	
	
	c.execute(sql,(kanal,))
	try:
		try:
			tittel, artist, digastype, tid = c.fetchone()
		finally:
			c.close()
	except TypeError:
		if hovedkanal and not distriktssending:
			return hentItemNext(d,hovedkanal,None)
		else:
			return []

	if type(tid)!=type(''):
		#Dette er en forelÃ¸pig patch for at en har begynt Ã¥ bruke datetime objekter
		tid = tid.isoformat()
	
	ur = tid[11:16]
	
	#For å få kompabilitet med BMS
	if digastype:		
		if digastype != 'Music':
			return []
		
	if kanal in nesteItemtittel:
		if not artist  and ('artist' in nesteItemtittel[kanal]):
			item = tittel
			
		else:
			item = eval(choice(nesteItemtittel[kanal])) 
	else:
		item = eval(choice(nesteItemtittel['nrk']))
	
	s=[]
	#Sette sammen dls til så få linjer som mulig
	part = ''
	deler = item.split('|')
	for delen in deler:
		
		
		if part:
			if len(part) + len(delen) < 125:
				part = part + ' ' + delen
			elif len(delen) < 125:
				#Vi legger den ferdige dls fragmentet til listen
				s.append(part + '...')
				part = '...' + delen
			else:
				#Dls frqagmentet er for langt
				#Vi deler det på punktum, dersom det finnes
				if '.' in delen:
					del1,del2 = delen.split('.',1)
					if len(part) + len(del1) < 125:
						s.append(part + ' ' + del1 + '...')
						part = '...' + del2
					else:
						#Vi må dytte part i listen
						s.append(part + '...')
						s.append('...'+del1 + '...')
						part = '...' + del2
				else:
					pass
					print "#HER SKULLE VI IKKE HA VÆRT#"
					#eg krise
		else:
		
			part = delen
	#Opprydding vi må uansett legge til den siste part
	s.append(part)
	
	return s
	
def hentNewsItemNext(d,kanal,hovedkanal,distriktssending=0):
	"Henter informasjon om det neste innslaget som skal på lufta, returnerer en liste med et element."
	#Dersom vi ikke har en distriktssending, skal vi gå til hovedkanalen for metadata:
	#******
	distriktssending = 0
	if not distriktssending:
		kanal = hovedkanal


	
	c= d.cursor()
	#Først må vi finne ut om vi har en samsending
	
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
	
		
	#Ellers viser vi nesteinformasjon
	sql = """SELECT tittel, artist, digastype, tid FROM iteminfo WHERE kanal=%s AND type='item' AND localid = '4' LIMIT 1;"""
	
	
	c.execute(sql,(kanal,))
	try:
		try:
			tittel,artist, digastype, tid = c.fetchone()
		finally:
			c.close()
	except TypeError:
		if hovedkanal and not distriktssending:
			return hentNewsItemNext(d,hovedkanal,None)
		else:
			return []
	
	if digastype != 'News':
		return []
	
	if type(tid)!=type(''):
		#Dette er en forelÃ¸pig patch for at en har begynt Ã¥ bruke datetime objekter
		tid = tid.isoformat()


	ur = tid[11:16]

	if kanal in nesteNewstittel:
		if not artist and ('artist' in nesteNewstittel[kanal]):
			item = tittel
			
		else:
			item = eval(choice(nesteNewstittel[kanal])) 
	else:
		item = eval(choice(nesteNewstittel['nrk']))
	
	s=[]
	#Sette sammen dls til så få linjer som mulig
	part = ''
	deler = item.split('|')
	for delen in deler:
		
		
		if part:
			if len(part) + len(delen) < 125:
				part = part + ' ' + delen
			elif len(delen) < 125:
				#Vi legger den ferdige dls fragmentet til listen
				s.append(part + '...')
				part = '...' + delen
			else:
				#Dls frqagmentet er for langt
				#Vi deler det på punktum, dersom det finnes
				if '.' in delen:
					del1,del2 = delen.split('.',1)
					if len(part) + len(del1) < 125:
						s.append(part + ' ' + del1 + '...')
						part = '...' + del2
					else:
						#Vi må dytte part i listen
						s.append(part + '...')
						s.append('...'+del1 + '...')
						part = '...' + del2
				else:
					pass
					print "#HER SKULLE VI IKKE HA VÆRT#"
					#eg krise
		else:
		
			part = delen
	#Opprydding vi må uansett legge til den siste part
	s.append(part)
	
	return s


def hentBadetemperaturer(d,kanal,hovedkanal,distriktssending=0):
	"Henter badetemperaturer til reiseradioen o.l."
	c= d.cursor()
	sql = """select
stedsnavn,
vanntemperatur

from bade_temp
where
vanntemperatur <> 0
and 
TO_DAYS(NOW()) - TO_DAYS(oppdatert) = 0
and svarteliste = 'N'
order by
vanntemperatur 
desc
;"""

	sql2 = """select
stedsnavn,
vanntemperatur

from bade_temp
where
vanntemperatur <> 0
and 
TO_DAYS(NOW()) - TO_DAYS(oppdatert) = 0
and
svarteliste = 'N'
and 
fylkesnavn in ('Oslo', 'Akershus','Østfold','Vestfold','Buskerud','Telemark')
order by
vanntemperatur 
desc
;"""
	#Finne riktig sql spørring
	if kanal=='p1of' or kanal=='p1_ndoa':
		sql=sql2
 
	
	s=[]
	listestreng = 'Badetemperaturene : Høyest - '
	c.execute(sql,)
	temperaturliste = c.fetchall()
	if len(temperaturliste) == 0:
		return []
	if len(temperaturliste) > 5:
		temperaturliste = [temperaturliste[0]]+sample(temperaturliste[1:-1],3)+ [temperaturliste[-1]]
	for temp in temperaturliste:
		sted,temperatur = temp
		if ',' in sted:
			sted = sted.split(',')[0]
		listestreng += "%s:%s|" % (sted,temperatur)
	listestreng += '(lavest)'
	

	#Sette sammen dls til så få linjer som mulig
	part = ''
	deler = listestreng.split('|')
	for delen in deler:
		
		if part:
			if len(part) + len(delen) < 125:
				part = part + ' ' + delen
			elif len(delen) < 125:
				#Vi legger den ferdige dls fragmentet til listen
				s.append(part + '...')
				part = '...' + delen
			
		else:
		
			part = delen
	#Opprydding vi må uansett legge til den siste part
	s.append(part)

		
	return s
def hentResult(d,kanal,blokk,hovedkanal,datatype,distriktssending=0):
	"Henter resultater (Fotball)"
	#Lage liste
	c= d.cursor()
	sql = """select
h_lag,
b_lag,
hjemme_P,
borte_P,
status


from result
where
TO_DAYS(NOW()) - TO_DAYS(oppdatert) = 0
and
status <> 0
order by
id
desc
;"""

	s=[]
	listestreng = '4-4-2: '
	c.execute(sql,)
	resultatliste = c.fetchall()
	c.close()
	#print resultatliste
	if len(resultatliste) == 0:
		return [] #Rettes når man skal ha breaking meldinger
		
	for resultat in resultatliste:
		#Lage flagg
		status = resultat[4]
		if status ==1:
			flagg = '*'
		elif status == 2:
			flagg = 'p'
		else:
			flagg = ''
		if status == 0:
			listestreng += "%s-%s:x-x|" % resultat[:2]
		else:
			listestreng += "%s-%s:%s-%s%s|" % (resultat[:4]+(flagg,))
	listestreng += ''
	

	#Sette sammen dls til så få linjer som mulig
	part = ''
	deler = listestreng.split('|')
	for delen in deler:
		
		if part:
			if len(part) + len(delen) < 125:
				part = part + ' ' + delen
			elif len(delen) < 125:
				#Vi legger den ferdige dls fragmentet til listen
				s.append(part + '...')
				part = '...' + delen
			
		else:
		
			part = delen
	#Opprydding vi må uansett legge til den siste part
	s.append(part)
	#print s
	
	#Hente ut flash meldingen
	c= d.cursor()
	sql = """select
id,
hendelse,
oppdatert,
status

from result
#where
#TO_DAYS(NOW()) - TO_DAYS(oppdatert) = 0
order by
oppdatert
desc
limit 1
;"""

	try:
		#Denne tjenesten kann feile, da bare hoppper vi over det 
	
		c.execute(sql,)
		id, hendelse, oppdatert, status = c.fetchone()
		if hendelse != '' and datatype=='result':
			sql = """INSERT INTO breaking(id,kanal,blokk,visningslengde,tid,tekst) VALUES 
					(%s,%s,%s,%s,NOW(),%s)
					""" 
			c.execute(sql,(
						id,
						kanal,
						blokk,
						15,
						hendelse
						)
					) 
			c.close()
			#Da har vi lagt noe til i køen, nå kan vi prøve å tømme den igjen
			#Vi kjører køtømmeren
		
		
			spillUtBreaking.main(kanal)
		else:
			#Vi har ingenting, vi lukker
			c.close()
		
	except:
		pass
	#Sjekke om vi skal ha med meldingen, aldri etter klokken 22.
	if time.localtime()[3]>21:
		return []
	else:	
		return s


def hentTraffic(d,kanal,blokk,hovedkanal,datatype, distriktssending=0, id=''):
	"Henter Trafikkmeldinger, legger disse rett til utspillingskø for listetype null meldinger, trafikkmeldinger er kun breaking"
	#Datatype trengs for enheter som kanskje er breaking
	#Denne skal bare dytte trafikkmeldinger i køen, aldri legge noe ut i en liste, derfor skal den bare svare på trafikkmeldinge
	if datatype != 'traffic':
		return []
	#Hente ut flash meldingen
	c= d.cursor()
	sql = """select
kortmelding,
fylke,
viktighet
from traffic
where
id=%s
limit 1
;"""

	
	
	c.execute(sql,(id,))
	kortmelding, fylke, viktighet = c.fetchone()
	
	#Gjelder meldingen innenfor kanalens virkningsområde
	
	sql = """select
utbredelse 
from kanal
where
navn=%s
limit 1
;"""
	c.execute(sql,(kanal,))
	utbredelse,  = c.fetchone()
	if not (fylke in utbredelse or utbredelse=='Riks'):
		#Vi er ikke på rett sted i geografien
		return []
	
	
	#Forutsetter at vi skal sende ut meldingen
	if viktighet == 5:
		times = 3
	else:
		times = 1
	for i in range(times):
		#Vi oppdaterer
		sql = """INSERT INTO breaking(id,kanal,blokk,visningslengde,tid,tekst) VALUES
										(%s,%s,%s,%s,NOW(),%s)
										"""
		c.execute(sql,(
										id,
										kanal,
										blokk,
										15,
										kortmelding
												)
										)
	c.close()
	#Da har vi lagt noe til i køen, nå kan vi prøve å tømme den igjen
	#Vi kjører køtømmeren

						
	spillUtBreaking.main(kanal)
	

	return []




def storForbokstav(item):
	return item[0].upper() + item[1:]
	
def roter(s,n):
	"Roterer en liste N plasser"
	return s[n:] + s[:n]
	
def lagVisningstider(streng, min = 4, max = 30):
	"Lager en kommaseparert liste med visningstider, slik at vi får en individuel tilpassning av dls-ene"
	#128 er max linjelengde som gir verdien max
	
	return str(int((len(streng)) / 128.0 * max + min))
	
	

def tilDab(kanal='alle',datatype=None,id=''):
	"Henter data for en gitt kanal ut i fra de forskjellige databasene og setter sammen til en DLS som sendes videre som et mimemultipartdokument."

	#kanal='alle'
	#Fange opp at jeg skal kunne generere nytt på alle kanaler.
	d = database()
	if kanal == 'alle':
		kanaler = finnKanaler(d,ikkeDistrikt = False)
	else:
		kanaler = [kanal]
		#Det kan hende at kanalene er delt opp i distrikter - eks. p1oslo
			
	#Finne blokker
	#blokker = finnBlokker(d)
	#Breaking blir styrt av typen inn ved at det står datatype:breaking
	#Ved breaking sender vi det som skal breakes til en egen kø
	#Vi genererer alltid en vanlig liste, selv om vi får breaking. Derfor:
	if 'breaking' in datatype:
		listetype = 1
		breaking = 1
	else:
		listetype = 1
		breaking = 0
	#Datatypen må trimmes hvis den inneholder :breaking
	if ':' in datatype:
		datatype = datatype.split(':')[0]	
		
	for kanal in kanaler:
		#Det kan hende at kanalene er delt opp i distrikter - eks. p1oslo
		#utvid kanaler
		distriktskanaler = distriktskanal(d, kanal)
		if len(distriktskanaler) == 1:
			#Vi har kunn en kanal, distrikskanal eller kanalen selv, vi mÃ¥ finne moderkanalen
			hovedkanal = finnHovedkanal(d, kanal)
			harDistrikter = False
		else:
			#Vi har en kanal med barn, ergo er hovedkanalen kanalen selv.
			hovedkanal = kanal
			harDistrikter = True 

		for kanal in distriktskanaler:
			#Filtrer for distriktskanaler som hr egne metadata
			if hentProgrammeinfo(d, kanal, hovedkanal, harDistrikter = harDistrikter)[0][0]=='VOID':
				if verbose:print "%s hadde egne data, ikke bruk %s" % (kanal, hovedkanal)
				continue
			visningsvalgBlokk = hentVisningsvalg(d, kanal, datatype=datatype)
			if verbose:print 'Skal vises:', kanal, visningsvalgBlokk.keys() 
			#Flush testfilene
                        if not (breaking or testModus):
                                lagTestWeb.sendData(kanal,
                                        liste = [],
                                        )

			
			for blokk in visningsvalgBlokk:
				if blokk in ikkeDls:
					if verbose:print "Ikke vis som DLS pÃ¥ %s" % blokk
					continue
				#Bygge opp visningslista
				#Hente visningsvalg
				
				#**************************************
				# Her må vi finne ut om vi skal lage en liste av typen 1 vise en gang og en ordinær liste
				#Listetypen er gitt av om den insendte datatypen skal gå som breaking news eller inn i ordinær liste
				#**************************************
				
				visningsvalg = visningsvalgBlokk[blokk]
				if verbose:print 'Skal vises:', kanal, visningsvalgBlokk.keys() 

				
				if verbose:print "Visningsvalg:", visningsvalg
				if verbose:print "Datatype:", datatype

				fletting = False
				
				s=[]
				sk=[]	
				#Så til tjenestegruppene
				if 'news' in visningsvalg:
					if listetype == 0:
						max = 1
					else:
						max = 7
					nytt = hentNyheter(d,kanal,max=max)
				else:
					nytt = []
				
				#Vi trenger aa hente programmeinfo uansett, men vi bruker dataene bare hvis det skal vises
				programmeDls, distriktssending = hentProgrammeinfo(d,kanal,hovedkanal, harDistrikter = harDistrikter)

				if 'iteminfo' in visningsvalg:
					s.extend(hentIteminfo(d,kanal,hovedkanal, distriktssending=distriktssending))
				if 'newsItem' in visningsvalg:
					s.extend(hentNewsItem(d,kanal,hovedkanal, distriktssending=distriktssending))
				if fletting:
					try:
						s.extend(nytt.next())
					except StopIteration:
						pass
	
				if 'pgrinfo' in visningsvalg:
					s.extend(hentPgrinfo(d,kanal,hovedkanal))
				if fletting:
					try:
						s.extend(nytt.next())
					except StopIteration:
						pass
				#ProgrammeDls hentes ut ovenfor
				if 'programmeinfo' in visningsvalg:
					s.extend(programmeDls)
					
				if fletting:
					try:
						s.extend(nytt.next())
					except StopIteration:
						pass
				if 'textinfo' in visningsvalg:
					s.extend(hentTextinfo(d,kanal, blokk,hovedkanal,datatype,breaking=breaking))
					#Dette her er flash meldinger
			
				if fletting:
					try:
						s.extend(nytt.next())
					except StopIteration:
						pass

				if 'iteminfo' in visningsvalg:
					#Musikkobjekter
					linja = hentIteminfo(d,kanal,hovedkanal, distriktssending=distriktssending)
					s.extend(linja)
					sk.extend(linja)
				if 'musicInfo' in visningsvalg:
					#Tillegsinfo om musikk
					s.extend(hentIteminfoExtra(d,kanal,hovedkanal, distriktssending=distriktssending))
					#print s
				#Et element er aldri både 'music' og 'news', derfor vill maks to innførsler her
				#s.extend([]) har ingen effekt
				if 'newsItem' in visningsvalg:
					#Andre objekter
					linja = hentNewsItem(d,kanal,hovedkanal, distriktssending=distriktssending)
					s.extend(linja)
					sk.extend(linja)
				if 'newsInfo' in visningsvalg:
					#Tillegsinfo om news
					s.extend(hentNewsInfo(d,kanal,hovedkanal, distriktssending=distriktssending))
					
				if fletting:
					try:
						s.extend(nytt.next())
					except StopIteration:
						pass
				if 'itemNext' in visningsvalg:
					s.extend(hentItemNext(d,kanal,hovedkanal))
				if 'newsItemNext' in visningsvalg:
					s.extend(hentNewsItemNext(d,kanal,hovedkanal))
					
					
				if fletting:
					try:
						s.extend(nytt.next())
					except StopIteration:
						pass

						
				#Dersom det er veldig kort DLS så kan vi tvangsstyre infofeltet for ptogram
				if 'programmeinfo' in visningsvalg and len(s)<3:
					s.extend(hentProgrammeinfo(d,kanal,hovedkanal, useTimeLimit=False, harDistrikter = harDistrikter)[0])		
						
				if 'programmeNext' in visningsvalg:
					s.extend(hentProgrammeNext(d,kanal,hovedkanal))
				if fletting:
					try:
						s.extend(nytt.next())
					except StopIteration:
						pass
				if 'epg' in visningsvalg:
					s.extend(hentEpg(d,kanal,hovedkanal))
				if fletting:
					try:
						s.extend(nytt.next())
					except StopIteration:
						pass
				if 'result' in visningsvalg:
					s.extend(hentResult(d,kanal, blokk,hovedkanal, datatype))
				if fletting:
					try:
						s.extend(nytt.next())
					except StopIteration:
						pass
				if 'traffic' in visningsvalg:
					s.extend(hentTraffic(d,kanal,blokk,hovedkanal,datatype,id=id))
				if fletting:
					try:
						s.extend(nytt.next())
					except StopIteration:
						pass

				#Dumpe ut resten av nyhetene
				
				for n in nytt:
					s.extend(n)
					
				#Så er det badetemperaturene - kan bli laaaaange
				if 'bath' in visningsvalg:
					s.extend(hentBadetemperaturer(d,kanal,hovedkanal))
				
				if verbose:
					print kanal
					for i in s:
						print i
						print '-' * 128
				if verbose:print kanal,datatype
				#Dabnavn
				c = d.cursor()
				
				sql = """SELECT dabNavn FROM kanal WHERE NAVN=%s;"""
				
				c.execute(sql,(kanal,))
				try:
					kanal_dab =  c.fetchone()[0]
				except:
					kanal_dab = kanal
				c.close()

				if testModus:
					print "Sendte ingenting inn"
					print s
					continue	
				#Vi setter inn ekstra linje med tekst
				#if kanal in ['an']:
				#	s.append('Søk etter kanaler på nytt for å få hele NRKs DAB-tilbud')
	
				#Vi kan ikke sende en tom liste
				if not s:
					s=['.']	
				#Send data til DAB
				multiplex = blokk
				if verbose:print "MULTIPLEX", multiplex
				#multiplex = 'ALL' # Dette kan difrensieres etterhvert
				start = sendTilDab.dabdato(time.time()) #DVS vi sender en liste som gjelder fra nå
				#Dersom vi har iteminfo er levetiden på listen lik den gjenværende tiden på det korteste innslaget
				if distriktssending:
					levetid = minimumLevetid(d,kanal)
				else:
					levetid = minimumLevetid(d,hovedkanal)
				if levetid <=0:
					#Vi har ingen ok tidsangivelse
					levetid = 60 * 60 * maxLevetid #dvs i hele timer regnet om til sekunder
				
				stop = sendTilDab.dabdato(time.time() + levetid + 5 )  #5 sekunder ofset slik at infoen heller henger enn forsvinner like før en oppdatering
				if len(sk) == 1 and levetid < 70:
					#Vi legger ut en flashmelding
					kommando = "SendDataDLS;%s;%s;%s;%s;%s;%s" % (
						multiplex,
						kanal_dab,
						1, #listetype Single=0,Loop=1,Background loop=2
						start,
						stop,
						30 # visningstider
					)
 
					sendTilDab.sendData(
						'http://160.68.105.26:8888/api',
						 #'http://localhost/cgi-bin/mimetest.py',
						 kommando = kommando,
						liste = sk
						)




				#Lag en kommaseparert liste over visningstider
				visningstider = ','.join(map(lagVisningstider,s))
				if visningstider == '':
					visningstider = '10'	
				#Lag kommando
				
				
				kommando = "SendDataDLS;%s;%s;%s;%s;%s;%s" % (
					multiplex,
					kanal_dab,
					listetype,#listetype Single=0,Loop=1,Background loop=2
					start,
					stop,
					visningstider 
					)
					
				if verbose:print kommando
				
				
				svar = sendTilDab.sendData(
				'http://160.68.105.26:8888/api',
				#'http://localhost/cgi-bin/mimetest.py',
				kommando = kommando,
				liste = s
				)['msg']
				
				#print svar
				
				svar2 = lagTestWeb.sendData(kanal,
				liste = s,
				blokk = blokk,
				svar = svar
				)
				if verbose:print svar2
		
	#Lukke databasen
	
	d.close()
	
	
if __name__=='__main__':
	tilDab(kanal='p3',datatype='iteminfo')
	
