#! /usr/local/bin/python
# -*- coding: iso-8859-1 -*-

"""dls tjenester
utspillingsmodul.
Tømmer køen som har blitt lagt av breaking news og resultattjenesten
Har to modus, startet fra dls - modulen, med kanalnavn som argument
og en der den startes fra en crontab uten noe argument
"""


# TODO



# BUGS


import MySQLdb as mdb
import re
import time
from sys import argv

import sendTilDab
import lagTestWeb
from dbConn import database

#from annonser import *

tidssperre = 20

verbose = True


#def database(host = "160.68.118.48", user="tormodv", database="dab",passord="allmc21"):
#def database(host = "localhost", user="tormodv", database="dab",passord=""):
#	"Lager en databaseconnection."
#	d = mdb.connect(user=user,passwd=passord, host=host)
#	d.select_db(database)
#	return d


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





def storForbokstav(item):
	return item[0].upper() + item[1:]
	
def roter(s,n):
	"Roterer en liste N plasser"
	return s[n:] + s[:n]
	
def lagVisningstider(streng, min = 4, max = 20):
	"Lager en kommaseparert liste med visningstider, slik at vi får en individuel tilpassning av dls-ene"
	#128 er max linjelengde som gir verdien max
	
	return str(int((len(streng)) / 128.0 * max + min))
	
	

def main(kanal='alle'):
	"Sender ut det første elementet i køen for alle kanaler, dersom kanal ikke er satt som argument, da hentes kun et element for denne kanalen."
	#kanal = 'alle'
	if verbose:print '*****************************************************'
	#Kontakte databasen 
	
	d = database()
	
	#Først gjør vi en spørring, denne returnerer en liste av køen, grupert på elementer eller kun for den ene kanalen
	
	
	if kanal=='alle':
	
		c= d.cursor()
		sql = """select  

				kanal, blokk, visningslengde, tekst, localid
				from breaking
				
				group by 
				kanal

				order by

				tid

				;"""
 
	
	
		c.execute(sql,)
		breakingliste = c.fetchall()
		
		c.close()

	
	else:
		c= d.cursor()
		sql = """select  

					kanal, blokk, visningslengde, tekst, localid
				from breaking
				where kanal=%s
				

				order by

				tid
				limit 1
				;"""

	
	
		c.execute(sql,(kanal,))
		if c.rowcount ==1:
			breakingliste = [c.fetchone()]
		else:
			breakingliste = []
		c.close()
		


	for breaking in breakingliste:
		#Deler opp datasett
		kanal, blokk, visningslengde, tekst, localid = breaking
		#Sjekke først om denne kanalen har noe nylig lagt ut
		if verbose:print kanal, blokk, visningslengde, tekst
		c = d.cursor()
		sql = """ select UNIX_TIMESTAMP(tid) from breaking_last where kanal=%s limit 1;"""
		c.execute(sql,(kanal,))
		if c.rowcount ==1:
			#Denne finnes fra før og vi må vurdere om toden er mindre en tidssperre sekunder siden
			tid = c.fetchone()[0]
			#print tid - time.time()
			if time.time() - tid < tidssperre:
				c.close()
				continue
			
			#Vi legger ut noe nytt oppdatere
			sql = """UPDATE breaking_last SET 
						tid=NOW()
						where
						kanal=%s;"""
			c.execute(sql,(kanal,))
			
		else:
			#Her har vi ikke en gang hatt kanalen før vi legger inn tidssperren før vi legger noe ut
			sql =  """INSERT INTO breaking_last(kanal,tid) VALUES 
					(%s,NOW());
					""" 
			c.execute(sql,(kanal,))
		#Nå skal vi vise dataene som breaking melding
		kanal_dab = kanal
				
		#Send data til DAB
		multiplex = blokk
		if verbose:print "MULTIPLEX", multiplex
		
		start= sendTilDab.dabdato(time.time()) #DVS vi sender en liste som gjelder fra nå
		stop= sendTilDab.dabdato(time.time() + visningslengde)
		visningstider = visningslengde
		#Dersom vi har iteminfo er levetiden på listen lik den gjenværende tiden på det korteste innslaget
		
		#Lag kommando
		
		
		kommando = "SendDataDLS;%s;%s;%s;%s;%s;%s" % (
			multiplex,
			kanal_dab,
			0,#listetype Single=0,Loop=1,Background loop=2
			start,
			stop,
			visningstider 
			)
			
		if verbose:print kommando
		
		svar = sendTilDab.sendData(
		'http://160.68.105.26:8888/api',
		#'http://localhost/cgi-bin/mimetest.py',
		kommando = kommando,
		liste = [tekst]
		)['msg']
		
		if verbose : print svar
		try:
			svar2 = lagTestWeb.sendData(kanal,
				liste = [tekst], listetype = 0
			)
		except:
			svar2="Feil i oppretelsen av testdokument"

		if verbose:print svar2

		
		#Så stryker vi raden dette gjelder
		
		sql = """DELETE FROM breaking WHERE localid=%s;"""
		c.execute(sql,(localid,))
		
		if verbose:print "###DELETE###"
		
		c.close()

		
	
	
	#Lukke databasen
	
	d.close()

if __name__=='__main__':
	
	try:
	
		if argv[1]=="intervall" or argv[1]=="-i":
			intervall = int(argv[2])
			#dette gir oss ant kjøringer på et minutt
			loop = int(59 / intervall)
			for i in range(loop):
				main()
				time.sleep(intervall)
		
		elif argv[1]=="help" or argv[1]=="-h":
		
			print """Program for å lage digasrapporter i databasen.
Options:
========
	-i eller intervall : avstanden mellom hvert forsøk på utsendelse
	-h eller help : Denne hjelpeteksten
""" 
			
		else:
			print """Usage : %s -i ss
run with -h or help for more help""" % argv[0]

	except 0:

		print """Usage : %s -i ss
run with -h or help for more help""" % argv[0]
	
	
	
	
	
	
