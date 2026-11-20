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
from .attacks import distill_epoch, generate_become, generate_dfme, generate_random
from .data import load_split
from .evaluation import evaluate
from .gro import gro_step
from .model import SASRec
from .training import (SASWindows, append_jsonl, git_commit, load_checkpoint,
                       linear_warmup_decay, save_checkpoint, set_seed, source_optimizer)


def _configuration(path: str) -> dict:
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    if config["dataset"] != "ml-1m" or config["backbone"] != "sasrec":
        raise ValueError("the current runnable model/data entry supports ML-1M + SASRec")
    if config.get("protocol") == "unified-defense-v1":
        if (config["api"]["topk"] != 100 or config["evaluation"]["mode"] != "full"
                or config["evaluation"]["agreement_reference"] != "clean"
                or config["evaluation"]["history_filter"] != "exclude_seen_restore_target"
                or config["evaluation"]["k"] != 10):
            raise ValueError("formal protocol requires Top-100, full ranking and clean-reference Agreement")
        if any(settings["n_sequences"] < 1 for settings in config["attacks"].values()):
            raise ValueError("nominal sequence budgets must be positive")
        if config["attacks"]["become"].get("scheduler", "constant") != "constant":
            raise ValueError("the implemented BECOME phase loop supports its constant scheduler")
        for attack in ("random", "dfme"):
            if config["attacks"][attack].get("scheduler", "constant") not in {"constant", "linear_warmup_decay"}:
                raise ValueError(f"unsupported scheduler for {attack}")
    config["_config_sha256"] = _identity(Path(path))
    return config


def _configured_split(config: dict):
    split = load_split(config["data_path"])
    expected_hash = config.get("expected_data_sha256")
    if expected_hash and split.source_sha256 != expected_hash:
        raise ValueError(f"dataset SHA-256 mismatch: expected {expected_hash}, got {split.source_sha256}")
    return split


def _model(config: dict, n_items: int) -> SASRec:
    return SASRec(n_items=n_items, **config["model"])


def _checkpoint_path(root: Path, defense: str, *, best: bool = False) -> Path:
    return root / "checkpoints" / f"teacher_{defense}{'_best' if best else ''}.pt"


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


def _load_teacher(config, split, defense, run_root, device):
    path = _checkpoint_path(run_root, defense, best=True)
    if not path.is_file():
        raise FileNotFoundError(f"train the {defense} teacher first: {path}")
    model = _model(config, split.n_items).to(device)
    state = load_checkpoint(path, model=model, restore_rng=False)
    metadata = state["metadata"]
    if (metadata.get("data_sha256") != split.source_sha256
            or metadata.get("config_sha256") != config["_config_sha256"]):
        raise ValueError(f"checkpoint dataset or configuration differs: {path}")
    return model, path, state


