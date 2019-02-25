# -*- coding: utf-8 -*-

"""dls tjenester
utspillingsmodul.
Henter data fra databasen, sjekker utvalget fra sidevisningsmodulen, sjekker item som er på utspillingsmodulen
roterer så listen deretter.
"""

import time
from random import choice, sample

import send_til_server
from annonser import *
from db_conn import database

IKKE_DLS = ['nett'] #Legg inn bloknavn som ikke støtter dls teknologien, nettradioen f. eks.

EGENPROD = 'EBU-NONRK' #Label for egenproduksjon
MAX_LEVETID = 2
VERBOSE = True
LAGET_GRENSE = 1980 #Årstall for når vi skal markere at eldre er arkivopptak

def minimum_levetid(d, kanal):
    "Finner den laveste gjenværende tid på en kanal"
    # Denne må modifiseres for å ta hensyn til alle dls'ene i kanalen
    # Kanskje heller ta vare på alle stoptidene slik at vi kan legge de på en stak som regenererer dls,ene?
    c = d.cursor()
    sql = """select
UNIX_TIMESTAMP(tid) + lengde - UNIX_TIMESTAMP()
 as tid_igjen
from iteminfo
where
 kanal=%s
order by tid_igjen
Limit 1;
"""
    c.execute(sql, (kanal))
    try:
        try:
            periode = int(c.fetchone()[0])
        finally:
            c.close()
    except TypeError:
        return 0
    if kanal != 'ak':
        periode += 600
    return periode

def sammenlign_tittler(tittel1, tittel2):
    "Sammenligner om titler er nesten like, f. eks. to satser av et verk, returnerer True hvis vi synes det er likt"
    try:
        for i, bokstav1 in enumerate(tittel1):
            if bokstav1 != tittel2[i]:
                break
    except IndexError:
        pass
    #Vi tar ut forskjellene
    likheten = tittel1[:i].rstrip(':.;, ')
    forskjell = tittel1[i:]

    #Vi gjør en enkel test i første omgang, siden kan dette brukes til noe ala : ... sats 1. fulgt av sats 2.
    if len(likheten) > 2.5 * len(forskjell) and 'sats' in forskjell:
        return True
    else:
        return False

def iso_til_dato(dato, sekunder=0, sql=False):
    "Gjør om iso strenger til vanlige sekunder"
    if not dato:
        return 0
    # FIXME: Denne er trolig unødvendig nå
    if type(dato) != type(''):
        #Dette er en foreløpig patch for at en har begynt å bruke datetime objekter
        dato = dato.isoformat()
    if 'T' in dato or sql is True:
        try:
            if sekunder:
                tid = time.mktime((int(dato[0:4]), int(dato[5:7]), int(dato[8:10]), int(dato[11:13]), int(dato[14:16]),
                                   int(dato[17:19]), -1, -1, -1))
            else:
                tid = time.mktime((int(dato[0:4]),int(dato[5:7]), int(dato[8:10]), int(dato[11:13]), int(dato[14:16]),
                                   0, -1, -1, -1))
        except ValueError:
            tid = 0
    else:
        try:
            tid = int(dato)
        except:
            tid = 0
    return tid

def insert_value(template, tittel, artist, beskrivelse, digastype, label):
    "I steden for eval, setter vi inn verdier i en streng: <tittel> byttes med tittelen"

    return template.replace('<tittel>', tittel).replace('<artist>', artist)

def finn_kanaler(d,):
    "Returnerer alle kanalnavnene fra dab-databasen"
    c = d.cursor()
    sql = """SELECT DISTINCT navn FROM kanal WHERE foreldre_id=id;"""
    svar = []
    c.execute(sql)
    while 1:
        post = c.fetchone()
        if post:
            svar.append(post[0].lower())
        else:
            break
    c.close()
    return svar

def distriktskanal(d, kanal):
    "Returnerer en liste av underkanaler på grunnlag av et kanalnavn"
    #Finne først intern ideen på kanalen
    c = d.cursor()
    sql = """SELECT DISTINCT id FROM kanal WHERE navn =%s LIMIT 1;"""
    c.execute(sql, (kanal))
    row = c.fetchone()
    c.close()
    if row:
        kanalId = row[0]
    else:
        kanalId = 99
        if VERBOSE:
            print("UKJENT KANAL", kanal)

    #Finne så hvilke distriktskanaler vi har

    c = d.cursor()
    sql = """SELECT navn FROM kanal WHERE foreldre_id =%s ;"""
    s = []
    c.execute(sql, (kanalId))
    while 1:
        p = c.fetchone()
        if p:
            s.append(p[0])
        else:
            break
    c.close()
    #Dersom denne ender i en null, så har denne kanalen ingen avleggere, ikke en gang seg selv.
    #Derfor legger vi til kanalen selv som det ene punktet i en liste
    if s == []:
        c = d.cursor()
        sql = """SELECT navn FROM kanal WHERE ID =%s LIMIT 1;"""
        s = []
        c.execute(sql, (kanalId))
        while 1:
            p = c.fetchone()
            if p:
                s.append(p[0])
            else:
                break
        c.close()
    return s

