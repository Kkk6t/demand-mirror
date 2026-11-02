"""导出 Markdown 报告：证据台账 + 判定 + 实验方案，可以直接放进仓库或发给别人。"""

from __future__ import annotations

from datetime import datetime

from .models import LEVEL_NAMES, OBS_LABELS, STATUS_MEANING, Level, Project, Stance
from .rules import evaluate


def _fmt(dt: datetime | None) -> str:
    return dt.strftime("%Y-%m-%d %H:%M") if dt else "—"


def _cell(s: str) -> str:
    return s.replace("|", "｜").replace("\n", " ")


def to_markdown(p: Project, now: datetime) -> str:
    v = evaluate(p, now)
    L: list[str] = []
    L.append(f"# 验证报告：{p.title}\n")
    L.append(f"> 由「需求照妖镜」生成于 {_fmt(now)}。本报告不打分、不给建议，只记录现在有什么证据。\n")

    L.append("## 判定\n")
    L.append(f"**{v.status.value}**　·　手里最硬的证据：{LEVEL_NAMES[v.highest_level]}\n")
    L.append(STATUS_MEANING[v.status] + "\n")
    for r in v.reasons:
        L.append(f"- {r}")
    L.append("")

    L.append("## 点子\n")
    L.append(p.idea.strip() + "\n")
    if p.questions:
        L.append("## 3 个问题\n")
        for q in p.questions:
            L.append(f"**{q.question}**\n")
            L.append((p.answers.get(q.id) or "（没回答）") + "\n")

    if p.assumptions:
        L.append("## 最可能出错的地方\n")
        L.append("| 类型 | 你默认相信的事 | 出现什么情况说明它错了 |")
        L.append("|---|---|---|")
        for a in p.assumptions:
            L.append(f"| {a.kind} | {_cell(a.statement)} | {_cell(a.how_to_falsify)} |")
        L.append("")

    if p.criteria:
        L.append("## 放弃条件\n")
        state = f"定于 {_fmt(p.lock.locked_at)}（看资料之前），编号 `{p.lock.fingerprint}`" if p.lock.locked else "还没定"
        L.append(f"{state}\n")
        L.append("| 条件 | 数的是 | 现在 | 达到了吗 |")
        L.append("|---|---|---|---|")
        for r in v.results:
            ok = "达到" if r.met else ("到期没达到" if r.expired else "还没")
            L.append(
                f"| {_cell(r.criterion.sentence())} | {LEVEL_NAMES[r.criterion.level]} | {r.count} | {ok} |"
            )
        L.append("")
        if p.lock.history:
            L.append("### 修改记录\n")
            for ch in p.lock.history:
                tag = "（放宽）" if ch.loosened else ""
                L.append(f"- {_fmt(ch.at)}{tag}：{ch.reason}")
            L.append("")

    if p.research_done:
        L.append("## 网上找到的资料\n")
        L.append("网上的资料只能说明市场情况，证明不了有人会给你付钱。反对意见排在前面。\n")
        if p.evidence:
            L.append("| 态度 | 可信度 | 说明了什么 | 出处 |")
            L.append("|---|---|---|---|")
            for e in p.evidence:
                src = f"[{_cell(e.source_title or e.url)}]({e.url})" if e.url else "—"
                L.append(f"| {e.stance.value} | {LEVEL_NAMES[e.level]} | {_cell(e.claim)} | {src} |")
            L.append("")
        else:
            L.append("没有找到资料。\n")
        if p.queries:
            L.append("<details><summary>搜索词</summary>\n")
            for q in p.queries:
                L.append(f"- [{q.kind}] {q.query}")
            L.append("\n</details>\n")

    if p.experiment:
        ex = p.experiment
        L.append("## 一周发帖测试\n")
        L.append(f"开始时间：{_fmt(ex.started_at)}\n")
        for d in ex.days:
            L.append(f"- 第 {d.day} 天：{d.action}")
        L.append("")
        if ex.posts:
            L.append("### 要发的帖子\n")
            for post in ex.posts:
                c = p.criterion(post.criterion_id)
                L.append(f"**{post.channel}**" + (f"：{post.title}" if post.title else "") + "\n")
                L.append(post.body.strip() + "\n")
                L.append(f"让读者做的事：{post.cta}　→ 记到「{c.metric if c else '—'}」\n")
        if ex.interview_questions:
            L.append("### 去问人的问题\n")
            for i, q in enumerate(ex.interview_questions, 1):
                L.append(f"{i}. {q}")
            L.append("")

    if p.observations:
        L.append("## 收到的真实反应\n")
        L.append("| 归类 | 原话 |")
        L.append("|---|---|---|")
        for o in p.observations:
            L.append(f"| {OBS_LABELS.get(o.label, o.label)} | {_cell(o.text)} |")
        L.append("")

    if p.guard_hits:
        L.append("## 被拦下的空话\n")
        L.append(f"AI 的回答里有 {len(p.guard_hits)} 处没有证据的乐观说法被拦下：" + "、".join(sorted({h.phrase for h in p.guard_hits})) + "\n")

    return "\n".join(L).rstrip() + "\n"


__all__ = ["to_markdown", "Level"]
