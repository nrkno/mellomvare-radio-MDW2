#! /usr/local/bin/python
# -*- coding: iso-8859-1 -*-

"""POST mottak for xml dokumenter"""
#! /usr/local/bin/python

#TODO:

#Lage grensesnitt for oppdateringer, dvs. at en GET til dette skriptet (ALT != POST) starter utspillings enhetene i oppdateringsmodus.

##Status er 0 for ikke prossesert, 1 for oppdatert info,  2 for ny, 3 for "force breaking"?

import time
now = time.time()
from os import environ
from cgi import parse_qs
from sys import stdin, exc_info
import gluonspin
import traceback

dumpFolder = '/var/www/html/metamorfose/'

verbose = False
testFil = False

quark = "mmt"

allow = ['10.0.1.17','*'] # Egentlig karuselladressene, eller *

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

	
def main(dok):
	#Lage filnavn
	filnavn = "morf%s:xml" % time.time()
	filnavn = filnavn.replace('.','_').replace(':','.')
	f = open(dumpFolder + filnavn, 'w')
	f.write(dok)
	f.close()
	totalStatusOK = True
	if totalStatusOK:
		#Vi skal returnere OK
		return OK(quark)
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

	
