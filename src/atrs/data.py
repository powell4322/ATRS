"""Chronological leave-one-out data protocol for SASRec text exports.

The text files contain ordered ``user_id item_id`` pairs. They do not contain
timestamps, so chronology can only be inherited from their line order.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Split:
    train: dict[int, list[int]]
    valid: dict[int, int]
    test: dict[int, int]
    n_items: int
    source_sha256: str
    source_path: str
    n_interactions: int

    @property
    def users(self) -> list[int]:
        return sorted(self.train)

    def metadata(self) -> dict:
        return {
            "source_path": self.source_path,
            "source_sha256": self.source_sha256,
            "format": "user item; within-user line order is chronology",
            "split": "last two per user: validation, test",
            "n_users": len(self.train),
            "n_items": self.n_items,
            "n_interactions": self.n_interactions,
            "n_train": sum(map(len, self.train.values())),
            "n_valid": len(self.valid),
            "n_test": len(self.test),
            "item_mapping": "identity; IDs must be contiguous 1..n_items",
        }

    def save_metadata(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.metadata(), indent=2), encoding="utf-8")


def load_split(path: str | Path, *, require_dense_ids: bool = True) -> Split:
    path = Path(path)
    sequences: dict[int, list[int]] = defaultdict(list)
    item_ids: set[int] = set()
    hasher = hashlib.sha256()
    n_rows = 0
    last_user = None
    closed_users: set[int] = set()
    with path.open("rb") as stream:
        for line_number, raw in enumerate(stream, 1):
            hasher.update(raw)
            fields = raw.split()
            if len(fields) != 2:
                raise ValueError(f"{path}:{line_number}: expected user item")
            try:
                user, item = map(int, fields)
            except ValueError as exc:
                raise ValueError(f"{path}:{line_number}: IDs must be integers") from exc
            if user < 1 or item < 1:
                raise ValueError(f"{path}:{line_number}: IDs must be positive")
            if user != last_user:
                if last_user is not None:
                    closed_users.add(last_user)
                if user in closed_users:
                    raise ValueError(f"{path}:{line_number}: user blocks are interleaved")
                last_user = user
            sequences[user].append(item)
            item_ids.add(item)
            n_rows += 1
    if not sequences:
        raise ValueError(f"{path}: empty dataset")
    if require_dense_ids and (min(item_ids) != 1 or len(item_ids) != max(item_ids)):
        raise ValueError("Item IDs must be dense 1..N; supply an explicit mapping before training")
    short = [user for user, seq in sequences.items() if len(seq) < 3]
    if short:
        raise ValueError(f"{len(short)} users have fewer than 3 interactions; first={short[:5]}")
    train = {user: seq[:-2] for user, seq in sequences.items()}
    valid = {user: seq[-2] for user, seq in sequences.items()}
    test = {user: seq[-1] for user, seq in sequences.items()}
    return Split(train, valid, test, max(item_ids), hasher.hexdigest(), str(path.resolve()), n_rows)


def left_pad(items: list[int] | tuple[int, ...], max_len: int) -> list[int]:
    if max_len < 1:
        raise ValueError("max_len must be positive")
    tail = list(items)[-max_len:]
    return [0] * (max_len - len(tail)) + tail
