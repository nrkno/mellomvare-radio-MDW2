#!/bin/sh
namespace=${1:-mdw-test}
echo Using namespace $namespace
kubectl create -f deployment.yaml -n $namespace
kubectl create -f service.yaml -n $namespace
