#! /usr/local/bin/python
# -*- coding: iso-8859-1 -*-

import pymysql as mdb
# TODO: endres til ny base, bruker bare denne for test
def database(host="malxmysql18", user="dab_usr", database="dab", passord="DyFJBMSjW9Xb2"):
        d = mdb.connect(user=user,passwd=passord, host=host)
        d.select_db(database)
        return d

