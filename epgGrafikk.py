#! /usr/local/bin/python
# -*- coding: iso-8859-1 -*-
######################################################################
#   Versjon som støtter epg i dls
#	
######################################################################
#import cgitb; cgitb.enable(display=1, logdir="/var/log/gluon")


"""
select
tid, tittel, tekstekode
from epgHK

where sendedato > now()
and 
kanal = "NRK 2"
order by sort
;

"""


import os
import time

import MySQLdb as mdb
from dbConn import database

iDrift = 1
macTest = 1

ECC = 'E2' #Landaskode for Norge
Eld =  {'riks':'FF20','region':'FF30'}
SidSufix = {'p1':'1',
		'p2':'2',
		'p3':'3',
		'ak':'4',
		'sami':'5',
		'an':'6',
		'storting':'7',
		'mpetre':'8'}

kanalSW = {'NRK1':'NRK 1','NRK2':'NRK 2','NRK3':'NRK 3'}

		

mal="""<?xml version="1.0" encoding="ISO-8859-1"?>
<schedule date="%s" channel="%s">
%s</schedule>"""

linjemal="""<programme starttime="%s" title="%s" subtitlecode="%s" />\n"""


crlf = chr(10) + chr(13)
crlf =  chr(10)

#def database(host="160.68.118.48", user="tormodv", database="dab",passord="allmc21"):
#def database(host="127.0.0.1", user="tormodv", database="dab",passord=""):
#	d = mdb.connect(user=user,passwd=passord, host=host)
#	d.select_db(database)
#	return d

def main(kanal = "NRK 2"):
	
	if kanal in kanalSW:
		kanal = kanalSW[kanal]
	s = ''
	d = database()
	c = d.cursor()
	sql = """select tid, tittel, tekstekode from epgHK where sendedato > now() and kanal = %s order by sort ;"""
	
	c.execute(sql,(
					kanal,))
	programmer = c.fetchall()
	
	
	sql = """select date(sendedato) from epgHK where sendedato > now() and kanal = %s order by sort limit 1;"""
	
	c.execute(sql,(
					kanal,))
	dato = c.fetchone()[0]
	
	#dato = ''
	
	c.close()
	d.close()
	for p in programmer:
		s += linjemal % p
	return mal % (dato, kanal, s)

if __name__=='__main__':
	
	
	
	print "Content-type: text/xml"
	print
	

	alfa= main(kanal = os.environ['QUERY_STRING'])
	print alfa
	
				
