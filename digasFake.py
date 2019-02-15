#! /usr/local/bin/python
# -*- coding: iso-8859-1 -*-

"""Tilrettelegger modul for DAB og nettradio - versjon med tråder for hver av utkanalene"""
#! /usr/local/bin/python

#TODO:

#Lage grensesnitt for oppdateringer, dvs. at en GET til dette skriptet (ALT != POST) starter utspillings enhetene i oppdateringsmodus.

##Status er 0 for ikke prossesert, 1 for oppdatert info,  2 for ny, 3 for "force breaking"?

import time
now = time.time()
from os import environ
from cgi import parse_qs
from sys import stdin, exc_info
from threading import Thread
from Queue import Queue
import gluonspin
import traceback

# Importer parsermoduler

import digasFakeLib




verbose = False
testFil = False
traader = True #Kjører hver av utspillingsmodulene i tråder
maxVent = 60 #Maks ventetid på utspillingsmodulene
quark = "digasFake"

#print "Importtid:",time.time()-now

allow = ['10.0.1.17','*'] # Egentlig karuselladressene, eller *

parsere = {
	
	'/gluon/body/tables/@type=epg':'digasFakeLib.parser(dok)',
		}

utenheter = {
	}
	

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

def startUtspiller( innstikkNavn = None, innstikkType=None, parametre = {}, returMeldinger = None):
	"Enhet som startes som en tråd og som laster riktig utspillingsenhet"
	
	#Setter riktige variabler for eval funksjonen
	kanal=parametre['kanal']
	datatype =parametre['datatype']
	if 'id' in parametre:
		id = parametre['id']
	else:
		id = ''
	try:
		msg = eval(innstikkType)
		if not msg:
			msg=''
		returMeldinger.put({'innstikkNavn':innstikkNavn, 'status':'ok','msg':msg})
	except:
		type, val, tb = exc_info()
		msg = "".join(traceback.format_exception(type, val, tb))
		returMeldinger.put({'innstikkNavn':innstikkNavn, 'status':'error','msg':msg})
	
def main(dok):
	#Hvis det ikke er noe dok her er det ønsket en oppdatering
	s=[]
	p=[]
	#Finne riktig parser til dokumentet
	if dok:
		for krav in parsere:
			iBane = gluonspin.gluonPath(krav)
			gluonspin.parseString(dok,iBane)
			if iBane.pathInXml:
				p.append(parsere[krav])
				s.append(eval(parsere[krav]))
				#Siden vi aldri får match på mer en en type kan vi avbryte nå
				break

	else:
		#Lager proforma liste for å oppdatere alle
		s=[{'status':1,'kanal':'alle','datatype':'iteminfo'}]
	#Start utspillingstjeneste
	
	if verbose:print "Start utspilling:",time.time()-now
	#Innstikkstyper for hver av tjenestetypene i dab, dls, mot o.l.
	
	#Sjekke hva som er oppdatert
	s2 = []
	trd = []
	meldinger = Queue()
	warnings = []
	for i in s:
		if not i['status']:
			if verbose:print "IGNORERES"
			continue
		kanal=i['kanal']
		datatype =i['datatype']
		if 'id' in i:
			id = i['id']
		else:
			id = ''
		
		
		for ut in utenheter:
			if traader:
				t = Thread(target=startUtspiller,
						kwargs = {'innstikkNavn':ut, 'innstikkType':utenheter[ut], 'parametre':i, 'returMeldinger': meldinger}
						)
				t.setName(ut)
				t.setDaemon(1) 
				t.start()
				trd.append(t)
			else:
				s2.append(eval(utenheter[ut]))
				
			if verbose:print "UTg:",ut,time.time()-now
		#Samle trådene
		nu=time.time()
		warnings = ['Warnings:']
		for t in trd:
			vent = maxVent - (time.time() -nu)
			t.join(vent)
			if t.isAlive():
				warnings.append("%s brukte mer en %s sekunder" % (t.getName(), maxVent))
			
	
	#Dersom noe trenger opprydningsrutiner legges disse inn her etter alle utspillingsmodulene
	if dok:
		#Venter bare ved dok
		time.sleep(20)
	for n,i in enumerate(p):
		if verbose:print n,i
		if '.' in i:
			modul = i.split('.')[0]
			if 'opprensk' in dir(eval(modul)):
				#kall riktig modul, med resultatet fra parsingen
				eval(modul+'.opprensk(s[n])')
				if verbose:print 'VI RYDDER'
	#Vi sjekker trådene enda en gang og lager en sluttrapport
	for t in trd:
		t.join(0.1)
		if t.isAlive():
			warnings.append("%s ble tvunget ned etter %s sekunder" % (t.getName(), maxVent))
	#Sjekke meldingene
	totalStatusOK = True
	totalMelding = []
	while not meldinger.empty():
		melding = meldinger.get()
		if melding['status']=='error':
			totalStatusOK = False
		totalMelding.append("\n%(innstikkNavn)s\n%(status)s\n%(msg)s" % melding)
	#Legge til Warnings
	if len(warnings)>1:
		#Vi skal legge til warningsene
		totalMelding.extend(warnings)
	if totalStatusOK:
		#Vi skal returnere OK
		return OK(quark,melding="\n".join(totalMelding))
	else:
		#Vi fyrer feilmelding
		return error('dab11',quark,melding="\n".join(totalMelding))

	


if (__name__=='__main__'):
		#Dette skal vaere et cgi skript
				
		print "Content-type: text/html"
		print
		
		#print environ
		
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
					#print "Oppdaterer"
					lengde = 0
					xmldokument = ''
					if testFil:
						f=open("item.xml")
						
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
				print error("dab10",quark, melding=msg)
	
	

			else:
				#Alfa kan enten være en OK eller en feilmelding som er håndtert av systemet
				
				print alfa

	
