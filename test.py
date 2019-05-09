# -*- coding: utf-8 -*-

"Tester for MDW2"

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

with open('/Users/n12327/Documents/Xcode prosjekter/MDW2/Eksempelfiler/item.xml') as fp:
    dok = fp.read()
#iteminfo.parser(dok)
#dls_ext.lag_metadata(kanal='gulling')
#dab.main(dok)
print(get_iteminfo.get_insert_data())

print('Hello')
