"""Paper-specific data-free extraction methods over the same ranked-ID oracle.

All code in this module is independently written from the paper equations.
The published BECOME source has a beta=1 discrepancy; see KNOWN_DEVIATIONS.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Iterable

import torch
from torch import nn
from torch.nn import functional as F

from .api import BudgetExhausted, RankingOracle
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


def pairwise_loss(scores: torch.Tensor, rankings: torch.Tensor, negatives: torch.Tensor,
                  margin_rank: float, margin_neg: float, beta: float | None = None) -> torch.Tensor:
    """Adjacent-rank hinge plus top-k/negative hinge (DFME and BECOME)."""
    positive = scores.gather(1, rankings)
    negative = scores.gather(1, negatives)
    rank_loss = F.relu(positive[:, 1:] - positive[:, :-1] + margin_rank).mean()
    # Paper Eq. 22 pairs j negatives per positive. Caller supplies j*k negatives.
    if negative.size(1) % positive.size(1) == 0:
        reference = positive.repeat_interleave(negative.size(1) // positive.size(1), dim=1)
    else:
        reference = positive[:, :1].expand_as(negative)
    neg_loss = F.relu(negative - reference + margin_neg).mean()
    return rank_loss + neg_loss if beta is None else beta * rank_loss + (1 - beta) * neg_loss


def listwise_loss(scores: torch.Tensor, rankings: torch.Tensor,
                  negatives: torch.Tensor) -> torch.Tensor:
    """Sim4Rec Eq. 9-10: Plackett-Luce top-K likelihood with N negatives."""
    ordered = torch.cat([rankings, negatives], dim=1)
    selected = scores.gather(1, ordered)
    k = rankings.size(1)
    terms = [torch.logsumexp(selected[:, position:], dim=1) - selected[:, position]
             for position in range(k)]
    return torch.stack(terms, dim=1).sum(dim=1).mean()


def distill_epoch(student: nn.Module, optimizer: torch.optim.Optimizer,
                  samples: list[Sample], method: str, *, batch_size: int,
                  device: str, rng: random.Random, margin_rank: float = 0.5,
                  margin_neg: float = 0.5, beta: float | None = None,
                  negatives_per_positive: int = 1) -> float:
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
        negs = negatives_outside_topk(ranks, student.n_items,
                                      ranks.size(1) * negatives_per_positive)
        scores = student.next_scores(tokens)
        if method == "sim4rec":
            loss = listwise_loss(scores, ranks, negs)
        elif method in {"dfme", "become"}:
            loss = pairwise_loss(scores, ranks, negs, margin_rank, margin_neg, beta)
        else:
            raise ValueError(method)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        nn.utils.clip_grad_norm_(student.parameters(), 5)
        optimizer.step()
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
                  n_items: int, rng: random.Random, batch_size: int = 32) -> list[Sample]:
    """DFME autoregressive generation and source-style T-1 prefix training."""
    if sequence_len < 2:
        raise ValueError("DFME requires sequence_len >= 2")
    samples: list[Sample] = []
    for start in range(0, n_sequences, batch_size):
        count = min(batch_size, n_sequences - start)
        sequences = [[rng.randint(1, n_items)] for _ in range(count)]
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
                      alpha: float = 0.5) -> int:
    for item in ranking:
        frequencies[item] += 1
    inverse = [1 / (math.log(frequencies[item] + 1) + 1) for item in ranking]
    random_sorted = sorted((rng.random() for _ in ranking), reverse=True)
    weights = [alpha * a + (1 - alpha) * b for a, b in zip(inverse, random_sorted)]
    return rng.choices(ranking, weights=weights, k=1)[0]


def generate_become(oracle: RankingOracle, student: nn.Module,
                    optimizer: torch.optim.Optimizer, *, n_sequences: int,
                    sequence_len: int, n_items: int, rng: random.Random,
                    phases: int, initial_fraction: float, select_fraction: float,
                    alpha: float, distill_epochs_per_phase: int, batch_size: int,
                    device: str, margin_rank: float, margin_neg: float,
                    beta: float) -> tuple[list[Sample], list[float]]:
    """Feedback phases, low-agreement selection, and rank/frequency sampling.

    Phase lengths are drawn from |N(mu,sigma)| then scaled to the remaining
    sequence length. The BECOME paper does not publish exact mu/sigma; we use
    mu=1,sigma=0.2 and record this as an adaptation.
    """
    if phases < 1 or not 0 < initial_fraction <= 1 or not 0 < select_fraction <= 1:
        raise ValueError("invalid BECOME phase configuration")
    sequences = [[rng.randint(1, n_items)] for _ in range(n_sequences)]
    oracle.counts.generated_sequences += n_sequences
    frequencies = [0] * (n_items + 1)
    samples: list[Sample] = []
    losses: list[float] = []
    initial_end = max(1, min(sequence_len, round(sequence_len * initial_fraction)))
    last_queried = [0] * n_sequences

    def extend(targets: dict[int, int], cached_rankings: dict[int, list[int]] | None = None) -> None:
        # Start the next phase from the already-labelled terminal prefix.
        if cached_rankings:
            for i, target in targets.items():
                if len(sequences[i]) < target and last_queried[i] == len(sequences[i]):
                    sequences[i].append(_frequency_choice(cached_rankings[i], frequencies, rng, alpha))
        while targets:
            current = [i for i, target in targets.items()
                       if last_queried[i] < len(sequences[i]) <= target]
            if not current:
                break
            prefixes = [tuple(sequences[i]) for i in current]
            rankings = _query(oracle, prefixes, samples)
            for i, ranking in zip(current, rankings):
                last_queried[i] = len(sequences[i])
                if len(sequences[i]) < targets[i] and len(sequences[i]) < sequence_len:
                    sequences[i].append(_frequency_choice(ranking, frequencies, rng, alpha))

    extend({i: initial_end for i in range(n_sequences)})
    for _ in range(distill_epochs_per_phase):
        losses.append(distill_epoch(student, optimizer, samples, "become", batch_size=batch_size,
                                   device=device, rng=rng, margin_rank=margin_rank,
                                   margin_neg=margin_neg, beta=beta,
                                   negatives_per_positive=max(1, (n_items - oracle.k) // oracle.k)))
    remaining = sequence_len - initial_end
    if remaining <= 0:
        return samples, losses
    raw = [abs(rng.gauss(1, 0.2)) for _ in range(phases)]
    lengths = [int(remaining * value / sum(raw)) for value in raw]
    lengths[-1] += remaining - sum(lengths)
    for phase_len in lengths:
        # Low teacher/student top-k overlap is a ranking-only discrepancy.
        agreement: list[tuple[float, int]] = []
        feedback_rankings: dict[int, list[int]] = {}
        student.eval()
        with torch.no_grad():
            for i in range(n_sequences):
                prefix = tuple(sequences[i])
                ranking = oracle.predict_topk([prefix])[0]
                feedback_rankings[i] = ranking
                scores = student.next_scores(torch.tensor([left_pad(prefix, student.max_len)], device=device))
                predicted = set((torch.argsort(scores[:, 1:], dim=-1, descending=True)[:, :oracle.k] + 1)[0].tolist())
                agreement.append((len(predicted.intersection(ranking)) / oracle.k, i))
        chosen = [i for _, i in sorted(agreement)[:max(1, round(select_fraction * n_sequences))]]
        # BECOME extends under-performing sequences only. Others retain shorter lengths.
        if phase_len:
            targets = {i: min(sequence_len, len(sequences[i]) + phase_len) for i in chosen}
            extend(targets, feedback_rankings)
        for _ in range(distill_epochs_per_phase):
            losses.append(distill_epoch(student, optimizer, samples, "become", batch_size=batch_size,
                                       device=device, rng=rng, margin_rank=margin_rank,
                                       margin_neg=margin_neg, beta=beta,
                                       negatives_per_positive=max(1, (n_items - oracle.k) // oracle.k)))
    return samples, losses


class GRUGenerator(nn.Module):
    """Sim4Rec sequential generator (GRU)."""
    def __init__(self, n_items: int, hidden: int = 64):
        super().__init__()
        self.n_items = n_items
        self.embedding = nn.Embedding(n_items + 1, hidden)
        self.gru = nn.GRU(hidden, hidden, batch_first=True)
        self.head = nn.Linear(hidden, n_items)

    def forward(self, tokens: torch.Tensor) -> torch.Tensor:
        states, _ = self.gru(self.embedding(tokens))
        return self.head(states)

    def sample(self, starts: list[int], length: int, device: str) -> tuple[list[tuple[int, ...]], torch.Tensor]:
        tokens = torch.tensor(starts, device=device).unsqueeze(1)
        current = tokens
        hidden = None
        log_probabilities = []
        for _ in range(length - 1):
            output, hidden = self.gru(self.embedding(current), hidden)
            logits = self.head(output[:, -1, :])
            distribution = torch.distributions.Categorical(logits=logits)
            item = distribution.sample() + 1
            log_probabilities.append(distribution.log_prob(item - 1))
            tokens = torch.cat([tokens, item[:, None]], dim=1)
            current = item[:, None]
        logp = torch.stack(log_probabilities, 1).sum(1) if log_probabilities else torch.zeros(len(starts), device=device)
        return [tuple(row) for row in tokens.tolist()], logp


def _sim4rec_choice(ranking: list[int], frequencies: list[int], prefix: list[int],
                    rng: random.Random) -> int:
    weights = []
    for item in ranking:
        freq = frequencies[item]
        if freq < 3:
            weight = 1 / (freq + 1)
        else:
            weight = 0.5 * math.sqrt(math.log(max(freq, 2))) / (freq + 1)
        if item in prefix:
            weight /= 2
        weights.append(weight)
    selected = rng.choices(ranking, weights=weights, k=1)[0]
    frequencies[selected] += 1
    return selected


def generate_sim4rec_seed(oracle: RankingOracle, *, n_sequences: int,
                          sequence_len: int, n_items: int,
                          rng: random.Random) -> tuple[list[Sample], list[tuple[int, ...]]]:
    samples: list[Sample] = []
    sequences = [[rng.randint(1, n_items)] for _ in range(n_sequences)]
    oracle.counts.generated_sequences += n_sequences
    frequencies = [0] * (n_items + 1)
    for _ in range(sequence_len):
        prefixes = [tuple(seq) for seq in sequences]
        rankings = _query(oracle, prefixes, samples)
        if len(sequences[0]) < sequence_len:
            for seq, ranking in zip(sequences, rankings):
                seq.append(_sim4rec_choice(ranking, frequencies, seq, rng))
    return samples, [tuple(seq) for seq in sequences]


def pretrain_generator(generator: GRUGenerator, sequences: list[tuple[int, ...]], *,
                       epochs: int, batch_size: int, device: str, lr: float = 0.01) -> list[float]:
    optimizer = torch.optim.Adam(generator.parameters(), lr=lr, weight_decay=0.01)
    losses = []
    for _ in range(epochs):
        generator.train()
        epoch_losses = []
        for start in range(0, len(sequences), batch_size):
            batch = torch.tensor(sequences[start:start + batch_size], device=device)
            if batch.size(1) < 2:
                continue
            logits = generator(batch[:, :-1])
            loss = F.cross_entropy(logits.reshape(-1, generator.n_items), (batch[:, 1:] - 1).reshape(-1))
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
            epoch_losses.append(float(loss.detach()))
        losses.append(sum(epoch_losses) / len(epoch_losses) if epoch_losses else 0.0)
    return losses


def run_sim4rec(oracle: RankingOracle, student: nn.Module,
                student_optimizer: torch.optim.Optimizer, *, n_seed_sequences: int,
                sequence_len: int, n_items: int, rng: random.Random,
                pretrain_epochs: int, adversarial_rounds: int, round_batch: int,
                memory_batches: int, distill_epochs_per_round: int,
                batch_size: int, device: str) -> tuple[list[Sample], list[float], GRUGenerator]:
    """CSG -> GRU MLE -> REINFORCE hard-query mining -> listwise distillation.

    A generated full sequence receives the terminal discrepancy reward from
    Eq. 14. The cache holds earlier generated samples; the current round plus
    cached samples forms the distillation input pool.
    """
    seed_samples, sequences = generate_sim4rec_seed(oracle, n_sequences=n_seed_sequences,
                                                     sequence_len=sequence_len,
                                                     n_items=n_items, rng=rng)
    generator = GRUGenerator(n_items).to(device)
    losses = pretrain_generator(generator, sequences, epochs=pretrain_epochs,
                                batch_size=batch_size, device=device)
    losses.append(distill_epoch(student, student_optimizer, seed_samples, "sim4rec",
                                batch_size=batch_size, device=device, rng=rng))
    generator_optimizer = torch.optim.Adam(generator.parameters(), lr=0.01, weight_decay=0.01)
    bank = seed_samples.copy()
    for _ in range(adversarial_rounds):
        generator.train()
        generated, logp = generator.sample([rng.randint(1, n_items) for _ in range(round_batch)],
                                           sequence_len, device)
        oracle.counts.generated_sequences += round_batch
        current: list[Sample] = []
        _query(oracle, generated, current)
        student.eval()
        with torch.no_grad():
            tokens = torch.tensor([left_pad(s.prefix, student.max_len) for s in current], device=device)
            rankings = torch.tensor([s.ranking for s in current], device=device)
            negatives = negatives_outside_topk(rankings, n_items, rankings.size(1))
            scores = student.next_scores(tokens)
            # Individual terminal rewards, detached from the student.
            ordered = scores.gather(1, torch.cat([rankings, negatives], 1))
            rewards = torch.stack([torch.logsumexp(ordered[:, i:], 1) - ordered[:, i]
                                   for i in range(rankings.size(1))], 1).sum(1).detach()
        policy_loss = -(logp * (rewards - rewards.mean())).mean()
        generator_optimizer.zero_grad(set_to_none=True)
        policy_loss.backward()
        generator_optimizer.step()
        # Memory bank capacity Mbank * batch size, current batch always retained.
        bank.extend(current)
        bank = bank[-memory_batches * round_batch:]
        for _ in range(distill_epochs_per_round):
            losses.append(distill_epoch(student, student_optimizer, bank, "sim4rec",
                                       batch_size=batch_size, device=device, rng=rng))
    return seed_samples + bank, losses, generator
