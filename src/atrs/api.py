"""Ranking-only oracle boundary and exact request accounting."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence

import torch

from .data import left_pad


@dataclass
class QueryCounts:
    generated_sequences: int = 0
    unique_queried_prefixes: int = 0
    oracle_requests: int = 0  # one new prefix, not one batch forward
    model_forward_calls: int = 0  # one batched model invocation
    cache_hits: int = 0
    retained_samples: int = 0


class BudgetExhausted(RuntimeError):
    pass


class RankingOracle:
    def __init__(self, model, *, k: int = 100, max_requests: int | None = None,
                 batch_size: int = 128, cache: bool = True, device: str = "cpu"):
        if k < 1 or k > model.n_items:
            raise ValueError("k must be in 1..n_items")
        self.__model = model.to(device).eval()
        for parameter in self.__model.parameters():
            parameter.requires_grad_(False)
        self.k = k
        self.max_requests = max_requests
        self.batch_size = batch_size
        self.device = device
        self.cache = cache
        self.__cache: dict[tuple[int, ...], tuple[int, ...]] = {}
        self.counts = QueryCounts()

    def predict_topk(self, prefixes: Sequence[Sequence[int]]) -> list[list[int]]:
        keys = [tuple(int(x) for x in prefix) for prefix in prefixes]
        for key in keys:
            if not key or any(x < 1 or x > self.__model.n_items for x in key):
                raise ValueError("prefixes must contain valid positive item IDs")
        pending = list(dict.fromkeys(key for key in keys if not (self.cache and key in self.__cache)))
        new_count = len(pending) if self.cache else len(keys)
        if self.max_requests is not None and self.counts.oracle_requests + new_count > self.max_requests:
            raise BudgetExhausted(f"request budget {self.max_requests} exceeded")
        results: dict[tuple[int, ...], tuple[int, ...]] = {}
        if self.cache:
            results.update(self.__cache)
            self.counts.cache_hits += len(keys) - len(pending)
        else:
            pending = keys
        with torch.no_grad():
            for start in range(0, len(pending), self.batch_size):
                part = pending[start:start + self.batch_size]
                inputs = torch.tensor([left_pad(key, self.__model.max_len) for key in part], device=self.device)
                scores = self.__model.next_scores(inputs)[:, 1:]
                # No seen-item filtering: matches the DFME/BECOME generator source.
                # Stable sorting gives a defined item-ID tie break.
                ranked = torch.argsort(scores, dim=-1, descending=True, stable=True)[:, :self.k] + 1
                for key, row in zip(part, ranked.tolist()):
                    results[key] = tuple(row)
                self.counts.model_forward_calls += 1
        if self.cache:
            self.__cache.update({key: results[key] for key in pending})
        self.counts.oracle_requests += new_count
        self.counts.unique_queried_prefixes = len(self.__cache) if self.cache else len(set(keys))
        return [list(results[key]) for key in keys]

    def counters(self) -> dict:
        return asdict(self.counts)
