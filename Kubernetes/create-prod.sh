#!/bin/sh
namespace=${1:-mdw-prod}
echo Using namespace $namespace
kubectl create -f secret.yaml -n $namespace
kubectl create -f deployment.yaml -n $namespace
kubectl create -f service.yaml -n $namespace
kubectl create -f ingress.yaml -n $namespace
