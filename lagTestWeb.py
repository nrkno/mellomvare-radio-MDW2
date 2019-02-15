#! /usr/bin/python
# -*- coding: iso-8859-1 -*-

#Hjelpemodul for å sende ting inn i dab systemet

import time
from httplib import HTTPConnection
import os, sys, traceback
import httplib
from random import randint

webroot = "/Library/WebServer/Documents/dls/"
webroot = "/var/www/html/dls/"
logroot = "/data2/log/aktiv/"
logging = True

htmlHead="""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
    "http://www.w3.org/TR/html4/loose.dtd">
<html><head>
<title>DLS - Test</title>
<meta http-equiv="Content-type" content="text/html; charset=iso-8859-1">
</head>
<body bgcolor="#FFFFFF">"""

htmlEnd = """</body>
</html>"""


def dabdato(ticks,format = 'datetime'):
	

	YY,MM,DD,H,M,S,WD,YD,DST = time.localtime(ticks)
	if format == 'datetime':
		return "%02d.%02d.%02d %02d:%02d:%02d" % (DD,MM,YY%100,H,M,S)
	elif format == 'date':
		return "%02d.%02d.%02d" % (DD,MM,YY%100)
	else:
		return "%02d:%02d:%02d" % (H,M,S)
	
def sendData(kanal, liste = [] , listetype = 1, ren_Tekst = True, html = False, blokk = '', svar=''):
	"""Lager en fil med kanalnavn + html"""
	if html and blokk:
		fil = htmlHead
		fil += "<h1>Dls for : %s</h1>" % kanal
		for l in liste:
			fil += "<p>%s</p>" % l
		fil += htmlEnd
		if listetype ==1:
			f=open(webroot + kanal +".html","w")
		else:
			f=open(webroot + kanal +"_flash.html","w")
		f.write(fil)
		f.close()
	if ren_Tekst and listetype == 1:

		if blokk == '':
			mode = 'w'
		else:
			mode = 'a'
		f=open(webroot + kanal +".txt", mode)
		if mode == 'a':
			f.write("\n\n" + blokk + ":\n")
			f.write("\n".join(liste))
			try:
				f.write("\nRespons : " + svar.splitlines()[6])
			except:
				pass
		f.write('\nOppdatert: ' + time.ctime())		
		f.close()
		#lage p1logg
		if logging and mode == 'a':
			try:
				f=open(logroot + kanal +".txt", 'a')
			except:
				f=open(logroot + kanal +".txt", 'w') 
			f.write("\n\n" + blokk + ":\n")
			f.write("\n".join(liste))
	 		try:
				f.write("\nRespons : " + svar.splitlines()[6])
			except:
				pass
			f.write('\nOppdatert: ' + time.ctime())
			f.close()
		if logging and mode == 'w':
			f=open(logroot + kanal +".txt", 'a')
			f.write('\n***********************')
			f.close()

	return "Ikke ferdig"
	ret_svar = {}
		
	ret_svar['status']='0'
	ret_svar['reason']='Starter utsendelse'
	
	
	
def main():
	
	pass
	
if __name__ == '__main__':
	
	alfa= main()
	print alfa						
	

    
    

