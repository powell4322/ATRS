"""Separate full-ranking and sampled-ranking protocols."""
from __future__ import annotations

import math
import random

import torch

from .data import Split, left_pad


@torch.no_grad()
def evaluate(model, split: Split, *, mode: str, fold: str = "test",
             teacher=None, sampled_negatives: int = 100,
             seed: int = 42, device: str = "cpu", batch_size: int = 128) -> dict[str, float | int | str]:
    """Evaluate one positive per user.

    Full ranking excludes items in the evaluation prefix and re-includes the
    held-out target even if it repeats. Sampled mode uses a fixed 100-negative
    candidate set drawn outside every interaction in that user's full history.
    Teacher/student agreement is computed over the same candidate universe.
    """
    if mode not in {"full", "sampled"} or fold not in {"valid", "test"}:
        raise ValueError("invalid mode/fold")
    model = model.to(device).eval()
    if teacher is not None:
        teacher = teacher.to(device).eval()
    totals = {"hr@10": 0.0, "ndcg@10": 0.0, "agr@1": 0.0, "agr@10": 0.0}
    users = split.users
    for start in range(0, len(users), batch_size):
        part = users[start:start + batch_size]
        histories = [split.train[user] + ([split.valid[user]] if fold == "test" else [])
                     for user in part]
        targets = [split.valid[user] if fold == "valid" else split.test[user] for user in part]
        masks = torch.zeros(len(part), split.n_items + 1, dtype=torch.bool, device=device)
        if mode == "full":
            masks[:, 1:] = True
            for row, (history, target) in enumerate(zip(histories, targets)):
                masks[row, history] = False
                masks[row, target] = True
        else:
            for row, (user, target) in enumerate(zip(part, targets)):
                excluded = set(split.train[user]) | {split.valid[user], split.test[user]}
                pool = [item for item in range(1, split.n_items + 1) if item not in excluded]
                negatives = random.Random(seed + user).sample(pool, min(sampled_negatives, len(pool)))
                masks[row, [target, *negatives]] = True
        tokens = torch.tensor([left_pad(history, model.max_len) for history in histories], device=device)
        scores = model.next_scores(tokens).masked_fill(~masks, -torch.inf)
        k = min(10, int(masks.sum(dim=1).min()))
        ranked = torch.argsort(scores, dim=1, descending=True, stable=True)[:, :k]
        target_tensor = torch.tensor(targets, device=device).unsqueeze(1)
        hits = ranked.eq(target_tensor)
        totals["hr@10"] += float(hits.any(dim=1).sum())
        positions = torch.arange(k, device=device) + 2
        totals["ndcg@10"] += float((hits / torch.log2(positions)).sum())
        if teacher is not None:
            teacher_tokens = torch.tensor([left_pad(history, teacher.max_len) for history in histories], device=device)
            teacher_scores = teacher.next_scores(teacher_tokens).masked_fill(~masks, -torch.inf)
            teacher_ranked = torch.argsort(teacher_scores, dim=1, descending=True, stable=True)[:, :k]
            totals["agr@1"] += float(ranked[:, 0].eq(teacher_ranked[:, 0]).sum())
            overlap = ranked.unsqueeze(2).eq(teacher_ranked.unsqueeze(1)).any(dim=2).sum(dim=1)
            totals["agr@10"] += float((overlap / k).sum())
    result = {key: value / len(split.users) for key, value in totals.items()}
    if teacher is None:
        result.pop("agr@1")
        result.pop("agr@10")
    return {"protocol": mode, "fold": fold, "users": len(split.users), **result}
