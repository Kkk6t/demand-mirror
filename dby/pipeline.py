"""六个步骤的编排。每一步：拼 prompt → 调模型 → 乐观拦截 → 代码校验 → 写回项目。"""

from __future__ import annotations

import json
from datetime import datetime

from . import prompts
from .guard import scrub_obj
from .llm import LLM
from .models import (
    DESK_RESEARCH_MAX,
    Assumption,
    Criterion,
    DayPlan,
    Evidence,
    Experiment,
    Level,
    Observation,
    Post,
    Project,
    Question,
    SearchQuery,
    SearchResult,
    Stance,
)
from .rules import RuleError
from .search import SearchError, Searcher

MAX_RESULTS_TO_MODEL = 30

LABEL_TO_LEVEL = {
    "付费": (Level.L4, Stance.support),
    "承诺": (Level.L3, Stance.support),
    "言论": (Level.L1, Stance.support),
    "否定": (Level.L1, Stance.against),
}

AGAINST_TEMPLATES = ["{k} 免费替代", "{k} 不好用", "{k} 没必要"]


def _ask(llm: LLM, project: Project, task: str, prompt: str) -> dict:
    data = llm.json(task, prompt)
    return scrub_obj(data, task, project.guard_hits)


def _stance(value: str) -> Stance:
    for s in Stance:
        if s.value == str(value).strip():
            return s
    return Stance.neutral


def _int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _answers_text(p: Project) -> str:
    lines = []
    for q in p.questions:
        a = p.answers.get(q.id, "").strip() or "（没回答）"
        lines.append(f"问：{q.question}\n答：{a}")
    return "\n\n".join(lines)


# ---------- 第 1 步：追问 ----------


def ask_questions(p: Project, llm: LLM) -> None:
    if not p.idea.strip():
        raise RuleError("先写下你的点子。")
    data = _ask(llm, p, "clarify", prompts.CLARIFY.format(idea=p.idea))
    qs = [
        Question(question=q["question"], why=q.get("why", ""))
        for q in data.get("questions", [])
        if isinstance(q, dict) and q.get("question")
    ]
    if not qs:
        raise RuleError("模型没有给出追问，请重试。")
    p.questions = qs[:3]
    p.answers = {}


# ---------- 第 2 步：假设和淘汰标准草稿 ----------


def draft_criteria(p: Project, llm: LLM) -> None:
    if p.lock.locked:
        raise RuleError("标准已经锁定。")
    data = _ask(
        llm,
        p,
        "criteria",
        prompts.CRITERIA.format(idea=p.idea, answers=_answers_text(p)),
    )
    p.assumptions = [
        Assumption(
            kind=a.get("kind", "需求") if a.get("kind") in ("需求", "渠道", "付费") else "需求",
            statement=a["statement"],
            how_to_falsify=a.get("how_to_falsify", ""),
        )
        for a in data.get("assumptions", [])
        if isinstance(a, dict) and a.get("statement")
    ]
    crit = []
    for c in data.get("criteria", []):
        if not isinstance(c, dict) or not c.get("metric"):
            continue
        level = Level.L4 if _int(c.get("level"), 3) >= 4 else Level.L3
        extra = {"id": c["id"]} if isinstance(c.get("id"), str) and c["id"].startswith("c_") else {}
        crit.append(
            Criterion(
                **extra,
                metric=c["metric"],
                level=level,
                threshold=max(1, _int(c.get("threshold"), 1)),
                days=min(60, max(1, _int(c.get("days"), 7))),
                note=c.get("note", ""),
            )
        )
    if crit and not any(c.level == Level.L4 for c in crit):
        crit.append(Criterion(metric="付定金的人数", level=Level.L4, threshold=1, days=7, note="模型没给付费标准，代码补的"))
    p.criteria = crit
    p.keywords = [k for k in data.get("keywords", []) if isinstance(k, str) and k.strip()][:3]


# ---------- 第 4 步：案头调研 ----------


def plan_queries(p: Project, llm: LLM) -> list[SearchQuery]:
    data = _ask(
        llm,
        p,
        "queries",
        prompts.QUERIES.format(idea=p.idea, keywords="、".join(p.keywords) or "（无）"),
    )
    qs = [
        SearchQuery(query=q["query"].strip(), kind="反对" if q.get("kind") == "反对" else "支持")
        for q in data.get("queries", [])
        if isinstance(q, dict) and q.get("query", "").strip()
    ]
    # 代码保证：反对类搜索词至少占一半
    k = p.keywords[0] if p.keywords else ""
    templates = iter(AGAINST_TEMPLATES)
    while k and sum(q.kind == "反对" for q in qs) * 2 < len(qs):
        t = next(templates, None)
        if t is None:
            break
        qs.append(SearchQuery(query=t.format(k=k), kind="反对"))
    # 模板用完还不够，就砍掉多余的支持类搜索词
    while sum(q.kind == "反对" for q in qs) * 2 < len(qs):
        idx = max(i for i, q in enumerate(qs) if q.kind == "支持")
        qs.pop(idx)
    return qs[:10]


def skip_research(p: Project) -> None:
    """不搜了，直接进入下一步。"""
    if not p.lock.locked:
        raise RuleError("先定好放弃条件。")
    p.research_done = True


