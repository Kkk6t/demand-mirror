"""先别做 · Streamlit 界面。运行：streamlit run app.py"""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

from dby import pipeline, storage, ui
from dby.config import PRESETS, Settings, build, build_demo
from dby.demo import DEMO_ANSWERS, DEMO_IDEA, DEMO_RAW_COMMENTS
from dby.llm import LLMError
from dby.models import LEVEL_NAMES, STATUS_MEANING, Criterion, Level, Project, Stance
from dby.report import to_markdown
from dby.rules import RuleError, change_criteria, evaluate, lock_criteria
from dby.search import SearchError

load_dotenv()
st.set_page_config(page_title="先别做", page_icon="🔖", layout="centered")
st.html(ui.CSS)
# 页面本身是中文，但 Streamlit 默认把 <html> 标成英文，浏览器会自动"翻译"，
# 翻译插件改写页面会让 Streamlit 白屏。这里把语言改成中文并禁止翻译。
components.html(
    """<script>
    const d = window.parent.document;
    d.documentElement.lang = "zh-CN";
    d.documentElement.setAttribute("translate", "no");
    d.documentElement.classList.add("notranslate");
    if (!d.querySelector('meta[name="google"]')) {
      const m = d.createElement("meta"); m.name = "google"; m.content = "notranslate"; d.head.appendChild(m);
    }
    </script>""",
    height=0,
)

KINDS = {"留了联系方式的人": Level.L3, "付了钱的人": Level.L4}
KIND_OF = {v: k for k, v in KINDS.items()}

# ---------------- 状态 ----------------

ss = st.session_state
if "settings" not in ss:
    ss.settings = Settings.from_env()
if "project" not in ss:
    ss.project = Project(idea=DEMO_IDEA, demo=True) if ss.settings.demo else Project()
if "offset" not in ss:
    ss.offset = 0  # 示例里"假装过了几天"

p: Project = ss.project
settings: Settings = ss.settings
llm, searcher = build_demo() if p.demo else build(settings)
needs_key = not p.demo and settings.demo


def now() -> datetime:
    return datetime.now() + timedelta(days=ss.offset if p.demo else 0)


def run(fn, *args, spinner: str = "处理中…"):
    """执行一步操作：统一处理错误，成功后自动存档。"""
    if needs_key:
        st.warning("还没连接 AI。先在页面最上面填好 API Key。")
        return None, False
    try:
        with st.spinner(spinner):
            out = fn(*args)
        storage.save(p)
        return out, True
    except RuleError as err:
        st.warning(str(err))
    except (LLMError, SearchError) as err:
        st.error(f"{err}\n\n检查 API Key 和模型名是否填对、账户里有没有余额，或者稍后再试。")
    return None, False


def new_project(demo: bool) -> None:
    ss.project = Project(idea=DEMO_IDEA, demo=True) if demo else Project()
    ss.offset = 0
    for k in [k for k in ss.keys() if str(k).startswith(("chg_", "comments", "research_notes"))]:
        del ss[k]


def locked_note(text: str) -> None:
    st.markdown(f'<div class="locked-note">{ui.e(text)}</div>', unsafe_allow_html=True)


# ---------------- 侧边栏 ----------------

verdict = evaluate(p, now())

