# 🚀 Polyaxon CE on Vast.ai

Run ML training jobs and Jupyter notebooks on cheap GPU instances using [Polyaxon CE](https://polyaxon.com/) + [Vast.ai](https://vast.ai/).

> One-click setup: k3s → Polyaxon → GPU-enabled training — all automated.

## Quick Start

### 1. Create a Vast.ai Instance

Use the KVM template with this **on-start script**:

```bash
curl -sL https://raw.githubusercontent.com/sleep3r/polyaxon-vastai-example/main/setup.sh | bash
```

| Parameter | Value |
|-----------|-------|
| **Image** | `docker.io/vastai/kvm:ubuntu_desktop_22.04-2025-11-21` |
| **Disk** | 100 GB |
| **Ports** | `1111, 8000` |

<details>
<summary>📋 Full template settings</summary>

| Field | Value |
|-------|-------|
| OPEN_BUTTON_TOKEN | `1` |
| OPEN_BUTTON_PORT | `1111` |
| PORTAL_CONFIG | `localhost:1111:11111:/:Portal\|localhost:8000:18000:/:Polyaxon` |

</details>

### 2. Configure Local CLI

```bash
# Install dependencies
uv sync

# Copy and edit .env
cp .env.example .env
# Set POLYAXON_HOST to your Cloudflare tunnel URL or instance IP
```

### 3. Run Training

```bash
make run        # Upload code + launch training job
make logs       # Stream logs
make status     # List all runs
```

### 4. Launch Jupyter Notebook

```bash
make notebook   # Start GPU-enabled Jupyter notebook
```

## Project Structure

```
├── setup.sh            # Vast.ai on-start: k3s + Polyaxon + GPU
├── vastai_template.sh  # Template documentation
├── polyaxonfile.yaml   # Training job definition
├── notebook.yaml       # Jupyter notebook definition
├── mnist_train.py      # Example training script (MNIST)
├── Makefile             # CLI shortcuts
├── .env.example        # Environment template
└── .polyaxonignore      # Upload exclusions
```

## How It Works

```
Local Machine                    Vast.ai KVM Instance
┌─────────────┐    Cloudflare    ┌──────────────────────┐
│ polyaxon CLI │───── tunnel ────▶│ Caddy → socat:18000  │
│ make run -u  │    (HTTPS)      │   ↓                  │
└─────────────┘                  │ k3s + Polyaxon CE     │
                                 │   ↓                  │
                                 │ Job Pod (GPU) 🔥     │
                                 │   pytorch/pytorch     │
                                 └──────────────────────┘
```

## Key Design Decisions

- **`perCore: false`** — Prevents Polyaxon from spawning workers per CPU core (crucial for 64+ core machines)
- **`limitResources: false`** — Disables hardcoded 8GB memory limits from the Helm chart
- **nvidia runtime** — Configured before k3s start so containerd can pass GPUs to pods
- **socat port-forward** — Persistent systemd service instead of flaky `kubectl port-forward`

## Commands

| Command | Description |
|---------|-------------|
| `make check` | Verify connection to Polyaxon server |
| `make init` | Create project on server |
| `make run` | Upload code & launch training |
| `make notebook` | Start Jupyter notebook with GPU |
| `make logs` | Stream run logs |
| `make status` | List runs |
| `make dashboard` | Open Polyaxon UI |

## License

MIT
