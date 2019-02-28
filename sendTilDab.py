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

def dabdato(ticks,format = 'datetime'):


	YY,MM,DD,H,M,S,WD,YD,DST = time.localtime(ticks)
	if format == 'datetime':
		return "%02d.%02d.%02d %02d:%02d:%02d" % (DD,MM,YY%100,H,M,S)
	elif format == 'date':
		return "%02d.%02d.%02d" % (DD,MM,YY%100)
	else:
		return "%02d:%02d:%02d" % (H,M,S)

def sendData(uri, kommando = None, feltListe = {}, liste = [], data_enc = None, mimetype = 'Content-Type: dab/datadls', forceUnicode = True):
	"""Sender en liste av data"""
	ret_svar = {}

	ret_svar['status']='0'
	ret_svar['reason']='Starter utsendelse'



	#Sett opp headers
	boundary = '-' * 20 + '%s%s_%s' % ('G', int(time.time()), randint(1,10000))
   	headers = {"content-type": 'multipart/form-data; boundary=%s' % boundary,
		"Accept": "*/*",
		"User-Agent":"Gluon 0.3.1 [no] (%s; U)"%sys.platform}



	#Så lager vi mimedataene
	data = ''
	nl = chr(13) + chr(10)
	#nl = "\n"
	#Først legger vi inn kommandoen
	if kommando:
		data += "--" + boundary + nl
		data += 'Content-Disposition: form-data; name="Command 1"%s' % (nl)
		data += 'Content-Length: %s%s' % (len(kommando),nl)
		data += 'Content-Type: dab/command' + nl
		data += nl
		data += kommando
		data += nl

	for key in feltListe:

		if type(feltListe[key])!=type([]):
			data += "--" + boundary + nl
			data += 'Content-Disposition: form-data; name="%s"%s' % (key,nl)
			data += 'Content-Length: %s%s' % (len(feltListe[key]),nl)
			data += mimetype + nl
			data += nl
			data += feltListe[key]
			data += nl
		else:

			c=0
			for felt in feltListe[key]:
				if forceUnicode:
					try:
						fu = unicode(felt,'iso-8859-1')
					except:
						fu = felt
					felt = fu.encode('utf-8')
				c+=1
				data += "--" + boundary + nl
				data += 'Content-Disposition: form-data; name="item%s"%s' % (c,nl)
				data += 'Content-Length: %s%s' % (len(felt),nl)
				data += 'Content-Type: dab/datadls' + nl
				data += nl
				data += felt
				data += nl
	if liste:
		#Dette er en typisk liste over parametre etter en kommando
		c=0
		for item in liste:
			if len(item)>128:
				item = item[:128]
			if forceUnicode:
				try:
					fu = unicode(item,'iso-8859-1')
				except:
					fu = item
				item = fu.encode('utf-8')
			c+=1
			data += "--" + boundary + nl
			data += 'Content-Disposition: form-data; name="Contentfield %s"%s' % (c,nl)
			data += 'Content-Length: %s%s' % (len(item),nl)
			data += 'Content-Type: dab/datadls' + nl
			data += nl
			data += item
			data += nl


	#avslutte
	data +=  boundary + '--' + nl
	#print data

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
	#Sjekke om konfigurasjonen finnes, dvs at jeg ikke får noe feilmeldingtilbake
	if "NOK;Can" in ret_svar['msg']:
		#Dette gikk jo ikke - vente
		time.sleep(2)
		#sende igjen
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
	                ret_svar['msg'] = '*' + svar.read()
	                #ret_svar['duration'] = "PT%sS" % (time.time() - start)


	                conn.close()
	                utverdier['dab']= ret_svar


	return ret_svar





def main():

	print dabdato(time.time())
	#
	#Her bygger du selve kommandoen
	#
	kommando = "SendDataMOT;%s;%s;%s;%s;%s" % (
		'riks1',
		'dabpluss',
		1,#listetype Single=0,Loop=1,Background loop=2
		dabdato(time.time()),
		dabdato(time.time() + 60),
		)
	f = open('/Users/n12327/Desktop/test.jpg')
	dok = f.read()
	f.close()

	dok = {'File0"; filename="%s' % 'test1.jpg' : dok}

	print sendData(
		'http://160.68.105.26:8888/api',
		kommando,
		feltListe = dok,
		mimetype = 'Content-Type: dab/mot'
		)


	"""
	print sendData(
		'http://nrk29084.intern.nrk.no/scripts/DabApi.dll/upload',
		 feltListe = testliste, data_enc = None )['msg']
	"""

	pass

if __name__ == '__main__':

	alfa= main()
	print alfa





