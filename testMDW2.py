# -*- coding: utf-8 -*-
"ertå"
#Tester for MDW2



import sys
import xml.dom.minidom

from os import environ as env
import gluoncommons
from os import listdir
import re
#import dab
#print(env)

VERBOSE = False

def av_sats(tittel):
    "Filtrerer titler etter sats"
    if tittel:
        sats_filter = re.compile('(.*?)(: \d*?\. sats)(.*?)\Z')
        matchet = sats_filter.match(tittel)
        if matchet:
            return matchet.group(1) + matchet.group(2)
    return tittel

def av_dur(tittel):
    "Filtrerer ut toneart"
    if tittel:
        dur_filter = re.compile('(.*?)(, \w*?-dur|, \w*?-moll)(.*?)\Z')
        matchet = dur_filter.match(tittel)
        if matchet:
            return matchet.group(1) + matchet.group(3)
        else:
            return tittel


def av_opus(tittel):
    if tittel:
        #Opusnummer og undernummer, inskutt
        sats_filter = re.compile('(.*?)(, op\.? \d* nr\. \d*)(.*?)\Z')
        matchet = sats_filter.match(tittel)
        if matchet:
            tittel = matchet.group(1) + matchet.group(3)
        #Opusnummer til slutt
        sats_filter = re.compile('(.*?), op\.? \d*\Z')
        matchet = sats_filter.match(tittel)
        if matchet:
            tittel = matchet.group(1)
        #Opusnummer og undernummer til slutt
        sats_filter = re.compile('(.*?):?,? op\.? \d*\.? nr\. \d*\Z')
        matchet = sats_filter.match(tittel)
        if matchet:
            tittel = matchet.group(1)

    return tittel

def av_BWV(tittel):
    if tittel:
        #Opusnummer og undernummer, inskutt
        sats_filter = re.compile('(.*?), BWV \d*(.*?)\Z')
        matchet = sats_filter.match(tittel)
        if matchet:
            tittel = matchet.group(1) + matchet.group(2)
    return tittel

def av_RV(tittel):
    if tittel:
        #Opusnummer og undernummer, inskutt
        sats_filter = re.compile('(.*?), RV \d*(.*?)\Z')
        matchet = sats_filter.match(tittel)
        if matchet:
            tittel = matchet.group(1) + matchet.group(2)
    return tittel

def av_RV(tittel):
    if tittel:
        sats_filter = re.compile('(.*?), RV \d*(.*?)\Z')
        matchet = sats_filter.match(tittel)
        if matchet:
            tittel = matchet.group(1) + matchet.group(2)
    return tittel

def av_K(tittel):
    if tittel:

        sats_filter = re.compile('(.*?),? K\. ?\d*\Z')
        matchet = sats_filter.match(tittel)
        if matchet:
            tittel = matchet.group(1)
    return tittel

def get_title(doc):
    pars = xml.dom.minidom.parseString(doc)
    objekter = gluoncommons.finnVerdi(pars, '/gluon/objects/object/subelements/+object', nodetre=True)
    for objekt in objekter:
        if gluoncommons.finnVerdi(objekt, '@runorder')=='future':
            return gluoncommons.finnVerdi(objekt, 'metadata/titles/title')


def short_name(name):
    initials = []
    if not name:
        return name
    names = name.rstrip().split(' ')
    gnames = names[:-1]
    for gname in gnames:
        initials.append(gname[0])


    initials.append(names[-1])
    #print(initials)
    return ' '.join(initials)


def filter_title(tittel, initsial=False):
    "Filtrerer titler"
    if tittel and '{' in tittel and '}' in tittel:
        composer, rest = tittel.split('{')
        if initsial:
            composer = short_name(composer)
        place, annonsment = rest.split('}')
        shortened = (composer + annonsment).replace('  ', '').replace(' :', ':')

        return shortened
    else:
        return tittel


def hent_filer(folder):
    org_len = 0
    res_len = 0
    for filename in listdir(folder):
        if filename.startswith('.'):
            continue
        f = open(folder + filename, encoding='utf-8')
        doc = f.read()
        f.close()

        title = get_title(doc)
        if title is None:
            continue
        print(title)
        org_len += len(title)
        title_uc = filter_title(title)
        if VERBOSE:
            print('title_uc:', title_uc)

        title_uc_init = filter_title(title, initsial=True)
        if VERBOSE:
            print('title_uc_init:', title_uc_init)

        title_uc_init_usats = av_sats(title_uc_init)
        if VERBOSE:
            print('title_uc_init_usats:', title_uc_init_usats)


        title_uc_init_usats = av_dur(title_uc_init_usats)

        title_uc_init_usats_uopus = av_opus(title_uc_init_usats)
        #if VERBOSE:
        #    print('title_uc_init_usats_uopus:', title_uc_init_usats_uopus)

        #title_uc_init_usats_uopus_BW = av_RV(av_BWV(av_K(title_uc_init_usats_uopus)))
        #print(title_uc_init_usats_uopus_BW)
        print(title_uc_init_usats)

        print()

        res_len += len(title_uc_init_usats)
        #

    print('Innsparing', res_len/org_len)

#print(sys.getdefaultencoding())
#print(sys.stdout.encoding)
hent_filer('/Users/n12327/Desktop/AKtest/')

