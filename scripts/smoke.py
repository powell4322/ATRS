"""Tiny software smoke test; its scores are not experimental evidence."""
from __future__ import annotations

import math
import random
import tempfile
from pathlib import Path

import torch

from atrs.api import RankingOracle
from atrs.attacks import (Sample, distill_epoch, generate_become, generate_dfme,
                          run_sim4rec)
from atrs.data import load_split
from atrs.evaluation import evaluate
from atrs.gro import gro_step
from atrs.model import SASRec
from atrs.training import SASWindows, load_checkpoint, save_checkpoint, set_seed


def main() -> None:
    torch.set_num_threads(2)
    set_seed(7)
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        data = root / "tiny.txt"
        data.write_text("1 1\n1 2\n1 3\n1 4\n1 5\n2 2\n2 3\n2 4\n2 5\n2 6\n", encoding="utf-8")
        split = load_split(data, require_dense_ids=False)
        model = SASRec(6, max_len=4, hidden=8, layers=1, heads=2, dropout=0)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
        windows = SASWindows(split, max_len=4)
        batch = [torch.stack([windows[i][j] for i in range(len(windows))]) for j in range(3)]
        optimizer.zero_grad()
        loss = model.bce_loss(*batch)
        loss.backward()
        optimizer.step()
        assert math.isfinite(float(loss.detach()))
        api = RankingOracle(model, k=3, max_requests=30, batch_size=2)
        first = api.predict_topk([[1], [2]])
        assert api.predict_topk([[1]])[0] == first[0]
        assert api.counters()["oracle_requests"] == 2
        samples = generate_dfme(api, n_sequences=1, sequence_len=2, n_items=6,
                                rng=random.Random(7), batch_size=1)
        student = SASRec(6, max_len=4, hidden=8, layers=1, heads=2, dropout=0)
        student_optimizer = torch.optim.Adam(student.parameters(), lr=0.001)
        assert math.isfinite(distill_epoch(student, student_optimizer, samples, "dfme",
                                         batch_size=2, device="cpu", rng=random.Random(7)))
        student_gro = SASRec(6, max_len=4, hidden=8, layers=1, heads=2, dropout=0)
        student_gro_optimizer = torch.optim.Adam(student_gro.parameters(), lr=0.001)
        gro = gro_step(model, student_gro, optimizer, student_gro_optimizer,
                       *batch, topk=3)
        assert all(math.isfinite(value) for value in gro.values())
        checkpoint = root / "checkpoint.pt"
        save_checkpoint(checkpoint, model=model, optimizer=optimizer, epoch=1,
                        metadata={"data_sha256": split.source_sha256})
        reloaded = SASRec(6, max_len=4, hidden=8, layers=1, heads=2, dropout=0)
        assert load_checkpoint(checkpoint, model=reloaded)["epoch"] == 1
        metrics = evaluate(reloaded, split, mode="full", teacher=student, batch_size=2)
        assert math.isfinite(metrics["hr@10"])
        for method in ("become", "sim4rec"):
            oracle = RankingOracle(model, k=3, max_requests=30, batch_size=2)
            surrogate = SASRec(6, max_len=4, hidden=8, layers=1, heads=2, dropout=0)
            opt = torch.optim.Adam(surrogate.parameters(), lr=0.001)
            if method == "become":
                generated, losses = generate_become(
                    oracle, surrogate, opt, n_sequences=2, sequence_len=3,
                    n_items=6, rng=random.Random(7), phases=1,
                    initial_fraction=0.5, select_fraction=0.5, alpha=0.5,
                    distill_epochs_per_phase=1, batch_size=2, device="cpu",
                    margin_rank=0.5, margin_neg=0.5, beta=0.5)
            else:
                generated, losses, _ = run_sim4rec(
                    oracle, surrogate, opt, n_seed_sequences=2, sequence_len=3,
                    n_items=6, rng=random.Random(7), pretrain_epochs=1,
                    adversarial_rounds=1, round_batch=2, memory_batches=2,
                    distill_epochs_per_round=1, batch_size=2, device="cpu")
            assert generated and losses and all(math.isfinite(value) for value in losses)
        print("smoke passed: data, SASRec, oracle, DFME, BECOME, Sim4Rec, GRO, checkpoint, evaluation")


if __name__ == "__main__":
    main()
