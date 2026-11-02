"""界面用的 HTML 片段和样式。视觉概念：一张「点子检验单」。"""

from __future__ import annotations

import html

from .models import DESK_RESEARCH_MAX, LEVEL_HINTS, LEVEL_NAMES, Evidence, Level, Observation, Stance, Status

CSS = """
<style>
:root {
  --paper: #F6F8FB;
  --sheet: #FFFFFF;
  --ink: #1D2A44;
  --muted: #5C6A80;
  --rule: #CAD6E4;
  --rule-soft: #E3EAF2;
  --red: #B3342B;
  --green: #2E7650;
  --grey: #727C8C;
  --mark: #FFF1B8;
}
html, body, [class*="css"], .stMarkdown, .stTextArea textarea, .stTextInput input, button {
  font-family: "Noto Sans SC", "Noto Sans CJK SC", "PingFang SC", "Microsoft YaHei", "微软雅黑", sans-serif;
}
.stApp { background: var(--paper); color: var(--ink); }
[data-testid="stSidebar"] { background: #EDF1F6; border-right: 1px solid var(--rule); }
.block-container { max-width: 900px; padding-top: 2.2rem; }
h1, h2, h3, .serif, .masthead h1, .step h3 { font-family: "Noto Serif SC", "Noto Serif CJK SC", "Source Han Serif SC", "Songti SC", "STSong", "SimSun", "宋体", serif !important; color: var(--ink); letter-spacing: 0; }

/* 抬头 */
.masthead { border-bottom: 3px double var(--ink); padding-bottom: .9rem; margin-bottom: 1.6rem; }
.masthead h1 { font-size: 3.1rem; font-weight: 900; line-height: 1.05; margin: 0; padding: 0; }
.masthead p { color: var(--muted); font-size: 1.05rem; margin: .5rem 0 0; }
.masthead .mode { font-size: .85rem; color: var(--muted); margin-top: .6rem; }
.masthead .mode b { color: var(--ink); font-weight: 500; }

/* 步骤抬头：像表格的栏目 */
.step { display: grid; grid-template-columns: 2.4rem 1fr auto; align-items: baseline;
        border-top: 1px solid var(--ink); padding-top: .7rem; margin: 2.2rem 0 .6rem; }
.step .n { font-family: "Noto Serif SC", "Noto Serif CJK SC", "Source Han Serif SC", "Songti SC", "STSong", "SimSun", serif; font-weight: 900; font-size: 1.5rem; color: var(--ink); }
.step h3 { margin: 0; padding: 0; font-size: 1.3rem; font-weight: 600; }
.step .s { font-size: .82rem; color: var(--muted); }
.step.todo { border-top-color: var(--rule); }
.step.todo .n, .step.todo h3 { color: #9AA6B8; }
.lede { color: var(--muted); font-size: .95rem; margin: 0 0 .8rem 2.4rem; max-width: 70ch; }

/* 印章：整个界面唯一大胆的元素 */
.stamp { display: inline-block; font-family: "Noto Serif SC", "Noto Serif CJK SC", "Source Han Serif SC", "Songti SC", "STSong", "SimSun", serif; font-weight: 900;
         font-size: 1.55rem; padding: .45rem 1.1rem; border: 4px double currentColor;
         border-radius: 6px; transform: rotate(-7deg); letter-spacing: .12em; opacity: .92;
         mix-blend-mode: multiply; }
.stamp.big { font-size: 2.4rem; padding: .6rem 1.6rem; border-width: 6px; }
.stamp.未验证 { color: var(--grey); }
.stamp.出现反向信号 { color: var(--red); }
.stamp.出现付费信号 { color: var(--green); }
.stamp-wrap { padding: .6rem 0 1rem .4rem; }
.stamp-wrap.anim { padding: 1.2rem 0 1.8rem .6rem; }
.stamp-wrap.anim .stamp { animation: thud .32s cubic-bezier(.2,1.6,.4,1) both; }
@keyframes thud { from { transform: rotate(-7deg) scale(1.6); opacity: 0; } to { transform: rotate(-7deg) scale(1); opacity: .92; } }
@media (prefers-reduced-motion: reduce) { .stamp-wrap.anim .stamp { animation: none; } }

/* 证据阶梯 */
.ladder { margin: .4rem 0 .2rem; }
.rung { display: grid; grid-template-columns: 2rem 1fr; gap: .5rem; align-items: center;
        padding: .28rem 0; font-size: .86rem; color: #9AA6B8; }
.rung .tag { font-weight: 700; text-align: center; border: 1.5px solid #BCC7D6; border-radius: 3px; font-size: .75rem; padding: 1px 0; }
.rung.on { color: var(--ink); }
.rung.on .tag { background: var(--ink); border-color: var(--ink); color: #fff; }
.rung small { display: block; font-size: .74rem; color: inherit; opacity: .8; }
.cap { border-top: 1.5px dashed var(--muted); margin: .15rem 0 .15rem 2.5rem; font-size: .72rem; color: var(--muted); padding-top: 2px; }

/* 台账 */
table.ledger { width: 100%; border-collapse: collapse; font-size: .9rem; margin: .4rem 0 1rem; background: var(--sheet); }
.ledger th { text-align: left; font-weight: 500; color: var(--muted); font-size: .8rem; border-bottom: 1.5px solid var(--ink); padding: .4rem .5rem; }
.ledger td { border-bottom: 1px solid var(--rule-soft); padding: .55rem .5rem; vertical-align: top; }
.ledger td.k { white-space: nowrap; width: 4.2rem; }
.ledger a { color: var(--ink); text-decoration-color: var(--rule); text-underline-offset: 3px; font-size: .82rem; }
.ledger a:hover { text-decoration-color: var(--ink); }
.hl { background: linear-gradient(transparent 58%, var(--mark) 58%); -webkit-box-decoration-break: clone; box-decoration-break: clone; }
.pill { display: inline-block; font-size: .76rem; padding: 1px 7px; border-radius: 3px; border: 1px solid; }
.pill.反对 { color: var(--red); }
.pill.支持 { color: var(--green); }
.pill.中性 { color: var(--grey); }
.lv { font-size: .76rem; color: var(--muted); margin-left: .3rem; }

/* 标准、帖子 */
.rule-line { font-family: "Noto Serif SC", "Noto Serif CJK SC", "Source Han Serif SC", "Songti SC", "STSong", "SimSun", serif; font-size: 1.05rem; padding: .45rem 0; border-bottom: 1px solid var(--rule-soft); }
.rule-line .lv { font-family: "Noto Sans SC", sans-serif; }
.meta { font-size: .82rem; color: var(--muted); }
.post { background: var(--sheet); border: 1px solid var(--rule); border-radius: 4px; padding: .9rem 1rem; margin-bottom: .8rem; }
.post .ch { font-weight: 700; font-size: .85rem; }
.post .t { font-family: "Noto Serif SC", "Noto Serif CJK SC", "Source Han Serif SC", "Songti SC", "STSong", "SimSun", serif; font-weight: 600; font-size: 1.05rem; margin: .3rem 0; }
.post .b { font-size: .92rem; line-height: 1.75; }
.post .cta { margin-top: .6rem; padding: .45rem .6rem; border-left: 3px solid var(--ink); background: #F1F4F8; font-size: .9rem; }
.guard { font-size: .82rem; color: var(--muted); }
.guard b { color: var(--red); font-weight: 700; }

.stButton button[kind="primary"] { background: var(--ink); border-color: var(--ink); }
.stButton button[kind="primary"]:hover { background: #2C3D60; border-color: #2C3D60; }
.stButton button:focus-visible { outline: 2px solid var(--ink); outline-offset: 2px; }
@media (max-width: 640px) {
  .masthead h1 { font-size: 2.3rem; }
  .lede { margin-left: 0; }
  .ledger td.k { white-space: normal; }
}
</style>
"""

