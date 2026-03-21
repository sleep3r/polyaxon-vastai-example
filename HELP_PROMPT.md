# containerd крашится при старте k3s на Vast.ai KVM

## Контекст

Разворачиваю Polyaxon CE на Vast.ai KVM инстансе (RTX 4070 Ti SUPER). Скрипт setup.sh запускается через cloud-init on-start, устанавливает k3s + helm + polyaxon.

**Проблема:** k3s крашится в цикле — containerd падает с `exit status 1`.

## Критичные строки из логов

```
level=info msg="Found nvidia container runtime at /usr/bin/nvidia-container-runtime"
level=info msg="Using containerd config template at /var/lib/rancher/k3s/agent/etc/containerd/config.toml.tmpl"
level=info msg="Running containerd -c /var/lib/rancher/k3s/agent/etc/containerd/config.toml ..."
level=error msg="Sending HTTP/1.1 503 response to 127.0.0.1:...: runtime core not ready"
level=error msg="Shutdown request received: containerd exited: exit status 1"
systemd[1]: k3s.service: Failed with result 'protocol'.
```

k3s перезапускается каждые ~8 сек, счётчик рестартов: 10, 11, 12, 13...

## Что именно мы сделали

Изначально мы создавали файл `/var/lib/rancher/k3s/agent/etc/containerd/config.toml.tmpl` с содержимым:

```toml
{{ template "base" . }}

[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia]
  privileged_without_host_devices = false
  runtime_type = "io.containerd.runc.v2"
[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia.options]
  BinaryName = "/usr/bin/nvidia-container-runtime"
```

Этот файл ломал containerd (exit status 1).

## Что мы уже знаем

1. k3s v1.34.5 — **сам определяет** nvidia runtime: `Found nvidia container runtime at /usr/bin/nvidia-container-runtime`
2. Значит наш `config.toml.tmpl` НЕ НУЖЕН — k3s автоматически настроит nvidia
3. Мы уже удалили создание этого файла из setup.sh и запушили в GitHub

## Текущий setup.sh (после фикса)

```bash
#!/bin/bash
exec &>/var/log/polyaxon.log
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
echo 'export KUBECONFIG=/etc/rancher/k3s/k3s.yaml'>>/root/.bashrc

# Wait for unattended-upgrades to finish (first boot race condition)
while fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1 || fuser /var/lib/dpkg/lock >/dev/null 2>&1; do
  echo "Waiting for apt lock..."
  sleep 5
done

apt-get update -qq && apt-get install -y -qq socat

# k3s v1.34+ auto-detects nvidia-container-runtime, no config needed

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
```

## Вопросы

1. **Правильно ли наше решение?** Удалить `config.toml.tmpl` и доверить k3s v1.34 автоопределение nvidia runtime — это корректный подход?

2. **Что именно ломалось?** Почему `{{ template "base" . }}` + nvidia runtime секция вызывала `containerd exited: exit status 1`? Это проблема синтаксиса Go-шаблона, несовместимость с containerd 2.x, или что-то другое?

3. **На текущем инстансе** (где уже есть сломанный `config.toml.tmpl`) — достаточно ли просто удалить файл и перезапустить k3s? Или нужно ещё что-то?

```bash
rm -f /var/lib/rancher/k3s/agent/etc/containerd/config.toml.tmpl
systemctl restart k3s
```

4. **GPU в k8s подах.** k3s v1.34 автоматически обнаруживает nvidia runtime. Но будет ли GPU доступна внутри k8s подов? Нужен ли отдельно NVIDIA device plugin (`nvidia-device-plugin.yml`) для того чтобы `nvidia.com/gpu` ресурс появился в node capacity?

5. **Есть ли необходимость делать nvidia runtime дефолтным** (через `--default-runtime=nvidia` или `default_runtime_name = "nvidia"` в containerd config)? Или достаточно указать `nvidia.com/gpu: 1` в ресурсах пода и k8s сам использует nvidia runtime?

## Среда

- Vast.ai KVM instance
- Ubuntu 22.04
- NVIDIA GeForce RTX 4070 Ti SUPER
- k3s v1.34.5+k3s1
- nvidia-container-runtime уже установлен на хосте
