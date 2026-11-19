"""Small defender-side experiments. Run with python -m atrs.research."""
from __future__ import annotations

import argparse
import json
import math
import random
import time
import traceback
from pathlib import Path

import torch

from .api import RankingOracle
from .attacks import Sample, distill_epoch, generate_dfme
from .cli import _configuration, _configured_split, _identity, _load_teacher, _model, _save_queries
from .evaluation import evaluate
from .feedback_diagnostics import FeedbackDiagnosticOracle, trajectory_metrics
from .learning_progress import LearningProgressProbe
from .training import SASWindows, git_commit, set_seed, source_adamw


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def _oracle_settings(config, args):
    return {"k": config["api"]["topk"], "batch_size": config["api"]["batch_size"],
            "max_requests": args.sequences * args.length, "device": args.device}


def _generate(oracle, args, n_items, *, seed, initial_items=None):
    return generate_dfme(oracle, n_sequences=args.sequences, sequence_len=args.length,
                         n_items=n_items, rng=random.Random(seed), batch_size=32,
                         initial_items=initial_items)


def _student(config, args, n_items):
    set_seed(args.seed + 2001)
    student = _model(config, n_items).to(args.device)
    optimizer = source_adamw(student, lr=config["attacks"]["dfme"]["lr"],
                             weight_decay=config["training"]["weight_decay"])
    return student, optimizer


def _distill(config, args, student, optimizer, samples, *, epochs, component="total"):
    settings = config["attacks"]["dfme"]
    rng = random.Random(args.seed + 3001)
    losses = [
        distill_epoch(student, optimizer, samples, "dfme", batch_size=args.batch_size,
                      device=args.device, rng=rng, margin_rank=settings["margin_rank"],
                      margin_neg=settings["margin_neg"], component=component)
        for _ in range(epochs)
    ]
    return {"loss_by_epoch": losses, "training_steps": epochs * math.ceil(len(samples) / args.batch_size)}


def _metrics(config, args, student, teacher, split):
    return evaluate(student, split, mode="full", fold=args.fold, teacher=teacher,
                    device=args.device, batch_size=config["training"]["eval_batch_size"])


def _learning_progress(config, args, teacher, split, output):
    warmup_samples = []
    warmup_counts = None
    # Different initial IDs give the warm-up and probe trajectories disjoint raw prefixes.
    initial = random.Random(args.seed + 101).sample(range(1, split.n_items + 1), 2 * args.sequences)
    if args.warmup_epochs:
        warmup_oracle = RankingOracle(teacher, **_oracle_settings(config, args))
        warmup_samples = _generate(warmup_oracle, args, split.n_items, seed=args.seed + 102,
                                   initial_items=initial[:args.sequences])
        warmup_counts = warmup_oracle.counters()
        _save_queries(output / "warmup_queries.jsonl.gz", warmup_samples)
    oracle = RankingOracle(teacher, **_oracle_settings(config, args))
    probes = _generate(oracle, args, split.n_items, seed=args.seed + 103,
                       initial_items=initial[args.sequences:])
    student, optimizer = _student(config, args, split.n_items)
    warmup = _distill(config, args, student, optimizer, warmup_samples, epochs=args.warmup_epochs)

    reference_windows = SASWindows(split, max_len=min(args.reference_length, student.max_len), seed=args.seed)
    reference_indices = random.Random(args.seed + 104).sample(
        range(len(reference_windows)), min(len(reference_windows), args.reference_rows),
    )
    if not reference_indices:
        raise ValueError("T2–T4 needs at least one train-only reference window")
    rows = [reference_windows[index] for index in reference_indices]
    tokens, positives, negatives = (torch.stack(part).to(args.device) for part in zip(*rows))
    reference = tokens, positives[:, -1:], negatives[:, -1:]
    probe = LearningProgressProbe(student, reference, eta=args.eta)
    rng = random.Random(args.seed + 105)
    frozen = rng.sample(probes, min(args.queries, len(probes)))
    settings = config["attacks"]["dfme"]
    diagnostics = [
        probe.run(sample, head=args.head, per_edit=args.candidates, rng=rng,
                  margin_rank=settings["margin_rank"], margin_neg=settings["margin_neg"])
        for sample in frozen
    ]
    candidates = [row for case in diagnostics for row in case["candidates"]]
    return {
        "query_counts": oracle.counters(), "warmup_query_counts": warmup_counts,
        "warmup": warmup, "reference_window_indices": reference_indices,
        "defender_reference": "train-only next-item BCE with fixed train-only negatives",
        "projection_max_abs_error": max(abs(row["j_lp"] - row["j_lp_full_jvp"]) for row in candidates),
        "output_only_max_abs_error": max(abs(row["j_lp"] - row["j_lp_output_only"]) for row in candidates),
        "queries": diagnostics,
    }


