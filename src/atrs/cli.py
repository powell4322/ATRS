"""Noninteractive phase-I experiment commands. Run with ``python -m atrs.cli``."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import random
import time
from pathlib import Path

import torch
from torch.utils.data import DataLoader

from .api import RankingOracle
from .attacks import distill_epoch, generate_become, generate_dfme, run_sim4rec
from .data import load_split
from .evaluation import evaluate
from .gro import gro_step
from .model import SASRec
from .training import (SASWindows, append_jsonl, load_checkpoint, save_checkpoint,
                       set_seed, source_adamw)


def _configuration(path: str) -> dict:
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    if config["dataset"] != "ml-1m" or config["backbone"] != "sasrec":
        raise ValueError("phase I currently supports ML-1M + SASRec only")
    return config


def _model(config: dict, n_items: int) -> SASRec:
    return SASRec(n_items=n_items, **config["model"])


def _checkpoint_path(root: Path, defense: str) -> Path:
    return root / "checkpoints" / f"teacher_{defense}.pt"


def _identity(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _save_queries(path: Path, samples) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", newline="\n") as stream:
                for sample in samples:
                    stream.write(json.dumps({"prefix": sample.prefix, "ranking": sample.ranking}) + "\n")
    return _identity(path)


def _fit_teacher(config: dict, split, defense: str, run_root: Path,
                 device: str, epochs_override: int | None, resume: bool) -> None:
    if defense not in {"none", "gro", "continued-clean"}:
        raise ValueError(defense)
    seed = config["seed"]
    set_seed(seed)
    model = _model(config, split.n_items).to(device)
    settings = config["training"]
    optimizer = source_adamw(model, lr=settings["lr"],
                             weight_decay=settings["weight_decay"])
    local_student = None
    local_optimizer = None
    if defense == "gro":
        torch.manual_seed(seed + 1001)
        local_student = _model(config, split.n_items).to(device)
        local_optimizer = source_adamw(local_student, lr=settings["lr"],
                                       weight_decay=settings["weight_decay"])
        set_seed(seed)
    checkpoint = _checkpoint_path(run_root, defense)
    start_epoch = 0
    if resume and checkpoint.exists():
        payload = load_checkpoint(checkpoint, model=model, optimizer=optimizer,
                                  student=local_student, student_optimizer=local_optimizer,
                                  map_location=device)
        start_epoch = payload["epoch"]
    elif defense != "none":
        clean = _checkpoint_path(run_root, "none")
        if not clean.exists():
            raise FileNotFoundError(f"train the clean teacher first: {clean}")
        payload = load_checkpoint(clean, model=model, map_location=device)
        if payload["metadata"]["data_sha256"] != split.source_sha256:
            raise ValueError("clean checkpoint uses a different dataset")
    windows = SASWindows(split, max_len=model.max_len, seed=seed,
                         sliding_fraction=settings["sliding_fraction"])
    if not windows:
        raise ValueError("dataset has no training windows")
    count_epochs = epochs_override if epochs_override is not None else (
        settings["clean_epochs"] if defense == "none" else settings["finetune_epochs"])
    best_ndcg = -1.0
    best_path = checkpoint.with_name(checkpoint.stem + "_best.pt")
    if resume and best_path.exists():
        best_payload = torch.load(best_path, map_location="cpu", weights_only=False)
        best_ndcg = best_payload.get("metadata", {}).get("validation_ndcg", -1.0)
    stale_epochs = 0
    for epoch in range(start_epoch, count_epochs):
        windows.epoch = epoch
        loader = DataLoader(windows, batch_size=settings["batch_size"], shuffle=True,
                            num_workers=0)
        started = time.perf_counter()
        sums: dict[str, float] = {}
        steps = 0
        for tokens, positives, negatives in loader:
            tokens, positives, negatives = (x.to(device) for x in (tokens, positives, negatives))
            if defense == "gro":
                values = gro_step(model, local_student, optimizer, local_optimizer,
                                  tokens, positives, negatives,
                                  topk=config["api"]["topk"],
                                  margin_rank=config["gro"]["margin_rank"],
                                  margin_neg=config["gro"]["margin_neg"],
                                  margin_swap=config["gro"]["margin_swap"],
                                  swap_weight=config["gro"]["swap_weight"])
            else:
                model.train()
                optimizer.zero_grad(set_to_none=True)
                loss = model.bce_loss(tokens, positives, negatives)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 5)
                optimizer.step()
                values = {"total": float(loss.detach())}
            for key, value in values.items():
                sums[key] = sums.get(key, 0) + value
            steps += 1
        validation = evaluate(model, split, mode="full", fold="valid", device=device,
                              batch_size=settings["eval_batch_size"])
        record = {"event": "teacher_epoch", "dataset": config["dataset"],
                  "defense": defense, "seed": seed, "epoch": epoch + 1,
                  "loss": {key: value / steps for key, value in sums.items()},
                  "validation": validation, "seconds": time.perf_counter() - started,
                  "data_sha256": split.source_sha256}
        append_jsonl(run_root / "logs" / f"teacher_{defense}.jsonl", record)
        save_checkpoint(checkpoint, model=model, optimizer=optimizer, epoch=epoch + 1,
                        metadata={"defense": defense, "data_sha256": split.source_sha256,
                                  "validation_ndcg": validation["ndcg@10"]},
                        student=local_student, student_optimizer=local_optimizer)
        if validation["ndcg@10"] > best_ndcg:
            best_ndcg = validation["ndcg@10"]
            stale_epochs = 0
            save_checkpoint(best_path, model=model, optimizer=optimizer, epoch=epoch + 1,
                            metadata={"defense": defense, "data_sha256": split.source_sha256,
                                      "validation_ndcg": validation["ndcg@10"]},
                            student=local_student, student_optimizer=local_optimizer)
        else:
            stale_epochs += 1
        print(json.dumps(record, ensure_ascii=False))
        if stale_epochs >= settings["patience"]:
            break


def _run_attack(config: dict, split, defense: str, attack: str,
                run_root: Path, device: str) -> None:
    set_seed(config["seed"])
    teacher_checkpoint = _checkpoint_path(run_root, defense).with_name(f"teacher_{defense}_best.pt")
    teacher = _model(config, split.n_items).to(device)
    teacher_state = load_checkpoint(teacher_checkpoint, model=teacher, map_location=device)
    if teacher_state["metadata"]["data_sha256"] != split.source_sha256:
        raise ValueError("teacher checkpoint uses a different dataset")
    teacher.eval()
    torch.manual_seed(config["seed"] + 2001)
    student = _model(config, split.n_items).to(device)
    optimizer = source_adamw(student, lr=config["attacks"][attack]["lr"],
                             weight_decay=config["training"]["weight_decay"])
    api = config["api"]
    oracle = RankingOracle(teacher, k=api["topk"],
                           max_requests=api["max_requests"],
                           batch_size=api["batch_size"], device=device)
    settings = config["attacks"][attack]
    rng = random.Random(config["seed"] + 3001)
    start = time.perf_counter()
    if attack == "dfme":
        samples = generate_dfme(oracle, n_sequences=settings["n_sequences"],
                                sequence_len=settings["sequence_len"],
                                n_items=split.n_items, rng=rng,
                                batch_size=settings["generation_batch_size"])
        losses = [distill_epoch(student, optimizer, samples, "dfme",
                               batch_size=settings["batch_size"], device=device,
                               rng=rng, margin_rank=settings["margin_rank"],
                               margin_neg=settings["margin_neg"], beta=None)
                  for _ in range(settings["epochs"])]
    elif attack == "become":
        samples, losses = generate_become(oracle, student, optimizer,
                                          n_sequences=settings["n_sequences"],
                                          sequence_len=settings["sequence_len"],
                                          n_items=split.n_items, rng=rng,
                                          phases=settings["phases"],
                                          initial_fraction=settings["initial_fraction"],
                                          select_fraction=settings["select_fraction"],
                                          alpha=settings["alpha"],
                                          distill_epochs_per_phase=settings["epochs_per_phase"],
                                          batch_size=settings["batch_size"], device=device,
                                          margin_rank=settings["margin_rank"],
                                          margin_neg=settings["margin_neg"], beta=settings["beta"])
    elif attack == "sim4rec":
        samples, losses, generator = run_sim4rec(
            oracle, student, optimizer, n_seed_sequences=settings["n_seed_sequences"],
            sequence_len=settings["sequence_len"], n_items=split.n_items,
            rng=rng, pretrain_epochs=settings["pretrain_epochs"],
            adversarial_rounds=settings["adversarial_rounds"],
            round_batch=settings["round_batch"], memory_batches=settings["memory_batches"],
            distill_epochs_per_round=settings["epochs_per_round"],
            batch_size=settings["batch_size"], device=device)
    else:
        raise ValueError(attack)
    query_path = run_root / "queries" / f"{defense}_{attack}.jsonl.gz"
    query_sha256 = _save_queries(query_path, samples)
    out = run_root / "checkpoints" / f"student_{defense}_{attack}.pt"
    save_checkpoint(out, model=student, optimizer=optimizer, epoch=len(losses),
                    metadata={"attack": attack, "defense": defense,
                              "data_sha256": split.source_sha256,
                              "teacher_sha256": _identity(teacher_checkpoint),
                              "query_dataset_sha256": query_sha256,
                              "oracle_counts": oracle.counters()})
    teacher_metrics = evaluate(teacher, split, mode="full", teacher=None,
                               device=device, batch_size=config["training"]["eval_batch_size"])
    student_metrics = evaluate(student, split, mode="full", teacher=teacher,
                               device=device, batch_size=config["training"]["eval_batch_size"])
    sampled_metrics = evaluate(student, split, mode="sampled", teacher=teacher,
                               device=device, batch_size=config["training"]["eval_batch_size"])
    result = {"dataset": config["dataset"], "backbone": config["backbone"],
              "defense": defense, "attack": attack, "seed": config["seed"],
              "teacher_checkpoint": str(teacher_checkpoint),
              "teacher_sha256": _identity(teacher_checkpoint),
              "student_checkpoint": str(out), "student_sha256": _identity(out),
              "query_dataset": str(query_path), "query_dataset_sha256": query_sha256,
              "data_sha256": split.source_sha256,
              "budget_definition": "actual unique prefix requests to ranking-only oracle",
              "query_counts": oracle.counters(), "teacher_full": teacher_metrics,
              "student_full": student_metrics, "student_sampled": sampled_metrics,
              "last_distillation_loss": losses[-1] if losses else None,
              "seconds": time.perf_counter() - start}
    path = run_root / "results" / f"{defense}_{attack}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["preprocess", "train-teacher", "run-attack"])
    parser.add_argument("--config", default="experiments/ml1m_sasrec.json")
    parser.add_argument("--defense", choices=["none", "gro", "continued-clean"])
    parser.add_argument("--attack", choices=["dfme", "become", "sim4rec"])
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--epochs", type=int)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    config = _configuration(args.config)
    split = load_split(config["data_path"])
    root = Path(config["run_root"])
    split.save_metadata(root / "data_metadata.json")
    if args.command == "preprocess":
        print(json.dumps(split.metadata(), indent=2))
    elif args.command == "train-teacher":
        if args.defense is None:
            parser.error("--defense is required")
        _fit_teacher(config, split, args.defense, root, args.device, args.epochs, args.resume)
    else:
        if args.defense is None or args.attack is None:
            parser.error("--defense and --attack are required")
        _run_attack(config, split, args.defense, args.attack, root, args.device)


if __name__ == "__main__":
    main()