def finnHovedkanal(d, kanal):
    "Returnerer navnet på hovedkanalen eller kanalnavn på grunnlag av kanalnavn"
    #Finne først intern ideen på morkanalen
    c = d.cursor()
    sql = """SELECT DISTINCT foreldre_id FROM kanal WHERE navn =%s LIMIT 1;"""
    c.execute(sql, (kanal))
    row = c.fetchone()
    c.close()
    if row:
        hovedId = row[0]
    else:
        hovedId = 99
        print("UKJENT KANAL", kanal)

    #Finne hva hovedkanalen heter
    c = d.cursor()
    sql = """SELECT navn FROM kanal WHERE id =%s LIMIT 1;"""
    c.execute(sql, (hovedId))
    row = c.fetchone()
    c.close()
    if row:
        return row[0]
    return kanal

def finnBlokker(d):
    "Returnerer alle blokkene fra dab-databasen"
    c = d.cursor()
    sql = """SELECT DISTINCT id, navn FROM blokk;"""
    s = {}
    c.execute(sql)
    while 1:
        p = c.fetchone()
        if p:
            s[int(p[0])] = p[1]
        else:
            break
    c.close()
    return s

def hent_visningsvalg(d, kanal, datatype='iteminfo'):
    "Henter ut visningsvalg og verdier for filterfunksjonen"
    #Først finner vi kanal_ID på kanalen.
    blk = {}
    als = {}
    c = d.cursor()
    sql = """SELECT DISTINCT
            datatyper.tittel,datatyper.alias, blokk.navn
            FROM datatyper
            INNER JOIN dataikanal ON datatyper.id=dataikanal.datatype_id
            INNER JOIN blokk ON dataikanal.blokk_id=blokk.id
            INNER JOIN kanal ON kanal.id=dataikanal.kanal_id
            WHERE kanal.navn = %s;"""
    c.execute(sql, (kanal,))

    for row in c.fetchall():
        tittel, alias, blokk = row
        if not blokk in blk:
            blk[blokk] = [tittel]
            als[blokk] = [alias]
        else:
            blk[blokk].append(tittel)
            als[blokk].append(alias)
    if VERBOSE:
        print(blk, als)
    #Så er det vake blokker
    #Hvis ikke typen er i alias skal vi ikke ut på den blokken
    #finne typenummer
    sql = """SELECT alias
            FROM datatyper
            WHERE tittel = %s LIMIT 1"""
    c.execute(sql,(datatype,))
    if c.rowcount == 1:
        opt_type = c.fetchone()[0]
    else:
        opt_type = 0
    c.close()
    for vblk in als:
        if not opt_type in als[vblk]:
            blk.pop(vblk)
    return blk

def hentPgrinfo(d, kanal, hovedkanal):
    "Henter kanalnavn og kanalbeskrivelse. Returnerer en liste de kanalnavn er 1. element og beskrivelsen 2."
    c = d.cursor()
    sql = """SELECT tittel, beskrivelse FROM iteminfo WHERE kanal=%s AND type='pgr' LIMIT 1;"""
    c.execute(sql, (kanal,))
    try:
        try:
            tittel, beskrivelse = c.fetchone()
        finally:
            c.close()
    except TypeError:
        return []
    return [tittel, beskrivelse]

