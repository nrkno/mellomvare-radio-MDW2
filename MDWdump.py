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
import MySQLdb as mdb
from dbConn import database

verbose = False
testFil = False
traader = True #Kjører hver av utspillingsmodulene i tråder
maxVent = 60 #Maks ventetid på utspillingsmodulene


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

#def database(host="160.68.118.48", user="tormodv", database="dab",passord="allmc21"):
#def database(host="127.0.0.1", user="tormodv", database="dab",passord=""):
#	d = mdb.connect(user=user,passwd=passord, host=host)
#	d.select_db(database)
#	return d

	
def main():
	#Hvis det ikke er noe dok her er det ønsket en oppdatering
	d = database()
	c = d.cursor()
	sql = """SELECT kanal, type, localid, tittel, progId, laget, tid, lengde, beskrivelse, artist, digastype FROM iteminfo ORDER by kanal"""
	
	print '<html><table border="1">'
	
	
	c.execute(sql,)
	rows = c.fetchall()
	c.close()
	d.close()
	#print rows
	for row in rows:
		print '<tr>'
		for col in row:
			print '<td>%s</td>' % col
			
			
		print '</tr>'
		
	
	print "</table></html>"

if (__name__=='__main__'):
		#Dette skal vaere et cgi skript
				
		print "Content-type: text/html"
		print
		
		#print environ
		
		
				
		main()

	

