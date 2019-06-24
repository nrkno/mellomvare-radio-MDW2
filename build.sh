#!/bin/sh

#  build.sh
#  MDW2
#
#  Created by Tormod Værvågen on 24/06/2019.
#  Copyright © 2019 Tormod Værvågen. All rights reserved.

BASEDIR=$(pwd)
IMAGE_TAG=${1:-test}
IMAGE_NAME=plattform.azurecr.io/mdw2/mdw2
IMAGE_TITLE="Metadata DAB Web"

echo "Building Docker image $IMAGE_TITLE ($IMAGE_ID) from $BASEDIR."

docker build -t "$IMAGE_NAME:$IMAGE_TAG" "$BASEDIR" --no-cache|| exit 1
