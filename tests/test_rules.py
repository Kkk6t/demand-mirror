from datetime import datetime, timedelta

import pytest

from dby.models import Criterion, Evidence, Experiment, Level, Observation, Project, Stance, Status
from dby.rules import RuleError, change_criteria, evaluate, lock_criteria

NOW = datetime(2026, 11, 2, 12, 0)


def make_project() -> Project:
    p = Project(idea="测试点子")
    p.criteria = [
        Criterion(id="c_ask", metric="私信人数", level=Level.L3, threshold=5, days=7),
        Criterion(id="c_pay", metric="定金人数", level=Level.L4, threshold=2, days=10),
    ]
    return p


def test_lock_requires_a_payment_criterion():
    p = Project(idea="x", criteria=[Criterion(metric="私信", level=Level.L3, threshold=3, days=7)])
    with pytest.raises(RuleError, match="付钱"):
        lock_criteria(p, NOW)


def test_lock_rejects_cheap_signals():
    p = make_project()
    p.criteria.append(Criterion(metric="点赞数", level=Level.L1, threshold=100, days=7))
    with pytest.raises(RuleError, match="点赞"):
        lock_criteria(p, NOW)


def test_change_after_lock_needs_reason_and_detects_loosening():
    p = make_project()
    lock_criteria(p, NOW)
    fp = p.lock.fingerprint
    looser = [c.model_copy() for c in p.criteria]
    looser[1].threshold = 1
    with pytest.raises(RuleError, match="理由"):
        change_criteria(p, looser, "  ", NOW)
    ch = change_criteria(p, looser, "第一周只有周末能发帖", NOW)
    assert ch.loosened
    assert p.lock.fingerprint != fp
    assert evaluate(p, NOW).loosen_count == 1


def test_tightening_is_not_loosening():
    p = make_project()
    lock_criteria(p, NOW)
    tighter = [c.model_copy() for c in p.criteria]
    tighter[0].threshold = 10
    assert not change_criteria(p, tighter, "太容易了", NOW).loosened


def test_desk_research_alone_can_never_reach_paid():
    p = make_project()
    lock_criteria(p, NOW)
    p.research_done = True
    p.evidence = [Evidence(claim=f"支持{i}", stance=Stance.support, level=Level.L4) for i in range(10)]
    v = evaluate(p, NOW)
    assert v.status == Status.unverified
    assert v.highest_level == Level.L2  # 即使模型写了 L4，案头证据也被压到 L2


def test_enough_behavioural_counter_evidence_is_negative():
    p = make_project()
    p.research_done = True
    p.evidence = [
        Evidence(claim="免费替代", stance=Stance.against, level=Level.L2),
        Evidence(claim="竞品很多", stance=Stance.against, level=Level.L2),
    ]
    assert evaluate(p, NOW).status == Status.negative


def test_weak_counter_evidence_is_not_enough():
    p = make_project()
    p.research_done = True
    p.evidence = [Evidence(claim="有人说没必要", stance=Stance.against, level=Level.L1)] * 5
    assert evaluate(p, NOW).status == Status.unverified


def test_expired_unmet_criterion_kills():
    p = make_project()
    p.experiment = Experiment(started_at=NOW - timedelta(days=8))
    p.manual_counts = {"c_ask": 2}
    v = evaluate(p, NOW)
    assert v.status == Status.negative
    assert any("私信人数" in r for r in v.reasons)


def test_not_expired_yet_stays_unverified():
    p = make_project()
    p.experiment = Experiment(started_at=NOW - timedelta(days=3))
    p.manual_counts = {"c_ask": 2, "c_pay": 1}
    v = evaluate(p, NOW)
    assert v.status == Status.unverified
    assert v.highest_level == Level.L4


def test_payment_met_is_paid_even_with_counter_evidence():
    p = make_project()
    p.research_done = True
    p.evidence = [Evidence(claim="免费替代", stance=Stance.against, level=Level.L2)] * 3
    p.experiment = Experiment(started_at=NOW - timedelta(days=2))
    p.observations = [Observation(text="已付", label="付费", level=Level.L4, stance=Stance.support)] * 2
    assert evaluate(p, NOW).status == Status.paid


def test_manual_count_overrides_classified_comments():
    p = make_project()
    p.experiment = Experiment(started_at=NOW)
    p.observations = [Observation(text="已付", label="付费", level=Level.L4, stance=Stance.support)] * 2
    p.manual_counts = {"c_pay": 0}
    assert evaluate(p, NOW).status != Status.paid


def test_negative_comments_do_not_count_toward_criteria():
    p = make_project()
    p.experiment = Experiment(started_at=NOW)
    p.observations = [Observation(text="不需要", label="否定", level=Level.L4, stance=Stance.against)] * 3
    assert evaluate(p, NOW).status == Status.unverified