e = html.escape


def masthead(mode: str) -> str:
    return f"""<div class="masthead"><h1>先别做</h1>
<p>不预测你的点子行不行，只帮你拿到能推翻它的证据。</p>
<div class="mode">{mode}</div></div>"""


def step(n: int, title: str, state: str = "", todo: bool = False) -> str:
    cls = "step todo" if todo else "step"
    return f'<div class="{cls}"><span class="n">{n}</span><h3>{e(title)}</h3><span class="s">{e(state)}</span></div>'


def lede(text: str) -> str:
    return f'<p class="lede">{e(text)}</p>'


def stamp(status: Status, big: bool = False, anim: bool = False) -> str:
    cls = f"stamp {status.value}" + (" big" if big else "")
    wrap = "stamp-wrap anim" if anim else "stamp-wrap"
    return f'<div class="{wrap}"><span class="{cls}">{e(status.value)}</span></div>'


def ladder(highest: Level) -> str:
    rows = []
    for lv in sorted(Level, reverse=True):
        on = " on" if lv <= highest else ""
        rows.append(
            f'<div class="rung{on}"><span class="tag">L{int(lv)}</span>'
            f"<span>{LEVEL_NAMES[lv]}<small>{LEVEL_HINTS[lv]}</small></span></div>"
        )
        if lv == DESK_RESEARCH_MAX + 1:
            rows.append('<div class="cap">以上只能靠实验拿到</div>')
    return '<div class="ladder">' + "".join(rows) + "</div>"


def ledger(items: list[Evidence]) -> str:
    rows = []
    for x in items:
        src = (
            f'<a href="{e(x.url)}" target="_blank" rel="noopener">{e(x.source_title or x.url)}</a>'
            if x.url
            else "—"
        )
        claim = f'<span class="hl">{e(x.claim)}</span>' if x.stance == Stance.against else e(x.claim)
        rows.append(
            f'<tr class="{x.stance.value}"><td class="k"><span class="pill {x.stance.value}">{x.stance.value}</span></td>'
            f'<td class="k">L{int(x.level)} {LEVEL_NAMES[x.level]}</td>'
            f"<td>{claim}</td><td>{src}</td></tr>"
        )
    head = "<tr><th>立场</th><th>等级</th><th>说明了什么</th><th>来源</th></tr>"
    return f'<table class="ledger">{head}{"".join(rows)}</table>'


def observations(items: list[Observation]) -> str:
    rows = []
    for o in items:
        stance = "反对" if o.stance == Stance.against else "支持"
        lv = "—" if o.stance == Stance.against else f"L{int(o.level)} {LEVEL_NAMES[o.level]}"
        rows.append(
            f'<tr class="{stance}"><td class="k"><span class="pill {stance}">{e(o.label)}</span></td>'
            f'<td class="k">{lv}</td><td>{e(o.text)}</td></tr>'
        )
    head = "<tr><th>归类</th><th>等级</th><th>原话</th></tr>"
    return f'<table class="ledger">{head}{"".join(rows)}</table>'


def post(channel: str, title: str, body: str, cta: str, counts: str) -> str:
    t = f'<div class="t">{e(title)}</div>' if title else ""
    return (
        f'<div class="post"><div class="ch">{e(channel)}</div>{t}<div class="b">{e(body.strip()).replace(chr(10), "<br>")}</div>'
        f'<div class="cta">{e(cta)}</div><div class="meta" style="margin-top:.4rem">数据计入：{e(counts)}</div></div>'
    )
