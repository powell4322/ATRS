"""Causal SASRec matching the DFME/BECOME source model structure.

This is a fresh implementation of the two-block, two-head SASRec used by the
reference extraction code: tied item scores, length-relative positions,
causal attention, residual norms, 1x1 feed-forward layers, BCE training.
"""
from __future__ import annotations

import math

import torch
from torch import nn
from torch.nn import functional as F


class _SourceLayerNorm(nn.Module):
    """The reference model normalizes by sample std rather than population std."""
    def __init__(self, width: int):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(width))
        self.bias = nn.Parameter(torch.zeros(width))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        mean = x.mean(-1, keepdim=True)
        std = x.std(-1, keepdim=True, correction=1)
        return self.weight * (x - mean) / (std + 1e-6) + self.bias


class _SASBlock(nn.Module):
    def __init__(self, hidden: int, heads: int, dropout: float, attention_dropout: float):
        super().__init__()
        if hidden % heads:
            raise ValueError("hidden must be divisible by heads")
        self.heads = heads
        self.head_width = hidden // heads
        self.before_attention_norm = _SourceLayerNorm(hidden)
        self.query = nn.Linear(hidden, hidden)
        self.key = nn.Linear(hidden, hidden)
        self.value = nn.Linear(hidden, hidden)
        self.attention_dropout = nn.Dropout(attention_dropout)
        self.after_attention_norm = _SourceLayerNorm(hidden)
        self.feed_in = nn.Conv1d(hidden, hidden * 4, kernel_size=1)
        self.feed_out = nn.Conv1d(hidden * 4, hidden, kernel_size=1)
        self.feed_dropout = nn.Dropout(dropout)
        self.after_feed_norm = _SourceLayerNorm(hidden)

    def forward(self, x: torch.Tensor, valid_keys: torch.Tensor) -> torch.Tensor:
        batch, length, hidden = x.shape
        q_input = self.before_attention_norm(x)
        q = self.query(q_input).reshape(batch, length, self.heads, self.head_width).transpose(1, 2)
        k = self.key(x).reshape(batch, length, self.heads, self.head_width).transpose(1, 2)
        v = self.value(x).reshape(batch, length, self.heads, self.head_width).transpose(1, 2)
        logits = q @ k.transpose(-1, -2) / math.sqrt(self.head_width)
        causal = torch.tril(torch.ones(length, length, dtype=torch.bool, device=x.device))
        allowed = causal[None, None, :, :] & valid_keys[:, None, None, :]
        logits = logits.masked_fill(~allowed, -1e9)
        context = self.attention_dropout(logits.softmax(-1)) @ v
        context = context.transpose(1, 2).reshape(batch, length, hidden)
        # The source attention residual adds the normalized query input.
        x = self.after_attention_norm(context + q_input)
        fed = self.feed_in(x.transpose(1, 2))
        fed = self.feed_dropout(F.relu(fed))
        fed = self.feed_out(fed).transpose(1, 2)
        return self.after_feed_norm(x + self.feed_dropout(fed))


class SASRec(nn.Module):
    def __init__(self, n_items: int, max_len: int = 400, hidden: int = 64,
                 layers: int = 2, heads: int = 2, dropout: float = 0.1,
                 attention_dropout: float | None = None):
        super().__init__()
        self.n_items = n_items
        self.max_len = max_len
        self.hidden = hidden
        self.heads = heads
        self.dropout_rate = dropout
        self.attention_dropout_rate = attention_dropout if attention_dropout is not None else dropout
        self.item = nn.Embedding(n_items + 1, hidden, padding_idx=0)
        self.position = nn.Embedding(max_len + 1, hidden)
        self.dropout = nn.Dropout(dropout)
        self.blocks = nn.ModuleList([
            _SASBlock(hidden, heads, dropout, self.attention_dropout_rate)
            for _ in range(layers)
        ])
        # Reference code uses truncated-normal initialization for transformer
        # weights, while keeping embedding module defaults.
        for name, parameter in self.blocks.named_parameters():
            if "norm" not in name and parameter.ndim > 1:
                nn.init.trunc_normal_(parameter, std=0.02, a=-0.04, b=0.04)

    def encode(self, tokens: torch.Tensor) -> torch.Tensor:
        if tokens.ndim != 2 or tokens.size(1) > self.max_len:
            raise ValueError("tokens must have shape [batch, length <= max_len]")
        valid = tokens.gt(0)
        if (~valid).all(dim=1).any():
            raise ValueError("every sequence must contain at least one item")
        positions = valid.long().cumsum(-1) * valid.long()
        x = self.dropout(self.item(tokens) + self.position(positions))
        for block in self.blocks:
            x = block(x, valid)
        return x

    def forward(self, tokens: torch.Tensor) -> torch.Tensor:
        return self.encode(tokens) @ self.item.weight.T

    def next_scores(self, tokens: torch.Tensor) -> torch.Tensor:
        return self.forward(tokens)[:, -1, :]

    def bce_loss(self, tokens: torch.Tensor, positives: torch.Tensor,
                 negatives: torch.Tensor) -> torch.Tensor:
        scores = self.forward(tokens)
        positive_scores = scores.gather(-1, positives.unsqueeze(-1)).squeeze(-1)
        negative_scores = scores.gather(-1, negatives.unsqueeze(-1)).squeeze(-1)
        valid = positives.ne(0)
        if not valid.any():
            raise ValueError("batch has no training targets")
        selected = torch.cat([positive_scores[valid], negative_scores[valid]])
        targets = torch.cat([torch.ones_like(positive_scores[valid]),
                             torch.zeros_like(negative_scores[valid])])
        return F.binary_cross_entropy_with_logits(selected, targets)

    def config(self) -> dict:
        return {"n_items": self.n_items, "max_len": self.max_len,
                "hidden": self.hidden, "layers": len(self.blocks),
                "heads": self.heads, "dropout": self.dropout_rate,
                "attention_dropout": self.attention_dropout_rate}
