# -*- coding: utf-8 -*-
"Dette er en hjelpefil for annonseringer i de forskjellige kanalene"

spiller = ['spiller', 'fremf¿rer']
spilles = ['spilles av', 'fremf¿res av']
spiltAv = ['med', 'fremf¿rt av']
lytter = ['Du h¿rer ', 'Du lytter til ', 'NŒ: ']
nesteLytter = ['SŒ fŒr du h¿re ']

# | gir ny linje dersom det trengs, ellers vil det fremstå som et ordskille.

# Tilgjengelige variabler : tittel,artist, beskrivelse, digastype, label og for neste ogsaa ur

#NRK kanalen er en kanal som brukes dersom kanalnavnet er ukjent
#_S kanalene er tilbruk der man har "solister"
#itemtittel brukes for musikkinslag
itemtittel = {'nrk':["tittel + ' med ' + artist"],
		'p1':["tittel + ' med ' + artist","artist + ' med ' + tittel"],
		'p2':["tittel + ' med ' + artist"],
		'p3':["artist + ' med ' + tittel"],
		'fmk':["tittel + ' med ' + artist"],
		'p1of':["tittel + ' med ' + artist"],
		'ak':["'NŒ: '+ tittel + '|fremf¿rt av ' + artist"],
		'mpetre':["artist + ' med ' + tittel"],
		'ev1':["tittel + ' ' + artist"],
		'ev2':["tittel + ' ' + artist"],
		}

#newstittel brukes for news innslag fra Digas
#Hvis man ikke vil ha med artistfeltet i en kanal, bruk '<kanalnavn>':["tittel"]
newstittel =  {'nrk':["tittel + '.|' + artist"],
		'p1':["tittel + ',|ved ' + artist"],
		'nrk_5_1':["tittel"],
		'barn':["tittel"],
		'gull':["tittel"],
			}

#NRK kanalen er en kanal som brukes dersom kanalnavnet er ukjent
nesteItemtittel = {'nrk':["'Neste blir ' + tittel + ' med ' + artist"],
		'p1':["'Neste: ' + tittel + ' med ' + artist"],
		'p2':["'Neste: ' + tittel + ' med ' + artist"],
		'p3':["'Snart: '+ tittel + ', ' + artist"],
		'ak':["'Neste: ' + tittel"],
		'mpetre':["'Neste blir ' + tittel + ' med ' + artist"],
		'ev1':["'Neste: ' + tittel"],
                'ev2':["'Neste: ' + tittel"],
		'p5oslo':["'P5 snart:' + artist + '-' + tittel"],
                'p5stavanger':["'P5 snart:' + artist + '-' + tittel"],
                'p5trondheim':["'P5 snart:' + artist + '-' + tittel"],
                'p5bergen':["'P5 snart:' + artist + '-' + tittel"],
		}

#brukes for news innslag fra Digas
nesteNewstittel =  {'nrk':["'Neste: ' + tittel + '.|' + artist"],
	        'nrk_5_1':["'Neste: ' + tittel"],
            'barn':["'Neste: ' + tittel"],
		    'gull':["ur + ': ' + tittel"],
		    'ev1':["'Neste: ' + tittel"],
            'ev2':["'Neste: ' + tittel"],

			}
