# -*- coding: utf-8 -*-
"ertå"
#Tester for MDW2





from os import environ as env
import gluoncommons
from os import listdir
#import dab


def hent_filer(folder):
    for filename in listdir(folder):
        if filename.startswith('.'):
            continue
            
        print(filename)



hent_filer('/Users/n12327/Desktop/AKtest')