def hentProgrammeinfo(d, kanal, hovedkanal, distriktssending=False, useTimeLimit=True, har_distrikter=False, forceDistrikt=True):
    """Henter informasjon om programmet som er på lufta, returnerer en liste med et element. Ved distriktssendinger kan flagget
    for distriktssendinger settes.
    Finner ut om det gjeldenede programmet er på lufta akkurat nå, dersom ikke finner ut om hovedkanalen har data
    Dersom forceDistrikt flagget er satt, så vil et program i en distriktskanal komme på lufta uten at det er definert dirstriktskanal"""
    #Skal returnere lista og distriktsflagg
    #Endres når det ikke blir vanlig å legge inn programleder i beskrivelsesfeltet
    if VERBOSE:
        print()
        print('Henter programme info - inn')
        print('kanal=%s, hovedkanal=%s, distriktssending=%s, useTimeLimit=%s, har_distrikter=%s' % ( kanal, hovedkanal, distriktssending, useTimeLimit, har_distrikter))
    c = d.cursor()
    
    #Sjekke om programmet er utløpt i kanalen
    sql = """select tittel, beskrivelse, artist, tid FROM iteminfo
    WHERE kanal=%s AND type='programme' AND localid = '1' AND
    UNIX_TIMESTAMP(tid) + lengde >= UNIX_TIMESTAMP(now()) AND not(UNIX_TIMESTAMP(tid)>UNIX_TIMESTAMP(now())) AND
    progId !='DUMMY_PROD_NR'
    LIMIT 1;"""
    #Denne gir og PI sendeflatetype
    c.execute(sql, (kanal,))
    if c.rowcount:
        iProgramme = True
        if VERBOSE:
            print("%s har et PROGRAM" % kanal)
    else:
        iProgramme = False
        if VERBOSE:
            print("%s IKKE eget PROGRAM" % kanal)
    if iProgramme and har_distrikter:
        #Vi har med å gjøre en distriktskanal som har eget program, da skal hele dls-en ignoreres. Den skal genereres ut ifra kanalens egen oppkall
        c.close()
        if VERBOSE:
            print('VOID - har eget program')
        return ['VOID'], False
        # Sjekke på denne verdien om kanalen skal hoppes over i

    #Vi må sjekke om hovedkanalen har en distriktsflate

    sql = """SELECT digastype FROM iteminfo WHERE kanal=%s AND type='programme' AND localid = '1' LIMIT 1;"""
    #Denne gir og PI sendeflatetype
    c.execute(sql, (hovedkanal,))
    try:
        try:
            digastype, = c.fetchone()
        finally:
            c.close()
    except TypeError:
        digastype = ''
        #Sjekke omo denne egentlig vil kunne feile
    #Finne alternativ måte for å tenne distriktsflagg
    if iProgramme and (kanal != hovedkanal):
        #Kanalen har et aktivt program, og den har en mor, dvs hovedkanl er ikke seg selv.
        distriktssending = True
        tittelSufix = ''
    elif digastype == '50' and (kanal != hovedkanal):
        #Vi har en distriktssending av den gamle typen
        distriktssending = True
        #Vi har ennå ikke distriktsvise programme info
        #Vi henter først ut navnet "Brandet" på kanalen
        c = d.cursor()
        sql = """SELECT branding FROM kanal WHERE navn=%s LIMIT 1;"""
        c.execute(sql,(kanal,))
        try:
            try:
                branding, = c.fetchone()
            finally:
                c.close()
        except TypeError:
            pass
            #Sjekke omo denne egentlig vil kunne feile
        if branding:
            tittelSufix = ' fra ' + branding
        else:
            tittelSufix = ''
        kanal = hovedkanal #Dette gjør at vi aldri henter programdata fra distriktsflaten
    else:
        #Hovedkanalen er ikke registrert med en distriktsflate, sjekke om vi skal la underkanalen ta styringen
        #Vi skal ikke har regionvise resultater
        if forceDistrikt and iProgramme:
            #Vi bytter ikke kanaler, men stryker sufix
            tittelSufix = ''
        else:
            kanal = hovedkanal
            tittelSufix = ''

    c = d.cursor()
    sql = """SELECT tittel, beskrivelse, artist, tid FROM iteminfo WHERE kanal=%s AND type='programme' AND localid = '1'
    LIMIT 1;"""

    c.execute(sql,(kanal,))
    try:
        try:
            tittel, beskrivelse, artist, tid = c.fetchone()
        finally:
            c.close()
    except TypeError:
        if VERBOSE:
            print("Feil i utlesing av kanaldata=%s, henter fra hovedkanal=%s" % (kanal, hovedkanal))
        #Dersom vi ikke har noe her, kan det hende det er en distriktskanal som ikke har egne metadata,
        # *** ENDRING sjekke om programdataene er utløpt
        if hovedkanal and (not distriktssending):
            return hentProgrammeinfo(d,hovedkanal,None, distriktssending=distriktssending, useTimeLimit= useTimeLimit)
        else:
            return [''], distriktssending

    tittel = tittel + tittelSufix #Legger på f. eks. "fra NRK Trøndelag" på dirstriksflater
    if VERBOSE:
        print('Henter programme info - ut')
        print('kanal=%s, hovedkanal=%s, distriktssending=%s, useTimeLimit=%s, har_distrikter=%s' % ( kanal, hovedkanal, distriktssending, useTimeLimit, har_distrikter))
    #Dersom vi ikke er i en sending, skal vi jo ikke vise noe program
    #Dersom vi er mer enn fem minutter, 300 sekunder inn i et program viser vi bare programmet

    sekunderSiden = time.time() - iso_til_dato(tid, sekunder=1, sql=1)
    #Tar bort programomtale litt ut i programmet.
    if sekunderSiden > 600 and useTimeLimit:
        return [tittel], distriktssending
    if artist:
        item = tittel + '. ' + artist
        if len(item) > 128:
                return [tittel, artist], distriktssending
        else:
                return [item], distriktssending
    else:
        item = tittel + '. ' + beskrivelse
        if len(item) > 128:
                return [tittel, beskrivelse], distriktssending
        else:
                return [item], distriktssending

def hentProgrammeNext(d, kanal, hovedkanal, distriktssending=0):
    "Henter informasjon om det neste programmet som skal på lufta, returnerer en liste med et element."
    c = d.cursor()
    sql = """SELECT tittel, tid FROM iteminfo WHERE kanal=%s AND type='programme' AND localid = '2' LIMIT 1;"""
    c.execute(sql, (kanal, ))
    try:
        try:
            tittel, tid = c.fetchone()
        finally:
            c.close()
    except TypeError:
        if hovedkanal and not distriktssending:
            return hentProgrammeNext(d, hovedkanal, None)
        return []

    if type(tid) != type(''):
        #Dette er en foreløpig patch for at en har begynt å bruke datetime objekter
        tid = tid.isoformat()
    item = tid[11:16] + '- ' + tittel
    return [item]

