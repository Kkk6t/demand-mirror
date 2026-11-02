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
from dby.models import LEVEL_NAMES, Criterion, Level, Project, Stance
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

LEVEL_LABEL = {Level.L3: "承诺", Level.L4: "付费"}
LABEL_LEVEL = {v: k for k, v in LEVEL_LABEL.items()}

# ---------------- 状态 ----------------

ss = st.session_state
if "settings" not in ss:
    ss.settings = Settings.from_env()
if "project" not in ss:
    ss.project = Project(idea=DEMO_IDEA, demo=True) if ss.settings.demo else Project()
if "offset" not in ss:
    ss.offset = 0  # 演示模式下"假装过了几天"

p: Project = ss.project
settings: Settings = ss.settings
llm, searcher = build_demo() if p.demo else build(settings)


def now() -> datetime:
    return datetime.now() + timedelta(days=ss.offset if p.demo else 0)


def run(fn, *args, spinner: str = "处理中…"):
    """执行一步操作：统一处理错误，成功后自动存档。"""
    try:
        with st.spinner(spinner):
            out = fn(*args)
        storage.save(p)
        return out, True
    except RuleError as err:
        st.warning(str(err))
    except (LLMError, SearchError) as err:
        st.error(f"{err}\n\n检查侧边栏里的 API Key 和模型名，或者稍后重试。")
    return None, False


def new_project(demo: bool) -> None:
    ss.project = Project(idea=DEMO_IDEA, demo=True) if demo else Project()
    ss.offset = 0
    ss.pop("comments", None)


# ---------------- 侧边栏 ----------------

verdict = evaluate(p, now())

