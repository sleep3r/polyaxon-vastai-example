#!/bin/bash
# Polyaxon CE on k3s — on-start script for Vast.ai KVM instances
# Fetched via: curl -sL https://raw.githubusercontent.com/sleep3r/polyaxon-vastai-example/main/setup.sh | bash
exec &>/var/log/polyaxon.log
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
echo 'export KUBECONFIG=/etc/rancher/k3s/k3s.yaml'>>/root/.bashrc

apt-get update -qq && apt-get install -y -qq socat

# Configure nvidia runtime for k3s containerd (BEFORE k3s start)
mkdir -p /var/lib/rancher/k3s/agent/etc/containerd
cat > /var/lib/rancher/k3s/agent/etc/containerd/config.toml.tmpl << 'NVEOF'
[plugins."io.containerd.grpc.v1.cri".containerd]
  default_runtime_name = "nvidia"
[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia]
  privileged_without_host_devices = false
  runtime_type = "io.containerd.runc.v2"
[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia.options]
  BinaryName = "/usr/bin/nvidia-container-runtime"
NVEOF

# Install k3s (skip if already installed)
command -v k3s || {
  curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="--disable=traefik" sh -
  until kubectl get nodes &>/dev/null; do sleep 2; done
  kubectl wait --for=condition=Ready node --all --timeout=120s
}

# Install helm
command -v helm || curl -sfL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Install NVIDIA device plugin for GPU support
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.1/nvidia-device-plugin.yml

# Prepare artifacts directory
mkdir -p /data/artifacts && chmod 777 /data/artifacts

# Install Polyaxon CE (only on first run)
if ! kubectl get ns polyaxon &>/dev/null; then
  kubectl create ns polyaxon
  helm repo add polyaxon https://charts.polyaxon.com && helm repo update

  # PV/PVC for artifacts store
  cat > /tmp/pv.yaml << EOF
apiVersion: v1
kind: PersistentVolume
metadata:
  name: polyaxon-pv
spec:
  capacity:
    storage: 50Gi
  accessModes: [ReadWriteMany]
  storageClassName: ""
  hostPath:
    path: /data/artifacts
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: polyaxon-pvc
  namespace: polyaxon
spec:
  accessModes: [ReadWriteMany]
  storageClassName: ""
  volumeName: polyaxon-pv
  resources:
    requests:
      storage: 50Gi
EOF
  kubectl apply -f /tmp/pv.yaml

  # Helm values — perCore:false prevents OOM on many-core machines
  cat > /tmp/vals.yaml << EOF
limitResources: false
api:
  perCore: false
  concurrency: 4
gateway:
  perCore: false
  concurrency: 4
streams:
  perCore: false
  concurrency: 4
worker:
  perCore: false
  concurrency: 4
scheduler:
  perCore: false
  concurrency: 2
artifactsStore:
  name: default-artifacts-store
  kind: volume_claim
  schema:
    volumeClaim: polyaxon-pvc
    mountPath: /artifacts
EOF
  helm install polyaxon polyaxon/polyaxon -n polyaxon -f /tmp/vals.yaml --wait --timeout 300s
fi

# Port forward: socat maps host:18000 -> gateway:80
GW=$(kubectl get svc -n polyaxon polyaxon-polyaxon-gateway -o jsonpath='{.spec.clusterIP}')
cat > /etc/systemd/system/polyaxon-fwd.service << EOF
[Unit]
After=network.target
[Service]
ExecStart=/usr/bin/socat TCP-LISTEN:18000,fork,reuseaddr TCP:${GW}:80
Restart=always
RestartSec=3
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload && systemctl enable --now polyaxon-fwd

echo "Polyaxon ready — GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null || echo 'none')"
