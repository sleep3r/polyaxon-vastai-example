# Polyaxon CE Training Server (VM)

> **[► Create an Instance](https://cloud.vast.ai/?ref_id=62897&creator_id=62897&name=Polyaxon%20CE%20Training%20Server)**

## What is this template?

This template gives you a **fully automated ML training platform** with Polyaxon CE running on a lightweight Kubernetes cluster (k3s). GPU support, experiment tracking, model versioning, and Jupyter notebooks — all set up automatically on first boot. Access the Polyaxon dashboard through your browser, or connect via SSH.

**Think:** *"Your own private MLOps platform with GPU training, experiment tracking, and notebooks — deployed in 5 minutes on a cheap cloud GPU."*

> **Note:** This is a full virtual machine with KDE desktop environment. Polyaxon CE is installed via k3s (lightweight Kubernetes) and is accessible through the Instance Portal. The desktop can also be used for interactive work via VNC/browser.

---

## What can I do with this?

- **Run ML training jobs** with full GPU acceleration and automatic experiment tracking
- **Track experiments** — hyperparameters, metrics, model checkpoints, confusion matrices
- **Launch Jupyter notebooks** with GPU support directly from Polyaxon
- **Compare runs** — side-by-side metric charts, parameter diffs in the Polyaxon UI
- **Version models** — automatic checkpointing and artifact storage
- **Parameterized runs** — override hyperparameters from CLI without changing code
- **Full desktop environment** — KDE Plasma accessible via browser for interactive work

---

## Who is this for?

This is **perfect** if you:
- Want a private ML platform without the complexity of managed cloud MLOps services
- Need GPU training with proper experiment tracking (not just terminal output)
- Are training PyTorch/TensorFlow models and want to compare runs visually
- Want Jupyter notebooks with GPU access alongside managed training jobs
- Need model versioning and artifact storage for reproducibility
- Are a team or solo researcher looking for a self-hosted alternative to W&B/MLflow

---

## Quick Start Guide

### **Step 1: Launch Your Instance**
Click the **[Rent](https://cloud.vast.ai/?ref_id=62897&creator_id=62897&name=Polyaxon%20CE%20Training%20Server)** button when you've found a GPU instance that works for you.

Setup takes ~5 minutes. Monitor progress via SSH:
```bash
tail -f /var/log/polyaxon.log
```

### **Step 2: Access Polyaxon**
- **Via Instance Portal:** Click the **"Open"** button → select **Polyaxon** from the portal
- **Via direct URL:** Navigate to `http://instance_ip:18000`
- **Via SSH:** Connect with `ssh -p mapped_port root@instance_ip`

> **💡 Tip:** The Instance Portal provides easy access to the Polyaxon dashboard alongside the desktop environment viewers.

### **Step 3: Configure Your Local CLI**

On your local machine:
```bash
pip install polyaxon

# Configure connection (use your instance IP or Cloudflare tunnel URL)
export POLYAXON_HOST=http://<INSTANCE_IP>:18000

# Get your auth token from the Polyaxon UI (Settings → User tokens)
polyaxon config set --host=$POLYAXON_HOST
```

### **Step 4: Run Your First Experiment**

Clone the example repository:
```bash
git clone https://github.com/sleep3r/polyaxon-vastai-example.git
cd polyaxon-vastai-example

# Create a project
polyaxon project create --name mnist-test

# Upload code & launch GPU training
polyaxon run -f infra/polyaxonfile.yaml -u -p mnist-test
```

### **Step 5: Monitor & Compare**
- Open the Polyaxon dashboard to see live metrics
- Check the **Metrics** tab for loss/accuracy curves
- View **Artifacts** for saved model checkpoints
- Use **Inputs** tab to see hyperparameters for each run

---

## Key Features

### **Automated Setup**
- **k3s Kubernetes** cluster installed and configured automatically
- **NVIDIA GPU support** with device plugin and default nvidia runtime
- **Polyaxon CE** deployed via Helm with optimized configuration
- **Persistent storage** for artifacts and model checkpoints
- **Port forwarding** via systemd service (reliable, survives reboots)

### **Experiment Tracking**
| Feature | Description |
| ------- | ----------- |
| **Hyperparameters** | All inputs logged and visible in UI |
| **Metrics** | Loss, accuracy, custom metrics with step-based charts |
| **Model Versioning** | Best checkpoints saved and versioned automatically |
| **Confusion Matrix** | Visual confusion matrix in dashboard |
| **Progress Bar** | Real-time training progress in Polyaxon UI |
| **Run Comparison** | Side-by-side charts and parameter diffs |

### **Parameterized Runs**
Override any hyperparameter without changing code:
```bash
# Quick test
polyaxon run -f infra/polyaxonfile.yaml -u -P epochs=2

# Full training with custom params
polyaxon run -f infra/polyaxonfile.yaml -u -P epochs=15 -P lr=0.0005 -P hidden_size=256
```

### **Jupyter Notebooks**
Launch GPU-enabled notebooks directly from Polyaxon:
```bash
polyaxon run -f infra/notebook.yaml -p your-project
```

### **Desktop Environment**
| Method | Best For | Port |
| ------ | -------- | ---- |
| **Instance Portal** | Easy browser access | 1111 |
| **Selkies WebRTC** | Low-latency desktop | 6100 |
| **Guacamole** | Universal browser access | 6200 |
| **VNC Client** | Native desktop apps | 5900 |
| **SSH** | Terminal access | 22 |

### **Networking**
- **Cloudflare tunnels** for instant HTTPS access without port forwarding
- **Tailscale** for private networking (run `sudo tailscale up`)
- **Instance Portal** for tunnel management and service dashboard

---

## Architecture

```
┌─────────────────────────────────────────────┐
│           Vast.ai KVM Instance              │
│                                             │
│  ┌────────────────────────────────────────┐  │
│  │  k3s (Lightweight Kubernetes)          │  │
│  │                                        │  │
│  │  ┌──────────────┐  ┌───────────────┐   │  │
│  │  │ Polyaxon CE  │  │ NVIDIA Device │   │  │
│  │  │  API/Gateway │  │    Plugin     │   │  │
│  │  └──────┬───────┘  └───────────────┘   │  │
│  │         │                              │  │
│  │  ┌──────▼───────┐  ┌───────────────┐   │  │
│  │  │ Training Pod │  │ Notebook Pod  │   │  │
│  │  │  (GPU) 🔥    │  │  (GPU) 📓    │   │  │
│  │  └──────────────┘  └───────────────┘   │  │
│  └────────────────────────────────────────┘  │
│                                             │
│  socat :18000 → Gateway    KDE Desktop      │
└─────────────────────────────────────────────┘
```

---

## Configuration

### **What's Pre-configured**
- k3s with `--default-runtime=nvidia` (all pods get GPU access automatically)
- Polyaxon CE with `perCore: false` (prevents OOM on many-core machines)
- `limitResources: false` (disables hardcoded memory limits)
- Persistent volume at `/data/artifacts` for model storage
- socat port-forward as systemd service (reliable, auto-restarts)

### **Environment Variables**
| Variable | Default | Description |
| -------- | ------- | ----------- |
| `OPEN_BUTTON_TOKEN` | `1` | Portal authentication token |
| `OPEN_BUTTON_PORT` | `1111` | Instance Portal port |
| `PORTAL_CONFIG` | *(see below)* | Service routing configuration |

### **Port Configuration**
| Port | Service |
| ---- | ------- |
| 1111 | Instance Portal |
| 3478/udp | TURN server (WebRTC) |
| 5900 | VNC |
| 6100 | Selkies WebRTC desktop |
| 6200 | Guacamole desktop |
| 8000 (→18000) | Polyaxon dashboard |

---

## Example Project

This template comes with a ready-to-use example: **MNIST training with PyTorch**.

📦 **Repository:** [sleep3r/polyaxon-vastai-example](https://github.com/sleep3r/polyaxon-vastai-example)

```
├── train.py              # Training with full Polyaxon tracking
├── configs/
│   └── experiment.yaml         # Hyperparameters (model, training, data)
├── infra/
│   ├── setup.sh                # This template's on-start script
│   ├── polyaxonfile.yaml       # Job definition (image, GPU, inputs)
│   └── notebook.yaml           # Jupyter notebook service
└── Makefile                    # CLI shortcuts (make run, make logs, etc.)
```

The training script demonstrates:
- YAML config loading with CLI overrides
- `tracking.log_inputs()` — hyperparameters in UI
- `tracking.log_metrics(step=)` — loss/accuracy charts
- `tracking.log_model()` — best checkpoint versioning
- `tracking.log_confusion_matrix()` — visual matrix
- `tracking.log_progress()` — progress bar in dashboard

---

## Important Notes

### **Setup Time**
- Full setup takes **~5 minutes** on first boot
- Includes: k3s install, Helm chart deployment, NVIDIA plugin, port forwarding
- Monitor with: `tail -f /var/log/polyaxon.log`
- Last line when ready: `Polyaxon ready — GPU: <your GPU model>`

### **Authentication**
- **Desktop:** Username `user`, password `password`
- **Instance Portal:** Automatic via "Open" button
- **Polyaxon:** Create user tokens in Settings → User tokens
- **VNC password:** Same as `OPEN_BUTTON_TOKEN` unless `VNC_PASSWORD` is set

### **GPU Support**
- NVIDIA drivers are pre-installed in the VM image
- k3s auto-detects `nvidia-container-runtime`
- `--default-runtime=nvidia` ensures all pods get GPU access
- NVIDIA device plugin registers `nvidia.com/gpu` resource for scheduling

### **Storage**
- Artifacts stored at `/data/artifacts` (50 GB PersistentVolume)
- Model checkpoints persisted across training runs
- Notebooks stored in the artifacts directory

---

## Troubleshooting

### **Polyaxon not accessible?**
```bash
# Check if all pods are running
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
kubectl get pods -n polyaxon

# Check port forward
systemctl status polyaxon-fwd

# Restart if needed
systemctl restart polyaxon-fwd
```

### **GPU not detected in pods?**
```bash
# Verify GPU is visible to k8s
kubectl describe node | grep nvidia.com/gpu

# Check device plugin
kubectl get pods -n kube-system | grep nvidia
```

### **k3s service issues?**
```bash
# Check k3s status
systemctl status k3s

# View k3s logs
journalctl -u k3s -f
```

---

## Need More Help?

- **Polyaxon Documentation:** [polyaxon.com/docs](https://polyaxon.com/docs/)
- **Example Repository:** [sleep3r/polyaxon-vastai-example](https://github.com/sleep3r/polyaxon-vastai-example)
- **Polyaxon Tracking API:** [Tracking Module](https://polyaxon.com/docs/experimentation/tracking/module/)
- **k3s Documentation:** [k3s.io](https://k3s.io/)
- **Vast.ai SSH Setup:** [SSH Documentation](https://docs.vast.ai/instances/sshscp)
- **Support:** Use the messaging icon in the Vast.ai console

---

updated 2026-03-23 22:00
