#!/bin/sh
namespace=${1:-mdw-test}
echo Using namespace $namespace
kubectl apply -f deployment.yaml -n $namespace
