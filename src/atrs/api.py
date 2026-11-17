"""Ranking-only oracle boundary and exact request accounting."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence

import torch

from .data import left_pad


@dataclass
class QueryCounts:
    generated_sequences: int = 0
    requested_prefixes: int = 0
    unique_queried_prefixes: int = 0
    oracle_requests: int = 0  # one new prefix, not one batch forward
    model_forward_calls: int = 0  # one batched model invocation
    cache_hits: int = 0
    retained_samples: int = 0
    feedback_prefixes: int = 0
    feedback_oracle_requests: int = 0


class BudgetExhausted(RuntimeError):
    pass


class RankingOracle:
    def __init__(self, model, *, k: int = 100, max_requests: int | None = None,
                 batch_size: int = 128, cache: bool = True, device: str = "cpu"):
        if k < 1 or k > model.n_items:
            raise ValueError("k must be in 1..n_items")
        if batch_size < 1 or (max_requests is not None and max_requests < 0):
            raise ValueError("batch_size must be positive and max_requests nonnegative")
        self.__model = model.to(device).eval()
        for parameter in self.__model.parameters():
            parameter.requires_grad_(False)
        self.k = k
        self.max_requests = max_requests
        self.batch_size = batch_size
        self.device = device
        self.cache = cache
        self.__cache: dict[tuple[int, ...], tuple[int, ...]] = {}
        self.__seen: set[tuple[int, ...]] = set()
        self.counts = QueryCounts()

    def predict_topk(self, prefixes: Sequence[Sequence[int]], *,
                     feedback: bool = False) -> list[list[int]]:
        keys = [tuple(int(x) for x in prefix) for prefix in prefixes]
        for key in keys:
            if not key or any(x < 1 or x > self.__model.n_items for x in key):
                raise ValueError("prefixes must contain valid positive item IDs")
        pending = (list(dict.fromkeys(key for key in keys if key not in self.__cache))
                   if self.cache else keys)
        new_count = len(pending)
        if self.max_requests is not None and self.counts.oracle_requests + new_count > self.max_requests:
            raise BudgetExhausted(f"request budget {self.max_requests} exceeded")
        results = self.__cache if self.cache else {}
        fresh: dict[tuple[int, ...], tuple[int, ...]] = {}
        uncached: list[list[int]] = []
        with torch.no_grad():
            for start in range(0, len(pending), self.batch_size):
                part = pending[start:start + self.batch_size]
                inputs = torch.tensor([left_pad(key, self.__model.max_len) for key in part], device=self.device)
                scores = self.__model.next_scores(inputs)[:, 1:]
                # No seen-item filtering: matches the DFME/BECOME generator source.
                # Stable sorting gives a defined item-ID tie break.
                ranked = torch.argsort(scores, dim=-1, descending=True, stable=True)[:, :self.k] + 1
                rows = ranked.tolist()
                if self.cache:
                    fresh.update((key, tuple(row)) for key, row in zip(part, rows))
                else:
                    uncached.extend(rows)
                self.counts.model_forward_calls += 1
        results.update(fresh)
        self.__seen.update(keys)
        self.counts.requested_prefixes += len(keys)
        self.counts.oracle_requests += new_count
        self.counts.cache_hits += len(keys) - new_count
        self.counts.unique_queried_prefixes = len(self.__seen)
        if feedback:
            self.counts.feedback_prefixes += len(keys)
            self.counts.feedback_oracle_requests += new_count
        return [list(results[key]) for key in keys] if self.cache else uncached

    def counters(self) -> dict:
        return asdict(self.counts)
