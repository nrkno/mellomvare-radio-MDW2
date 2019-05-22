# -*- coding: utf-8 -*-

"Tester for MDW2"

from os import environ
from urllib.request import urlopen

# TODO: Skift til den nye databasen
# TODO: bruk dette til å lese datetime:  datetime.datetime.fromisoformat('1998-03-09T13:45:00')
#import dabfilter
import dab
import dls_ext
import ut_gluon2
import iteminfo
import get_iteminfo


#print(dls_ext.til_dab(kanal='ak'))

#ut_gluon2.lag_metadata(kanal='p3', datatype='iteminfo', test_modus=True)
adr = 'http://127.0.0.1:5500/dab.wsgi/p4'
with open('/Users/n12327/Documents/Xcode_prosjekter/MDW2/Eksempelfiler/item.xml') as fp:
    dok = fp.read().encode('utf-8')

result = urlopen(adr, data=dok, timeout=5)

print(result.status)
print(result.read().decode('utf-8'))
#iteminfo.parser(dok)
#dls_ext.lag_metadata(kanal='gulling')
#dab.main(dok)
#print(get_iteminfo.get_insert_data())

print('Hello')
