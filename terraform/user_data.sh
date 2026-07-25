#!/bin/bash
set -e

# Update system
apt-get update -y

# Install k3s (lightweight Kubernetes distro - fits in 1GB RAM t2.micro)
curl -sfL https://get.k3s.io | sh -s - --write-kubeconfig-mode 644

# Wait for k3s to be ready
until kubectl get nodes; do
  sleep 5
done

# Install Helm (needed for Prometheus/Grafana stack later)
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Create namespace for our app
kubectl create namespace autopilot-ops || true

echo "k3s bootstrap complete" > /var/log/bootstrap-complete.log
