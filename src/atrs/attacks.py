"""Paper-specific data-free extraction methods over the same ranked-ID oracle.

All code in this module is independently written from the paper equations.
The published BECOME source has a beta=1 discrepancy; see docs/03_CONFIGURATION_AUDIT.md.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

import torch
from torch import nn
from torch.nn import functional as F

from .api import RankingOracle
from .data import left_pad


@dataclass(frozen=True)
class Sample:
    prefix: tuple[int, ...]
    ranking: tuple[int, ...]


def negatives_outside_topk(rankings: torch.Tensor, n_items: int, count: int) -> torch.Tensor:
    """Uniform negatives from 1..n_items excluding each teacher top-k list."""
    batch, k = rankings.shape
    count = min(count, n_items - k)
    if count < 1:
        raise ValueError("top-k must leave at least one negative item")
    weights = torch.ones(batch, n_items + 1, device=rankings.device)
    weights[:, 0] = 0
    weights.scatter_(1, rankings, 0)
    return torch.multinomial(weights, count, replacement=False)


def pairwise_margins(scores: torch.Tensor, rankings: torch.Tensor, negatives: torch.Tensor,
                     margin_rank: float, margin_neg: float) -> tuple[torch.Tensor, torch.Tensor]:
    positive = scores.gather(1, rankings)
    negative = scores.gather(1, negatives)
    rank = positive[:, 1:] - positive[:, :-1] + margin_rank
    # Paper Eq. 22 pairs j negatives per positive. Caller supplies j*k negatives.
    if negative.size(1) % positive.size(1) == 0:
        reference = positive.repeat_interleave(negative.size(1) // positive.size(1), dim=1)
    else:
        reference = positive[:, :1].expand_as(negative)
    return rank, negative - reference + margin_neg


def pairwise_loss(scores: torch.Tensor, rankings: torch.Tensor, negatives: torch.Tensor,
                  margin_rank: float, margin_neg: float, beta: float | None = None,
                  *, component: str = "total") -> torch.Tensor:
    """Adjacent-rank hinge plus top-k/negative hinge (DFME and BECOME)."""
    rank, inter = pairwise_margins(scores, rankings, negatives, margin_rank, margin_neg)
    rank_loss = F.relu(rank).mean() if rank.numel() else scores.sum() * 0
    neg_loss = F.relu(inter).mean()
    if component == "intra":
        return rank_loss
    if component == "inter":
        return neg_loss
    if component != "total":
        raise ValueError(f"unknown loss component: {component}")
    return rank_loss + neg_loss if beta is None else beta * rank_loss + (1 - beta) * neg_loss


def distill_epoch(student: nn.Module, optimizer: torch.optim.Optimizer,
                  samples: list[Sample], method: str, *, batch_size: int,
                  device: str, rng: random.Random, margin_rank: float = 0.5,
                  margin_neg: float = 0.5, beta: float | None = None,
                  negatives_per_positive: int = 1, component: str = "total",
                  negative_sampling: str = "outside_topk", scheduler=None) -> float:
    if not samples:
        raise ValueError("cannot distill an empty sample set")
    student.train()
    order = list(range(len(samples)))
    rng.shuffle(order)
    total, n_batches = 0.0, 0
    for start in range(0, len(order), batch_size):
        part = [samples[i] for i in order[start:start + batch_size]]
        tokens = torch.tensor([left_pad(s.prefix, student.max_len) for s in part], device=device)
        ranks = torch.tensor([s.ranking for s in part], device=device)
        count = ranks.size(1) * negatives_per_positive
        if negative_sampling == "source_softmax":
            # Both inspected author repositories set Top-K weights to zero
            # before softmax. This leaves positive mass on Top-K and padding.
            weights = torch.ones(len(part), student.n_items + 1, device=device)
            weights.scatter_(1, ranks, 0)
            negs = torch.multinomial(weights.softmax(-1), count, replacement=True)
        elif negative_sampling == "outside_topk":
            negs = negatives_outside_topk(ranks, student.n_items, count)
        else:
            raise ValueError(f"unknown negative sampling policy: {negative_sampling}")
        scores = student.next_scores(tokens)
        if method in {"random", "dfme", "become"}:
            loss = pairwise_loss(scores, ranks, negs, margin_rank, margin_neg, beta,
                                 component=component)
        else:
            raise ValueError(method)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        nn.utils.clip_grad_norm_(student.parameters(), 5)
        optimizer.step()
        if scheduler is not None:
            scheduler.step()
        total += float(loss.detach())
        n_batches += 1
    return total / n_batches


def _query(oracle: RankingOracle, prefixes: list[tuple[int, ...]], samples: list[Sample]) -> list[list[int]]:
    rankings = oracle.predict_topk(prefixes)
    samples.extend(Sample(prefix, tuple(ranking)) for prefix, ranking in zip(prefixes, rankings))
    oracle.counts.retained_samples += len(prefixes)
    return rankings


def _sample_uniform(rankings: list[list[int]], rng: random.Random) -> list[int]:
    return [rng.choice(ranking) for ranking in rankings]


def generate_dfme(oracle: RankingOracle, *, n_sequences: int, sequence_len: int,
                  n_items: int, rng: random.Random, batch_size: int = 32,
                  initial_items: list[int] | None = None) -> list[Sample]:
    """DFME autoregressive generation and source-style T-1 prefix training."""
    if sequence_len < 2:
        raise ValueError("DFME requires sequence_len >= 2")
    if initial_items is not None and len(initial_items) != n_sequences:
        raise ValueError("initial_items must contain one item per sequence")
    samples: list[Sample] = []
    for start in range(0, n_sequences, batch_size):
        count = min(batch_size, n_sequences - start)
        seeds = ([rng.randint(1, n_items) for _ in range(count)] if initial_items is None
                 else initial_items[start:start + count])
        sequences = [[item] for item in seeds]
        oracle.counts.generated_sequences += count
        for step in range(sequence_len):
            prefixes = [tuple(seq) for seq in sequences]
            if step + 1 == sequence_len:
                # Official SAS distillation loader uses prefixes 1..T-1.
                # Its generator still queries the final prefix; count it.
                oracle.predict_topk(prefixes)
                break
            rankings = _query(oracle, prefixes, samples)
            if step + 1 < sequence_len:
                for seq, item in zip(sequences, _sample_uniform(rankings, rng)):
                    seq.append(item)
    return samples


def _frequency_choice(ranking: list[int], frequencies: list[int], rng: random.Random,
                      alpha: float = 0.5, *, observe: bool = True) -> int:
    if observe:
        for item in ranking:
            frequencies[item] += 1
    inverse = [1 / (math.log(frequencies[item] + 1) + 1) for item in ranking]
    random_sorted = sorted((rng.random() for _ in ranking), reverse=True)
    weights = [alpha * a + (1 - alpha) * b for a, b in zip(inverse, random_sorted)]
    return rng.choices(ranking, weights=weights, k=1)[0]


def generate_random(oracle: RankingOracle, *, n_sequences: int, sequence_len: int,
                    n_items: int, rng: random.Random, batch_size: int = 50) -> list[Sample]:
    """Uniform catalog sequences, queried at every prefix as in the paper baseline."""
    samples: list[Sample] = []
    for start in range(0, n_sequences, batch_size):
        count = min(batch_size, n_sequences - start)
        sequences = [[rng.randint(1, n_items) for _ in range(sequence_len)] for _ in range(count)]
        oracle.counts.generated_sequences += count
        for length in range(1, sequence_len + 1):
            prefixes = [tuple(sequence[:length]) for sequence in sequences]
            if length == sequence_len:
                oracle.predict_topk(prefixes)
            else:
                _query(oracle, prefixes, samples)
    return samples


def generate_become(oracle: RankingOracle, student: nn.Module,
                    optimizer: torch.optim.Optimizer, *, n_sequences: int,
                    sequence_len: int, n_items: int, rng: random.Random,
                    phases: int, initial_fraction: float, select_fraction: float,
                    alpha: float, distill_epochs_per_phase: int, batch_size: int,
                    device: str, margin_rank: float, margin_neg: float,
                    beta: float, phase_mean: float = 1.0, phase_std: float = 0.2,
                    feedback_k: int | None = None,
                    negative_sampling: str = "outside_topk", negatives_per_positive: int | None = None,
                    final_phase_epochs: int | None = None, terminal_holdout: bool = False,
                    frequency_policy: str = "sampling_events",
                    phase_rounding: str = "floor") -> tuple[list[Sample], list[float]]:
    """Feedback phases, low-agreement selection, and rank/frequency sampling.

    Phase lengths follow the configured absolute normal draw. Formal configs
    use the author's random_len defaults (0, 1) and rounding. The legacy path
    keeps (1, 0.2) and floor allocation for old experiment configurations.
    """
    if phases < 1 or not 0 < initial_fraction <= 1 or not 0 < select_fraction <= 1:
        raise ValueError("invalid BECOME phase configuration")
    if feedback_k is not None and not 1 <= feedback_k <= oracle.k:
        raise ValueError("feedback_k must fit within the returned ranking")
    if frequency_policy not in {"sampling_events", "unique_responses"}:
        raise ValueError("unknown BECOME frequency_policy")
    sequences = [[rng.randint(1, n_items)] for _ in range(n_sequences)]
    oracle.counts.generated_sequences += n_sequences
    frequencies = [0] * (n_items + 1)
    samples: list[Sample] = []
    losses: list[float] = []
    initial_end = max(1, min(sequence_len, round(sequence_len * initial_fraction)))
    last_queried = [0] * n_sequences
    observed: set[tuple[int, ...]] = set()

    def observe(prefix, ranking):
        if frequency_policy == "unique_responses" and prefix not in observed:
            for item in ranking:
                frequencies[item] += 1
            observed.add(prefix)

    def choice(ranking):
        return _frequency_choice(ranking, frequencies, rng, alpha,
                                 observe=frequency_policy == "sampling_events")

    def train(epochs):
        terminals = {tuple(sequence) for sequence in sequences}
        training = [sample for sample in samples if sample.prefix not in terminals] if terminal_holdout else samples
        for _ in range(epochs):
            losses.append(distill_epoch(
                student, optimizer, training, "become", batch_size=batch_size,
                device=device, rng=rng, margin_rank=margin_rank, margin_neg=margin_neg, beta=beta,
                negatives_per_positive=(negatives_per_positive if negatives_per_positive is not None
                                        else max(1, (n_items - oracle.k) // oracle.k)),
                negative_sampling=negative_sampling,
            ))

    def extend(targets: dict[int, int], cached_rankings: dict[int, list[int]] | None = None) -> None:
        # Start the next phase from the already-labelled terminal prefix.
        if cached_rankings:
            for i, target in targets.items():
                if len(sequences[i]) < target and last_queried[i] == len(sequences[i]):
                    sequences[i].append(choice(cached_rankings[i]))
        while targets:
            current = [i for i, target in targets.items()
                       if last_queried[i] < len(sequences[i]) <= target]
            if not current:
                break
            prefixes = [tuple(sequences[i]) for i in current]
            rankings = _query(oracle, prefixes, samples)
            for i, ranking in zip(current, rankings):
                observe(tuple(sequences[i]), ranking)
                last_queried[i] = len(sequences[i])
                if len(sequences[i]) < targets[i] and len(sequences[i]) < sequence_len:
                    sequences[i].append(choice(ranking))

    extend({i: initial_end for i in range(n_sequences)})
    train(distill_epochs_per_phase)
    remaining = sequence_len - initial_end
    if remaining <= 0:
        return samples, losses
    raw = [abs(rng.gauss(phase_mean, phase_std)) for _ in range(phases)]
    if phase_rounding == "floor":
        lengths = [int(remaining * value / sum(raw)) for value in raw]
        lengths[-1] += remaining - sum(lengths)
    elif phase_rounding == "round":
        lengths = [round(remaining * value / sum(raw)) for value in raw]
        difference = remaining - sum(lengths)
        while difference:
            for index in range(phases):
                if difference > 0:
                    lengths[index] += 1
                    difference -= 1
                elif difference < 0 and lengths[index]:
                    lengths[index] -= 1
                    difference += 1
    else:
        raise ValueError("unknown phase_rounding")
    for phase_index, phase_len in enumerate(lengths):
        # Low teacher/student top-k overlap is a ranking-only discrepancy.
        agreement: list[tuple[float, int]] = []
        feedback_rankings: dict[int, list[int]] = {}
        student.eval()
        with torch.no_grad():
            for i in range(n_sequences):
                prefix = tuple(sequences[i])
                ranking = oracle.predict_topk([prefix], feedback=True)[0]
                observe(prefix, ranking)
                feedback_rankings[i] = ranking
                scores = student.next_scores(torch.tensor([left_pad(prefix, student.max_len)], device=device))
                metric_k = feedback_k or oracle.k
                predicted = set((torch.argsort(scores[:, 1:], dim=-1, descending=True,
                                               stable=True)[:, :metric_k] + 1)[0].tolist())
                agreement.append((len(predicted.intersection(ranking[:metric_k])) / metric_k, i))
        chosen = [i for _, i in sorted(agreement)[:max(1, round(select_fraction * n_sequences))]]
        # BECOME extends under-performing sequences only. Others retain shorter lengths.
        if phase_len:
            targets = {i: min(sequence_len, len(sequences[i]) + phase_len) for i in chosen}
            extend(targets, feedback_rankings)
        epochs = (final_phase_epochs if phase_index == len(lengths) - 1 and final_phase_epochs is not None
                  else distill_epochs_per_phase)
        train(epochs)
    if terminal_holdout:
        terminals = {tuple(sequence) for sequence in sequences}
        samples = [sample for sample in samples if sample.prefix not in terminals]
    oracle.generation_details = {
        "phase_lengths": lengths, "final_sequence_lengths": [len(sequence) for sequence in sequences],
        "terminal_holdout": terminal_holdout, "frequency_policy": frequency_policy,
    }
    return samples, losses