def run_research(p: Project, llm: LLM, searcher: Searcher) -> list[str]:
    """返回过程中的提示信息（例如某条搜索失败）。"""
    if not p.lock.locked:
        raise RuleError("先锁定淘汰标准，再看资料。不然很容易看完资料再把标准改成能通过的样子。")
    notes: list[str] = []
    p.queries = plan_queries(p, llm)

    seen: set[str] = set()
    results: list[SearchResult] = []
    failures = 0
    for q in p.queries:
        try:
            found = searcher.search(q.query, n=5)
        except SearchError as e:
            failures += 1
            if str(e) not in notes:
                notes.append(str(e))
            continue
        for r in found:
            if r.url not in seen:
                seen.add(r.url)
                results.append(r)
    if p.queries and failures == len(p.queries):
        raise SearchError(notes[0])
    p.search_results = results[:MAX_RESULTS_TO_MODEL]

    if not p.search_results:
        notes.append("这次没有搜到资料，所以没有反对意见可看。可以直接进入下一步。")
        p.evidence = []
        p.research_done = True
        return notes

    listing = "\n".join(
        f"[ref {i}] {r.title}\n{r.url}\n{r.snippet[:300]}" for i, r in enumerate(p.search_results)
    )
    data = _ask(
        llm,
        p,
        "evidence",
        prompts.CLASSIFY_EVIDENCE.format(idea=p.idea, results=listing),
    )
    evidence: list[Evidence] = []
    dropped = 0
    for e in data.get("evidence", []):
        ref = _int(e.get("ref") if isinstance(e, dict) else None, -1)
        if not (0 <= ref < len(p.search_results)) or not e.get("claim"):
            dropped += 1  # 模型引用了不存在的来源：丢掉
            continue
        src = p.search_results[ref]
        level = Level(min(max(_int(e.get("level"), 0), 0), DESK_RESEARCH_MAX))  # 代码强制上限 L2
        evidence.append(
            Evidence(
                claim=e["claim"],
                stance=_stance(e.get("stance", "")),
                level=level,
                source_title=src.title,
                url=src.url,
                query=src.query,
            )
        )
    if dropped:
        notes.append(f"AI 有 {dropped} 条说法找不到出处，已经去掉了。")
    order = {Stance.against: 0, Stance.support: 1, Stance.neutral: 2}
    evidence.sort(key=lambda x: (order[x.stance], -int(x.level)))
    p.evidence = evidence
    p.research_done = True
    return notes


# ---------- 第 5 步：验证实验 ----------


def plan_experiment(p: Project, llm: LLM) -> None:
    if not p.lock.locked:
        raise RuleError("先锁定淘汰标准。")
    criteria_text = "\n".join(
        f"- id={c.id}｜{c.sentence()}｜等级：{'付费' if c.level == Level.L4 else '承诺'}" for c in p.criteria
    )
    against = [e for e in p.evidence if e.stance == Stance.against][:5]
    against_text = "\n".join(f"- {e.claim}" for e in against) or "（没有找到）"
    data = _ask(
        llm,
        p,
        "experiment",
        prompts.EXPERIMENT.format(
            idea=p.idea, answers=_answers_text(p), criteria=criteria_text, against=against_text
        ),
    )
    ids = {c.id for c in p.criteria}
    fallback = next((c.id for c in p.criteria if c.level == Level.L3), p.criteria[0].id)
    days = [
        DayPlan(
            day=_int(d.get("day"), i + 1),
            action=d["action"],
            criterion_id=d.get("criterion_id") if d.get("criterion_id") in ids else None,
        )
        for i, d in enumerate(data.get("days", []))
        if isinstance(d, dict) and d.get("action")
    ]
    posts = [
        Post(
            channel=x.get("channel", "其他"),
            title=x.get("title", ""),
            body=x["body"],
            cta=x.get("cta", "") or "评论区回复「想要」",
            criterion_id=x.get("criterion_id") if x.get("criterion_id") in ids else fallback,
        )
        for x in data.get("posts", [])
        if isinstance(x, dict) and x.get("body")
    ]
    questions = [q for q in data.get("interview_questions", []) if isinstance(q, str) and q.strip()]
    started = p.experiment.started_at if p.experiment else None
    p.experiment = Experiment(days=days, posts=posts, interview_questions=questions, started_at=started)


def start_experiment(p: Project, now: datetime) -> None:
    if not p.experiment:
        raise RuleError("先生成实验方案。")
    if not p.experiment.started_at:
        p.experiment.started_at = now


# ---------- 第 6 步：回填结果 ----------


def classify_observations(p: Project, llm: LLM, raw: str) -> list[Observation]:
    if not raw.strip():
        raise RuleError("先粘贴评论或私信。")
    data = _ask(
        llm,
        p,
        "observations",
        prompts.CLASSIFY_OBSERVATIONS.format(idea=p.idea, raw=raw[:6000]),
    )
    added = []
    for it in data.get("items", []):
        if not isinstance(it, dict):
            continue
        label = str(it.get("label", "")).strip()
        if label not in LABEL_TO_LEVEL or not it.get("text"):
            continue  # "无关"或格式不对，跳过
        level, stance = LABEL_TO_LEVEL[label]  # 等级由代码根据标签决定
        added.append(Observation(text=it["text"], label=label, level=level, stance=stance))
    p.observations.extend(added)
    return added


def criteria_json(p: Project) -> str:
    return json.dumps([c.model_dump(mode="json") for c in p.criteria], ensure_ascii=False)
