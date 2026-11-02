"""乐观拦截器。

在 prompt 里写"请客观"挡不住模型的乐观倾向，所以在输出端用规则再过一遍：
分数、成功率、"前景广阔""刚需"这类没有证据支撑的判断，一律替换掉并计数。
"""

from __future__ import annotations

import re
from typing import Any

from .models import GuardHit

REPLACEMENT = "〔已拦截：无证据的判断〕"

_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("打分", re.compile(r"\d+(?:\.\d+)?\s*[/／]\s*10(?!\d)")),
    ("打分", re.compile(r"\d+(?:\.\d+)?\s*[/／]\s*100(?!\d)")),
    ("打分", re.compile(r"(?:评分|打分|得分|总分|潜力分|可行性)\s*[:：为是]?\s*\d+(?:\.\d+)?\s*分?")),
    ("打分", re.compile(r"(?<![\d.])\d{1,3}(?:\.\d)?\s*分(?=$|[\s，。,.;；!！）)])")),
    ("成功率", re.compile(r"(?:成功|跑通|盈利)(?:率|概率|可能性)\s*[:：为约是大概有]*\s*\d+(?:\.\d+)?\s*%")),
    ("星级", re.compile(r"[★⭐]{2,}")),
]

_PHRASES = [
    "前景广阔", "前景巨大", "前景非常好", "非常有前景", "很有前景", "大有可为",
    "潜力巨大", "潜力无限", "巨大的潜力", "巨大潜力",
    "市场巨大", "巨大的市场", "市场空间巨大", "广阔的市场",
    "蓝海", "风口", "刚需", "痛点明确", "需求旺盛", "需求强烈", "需求巨大",
    "市场空白", "空白市场", "填补空白",
    "一定能成功", "必然成功", "肯定能火", "一定会火", "稳赚", "躺赚",
    "值得一做", "值得去做", "非常值得", "强烈建议",
]

_ADVICE = re.compile(r"建议(?:你)?(?:立即|马上|尽快|直接)?(?:开发|上线|开始做|做这个|立项|投入)")


def scrub(text: str, where: str = "") -> tuple[str, list[GuardHit]]:
    hits: list[GuardHit] = []
    out = text
    for name, pat in _PATTERNS:
        def _sub(m: re.Match, name=name) -> str:
            hits.append(GuardHit(where=where, phrase=m.group(0)))
            return REPLACEMENT
        out = pat.sub(_sub, out)
    for phrase in _PHRASES:
        if phrase in out:
            hits.extend(GuardHit(where=where, phrase=phrase) for _ in range(out.count(phrase)))
            out = out.replace(phrase, REPLACEMENT)
    def _sub_advice(m: re.Match) -> str:
        hits.append(GuardHit(where=where, phrase=m.group(0)))
        return REPLACEMENT
    out = _ADVICE.sub(_sub_advice, out)
    return out, hits


def scrub_obj(obj: Any, where: str, hits: list[GuardHit]) -> Any:
    """递归清理模型返回的 JSON 里的所有字符串。"""
    if isinstance(obj, str):
        clean, h = scrub(obj, where)
        hits.extend(h)
        return clean
    if isinstance(obj, list):
        return [scrub_obj(x, where, hits) for x in obj]
    if isinstance(obj, dict):
        return {k: scrub_obj(v, where, hits) for k, v in obj.items()}
    return obj
