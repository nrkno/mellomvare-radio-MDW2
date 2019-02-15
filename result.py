#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-

#Denne settes på server
#! /usr/bin/python
"""Resultat tjenester"""
#Lage egen køordner for breaking news
#Listene skal oppdateres uansett, dls.py kaster nytt item i breaking køen (egen rutine)
#Forenkle databehandlingen hvis nødvendig

#TODO:
#Lage støtte for stryking av kamper ved status=0 ***

#Når det blir 1-0 kan jeg ikke bruke termen lagt på til


import xml.dom.minidom
from gluoncommons import finnVerdi
import MySQLdb as mdb
import time
from dbConn import database
ligaer = ['l1','#l49','#*'] # Alle arrID'er som ikke er i listen blir ignorert

hockeyterm = {
		'owngoal':u'selvmål',
		'og':u'sm.',
		'penalty':u'straffe',
		'pen':u'str',
		'goal':u'mål',
		'corner':None,
		'cor':None,
		'attempt':u'målsjanse',
		'att':u'målsj.',
		'round':u'periode',
		'punTerm':u'Utvisninger:',
		'pun1':u'2 min.',
		'pun2':u'5 min.',
		'pun3':u'10 min.',
		'p1':u'2 min.',
		'p2':u'5 min.',
		'p3':u'10 min.',
		'refFormat':'\"%s%s%s %s\" % (merkelapp,maaltid,variant,hvem)',
		'render':['goal','punishment']
		}



fotballterm = {
		'owngoal':u'selvmål',
		'og':u's.m.',
		'penalty':u'straffe',
		'pen':u'str',
		'goal':u'mål',
		'corner':u'hjørnespark',
		'cor':'hj.sp.',
		'attempt':u'målsjanse',
		'att':u'målsj.',
		'round':u'omgang',
		'punTerm':u'Kort:',
		'pun1':u'Gult k.',
		'pun2':u'Rødt k.',
		'pun3':u'Rødt k.',
		'p1':u'GK:',
		'p2':u'RK:',
		'p3':u'RK:',
		'refFormat':'\"%s%s%s %s\" % (merkelapp,hvem,maaltid,variant)',
		'render':['goal','punishment']
		}

#def database(host = "160.68.118.48", user="tormodv", database="dab",passord="allmc21"):
#def database(host = "localhost", user="tormodv", database="dab",passord=""):
#	d = mdb.connect(user=user,passwd=passord, host=host)
#	d.select_db(database)
#	return d
	


def lagStilling(
		event,
		kampen,
		status=0,
		periode=0, 
		referat=0, 
		refStilling=0, 
		refTidsmerke=0,
		assist=0,
		sekund=0,
		periodeHeding=0,
		periodelengde=0,
		term=None,
		kompaktFormat=1,
		bredde=40,
		kolonneskille = 18,
		ikkeGult = 1,
		kortreferat = 1
		
		):
		
	#Denne kan forenkles betraktelig
	
	#Finne forkortelser for hjemme og bortelag
	sisteHendelse = ''
	hjemme = kampen['hjemmelag']
	borte = kampen['bortelag']
	if kampen.has_key('hlag'):
		h=kampen['hlag']
	else:
		h=hjemme[:1]
	if kampen.has_key('blag'):
		b=kampen['blag']
	else:
		b=borte[:1]
	if h==b:
		h=(hjemme[:1]+hjemme[-1:]).upper()
		b=(borte[:1]+borte[-1:]).upper()
		
	#print h, b
	#*** Sjekke om results er bra nok
	
	hjTot = finnVerdi(event, 'teams/home/@goals')
	boTot = finnVerdi(event, 'teams/away/@goals')
	
	
	
				
	if periode:
		if status==1:
			ongToken='...'
		else:
			ongToken=')'
			
		stilling = "%s-%s (%s%s" % (hjTot,boTot,stilling[:-2],ongToken)
	else:
		
		if status==1:
			ongToken='*'
		elif status==2:
			ongToken='p'
		else:
			ongToken=''
		if kompaktFormat==2:
			ongToken=''
			
		#print ongToken
		
		stilling = "%s-%s%s" % (hjTot,boTot,ongToken)
		
	#Lage en liste av to lister for TTV
	
	if status==2:
		sisteHendelse = 'Pauseresultat: %s mot %s, %s' % (hjemme,borte,stilling)
	if status==3:
		sisteHendelse = 'Sluttresultat: %s mot %s, %s' % (hjemme,borte,stilling)
	#Lage resultatstrengen
	resultat = '%s-%s, %s' % (hjemme,borte,stilling)
	
	
	
	
	return {
			'resultat':resultat,
			'hjemmepoeng':hjTot,
			'bortepoeng':boTot,
			'stilling':stilling,
			'referat':'',
			'noeNyttForTTV':'',
			'sisteNytt':sisteHendelse
			}
	

