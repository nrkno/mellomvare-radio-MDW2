#! /usr/bin/python
# -*- coding: iso-8859-1 -*-


# TODO:

import xml.sax
from xml.sax import parseString
from threading import Lock, Thread
from urllib import urlencode
from httplib import HTTPConnection
from cPickle import load
import time
import sys

opt_ut = Lock()


maxReqursivLevel = 4

server = 'vmalxdab02'
#server = 'mamcmac12'




def sendData(uri, method="POST", data_raw = None, data_enc = None, svar_fra_mottager = 1,tag='karusell', reqursivLevel = 1, multipefaktor = 1):
	"""Sender gluoner til de forskjellige transmitterne.
	Denne brukes av trådmodulen og blir kjørt en gang pr. transmitter"""
	ret_svar = {}
	utverdier={}
	#Lager midlertidig svar som ev. oversktives senere
	#Lock og skriv
	
	ret_svar['status']='0'
	ret_svar['reason']='Starter utsendelse'
	
	
	utverdier[tag] = ret_svar
	#start = time.time()
	#Sett opp headers
	if data_raw:
		headers = {"Content-type": "application/xml",
			"Accept": "*/*",
			"User-Agent":"Gluon 0.5.0 [no] (%s; U)"%sys.platform}
		data = data_raw
	else:
		headers = {"Content-type": "application/x-www-form-urlencoded",
			"Accept": "*/*",
			"User-Agent":"Gluon 0.5.0 [no] (%s; U)"%sys.platform}
		data = data_enc
	#Dele opp uri til hostname og url
	host,url = uri[7:].split('/',1)
	start = time.time()
	try:
		conn = HTTPConnection(host)
		conn.request(method, '/' + url,data, headers)
		
		ret_svar['status']='3'
		ret_svar['reason'] = 'Sendt data - transmitter svarer ikke. Ting er sansynlighvis OK'
		#Dette skyldes som regel en treg mottaker og er ikke nødvendighvis en feil
		time.sleep(0.003)
	except:
		#Legge inn forskjellige verdier her
		#Ev. legge inn rutine for automatisk forsøk igjen
		ret_svar['status']='1'
		ret_svar['reason'] = 'Kunne ikke lage forbindelse'
	else:
		if svar_fra_mottager:
			svar = conn.getresponse()
			#print dir(svar)
			ret_svar['status'] = svar.status
			ret_svar['reason'] = svar.reason
			if method == 'HEAD':
				ret_svar['msg'] = ''
			else:
				ret_svar['msg'] = svar.read()
			ret_svar['duration'] = "PT%sS" % (time.time() - start)
			
		else:
			tid = time.time() - start
			ret_svar['msg']='TID: %s HVEM: %s' % (tid,tag)
		conn.close()
	#Sjekk om vi har en 302
	if ret_svar['status']==302:
		#Vi sender videre i denne omgang
		if reqursivLevel<maxReqursivLevel:
			nyUrl = svar.getheader('Location')
			nytransmitter = tag + ":redirekt_%s" % reqursivLevel
			sendData(nyUrl, 
			data_raw = data_raw, 
			svar_fra_mottager = svar_fra_mottager,
			tag=nytransmitter,
			reqursivLevel = reqursivLevel + 1)
		#ret_svar['msg'] = nyUrl
	#Lock og skriv
	
	utverdier[tag]= ret_svar
	return utverdier
	
