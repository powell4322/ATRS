"""Publish validated result JSON to result/ and analysis to docs/."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CELLS = [(defense, attack)
         for defense in ("none", "gro", "continued-clean")
         for attack in ("dfme", "become")]


def cells_for(config: dict, *, defenses=None, attacks=None) -> list[tuple[str, str]]:
    if config.get("protocol") == "unified-defense-v1":
        return [(defense, attack) for defense in (defenses or config["runnable_defenses"])
                for attack in (attacks or ("random", "dfme", "become"))]
    return CELLS


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


def load_complete_matrix(config: dict, config_hash: str, run_root: Path, *,
                         defenses=None, attacks=None) -> list[tuple[Path, dict]]:
    paths = [(run_root / "results" / f"{defense}_{attack}.json", defense, attack)
             for defense, attack in cells_for(config, defenses=defenses, attacks=attacks)]
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
        cap = config["api"]["max_requests"]
        if not isinstance(requests, int) or requests <= 0 or (cap is not None and requests > cap):
            raise ValueError(f"{path}: invalid oracle request count: {requests!r}")
        counts = result["query_counts"]
        if "requested_prefixes" in counts:
            if counts["requested_prefixes"] != requests + counts["cache_hits"]:
                raise ValueError(f"{path}: inconsistent query counts")
        if result["teacher_full"]["protocol"] != "full" or result["student_full"]["protocol"] != "full":
            raise ValueError(f"{path}: full-ranking protocol missing")
        if result["teacher_full"]["fold"] != "test" or result["student_full"]["fold"] != "test":
            raise ValueError(f"{path}: test fold missing")
        formal = config.get("protocol") == "unified-defense-v1"
        if formal and (result.get("schema_version") != 2 or result.get("agreement_reference") != "clean"
                       or result.get("protocol") != config["protocol"]
                       or result.get("nominal_sequences") != config["attacks"][attack]["n_sequences"]
                       or result.get("resolved_attack_config") != config["attacks"][attack]):
            raise ValueError(f"{path}: formal protocol or attack settings mismatch")
        if not formal and result["student_sampled"]["protocol"] != "sampled":
            raise ValueError(f"{path}: sampled evaluation missing")
        recall = "recall@10" if formal else "hr@10"
        student_names = (recall, "ndcg@10", "agr@10") if formal else (recall, "ndcg@10", "agr@1", "agr@10")
        for section, names in (("teacher_full", (recall, "ndcg@10")),
                               ("student_full", student_names)):
            for name in names:
                checked_metric(result, section, name)
        rows.append((path, result))
    if len(commits) != 1:
        raise ValueError(f"matrix spans multiple Git commits: {sorted(commits)}")
    clean_hash = teacher_hashes.get("none")
    if clean_hash is None:
        references = {result.get("agreement_reference_sha256") for _, result in rows}
        if len(references) != 1 or None in references:
            raise ValueError("selected defense cells need one common clean reference checkpoint")
        clean_hash = references.pop()
    if any("clean_parent_sha256" in result for _, result in rows):
        for path, result in rows:
            if result["defense"] != "none" and result.get("clean_parent_sha256") != clean_hash:
                raise ValueError(f"{path}: clean parent differs from the None teacher")
    if config.get("protocol") == "unified-defense-v1":
        for path, result in rows:
            if result["agreement_reference_sha256"] != clean_hash:
                raise ValueError(f"{path}: main Agreement reference differs from the clean target")
    return rows


def write_formal_report(report: Path, archive_root: Path) -> None:
    """Aggregate verified per-seed archives, preserving each attack's defense comparisons."""
    rows = []
    configurations = []
    for manifest_path in sorted(archive_root.glob("*/manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("protocol") != "unified-defense-v1":
            continue
        config_path = manifest_path.parent / "config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        if sha256(config_path) != manifest["config_sha256"]:
            raise ValueError(f"archived configuration hash differs: {config_path}")
        configurations.append({key: value for key, value in config.items() if key not in {"seed", "run_root"}})
        for cell in manifest["cells"]:
            path = manifest_path.parent / cell["file"]
            if sha256(path) != cell["sha256"]:
                raise ValueError(f"archived result hash differs: {path}")
            rows.append((path, json.loads(path.read_text(encoding="utf-8"))))
    if configurations and any(config != configurations[0] for config in configurations[1:]):
        raise ValueError("aggregate formal archives must use the same settings apart from seed and run_root")
    identities = [(row["seed"], row["attack"], row["defense"]) for _, row in rows]
    if len(identities) != len(set(identities)):
        raise ValueError("duplicate seed/attack/defense cells in the aggregate archive")
    lines = [
        "# 08 实验结果与分析", "",
        "[00 导航](00_INDEX.md) · [04 实验协议](04_EXPERIMENT_PROTOCOL.md) · [07 进度](07_PROGRESS.md)", "",
        "以下数值来自已归档的真实运行。主 Agreement 以原始未保护 Target 为参照。", "",
        "当前页面列出已完成的所选防御任务，未执行的 cell 由进度页记录。Ours 等待后续研究方案确定。", "",
        "| Seed | Attack | Defense | Target Recall@10 | Target NDCG@10 | Surrogate Recall@10 | Surrogate NDCG@10 | Agreement@10 | 结果 |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for path, result in rows:
        target, student = result["teacher_full"], result["student_full"]
        numbers = (target["recall@10"], target["ndcg@10"], student["recall@10"],
                   student["ndcg@10"], student["agr@10"])
        metrics = " | ".join(f"{value:.6f}" for value in numbers)
        link = Path(os.path.relpath(path, report.parent)).as_posix()
        lines.append(f"| {result['seed']} | {result['attack']} | {result['defense']} | {metrics} | [JSON]({link}) |")
    lines.extend(["", "## 同一攻击下的防御效应", "",
                  "差值使用同一 seed、同一攻击的两个防御条件。", "",
                  "| Seed | Attack | 比较 | Δ Target Recall@10 | Δ Target NDCG@10 | Δ Surrogate Recall@10 | Δ Surrogate NDCG@10 | Δ Agreement@10 |",
                  "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |"])
    indexed = {(result["seed"], result["attack"], result["defense"]): result for _, result in rows}
    measurements = (("teacher_full", "recall@10"), ("teacher_full", "ndcg@10"),
                    ("student_full", "recall@10"), ("student_full", "ndcg@10"), ("student_full", "agr@10"))
    for seed, attack, defense in sorted(indexed):
        if defense != "gro" or (seed, attack, "none") not in indexed:
            continue
        protected = indexed[(seed, attack, defense)]
        clean = indexed[(seed, attack, "none")]
        values = " | ".join(f"{protected[section][name] - clean[section][name]:+.6f}"
                            for section, name in measurements)
        lines.append(f"| {seed} | {attack} | GRO − None | {values} |")
    summaries = []
    for attack in ("random", "dfme", "become"):
        for defense in dict.fromkeys(result["defense"] for _, result in rows):
            group = [result for _, result in rows if result["attack"] == attack and result["defense"] == defense]
            seeds = {result["seed"] for result in group}
            if seeds != {42, 43, 44} or len(group) != 3:
                continue
            if len({result["git_commit"] for result in group}) != 1:
                raise ValueError("three-seed aggregation requires a common source commit")
            statistics_cells = []
            for section, metric in measurements:
                values = [result[section][metric] for result in group]
                statistics_cells.append(f"{statistics.mean(values):.6f} ± {statistics.stdev(values):.6f}")
            summaries.append(f"| {attack} | {defense} | 3 | " + " | ".join(statistics_cells) + " |")
    if summaries:
        lines.extend(["", "## 三种子汇总", "",
                      "| Attack | Defense | 完成种子数 | Target Recall@10 | Target NDCG@10 | Surrogate Recall@10 | Surrogate NDCG@10 | Agreement@10 |",
                      "| --- | --- | ---: | --- | --- | --- | --- | --- |", *summaries])
    lines.extend(["", "## 资源记录", "",
                  "资源用于审查同一攻击在不同防御下的消耗。", "",
                  "| Seed | Attack | Defense | 名义序列 | 不同原始前缀 | 不同模型上下文 | 逻辑请求 | 反馈行 | 新 API 请求 | 训练步数 |",
                  "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"])
    for _, result in rows:
        counts = result["query_counts"]
        lines.append(f"| {result['seed']} | {result['attack']} | {result['defense']} | "
                     f"{result['nominal_sequences']} | {counts['unique_queried_prefixes']} | "
                     f"{counts['unique_model_contexts']} | {counts['requested_prefixes']} | "
                     f"{counts['feedback_prefixes']} | {counts['oracle_requests']} | {result['training_steps']} |")
    lines.extend(["", "## 分析要求", "",
                  "探索阶段逐个 seed 记录结果，多种子复测由后续研究进度决定；仅对齐全的三种子组汇总均值和样本标准差。"
                  "同时检查 Target 效用、None 下的提取信号、实际预算与 checkpoint 谱系。"
                  "本页尚未提供跨种子的统计显著性判断。", ""])
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines), encoding="utf-8")


def publish(config_path: Path, report: Path, archive: Path, *, defenses=None, attacks=None) -> None:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    run_root = Path(config["run_root"])
    if not run_root.is_absolute():
        run_root = ROOT / run_root
    config_hash = sha256(config_path)
    rows = load_complete_matrix(config, config_hash, run_root, defenses=defenses, attacks=attacks)
    archive.mkdir(parents=True, exist_ok=True)
    previous = archive / "manifest.json"
    if config.get("protocol") == "unified-defense-v1" and previous.is_file():
        old_manifest = json.loads(previous.read_text(encoding="utf-8"))
        if (old_manifest["config_sha256"] != config_hash
                or old_manifest["git_commit"] != rows[0][1]["git_commit"]):
            raise ValueError("existing archive uses different code/configuration; choose a new archive directory")
        selected = {(result["defense"], result["attack"]) for _, result in rows}
        for cell in old_manifest["cells"]:
            if (cell["defense"], cell["attack"]) in selected:
                continue
            path = archive / cell["file"]
            if sha256(path) != cell["sha256"]:
                raise ValueError(f"archived result hash differs: {path}")
            rows.append((path, json.loads(path.read_text(encoding="utf-8"))))
    for path, _ in rows:
        if path.resolve() != (archive / path.name).resolve():
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
        "protocol": config.get("protocol", "legacy-phase1"),
        "cells": [{"defense": result["defense"], "attack": result["attack"],
                   "file": path.name, "sha256": sha256(archive / path.name)}
                  for path, result in rows],
    }
    (archive / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if config.get("protocol") == "unified-defense-v1":
        shutil.copyfile(config_path, archive / "config.json")
        write_formal_report(report, archive.parent)
        return
    lines = [
        "# 08 实验结果与分析",
        "",
        "<!-- doc-nav:start -->",
        "[00 导航](00_INDEX.md) · [09 待确认](09_IMPLEMENTATION_AND_TBD.md)",
        "<!-- doc-nav:end -->",
        "",
        "<!-- doc-toc:start -->",
        "**本页目录**",
        "",
        "- [Descriptive differences](#section-1)",
        "<!-- doc-toc:end -->",
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
        '<a id="section-1"></a>',
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
        "Data, protocol and implementation differences are documented in [05](05_DATA_AND_BUDGET.md), [04](04_EXPERIMENT_PROTOCOL.md) and [03](03_CONFIGURATION_AUDIT.md).",
        "",
    ]
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/gro_first/ml1m_sasrec_seed42.json")
    parser.add_argument("--report")
    parser.add_argument("--archive")
    parser.add_argument("--defenses", nargs="+", choices=["none", "gro"])
    parser.add_argument("--attacks", nargs="+", choices=["random", "dfme", "become"])
    args = parser.parse_args()
    config_path = Path(args.config).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    formal = config.get("protocol") == "unified-defense-v1"
    stage = config_path.parent.name if formal else "phase1"
    archive = Path(args.archive) if args.archive else ROOT / "result" / stage / config_path.stem
    default_report = ROOT / "docs/08_RESULTS.md" if formal else archive / "ANALYSIS.md"
    report = Path(args.report) if args.report else default_report
    publish(config_path, report.resolve(), archive.resolve(), defenses=args.defenses, attacks=args.attacks)
    print(f"published validated results to {report}")


if __name__ == "__main__":
    main()
