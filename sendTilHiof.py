#! /usr/local/bin/python
# -*- coding: iso-8859-1 -*-

#Hjelpemodul for å sende ting inn i dab systemet

import time
from httplib import HTTPConnection
import os, sys, traceback
import httplib
from random import randint


utverdier={}
testliste = {'multiplex':'Nasjonal',
			'kanal':'p9',
			'listetype':'1',
			'start':'12.03.03 12:43:05',
			'stopp':'12.03.03 17:43:05',
			'varighet':'10',
			'tekster':['et felt','felt to']}

FileUploadRequestException="Dette gikk ikke :"
#Gjør til klasse

def isodato(ticks,format = 'datetime'):
	

	YY,MM,DD,H,M,S,WD,YD,DST = time.localtime(ticks)
	if format == 'datetime':
		return "%04d-%02d-%02dT%02d:%02d:%02d" % (YY,MM,DD,H,M,S)
	elif format == 'date':
		return "%02d.%02d.%02d" % (DD,MM,YY%100)
	else:
		return "%02d:%02d:%02d" % (H,M,S)

def sendData(uri, kanal = 'kanal', blokk = 'blokk', start = None, stop = None, liste = [],  forceUnicode = True):	
	"""Sender en liste av data"""
	ret_svar = {}
		
	ret_svar['status']='0'
	ret_svar['reason']='Starter utsendelse'
	
	
	
	#Sett opp headers
	headers = {"Content-type": "application/xml",
			"Accept": "*/*",
			"User-Agent":"Gluon 0.5.0 [no] (%s; U)"%sys.platform}
		
	
	#Vi lager listen
	xmlListe = ''
	for rad in liste:
		xmlListe += '  <rad data="%s" visningstid="%s" />\n' % rad
		
	#Så lager vi XML dataene
	xmlMal = """<?xml version="1.0" encoding="iso-8859-1"?>
<dls kanal="%s" blokk="%s" start="%s" stop="%s">
%s</dls>
	"""
	
	data = xmlMal % (
	
					kanal,
					blokk,
					start,
					stop,
					xmlListe
					)
		
	#Dele opp uri til hostname og url
	host,url = uri[7:].split('/',1)
	try:
		conn = HTTPConnection(host)
		conn.request("POST", '/' + url,data, headers)
		
		ret_svar['reason'] = 'Sendt data - transmitter svarer ikke.'
		time.sleep(0.005)
	except 0:
		#Legge inn forskjellige verdier her
		ret_svar['reason'] = 'Kunne ikke lage forbindelse'
	else:
		
		svar = conn.getresponse()
		ret_svar['status'] = svar.status
		ret_svar['reason'] = svar.reason
		ret_svar['msg'] = svar.read()
		#ret_svar['duration'] = "PT%sS" % (time.time() - start)
			
		
		conn.close()
		utverdier['dab']= ret_svar
 
	
	return ret_svar

	
def main():

	print dabdato(time.time())
	
	return
	
	print sendData(
		'http://160.68.105.26:8888/api',
		kommando = "SendDataDLS;",
		 feltListe = testliste, data_enc = None )
	"""
	print sendData(
		'http://nrk29084.intern.nrk.no/scripts/DabApi.dll/upload',
		 feltListe = testliste, data_enc = None )['msg']
	"""
	
	pass
	
if __name__ == '__main__':
	
	alfa= sendData('http://test.nrk.no/test.py', liste=[u'et felt','felt to'])
	print alfa						
	

    
    

