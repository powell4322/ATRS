"""Run selected full-budget cells; default to seed42 DFME paired None/GRO."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import torch

from atrs.cli import _configuration, _identity
from atrs.training import git_commit
from export_results import publish


ROOT = Path(__file__).resolve().parents[1]


def run_logged(arguments: list[str], log: Path) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"command": arguments}) + "\n")
        stream.flush()
        with subprocess.Popen(arguments, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, encoding="utf-8", errors="replace") as process:
            for line in process.stdout:
                print(line, end="", flush=True)
                stream.write(line)
                stream.flush()
            status = process.wait()
    if status:
        raise subprocess.CalledProcessError(status, arguments)


def complete_result(path: Path, config: dict, defense: str, attack: str) -> bool:
    if not path.exists():
        return False
    result = json.loads(path.read_text(encoding="utf-8"))
    expected = (config["_config_sha256"], config["expected_data_sha256"], git_commit(),
                defense, attack, config["seed"])
    actual = tuple(result.get(key) for key in
                   ("config_sha256", "data_sha256", "git_commit", "defense", "attack", "seed"))
    if actual != expected:
        raise ValueError(f"existing result has different inputs or code: {path}; use a new run_root")
    for file_key, hash_key in (("teacher_checkpoint", "teacher_sha256"),
                               ("student_checkpoint", "student_sha256"),
                               ("query_dataset", "query_dataset_sha256")):
        artifact = Path(result[file_key])
        if not artifact.is_file() or _identity(artifact) != result[hash_key]:
            raise ValueError(f"result artifact is absent or changed: {artifact}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--configs", nargs="+",
                        default=["configs/gro_first/ml1m_sasrec_seed42.json"],
                        help="configuration files; defaults to seed 42 only")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--defenses", nargs="+", choices=["none", "gro"], default=["none", "gro"],
                        help="defenses to run; defaults to the None/GRO comparison")
    parser.add_argument("--attacks", nargs="+", choices=["random", "dfme", "become"],
                        default=["dfme"], help="attacks to run; defaults to DFME only")
    args = parser.parse_args()
    os.chdir(ROOT)
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    if args.device.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable to this Python environment")
    for filename in args.configs:
        config = _configuration(filename)
        if config.get("protocol") != "unified-defense-v1":
            raise ValueError("run_formal uses configs with the unified-defense-v1 protocol")
        root = Path(config["run_root"])
        logs = root / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        environment = {
            "git_commit": git_commit(), "torch": str(torch.__version__), "cuda": torch.version.cuda,
            "device": args.device, "python": sys.version, "command": sys.argv,
            "gpu": torch.cuda.get_device_name(torch.device(args.device)) if args.device.startswith("cuda") else None,
        }
        (logs / "environment.json").write_text(json.dumps(environment, indent=2), encoding="utf-8")
        command = [sys.executable, "-u", "-m", "atrs.cli"]
        common = ["--config", filename, "--device", args.device]
        defenses = list(dict.fromkeys(args.defenses))
        attacks = list(dict.fromkeys(args.attacks))
        if "none" not in defenses:
            print("clean teacher is a shared training/reference prerequisite; None attack cells are deferred",
                  flush=True)
        for defense in dict.fromkeys(["none", *defenses]):
            checkpoint = root / "checkpoints" / f"teacher_{defense}.pt"
            training = command + ["train-teacher", *common, "--defense", defense]
            if checkpoint.exists():
                training.append("--resume")
            run_logged(training, logs / f"console-teacher-{defense}.log")
            if defense not in defenses:
                continue
            for attack in attacks:
                result = root / "results" / f"{defense}_{attack}.json"
                if complete_result(result, config, defense, attack):
                    print(f"reuse completed cell: {result}", flush=True)
                    continue
                run_logged(command + ["run-attack", *common, "--defense", defense, "--attack", attack],
                           logs / f"console-{defense}-{attack}.log")
        publish(ROOT / filename, ROOT / "docs/08_RESULTS.md",
                ROOT / "result" / Path(filename).parent.name / Path(filename).stem,
                defenses=defenses, attacks=attacks)


if __name__ == "__main__":
    main()