def hentIteminfo(d, kanal, hovedkanal, distriktssending=0):
    "Henter informasjon om musikkinnslaget som er på lufta, returnerer en liste med et element."
    #Dersom vi ikke har en distriktssending, skal vi gå til hovedkanalen for metadata:
    if not distriktssending:
        kanal = hovedkanal
    c = d.cursor()
    #Først må vi finne ut om vi har en samsending

    sql = """SELECT kildekanal FROM iteminfo WHERE kanal=%s AND type='programme'  AND localid = '1' LIMIT 1 ;"""
    c.execute(sql, (kanal,))
    row =  c.fetchone()
    if row:
        kildekanal = row[0]
    else:
        kildekanal = False
    if kildekanal:
        #Da henter vi verdiene fra denne isteden
        kanal = kildekanal
    
    sql = """SELECT tittel, artist, beskrivelse, digastype, label FROM iteminfo WHERE kanal=%s AND type='item' AND localid = '3' LIMIT 1;"""
    c.execute(sql, (kanal,))
    try:
        try:
            tittel, artist, beskrivelse, digastype, label = c.fetchone()
        finally:
            c.close()
    except TypeError:
        if hovedkanal and not distriktssending:
            return hentIteminfo(d, hovedkanal, None)
        else:
            return []
    if digastype:
        if digastype !='Music':
            return []
    #Vi finner opptaksdato
    c = d.cursor()
    sql = """SELECT YEAR(laget) FROM iteminfo WHERE kanal=%s AND type='item'  AND localid = '3' LIMIT 1 ;"""
    c.execute(sql, (kanal,))
    try:
        try:
            laget, = c.fetchone()
        finally:
            c.close()
    except :
        laget = 0
    else:
        if laget < LAGET_GRENSE:
            tittel = "%s, innspilt %s," % (tittel, laget)

    if kanal in itemtittel:
        if not artist:
            item = tittel
        else:
            item = insert_value(choice(itemtittel[kanal]), tittel, artist, beskrivelse, digastype, label)
    else:
        item = insert_value(choice(itemtittel['nrk']), tittel, artist, beskrivelse, digastype, label)
    
    if label.startswith(EGENPROD):
        # Vi tar den enkle utvegen, det er snakk om en ann. av et program, denne er det vel snart ikke brukt for lenger men vi beholder den litt til. ***
        item = tittel+ '.|'+ artist

    #******REFR_Start
    s=[]
    #Sette sammen dls til så få linjer som mulig
    part = ''
    deler = item.split('|')
    for delen in deler:
        if part:
            if len(part) + len(delen) < 125:
                part = part + ' ' + delen
            elif len(delen) < 125:
                #Vi legger den ferdige dls fragmentet til listen
                s.append(part + '...')
                part = '...' + delen
            else:
                #Dls frqagmentet er for langt
                #Vi deler det på punktum, dersom det finnes
                if '.' in delen:
                    del1, del2 = delen.split('.', 1)
                    if len(part) + len(del1) < 125:
                        s.append(part + ' ' + del1 + '...')
                        part = '...' + del2
                    else:
                        #Vi må dytte part i listen
                        s.append(part + '...')
                        s.append('...'+ del1 + '...')
                        part = '...' + del2
                else:
                    print("#HER SKULLE VI IKKE HA VÆRT#")
                    #eg krise
                    #Lage rutine som deler på ord
        else:
            part = delen
    #Opprydding vi må uansett legge til den siste part
    s.append(part)
    #******REFR_END

    #Dersom det er ønskelig legge til platemerke
    if kanal == 'ak' and label:
        if not label.startswith('EBU-'):
            s.append(label)
    return s

def hentIteminfoExtra(d, kanal, hovedkanal, distriktssending=0):
    "Henter informasjon om ekstra musikkinformasjon om innslaget som er på lufta, returnerer en liste med et element."
    #Dersom vi ikke har en distriktssending, skal vi gå til hovedkanalen for metadata:
    if not distriktssending:
        kanal = hovedkanal
    c = d.cursor()
    #Først må vi finne ut om vi har en samsending
    sql = """SELECT kildekanal FROM iteminfo WHERE kanal=%s AND type='programme'  AND localid = '1' LIMIT 1 ;"""
    c.execute(sql,(kanal,))
    row =  c.fetchone()
    if row:
        kildekanal = row[0]
    else:
        kildekanal = False
    if kildekanal:
        #Da henter vi verdiene fra denne isteden
        kanal = kildekanal

    sql = """SELECT tittel,artist, beskrivelse, digastype, label FROM iteminfo WHERE kanal=%s AND type='item'  AND localid = '3' LIMIT 1 ;"""
    c.execute(sql,(kanal,))
    try:
        try:
            tittel, artist, beskrivelse, digastype, label = c.fetchone()
        finally:
            c.close()
    except TypeError:
        if hovedkanal and not distriktssending:
            return hentIteminfoExtra(d, hovedkanal, None)
        else:
            return []

    #For å få kompabilitet med BMS
    if digastype:
        if digastype !='Music':
            return []
    #Siden vi bare skal ha Extrainfo her
    if beskrivelse:
        item = beskrivelse
    else:
        return []
    s=[]
    #Sette sammen dls til så få linjer som mulig
    part = ''
    deler = item.split('|')
    for delen in deler:

        if part:
            if len(part) + len(delen) < 125:
                part = part + ' ' + delen
            elif len(delen) < 125:
                #Vi legger den ferdige dls fragmentet til listen
                s.append(part + '...')
                part = '...' + delen
            else:
                #Dls frqagmentet er for langt
                #Vi deler det på punktum, dersom det finnes
                if '.' in delen:
                    del1, del2 = delen.split('.', 1)
                    if len(part) + len(del1) < 125:
                        s.append(part + ' ' + del1 + '...')
                        part = '...' + del2
                    else:
                        #Vi må dytte part i listen
                        s.append(part + '...')
                        s.append('...'+ del1 + '...')
                        part = '...' + del2
                else:
                    pass
                    print("#HER SKULLE VI IKKE HA VÆRT#")
                    #eg krise
                    #Lage rutine som deler på ord
        else:

            part = delen
    #Opprydding vi må uansett legge til den siste part
    s.append(part)
    return s