def sendData2(uri, method="POST", data_raw = None, data_enc = None, svar_fra_mottager = 1,tag='karusell', reqursivLevel = 1, multipefaktor = 1):
	"""Sender gluoner til de forskjellige transmitterne. Plagemodus
	Denne brukes av trådmodulen og blir kjørt en gang pr. transmitter"""
	ret_svar = {}
	utverdier={}
	#Lager midlertidig svar som ev. oversktives senere
	#Lock og skriv
	
	ret_svar['status']='0'
	ret_svar['reason']='Starter utsendelse'
	
	
	utverdier[tag] = ret_svar
	#start = time.time()
	#Sett opp headers
	if data_raw:
		headers = {"Content-type": "application/xml",
			"Accept": "*/*",
			"User-Agent":"Gluon 0.5.0 [no] (%s; U)"%sys.platform}
		data = data_raw
	else:
		headers = {"Content-type": "application/x-www-form-urlencoded",
			"Accept": "*/*",
			"User-Agent":"Gluon 0.5.0 [no] (%s; U)"%sys.platform}
		data = data_enc
	#Dele opp uri til hostname og url
	host,url = uri[7:].split('/',1)
	start = time.time()
	try:
		conn = HTTPConnection(host)
		conn.request(method, '/' + url,data, headers)
		
		ret_svar['status']='3'
		ret_svar['reason'] = 'Sendt data - transmitter svarer ikke. Ting er sansynlighvis OK'
		#Dette skyldes som regel en treg mottaker og er ikke nødvendighvis en feil
		time.sleep(0.003)
	except:
		#Legge inn forskjellige verdier her
		#Ev. legge inn rutine for automatisk forsøk igjen
		ret_svar['status']='1'
		ret_svar['reason'] = 'Kunne ikke lage forbindelse'
	else:
		if svar_fra_mottager:
			svar = conn.getresponse()
			#print dir(svar)
			ret_svar['status'] = svar.status
			ret_svar['reason'] = svar.reason
			if method == 'HEAD':
				ret_svar['msg'] = ''
			else:
				ret_svar['msg'] = svar.read()
			ret_svar['duration'] = "PT%sS" % (time.time() - start)
			
		else:
			tid = time.time() - start
			ret_svar['msg']='TID: %s HVEM: %s' % (tid,tag)
		conn.close()
	#Sjekk om vi har en 302
	if ret_svar['status']==302:
		#Vi sender videre i denne omgang
		if reqursivLevel<maxReqursivLevel:
			nyUrl = svar.getheader('Location')
			nytransmitter = tag + ":redirekt_%s" % reqursivLevel
			sendData(nyUrl, 
			data_raw = data_raw, 
			svar_fra_mottager = svar_fra_mottager,
			tag=nytransmitter,
			reqursivLevel = reqursivLevel + 1)
		#ret_svar['msg'] = nyUrl
	#Lock og skriv
	
	utverdier[tag]= ret_svar
	return utverdier


def main():
	#enMeg = "*" * (1024*1024)
	#dataLyd=enMeg*100	#
	"""
	f=open('23412.jpg')
	dataBilde1 = f.read()
	f.close()
	
	f=open('35782.jpg')
	dataBilde2 = f.read()
	f.close()
	
	f=open('1087.pdf')
	dataPdf = f.read()
	f.close()
	
	#dataBilde1='#'*50000
	#dataBilde2='$'*4000
	
	print 'Sjekker bildefil1'
	rapport = sendData('http://%s/DMAnyserver/1003888.jpg' % server, method="HEAD")['karusell']
	print 'STATUS:  ', rapport['status'],  rapport['reason']
	print 'MELDING: ' , rapport['msg']
	print 'TID:     ' , rapport['duration']
	
	#time.sleep(1)

	
	print 'Sender bildefil1'
	rapport = sendData('http://%s/DMAnyserver/1003888.jpg' % server, method="PUT", data_raw = dataBilde1)['karusell']
	print 'STATUS:  ', rapport['status'],  rapport['reason']
	print 'MELDING: ' , rapport['msg']
	print 'TID:     ' , rapport['duration']
	
	#time.sleep(1)
"""
	
	#Sende xml
	f=open('item.xml')
	#f=open('nDMA_529337070_18_01_2010_14_38.xml')
	#f=open('ndma_fa5bfec35fff12d2-c603600187d81ad0.xml')#Samletest
	dok = f.read()
	f.close()
	print "Sender metadata:"
	rapport = sendData('http://%s/cgi-bin/dab.py' % server, method="POST", data_raw = dok)['karusell']
	print 'STATUS:  ', rapport['status'],  rapport['reason']
	print 'MELDING: ' , rapport['msg']
	print 'TID:     ' , rapport['duration']
	"""
	#time.sleep(1)
	f=open('testfil44.wav')
	lyd = f.read()
	f.close()
	print 'Sender lydfil'
	rapport = sendData('http://%s/DMAnyserver/1003933.wav' % server, method="PUT", data_raw = lyd, multipefaktor = 1)['karusell']
	print 'STATUS:  ', rapport['status'],  rapport['reason']
	print 'MELDING: ' , rapport['msg']
	print 'TID:     ' , rapport['duration']
	
	#time.sleep(15)
	
	
	print 'Sender bildefil2'
	rapport = sendData('http://%s/DMAnyserver/1003887.jpg' % server, method="PUT", data_raw = dataBilde2)['karusell']
	print 'STATUS:  ', rapport['status'],  rapport['reason']
	print 'MELDING: ' , rapport['msg']
	print 'TID:     ' , rapport['duration']
	
	print 'Sender pdf'
	rapport = sendData('http://%s/DMAnyserver/1087.pdf' % server, method="PUT", data_raw = dataPdf)['karusell']
	print 'STATUS:  ', rapport['status'],  rapport['reason']
	print 'MELDING: ' , rapport['msg']
	print 'TID:     ' , rapport['duration']
	
"""

if __name__=="__main__":

	main()
	print "Syntax OK"
