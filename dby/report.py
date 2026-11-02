"""导出 Markdown 报告：证据台账 + 判定 + 实验方案，可以直接放进仓库或发给别人。"""

from __future__ import annotations

from datetime import datetime

from .models import LEVEL_NAMES, Level, Project, Stance
from .rules import evaluate


def _fmt(dt: datetime | None) -> str:
    return dt.strftime("%Y-%m-%d %H:%M") if dt else "—"


def _cell(s: str) -> str:
    return s.replace("|", "｜").replace("\n", " ")


def to_markdown(p: Project, now: datetime) -> str:
    v = evaluate(p, now)
    L: list[str] = []
    L.append(f"# 验证报告：{p.title}\n")
    L.append(f"> 由「先别做」生成于 {_fmt(now)}。本报告不打分、不给建议，只记录现在有什么证据。\n")

    L.append("## 判定\n")
    L.append(f"**{v.status.value}**　·　目前最高证据等级：L{int(v.highest_level)} {LEVEL_NAMES[v.highest_level]}\n")
    for r in v.reasons:
        L.append(f"- {r}")
    L.append("")

    L.append("## 点子\n")
    L.append(p.idea.strip() + "\n")
    if p.questions:
        L.append("## 追问\n")
        for q in p.questions:
            L.append(f"**{q.question}**\n")
            L.append((p.answers.get(q.id) or "（没回答）") + "\n")

    if p.assumptions:
        L.append("## 最危险的假设\n")
        L.append("| 类型 | 假设 | 什么情况说明它错了 |")
        L.append("|---|---|---|")
        for a in p.assumptions:
            L.append(f"| {a.kind} | {_cell(a.statement)} | {_cell(a.how_to_falsify)} |")
        L.append("")

    if p.criteria:
        L.append("## 淘汰标准\n")
        state = f"锁定于 {_fmt(p.lock.locked_at)}，指纹 `{p.lock.fingerprint}`" if p.lock.locked else "未锁定"
        L.append(f"{state}\n")
        L.append("| 标准 | 等级 | 当前 | 达标 |")
        L.append("|---|---|---|---|")
        for r in v.results:
            ok = "是" if r.met else ("到期未达标" if r.expired else "否")
            L.append(
                f"| {_cell(r.criterion.sentence())} | L{int(r.criterion.level)} {LEVEL_NAMES[r.criterion.level]} | {r.count} | {ok} |"
            )
        L.append("")
        if p.lock.history:
            L.append("### 修改记录\n")
            for ch in p.lock.history:
                tag = "（放宽）" if ch.loosened else ""
                L.append(f"- {_fmt(ch.at)}{tag}：{ch.reason}")
            L.append("")

    if p.research_done:
        L.append("## 证据台账\n")
        L.append("案头资料最高只能到 L2（行为），证明不了有人会为你付钱。\n")
        if p.evidence:
            L.append("| 立场 | 等级 | 说明了什么 | 来源 |")
            L.append("|---|---|---|---|")
            for e in p.evidence:
                src = f"[{_cell(e.source_title or e.url)}]({e.url})" if e.url else "—"
                L.append(f"| {e.stance.value} | L{int(e.level)} | {_cell(e.claim)} | {src} |")
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
        L.append("## 7 天验证实验\n")
        L.append(f"开始时间：{_fmt(ex.started_at)}\n")
        for d in ex.days:
            L.append(f"- 第 {d.day} 天：{d.action}")
        L.append("")
        if ex.posts:
            L.append("### 可计数的宣传\n")
            for post in ex.posts:
                c = p.criterion(post.criterion_id)
                L.append(f"**{post.channel}**" + (f"：{post.title}" if post.title else "") + "\n")
                L.append(post.body.strip() + "\n")
                L.append(f"行动：{post.cta}　→ 计入「{c.metric if c else '—'}」\n")
        if ex.interview_questions:
            L.append("### 访谈问题\n")
            for i, q in enumerate(ex.interview_questions, 1):
                L.append(f"{i}. {q}")
            L.append("")

    if p.observations:
        L.append("## 收到的反馈\n")
        L.append("| 归类 | 等级 | 原话 |")
        L.append("|---|---|---|")
        for o in p.observations:
            lvl = "反对" if o.stance == Stance.against else f"L{int(o.level)}"
            L.append(f"| {o.label} | {lvl} | {_cell(o.text)} |")
        L.append("")

    if p.guard_hits:
        L.append("## 乐观拦截\n")
        L.append(f"模型输出里有 {len(p.guard_hits)} 处无证据的乐观表述被拦截：" + "、".join(sorted({h.phrase for h in p.guard_hits})) + "\n")

    return "\n".join(L).rstrip() + "\n"


__all__ = ["to_markdown", "Level"]
