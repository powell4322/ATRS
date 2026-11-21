"""Training examples, reproducible seeding, and resumable checkpoints."""
from __future__ import annotations

import json
import random
import subprocess
from tempfile import NamedTemporaryFile
from pathlib import Path

import torch
from torch.utils.data import Dataset

from .data import Split, left_pad


def set_seed(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)


def git_commit() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL,
                                       text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def source_optimizer(model, *, lr: float, weight_decay: float, name: str = "adamw"):
    """Reference parameter groups, with an explicit optimizer choice."""
    decay, no_decay = [], []
    for parameter_name, parameter in model.named_parameters():
        (no_decay if "bias" in parameter_name or "norm" in parameter_name else decay).append(parameter)
    optimizer = {"adam": torch.optim.Adam, "adamw": torch.optim.AdamW}.get(name.lower())
    if optimizer is None:
        raise ValueError(f"unsupported optimizer: {name}")
    return optimizer([{"params": decay, "weight_decay": weight_decay},
                      {"params": no_decay, "weight_decay": 0.0}], lr=lr, eps=1e-8)


def source_adamw(model, *, lr: float, weight_decay: float):
    return source_optimizer(model, lr=lr, weight_decay=weight_decay)


def linear_warmup_decay(optimizer, *, warmup_steps: int, total_steps: int):
    if warmup_steps < 0 or total_steps < 1:
        raise ValueError("warmup_steps must be nonnegative and total_steps positive")

    def factor(step):
        if step < warmup_steps:
            return step / max(1, warmup_steps)
        return max(0.0, (total_steps - step) / max(1, total_steps - warmup_steps))

    return torch.optim.lr_scheduler.LambdaLR(optimizer, factor)


class SASWindows(Dataset):
    """Train-only sliding windows; held-out interactions never enter sampling."""
    def __init__(self, split: Split, *, max_len: int, seed: int = 42,
                 sliding_fraction: float = 0.5):
        self.n_items = split.n_items
        self.max_len = max_len
        self.seed = seed
        self.epoch = 0
        self.rows: list[tuple[int, list[int]]] = []
        step = max(1, int(max_len * sliding_fraction))
        for user in split.users:
            sequence = split.train[user]
            if len(sequence) < 2:
                continue
            for end in range(len(sequence), 1, -step):
                start = max(0, end - (max_len + 1))
                self.rows.append((user, sequence[start:end]))
                if start == 0:
                    break
        self.seen_train = {user: set(seq) for user, seq in split.train.items()}

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int):
        user, sequence = self.rows[index]
        tokens = left_pad(sequence[:-1], self.max_len)
        positives = left_pad(sequence[1:], self.max_len)
        rng = random.Random(self.seed + self.epoch * 1_000_003 + index)
        if len(self.seen_train[user]) >= self.n_items:
            raise ValueError(f"user {user} has interacted with every item")
        negatives = []
        for positive in positives:
            if positive == 0:
                negatives.append(0)
                continue
            item = rng.randint(1, self.n_items)
            while item in self.seen_train[user]:
                item = rng.randint(1, self.n_items)
            negatives.append(item)
        return (torch.tensor(tokens), torch.tensor(positives), torch.tensor(negatives))


def save_checkpoint(path: str | Path, *, model, optimizer, epoch: int,
                    metadata: dict, student=None, student_optimizer=None, scheduler=None) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"model": model.state_dict(), "optimizer": optimizer.state_dict(),
               "model_config": model.config(), "epoch": epoch,
               "metadata": {**metadata, "git_commit": git_commit()},
               "torch_rng": torch.get_rng_state(), "python_rng": random.getstate()}
    if torch.cuda.is_available():
        payload["cuda_rng"] = torch.cuda.get_rng_state_all()
    if student is not None:
        payload["student"] = student.state_dict()
    if student_optimizer is not None:
        payload["student_optimizer"] = student_optimizer.state_dict()
    if scheduler is not None:
        payload["scheduler"] = scheduler.state_dict()
    with NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
    try:
        torch.save(payload, temporary)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def load_checkpoint(path: str | Path, *, model, optimizer=None,
                    student=None, student_optimizer=None, map_location="cpu",
                    restore_rng: bool = True) -> dict:
    payload = torch.load(path, map_location=map_location, weights_only=False)
    if payload["model_config"] != model.config():
        raise ValueError("model configuration differs from checkpoint")
    model.load_state_dict(payload["model"])
    if optimizer is not None:
        optimizer.load_state_dict(payload["optimizer"])
    if student is not None:
        student.load_state_dict(payload["student"])
    if student_optimizer is not None:
        student_optimizer.load_state_dict(payload["student_optimizer"])
    if restore_rng:
        if "torch_rng" in payload:
            torch.set_rng_state(payload["torch_rng"].cpu())
        if "cuda_rng" in payload and torch.cuda.is_available():
            torch.cuda.set_rng_state_all([state.cpu() for state in payload["cuda_rng"]])
        if "python_rng" in payload:
            random.setstate(payload["python_rng"])
    return payload


def append_jsonl(path: str | Path, record: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def print_epoch_progress(label: str, epoch: int, epochs: int, metrics: dict[str, float]) -> None:
    """Print one compact epoch row; complete records remain in JSONL files."""
    width = 20
    filled = min(width, width * epoch // max(1, epochs))
    bar = "#" * filled + "-" * (width - filled)
    values = " | ".join(f"{name}={value:.5f}" for name, value in metrics.items())
    print(f"{label} [{bar}] {epoch}/{epochs} | {values}", flush=True)
