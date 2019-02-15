# -*- coding: utf-8 -*-

import re

def forkort_tittel(tittel):
    #Pre-test
    if tittel is None:
        return tittel

    if True:
        tittel = av_land_forkort_navn(tittel, initsial=True)

    if True:
        tittel = av_sats(tittel)

    if True:
        tittel = av_dur(tittel)

    if False:
        tittel = av_opus(tittel)

    if False:
        tittel = av_RV(tittel)

    if False:
        tittel = av_BWV(tittel)

    return tittel


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
        dur_filter = re.compile('(.*?)( ?,?i? \w*?-dur| ?,?i? \w*?-moll)(.*?)\Z')
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


def av_land_forkort_navn(tittel, initsial=False):
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