def lagHead(event,id):
	
	s={}
	s['resultatID']=id
	#dette for å merke resultatiden i selve kampobjektet.
	
	## Hovedoverskrift
	s['arrangement'] = finnVerdi(event,'metadata/arrangement/@name')
	
	#Gruppe, sesong og kampbetegnelse
	s['gruppe'] = ''
	s['sessong'] = finnVerdi(event,'metadata/arrangement/@season')
		
	s['kamp'] = finnVerdi(event,'metadata/round/@name')
		
	## Stadion og dato
	
	s['sted'] = finnVerdi(event,'metadata/location/@name')
	
		
	#Tiden i sekunder slik at det er lett ' sammenligne om kampen er i dag eller ig'r....
	
	s['epocTid'] = finnVerdi(event, 'metadata/@start')
	
	###########################################
	## Hente hjemme og bortelag
	
	
	
	s['hjemmelag'] =  finnVerdi(event,'teams/home/@name')
	s['hlag'] = finnVerdi(event,'teams/home/@short')
	s['bortelag'] =  finnVerdi(event,'teams/away/@name')
	s['blag'] = finnVerdi(event,'teams/away/@short')
	

	
	## Hente ut arrID en
	s['arrID'] = finnVerdi(event,'metadata/arrangement/@id')
	
	return s
	


def parser(dok):
	"""Lager korte meldinger fra scoringer, samt lager en liste over siste "tipperunde".
Skal også kunne ta imot sidevisninger fra arena."""
	pars = xml.dom.minidom.parseString(dok)
	
	
	#Dele opp treet i grener:
	
	kropp = pars.getElementsByTagName('event')[0]
	#vedlikehold = pars.getElementsByTagName('maintenance')
	
	if kropp:

		priority =int( pars.getElementsByTagName('gluon')[0].getAttribute('priority'))
		metadata = kropp.getElementsByTagName('metadata')[0]
		status = int(finnVerdi(metadata, 'status/@id'))
		sport = finnVerdi(metadata, 'sport/@name')
		resultatID = finnVerdi(kropp, '@id')
		
		
		if sport == "soccer":
			term = fotballterm
		elif sport == "icehockey":
			term = hockeyterm
		kampen = lagHead(kropp,resultatID)
		#print kampen
		res= lagStilling(
				kropp,
				kampen,
				status=status, 
				periode=0, 
				referat=1, 
				assist=0, 
				sekund=0,
				refStilling=1,
				refTidsmerke=1,
				periodelengde=45,
				term=term,
				kompaktFormat=1,
				periodeHeding=0
				
				)
		#print res	
			
		#Skal denne ligaen taes vare på?
		if not (kampen['arrID'] in ligaer or '*' in ligaer):
			print 555555 #
			return {'status':0, 'kanal':'alle', 'datatype':'result'}
		#Lage databasetilkobling
		d=database()
		#Oppdatere databasen
		c= d.cursor()
		#*** Lage en oppryddningsrutine her
		
		if priority==0:
			sql = """DELETE FROM result 
				WHERE id=%s;"""
			c.execute(sql,(resultatID,)) 
			gluonStatus = 1
		else:
		
		
			#Sjekke om kampideen finnes fra før
			sql = """SELECT id FROM result 
				WHERE id=%s;"""
			c.execute(sql,(resultatID,)) 
			
			if c.rowcount== 1:
				gluonStatus = 1
				
				sql = """UPDATE result SET 
					id=%s,
					start=%s,
					oppdatert=%s,
					hendelse=%s,
					resultat=%s,
					fremvist=%s,
					hjemme_P=%s,
					borte_P=%s,
					h_lag=%s,
					b_lag=%s,
					status=%s
					WHERE id=%s;""" 
				
				c.execute(sql,(
					resultatID,
					kampen['epocTid'],
					mdb.TimestampFromTicks(time.time()),
					res['sisteNytt'].encode('latin-1'),
					res['resultat'].encode('latin-1'),
					"N",
					res['hjemmepoeng'],
					res['bortepoeng'],
					kampen['hlag'],
					kampen['blag'],
					status,
					resultatID
					)
				) 
			else:
				#Det er ingen felter som er oppdatert
				
				gluonStatus = 2
				sql = """INSERT INTO result(id,start, oppdatert,hendelse,resultat,fremvist,hjemme_P,borte_P,h_lag,b_lag,status) VALUES 
				(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
				""" 
				c.execute(sql,(
					resultatID,
					kampen['epocTid'],
					mdb.TimestampFromTicks(time.time()),
					res['sisteNytt'].encode('latin-1'),
					res['resultat'].encode('latin-1'),
					"N",
					res['hjemmepoeng'],
					res['bortepoeng'],
					kampen['hlag'],
					kampen['blag'],
					status
					)
				) 
		c.close()
		
		
			
		
	#print "RESULT PARSER"
	#Status er 0 for ikke prossesert, 1 for oppdatert info,  2 for ny, 3 for "force breaking"?
	return {'status':gluonStatus, 'kanal':'alle', 'datatype':'result'}


if __name__=='__main__':
	f = open('fopp.xml')
	dok = f.read()
	f.close()
	print parser(dok)
	