def hent_news_item(d, kanal, hovedkanal, distriktssending=0):
    "Henter informasjon om innslaget som er på lufta, dersom det er et news innslag; returnerer en liste med et element."
    # Dersom vi ikke har en distriktssending, skal vi gå til hovedkanalen for metadata:
    # Slå av distrikt så lenge
    if not distriktssending:
        kanal = hovedkanal
    c = d.cursor()
    #Først må vi finne ut om vi har en samsending
    sql = """SELECT kildekanal FROM iteminfo WHERE kanal=%s AND type='programme'  AND localid = '1' LIMIT 1 ;"""
    c.execute(sql, (kanal, ))
    row =  c.fetchone()
    if row:
        kildekanal = row[0]
    else:
        kildekanal = False
    if kildekanal:
        #Da henter vi verdiene fra denne isteden
        kanal = kildekanal
    sql = """SELECT tittel,artist, beskrivelse, digastype, label FROM iteminfo WHERE kanal=%s AND type='item'  AND localid = '3' LIMIT 1 ;"""
    c.execute(sql, (kanal, ))
    try:
        try:
            tittel,artist, beskrivelse, digastype, label = c.fetchone()
        finally:
            c.close()
    except TypeError:
        if hovedkanal and not distriktssending:
            return hentIteminfo(d, hovedkanal, None)
        else:
            return []
    if digastype != 'News':
        return []
    #Vi finner opptaksdato
    c = d.cursor()
    sql = """SELECT YEAR(laget) FROM iteminfo WHERE kanal=%s AND type='item'  AND localid = '3' LIMIT 1 ;"""
    c.execute(sql, (kanal, ))
    try:
        try:
            laget, = c.fetchone()
        finally:
            c.close()
    except :
        laget = 0
    else:
        if laget<LAGET_GRENSE:
            tittel = "%s, innspilt %s," % (tittel, laget)

    if kanal in newstittel:
        if not artist:
            item = tittel
        elif artist[0] == '.':
            #Dette er en type som ikke kan bindes med verk, ved hjelp av "spiller" verbet.
            #Vi velger derfor egen annonseringstype for dette.
            try:
                item = eval(choice(newstittel[kanal+'_S']))
            except KeyError:
                #Dersom det ikke er laget egen maltype for dette faller vi tilbake på originalen
                item = eval(choice(newstittel[kanal]))
        else:
            item = eval(choice(newstittel[kanal]))
    else:
        item = eval(choice(newstittel['nrk']))
    s=[]
    #Sette sammen dls til så få linjer som mulig
    part = ''
    deler = item.split('|')
    for delen in deler:
        if part:
            if len(part) + len(delen) < 125:
                part = part + ' ' + delen
            elif len(delen) < 125:
                #Vi legger den ferdige dls fragmentet til listen
                s.append(part + '...')
                part = '...' + delen
            else:
                #Dls frqagmentet er for langt
                #Vi deler det på punktum, dersom det finnes
                
                if '.' in delen:
                    del1, del2 = delen.split('.', 1)
                    if len(part) + len(del1) < 125:
                        s.append(part + ' ' + del1 + '...')
                        part = '...' + del2
                    else:
                        #Vi må dytte part i listen
                        s.append(part + '...')
                        s.append('...'+ del1 + '...')
                        part = '...' + del2
                else:
                    pass
                    print("#HER SKULLE VI IKKE HA VÆRT#")
                    #eg krise
                    #Lage rutine som deler på ord
        else:
            part = delen
    #Opprydding vi må uansett legge til den siste part
    s.append(part)
    return s

