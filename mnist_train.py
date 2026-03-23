"""MNIST Training with Polyaxon Experiment Tracking.

Features:
  - YAML config (config.yaml) with CLI overrides
  - Polyaxon tracking: inputs, metrics, model, confusion matrix
  - Test evaluation every epoch
  - Best model checkpoint saving
  - Graceful fallback when running without Polyaxon
"""

import argparse
import os
import time
from pathlib import Path

import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_config(config_path: str = "config.yaml") -> dict:
    """Load YAML config, return flat dict for easy override."""
    try:
        import yaml
        with open(config_path) as f:
            raw = yaml.safe_load(f) or {}
    except (ImportError, FileNotFoundError):
        raw = {}

    return {
        "hidden_size": raw.get("model", {}).get("hidden_size", 128),
        "dropout": raw.get("model", {}).get("dropout", 0.2),
        "epochs": raw.get("training", {}).get("epochs", 5),
        "batch_size": raw.get("training", {}).get("batch_size", 64),
        "lr": raw.get("training", {}).get("lr", 0.001),
        "weight_decay": raw.get("training", {}).get("weight_decay", 1e-5),
        "log_interval": raw.get("training", {}).get("log_interval", 100),
        "num_workers": raw.get("data", {}).get("num_workers", 2),
    }


def parse_args(config: dict) -> dict:
    """CLI overrides on top of YAML config."""
    parser = argparse.ArgumentParser(description="MNIST Training")
    for key, val in config.items():
        parser.add_argument(f"--{key}", type=type(val), default=val)
    args = parser.parse_args()
    return vars(args)


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

