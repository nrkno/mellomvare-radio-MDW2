#! /usr/local/bin/python
# -*- coding: iso-8859-1 -*-

"""Værfilter for NRK Rogaland"""

# TODO:
# Sjekke hva slags rappport type vi har med å gjøre for å avgjøre hvilke rapporter vi har
#Metoden nå blir bare feil

#Bruke crlf i filene


#import cgitb; cgitb.enable(display=0, logdir="/log/")
import xml.sax
from xml.sax import parseString
from os import environ, remove, listdir, rename

from sys import argv, stdin, exc_info
import traceback
import time
import sys
import urllib
import copy

verbose =True
relativeReport = 'relativ faktisk' #Relativ og eller faktisk rapport (filnavn)

path = '/Users/tormodv/Documents/NRK Utvikling/Prosjekter/Rogalandveir/applikasjon/'
path = '/var/www/html/rogaland/'

crlf = chr(10) + chr(13)
crlf = chr(13) + chr(10)
allow = ['*']
quark = 'rogalandVeir'

utverdier = {}


steder = ['31','149','150','58','66','140','204','206','176','401','402','403','404','405','406','407','408','409','410','411','412',
			'413','414','415','416','417','418','419','420','421','143','191']
	
#steder = ['58','204','66','31','143']
	
def finnDagerFram(dateIssued,startDate):
	#Trunker datoene til midnatt
	issued =  time.mktime ((int(dateIssued[0:4]),int(dateIssued[5:7]), int(dateIssued[8:10]),0,0,0,-1,-1,-1))
	start = time.mktime ((int(startDate[0:4]),int(startDate[5:7]), int(startDate[8:10]),0,0,0,-1,-1,-1))
	return int((start-issued)/(24*3600))

class gluonspinError(Exception):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)
	
	pass
	
class veirParser(xml.sax.handler.ContentHandler):
	"""Parser digas XML og oppdaterer databasen tilsvarende"""
	
	def __init__(self, modus):
		
		self.utDokVarsel = u''
		self.utDok = ''
		self.inLocation = False
		self.getName = False
		self.modus = modus
		self.inPeriod = False
		self.getDate = False
		self.dateIssued = ''
		self.reporttype = ''
		
		
		
		
	def startElement (self,name, attrs ):
		#print 1,name
		if name == 'date_issued':
			self.getDate = True
		if name == 'period':
			self.startDate = attrs['startDate']
			self.inPeriod = True
		if name == 'weather':
			if self.inPeriod:
				self.weatherObservations = [attrs['id'], attrs['symbol'], attrs['number'],  attrs['name']]
			else:
				self.reporttype = attrs['type']
				#Vi kan rotere filene når vi nå vet hva dette er
				if self.reporttype in ['forecast']:
					if self.modus == 'w':
						roterFiler(self.reporttype)
		#Alt om navn på sted
		elif name == 'location':
			self.locationID = attrs['dataid']
			self.inLocation = True
		if self.inLocation and name == 'name':
			self.getName = True
			
		#Varsler
		elif name == 'temperature':
			
			self.temperature = int(float(attrs['celcius']))
		elif name == 'windSpeed':
			self.windSpeed = [attrs['mps'],attrs['beaufort'],attrs['name']]
		elif name == 'windDirection':
			self.windDirection = [attrs['deg'],attrs['name']]
		elif name == 'symbol':
			self.symbol = [attrs['number'],attrs['name']]
		#Ting som er i observasjonsfilene
		elif name == 'cloudiness':
			self.cloudiness = [attrs['id'], attrs['eights'], attrs['percent']]
		

				
		
	def endElement(self,name ):
		"Vi oppdaterer en datalinje i dokumentet dersom vi går ut ifra en forecast"
		
		if name == 'forecast' and self.locationID in steder:
			self.utDokVarsel += "%s;%s;%s;%s;%s;%s%s" % (
							self.locationID,
							self.locationName,
							self.temperature,
							';'.join(self.windSpeed),
							';'.join(self.windDirection),
							';'.join(self.symbol),
							crlf
							)
			#For sikkerhets skyld nulle verdiene
			self.locationID = ''
			self.locationName = ''
			self.temperature = ''
			self.windSpeed = {}
			self.windDirection = {}
			self.symbol = {}
			
			
		if name == 'observation' and self.locationID in steder:
			self.utDokVarsel += "%s;%s;%s;%s;%s;%s%s" % (
							self.startDate,
							self.locationID,
							self.locationName,
							self.temperature,
							';'.join(self.cloudiness),
							';'.join(self.weatherObservations),
							crlf
							)
			#For sikkerhets skyld nulle verdiene
			self.startDate =''
			self.locationID =''
			self.locationName = ''
			self.temperature = ''
			self.cloudiness = {}
			self.weatherObservations = {}			

		if name == 'name':
			self.getName = False
		if name == 'location':
			self.inLocation = False
		if name == 'period' and self.reporttype == 'forecast':
			print self.modus
			self.inPeriod = False
			#Vi må lagre perioden i et eget dokument
			if 'faktisk' in relativeReport:
				#print "FAKTISK"
				filnavn = path + self.reporttype +'-'+ self.startDate[:13] + '.txt'
				if self.modus == 'w':
					roter2(filnavn)
				r=open(filnavn,self.modus)
				r.write(self.utDokVarsel.encode('iso-8859-1'))
				r.close()
				
				
			if 'relativ' in relativeReport:
				#print "RELATIV"
				dagerFram = finnDagerFram(self.dateIssued,self.startDate)
				if dagerFram == 0:
					prefix = 'idag'
				elif dagerFram == 1:
					prefix =  'imorgen'
				elif dagerFram >1:
					return
				
				filnavn = prefix + 'Klokka' + self.startDate[11:13]+ '.txt'
				if self.modus == 'w':
					roter2(filnavn)
				r=open(path + filnavn,self.modus)
				r.write(self.utDokVarsel.encode('iso-8859-1'))
				r.close()
				
			self.utDokVarsel = u''
			
			
	
			
	def characters (self,content ):
		if self.getName:
			self.locationName = content
		if self.getDate:
			self.getDate = False
			self.dateIssued = content
			
			
	def endDocument(self):
		"Hendelser på slutten av dokumentet"
		if self.reporttype == 'observation':
		
			
			#Lagre hele dokumentet
			filnavn='observasjonerIdag.txt'
			r=open(path + filnavn,'a')
			r.write(self.utDokVarsel.encode('iso-8859-1'))
			r.close()
			self.utDokVarsel = u''

			
		
		
	
