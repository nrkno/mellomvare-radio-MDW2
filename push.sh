#!/bin/sh

#  push til repo
#  MDW2
#
#  Created by Tormod Værvågen on 24/06/2019.
#  Copyright © 2019 Tormod Værvågen. All rights reserved.

#Loggge på
az acr login --subscription Drift --name plattform


docker push plattform.azurecr.io/mdw2/mdw2:test