def _fit_teacher(config: dict, split, defense: str, run_root: Path,
                 device: str, epochs_override: int | None, resume: bool) -> None:
    if defense not in {"none", "gro", "continued-clean"}:
        raise ValueError(defense)
    seed = config["seed"]
    set_seed(seed)
    checkpoint = _checkpoint_path(run_root, defense)
    best_path = _checkpoint_path(run_root, defense, best=True)
    if not resume and (checkpoint.exists() or best_path.exists()):
        raise FileExistsError(f"teacher outputs already exist: use --resume or a new run_root ({run_root})")
    model = _model(config, split.n_items).to(device)
    settings = config["training"]
    optimizer = source_optimizer(model, lr=settings["lr"], weight_decay=settings["weight_decay"],
                                 name=settings.get("optimizer", "adamw"))
    local_student = None
    local_optimizer = None
    if defense == "gro":
        torch.manual_seed(seed + 1001)
        local_student = _model(config, split.n_items).to(device)
        local_optimizer = source_optimizer(local_student, lr=settings["lr"],
                                           weight_decay=settings["weight_decay"],
                                           name=settings.get("optimizer", "adamw"))
        set_seed(seed)
    parent = {}
    if defense != "none":
        _, clean, clean_state = _load_teacher(config, split, "none", run_root, "cpu")
        parent = {"clean_parent_sha256": _identity(clean), "clean_parent_epoch": clean_state["epoch"],
                  "clean_parent_validation_ndcg": clean_state["metadata"].get("validation_ndcg")}
    start_epoch = 0
    stale_epochs = 0
    if resume and checkpoint.exists():
        payload = load_checkpoint(checkpoint, model=model, optimizer=optimizer,
                                  student=local_student, student_optimizer=local_optimizer)
        if (payload["metadata"].get("data_sha256") != split.source_sha256
                or payload["metadata"].get("config_sha256") != config["_config_sha256"]):
            raise ValueError("checkpoint dataset or configuration differs from this run")
        if parent and payload["metadata"].get("clean_parent_sha256") != parent["clean_parent_sha256"]:
            raise ValueError("fine-tuning checkpoint has a different or unrecorded clean parent; use a new run_root")
        start_epoch = payload["epoch"]
        stale_epochs = payload["metadata"].get("stale_epochs", 0)
    elif defense != "none":
        model.load_state_dict(clean_state["model"])
        set_seed(seed)
    windows = SASWindows(split, max_len=model.max_len, seed=seed,
                         sliding_fraction=settings["sliding_fraction"])
    if not windows:
        raise ValueError("dataset has no training windows")
    count_epochs = epochs_override if epochs_override is not None else (
        settings["clean_epochs"] if defense == "none" else settings["finetune_epochs"])
    scheduler = None
    scheduler_name = (settings.get("scheduler", "constant") if defense == "none"
                      else settings.get("finetune_scheduler", "constant"))
    warmup_steps = (settings.get("warmup_steps", 0) if defense == "none"
                    else settings.get("finetune_warmup_steps", 0))
    if scheduler_name == "linear_warmup_decay":
        total_steps = count_epochs * ((len(windows) + settings["batch_size"] - 1) // settings["batch_size"])
        scheduler = linear_warmup_decay(optimizer, warmup_steps=warmup_steps,
                                        total_steps=total_steps)
        if start_epoch:
            scheduler.load_state_dict(payload["scheduler"])
            for group, lr in zip(optimizer.param_groups, scheduler.get_last_lr()):
                group["lr"] = lr
    best_ndcg = -1.0
    if start_epoch and best_path.exists():
        best_payload = torch.load(best_path, map_location="cpu", weights_only=False)
        best_ndcg = best_payload.get("metadata", {}).get("validation_ndcg", -1.0)
    if start_epoch and payload["metadata"].get("validation_ndcg", -1.0) > best_ndcg:
        # Recover when the previous process saved latest and stopped before publishing best.
        best_ndcg = payload["metadata"]["validation_ndcg"]
        save_checkpoint(best_path, model=model, optimizer=optimizer, epoch=start_epoch,
                        metadata=payload["metadata"], student=local_student, student_optimizer=local_optimizer,
                        scheduler=scheduler)
    for epoch in range(start_epoch, count_epochs):
        if settings["patience"] is not None and stale_epochs >= settings["patience"]:
            break
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
                                  swap_weight=config["gro"]["swap_weight"],
                                  loss_normalization=config["gro"].get("loss_normalization", "mean"))
            else:
                model.train()
                optimizer.zero_grad(set_to_none=True)
                loss = model.bce_loss(tokens, positives, negatives)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 5)
                optimizer.step()
                values = {"total": float(loss.detach())}
            if scheduler is not None:
                scheduler.step()
            for key, value in values.items():
                sums[key] = sums.get(key, 0) + value
            steps += 1
        validation = evaluate(model, split, mode="full", fold="valid", device=device,
                              batch_size=settings["eval_batch_size"])
        record = {"event": "teacher_epoch", "dataset": config["dataset"],
                  "defense": defense, "seed": seed, "epoch": epoch + 1,
                  "git_commit": git_commit(),
                  "loss": {key: value / steps for key, value in sums.items()},
                  "validation": validation, "seconds": time.perf_counter() - started,
                  "data_sha256": split.source_sha256,
                  "config_sha256": config["_config_sha256"], "training_steps": steps, **parent}
        append_jsonl(run_root / "logs" / f"teacher_{defense}.jsonl", record)
        improved = validation["ndcg@10"] > best_ndcg
        if improved:
            best_ndcg = validation["ndcg@10"]
            stale_epochs = 0
        else:
            stale_epochs += 1
        metadata = {"defense": defense, "data_sha256": split.source_sha256,
                    "config_sha256": config["_config_sha256"],
                    "validation_ndcg": validation["ndcg@10"], "stale_epochs": stale_epochs,
                    "training_steps": (epoch + 1) * steps, **parent}
        save_checkpoint(checkpoint, model=model, optimizer=optimizer, epoch=epoch + 1,
                        metadata=metadata, student=local_student, student_optimizer=local_optimizer,
                        scheduler=scheduler)
        if improved:
            save_checkpoint(best_path, model=model, optimizer=optimizer, epoch=epoch + 1,
                            metadata=metadata, student=local_student, student_optimizer=local_optimizer,
                            scheduler=scheduler)
        print(json.dumps(record, ensure_ascii=False))