def _feedback(config, args, teacher, split, output):
    manifest = {}
    cells = {}
    initial = random.Random(args.seed + 201).sample(range(1, split.n_items + 1), args.sequences)
    for generation in (0, 1):
        oracle = FeedbackDiagnosticOracle(
            teacher, head=args.head, replacements=args.replacements,
            generation_protected=bool(generation), seed=args.seed + 202,
            **_oracle_settings(config, args),
        )
        generated = _generate(oracle, args, split.n_items, seed=args.seed + 203, initial_items=initial)
        counts = oracle.counters()
        if counts["oracle_requests"] != args.sequences * args.length:
            raise RuntimeError("paired DFME trajectories must use the same unique-prefix budget")
        manifest[str(generation)] = {
            "query_counts": counts,
            "paired_views": len(oracle.views),
            "trajectory": trajectory_metrics(
                (prefix for prefix in oracle.views if len(prefix) == args.length), split.n_items,
            ),
        }
        for supervision in (0, 1):
            cell = f"B-{generation}{supervision}"
            samples = oracle.supervision(generated, protected=bool(supervision))
            query_sha = _save_queries(output / f"{cell}_queries.jsonl.gz", samples)
            student, optimizer = _student(config, args, split.n_items)
            progress = _distill(config, args, student, optimizer, samples, epochs=args.epochs)
            cells[cell] = {**progress, "metrics": _metrics(config, args, student, teacher, split),
                           "diagnostic_supervision_reads": len(samples), "query_sha256": query_sha}
    effects = {}
    for metric in ("hr@10", "ndcg@10", "agr@1", "agr@10"):
        clean, supervision, trajectory, joint = (cell["metrics"][metric] for cell in cells.values())
        effects[metric] = {
            "supervision_at_clean_trajectory": supervision - clean,
            "trajectory_at_clean_supervision": trajectory - clean,
            "supervision_main_effect": ((supervision - clean) + (joint - trajectory)) / 2,
            "trajectory_main_effect": ((trajectory - clean) + (joint - supervision)) / 2,
            "interaction": joint - trajectory - supervision + clean,
        }
    return {
        "generation": manifest, "cells": cells, "effects_protected_minus_clean": effects,
        "conditional_uniform_tv": args.replacements / config["api"]["topk"],
        "initial_items": initial, "diagnostic_dual_access": True,
    }


def _knowledge_value(config, args, teacher, split, output):
    oracle = RankingOracle(teacher, **_oracle_settings(config, args))
    samples = _generate(oracle, args, split.n_items, seed=args.seed + 401)
    digest = _save_queries(output / "clean_queries.jsonl.gz", samples)
    topk = oracle.k
    widths = sorted({width for width in (5, 10, 20, 50) if width < topk} | {topk})
    controls = [(f"top-{width}", 0, width, "total") for width in widths]
    if args.extended:
        controls.extend((f"rank-{lo + 1}-{hi}", lo, hi, "total")
                        for lo, hi in zip([0, *widths], widths))
        controls.extend((f"top-{topk}-{component}", 0, topk, component) for component in ("intra", "inter"))
    cells = {}
    for name, lo, hi, component in controls:
        student, optimizer = _student(config, args, split.n_items)
        supervision = [Sample(sample.prefix, sample.ranking[lo:hi]) for sample in samples]
        progress = _distill(config, args, student, optimizer, supervision,
                            epochs=args.epochs, component=component)
        cells[name] = {**progress, "metrics": _metrics(config, args, student, teacher, split),
                       "ranking_start": lo + 1, "ranking_end": hi, "loss_component": component}
    return {"query_counts": oracle.counters(), "query_sha256": digest, "cells": cells}


