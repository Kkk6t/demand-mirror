from datetime import datetime, timedelta

import pytest

from dby import pipeline
from dby.demo import DEMO_ANSWERS, DEMO_IDEA, DEMO_RAW_COMMENTS, DEMO_RESPONSES, DEMO_SEARCH
from dby.llm import DemoLLM
from dby.models import Level, Project, Stance, Status
from dby.report import to_markdown
from dby.rules import RuleError, evaluate, lock_criteria
from dby.search import DemoSearch

NOW = datetime(2026, 11, 2, 12, 0)


class FakeLLM:
    """按任务返回给定数据，用来测试代码是否校验模型输出。"""

    name = "fake"

    def __init__(self, responses):
        self.responses = responses

    def json(self, task, prompt):
        return self.responses[task]


def demo_project() -> Project:
    llm, searcher = DemoLLM(DEMO_RESPONSES), DemoSearch(DEMO_SEARCH)
    p = Project(idea=DEMO_IDEA, demo=True)
    pipeline.ask_questions(p, llm)
    p.answers = {q.id: a for q, a in zip(p.questions, DEMO_ANSWERS)}
    pipeline.draft_criteria(p, llm)
    lock_criteria(p, NOW)
    pipeline.run_research(p, llm, searcher)
    pipeline.plan_experiment(p, llm)
    return p


def test_demo_flow_end_to_end():
    p = demo_project()
    assert len(p.questions) == 3
    assert p.lock.locked
    assert p.evidence and all(e.url.startswith("https://") for e in p.evidence)
    assert all(e.level <= Level.L2 for e in p.evidence)
    # 自我验证的诚实结论：案头调研已经出现反向信号
    assert evaluate(p, NOW).status == Status.negative
    assert all(post.criterion_id in {c.id for c in p.criteria} for post in p.experiment.posts)

    pipeline.start_experiment(p, NOW)
    pipeline.classify_observations(p, DemoLLM(DEMO_RESPONSES), DEMO_RAW_COMMENTS)
    labels = [o.label for o in p.observations]
    assert labels.count("付费") == 1 and labels.count("承诺") == 2

    # 第 8 天，私信只有 2 个（标准是 5）：淘汰条件触发
    v = evaluate(p, NOW + timedelta(days=8))
    assert v.status == Status.negative
    assert any("天到了" in r for r in v.reasons)

    md = to_markdown(p, NOW)
    assert "网上找到的资料" in md and "先别做" in md


def test_research_requires_locked_criteria():
    llm, searcher = DemoLLM(DEMO_RESPONSES), DemoSearch(DEMO_SEARCH)
    p = Project(idea=DEMO_IDEA)
    pipeline.draft_criteria(p, llm)
    with pytest.raises(RuleError, match="锁定"):
        pipeline.run_research(p, llm, searcher)


def test_invented_sources_are_dropped_and_levels_capped():
    p = Project(idea="x")
    p.criteria = DemoLLM(DEMO_RESPONSES).json("criteria", "")["criteria"]
    pipeline.draft_criteria(p, DemoLLM(DEMO_RESPONSES))
    lock_criteria(p, NOW)
    fake = FakeLLM(
        {
            "queries": {"queries": [{"query": "AI startup idea validator", "kind": "支持"}]},
            "evidence": {
                "evidence": [
                    {"ref": 0, "claim": "真实来源，但模型说是付费级", "stance": "支持", "level": 4},
                    {"ref": 99, "claim": "编出来的来源", "stance": "支持", "level": 2},
                    {"claim": "没有 ref", "stance": "支持", "level": 2},
                ]
            },
        }
    )
    notes = pipeline.run_research(p, fake, DemoSearch(DEMO_SEARCH))
    assert len(p.evidence) == 1
    assert p.evidence[0].level == Level.L2
    assert any("有 2 条说法找不到出处" in n for n in notes)


def test_against_queries_are_topped_up_by_code():
    p = Project(idea="x", keywords=["简历模板"])
    fake = FakeLLM({"queries": {"queries": [{"query": f"q{i}", "kind": "支持"} for i in range(4)]}})
    qs = pipeline.plan_queries(p, fake)
    assert sum(q.kind == "反对" for q in qs) * 2 >= len(qs)


def test_observation_levels_come_from_labels_not_model():
    p = Project(idea="x")
    fake = FakeLLM(
        {
            "observations": {
                "items": [
                    {"text": "好想要！！", "label": "言论", "level": 4},
                    {"text": "太贵了", "label": "否定"},
                    {"text": "今天天气不错", "label": "无关"},
                ]
            }
        }
    )
    pipeline.classify_observations(p, fake, "随便")
    assert [o.level for o in p.observations] == [Level.L1, Level.L1]
    assert p.observations[1].stance == Stance.against


def test_hype_in_model_output_is_intercepted():
    p = Project(idea="x")
    fake = FakeLLM({"clarify": {"questions": [{"question": "这是刚需吗？市场潜力 9/10", "why": ""}]}})
    pipeline.ask_questions(p, fake)
    assert "刚需" not in p.questions[0].question
    assert len(p.guard_hits) == 2


def test_search_401_is_explained_in_plain_words():
    import requests
    from dby.search import _explain

    resp = requests.Response()
    resp.status_code = 401
    err = _explain("博查", requests.HTTPError(response=resp))
    assert "Key 不对" in str(err) and "open.bochaai.com" in str(err)


def test_skip_research_moves_on():
    p = Project(idea="x")
    pipeline.draft_criteria(p, DemoLLM(DEMO_RESPONSES))
    lock_criteria(p, NOW)
    pipeline.skip_research(p)
    assert p.research_done and p.evidence == []
    assert evaluate(p, NOW).status == Status.unverified


def test_save_env_roundtrip(tmp_path, monkeypatch):
    for k in ("LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY", "SEARCH_PROVIDER", "SEARCH_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    from dby.config import Settings, save_env

    s = Settings("https://api.deepseek.com", "sk-a", "deepseek-chat", "博查", "sk-b")
    f = tmp_path / ".env"
    save_env(s, f)
    text = f.read_text(encoding="utf-8")
    assert "LLM_API_KEY=sk-a" in text and "SEARCH_API_KEY=sk-b" in text
    assert Settings.from_env().search_api_key == "sk-b"