def hent_news_info(d, kanal, hovedkanal, distriktssending=0):
    "Henter extra informasjon om nyhetsinnslag som er på lufta, returnerer en liste med et element."
    #Dersom vi ikke har en distriktssending, skal vi gå til hovedkanalen for metadata:
    distriktssending = 0
    if not distriktssending:
        kanal = hovedkanal
    c = d.cursor()
    #Først må vi finne ut om vi har en samsending
    sql = """SELECT kildekanal FROM iteminfo WHERE kanal=%s AND type='programme'  AND localid = '1' LIMIT 1 ;"""
    c.execute(sql, (kanal, ))
    row =  c.fetchone()
    if row:
        kildekanal = row[0]
    else:
        kildekanal = False
    if kildekanal:
        #Da henter vi verdiene fra denne isteden
        kanal = kildekanal

    sql = """SELECT tittel,artist, beskrivelse, digastype, label FROM iteminfo WHERE kanal=%s AND type='item'  AND localid = '3' LIMIT 1 ;"""
    
    c.execute(sql,(kanal,))
    try:
        try:
            tittel,artist, beskrivelse, digastype, label = c.fetchone()
        finally:
            c.close()
    except TypeError:
        if hovedkanal and not distriktssending:
            return hent_news_info(d,hovedkanal,None)
        return []

    if digastype !='News':
        return []
    
    #Vi finner opptaksdato
    c = d.cursor()()
    sql = """SELECT YEAR(laget) FROM iteminfo WHERE kanal=%s AND type='item'  AND localid = '3' LIMIT 1 ;"""
    c.execute(sql,(kanal,))
    try:
        try:
            laget, = c.fetchone()
        finally:
            c.close()
    except :
        laget = 0
    else:
        if laget < LAGET_GRENSE:
            tittel = "%s, innspilt %s," % (tittel,laget)

    if beskrivelse:
        item = beskrivelse
    else:
        return []

    s=[]
    #Sette sammen dls til så få linjer som mulig
    part = ''
    deler = item.split('|')
    for delen in deler:
        
        
        if part:
            if len(part) + len(delen) < 125:
                part = part + ' ' + delen
            elif len(delen) < 125:
                #Vi legger den ferdige dls fragmentet til listen
                s.append(part + '...')
                part = '...' + delen
            else:
                #Dls frqagmentet er for langt
                #Vi deler det på punktum, dersom det finnes
                
                if '.' in delen:
                    del1, del2 = delen.split('.', 1)
                    if len(part) + len(del1) < 125:
                        s.append(part + ' ' + del1 + '...')
                        part = '...' + del2
                    else:
                        #Vi må dytte part i listen
                        s.append(part + '...')
                        s.append('...'+ del1 + '...')
                        part = '...' + del2
                else:
                    pass
                    print("#HER SKULLE VI IKKE HA VÆRT#")
                    #eg krise
                    #Lage rutine som deler på ord
        else:

            part = delen
    #Opprydding vi må uansett legge til den siste part
    s.append(part)

    return s

def hent_item_next(d, kanal, hovedkanal, distriktssending=False):
    "Henter informasjon om det neste innslaget som skal på lufta, returnerer en liste med et element."
    #Dersom vi ikke har en distriktssending, skal vi gå til hovedkanalen for metadata:

    distriktssending = 0
    if not distriktssending:
        kanal = hovedkanal
    c = d.cursor()
    #Først må vi finne ut om vi har en samsending
    sql = """SELECT kildekanal FROM iteminfo WHERE kanal=%s AND type='programme'  AND localid = '1' LIMIT 1 ;"""
    c.execute(sql, (kanal,))
    row = c.fetchone()
    if row:
        kildekanal = row[0]
    else:
        kildekanal = False
    if kildekanal:
        #Da henter vi verdiene fra denne isteden
        kanal = kildekanal
    
    #Først finne ut om vi har to like titler. Dersom denne feiler har vi i alle fall ikke noen like titler.
    try:
        sql = """SELECT tittel FROM iteminfo WHERE kanal=%s AND type='item' AND (localid = '4' OR localid = '3')  LIMIT 2;"""
        c.execute(sql,(kanal,))
        
        tittel1 = c.fetchone()[0]
        tittel2 = c.fetchone()[0]
    except:
        # FIXME: Dette er tull
        tittel1 = 'x'
        tittel2 = 'y'

    #Dersom titlene er like med untak av satsbetegnelsene viser vi ingenting
    else:
        if sammenlign_tittler(tittel1, tittel2):
            return []
    
    #Ellers viser vi nesteinformasjon
    sql = """SELECT tittel, artist, digastype, tid  FROM iteminfo WHERE kanal=%s AND type='item' AND localid = '4' LIMIT 1;"""
    
    
    c.execute(sql,(kanal,))
    try:
        try:
            tittel, artist, digastype, tid = c.fetchone()
        finally:
            c.close()
    except TypeError:
        if hovedkanal and not distriktssending:
            return hent_item_next(d, hovedkanal, None)
        else:
            return []

    if type(tid)!=type(''):
        #Dette er en foreløpig patch for at en har begynt å bruke datetime objekter
        tid = tid.isoformat()
    
    ur = tid[11:16]
    
    #For å få kompabilitet med BMS
    if digastype:
        if digastype != 'Music':
            return []
    
    if kanal in nesteItemtittel:
        if not artist  and ('artist' in nesteItemtittel[kanal]):
            item = tittel

        else:
            item = eval(choice(nesteItemtittel[kanal]))
    else:
        item = eval(choice(nesteItemtittel['nrk']))
    
    s=[]
    #Sette sammen dls til så få linjer som mulig
    part = ''
    deler = item.split('|')
    for delen in deler:
        
        
        if part:
            if len(part) + len(delen) < 125:
                part = part + ' ' + delen
            elif len(delen) < 125:
                #Vi legger den ferdige dls fragmentet til listen
                s.append(part + '...')
                part = '...' + delen
            else:
                #Dls frqagmentet er for langt
                #Vi deler det på punktum, dersom det finnes
                if '.' in delen:
                    del1, del2 = delen.split('.', 1)
                    if len(part) + len(del1) < 125:
                        s.append(part + ' ' + del1 + '...')
                        part = '...' + del2
                    else:
                        #Vi må dytte part i listen
                        s.append(part + '...')
                        s.append('...'+ del1 + '...')
                        part = '...' + del2
                else:
                    pass
                    print("#HER SKULLE VI IKKE HA VÆRT#")
                    #eg krise
        else:
        
            part = delen
    #Opprydding vi må uansett legge til den siste part
    s.append(part)
    
    return s

