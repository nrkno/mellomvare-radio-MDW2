# -*- coding: utf-8 -*-
"Forkorter titler, fra DMA slik at de blir mer lesbare som dls"
import re

def forkort_tittel(tittel):
    "Forkorter titler etter reglene gitt av NRK klassisk"
    if tittel is None:
        return tittel

    tittel = av_land_forkort_navn(tittel, initsial=True)

    tittel = av_sats(tittel)

    tittel = av_dur(tittel)

    #tittel = av_opus(tittel)

    #tittel = av_rv(tittel)

    #tittel = av_bwv(tittel)

    return tittel


def av_sats(tittel):
    "Filtrerer titler etter sats"
    if tittel:
        sats_filter = re.compile(r'(.*?)(: \d*?\. sats)(.*?)\Z')
        matchet = sats_filter.match(tittel)
        if matchet:
            return matchet.group(1) + matchet.group(2)
    return tittel

def av_dur(tittel):
    "Filtrerer ut toneart"
    if tittel:
        dur_filter = re.compile(r'(.*?)( ?,?i? \w*?-dur| ?,?i? \w*?-moll)(.*?)\Z')
        matchet = dur_filter.match(tittel)
        if matchet:
            return matchet.group(1) + matchet.group(3)

    return tittel


def av_opus(tittel):
    "Fjerner opus numre fra titler"
    if tittel:
        #Opusnummer og undernummer, inskutt
        sats_filter = re.compile(r'(.*?)(, op\.? \d* nr\. \d*)(.*?)\Z')
        matchet = sats_filter.match(tittel)
        if matchet:
            tittel = matchet.group(1) + matchet.group(3)
        #Opusnummer til slutt
        sats_filter = re.compile(r'(.*?), op\.? \d*\Z')
        matchet = sats_filter.match(tittel)
        if matchet:
            tittel = matchet.group(1)
        #Opusnummer og undernummer til slutt
        sats_filter = re.compile(r'(.*?):?,? op\.? \d*\.? nr\. \d*\Z')
        matchet = sats_filter.match(tittel)
        if matchet:
            tittel = matchet.group(1)
    return tittel

def av_bwv(tittel):
    "Tar bort numerering av verker av Bach"
    if tittel:
        #Opusnummer og undernummer, inskutt
        sats_filter = re.compile(r'(.*?), BWV \d*(.*?)\Z')
        matchet = sats_filter.match(tittel)
        if matchet:
            tittel = matchet.group(1) + matchet.group(2)
    return tittel

def av_rv(tittel):
    "Tar bort RV nummer"
    if tittel:
        #Opusnummer og undernummer, inskutt
        sats_filter = re.compile(r'(.*?), RV \d*(.*?)\Z')
        matchet = sats_filter.match(tittel)
        if matchet:
            tittel = matchet.group(1) + matchet.group(2)
    return tittel

def av_k(tittel):
    "Tar bort Köchel nummer"
    if tittel:
        sats_filter = re.compile(r'(.*?),? K\. ?\d*\Z')
        matchet = sats_filter.match(tittel)
        if matchet:
            tittel = matchet.group(1)
    return tittel

def short_name(name):
    "Forkorter navn"
    initials = []
    if not name:
        return name
    names = name.rstrip().split(' ')
    gnames = names[:-1]
    for gname in gnames:
        initials.append(gname[0])
    initials.append(names[-1])
    return ' '.join(initials)

def av_land_forkort_navn(tittel, initsial=False):
    "Filtrerer titler"
    if tittel and '{' in tittel and '}' in tittel:
        composer, rest = tittel.split('{')
        if initsial:
            composer = short_name(composer)
        annonsment = rest.split('}')[1]
        shortened = (composer + annonsment).replace('  ', '').replace(' :', ':')
        return shortened

    return tittel
