# -*- coding: utf-8 -*-
"Dette er en hjelpefil for roller"
ROLLERELASJON = {'sanger':2,'stryker':1,'treblåser':1,'messingblåsere':1,'tangent':1}
#Her må alle grupper inn

#Instrumenter som ikke er roller
IKKE_ROLLE = ['engelsk horn','fortepiano', 'hammerklaver']

ROLLELISTE = {
	#Sangere
	'sopran':{'gruppe':'sanger','tittel':'sopranen','aktiv':'synger','passiv':'synger'},
	'mezzosopran':{'gruppe':'sanger','tittel':'mezzosopranen','aktiv':'synger','passiv':'synger'},
	'alt':{'gruppe':'sanger','tittel':'alten','aktiv':'synger','passiv':'synger'},
	'tenor':{'gruppe':'sanger','tittel':'tenoren','aktiv':'synger','passiv':'synger'},
	'baryton':{'gruppe':'sanger','tittel':'barytonen','aktiv':'synger','passiv':'synger'},
	'bass':{'gruppe':'sanger','tittel':'bassen','aktiv':'synger','passiv':'synger'},
	#Ting med tangenter
	'piano':{'gruppe':'tangent','tittel':'pianisten','aktiv':'spiller','passiv':'akkompagnert av'},
	'fortepiano':{'gruppe':'tangent','tittel':'pianisten','aktiv':'spiller','passiv':'akkompagnert av'},
	'hammerklaver':{'gruppe':'tangent','tittel':'pianisten','aktiv':'spiller','passiv':'akkompagnert av'},
	'klaver':{'gruppe':'tangent','tittel':'pianisten','aktiv':'spiller','passiv':'akkompagnert av'},
	'cembalo':{'gruppe':'tangent','tittel':'cembalisten','aktiv':'spiller','passiv':'akkompagnert av'},
	#Strykere
	'fiolin':{'gruppe':'stryker','tittel':'fiolinisten','aktiv':'spiller','passiv':'akkompagnert av'},
	'bratsj':{'gruppe':'stryker','tittel':'bratsjisten','aktiv':'spiller','passiv':'akkompagnert av'},
	'cello':{'gruppe':'stryker','tittel':'cellisten','aktiv':'spiller','passiv':'akkompagnert av'},
	'kontrabass':{'gruppe':'stryker','tittel':'bassisten','aktiv':'spiller','passiv':'akkompagnert av'},
	#Treblåsere
	'klarinett':{'gruppe':'treblåser','tittel':'klarinettisten','aktiv':'spiller','passiv':'akkompagnert av'},
	'bassklarinett':{'gruppe':'treblåser','tittel':'bassklarinettisten','aktiv':'spiller','passiv':'akkompagnert av'},
	'klarinett':{'gruppe':'treblåser','tittel':'klarinettisten','aktiv':'spiller','passiv':'akkompagnert av'},
	'fagott':{'gruppe':'treblåser','tittel':'fagottisten','aktiv':'spiller','passiv':'akkompagnert av'},
	'fløyte':{'gruppe':'treblåser','tittel':'fløytisten','aktiv':'spiller','passiv':'akkompagnert av'},
	'engelsk horn':{'gruppe':'treblåser','tittel':'oboisten','aktiv':'spiller','passiv':'akkompagnert av'},
	'obo':{'gruppe':'treblåser','tittel':'oboisten','aktiv':'spiller','passiv':'akkompagnert av'},
	#Messingblåsere
	'horn':{'gruppe':'messingblåser','tittel':'hornisten','aktiv':'spiller','passiv':'akkompagnert av'},
	'trompet':{'gruppe':'messingblåser','tittel':'trompetisten','aktiv':'spiller','passiv':'akkompagnert av'},
	}
