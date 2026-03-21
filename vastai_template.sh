# Vast.ai Template: Polyaxon CE Training Server
# ================================================
#
# Template Name:     Polyaxon CE Training Server
# Template Desc:     K3s + Polyaxon CE for ML training with GPU (RTX 3090, etc.)
# VM Image:          docker.io/vastai/kvm:ubuntu_desktop_22.04-2025-11-21
# Ports:             1111, 3478/udp, 5900, 6100, 6200, 741641/udp, 8000
# Launch Mode:       Interactive shell server, SSH (Direct SSH ✓)
# Disk:              100 GB
#
# Environment Variables:
#   OPEN_BUTTON_TOKEN  = 1
#   OPEN_BUTTON_PORT   = 1111
#   PORTAL_CONFIG      = localhost:1111:11111:/:Instance Portal|localhost:6100:16100:/:Selkies Low Latency Desktop|localhost:6200:16200:/:Apache Guacamole Desktop (VNC)|localhost:8000:18000:/:Polyaxon
#
# On-start Script (3 строки, ОБЯЗАТЕЛЬНО с shebang — KVM использует cloud-init!):
#
#   #!/bin/bash
#   source /etc/environment
#   curl -sL https://raw.githubusercontent.com/sleep3r/polyaxon-vastai-example/main/setup.sh | bash
