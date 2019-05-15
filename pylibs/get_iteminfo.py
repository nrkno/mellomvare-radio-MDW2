# -*- coding: utf-8 -*-
"Gets data from other on-air now service"

import xml.dom.minidom
from datetime import datetime, timedelta
import pytz
from urllib.request import urlopen
from db_conn import database

from iteminfo import finn_verdi

SAMI_SR_URL = "http://api.sr.se/api/v2/playlists/rightnow?channelid=224"

def get_insert_data(url = SAMI_SR_URL, kanal='sami_sr'):
    "Gets data from url"
    
    #Lese data
    
    resp = urlopen(url)
    dok = resp.read()
    
    #Sjekke om dok er uforandret
    d = database()
    c = d.cursor()
    
    sql = """SELECT element FROM iteminfo WHERE kanal=%s and localid=3;"""
    c.execute(sql, (kanal, ))
    if c.rowcount == 1:
        gdok = c.fetchone()[0]
    
        if gdok == dok.decode('UTF-8'):
            return {'status':0, 'kanal':kanal}
    
    #Først fjerne eksisterende data
    
    d = database()
    c = d.cursor()
    
    sql = """DELETE FROM iteminfo
                WHERE kanal=%s;"""
    c.execute(sql, (kanal, ))

    resp = urlopen(url)
    dok = resp.read()
    
    
    
    
    pars = xml.dom.minidom.parseString(dok)
    
    # Trenger bare innslags info
    title = finn_verdi(pars, '/sr/playlist/song/title')
    if title != '':
        artist = finn_verdi(pars, '/sr/playlist/song/artist')
        start = finn_verdi(pars, '/sr/playlist/song/starttimeutc')
        stop = finn_verdi(pars, '/sr/playlist/song/stoptimeutc')
    
        start_time = datetime.fromisoformat(start[:-1])
        slutt_time = datetime.fromisoformat(stop[:-1])
    
        length = slutt_time - start_time
    
        utc_zone = pytz.timezone("UTC")
        utc_server = pytz.timezone("CET")

        start_time = utc_zone.localize(start_time).astimezone(utc_server)

        sql = """INSERT INTO iteminfo(kanal, tittel, artist, tid, lengde, element, localid, localprogid, digastype) VALUES
                    (%s,%s,%s,%s,%s,%s, 3, 1, "Music") ;"""
        
        c.execute(sql, (
                        kanal,
                        title,
                        artist,
                        start_time,
                        length.seconds,
                        dok
                        ))
    else:
        sql = """INSERT INTO iteminfo(kanal, element, localid, localprogid, digastype) VALUES
                    (%s,%s, 3, 1, "None") ;"""
        
        c.execute(sql, (
                        kanal,
                        resp.read()
                        ))
    c.execute("COMMIT")
    c.close()
    
    return {'status':1, 'kanal':kanal}