class MNISTNet(nn.Module):
    """Simple MLP with dropout for MNIST."""

    def __init__(self, hidden_size: int = 128, dropout: float = 0.2):
        super().__init__()
        self.net = nn.Sequential(
            nn.Flatten(),
            nn.Linear(784, hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size // 2, 10),
        )

    def forward(self, x):
        return self.net(x)


# ---------------------------------------------------------------------------
# Tracking helpers (graceful fallback)
# ---------------------------------------------------------------------------

class NoOpTracking:
    """Stub when polyaxon is not available."""

    def __getattr__(self, _):
        return lambda *a, **kw: None


def init_tracking():
    """Initialize Polyaxon tracking or fallback."""
    try:
        from polyaxon import tracking
        tracking.init()
        print("✅ Polyaxon tracking initialized")
        return tracking
    except Exception as e:
        print(f"⚠️  Polyaxon tracking not available ({e}), running offline")
        return NoOpTracking()


# ---------------------------------------------------------------------------
# Training & Evaluation
# ---------------------------------------------------------------------------

def train_epoch(model, loader, optimizer, criterion, device, epoch, config, tracking, global_step):
    """Train one epoch, log batch metrics."""
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0

    for batch_idx, (data, target) in enumerate(loader):
        data, target = data.to(device), target.to(device)

        optimizer.zero_grad()
        output = model(data)
        loss = criterion(output, target)
        loss.backward()
        optimizer.step()

        running_loss += loss.item()
        pred = output.argmax(dim=1)
        correct += pred.eq(target).sum().item()
        total += target.size(0)
        global_step += 1

        if batch_idx % config["log_interval"] == 0 and batch_idx > 0:
            avg_loss = running_loss / config["log_interval"]
            accuracy = correct / total
            print(
                f"  Epoch {epoch} [{batch_idx * len(data):>5d}/{len(loader.dataset)}]  "
                f"loss={avg_loss:.4f}  acc={accuracy:.4f}"
            )
            tracking.log_metrics(step=global_step, train_loss=avg_loss, train_accuracy=accuracy)
            running_loss = 0.0

    epoch_accuracy = correct / total
    return epoch_accuracy, global_step


@torch.no_grad()
def evaluate(model, loader, criterion, device):
    """Evaluate on test set, return loss, accuracy, all preds & targets."""
    model.eval()
    test_loss = 0.0
    correct = 0
    all_preds = []
    all_targets = []

    for data, target in loader:
        data, target = data.to(device), target.to(device)
        output = model(data)
        test_loss += criterion(output, target).item() * data.size(0)
        pred = output.argmax(dim=1)
        correct += pred.eq(target).sum().item()
        all_preds.extend(pred.cpu().tolist())
        all_targets.extend(target.cpu().tolist())

    n = len(loader.dataset)
    return test_loss / n, correct / n, all_preds, all_targets


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    config = parse_args(load_config())
    tracking = init_tracking()

    # Log all hyperparameters
    tracking.log_inputs(**config)

    # Device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"🖥  Device: {device}")
    if device.type == "cuda":
        print(f"   GPU: {torch.cuda.get_device_name(0)}")
        tracking.log_inputs(gpu=torch.cuda.get_device_name(0))

    # Data
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,)),
    ])
    train_ds = datasets.MNIST("./data", train=True, download=True, transform=transform)
    test_ds = datasets.MNIST("./data", train=False, download=True, transform=transform)
    train_loader = torch.utils.data.DataLoader(
        train_ds, batch_size=config["batch_size"], shuffle=True,
        num_workers=config["num_workers"], pin_memory=device.type == "cuda",
    )
    test_loader = torch.utils.data.DataLoader(
        test_ds, batch_size=1024, shuffle=False,
        num_workers=config["num_workers"], pin_memory=device.type == "cuda",
    )

    # Model
    model = MNISTNet(
        hidden_size=config["hidden_size"],
        dropout=config["dropout"],
    ).to(device)
    print(f"📐 Model params: {sum(p.numel() for p in model.parameters()):,}")

    optimizer = optim.Adam(
        model.parameters(),
        lr=config["lr"],
        weight_decay=config["weight_decay"],
    )
    criterion = nn.CrossEntropyLoss()

    # Training loop
    best_accuracy = 0.0
    best_epoch = 0
    global_step = 0
    model_dir = Path("model")
    model_dir.mkdir(exist_ok=True)
    start_time = time.time()

    print(f"\n🚀 Training for {config['epochs']} epochs\n")

    for epoch in range(1, config["epochs"] + 1):
        # Train
        train_acc, global_step = train_epoch(
            model, train_loader, optimizer, criterion, device,
            epoch, config, tracking, global_step,
        )

        # Evaluate
        val_loss, val_accuracy, all_preds, all_targets = evaluate(
            model, test_loader, criterion, device,
        )

        print(
            f"  Epoch {epoch} summary:  val_loss={val_loss:.4f}  "
            f"val_accuracy={val_accuracy:.4f}"
        )

        # Log epoch metrics
        tracking.log_metrics(
            step=epoch,
            val_loss=val_loss,
            val_accuracy=val_accuracy,
            train_accuracy=train_acc,
        )

        # Progress bar in Polyaxon UI
        tracking.log_progress(epoch / config["epochs"])

        # Save best model
        if val_accuracy > best_accuracy:
            best_accuracy = val_accuracy
            best_epoch = epoch
            model_path = str(model_dir / "mnist_best.pt")
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "accuracy": val_accuracy,
                "config": config,
            }, model_path)
            print(f"  💾 Best model saved (accuracy={val_accuracy:.4f})")

            # Log model to Polyaxon artifacts
            tracking.log_model(
                path=model_path,
                name="mnist-net",
                framework="pytorch",
                summary={
                    "accuracy": val_accuracy,
                    "epoch": epoch,
                    "hidden_size": config["hidden_size"],
                },
            )

    # Final summary
    elapsed = time.time() - start_time
    print(f"\n✅ Training complete in {elapsed:.1f}s")
    print(f"   Best accuracy: {best_accuracy:.4f} (epoch {best_epoch})")

    # Log confusion matrix (final epoch)
    tracking.log_confusion_matrix(
        name="confusion_matrix",
        x=all_targets,
        y=all_preds,
        step=config["epochs"],
    )

    # Log final outputs
    tracking.log_outputs(
        best_accuracy=best_accuracy,
        best_epoch=best_epoch,
        training_time_s=round(elapsed, 1),
    )


if __name__ == "__main__":
    main()
