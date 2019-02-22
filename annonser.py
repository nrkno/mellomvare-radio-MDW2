# -*- coding: utf-8 -*-
"Dette er en hjelpefil for annonseringer i de forskjellige kanalene"

spiller = ['spiller', 'fremf¿rer']
spilles = ['spilles av', 'fremf¿res av']
spilt_av = ['med', 'fremf¿rt av']
lytter = ['Du h¿rer ', 'Du lytter til ', 'NŒ: ']
neste_lytter = ['SŒ fŒr du h¿re ']

# | gir ny linje dersom det trengs, ellers vil det fremstŒ som et ordskille.

# Tilgjengelige variabler : tittel,artist, beskrivelse, digastype, label

# NRK kanalen er en kanal som brukes dersom kanalnavnet er ukjent
#_ S kanalene er tilbruk der man har "solister"
# itemtittel brukes for musikkinslag

itemtittel = {'nrk':["<tittel> med <artist>"],
		'ak':["NŒ: <tittel> |fremf¿rt av <artist>"],
		'mpetre':["<artist> med <tittel>"],
		'ev1':["<tittel> <artist>"],
		'ev2':["<tittel> <artist>"],
		}

# newstittel brukes for news innslag fra Digas
#H vis man ikke vil ha med artistfeltet i en kanal, bruk '<kanalnavn>':["tittel"]
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