def hent_news_item_next(d, kanal, hovedkanal, distriktssending=0):
    "Henter informasjon om det neste innslaget som skal på lufta, returnerer en liste med et element."
    #Dersom vi ikke har en distriktssending, skal vi gå til hovedkanalen for metadata:
    #******
    distriktssending = 0
    if not distriktssending:
        kanal = hovedkanal

    c = d.cursor()
    #Først må vi finne ut om vi har en samsending
    
    sql = """SELECT kildekanal FROM iteminfo WHERE kanal=%s AND type='programme'  AND localid = '1' LIMIT 1 ;"""
    c.execute(sql, (kanal,))
    row =  c.fetchone()
    if row:
        kildekanal = row[0]
    else:
        kildekanal = False
    if kildekanal:
        #Da henter vi verdiene fra denne isteden
        kanal = kildekanal
    
    #Ellers viser vi nesteinformasjon
    sql = """SELECT tittel, artist, digastype, tid FROM iteminfo WHERE kanal=%s AND type='item' AND localid = '4' LIMIT 1;"""
    
    c.execute(sql, (kanal,))
    try:
        try:
            tittel,artist, digastype, tid = c.fetchone()
        finally:
            c.close()
    except TypeError:
        if hovedkanal and not distriktssending:
            return hent_news_item_next(d, hovedkanal, None)
        return []
    
    if digastype != 'News':
        return []
    
    if type(tid)!=type(''):
        #Dette er en forelÃ¸pig patch for at en har begynt Ã¥ bruke datetime objekter
        tid = tid.isoformat()

    ur = tid[11:16]
    if kanal in nesteNewstittel:
        if not artist and ('artist' in nesteNewstittel[kanal]):
            item = tittel
        else:
            item = eval(choice(nesteNewstittel[kanal]))
    else:
        item = eval(choice(nesteNewstittel['nrk']))

    s=[]
    #Sette sammen dls til så få linjer som mulig
    part = ''
    deler = item.split('|')
    for delen in deler:
        if part:
            if len(part) + len(delen) < 125:
                part = part + ' ' + delen
            elif len(delen) < 125:
                #Vi legger den ferdige dls fragmentet til listen
                s.append(part + '...')
                part = '...' + delen
            else:
                #Dls frqagmentet er for langt
                #Vi deler det på punktum, dersom det finnes
                if '.' in delen:
                    del1, del2 = delen.split('.', 1)
                    if len(part) + len(del1) < 125:
                        s.append(part + ' ' + del1 + '...')
                        part = '...' + del2
                    else:
                        #Vi må dytte part i listen
                        s.append(part + '...')
                        s.append('...'+ del1 + '...')
                        part = '...' + del2
                else:
                    print("#HER SKULLE VI IKKE HA VÆRT#")
                    #eg krise
        else:
        
            part = delen
    #Opprydding vi må uansett legge til den siste part
    s.append(part)

    return s

def xml_entety(streng):
    "qout og amp er en kamp"
    return streng.replace('&', '&amp;').replace('"', '&quot;')

def roter(s,n):
    "Roterer en liste N plasser"
    return s[n:] + s[:n]

