"""GRO training step, adapted to a causal SASRec teacher.

Paper: Zhang et al., WSDM 2024, Eq. 4-6. GRO's published experiments use
BERT4Rec, so this SASRec application is a backbone transfer, not a native run.
"""
from __future__ import annotations

import torch
from torch.nn import functional as F

from .attacks import negatives_outside_topk


def gro_step(teacher, student, teacher_optimizer, student_optimizer,
             tokens: torch.Tensor, positives: torch.Tensor,
             negatives: torch.Tensor, *, topk: int = 100,
             margin_rank: float = 0.5, margin_neg: float = 0.5,
             margin_swap: float = 0.5, swap_weight: float = 0.01) -> dict[str, float]:
    """One joint teacher/student update with a dense swap matrix.

    The local student is initialized independently and discarded after GRO.
    It receives rankings on private teacher-training prefixes; it is never
    reused as an external attack student.
    """
    teacher.train()
    student.train()
    teacher_optimizer.zero_grad(set_to_none=True)
    student_optimizer.zero_grad(set_to_none=True)
    target_loss = teacher.bce_loss(tokens, positives, negatives)
    teacher_scores = teacher.next_scores(tokens)
    k = min(topk, teacher.n_items - 1)
    if k < 2:
        raise ValueError("GRO needs at least two ranked items and one negative")
    ranking = torch.argsort(teacher_scores[:, 1:].detach(), dim=1,
                            descending=True, stable=True)[:, :k] + 1
    batch, n_items_plus_pad = teacher_scores.shape
    swap = torch.zeros(batch, k, n_items_plus_pad, device=tokens.device,
                       dtype=teacher_scores.dtype)
    swap.scatter_(2, ranking.unsqueeze(-1), 1)
    swap.requires_grad_(True)
    student_scores = student.next_scores(tokens)
    ranked_student_scores = torch.bmm(swap, student_scores.unsqueeze(-1)).squeeze(-1)
    negatives_ranked = negatives_outside_topk(ranking, teacher.n_items, k)
    negative_scores = student_scores.gather(1, negatives_ranked)
    student_loss = (F.relu(ranked_student_scores[:, 1:] - ranked_student_scores[:, :-1]
                           + margin_rank).mean()
                    + F.relu(negative_scores - ranked_student_scores + margin_neg).mean())
    ranking_grad = torch.autograd.grad(student_loss, swap, retain_graph=True)[0].detach()
    ranking_grad[:, :, 0] = -torch.inf  # padding is not a candidate
    replacement = ranking_grad.argmax(dim=2)
    original_target = teacher_scores.gather(1, ranking)
    replacement_target = teacher_scores.gather(1, replacement)
    swap_loss = F.relu(original_target - replacement_target + margin_swap).mean()
    total = target_loss + student_loss + swap_weight * swap_loss
    total.backward()
    torch.nn.utils.clip_grad_norm_(teacher.parameters(), 5)
    torch.nn.utils.clip_grad_norm_(student.parameters(), 5)
    teacher_optimizer.step()
    student_optimizer.step()
    return {"target": float(target_loss.detach()),
            "student": float(student_loss.detach()),
            "swap": float(swap_loss.detach()),
            "total": float(total.detach())}