def _run_attack(config: dict, split, defense: str, attack: str,
                run_root: Path, device: str) -> None:
    set_seed(config["seed"])
    teacher, teacher_checkpoint, teacher_state = _load_teacher(config, split, defense, run_root, device)
    teacher_sha256 = _identity(teacher_checkpoint)
    clean_parent_sha256 = teacher_state["metadata"].get("clean_parent_sha256")
    if defense != "none" and clean_parent_sha256 != _identity(_checkpoint_path(run_root, "none", best=True)):
        raise ValueError("defended teacher has a different or unrecorded clean parent")
    teacher.eval()
    reference, reference_checkpoint, _ = _load_teacher(config, split, "none", run_root, device)
    reference_sha256 = _identity(reference_checkpoint)
    formal = config.get("protocol") == "unified-defense-v1"
    settings = config["attacks"][attack]
    torch.manual_seed(config["seed"] + 2001)
    student = _model(config, split.n_items).to(device)
    optimizer = source_optimizer(student, lr=settings["lr"],
                                 weight_decay=config["training"]["weight_decay"],
                                 name=settings.get("optimizer", config["training"].get("optimizer", "adamw")))
    training_steps = 0

    def count_step(*_):
        nonlocal training_steps
        training_steps += 1

    handle = optimizer.register_step_post_hook(count_step)
    api = config["api"]
    oracle = RankingOracle(teacher, k=api["topk"],
                           max_requests=api["max_requests"],
                           batch_size=api["batch_size"], cache=api.get("cache", True), device=device)
    rng = random.Random(config["seed"] + 3001)
    start = time.perf_counter()

    def log_progress(values):
        record = {"event": "attack_epoch", "defense": defense, "attack": attack,
                  "seed": config["seed"], "training_steps": training_steps,
                  "seconds": time.perf_counter() - start, **values}
        append_jsonl(run_root / "logs" / f"student_{defense}_{attack}.jsonl", record)
        print(json.dumps(record, ensure_ascii=False), flush=True)
    if attack in {"random", "dfme"}:
        generator = generate_random if attack == "random" else generate_dfme
        samples = generator(oracle, n_sequences=settings["n_sequences"],
                                sequence_len=settings["sequence_len"],
                                n_items=split.n_items, rng=rng,
                                batch_size=settings["generation_batch_size"])
        scheduler = None
        if settings.get("scheduler") == "linear_warmup_decay":
            total_steps = settings["epochs"] * ((len(samples) + settings["batch_size"] - 1) // settings["batch_size"])
            scheduler = linear_warmup_decay(optimizer, warmup_steps=settings["warmup_steps"],
                                            total_steps=total_steps)
        losses = []
        for epoch in range(settings["epochs"]):
            losses.append(distill_epoch(
                student, optimizer, samples, attack,
                batch_size=settings["batch_size"], device=device, rng=rng,
                margin_rank=settings["margin_rank"], margin_neg=settings["margin_neg"], beta=None,
                negative_sampling=settings.get("negative_sampling", "outside_topk"),
                scheduler=scheduler,
            ))
            log_progress({"phase": None, "epoch": epoch + 1, "epochs": settings["epochs"],
                          "loss": losses[-1], "training_rows": len(samples)})
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
                                          margin_neg=settings["margin_neg"], beta=settings["beta"],
                                          progress=log_progress,
                                          **{key: settings[key] for key in (
                                              "phase_mean", "phase_std", "feedback_k",
                                              "negative_sampling", "negatives_per_positive",
                                              "final_phase_epochs", "terminal_holdout", "frequency_policy",
                                              "phase_rounding") if key in settings})
    else:
        raise ValueError(attack)
    handle.remove()
    query_path = run_root / "queries" / f"{defense}_{attack}.jsonl.gz"
    query_sha256 = _save_queries(query_path, samples)
    out = run_root / "checkpoints" / f"student_{defense}_{attack}.pt"
    save_checkpoint(out, model=student, optimizer=optimizer, epoch=len(losses),
                    metadata={"attack": attack, "defense": defense,
                              "data_sha256": split.source_sha256,
                              "config_sha256": config["_config_sha256"],
                              "teacher_sha256": teacher_sha256,
                              "query_dataset_sha256": query_sha256,
                              "oracle_counts": oracle.counters()})
    teacher_metrics = evaluate(teacher, split, mode="full", teacher=None,
                               device=device, batch_size=config["training"]["eval_batch_size"])
    student_metrics = evaluate(student, split, mode="full", teacher=reference if formal else teacher,
                               device=device, batch_size=config["training"]["eval_batch_size"])
    sampled_metrics = None
    if not formal:
        sampled_metrics = evaluate(student, split, mode="sampled", teacher=teacher,
                                   device=device, batch_size=config["training"]["eval_batch_size"])
    result = {"schema_version": 2 if formal else 1,
              "protocol": config.get("protocol", "legacy-phase1"),
              "dataset": config["dataset"], "backbone": config["backbone"],
              "defense": defense, "attack": attack, "seed": config["seed"],
              "git_commit": git_commit(),
              "teacher_checkpoint": str(teacher_checkpoint),
              "teacher_sha256": teacher_sha256, "teacher_epoch": teacher_state["epoch"],
              "teacher_training_steps": teacher_state["metadata"].get("training_steps"),
              "clean_parent_sha256": clean_parent_sha256,
              "agreement_reference": "clean" if formal else "teacher",
              "agreement_reference_sha256": reference_sha256 if formal else teacher_sha256,
              "student_checkpoint": str(out), "student_sha256": _identity(out),
              "query_dataset": str(query_path), "query_dataset_sha256": query_sha256,
              "data_sha256": split.source_sha256,
              "config_sha256": config["_config_sha256"],
              "budget_definition": "nominal sequences with actual request accounting" if formal
                                   else "actual unique prefix requests to ranking-only oracle",
              "nominal_sequences": settings["n_sequences"],
              "resolved_attack_config": settings,
              "generation_details": getattr(oracle, "generation_details", {}),
              "query_counts": oracle.counters(), "teacher_full": teacher_metrics,
              "student_full": student_metrics, "student_sampled": sampled_metrics,
              "training_steps": training_steps, "retained_training_rows": len(samples),
              "distillation_loss_by_epoch": losses,
              "last_distillation_loss": losses[-1] if losses else None,
              "seconds": time.perf_counter() - start}
    path = run_root / "results" / f"{defense}_{attack}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["preprocess", "train-teacher", "run-attack"])
    parser.add_argument("--config", default="configs/gro_first/ml1m_sasrec_seed42.json")
    parser.add_argument("--defense", choices=["none", "gro", "continued-clean"])
    parser.add_argument("--attack", choices=["random", "dfme", "become"])
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--epochs", type=int)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.epochs is not None and args.epochs < 1:
        parser.error("--epochs must be positive")
    if args.command != "train-teacher" and (args.epochs is not None or args.resume):
        parser.error("--epochs and --resume apply to train-teacher only")
    if args.command != "run-attack" and args.attack is not None:
        parser.error("--attack applies to run-attack only")
    if args.command == "preprocess" and args.defense is not None:
        parser.error("--defense does not apply to preprocess")
    if args.command != "preprocess" and args.defense is None:
        parser.error("--defense is required")
    if args.command == "run-attack" and args.attack is None:
        parser.error("--attack is required")
    config = _configuration(args.config)
    if config.get("protocol") == "unified-defense-v1" and args.epochs is not None:
        parser.error("formal epoch limits come from the configuration; record changes in a new configuration")
    split = _configured_split(config)
    root = Path(config["run_root"])
    root.mkdir(parents=True, exist_ok=True)
    (root / "resolved_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    split.save_metadata(root / "data_metadata.json")
    if args.command == "preprocess":
        print(json.dumps(split.metadata(), indent=2))
    elif args.command == "train-teacher":
        _fit_teacher(config, split, args.defense, root, args.device, args.epochs, args.resume)
    else:
        _run_attack(config, split, args.defense, args.attack, root, args.device)


if __name__ == "__main__":
    main()
