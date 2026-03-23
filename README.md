# 🚀 Polyaxon CE on Vast.ai

Run ML experiments on cheap GPU instances with full tracking, model versioning, and notebooks — powered by [Polyaxon CE](https://polyaxon.com/) + [Vast.ai](https://vast.ai/).

> One-click setup: k3s → Polyaxon → GPU training — all automated via a public Vast.ai template.

## Quick Start

### 1. Create a Vast.ai Instance

Search for the public template **`Polyaxon CE Training Server`** on [Vast.ai Templates](https://cloud.vast.ai/templates/), or create a KVM instance manually with this **on-start script** (3 строки):

```bash
#!/bin/bash
source /etc/environment
curl -sL https://raw.githubusercontent.com/sleep3r/polyaxon-vastai-example/main/infra/setup.sh | bash
```

<details>
<summary>📋 Manual template settings</summary>

| Field | Value |
| ----- | ----- |
| **Image** | `docker.io/vastai/kvm:ubuntu_desktop_22.04-2025-11-21` |
| **Disk** | 100 GB |
| **Ports** | `1111, 3478/udp, 5900, 6100, 6200, 8000` |
| OPEN_BUTTON_TOKEN | `1` |
| OPEN_BUTTON_PORT | `1111` |
| PORTAL_CONFIG | `localhost:1111:11111:/:Portal\|localhost:8000:18000:/:Polyaxon` |

> ⚠️ On-start script **must** start with `#!/bin/bash` — KVM instances use cloud-init, not Docker.

</details>

Wait ~5 min for setup to finish. Check progress: `tail -f /var/log/polyaxon.log`

### 2. Configure Local CLI

```bash
uv sync                     # Install dependencies
cp .env.example .env        # Copy env template
# Edit .env → set POLYAXON_HOST and token
```

### 3. Run Experiments

```bash
make init                   # Create project on server
make run                    # Train (5 epochs, default config)
make run-fast               # Quick test (2 epochs)
make run-full               # Full training (15 epochs, lower lr)
make sweep                  # Hyperparameter search (12 random runs)
make pipeline               # DAG: prepare → train → evaluate
make schedule               # Nightly cron retraining
make logs                   # Stream logs
```

### 4. Launch Jupyter Notebook

```bash
make notebook               # GPU-enabled Jupyter in Polyaxon
```

---

## Project Structure

```text
├── train.py                    # Training script with Polyaxon tracking
│
├── configs/
│   └── experiment.yaml         # Hyperparameters (model, training, data)
│
├── infra/
│   ├── setup.sh                # Vast.ai on-start: k3s + Polyaxon + GPU
│   ├── polyaxonfile.yaml       # Job definition (image, GPU, inputs)
│   ├── notebook.yaml           # Jupyter notebook service
│   ├── sweep.yaml              # Hyperparameter sweep (random search)
│   ├── dag.yaml                # Pipeline: prepare → train → evaluate
│   └── schedule.yaml           # Nightly cron retraining
│
├── Makefile                    # CLI shortcuts
├── .env.example                # Environment template
├── .polyaxonignore             # Upload exclusions
└── pyproject.toml              # Python dependencies
```

## Experiment Tracking

The training script (`train.py`) integrates with Polyaxon's tracking API:

| Feature | API | What it does |
| ------- | --- | ------------ |
| **Hyperparams** | `log_inputs()` | All config values visible in UI |
| **Metrics** | `log_metrics(step=)` | Loss/accuracy curves with step axis |
| **Model** | `log_model()` | Best checkpoint versioned in artifacts |
| **Confusion matrix** | `log_confusion_matrix()` | Visual matrix in UI |
| **Progress** | `log_progress()` | Progress bar in Polyaxon dashboard |
| **Outputs** | `log_outputs()` | Final summary (best accuracy, epoch) |

### Config Override Chain

```text
configs/experiment.yaml  →  polyaxonfile inputs  →  CLI args
     (defaults)              (make run -P)         (--epochs=10)
```

Examples:

```bash
make run                                    # Use experiment.yaml defaults
make run-fast                               # Override: epochs=2
make run-full                               # Override: epochs=15, lr=0.0005
uv run polyaxon run -f infra/polyaxonfile.yaml -u -P epochs=10 -P lr=0.0003 -P hidden_size=256
```

## Hyperparameter Sweep

Run a random search over the hyperparameter space:

```bash
make sweep                  # 12 experiments, 2 concurrent
```

| Parameter | Search Space |
| --------- | ------------ |
| `lr` | logspace: 0.0001 → 0.01 (5 points) |
| `hidden_size` | 64, 128, 256, 512 |
| `dropout` | 0.1, 0.2, 0.3, 0.5 |
| `batch_size` | 32, 64, 128 |

Results are tracked in Polyaxon UI — compare metric curves side-by-side and pick the best config. Concurrency is set to 2 to avoid GPU memory contention on a single card.

## Pipeline (DAG)

Run a multi-step pipeline with dependencies:

```bash
make pipeline               # prepare-data → train → evaluate
```

```text
prepare-data ──→ train ──→ evaluate
 (download)     (GPU)     (load checkpoint,
                           print results)
```

Each step runs as a separate Kubernetes job. `train` only starts after `prepare-data` completes, `evaluate` waits for `train`. Hyperparameters are passed through the entire chain.

## Schedule

Set up automatic nightly retraining:

```bash
make schedule               # Cron: every day at 02:00 UTC
```

The schedule creates a persistent operation that triggers a new training run every night. Cache is disabled so each tick runs fresh. To stop the schedule, delete the operation from the Polyaxon UI or CLI.

## Architecture

```text
Local Machine                    Vast.ai KVM Instance
┌─────────────┐    Cloudflare    ┌──────────────────────────┐
│ polyaxon CLI │───── tunnel ────▶│ socat:18000 → Gateway    │
│ make run -u  │    (HTTPS)      │   ↓                      │
└─────────────┘                  │ k3s (Kubernetes)          │
                                 │   ├─ Polyaxon CE          │
                                 │   ├─ NVIDIA device plugin │
                                 │   └─ Job Pod (GPU) 🔥     │
                                 │       pytorch/pytorch      │
                                 └──────────────────────────┘
```

## Key Design Decisions

| Decision | Why |
| -------- | --- |
| `perCore: false` | Prevents OOM from spawning workers per CPU core on 64+ core machines |
| `limitResources: false` | Disables hardcoded 8GB memory limits from the Helm chart |
| `--default-runtime=nvidia` | All pods automatically get GPU access without `runtimeClassName` |
| `socat` port-forward | Persistent systemd service instead of flaky `kubectl port-forward` |
| `#!/bin/bash` in on-start | KVM cloud-init requires shebang (unlike Docker containers) |
| apt lock wait | Handles `unattended-upgrades` race condition on first boot |

## Commands Reference

| Command | Description |
| ------- | ----------- |
| `make check` | Verify connection to Polyaxon server |
| `make init` | Create project on server |
| `make run` | Upload code & launch training (5 epochs) |
| `make run-fast` | Quick test run (2 epochs) |
| `make run-full` | Full training (15 epochs, lr=0.0005) |
| `make sweep` | Hyperparameter search (12 random runs) |
| `make pipeline` | DAG: prepare → train → evaluate |
| `make schedule` | Nightly cron retraining |
| `make notebook` | Start Jupyter notebook with GPU |
| `make logs` | Stream run logs |
| `make status` | List runs |
| `make dashboard` | Open Polyaxon UI |

## License

MIT