def roterFiler(filtype):
	"Roterer filene, dvs skifter navn på dem"
	
	#Først stryker vi backup filene
	filer = listdir(path)
	for fil in filer:
		if "_bak" in fil and fil.startswith(filtype):
			remove(path + fil)
	#Navne om eksisterende
	filer = listdir(path)
	for fil in filer:	
		if ".txt" in fil and fil.startswith(filtype):
			deler = fil.split('.')
			nyfil = deler[0] + '_bak.' + deler[1]
			rename(path + fil, path + nyfil)
		
			
def roter2(fila):
	"Roterer fil"

	#F?rst stryker vi backup filene
	filer = listdir(path)
	for fil in filer:
		if "_bak" in fil and fil.startswith(fila.split('_')[0]):
			remove(path + fil)
	#Navne om eksisterende
	filer = listdir(path)
	for fil in filer:
		if ".txt" in fil and fil.startswith(fila):
			deler = fil.split('.')
			nyfil = deler[0] + '_bak.' + deler[1]
			rename(path + fil, path + nyfil)


					
def parser(xmlstreng, modus):
		
	s=[]
	
	
	veirData = veirParser(modus)
	try:
		parseString(xmlstreng, veirData)

	
	except xml.sax._exceptions.SAXParseException:
		#Dokumentet lar seg ikke parse
		s.extend(["""\t\t\t<error quark="%s">
		\t\t\t\t<errorMessage errorType="gl10"><message>%s sendte inn et dokument som ikke lot seg parse</message></errorMessage>
		\t\t\t</error>\n""" % (fra,fra)])
		return s,'0',fra #Artid settes til 0
	
	
	
	#print veirData.utDokVarsel.encode('iso-8859-1','replace')
	
	
			
def main(dok):
	if len(dok) < 1200000:
		#Kortdokument med hovedstedene
		#Vi finner ut hva slags filer dette er, observasjoner er små
		if len(dok)<200000:
			filtype = 'observation'
		else:
			filtype = 'forecast'
			
		modus = 'w'
	else:
		modus = 'a'
		
	
	parser(dok, modus)
	
	
			
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
					print "Ingen POST argumenter"
					lengde =0
					
					f=open("item.xml")
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
			
				
		
				print 'OK'

	
