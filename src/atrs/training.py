"""Training examples, reproducible seeding, and resumable checkpoints."""
from __future__ import annotations

import json
import random
import subprocess
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


def source_adamw(model, *, lr: float, weight_decay: float):
    """Reference-style AdamW groups with no decay on norms and biases."""
    decay, no_decay = [], []
    for name, parameter in model.named_parameters():
        (no_decay if "bias" in name or "norm" in name else decay).append(parameter)
    return torch.optim.AdamW([{"params": decay, "weight_decay": weight_decay},
                              {"params": no_decay, "weight_decay": 0.0}],
                             lr=lr, eps=1e-8)


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
                    metadata: dict, student=None, student_optimizer=None) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"model": model.state_dict(), "optimizer": optimizer.state_dict(),
               "model_config": model.config(), "epoch": epoch,
               "metadata": {**metadata, "git_commit": git_commit()},
               "torch_rng": torch.get_rng_state(), "python_rng": random.getstate()}
    if student is not None:
        payload["student"] = student.state_dict()
    if student_optimizer is not None:
        payload["student_optimizer"] = student_optimizer.state_dict()
    torch.save(payload, path)


def load_checkpoint(path: str | Path, *, model, optimizer=None,
                    student=None, student_optimizer=None, map_location="cpu") -> dict:
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
    if "torch_rng" in payload:
        torch.set_rng_state(payload["torch_rng"])
    if "python_rng" in payload:
        random.setstate(payload["python_rng"])
    return payload


def append_jsonl(path: str | Path, record: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