with st.sidebar:
    st.markdown('<div class="serif" style="font-size:1.15rem;font-weight:600">检验结果</div>', unsafe_allow_html=True)
    st.markdown(ui.stamp(verdict.status), unsafe_allow_html=True)
    st.markdown('<div class="meta">目前拿到的最高证据</div>', unsafe_allow_html=True)
    st.markdown(ui.ladder(verdict.highest_level), unsafe_allow_html=True)
    if p.guard_hits:
        st.markdown(
            f'<div class="guard">已拦截 <b>{len(p.guard_hits)}</b> 处模型的乐观表述：'
            + "、".join(sorted({h.phrase for h in p.guard_hits})[:6])
            + "</div>",
            unsafe_allow_html=True,
        )

    st.divider()
    st.markdown('<div class="serif" style="font-weight:600">档案</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    if c1.button("新建点子", use_container_width=True, disabled=settings.demo):
        new_project(demo=False)
        st.rerun()
    if c2.button("看示例", use_container_width=True):
        new_project(demo=True)
        st.rerun()

    saved = [x for x in storage.list_projects() if x.id != p.id and x.idea.strip()]
    if saved:
        pick = st.selectbox("打开存档", saved, format_func=lambda x: f"{x.title}（{x.created_at:%m-%d}）", index=None, placeholder="选择一个点子")
        if pick is not None and st.button("打开", use_container_width=True):
            ss.project = pick
            st.rerun()

    st.download_button(
        "导出存档（JSON）",
        p.model_dump_json(indent=2),
        file_name=f"{p.id}.json",
        mime="application/json",
        use_container_width=True,
    )
    up = st.file_uploader("导入存档", type="json", label_visibility="collapsed")
    if up is not None and st.button("载入这个存档", use_container_width=True):
        try:
            ss.project = Project.model_validate_json(up.getvalue())
            st.rerun()
        except Exception as err:  # noqa: BLE001
            st.warning(f"这个文件不是先别做的存档：{err}")

    st.divider()
    with st.expander("模型和搜索设置", expanded=False):
        preset = st.selectbox("模型服务", list(PRESETS) + ["自定义"], index=0)
        base_default, model_default = PRESETS.get(preset, (settings.llm_base_url, settings.llm_model))
        base = st.text_input("接口地址", value=base_default if preset != "自定义" else settings.llm_base_url)
        model = st.text_input("模型名", value=model_default if preset != "自定义" else settings.llm_model)
        key = st.text_input("API Key", value=settings.llm_api_key, type="password", help="留空就是演示模式")
        provider = st.radio("联网搜索", ["博查", "Tavily", "不接搜索"], horizontal=True,
                            index=["博查", "Tavily", "不接搜索"].index(settings.search_provider) if settings.search_provider in ("博查", "Tavily", "不接搜索") else 0)
        skey = st.text_input("搜索 API Key", value=settings.search_api_key, type="password", disabled=provider == "不接搜索")
        if st.button("保存设置", use_container_width=True):
            ss.settings = Settings(base, key, model, provider, skey)
            if p.demo and not ss.settings.demo:
                new_project(demo=False)
            st.rerun()
        st.caption("Key 只保存在这次会话里。也可以写在项目根目录的 .env 文件。")

    if p.demo and p.experiment and p.experiment.started_at:
        st.divider()
        ss.offset = st.slider("演示：假装实验已经过了几天", 0, 14, ss.offset)


# ---------------- 主体 ----------------

if p.demo:
    mode = "当前是<b>演示模式</b>：用「先别做」验证「先别做」自己。在侧边栏填 API Key 就能分析你的点子。"
else:
    mode = f"当前模型 <b>{ui.e(llm.name)}</b>，搜索 <b>{ui.e(searcher.name)}</b>"
st.markdown(ui.masthead(mode), unsafe_allow_html=True)

# 1 点子 -----------------------------------------------------------------
st.markdown(ui.step(1, "说出你的点子", "已追问" if p.questions else ""), unsafe_allow_html=True)
st.markdown(ui.lede("一两句话就够：做什么、给谁用。"), unsafe_allow_html=True)
idea = st.text_area(
    "点子",
    value=p.idea,
    height=100,
    label_visibility="collapsed",
    placeholder="例如：做一个帮大学生把课堂录音整理成复习提纲的小程序",
    disabled=p.demo or p.lock.locked,
)
if not p.demo:
    p.idea = idea
if st.button("开始追问", type="primary" if not p.questions else "secondary", disabled=p.lock.locked):
    _, ok = run(pipeline.ask_questions, p, llm, spinner="正在想该问你什么…")
    if ok:
        if p.demo:
            p.answers = {q.id: a for q, a in zip(p.questions, DEMO_ANSWERS)}
        st.rerun()

# 2 追问 -----------------------------------------------------------------
if p.questions:
    st.markdown(ui.step(2, "回答三个追问", "已起草标准" if p.criteria else ""), unsafe_allow_html=True)
    st.markdown(ui.lede("回答越具体，后面的标准和实验越有用。不知道就写不知道。"), unsafe_allow_html=True)
    for q in p.questions:
        ans = st.text_area(q.question, value=p.answers.get(q.id, ""), help=q.why, key=f"ans_{q.id}",
                           disabled=p.demo or p.lock.locked, height=80)
        if not p.demo:
            p.answers[q.id] = ans
    if st.button("起草假设和淘汰标准", type="primary" if not p.criteria else "secondary", disabled=p.lock.locked):
        _, ok = run(pipeline.draft_criteria, p, llm, spinner="正在找最危险的假设…")
        if ok:
            ss.crit_v = ss.get("crit_v", 0) + 1
            st.rerun()
else:
    st.markdown(ui.step(2, "回答三个追问", todo=True), unsafe_allow_html=True)


# 3 淘汰标准 -------------------------------------------------------------
def criteria_editor(key: str, criteria: list[Criterion]) -> list[Criterion] | None:
    df = pd.DataFrame(
        [
            {"id": c.id, "指标": c.metric, "等级": LEVEL_LABEL.get(c.level, "承诺"), "门槛": c.threshold, "天数": c.days, "怎么计数": c.note}
            for c in criteria
        ],
        columns=["id", "指标", "等级", "门槛", "天数", "怎么计数"],
    )
    edited = st.data_editor(
        df,
        key=key,
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True,
        column_config={
            "id": None,
            "指标": st.column_config.TextColumn(required=True, width="medium"),
            "等级": st.column_config.SelectboxColumn(options=["承诺", "付费"], required=True, width="small"),
            "门槛": st.column_config.NumberColumn(min_value=1, step=1, required=True, width="small"),
            "天数": st.column_config.NumberColumn(min_value=1, max_value=60, step=1, required=True, width="small"),
            "怎么计数": st.column_config.TextColumn(width="medium"),
        },
    )
    out = []
    for row in edited.to_dict("records"):
        if not str(row.get("指标") or "").strip():
            continue
        extra = {"id": row["id"]} if isinstance(row.get("id"), str) and row["id"] else {}
        try:
            out.append(
                Criterion(
                    **extra,
                    metric=str(row["指标"]).strip(),
                    level=LABEL_LEVEL.get(row.get("等级"), Level.L3),
                    threshold=int(row.get("门槛") or 1),
                    days=int(row.get("天数") or 7),
                    note=str(row.get("怎么计数") or ""),
                )
            )
        except (ValueError, TypeError):
            st.warning(f"「{row['指标']}」这一行的数字不对，门槛至少 1，天数 1~60。")
            return None
    return out


if p.criteria or p.assumptions:
    state = f"已锁定 · {p.lock.locked_at:%m-%d %H:%M}" if p.lock.locked else "未锁定"
    st.markdown(ui.step(3, "写下：出现什么结果你就放弃", state), unsafe_allow_html=True)

    if p.assumptions:
        with st.expander(f"这个点子最危险的 {len(p.assumptions)} 个假设", expanded=not p.lock.locked):
            for a in p.assumptions:
                st.markdown(f"**{a.kind}**　{a.statement}  \n<span class='meta'>说明它错了：{ui.e(a.how_to_falsify)}</span>", unsafe_allow_html=True)

    if not p.lock.locked:
        st.markdown(ui.lede("在看任何资料之前锁定它。只能用承诺（留联系方式、预约）和付费两种等级，点赞和「好想要」不算。"), unsafe_allow_html=True)
        base_key = f"critbase_{p.id}_{ss.get('crit_v', 0)}"
        if base_key not in ss:
            ss[base_key] = [c.model_copy() for c in p.criteria]
        new = criteria_editor(f"crit_edit_{base_key}", ss[base_key])
        if new is not None:
            p.criteria = new
        if st.button("锁定标准", type="primary"):
            _, ok = run(lock_criteria, p, now())
            if ok:
                st.rerun()
    else:
        for r in verdict.results:
            c = r.criterion
            dl = p.deadline(c)
            due = f"　截止 {dl:%m-%d}" if dl else ""
            st.markdown(
                f'<div class="rule-line">{ui.e(c.sentence())}<span class="lv">L{int(c.level)} {LEVEL_NAMES[c.level]}{due}</span></div>',
                unsafe_allow_html=True,
            )
        changes = len(p.lock.history)
        st.markdown(
            f'<div class="meta" style="margin-top:.4rem">指纹 {p.lock.fingerprint}'
            + (f"　·　改过 {changes} 次，其中放宽 {verdict.loosen_count} 次" if changes else "")
            + "</div>",
            unsafe_allow_html=True,
        )
        with st.expander("修改标准（理由会写进报告）"):
            changed = criteria_editor(f"crit_change_{p.lock.fingerprint}", p.criteria)
            reason = st.text_input("为什么要改", placeholder="例如：发现目标人群主要在周末活跃，期限要覆盖两个周末")
            if st.button("保存修改") and changed is not None:
                _, ok = run(change_criteria, p, changed, reason, now())
                if ok:
                    st.rerun()
else:
    st.markdown(ui.step(3, "写下：出现什么结果你就放弃", todo=True), unsafe_allow_html=True)

# 4 案头调研 -------------------------------------------------------------
if p.lock.locked:
    st.markdown(ui.step(4, "先找反对证据", f"{len(p.evidence)} 条证据" if p.research_done else ""), unsafe_allow_html=True)
    st.markdown(ui.lede("至少一半的搜索词专门用来推翻你的点子。网上的资料最高只能到 L2，证明不了有人会为你付钱。"), unsafe_allow_html=True)
    if searcher.name == "未接入搜索":
        st.info("还没接搜索，台账会是空的。在侧边栏填博查或 Tavily 的 Key。")
    if st.button("开始找证据", type="primary" if not p.research_done else "secondary"):
        notes, ok = run(pipeline.run_research, p, llm, searcher, spinner="正在搜索并整理证据…")
        if ok:
            ss.research_notes = notes
            st.rerun()
    for n in ss.get("research_notes", []):
        st.caption(n)
    if p.research_done and p.evidence:
        counts = {s: sum(1 for x in p.evidence if x.stance == s) for s in Stance}
        st.markdown(
            f'<div class="meta">反对 {counts[Stance.against]} 条，支持 {counts[Stance.support]} 条，中性 {counts[Stance.neutral]} 条。反对证据排在前面。</div>',
            unsafe_allow_html=True,
        )
        st.markdown(ui.ledger(p.evidence), unsafe_allow_html=True)
        with st.expander(f"用了 {len(p.queries)} 个搜索词"):
            for q in p.queries:
                st.markdown(f"- `{q.kind}` {q.query}")
else:
    st.markdown(ui.step(4, "先找反对证据", todo=True), unsafe_allow_html=True)

# 5 实验 -----------------------------------------------------------------
if p.research_done:
    ex = p.experiment
    state = f"开始于 {ex.started_at:%m-%d}" if ex and ex.started_at else ""
    st.markdown(ui.step(5, "跑一个 7 天的验证实验", state), unsafe_allow_html=True)
    st.markdown(ui.lede("宣传本身就是实验：每条帖子都带一个能数出来的行动，数字直接记到你锁定的标准上。"), unsafe_allow_html=True)
    if st.button("设计实验", type="primary" if not ex else "secondary"):
        _, ok = run(pipeline.plan_experiment, p, llm, spinner="正在设计实验和宣传文案…")
        if ok:
            st.rerun()
    if ex:
        tab_days, tab_posts, tab_q = st.tabs(["每天做什么", f"可计数的宣传（{len(ex.posts)}）", "访谈问题"])
        with tab_days:
            for d in ex.days:
                c = p.criterion(d.criterion_id) if d.criterion_id else None
                tail = f"　<span class='meta'>→ {ui.e(c.metric)}</span>" if c else ""
                st.markdown(f"**第 {d.day} 天**　{ui.e(d.action)}{tail}", unsafe_allow_html=True)
        with tab_posts:
            for post in ex.posts:
                c = p.criterion(post.criterion_id)
                st.markdown(ui.post(post.channel, post.title, post.body, post.cta, c.metric if c else "—"), unsafe_allow_html=True)
                with st.expander("复制这条"):
                    st.code("\n\n".join(x for x in [post.title, post.body.strip(), post.cta] if x), language=None, wrap_lines=True)
        with tab_q:
            st.caption("只问对方过去真实做过的事。「你会不会用」得到的答案没有意义。")
            for i, q in enumerate(ex.interview_questions, 1):
                st.markdown(f"{i}. {q}")
        if not ex.started_at:
            if st.button("今天开始实验", type="primary"):
                _, ok = run(pipeline.start_experiment, p, now())
                if ok:
                    st.rerun()
else:
    st.markdown(ui.step(5, "跑一个 7 天的验证实验", todo=True), unsafe_allow_html=True)

# 6 回填 -----------------------------------------------------------------
if p.experiment and p.experiment.started_at:
    day = (now() - p.experiment.started_at).days + 1
    st.markdown(ui.step(6, "回填真实结果", f"第 {day} 天"), unsafe_allow_html=True)
    st.markdown(ui.lede("把评论、私信、聊天记录粘贴进来，按行动归类。也可以直接填数字，填了的以你填的为准。"), unsafe_allow_html=True)

    if p.demo and "comments" not in ss:
        ss.comments = ""
    if p.demo and st.button("填入示例评论（虚构）"):
        ss.comments = DEMO_RAW_COMMENTS
    raw = st.text_area("评论和私信", key="comments", height=140, placeholder="一行一条，或者整段粘贴都行")
    if st.button("归类这些反馈", type="primary"):
        added, ok = run(pipeline.classify_observations, p, llm, raw, spinner="正在按行动归类…")
        if ok:
            st.toast(f"归类了 {len(added)} 条反馈")
            st.rerun()
    if p.observations:
        st.markdown(ui.observations(p.observations), unsafe_allow_html=True)
        if st.button("清空已归类的反馈"):
            p.observations = []
            storage.save(p)
            st.rerun()

    with st.expander("直接填数字"):
        cols = st.columns(len(p.criteria))
        for col, c in zip(cols, p.criteria):
            val = col.number_input(c.metric, min_value=0, step=1, value=p.manual_counts.get(c.id), key=f"num_{c.id}", placeholder="不填就用归类结果")
            if val is None:
                p.manual_counts.pop(c.id, None)
            else:
                p.manual_counts[c.id] = int(val)
else:
    st.markdown(ui.step(6, "回填真实结果", todo=True), unsafe_allow_html=True)

# 判定 -------------------------------------------------------------------
verdict = evaluate(p, now())
if p.lock.locked:
    st.markdown('<div class="step"><span class="n">=</span><h3>判定</h3><span class="s">由规则算出，不由模型决定</span></div>', unsafe_allow_html=True)
    left, right = st.columns([2, 3], vertical_alignment="center")
    with left:
        st.markdown(ui.stamp(verdict.status, big=True, anim=True), unsafe_allow_html=True)
    with right:
        for r in verdict.reasons:
            st.markdown(f"- {r}")
    if p.experiment and p.experiment.started_at:
        rows = [
            {"标准": r.criterion.metric, "现在": r.count, "门槛": r.criterion.threshold,
             "状态": "达标" if r.met else ("到期未达标" if r.expired else "进行中"), "来源": r.source}
            for r in verdict.results
        ]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    st.download_button(
        "下载验证报告（Markdown）",
        to_markdown(p, now()),
        file_name=f"验证报告-{p.title}.md",
        mime="text/markdown",
        type="primary",
    )
