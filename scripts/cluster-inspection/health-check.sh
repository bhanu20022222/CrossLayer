#!/bin/bash
# CrossLayer - Health Check Script
# Quick verification of CrossLayer deployment health

set -e

echo "CrossLayer Health Check - $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "============================================================="

# Check namespaces
echo -e "\n[1/6] Checking CrossLayer namespaces..."
microk8s kubectl get namespaces | grep crosslayer

# Check pods
echo -e "\n[2/6] Checking CrossLayer pods..."
microk8s kubectl get pods -n crosslayer-workloads -o wide

# Check services
echo -e "\n[3/6] Checking CrossLayer services..."
microk8s kubectl get svc -n crosslayer-workloads

# Check endpoints
echo -e "\n[4/6] Checking service endpoints..."
microk8s kubectl get endpoints -n crosslayer-workloads

# Health check via service
echo -e "\n[5/6] Testing health endpoint..."
microk8s kubectl run health-check --rm -it --restart=Never \
  --image=curlimages/curl -- \
  curl -s http://document-retrieval.crosslayer-workloads.svc.cluster.local/health 2>/dev/null || echo "Health check failed"

# Placement check
echo -e "\n[6/6] Testing placement endpoint..."
microk8s kubectl run placement-check --rm -it --restart=Never \
  --image=curlimages/curl -- \
  curl -s http://document-retrieval.crosslayer-workloads.svc.cluster.local/api/placement 2>/dev/null || echo "Placement check failed"

echo -e "\n============================================================="
echo "Health check complete."
