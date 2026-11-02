"""数据模型。

整个产品围绕一个判断：**证据有等级**。
案头资料（搜索结果）最高只能说明"市场上有人有这个问题"，
永远说明不了"有人会为你付钱"。所以等级 L3、L4 只能来自用户自己跑的实验。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from enum import Enum, IntEnum

from pydantic import BaseModel, Field


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


class Level(IntEnum):
    """证据等级。数字越大，越接近"有人真的要"。"""

    L0 = 0  # 推测：AI 或你自己的判断，没有来源
    L1 = 1  # 言论：有人说过想要、在讨论这个问题
    L2 = 2  # 行为：有人正在为这个问题花钱、花时间（买竞品、自己凑替代方案）
    L3 = 3  # 承诺：有人对【你】留了联系方式、预约、排队
    L4 = 4  # 付费：有人对【你】付了钱或定金


LEVEL_NAMES = {
    Level.L0: "猜的",
    Level.L1: "嘴上说",
    Level.L2: "在花钱花时间",
    Level.L3: "留了联系方式",
    Level.L4: "付了钱",
}

LEVEL_HINTS = {
    Level.L0: "AI 或你自己的判断，没有出处",
    Level.L1: "有人说想要，但没有任何行动",
    Level.L2: "有人已经在为这个问题买别的产品、自己凑合解决",
    Level.L3: "有人主动私信你、加你微信、预约",
    Level.L4: "有人真的给你付了钱或定金",
}

# 案头调研（联网搜索）能达到的最高等级。由代码强制，不由模型决定。
DESK_RESEARCH_MAX = Level.L2


class Stance(str, Enum):
    support = "支持"
    against = "反对"
    neutral = "中性"


class Status(str, Enum):
    """结果只有三种。没有分数，没有"建议做"。"""

    unverified = "还不知道"
    negative = "先别做"
    paid = "有人愿意付钱"


STATUS_MEANING = {
    Status.unverified: "证据还不够，说明不了任何事。继续往下走。",
    Status.negative: "你自己定的放弃条件被触发了，或者网上的反对意见很多。先别急着写代码。",
    Status.paid: "有人真的给你付钱了。可以开始做一个最小的版本。",
}


class Question(BaseModel):
    id: str = Field(default_factory=lambda: _id("q"))
    question: str
    why: str = ""


class Assumption(BaseModel):
    id: str = Field(default_factory=lambda: _id("a"))
    kind: str  # 需求 / 渠道 / 付费
    statement: str
    how_to_falsify: str = ""


class Criterion(BaseModel):
    """淘汰标准：在 days 天内，metric 达到 threshold，否则淘汰。"""

    id: str = Field(default_factory=lambda: _id("c"))
    metric: str
    level: Level
    threshold: int = Field(ge=1)
    days: int = Field(ge=1, le=60)
    note: str = ""

    def sentence(self) -> str:
        return f"{self.days} 天内，如果「{self.metric}」不到 {self.threshold} 个，就放弃"


class CriteriaChange(BaseModel):
    at: datetime
    reason: str
    before: list[Criterion]
    after: list[Criterion]
    loosened: bool  # 是否放水：门槛降低或期限延长


class CriteriaLock(BaseModel):
    locked_at: datetime | None = None
    fingerprint: str | None = None
    history: list[CriteriaChange] = Field(default_factory=list)

    @property
    def locked(self) -> bool:
        return self.locked_at is not None


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str = ""
    query: str = ""


class SearchQuery(BaseModel):
    query: str
    kind: str = "支持"  # 支持 / 反对（反对 = 专门找推翻点子的证据）


class Evidence(BaseModel):
    id: str = Field(default_factory=lambda: _id("e"))
    claim: str
    stance: Stance
    level: Level
    source_title: str = ""
    url: str = ""
    query: str = ""


class DayPlan(BaseModel):
    day: int
    action: str
    criterion_id: str | None = None


class Post(BaseModel):
    """可计数的宣传：每条宣传都必须带一个能数出来的行动。"""

    channel: str
    title: str = ""
    body: str
    cta: str  # 让读者做的那个动作，例如"评论区回复 想要"
    criterion_id: str  # 这条帖子产生的数据算进哪条标准


class Experiment(BaseModel):
    days: list[DayPlan] = Field(default_factory=list)
    posts: list[Post] = Field(default_factory=list)
    interview_questions: list[str] = Field(default_factory=list)
    started_at: datetime | None = None


class Observation(BaseModel):
    id: str = Field(default_factory=lambda: _id("o"))
    text: str
    label: str  # 付费 / 承诺 / 言论 / 否定
    level: Level
    stance: Stance


class GuardHit(BaseModel):
    where: str
    phrase: str


class Project(BaseModel):
    id: str = Field(default_factory=lambda: _id("p"))
    created_at: datetime = Field(default_factory=datetime.now)
    demo: bool = False
    quick: bool = False  # 用「一键体检」跑出来的

    idea: str = ""
    questions: list[Question] = Field(default_factory=list)
    answers: dict[str, str] = Field(default_factory=dict)

    assumptions: list[Assumption] = Field(default_factory=list)
    criteria: list[Criterion] = Field(default_factory=list)
    lock: CriteriaLock = Field(default_factory=CriteriaLock)

    keywords: list[str] = Field(default_factory=list)
    queries: list[SearchQuery] = Field(default_factory=list)
    search_results: list[SearchResult] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    research_done: bool = False

    experiment: Experiment | None = None
    observations: list[Observation] = Field(default_factory=list)
    manual_counts: dict[str, int] = Field(default_factory=dict)

    guard_hits: list[GuardHit] = Field(default_factory=list)

    def criterion(self, cid: str) -> Criterion | None:
        return next((c for c in self.criteria if c.id == cid), None)

    def deadline(self, c: Criterion) -> datetime | None:
        if not self.experiment or not self.experiment.started_at:
            return None
        return self.experiment.started_at + timedelta(days=c.days)

    @property
    def title(self) -> str:
        text = self.idea.strip().splitlines()[0] if self.idea.strip() else "未命名点子"
        return text[:24] + ("…" if len(text) > 24 else "")


# 归类标签在界面上的叫法
OBS_LABELS = {
    "付费": "付了钱",
    "承诺": "留了联系方式",
    "言论": "只是说说",
    "否定": "不需要",
}
