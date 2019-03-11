# -*- coding: utf-8 -*-

"Tester for MDW2"

# TODO: Skift til den nye databasen

#import dabfilter
import dab
import dls_ext
import ut_gluon2



#print(dls_ext.til_dab(kanal='ak'))

ut_gluon2.lag_metadata(kanal='p3', datatype='iteminfo', test_modus=True)

with open('/Users/n12327/Documents/Xcode prosjekter/MDW2/Eksempelfiler/item.xml') as fp:
    dok = fp.read()


print('Hello')
