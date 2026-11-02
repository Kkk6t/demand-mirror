"""界面用的 HTML 片段和样式。视觉概念：一张「点子检验单」。"""

from __future__ import annotations

import html

from .models import DESK_RESEARCH_MAX, LEVEL_HINTS, LEVEL_NAMES, OBS_LABELS, Evidence, Level, Observation, Stance, Status

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
.lede { color: var(--muted); font-size: .95rem; margin: 0 0 .8rem; max-width: 70ch; line-height: 1.7; }
.lede b { color: var(--ink); font-weight: 500; }

/* 首屏 */
.hero { padding: 1.2rem 0 .4rem; }
.hero h1 { font-size: 3.6rem !important; font-weight: 900; line-height: 1.05; margin: 0; padding: 0; }
.hero .pitch { font-size: 1.25rem; color: var(--ink); margin: .9rem 0 .3rem; line-height: 1.6; max-width: 34em; }
.hero .sub { font-size: .95rem; color: var(--muted); margin: 0 0 1.2rem; line-height: 1.7; max-width: 40em; }
.hero-wrap { display: grid; grid-template-columns: 1fr auto; align-items: center; gap: 1rem; }
.hero-stamp .stamp { font-size: 1.9rem; }
.gets { display: grid; grid-template-columns: repeat(3, 1fr); gap: .8rem; margin: 1.6rem 0 .4rem; }
.gets div { border-top: 2px solid var(--ink); padding-top: .5rem; font-size: .9rem; color: var(--muted); line-height: 1.6; }
.gets b { display: block; color: var(--ink); font-size: 1rem; font-weight: 600; margin-bottom: .15rem; }

/* 体检结果卡 */
.card { background: var(--sheet); border: 1px solid var(--rule); border-radius: 6px; padding: 1.4rem 1.6rem 1.2rem; margin: .4rem 0 1rem; }
.card .idea { color: var(--muted); font-size: .95rem; line-height: 1.7; margin-bottom: .2rem; }
.card .top { display: grid; grid-template-columns: auto 1fr; gap: 1.2rem; align-items: center; margin: .2rem 0 .6rem; }
.card .verdict { font-size: 1.12rem; font-weight: 500; line-height: 1.7; }
.card h4 { font-family: "Noto Serif SC", "Noto Serif CJK SC", "Source Han Serif SC", "Songti SC", "STSong", "SimSun", serif !important;
           font-size: 1.15rem; font-weight: 700; margin: 1.3rem 0 .5rem; padding: 0; color: var(--ink); }
.card ul.worry { list-style: none; margin: 0; padding: 0; }
.card ul.worry li { padding: .45rem 0 .45rem 1.3rem; position: relative; border-bottom: 1px solid var(--rule-soft); line-height: 1.7; }
.card ul.worry li:before { content: ""; position: absolute; left: 0; top: .95rem; width: .55rem; height: .55rem; background: var(--red); }
.card ul.worry a { font-size: .8rem; color: var(--muted); margin-left: .4rem; }
.card .line { font-family: "Noto Serif SC", "Noto Serif CJK SC", "Source Han Serif SC", "Songti SC", "STSong", "SimSun", serif; font-size: 1.05rem; padding: .25rem 0; }
.card .post { margin: .2rem 0 0; }
@media (max-width: 640px) {
  .hero h1 { font-size: 2.6rem !important; }
  .hero-wrap, .card .top { grid-template-columns: 1fr; }
  .gets { grid-template-columns: 1fr; }
}

