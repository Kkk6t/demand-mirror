"""判定规则。

状态由这里的代码决定，不由模型决定。模型只负责把文字归类，
"这个点子现在处于什么状态"永远是确定性规则算出来的，可以复现、可以测试。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime

from .models import (
    DESK_RESEARCH_MAX,
    LEVEL_NAMES,
    CriteriaChange,
    Criterion,
    Level,
    Project,
    Stance,
    Status,
)

# 案头调研里，至少有这么多条"行为级"反对证据，才算出现反向信号
DESK_NEGATIVE_MIN = 2


class RuleError(ValueError):
    """用户的操作违反了产品规则（例如没锁标准就想调研）。"""


# ---------- 淘汰标准 ----------


def fingerprint(criteria: list[Criterion]) -> str:
    payload = [
        {"metric": c.metric, "level": int(c.level), "threshold": c.threshold, "days": c.days}
        for c in criteria
    ]
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def validate_criteria(criteria: list[Criterion]) -> None:
    if not criteria:
        raise RuleError("至少写一条淘汰标准。")
    if not any(c.level == Level.L4 for c in criteria):
        raise RuleError("至少要有一条「付费」级别的标准。没有付费标准的验证，只能证明有人感兴趣。")
    for c in criteria:
        if c.level < Level.L3:
            raise RuleError(
                f"「{c.metric}」是{LEVEL_NAMES[c.level]}级别。淘汰标准只能用承诺（L3）或付费（L4），"
                "因为点赞和评论说'好想要'都不花成本。"
            )
        if not c.metric.strip():
            raise RuleError("有一条标准没写指标名称。")


def lock_criteria(project: Project, now: datetime) -> None:
    validate_criteria(project.criteria)
    project.lock.locked_at = now
    project.lock.fingerprint = fingerprint(project.criteria)


def is_loosened(before: list[Criterion], after: list[Criterion]) -> bool:
    """门槛降低、期限延长、删掉了标准，都算放水。"""
    b = {c.id: c for c in before}
    a = {c.id: c for c in after}
    if set(b) - set(a):
        return True
    for cid, old in b.items():
        new = a[cid]
        if new.threshold < old.threshold or new.days > old.days or new.level < old.level:
            return True
    return False


def change_criteria(
    project: Project, new: list[Criterion], reason: str, now: datetime
) -> CriteriaChange | None:
    """锁定前随便改；锁定后改必须写理由，并留下记录。"""
    if not project.lock.locked:
        project.criteria = new
        return None
    if not reason.strip():
        raise RuleError("锁定后修改标准必须写理由，理由会写进报告。")
    validate_criteria(new)
    change = CriteriaChange(
        at=now,
        reason=reason.strip(),
        before=[c.model_copy() for c in project.criteria],
        after=[c.model_copy() for c in new],
        loosened=is_loosened(project.criteria, new),
    )
    project.lock.history.append(change)
    project.criteria = new
    project.lock.fingerprint = fingerprint(new)
    return change


# ---------- 判定 ----------


@dataclass
class CriterionResult:
    criterion: Criterion
    count: int
    met: bool
    expired: bool
    source: str  # "手动填写" / "评论归类"


@dataclass
class Verdict:
    status: Status
    reasons: list[str] = field(default_factory=list)
    highest_level: Level = Level.L0
    results: list[CriterionResult] = field(default_factory=list)
    loosen_count: int = 0


def count_for(project: Project, c: Criterion) -> tuple[int, str]:
    """手动填写的数字优先；没填就用评论归类的结果。"""
    if c.id in project.manual_counts:
        return project.manual_counts[c.id], "手动填写"
    n = sum(
        1
        for o in project.observations
        if o.stance != Stance.against and o.level == c.level
    )
    return n, "评论归类"


def desk_against(project: Project) -> list:
    return [
        e
        for e in project.evidence
        if e.stance == Stance.against and e.level >= Level.L2
    ]


def evaluate(project: Project, now: datetime) -> Verdict:
    results: list[CriterionResult] = []
    for c in project.criteria:
        n, source = count_for(project, c)
        deadline = project.deadline(c)
        expired = deadline is not None and now >= deadline
        results.append(CriterionResult(c, n, n >= c.threshold, expired, source))

    # 最高证据等级：实验数据 + 案头支持证据（案头最高 L2）
    highest = Level.L0
    for e in project.evidence:
        if e.stance == Stance.support:
            highest = max(highest, min(e.level, DESK_RESEARCH_MAX))
    for o in project.observations:
        if o.stance != Stance.against:
            highest = max(highest, o.level)
    for r in results:
        if r.count > 0:
            highest = max(highest, r.criterion.level)

    loosen = sum(1 for ch in project.lock.history if ch.loosened)
    v = Verdict(Status.unverified, highest_level=Level(highest), results=results, loosen_count=loosen)

    pay = [r for r in results if r.criterion.level == Level.L4]
    killed = [r for r in results if r.expired and not r.met]
    against = desk_against(project)

    # 1. 付费标准全部达成：唯一能得到"付费信号"的路径
    if pay and all(r.met for r in pay):
        v.status = Status.paid
        for r in pay:
            v.reasons.append(
                f"「{r.criterion.metric}」达到 {r.count}，你定的标准是 {r.criterion.threshold}。"
            )
        for r in killed:
            v.reasons.append(f"但「{r.criterion.metric}」没达标（{r.count}/{r.criterion.threshold}），值得想想为什么。")
    # 2. 到期没达标：触发你自己写下的淘汰条件
    elif killed:
        v.status = Status.negative
        for r in killed:
            v.reasons.append(
                f"{r.criterion.days} 天到期，「{r.criterion.metric}」只有 {r.count}，"
                f"没到你自己定的 {r.criterion.threshold}。按你锁定的标准，这个点子该放下了。"
            )
    # 3. 案头资料里有足够多的行为级反对证据
    elif len(against) >= DESK_NEGATIVE_MIN:
        v.status = Status.negative
        v.reasons.append(
            f"案头调研找到 {len(against)} 条行为级反对证据（例如已有人在用免费替代方案）。"
            "这不代表一定失败，但你的实验需要先回答：为什么人们会放弃现有方案来用你的。"
        )
    # 4. 其余情况都是未验证
    else:
        if not project.research_done:
            v.reasons.append("还没做调研，也没跑实验。")
        elif not project.experiment or not project.experiment.started_at:
            v.reasons.append("案头调研只能证明到「行为」级别，证明不了有人会为你付钱。下一步是跑实验。")
        else:
            for r in pay:
                left = r.criterion.threshold - r.count
                v.reasons.append(f"「{r.criterion.metric}」现在是 {r.count}，离标准还差 {left}。")
            if not pay:
                v.reasons.append("实验进行中。")

    if loosen:
        v.reasons.append(f"注意：锁定后标准被放宽过 {loosen} 次。")
    return v
