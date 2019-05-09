# -*- coding: utf-8 -*-
"Gets data from other on-air now service"

from urllib.request import urlopen
from db_conn import database


SAMI_SR_URL = "http://api.sr.se/api/v2/playlists/rightnow?channelid=224"

def get_insert_data(url = SAMI_SR_URL, kanal='sami_sr'):
    "Gets data from url"

    resp = urlopen(url)

    print(resp)
