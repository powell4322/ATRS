"""Publish validated result JSON to result/ and analysis to docs/."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CELLS = [(defense, attack)
         for defense in ("none", "gro", "continued-clean")
         for attack in ("dfme", "become")]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def checked_metric(result: dict, section: str, name: str) -> float:
    value = result[section][name]
    if not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError(f"invalid {section}.{name}: {value!r}")
    return float(value)


def load_complete_matrix(config: dict, config_hash: str, run_root: Path) -> list[tuple[Path, dict]]:
    paths = [(run_root / "results" / f"{defense}_{attack}.json", defense, attack)
             for defense, attack in CELLS]
    missing = [str(path) for path, _, _ in paths if not path.is_file()]
    if missing:
        raise ValueError("incomplete matrix; missing result files: " + ", ".join(missing))
    rows: list[tuple[Path, dict]] = []
    commits: set[str] = set()
    teacher_hashes: dict[str, str] = {}
    for path, defense, attack in paths:
        result = json.loads(path.read_text(encoding="utf-8"))
        identity = (result.get("dataset"), result.get("backbone"),
                    result.get("seed"), result.get("defense"), result.get("attack"))
        expected = (config["dataset"], config["backbone"], config["seed"], defense, attack)
        if identity != expected:
            raise ValueError(f"{path}: cell identity mismatch: {identity!r}")
        if result.get("data_sha256") != config["expected_data_sha256"]:
            raise ValueError(f"{path}: data hash mismatch")
        if result.get("config_sha256") != config_hash:
            raise ValueError(f"{path}: configuration hash mismatch")
        commit = result.get("git_commit")
        if not isinstance(commit, str) or len(commit) != 40:
            raise ValueError(f"{path}: missing Git commit")
        commits.add(commit)
        teacher_hash = result["teacher_sha256"]
        if defense in teacher_hashes and teacher_hashes[defense] != teacher_hash:
            raise ValueError(f"{path}: teacher checkpoint differs within defense")
        teacher_hashes[defense] = teacher_hash
        requests = result["query_counts"]["oracle_requests"]
        if not isinstance(requests, int) or not 0 < requests <= config["api"]["max_requests"]:
            raise ValueError(f"{path}: invalid oracle request count: {requests!r}")
        if result["teacher_full"]["protocol"] != "full" or result["student_full"]["protocol"] != "full":
            raise ValueError(f"{path}: full-ranking protocol missing")
        if result["teacher_full"]["fold"] != "test" or result["student_full"]["fold"] != "test":
            raise ValueError(f"{path}: test fold missing")
        if result["student_sampled"]["protocol"] != "sampled":
            raise ValueError(f"{path}: sampled evaluation missing")
        for section, names in (("teacher_full", ("hr@10", "ndcg@10")),
                               ("student_full", ("hr@10", "ndcg@10", "agr@1", "agr@10"))):
            for name in names:
                checked_metric(result, section, name)
        rows.append((path, result))
    if len(commits) != 1:
        raise ValueError(f"matrix spans multiple Git commits: {sorted(commits)}")
    return rows


def publish(config_path: Path, report: Path, archive: Path) -> None:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    run_root = Path(config["run_root"])
    if not run_root.is_absolute():
        run_root = ROOT / run_root
    config_hash = sha256(config_path)
    rows = load_complete_matrix(config, config_hash, run_root)
    archive.mkdir(parents=True, exist_ok=True)
    for path, _ in rows:
        shutil.copyfile(path, archive / path.name)
    commit = rows[0][1]["git_commit"]
    manifest = {
        "schema_version": 1,
        "dataset": config["dataset"],
        "backbone": config["backbone"],
        "seed": config["seed"],
        "git_commit": commit,
        "config_sha256": config_hash,
        "data_sha256": config["expected_data_sha256"],
        "cells": [{"defense": result["defense"], "attack": result["attack"],
                   "file": path.name, "sha256": sha256(archive / path.name)}
                  for path, result in rows],
    }
    (archive / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# Phase I results: ML-1M / SASRec",
        "",
        "Status: complete six-cell server matrix; four primary comparisons and two continued-clean controls.",
        "",
        f"- Git commit: `{commit}`",
        f"- Configuration SHA-256: `{config_hash}`",
        f"- Dataset SHA-256: `{config['expected_data_sha256']}`",
        f"- Seed: `{config['seed']}`",
        "- Ranking protocol: full item ranking on the common test rows; history items excluded with the target restored.",
        "",
        "| Defense | Attack | Teacher HR@10 | Teacher NDCG@10 | Student HR@10 | Student NDCG@10 | Agr@1 | Agr@10 | Oracle requests | JSON |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for path, result in rows:
        teacher = result["teacher_full"]
        student = result["student_full"]
        label = {"none": "None", "gro": "GRO", "continued-clean": "Continued-clean control"}[result["defense"]]
        values = [teacher["hr@10"], teacher["ndcg@10"], student["hr@10"],
                  student["ndcg@10"], student["agr@1"], student["agr@10"]]
        metric_cells = " | ".join(f"{value:.4f}" for value in values)
        link = Path(os.path.relpath(archive / path.name, report.parent)).as_posix()
        lines.append(f"| {label} | {result['attack'].upper()} | {metric_cells} | "
                     f"{result['query_counts']['oracle_requests']} | [JSON]({link}) |")
    indexed = {(result["defense"], result["attack"]): result for _, result in rows}
    lines += [
        "",
        "## Descriptive differences",
        "",
        "Each value is GRO minus the named comparator on the same attack. These are single-seed differences, not significance estimates.",
        "",
        "| Attack | Comparator | Δ teacher HR@10 | Δ teacher NDCG@10 | Δ student HR@10 | Δ student NDCG@10 | Δ Agr@1 | Δ Agr@10 |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    measures = (("teacher_full", "hr@10"), ("teacher_full", "ndcg@10"),
                ("student_full", "hr@10"), ("student_full", "ndcg@10"),
                ("student_full", "agr@1"), ("student_full", "agr@10"))
    for attack in ("dfme", "become"):
        defended = indexed[("gro", attack)]
        for comparator in ("none", "continued-clean"):
            baseline = indexed[(comparator, attack)]
            differences = [defended[section][metric] - baseline[section][metric]
                           for section, metric in measures]
            cells = " | ".join(f"{value:+.4f}" for value in differences)
            lines.append(f"| {attack.upper()} | {comparator} | {cells} |")
    lines += [
        "",
        "These metrics and differences are generated from the validated result JSON, not entered by hand. Negative student or agreement differences indicate lower extraction metrics in this run; teacher utility, actual request counts and multi-seed uncertainty must also be examined before making defense claims. The JSON files also contain sampled-ranking evaluation, query counts, checkpoint hashes and timing. Do not mix sampled and full-ranking values in one table.",
        "",
        f"Machine-readable provenance: [manifest.json]({Path(os.path.relpath(archive / 'manifest.json', report.parent)).as_posix()}).",
        "",
        "The source data, model implementation and baseline deviations are documented in [DATA_PROTOCOL.md](DATA_PROTOCOL.md), [REPRODUCTION_PROTOCOL.md](REPRODUCTION_PROTOCOL.md) and [KNOWN_DEVIATIONS.md](KNOWN_DEVIATIONS.md).",
        "",
    ]
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/phase1/ml1m_sasrec_seed42.json")
    parser.add_argument("--report", default="docs/RESULTS.md")
    parser.add_argument("--archive", default="result/phase1/ml1m_sasrec_seed42")
    args = parser.parse_args()
    config_path = Path(args.config).resolve()
    publish(config_path, Path(args.report).resolve(), Path(args.archive).resolve())
    print(f"published validated results to {args.report}")


if __name__ == "__main__":
    main()
