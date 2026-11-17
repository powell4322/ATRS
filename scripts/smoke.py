"""Tiny software smoke test; its scores are not experimental evidence."""
from __future__ import annotations

import math
import random
import tempfile
from pathlib import Path

import torch

from atrs.api import RankingOracle
from atrs.attacks import Sample, distill_epoch, generate_become, generate_dfme
from atrs.data import load_split
from atrs.evaluation import evaluate
from atrs.gro import gro_step
from atrs.learning_progress import LearningProgressProbe
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
        if torch.cuda.is_available():
            device = "cuda"
        else:
            device = "cpu"
        model.to(device)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
        windows = SASWindows(split, max_len=4)
        batch = [torch.stack([windows[i][j] for i in range(len(windows))]).to(device)
                 for j in range(3)]
        optimizer.zero_grad()
        loss = model.bce_loss(*batch)
        loss.backward()
        optimizer.step()
        assert math.isfinite(float(loss.detach()))
        api = RankingOracle(model, k=3, max_requests=30, batch_size=2, device=device)
        first = api.predict_topk([[1], [2]])
        assert api.predict_topk([[1]])[0] == first[0]
        assert api.counters()["oracle_requests"] == 2
        samples = generate_dfme(api, n_sequences=1, sequence_len=2, n_items=6,
                                rng=random.Random(7), batch_size=1)
        student = SASRec(6, max_len=4, hidden=8, layers=1, heads=2, dropout=0).to(device)
        student_optimizer = torch.optim.Adam(student.parameters(), lr=0.001)
        assert math.isfinite(distill_epoch(student, student_optimizer, samples, "dfme",
                                         batch_size=2, device=device, rng=random.Random(7)))
        teacher_gro = SASRec(**model.config()).to(device)
        teacher_gro.load_state_dict(model.state_dict())
        teacher_gro_optimizer = torch.optim.Adam(teacher_gro.parameters(), lr=0.001)
        student_gro = SASRec(**model.config()).to(device)
        student_gro_optimizer = torch.optim.Adam(student_gro.parameters(), lr=0.001)
        before = [network.item.weight.detach().clone() for network in (teacher_gro, student_gro)]
        gro = gro_step(teacher_gro, student_gro, teacher_gro_optimizer, student_gro_optimizer,
                       *batch, topk=3)
        assert all(math.isfinite(value) for value in gro.values())
        assert all(not torch.equal(network.item.weight, weights)
                   for network, weights in zip((teacher_gro, student_gro), before))
        checkpoint = root / "checkpoint.pt"
        save_checkpoint(checkpoint, model=model, optimizer=optimizer, epoch=1,
                        metadata={"data_sha256": split.source_sha256})
        reloaded = SASRec(**model.config()).to(device)
        assert load_checkpoint(checkpoint, model=reloaded, map_location=device)["epoch"] == 1
        metrics = evaluate(reloaded, split, mode="full", teacher=student, batch_size=2, device=device)
        assert math.isfinite(metrics["hr@10"])
        oracle = RankingOracle(model, k=3, max_requests=30, batch_size=2, device=device)
        surrogate = SASRec(**model.config()).to(device)
        opt = torch.optim.Adam(surrogate.parameters(), lr=0.001)
        generated, losses = generate_become(
            oracle, surrogate, opt, n_sequences=2, sequence_len=3,
            n_items=6, rng=random.Random(7), phases=1,
            initial_fraction=0.5, select_fraction=0.5, alpha=0.5,
            distill_epochs_per_phase=1, batch_size=2, device=device,
            margin_rank=0.5, margin_neg=0.5, beta=0.5)
        assert generated and losses and all(math.isfinite(value) for value in losses)
        assert oracle.counts.feedback_prefixes == 2 and oracle.counts.feedback_oracle_requests == 0

        probe_student = SASRec(12, max_len=4, hidden=8, layers=1, heads=2, dropout=0).to(device)
        tokens, positives, negatives = batch
        probe = LearningProgressProbe(probe_student, (tokens, positives[:, -1:], negatives[:, -1:]),
                                      eta=0.001)
        diagnostics = probe.run(Sample((1, 2), (3, 4, 5)), head=1, per_edit=1,
                                rng=random.Random(7), margin_rank=0.5, margin_neg=0.5)
        for candidate in diagnostics["candidates"]:
            assert math.isclose(candidate["j_lp"], candidate["j_lp_full_jvp"],
                                abs_tol=1e-4, rel_tol=1e-4)
        print("smoke passed: data, SASRec, oracle, DFME, BECOME, GRO, checkpoint, evaluation, JVP")


if __name__ == "__main__":
    main()
