# -*- coding: utf-8 -*-
"Dette er en hjelpefil for annonseringer i de forskjellige kanalene"

spiller = ['spiller', 'fremfører']
spilles = ['spilles av', 'fremføres av']
spilt_av = ['med', 'fremført av']
lytter = ['Du hører ', 'Du lytter til ', 'Nå: ']
neste_lytter = ['Så får du høre ']

# | gir ny linje dersom det trengs, ellers vil det fremstå som et ordskille.

# Tilgjengelige variabler : tittel,artist, beskrivelse, digastype, label

# NRK kanalen er en kanal som brukes dersom kanalnavnet er ukjent

# itemtittel brukes for musikkinslag

itemtittel = {'nrk':["<tittel> med <artist>"],
		'ak':["Nå: <tittel> |fremført av <artist>"],
		'mpetre':["<artist> med <tittel>"],
		'ev1':["<tittel> <artist>"],
		'ev2':["<tittel> <artist>"],
		}

# newstittel brukes for news innslag fra Digas
# Hvis man ikke vil ha med artistfeltet i en kanal, bruk '<kanalnavn>':["tittel"]
newstittel =  {'nrk':["<tittel>. |<artist>"],
		'barn':["<tittel>"],
		'gull':["<tittel>"],
			}

# NRK kanalen er en kanal som brukes dersom kanalnavnet er ukjent
nesteItemtittel = {'nrk':["Neste: <tittel> med <artist>"],
		'p3':["Snart: <tittel + ', ' + artist"],
		'ak':["Neste: <tittel>"],
		'ev1':["Neste: <tittel>"],
        'ev2':["Neste: <tittel>"],
		}

# brukes for news innslag fra Digas
nesteNewstittel =  {'nrk':["Neste: <tittel>.|'<artist>"],
            'barn':["Neste: <tittel>"],
		    'ev1':["Neste: <tittel>"],
            'ev2':["Neste: <tittel>"],
			}
