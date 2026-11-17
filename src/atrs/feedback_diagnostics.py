"""Defender-side trajectory and supervision controls for DFME (T5)."""
from __future__ import annotations

import random
from collections import Counter

from .api import RankingOracle
from .attacks import Sample


def random_tail_replacement(ranking: list[int], *, n_items: int, head: int,
                            count: int, rng: random.Random) -> list[int]:
    if not 0 <= head <= len(ranking) or not 0 <= count <= min(len(ranking) - head, n_items - len(ranking)):
        raise ValueError("replacement count must fit both the editable tail and outside catalog")
    pool = sorted(set(range(1, n_items + 1)).difference(ranking))
    edited = ranking.copy()
    for pos, item in zip(rng.sample(range(head, len(ranking)), count), rng.sample(pool, count)):
        edited[pos] = item
    return edited


class FeedbackDiagnosticOracle(RankingOracle):
    """Pair views of one defender forward. Only the selected view generates queries."""

    def __init__(self, teacher, *, head: int, replacements: int, generation_protected: bool,
                 seed: int, **oracle_args):
        super().__init__(teacher, **oracle_args)
        self.n_items = teacher.n_items
        self.head = head
        self.replacements = replacements
        self.generation_protected = generation_protected
        self.seed = seed
        self.views: dict[tuple[int, ...], tuple[tuple[int, ...], tuple[int, ...]]] = {}

    def predict_topk(self, prefixes, *, feedback=False):
        rankings = super().predict_topk(prefixes, feedback=feedback)
        outputs = []
        for prefix, clean in zip(prefixes, rankings):
            key = tuple(prefix)
            if key not in self.views:
                # Shared edits even if the two trajectories encounter a prefix in different orders.
                rng = random.Random(f"{self.seed}:{key}")
                edited = random_tail_replacement(clean, n_items=self.n_items, head=self.head,
                                                 count=self.replacements, rng=rng)
                self.views[key] = (tuple(clean), tuple(edited))
            outputs.append(list(self.views[key][self.generation_protected]))
        return outputs

    def supervision(self, samples: list[Sample], *, protected: bool) -> list[Sample]:
        return [Sample(sample.prefix, self.views[sample.prefix][protected]) for sample in samples]


def trajectory_metrics(terminal_prefixes, n_items: int) -> dict:
    sequences = list(terminal_prefixes)
    frequencies = Counter(item for seq in sequences for item in seq)
    n_tokens = sum(map(len, sequences))
    return {
        "item_coverage": len(frequencies) / n_items,
        "generated_item_counts": dict(sorted(frequencies.items())),
        "unique_terminal_sequences": len(set(sequences)),
        "repeated_token_fraction": sum(len(seq) - len(set(seq)) for seq in sequences) / n_tokens,
    }