with st.sidebar:
    st.markdown('<div class="serif" style="font-size:1.15rem;font-weight:600">现在的结论</div>', unsafe_allow_html=True)
    st.markdown(ui.stamp(verdict.status), unsafe_allow_html=True)
    st.markdown(f'<div class="meaning">{ui.e(STATUS_MEANING[verdict.status])}</div>', unsafe_allow_html=True)

    st.markdown('<div class="serif" style="font-weight:600;margin-top:1.2rem">手里最硬的证据</div>', unsafe_allow_html=True)
    st.markdown('<div class="meta">从下往上越来越可信，深色是已经拿到的</div>', unsafe_allow_html=True)
    st.markdown(ui.ladder(verdict.highest_level), unsafe_allow_html=True)
    if p.guard_hits:
        st.markdown(
            f'<div class="guard">AI 的回答里有 <b>{len(p.guard_hits)}</b> 处没有证据的空话被拦下：'
            + "、".join(sorted({h.phrase for h in p.guard_hits})[:6])
            + "</div>",
            unsafe_allow_html=True,
        )

    st.divider()
    st.markdown('<div class="serif" style="font-weight:600">我的点子</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    if c1.button("写新点子", use_container_width=True):
        new_project(demo=False)
        st.rerun()
    if c2.button("看示例", use_container_width=True):
        new_project(demo=True)
        st.rerun()

    saved = [x for x in storage.list_projects() if x.id != p.id and x.idea.strip() and not x.demo]
    if saved:
        pick = st.selectbox("之前写过的", saved, format_func=lambda x: f"{x.title}（{x.created_at:%m-%d}）", index=None, placeholder="选一个继续")
        if pick is not None and st.button("打开", use_container_width=True):
            ss.project = pick
            st.rerun()

    with st.expander("备份 / 恢复"):
        st.download_button("下载备份文件", p.model_dump_json(indent=2), file_name=f"先别做-{p.id}.json",
                           mime="application/json", use_container_width=True)
        up = st.file_uploader("上传备份文件恢复", type="json")
        if up is not None and st.button("恢复", use_container_width=True):
            try:
                ss.project = Project.model_validate_json(up.getvalue())
                st.rerun()
            except Exception as err:  # noqa: BLE001
                st.warning(f"这个文件不是先别做的备份：{err}")

    with st.expander("AI 和搜索设置"):
        preset = st.selectbox("用哪家的 AI", list(PRESETS) + ["自定义"], index=0)
        base_default, model_default = PRESETS.get(preset, (settings.llm_base_url, settings.llm_model))
        base = st.text_input("接口地址", value=base_default if preset != "自定义" else settings.llm_base_url)
        model = st.text_input("模型名", value=model_default if preset != "自定义" else settings.llm_model)
        key = st.text_input("API Key", value=settings.llm_api_key, type="password")
        choices = ["博查", "Tavily", "不接搜索"]
        provider = st.radio("联网搜索用哪家", choices, horizontal=True,
                            index=choices.index(settings.search_provider) if settings.search_provider in choices else 0)
        skey = st.text_input("搜索的 API Key", value=settings.search_api_key, type="password", disabled=provider == "不接搜索")
        if st.button("保存", use_container_width=True):
            ss.settings = Settings(base, key, model, provider, skey)
            st.rerun()
        st.caption("Key 只在这次打开的页面里有效，关掉要重填。想一直生效，写进项目文件夹里的 .env 文件。")

    if p.demo and p.experiment and p.experiment.started_at:
        st.divider()
        ss.offset = st.slider("示例专用：假装已经过了几天", 0, 14, ss.offset, help="拖到 7 天以后，看看到期没达标会怎样")


# ---------------- 页面顶部 ----------------

if needs_key or p.demo:
    mode = ""
else:
    mode = f"已连接 <b>{ui.e(llm.name)}</b>　·　联网搜索：<b>{ui.e(searcher.name)}</b>"
st.markdown(ui.masthead(mode), unsafe_allow_html=True)

with st.expander("第一次用？先看这里", expanded=not p.questions):
    st.markdown(
        """<div class="howto">很多东西做出来没人用，是因为做之前没确认过有没有人要。问 AI 也没用，它很容易顺着你夸。
这个工具反过来：<b>不判断你的点子好不好，只帮你找到真实的证据</b>，包括对你不利的。<br>
跟着下面 6 步走，每步只做一件事：
<ol>
<li>写下你想做什么</li>
<li>回答 AI 的 3 个问题，把想法说具体</li>
<li>定好「出现什么结果我就放弃」</li>
<li>让 AI 上网找反对意见</li>
<li>照着 AI 写好的帖子发出去，测试一周</li>
<li>把收到的真实反应填回来，得出结论</li>
</ol></div>""",
        unsafe_allow_html=True,
    )

if p.demo:
    st.markdown(
        '<div class="notice">你正在看<b>示例</b>：作者用这个工具检验它自己。示例内容是固定的，<b>不能修改</b>，'
        "一路点按钮就能看完整个流程。想分析你自己的点子，点下面的按钮。</div>",
        unsafe_allow_html=True,
    )
    if st.button("写我自己的点子", type="primary"):
        new_project(demo=False)
        st.rerun()
elif needs_key:
    st.markdown(
        '<div class="notice"><b>先连接 AI</b>。这个工具要用 AI 来提问、搜资料、写帖子，需要一个 API Key。'
        '最简单的是 DeepSeek：到 <a href="https://platform.deepseek.com/api_keys" target="_blank">platform.deepseek.com</a> '
        "注册，充一点余额，点「创建 API Key」，把以 sk- 开头的那串字符复制到下面。</div>",
        unsafe_allow_html=True,
    )
    k1, k2 = st.columns([4, 1], vertical_alignment="bottom")
    new_key = k1.text_input("DeepSeek API Key", type="password", placeholder="sk-…")
    with st.expander("也想让它联网搜资料？（可选，不填也能用）"):
        st.markdown(
            '国内推荐博查：到 <a href="https://open.bochaai.com" target="_blank">open.bochaai.com</a> 注册并创建 Key。'
            "不填的话，第 4 步「网上的反对意见」会是空的。",
            unsafe_allow_html=True,
        )
        new_skey = st.text_input("博查 API Key", type="password")
    if k2.button("连接", type="primary", use_container_width=True):
        if not new_key.strip():
            st.warning("先把 Key 粘贴进去。")
        else:
            base, model = PRESETS["DeepSeek"]
            ss.settings = Settings(base, new_key.strip(), model, "博查" if new_skey.strip() else "不接搜索", new_skey.strip())
            st.rerun()

# ---------------- 第 1 步 ----------------

st.markdown(ui.step(1, "你想做什么", "已完成" if p.questions else ""), unsafe_allow_html=True)
st.markdown(ui.lede("用一两句话说清楚：做一个什么东西，给谁用。不用写得很完整，后面 AI 会追问。"), unsafe_allow_html=True)
idea = st.text_area(
    "你的点子",
    value=p.idea,
    height=100,
    label_visibility="collapsed",
    placeholder="例如：做一个小程序，帮大学生把上课录音整理成复习提纲",
    disabled=p.demo or p.lock.locked,
)
if p.demo:
    locked_note("示例内容不能修改。")
elif p.lock.locked:
    locked_note("放弃条件已经定了，点子不能再改。想换个点子，点左边的「写新点子」。")
else:
    p.idea = idea
if st.button("下一步：让 AI 问我几个问题", type="primary" if not p.questions else "secondary", disabled=p.lock.locked):
    _, ok = run(pipeline.ask_questions, p, llm, spinner="AI 正在想该问你什么…")
    if ok:
        if p.demo:
            p.answers = {q.id: a for q, a in zip(p.questions, DEMO_ANSWERS)}
        st.rerun()

# ---------------- 第 2 步 ----------------

if p.questions:
    st.markdown(ui.step(2, "回答 3 个问题", "已完成" if p.criteria else ""), unsafe_allow_html=True)
    st.markdown(
        ui.lede("AI 针对你的点子提了 3 个问题。照实回答就行，不知道就写「不知道」。答得越具体，后面帮你写的帖子越像样。"),
        unsafe_allow_html=True,
    )
    for i, q in enumerate(p.questions, 1):
        ans = st.text_area(
            f"问题 {i}：{q.question}",
            value=p.answers.get(q.id, ""),
            help=f"为什么问这个：{q.why}" if q.why else None,
            key=f"ans_{q.id}",
            disabled=p.demo or p.lock.locked,
            height=80,
            placeholder="在这里写你的回答",
        )
        if not p.demo and not p.lock.locked:
            p.answers[q.id] = ans
    if st.button("下一步：帮我起草放弃条件", type="primary" if not p.criteria else "secondary", disabled=p.lock.locked):
        _, ok = run(pipeline.draft_criteria, p, llm, spinner="AI 正在找这个点子最可能出错的地方…")
        if ok:
            st.rerun()
else:
    st.markdown(ui.step(2, "回答 3 个问题", todo=True), unsafe_allow_html=True)


# ---------------- 第 3 步 ----------------


def criteria_form(prefix: str, items: list[Criterion], editable: bool) -> None:
    """把每条放弃条件写成一句话来填，直接修改 items。"""
    remove = None
    for i, c in enumerate(items):
        with st.container(border=True):
            st.markdown(f"**第 {i + 1} 条**")
            a, b = st.columns(2)
            kind = a.selectbox("数哪种人", list(KINDS), index=0 if c.level == Level.L3 else 1,
                               key=f"{prefix}_k_{c.id}", disabled=not editable,
                               help="只能数这两种人。点赞、评论「好想要」不算，因为不花任何成本。")
            days = b.number_input("给自己几天", min_value=1, max_value=60, value=c.days, step=1,
                                  key=f"{prefix}_d_{c.id}", disabled=not editable)
            metric = st.text_input("具体数什么", value=c.metric, key=f"{prefix}_m_{c.id}", disabled=not editable,
                                   placeholder="例如：私信我要内测资格的人数")
            a, b = st.columns(2)
            thr = a.number_input("至少要有几个", min_value=1, max_value=10000, value=c.threshold, step=1,
                                 key=f"{prefix}_t_{c.id}", disabled=not editable)
            note = b.text_input("怎么算一个（可选）", value=c.note, key=f"{prefix}_n_{c.id}", disabled=not editable,
                                placeholder="例如：评论区说想要不算")
            if editable:
                c.level, c.days, c.metric, c.threshold, c.note = KINDS[kind], int(days), metric.strip(), int(thr), note
            st.markdown(f'<div class="preview">意思是：{ui.e(c.sentence())}。</div>', unsafe_allow_html=True)
            if editable and len(items) > 1 and st.button("删掉这条", key=f"{prefix}_x_{c.id}"):
                remove = i
    if remove is not None:
        items.pop(remove)
        st.rerun()
    if editable and st.button("再加一条", key=f"{prefix}_add"):
        items.append(Criterion(metric="", level=Level.L3, threshold=3, days=7))
        st.rerun()


if p.criteria or p.assumptions:
    state = f"已定好 · {p.lock.locked_at:%m-%d %H:%M}" if p.lock.locked else "还没定"
    st.markdown(ui.step(3, "定好放弃条件", state), unsafe_allow_html=True)
    st.markdown(
        ui.lede("这一步最重要。在看任何资料之前，先写下「几天内，如果某个数字不到多少，我就放弃」。"
                "这样一周后你没法骗自己。AI 已经起草了几条，你可以直接改。"),
        unsafe_allow_html=True,
    )

    if p.assumptions:
        with st.expander(f"AI 觉得这个点子最可能出错的 {len(p.assumptions)} 个地方", expanded=not p.lock.locked):
            for a in p.assumptions:
                st.markdown(
                    f"**{ui.e(a.kind)}**：{ui.e(a.statement)}  \n"
                    f"<span class='meta'>如果出现这种情况，说明这一条错了：{ui.e(a.how_to_falsify)}</span>",
                    unsafe_allow_html=True,
                )

    if not p.lock.locked:
        criteria_form("c", p.criteria, editable=True)
        st.caption("至少要有一条「付了钱的人」。只看私信，最多说明有人感兴趣，说明不了有人会买。")
        if st.button("就按这个定下来", type="primary"):
            _, ok = run(lock_criteria, p, now())
            if ok:
                st.rerun()
    else:
        for r in verdict.results:
            dl = p.deadline(r.criterion)
            due = f"　{dl:%m月%d日}到期" if dl else ""
            st.markdown(
                f'<div class="rule-line">{ui.e(r.criterion.sentence())}<span class="lv">数的是{LEVEL_NAMES[r.criterion.level]}的人{due}</span></div>',
                unsafe_allow_html=True,
            )
        if p.lock.history:
            st.markdown(
                f'<div class="meta" style="margin-top:.4rem">定好之后改过 {len(p.lock.history)} 次，其中放宽 {verdict.loosen_count} 次，都会写进报告。</div>',
                unsafe_allow_html=True,
            )
        with st.expander("我想改条件（会留下记录）"):
            buf_key = f"chg_{p.id}"
            if buf_key not in ss:
                ss[buf_key] = [c.model_copy() for c in p.criteria]
            criteria_form("chg", ss[buf_key], editable=True)
            reason = st.text_input("为什么要改", placeholder="例如：发现这群人主要周末才刷手机，期限要包含两个周末")
            if st.button("保存修改"):
                _, ok = run(change_criteria, p, ss[buf_key], reason, now())
                if ok:
                    del ss[buf_key]
                    st.rerun()
else:
    st.markdown(ui.step(3, "定好放弃条件", todo=True), unsafe_allow_html=True)

# ---------------- 第 4 步 ----------------

if p.lock.locked:
    st.markdown(ui.step(4, "先看网上的反对意见", f"找到 {len(p.evidence)} 条" if p.research_done else ""), unsafe_allow_html=True)
    st.markdown(
        ui.lede("AI 会上网搜，而且一半以上专门搜反对意见：有没有免费的替代品、类似的东西是不是没人用。"
                "网上的资料只能说明市场情况，证明不了有人会给你付钱，所以这一步结束后结论最多是「还不知道」或「先别做」。"),
        unsafe_allow_html=True,
    )
    if searcher.name == "未接入搜索":
        st.info("还没接联网搜索，这一步会搜不到东西。可以在左边「AI 和搜索设置」里填博查的 Key，也可以直接跳到下一步。")
    if st.button("开始搜", type="primary" if not p.research_done else "secondary"):
        notes, ok = run(pipeline.run_research, p, llm, searcher, spinner="AI 正在搜索并整理资料，大概要一分钟…")
        if ok:
            ss.research_notes = notes
            st.rerun()
    for n in ss.get("research_notes", []):
        st.caption(n)
    if p.research_done and p.evidence:
        counts = {s: sum(1 for x in p.evidence if x.stance == s) for s in Stance}
        st.markdown(
            f'<div class="meta">反对 {counts[Stance.against]} 条、支持 {counts[Stance.support]} 条、中性 {counts[Stance.neutral]} 条。'
            "标黄的是反对意见，排在最前面。点出处可以看原文。</div>",
            unsafe_allow_html=True,
        )
        st.markdown(ui.ledger(p.evidence), unsafe_allow_html=True)
        with st.expander("AI 搜了哪些词"):
            for q in p.queries:
                st.markdown(f"- 找{q.kind}意见：{q.query}")
else:
    st.markdown(ui.step(4, "先看网上的反对意见", todo=True), unsafe_allow_html=True)

# ---------------- 第 5 步 ----------------

if p.research_done:
    ex = p.experiment
    state = f"{ex.started_at:%m月%d日}开始" if ex and ex.started_at else ""
    st.markdown(ui.step(5, "发帖测试一周", state), unsafe_allow_html=True)
    st.markdown(
        ui.lede("AI 帮你安排好 7 天里每天做什么，并写好要发的帖子。每条帖子都会让看的人做一件能数出来的事，"
                "比如私信你、付定金。一周后你手里就有真实的数字，不用再猜。"),
        unsafe_allow_html=True,
    )
    if st.button("帮我安排这一周", type="primary" if not ex else "secondary"):
        _, ok = run(pipeline.plan_experiment, p, llm, spinner="AI 正在写帖子和每天的安排…")
        if ok:
            st.rerun()
    if ex:
        tab_posts, tab_days, tab_q = st.tabs([f"要发的帖子（{len(ex.posts)} 条）", "每天做什么", "可以去问人的问题"])
        with tab_posts:
            st.caption("复制下来，发到对应的平台。帖子最后那句让读者做的事很关键，别删。")
            for post in ex.posts:
                c = p.criterion(post.criterion_id)
                st.markdown(ui.post(post.channel, post.title, post.body, post.cta, c.metric if c else "—"), unsafe_allow_html=True)
                with st.expander("复制这条"):
                    st.code("\n\n".join(x for x in [post.title, post.body.strip(), post.cta] if x), language=None, wrap_lines=True)
        with tab_days:
            for d in ex.days:
                c = p.criterion(d.criterion_id) if d.criterion_id else None
                tail = f"　<span class='meta'>（这天的结果记到「{ui.e(c.metric)}」）</span>" if c else ""
                st.markdown(f"**第 {d.day} 天**　{ui.e(d.action)}{tail}", unsafe_allow_html=True)
        with tab_q:
            st.caption("有人私信你的话，可以约他聊 15 分钟。只问他过去真实做过的事。问「你会不会用」，对方出于客气都会说会，没有意义。")
            for i, q in enumerate(ex.interview_questions, 1):
                st.markdown(f"{i}. {q}")
        if not ex.started_at:
            st.markdown('<div class="meta" style="margin-top:.6rem">帖子发出去之后点这个按钮，放弃条件的天数从现在开始算。</div>', unsafe_allow_html=True)
            if st.button("我发出去了，开始计时", type="primary"):
                _, ok = run(pipeline.start_experiment, p, now())
                if ok:
                    st.rerun()
else:
    st.markdown(ui.step(5, "发帖测试一周", todo=True), unsafe_allow_html=True)

# ---------------- 第 6 步 ----------------

if p.experiment and p.experiment.started_at:
    day = (now() - p.experiment.started_at).days + 1
    st.markdown(ui.step(6, "把真实反应填回来", f"今天是第 {day} 天"), unsafe_allow_html=True)
    st.markdown(
        ui.lede("这一周里随时可以回来填。把收到的评论、私信、聊天记录复制进来，AI 会把每一条分成"
                "「付了钱」「留了联系方式」「只是说说」「不需要」。不想用 AI 分，也可以直接填数字。"),
        unsafe_allow_html=True,
    )
    if "comments" not in ss:
        ss.comments = ""
    if p.demo and st.button("填入示例评论（虚构的）"):
        ss.comments = DEMO_RAW_COMMENTS
    raw = st.text_area("复制进来的评论和私信", key="comments", height=140,
                       placeholder="直接粘贴就行，一行一条最好。例如：\n蹲一个！\n已私信，想试试\n这个有点贵")
    if st.button("帮我分类", type="primary"):
        added, ok = run(pipeline.classify_observations, p, llm, raw, spinner="AI 正在分类…")
        if ok:
            st.toast(f"分好了 {len(added)} 条")
            st.rerun()
    if p.observations:
        st.markdown(ui.observations(p.observations), unsafe_allow_html=True)
        if st.button("清空分类结果"):
            p.observations = []
            storage.save(p)
            st.rerun()

    with st.expander("直接填数字（填了就以你填的为准）"):
        for c in p.criteria:
            val = st.number_input(f"到现在为止，「{c.metric}」有几个", min_value=0, step=1,
                                  value=p.manual_counts.get(c.id), key=f"num_{c.id}", placeholder="不填就用 AI 分类的结果")
            if val is None:
                p.manual_counts.pop(c.id, None)
            else:
                p.manual_counts[c.id] = int(val)
else:
    st.markdown(ui.step(6, "把真实反应填回来", todo=True), unsafe_allow_html=True)

# ---------------- 结论 ----------------

verdict = evaluate(p, now())
if p.lock.locked:
    st.markdown('<div class="step"><span class="n">=</span><h3>结论</h3><span class="s">按你定的条件算出来，不是 AI 说的</span></div>', unsafe_allow_html=True)
    left, right = st.columns([2, 3], vertical_alignment="center")
    with left:
        st.markdown(ui.stamp(verdict.status, big=True, anim=True), unsafe_allow_html=True)
    with right:
        st.markdown(f"**{STATUS_MEANING[verdict.status]}**")
        for r in verdict.reasons:
            st.markdown(f"- {r}")
    if p.experiment and p.experiment.started_at:
        rows = [
            {"条件": r.criterion.metric, "现在": r.count, "要求": r.criterion.threshold,
             "情况": "达到了" if r.met else ("到期没达到" if r.expired else "进行中"), "数字来自": r.source}
            for r in verdict.results
        ]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    st.download_button(
        "下载完整报告",
        to_markdown(p, now()),
        file_name=f"验证报告-{p.title}.md",
        mime="text/markdown",
        type="primary",
        help="Markdown 格式，可以用记事本或 Typora 打开，也可以直接放进 GitHub。",
    )
