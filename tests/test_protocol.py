import math

import pytest
import torch

from atrs.api import BudgetExhausted, RankingOracle
from atrs.attacks import Sample, listwise_loss, pairwise_loss
from atrs.cli import _save_queries
from atrs.data import load_split
from atrs.evaluation import evaluate
from atrs.model import SASRec
from atrs.training import SASWindows


class DeterministicTeacher:
    n_items = 6
    max_len = 5

    def __init__(self):
        self.forwards = 0

    def to(self, _device):
        return self

    def eval(self):
        return self

    def parameters(self):
        return iter(())

    def next_scores(self, tokens):
        self.forwards += 1
        return torch.arange(7).float().repeat(tokens.size(0), 1)


def test_split_and_training_do_not_include_holdouts(tmp_path):
    source = tmp_path / "data.txt"
    source.write_text("1 1\n1 2\n1 3\n1 4\n1 5\n", encoding="utf-8")
    split = load_split(source)
    assert split.train[1] == [1, 2, 3]
    assert split.valid[1] == 4 and split.test[1] == 5
    windows = SASWindows(split, max_len=4)
    tokens, positive, negatives = windows[0]
    assert 4 not in positive and 5 not in positive
    assert all(item == 0 or item not in {1, 2, 3} for item in negatives.tolist())


def test_oracle_returns_only_ranked_ids_and_counts_cached_prefixes():
    teacher = DeterministicTeacher()
    oracle = RankingOracle(teacher, k=3, max_requests=2, batch_size=2)
    assert oracle.predict_topk([[1], [2], [1]]) == [[6, 5, 4]] * 3
    assert oracle.counters()["oracle_requests"] == 2
    assert oracle.counters()["model_forward_calls"] == 1
    assert teacher.forwards == 1
    assert oracle.predict_topk([[2]]) == [[6, 5, 4]]
    assert oracle.counters()["cache_hits"] == 2
    with pytest.raises(BudgetExhausted):
        oracle.predict_topk([[3]])
    assert oracle.counters()["oracle_requests"] == 2


def test_distillation_losses_preserve_distinct_objectives():
    scores = torch.tensor([[0.0, 3.0, 2.0, 1.0, 0.0]], requires_grad=True)
    topk = torch.tensor([[1, 2]])
    negatives = torch.tensor([[3, 4]])
    pair = pairwise_loss(scores, topk, negatives, 0.5, 0.5, beta=0.5)
    assert torch.isclose(pair, torch.tensor(0.0))
    listwise = listwise_loss(scores, topk, negatives)
    expected = (torch.logsumexp(scores[0, [1, 2, 3, 4]], 0) - scores[0, 1]
                + torch.logsumexp(scores[0, [2, 3, 4]], 0) - scores[0, 2])
    assert torch.isclose(listwise, expected)
    listwise.backward()
    assert torch.isfinite(scores.grad).all()


def test_full_ranking_filters_seen_items_for_both_models(tmp_path):
    source = tmp_path / "data.txt"
    source.write_text("1 1\n1 2\n1 3\n1 4\n1 5\n2 2\n2 3\n2 4\n2 5\n2 6\n", encoding="utf-8")
    split = load_split(source)
    torch.manual_seed(3)
    model = SASRec(6, max_len=4, hidden=8, layers=1, heads=2, dropout=0)
    result = evaluate(model, split, mode="full", teacher=model, batch_size=2)
    assert result["agr@1"] == 1.0
    assert result["agr@10"] == 1.0
    assert math.isfinite(result["ndcg@10"])


def test_exported_query_dataset_has_stable_checksum(tmp_path):
    samples = [Sample((1, 2), (4, 3, 2)), Sample((2, 4), (1, 5, 6))]
    first = _save_queries(tmp_path / "a.jsonl.gz", samples)
    second = _save_queries(tmp_path / "b.jsonl.gz", samples)
    assert first == second