/* 使用说明 */
.howto { background: var(--sheet); border: 1px solid var(--rule); border-radius: 4px; padding: .9rem 1.1rem; margin: 0 0 1rem; font-size: .93rem; line-height: 1.8; }
.howto ol { margin: .3rem 0 0 1.2rem; padding: 0; }
.howto li { margin: 0; }
.notice { border-left: 3px solid var(--ink); background: #EEF2F7; padding: .7rem .9rem; margin: .4rem 0 .8rem; font-size: .92rem; line-height: 1.7; }
.notice a { color: var(--ink); }
.preview { font-family: "Noto Serif SC", "Noto Serif CJK SC", "Source Han Serif SC", "Songti SC", "STSong", "SimSun", serif; font-size: 1rem; margin: .1rem 0 .3rem; }
textarea:disabled, input:disabled { color: var(--ink) !important; -webkit-text-fill-color: var(--ink) !important; opacity: 1 !important; }
.locked-note { font-size: .82rem; color: var(--muted); margin: -.4rem 0 .6rem; }

/* 印章：整个界面唯一大胆的元素 */
.stamp { display: inline-block; font-family: "Noto Serif SC", "Noto Serif CJK SC", "Source Han Serif SC", "Songti SC", "STSong", "SimSun", serif; font-weight: 900;
         font-size: 1.55rem; padding: .45rem 1.1rem; border: 4px double currentColor;
         border-radius: 6px; transform: rotate(-7deg); letter-spacing: .12em; opacity: .92;
         mix-blend-mode: multiply; }
.stamp.big { font-size: 2.4rem; padding: .6rem 1.6rem; border-width: 6px; }
.stamp.unverified { color: var(--grey); }
.stamp.negative { color: var(--red); }
.stamp.paid { color: var(--green); }
.meaning { font-size: .86rem; color: var(--muted); margin: -.3rem 0 .2rem; }
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
.ledger td.k { white-space: nowrap; }
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
.stButton button[kind="primary"]:disabled { background: #C9D2DE; border-color: #C9D2DE; color: #fff; }
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
<p>动手写代码之前，先花一周搞清楚：到底有没有人要。</p>
<div class="mode">{mode}</div></div>"""


def step(n: int, title: str, state: str = "", todo: bool = False) -> str:
    cls = "step todo" if todo else "step"
    return f'<div class="{cls}"><span class="n">{n}</span><h3>{e(title)}</h3><span class="s">{e(state)}</span></div>'


def lede(text: str) -> str:
    return f'<p class="lede">{e(text)}</p>'


def stamp(status: Status, big: bool = False, anim: bool = False) -> str:
    cls = f"stamp {status.name}" + (" big" if big else "")
    wrap = "stamp-wrap anim" if anim else "stamp-wrap"
    return f'<div class="{wrap}"><span class="{cls}">{e(status.value)}</span></div>'


def ladder(highest: Level) -> str:
    rows = []
    for lv in sorted(Level, reverse=True):
        on = " on" if lv <= highest else ""
        rows.append(
            f'<div class="rung{on}"><span class="tag">{int(lv)}</span>'
            f"<span>{LEVEL_NAMES[lv]}<small>{LEVEL_HINTS[lv]}</small></span></div>"
        )
        if lv == DESK_RESEARCH_MAX + 1:
            rows.append('<div class="cap">上面两级只能靠你自己发帖测试拿到</div>')
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
            f'<td class="k">{LEVEL_NAMES[x.level]}</td>'
            f"<td>{claim}</td><td>{src}</td></tr>"
        )
    head = "<tr><th>态度</th><th>可信度</th><th>说明了什么</th><th>出处</th></tr>"
    return f'<table class="ledger">{head}{"".join(rows)}</table>'


def observations(items: list[Observation]) -> str:
    rows = []
    for o in items:
        stance = "反对" if o.stance == Stance.against else ("支持" if o.level >= Level.L3 else "中性")
        rows.append(
            f'<tr class="{stance}"><td class="k"><span class="pill {stance}">{e(OBS_LABELS.get(o.label, o.label))}</span></td>'
            f'<td>{e(o.text)}</td></tr>'
        )
    head = "<tr><th>AI 归类</th><th>原话</th></tr>"
    return f'<table class="ledger">{head}{"".join(rows)}</table>'


def post(channel: str, title: str, body: str, cta: str, counts: str) -> str:
    t = f'<div class="t">{e(title)}</div>' if title else ""
    return (
        f'<div class="post"><div class="ch">{e(channel)}</div>{t}<div class="b">{e(body.strip()).replace(chr(10), "<br>")}</div>'
        f'<div class="cta">{e(cta)}</div><div class="meta" style="margin-top:.4rem">有人照做了，就记到「{e(counts)}」</div></div>'
    )


def hero() -> str:
    return f"""<div class="hero"><div class="hero-wrap"><div>
<h1>先别做</h1>
<p class="pitch">写下你想做的产品。1 分钟后，你会知道网上有谁在反对你、你该在什么情况下放弃、明天该发什么帖子去测试。</p>
</div><div class="hero-stamp">{stamp(Status.negative)}</div></div>
<p class="sub">很多东西做出来没人用，是因为做之前没确认过有没有人要。问 AI 也没用，它很容易顺着你夸。这个工具反过来，专门找对你不利的证据。</p>
</div>"""


def gets() -> str:
    return """<div class="gets">
<div><b>反对你的证据</b>网上已有的免费替代品、类似产品的下场，每条都附原文链接</div>
<div><b>你的放弃线</b>比如「7 天内私信不到 5 个就放弃」，在看资料之前就定死</div>
<div><b>明天就能发的帖子</b>每条都让读者做一件能数出来的事，一周后用数字说话</div>
</div>"""


def result_card(p, v, meaning: str) -> str:
    worries = [x for x in p.evidence if x.stance == Stance.against][:3]
    if worries:
        items = "".join(
            f'<li>{e(x.claim)}<a href="{e(x.url)}" target="_blank" rel="noopener">出处</a></li>' for x in worries
        )
        worry_title = "最该担心的事（网上找到的）"
    else:
        items = "".join(f"<li>{e(a.statement)}</li>" for a in p.assumptions[:3])
        worry_title = "最该担心的事（AI 推测的，还没找到网上证据）"
    lines = "".join(f'<div class="line">{e(c.sentence())}。</div>' for c in p.criteria)
    first = p.experiment.posts[0] if p.experiment and p.experiment.posts else None
    post_html = ""
    if first:
        c = p.criterion(first.criterion_id)
        post_html = "<h4>明天就发这条</h4>" + post(first.channel, first.title, first.body, first.cta, c.metric if c else "—")
    return f"""<div class="card">
<div class="idea">「{e(p.idea.strip())}」</div>
<div class="top">{stamp(v.status, big=True, anim=True)}<div class="verdict">{e(meaning)}</div></div>
<h4>{worry_title}</h4><ul class="worry">{items}</ul>
<h4>你的放弃线</h4>{lines}
{post_html}
</div>"""