def _positive(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def _parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("t1", "t2-t4", "t5"):
        command = commands.add_parser(name)
        command.add_argument("--config", default="configs/phase1/ml1m_sasrec_seed42.json")
        command.add_argument("--output", type=Path, required=True)
        command.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
        command.add_argument("--seed", type=int, default=42, help="diagnostic seed, independent of teacher")
        command.add_argument("--sequences", type=_positive, default=8 if name == "t2-t4" else 24)
        command.add_argument("--length", type=_positive, default=16 if name == "t2-t4" else 40)
        command.add_argument("--batch-size", type=_positive, default=32, help="distillation batch size")
        if name == "t2-t4":
            command.add_argument("--queries", type=_positive, default=12)
            command.add_argument("--candidates", type=_positive, default=6, help="maximum candidates per edit type")
            command.add_argument("--head", type=_positive, default=10)
            command.add_argument("--reference-rows", type=_positive, default=8)
            command.add_argument("--reference-length", type=_positive, default=50)
            command.add_argument("--eta", type=float, default=0.001, help="counterfactual SGD learning rate")
            command.add_argument("--warmup-epochs", type=int, default=0)
        else:
            command.add_argument("--epochs", type=_positive, default=2)
            command.add_argument("--fold", choices=("valid", "test"), default="valid")
        if name == "t1":
            command.add_argument("--extended", action="store_true", help="also test intervals and isolated loss terms")
        if name == "t5":
            command.add_argument("--head", type=_positive, default=10)
            command.add_argument("--replacements", type=_positive, default=10)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    config = _configuration(args.config)
    split = _configured_split(config)
    k = config["api"]["topk"]
    cap = config["api"]["max_requests"]
    if args.length < 2 or (cap is not None and args.sequences * args.length > cap):
        raise ValueError("require length >= 2 and sequences * length <= the configured request cap")
    if args.command == "t2-t4":
        if (not math.isfinite(args.eta) or args.eta <= 0 or args.warmup_epochs < 0
                or k - args.head < 2 or 2 * k >= split.n_items or 2 * args.sequences > split.n_items):
            raise ValueError("T2–T4 needs eta > 0, nonnegative warm-up, at least two editable ranks, "
                             "and a catalog larger than twice K with room for two sets of starts")
    if args.command == "t5":
        if (args.replacements > min(k - args.head, split.n_items - k)
                or args.sequences > split.n_items):
            raise ValueError("T5 replacements must fit the tail and outside catalog, and starts must be unique")
    teacher, checkpoint, state = _load_teacher(config, split, "none", Path(config["run_root"]), args.device)
    args.output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "usage": "defender mechanism diagnostic; excluded from formal attack training and selection",
        "arguments": {**vars(args), "output": str(args.output)},
        "teacher_config": config, "teacher_checkpoint": str(checkpoint),
        "teacher_sha256": _identity(checkpoint), "teacher_epoch": state["epoch"],
        "data_sha256": split.source_sha256, "git_commit": git_commit(),
        "torch_version": str(torch.__version__), "cuda_version": torch.version.cuda,
    }
    _write_json(args.output / "config.json", manifest)
    started = time.perf_counter()
    function = {"t1": _knowledge_value, "t2-t4": _learning_progress, "t5": _feedback}[args.command]
    try:
        result = function(config, args, teacher, split, args.output)
        _write_json(args.output / "result.json", {**result, "seconds": time.perf_counter() - started})
    except Exception:
        (args.output / "error.log").write_text(traceback.format_exc(), encoding="utf-8")
        raise
    print(args.output / "result.json")


if __name__ == "__main__":
    main()
