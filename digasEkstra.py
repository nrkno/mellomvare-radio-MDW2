#! /usr/local/bin/python
# -*- coding: iso-8859-1 -*-


"""Legger inn ekstra info fra digas i sigmabasen"""

#TODO


# BUGS

import xml.dom.minidom
import MySQLdb as mdb
import re
import time
from dbConn import database

verbose = False


#def database(host="160.68.118.48", user="tormodv", database="dab",passord="allmc21"):
#def database(host="localhost", user="tormodv", database="dab",passord=""):
#	d = mdb.connect(user=user,passwd=passord, host=host)
#	d.select_db(database)
#	return d

def sjekkProgramLengde(d,kanal):
	"Sjekker om programmet som er på lufta nå, har fått lengde 0, i så fall rettes den til tiden frem til neste program. Har ingen definert returverdi."
	#Sjekk programme lengde
	c =  d.cursor()
	sql = """SELECT lengde FROM iteminfo WHERE kanal=%s and localid = 1;"""
	c.execute(sql,(kanal)) 
	try:
		lengde = int(c.fetchone()[0])
	except TypeError:
		lengde = 0
	except ValueError:
		lengde = 0
	#Dersom lengden ikke er null nå kan vi returnere uten å gjøre noe mer
	if lengde != 0:
		c.close()
		return
	#Hvis ikke for vi finne lengden
	sql = """select 
MAX(UNIX_TIMESTAMP(tid))
-
MIN(UNIX_TIMESTAMP(tid))
from 
iteminfo
where kanal = %s; """
	c.execute(sql,(kanal))
	try:
		beregnetLengde = int(c.fetchone()[0])
	except TypeError:
		beregnetLengde = 0
	except ValueError:
		beregnetLengde = 0
	#Hvis lengden er null nå også er vi like kloke og må returnere
	if beregnetLengde == 0:
		c.close()
		return
	sql = """UPDATE iteminfo SET 
					lengde=%s
					WHERE kanal=%s and localid = 1;"""
	c.execute(sql,(beregnetLengde, kanal))
	c.close()
	if verbose:print "Rettet lengde på programm",lengde, beregnetLengde
		

def isoTilLengde(isoTid):
	tid = 0.0
	tidsFeil = "Feil i konvertering fra ISO 8601 format."
	if isoTid[0]!='P':
		raise tidsFeil,"Begynner ikke med P"
	#Split dager fra timer
	dager,timer = isoTid[1:].split('T')
	#Finn sekunder osv.
	p=re.search('(\d+|\d+\.\d+)S',timer)
	if p:
		tid += float(p.group(1))
	p=re.search('(\d+|\d+\.\d+)M',timer)
	if p:
		tid += float(p.group(1)) * 60
	p=re.search('(\d+|\d+\.\d+)H',timer)
	if p:
		tid += float(p.group(1)) * 3600
	# dager o.l.
	p=re.search('(\d+|\d+\.\d+)D',dager)
	if p:
		tid += float(p.group(1)) * 3600 * 24
	p=re.search('(\d+|\d+\.\d+)M',dager)
	if p:
		tid += float(p.group(1)) * 3600 * 24 * 30
	p=re.search('(\d+|\d+\.\d+)Y',dager)
	if p:
		tid += float(p.group(1)) * 3600 * 24 * 365
	
	return tid

def ISOtilDato(dato,sekunder=0, sql=0):
	offsett = 0
	if not dato:
		return 0
	if type(dato)!=type(''):
                #Dette er en forelÃ¸pig patch for at en har begynt Ã¥ bruke datetime objekter
                dato = dato.isoformat()
	if 'T' in dato or sql:
		aar = int(dato[0:4])
		if aar < 1970:
			#Da har vi et problem
			aar = aar + 60
			offsett = 1893456000.0
			
		try:
			if sekunder:
				tid= time.mktime ((aar,int(dato[5:7]), int(dato[8:10]),int(dato[11:13]),int(dato[14:16])
						,int(dato[17:19]),-1,-1,-1))
			else:
				tid= time.mktime ((aar,int(dato[5:7]), int(dato[8:10]),int(dato[11:13]),int(dato[14:16])
						,0,-1,-1,-1))
		except ValueError:
			tid = 0
			
	else:
		try:
			tid = int(dato)
		except:
			tid=0

	return tid - offsett
	

def finnUnger(noder,tag,kunEn=0):
	s=[]
	for node in noder:
		if node.nodeType == node.ELEMENT_NODE:
			if node.tagName == tag:
				s.append(node)
				if kunEn: return s
				
	return s

def hentVerdier(noder,lim='', encoding = 'utf-8'):
	s=''
	for node in noder:
		if node.nodeType == node.TEXT_NODE:
			s+=node.data + lim
	return s.encode(encoding,'replace')
	
def finnVerdi(xmlobjekt,path, entity = False, nodetre = False, encoding = 'iso-8859-1'):
	#path til nodeliste
	nodeliste = path.split('/')
	try:
		for node in nodeliste:
			if node=='':
				continue
			if node[0]!='@':
				if  node[0]=='+' and nodetre:
					xmlobjekt = finnUnger(xmlobjekt.childNodes,node[1:],kunEn=0)
					#Siden dette kun er gyldig i siste node:
					break
					#Så fortsetter vi under
				else:
					xmlobjekt = finnUnger(xmlobjekt.childNodes,node,kunEn=1)[0]
			else:
				#returnere attributverdi
				return xmlobjekt.getAttribute(node[1:]).encode(encoding,'replace')
				
	except IndexError:
		if nodetre:
			return []
		else:
			return ''
	if nodetre:
		return xmlobjekt
	if not entity:
		return hentVerdier(xmlobjekt.childNodes, encoding = encoding)
	else:
		return entetyReplace(hentVerdier(xmlobjekt.childNodes, encoding = encoding))
		
	
def entetyReplace(s):
	s = s.replace('&amp;','&')
	
	return s


def parser(xmlstreng):
	"Parser 24 itmer f¿r xml fra digas"
	
	
	#Skrive inn hele dok i basen
	
	
	##Status er 0 for ikke prossesert, 1 for oppdatert info,  2 for ny, 3 for "force breaking"
	
	#Fjernes etterpŒ
	status = 0
	
	
	
	#return {'status':status, 'kanal':kanal, 'datatype':'iteminfo'}
	
	#Lager en database forbindelse
	d=database()
	c=d.cursor()
	
	pars = xml.dom.minidom.parseString(xmlstreng)

	kropp = pars.getElementsByTagName('objects')[0]
	
	progID = finnVerdi( kropp,'object/@dataid', entity = 0)
	fragment = finnVerdi( kropp,'object/@fragment', entity = 0)
	
	#Hente kanal pŒ grunnlag av progID fra dab.sigma
	
	#***Oppdateres
	kanal = 'p1'
	
	status = 1
	try:
		#Denne feiler pent hvis posten ikke finnes
		sql = """UPDATE sigma SET
				digasExtra=%s
				WHERE progid=%s
				""" 
		c.execute(sql,(
			xmlstreng,
			progID
					
				)
			)
	except:
		status = 0
						
	c.close()


			



						
	#Lukke database
	d.commit()
	d.close()
	return {'status':status, 'kanal':kanal, 'datatype':'iteminfo'}
	
if __name__=='__main__':
	f=open('item3.xml')
	print parser(f.read())
	f.close()
	
