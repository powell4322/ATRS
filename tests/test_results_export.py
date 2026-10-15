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
    archive = tmp_path / "docs" / "results"
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
            "query_counts": {"oracle_requests": 10},
            "teacher_full": {"protocol": "full", "fold": "test", "hr@10": 0.3, "ndcg@10": 0.2},
            "student_full": {"protocol": "full", "fold": "test", "hr@10": 0.25,
                             "ndcg@10": 0.15, "agr@1": 0.1, "agr@10": 0.4},
            "student_sampled": {"protocol": "sampled"},
        }
        (source / f"{defense}_{attack}.json").write_text(json.dumps(result), encoding="utf-8")
    export_results.publish(config_path, report, archive)
    assert len(list(archive.glob("*.json"))) == 6
    assert "Status: complete six-cell" in report.read_text(encoding="utf-8")

    broken = source / "gro_dfme.json"
    result = json.loads(broken.read_text(encoding="utf-8"))
    result["config_sha256"] = "0" * 64
    broken.write_text(json.dumps(result), encoding="utf-8")
    with pytest.raises(ValueError, match="configuration hash mismatch"):
        export_results.publish(config_path, report, archive)
    assert "Status: complete six-cell" in report.read_text(encoding="utf-8")
