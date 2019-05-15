# -*- coding: utf-8 -*-

import pymysql as mdb
from os import environ

def database(host="malxmysql20", user="mdw2", database="MDW2"):
        d = mdb.connect(user=user, passwd=environ['DB_PASS_WD'], host=host)
        d.select_db(database)
        return d

