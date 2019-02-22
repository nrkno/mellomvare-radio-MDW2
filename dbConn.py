#! /usr/local/bin/python
# -*- coding: iso-8859-1 -*-

import pymysql as mdb

def database(host="malxmysql18", user="dab_usr", database="dab",passord="DyFJBMSjW9Xb2"):
#def database(host="160.68.118.48", user="tormodv", database="dab",passord="allmc21"):
#def database(host="localhost", user="tormodv", database="dab",passord=""):
        d = mdb.connect(user=user,passwd=passord, host=host)
        d.select_db(database)
        return d