def bygg_dls(d, kanal, hovedkanal, har_distrikter=False):
    "Bygger opp dels - returnerer en liste"

    visningsvalg_blokk = hent_visningsvalg(d, kanal)
    for blokk in visningsvalg_blokk:
        if blokk in IKKE_DLS:
            if VERBOSE:
                print("Ikke vis som DLS på %s" % blokk)
            continue
        # Bygge opp visningslista
        # Hente visningsvalg
        visningsvalg = visningsvalg_blokk[blokk]
        if VERBOSE:
            print('Skal vises:', kanal, visningsvalg_blokk.keys())
            print("Visningsvalg:", visningsvalg)

        dls_l=[]
        #Så til tjenestegruppene
        #Vi trenger aa hente programmeinfo uansett, men vi bruker dataene bare hvis det skal vises
        programme_dls, distriktssending = hentProgrammeinfo(d, kanal, hovedkanal, har_distrikter=har_distrikter)
        if 'iteminfo' in visningsvalg:
            dls_l.extend(hentIteminfo(d, kanal, hovedkanal, distriktssending=distriktssending))
        if 'newsItem' in visningsvalg:
            dls_l.extend(hent_news_item(d, kanal, hovedkanal, distriktssending=distriktssending))
        if 'pgrinfo' in visningsvalg:
            dls_l.extend(hentPgrinfo(d, kanal, hovedkanal))
        #ProgrammeDls hentes ut ovenfor
        if 'programmeinfo' in visningsvalg:
            dls_l.extend(programme_dls)
        if 'iteminfo' in visningsvalg:
            #Musikkobjekter
            dls_l.extend(hentIteminfo(d, kanal, hovedkanal, distriktssending=distriktssending))
        if 'musicInfo' in visningsvalg:
            #Tillegsinfo om musikk
            dls_l.extend(hentIteminfoExtra(d, kanal, hovedkanal, distriktssending=distriktssending))
        if 'newsItem' in visningsvalg:
            #Andre objekter
            dls_l.extend(hent_news_item(d, kanal, hovedkanal, distriktssending=distriktssending))
        if 'newsInfo' in visningsvalg:
            #Tillegsinfo om news
            dls_l.extend(hent_news_info(d, kanal, hovedkanal, distriktssending=distriktssending))
        if 'itemNext' in visningsvalg:
            dls_l.extend(hent_item_next(d, kanal, hovedkanal))
        if 'newsItemNext' in visningsvalg:
            dls_l.extend(hent_news_item_next(d, kanal, hovedkanal))

        #Dersom det er veldig kort DLS så kan vi tvangsstyre infofeltet for ptogram
        if 'programmeinfo' in visningsvalg and len(dls_l) < 4:
            dls_l.extend(hentProgrammeinfo(d, kanal, hovedkanal, useTimeLimit=False)[0])
        if 'programmeNext' in visningsvalg:
            dls_l.extend(hentProgrammeNext(d, kanal, hovedkanal))

        return dls_l

def lagVisningstider(text, min_sec=4, max_sec=30):
    "Lager en kommaseparert liste med visningstider, slik at vi får en individuel tilpassning av dls-ene"
    #128 er max linjelengde som gir verdien max
    return str(int((len(text)) / 128.0 * max_sec + min_sec))

def til_dab(kanal='alle'):
    "Henter data for en gitt kanal ut i fra de forskjellige databasene og setter sammen til en DLS som sendes videre som et mimemultipartdokument."
    
    d = database()
    if kanal == 'alle':
        kanaler = finn_kanaler(d)
    else:
        kanaler = [kanal]

    for kanal in kanaler:
        #Det kan hende at kanalene er delt opp i distrikter - eks. p1oslo
        distriktskanaler = distriktskanal(d, kanal)
        if len(distriktskanaler) == 1:
            #Vi har kunn en kanal, distrikskanal eller kanalen selv, vi må finne moderkanalen
            hovedkanal = finnHovedkanal(d, kanal)
            har_distrikter = False
        else:
            #Vi har en kanal med barn, ergo er hovedkanalen kanalen selv.
            hovedkanal = kanal
            har_distrikter = True

        for kanal in distriktskanaler:
            # Filtrer for distriktskanaler som har egne metadata, dvs som har sending

            if hentProgrammeinfo(d, kanal, hovedkanal, har_distrikter=har_distrikter)[0][0] == 'VOID':
                if VERBOSE:
                    print("\n%s hadde egne data, ikke bruk %s\n" % (kanal, hovedkanal))
                continue
            dls_liste = bygg_dls(d, kanal, hovedkanal, har_distrikter=har_distrikter) or ['.']
            if VERBOSE:
                print(kanal)
                for linje in dls_liste:
                    print(linje)
                    print('-' * 128)
            # FIXME: må vel være en lettere måte å få et timestamp på
            start = send_til_server.isodato(time.time()) #DVS vi sender en liste som gjelder fra nå
            # Dersom vi har iteminfo er levetiden på listen lik den gjenværende tiden på det korteste innslaget
            distriktssending = True
            if distriktssending:
                levetid = minimum_levetid(d, kanal)
            else:
                levetid = minimum_levetid(d, hovedkanal)
            if levetid <= 0:
                #Vi har ingen ok tidsangivelse
                levetid = 60 * 60 * MAX_LEVETID #dvs i hele timer regnet om til sekunder

            stop = send_til_server.isodato(time.time() + levetid + 5)  #5 sekunder ofset slik at infoen heller henger enn forsvinner like før en oppdatering
            dls_liste = map(xml_entety, dls_liste)
            #Lag en kommaseparert liste over visningstider
            # FIXME: map returnerer en generator
            dataliste = map(None, dls_liste, (map(lagVisningstider, dls_liste)))
            if VERBOSE:
                print(dataliste)
            """
            for addr in ["nrkhd-ice-01.netwerk.no","nrkhd-ice-02.netwerk.no"]:
                send_til_server.send_data(
                '%s:1204' % addr,
                kanal=kanal,
                blokk='riks1',
                start=start,
                stop=stop,
                liste=dataliste
                )
            """
    #Lukke databasen
    
    d.close()

if __name__=='__main__':
    til_dab(kanal='ak')

