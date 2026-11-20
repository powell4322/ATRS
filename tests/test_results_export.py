import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "export_results.py"
SPEC = importlib.util.spec_from_file_location("export_results", SCRIPT)
export_results = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(export_results)


def test_results_are_published_only_for_a_consistent_complete_matrix(tmp_path):
    config = {"dataset": "ml-1m", "backbone": "sasrec", "seed": 42,
              "expected_data_sha256": "a" * 64, "run_root": str(tmp_path / "runs"),
              "api": {"max_requests": 20}}
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    config_hash = export_results.sha256(config_path)
    report = tmp_path / "docs" / "RESULTS.md"
    archive = tmp_path / "result" / "phase1" / "ml1m_sasrec_seed42"
    with pytest.raises(ValueError, match="incomplete matrix"):
        export_results.publish(config_path, report, archive)
    assert not report.exists()

    source = tmp_path / "runs" / "results"
    source.mkdir(parents=True)
    for defense, attack in export_results.CELLS:
        result = {
            "dataset": "ml-1m", "backbone": "sasrec", "seed": 42,
            "defense": defense, "attack": attack, "git_commit": "f" * 40,
            "data_sha256": "a" * 64, "config_sha256": config_hash,
            "teacher_sha256": {"none": "b", "gro": "c", "continued-clean": "d"}[defense] * 64,
            "clean_parent_sha256": None if defense == "none" else "b" * 64,
            "query_counts": {"oracle_requests": 10, "cache_hits": 2, "requested_prefixes": 12},
            "teacher_full": {"protocol": "full", "fold": "test", "hr@10": 0.3, "ndcg@10": 0.2},
            "student_full": {"protocol": "full", "fold": "test", "hr@10": 0.25,
                             "ndcg@10": 0.15, "agr@1": 0.1, "agr@10": 0.4},
            "student_sampled": {"protocol": "sampled"},
        }
        (source / f"{defense}_{attack}.json").write_text(json.dumps(result), encoding="utf-8")
    export_results.publish(config_path, report, archive)
    assert len(list(archive.glob("*.json"))) == 7
    manifest = json.loads((archive / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["cells"]) == 6
    published = report.read_text(encoding="utf-8")
    assert "Status: complete six-cell" in published
    assert "## Descriptive differences" in published
    assert "# 08 实验结果与分析" in published
    assert "[00 导航](00_INDEX.md)" in published
    assert '[Descriptive differences](#section-1)' in published
    assert '<a id="section-1"></a>' in published
    assert "../result/phase1/ml1m_sasrec_seed42/manifest.json" in published

    broken = source / "gro_dfme.json"
    result = json.loads(broken.read_text(encoding="utf-8"))
    result["clean_parent_sha256"] = "0" * 64
    broken.write_text(json.dumps(result), encoding="utf-8")
    with pytest.raises(ValueError, match="clean parent differs"):
        export_results.publish(config_path, report, archive)

    result["config_sha256"] = "0" * 64
    broken.write_text(json.dumps(result), encoding="utf-8")
    with pytest.raises(ValueError, match="configuration hash mismatch"):
        export_results.publish(config_path, report, archive)
    assert "Status: complete six-cell" in report.read_text(encoding="utf-8")


def test_formal_results_require_clean_reference_and_support_nominal_budgets(tmp_path):
    config = {"protocol": "unified-defense-v1", "dataset": "ml-1m", "backbone": "sasrec",
              "seed": 42, "expected_data_sha256": "a" * 64, "run_root": str(tmp_path / "runs"),
              "runnable_defenses": ["none", "gro"], "api": {"max_requests": None},
              "attacks": {attack: {"n_sequences": 1000} for attack in ("random", "dfme", "become")}}
    config_path = tmp_path / "formal.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    source = tmp_path / "runs/results"
    source.mkdir(parents=True)
    config_hash = export_results.sha256(config_path)
    for defense, attack in export_results.cells_for(config):
        result = {
            "schema_version": 2, "protocol": config["protocol"],
            "dataset": "ml-1m", "backbone": "sasrec", "seed": 42,
            "defense": defense, "attack": attack, "git_commit": "f" * 40,
            "data_sha256": "a" * 64, "config_sha256": config_hash,
            "teacher_sha256": ("b" if defense == "none" else "c") * 64,
            "clean_parent_sha256": None if defense == "none" else "b" * 64,
            "agreement_reference": "clean", "agreement_reference_sha256": "b" * 64,
            "nominal_sequences": 1000, "resolved_attack_config": {"n_sequences": 1000},
            "query_counts": {"oracle_requests": 200000, "requested_prefixes": 200100,
                             "cache_hits": 100, "unique_queried_prefixes": 200000,
                             "unique_model_contexts": 200000, "feedback_prefixes": 100},
            "teacher_full": {"protocol": "full", "fold": "test", "recall@10": 0.3, "ndcg@10": 0.2},
            "student_full": {"protocol": "full", "fold": "test", "recall@10": 0.2,
                             "ndcg@10": 0.1, "agr@10": 0.4}, "training_steps": 1000,
        }
        (source / f"{defense}_{attack}.json").write_text(json.dumps(result), encoding="utf-8")
    report = tmp_path / "docs/08_RESULTS.md"
    archive = tmp_path / "result/formal/ml1m_sasrec_seed42"
    export_results.publish(config_path, report, archive, defenses=["gro"])
    partial = json.loads((archive / "manifest.json").read_text(encoding="utf-8"))
    assert len(partial["cells"]) == 3
    assert {cell["defense"] for cell in partial["cells"]} == {"gro"}
    export_results.publish(config_path, report, archive)
    assert "Agreement@10" in report.read_text(encoding="utf-8")
    assert "200000" in report.read_text(encoding="utf-8")
    for seed in (43, 44):
        seeded = {**config, "seed": seed}
        seeded_path = tmp_path / f"formal{seed}.json"
        seeded_path.write_text(json.dumps(seeded), encoding="utf-8")
        for path in source.glob("*.json"):
            result = json.loads(path.read_text(encoding="utf-8"))
            result.update(seed=seed, config_sha256=export_results.sha256(seeded_path))
            path.write_text(json.dumps(result), encoding="utf-8")
        export_results.publish(seeded_path, report, archive.with_name(f"ml1m_sasrec_seed{seed}"))
    assert "0.300000 ± 0.000000" in report.read_text(encoding="utf-8")
    bad_path = source / "gro_dfme.json"
    bad = json.loads(bad_path.read_text())
    bad.update(seed=42, config_sha256=config_hash)
    bad["agreement_reference_sha256"] = "c" * 64
    bad_path.write_text(json.dumps(bad), encoding="utf-8")
    for path in source.glob("*.json"):
        if path == bad_path:
            continue
        result = json.loads(path.read_text(encoding="utf-8"))
        result.update(seed=42, config_sha256=config_hash)
        path.write_text(json.dumps(result), encoding="utf-8")
    with pytest.raises(ValueError, match="Agreement reference"):
        export_results.publish(config_path, report, archive)
