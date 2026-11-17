"""Defender-side T2–T4 measurements for fixed DFME supervision."""
from __future__ import annotations

import random
import statistics
import time
from collections.abc import Callable

import torch
from torch.nn import functional as F

from .attacks import Sample, pairwise_margins


def ranking_candidates(ranking: tuple[int, ...], n_items: int, head: int,
                       per_edit: int, rng: random.Random) -> dict[str, tuple[int, ...]]:
    candidates = {"clean": ranking}
    positions = range(head, len(ranking))
    for pos in rng.sample(range(head, len(ranking) - 1), min(per_edit, len(positions) - 1)):
        swapped = list(ranking)
        swapped[pos:pos + 2] = ranking[pos:pos + 2][::-1]
        candidates[f"swap:{pos + 1}"] = tuple(swapped)
    outside = sorted(set(range(1, n_items + 1)).difference(ranking))
    count = min(per_edit, len(positions), len(outside) - len(ranking))
    for pos, item in zip(rng.sample(positions, count), rng.sample(outside, count)):
        replaced = list(ranking)
        replaced[pos] = item
        candidates[f"replace:{pos + 1}:{item}"] = tuple(replaced)
    return candidates


def _timed(device: torch.device, operation: Callable):
    if device.type == "cuda":
        torch.cuda.synchronize(device)
    start = time.perf_counter()
    value = operation()
    if device.type == "cuda":
        torch.cuda.synchronize(device)
    return value, time.perf_counter() - start


def _flat(tensors) -> torch.Tensor:
    return torch.cat([tensor.detach().flatten() for tensor in tensors])


def _ranks(values: list[float]) -> list[float]:
    ordered = sorted(values)
    tied: dict[float, tuple[int, int]] = {}
    for index, value in enumerate(ordered):
        first, _ = tied.get(value, (index, index))
        tied[value] = (first, index)
    return [sum(tied[value]) / 2 for value in values]


def _correlation(a: list[float], b: list[float]) -> float | None:
    if len(set(a)) < 2 or len(set(b)) < 2:
        return None
    return statistics.correlation(a, b)


def _selection_statistics(rows: list[dict]) -> dict:
    exact = [row["j_exact"] for row in rows]
    top = max(exact)
    result = {}
    for key in ("j_loss", "j_dev", "j_lp"):
        predictions = [row[key] for row in rows]
        chosen = max(range(len(rows)), key=predictions.__getitem__)
        result[key] = {
            "pearson": _correlation(predictions, exact),
            "spearman": _correlation(_ranks(predictions), _ranks(exact)),
            "regret": top - exact[chosen],
            "top_agreement": exact[chosen] == top,
            "chosen": rows[chosen]["candidate"],
        }
    return result


class LearningProgressProbe:
    def __init__(self, student, reference: tuple[torch.Tensor, ...], *, eta: float):
        self.student = student.eval()
        self.params = dict(student.named_parameters())
        self.device = next(student.parameters()).device
        self.eta = eta
        self.reference_tokens, self.reference_positives, self.reference_negatives = reference
        loss = self._reference_loss(self.params)
        direction = torch.autograd.grad(loss, tuple(self.params.values()))
        self.direction = dict(zip(self.params, direction))
        self.flat_direction = _flat(direction)
        self.reference_loss = float(loss.detach())

    def _scores(self, params, tokens):
        return torch.func.functional_call(self.student, params, (tokens,))[:, -1, :]

    def _reference_loss(self, params):
        scores = self._scores(params, self.reference_tokens)
        positive = scores.gather(1, self.reference_positives)
        negative = scores.gather(1, self.reference_negatives)
        return (F.softplus(-positive).mean() + F.softplus(negative).mean()) / 2

    def _sgd_reference_loss(self, gradient):
        with torch.no_grad():
            updated = {name: param - self.eta * value
                       for (name, param), value in zip(self.params.items(), gradient)}
            return float(self._reference_loss(updated))

    def run(self, sample: Sample, *, head: int, per_edit: int, rng: random.Random,
            margin_rank: float, margin_neg: float) -> dict:
        candidates = ranking_candidates(sample.ranking, self.student.n_items, head, per_edit, rng)
        union = set().union(*candidates.values())
        pool = sorted(set(range(1, self.student.n_items + 1)) - union)
        negatives = rng.sample(pool, min(len(pool), len(sample.ranking)))
        if len(negatives) != len(sample.ranking):
            raise ValueError("T2–T4 requires one shared outside-union negative per ranked item")
        tokens = torch.tensor([sample.prefix[-self.student.max_len:]], device=self.device)
        negs = torch.tensor([negatives], device=self.device)
        scores, forward_seconds = _timed(self.device, lambda: self.student.next_scores(tokens))
        (_, full_projection), jvp_seconds = _timed(
            self.device,
            lambda: torch.func.jvp(lambda params: self._scores(params, tokens),
                                   (self.params,), (self.direction,)),
        )
        with torch.no_grad():
            last_projection, last_projection_seconds = _timed(
                self.device,
                lambda: self.student.encode(tokens)[:, -1] @ self.direction["item.weight"].T,
            )

        observations = []
        for name, ranking in candidates.items():
            ranks = torch.tensor([ranking], device=self.device)
            intra, inter = pairwise_margins(scores, ranks, negs, margin_rank, margin_neg)
            intra_loss, inter_loss = intra.relu().mean(), inter.relu().mean()
            loss = intra_loss + inter_loss
            params = tuple(self.params.values())
            gradient, backward_seconds = _timed(
                self.device, lambda: torch.autograd.grad(loss, params, retain_graph=True),
            )
            post_loss, exact_seconds = _timed(
                self.device, lambda: self._sgd_reference_loss(gradient),
            )
            parameter_gradient = _flat(gradient)
            intra_parameter = _flat(torch.autograd.grad(intra_loss, params, retain_graph=True))
            inter_parameter = parameter_gradient - intra_parameter
            coefficients, coefficient_seconds = _timed(
                self.device, lambda: torch.autograd.grad(loss, scores, retain_graph=True)[0].detach(),
            )
            intra_coefficients = torch.autograd.grad(intra_loss, scores, retain_graph=True)[0].detach()
            inter_coefficients = coefficients - intra_coefficients
            active = intra.detach() > 0
            if name == "clean":
                clean_gradient, clean_post_loss = parameter_gradient, post_loss
                clean_intra, clean_inter = intra_parameter, inter_parameter
                clean_coefficients = coefficients
                clean_intra_coeff, clean_inter_coeff = intra_coefficients, inter_coefficients
            delta = clean_gradient - parameter_gradient
            score_delta = clean_coefficients - coefficients
            cosine = float(F.cosine_similarity(clean_gradient, parameter_gradient, dim=0))
            deviation = (1 - cosine if delta.norm().item() else 0.0)
            observations.append({
                "candidate": name, "ranking": ranking,
                "changed_positions": sum(a != b for a, b in zip(ranking, sample.ranking)),
                "replaced_members": len(set(ranking) - set(sample.ranking)),
                "j_loss": float(loss.detach()), "j_dev": deviation,
                "j_lp": float(torch.dot(self.flat_direction, delta)),
                "j_exact": post_loss - clean_post_loss, "reference_post_sgd": post_loss,
                "reference_change": post_loss - self.reference_loss,
                "j_lp_full_jvp": float((full_projection.detach() * score_delta).sum()),
                "j_lp_output_only": float((last_projection * score_delta).sum()),
                "active_intra_ratio": float(active.float().mean()),
                "active_inter_ratio": float((inter.detach() > 0).float().mean()),
                "intra_loss": float(intra_loss.detach()), "inter_loss": float(inter_loss.detach()),
                "intra_grad_l2": float(intra_parameter.norm()),
                "inter_grad_l2": float(inter_parameter.norm()),
                "total_grad_l2": float(parameter_gradient.norm()),
                "intra_grad_delta_l2": float((clean_intra - intra_parameter).norm()),
                "inter_grad_delta_l2": float((clean_inter - inter_parameter).norm()),
                "total_grad_delta_l2": float(delta.norm()),
                "intra_score_delta_l2": float((clean_intra_coeff - intra_coefficients).norm()),
                "inter_score_delta_l2": float((clean_inter_coeff - inter_coefficients).norm()),
                "backward_seconds": backward_seconds, "coefficient_seconds": coefficient_seconds,
                "exact_seconds": exact_seconds,
            })
        return {
            "prefix": sample.prefix, "negative_items": negatives,
            "reference_loss": self.reference_loss, "forward_seconds": forward_seconds,
            "jvp_seconds": jvp_seconds, "last_projection_seconds": last_projection_seconds,
            "candidates": observations, "selection": _selection_statistics(observations),
        }
