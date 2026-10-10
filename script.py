#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🪞 志业镜 v2 · Streamlit Web 版
================================
不做「推荐专业」的工具，而做「引导发现」的镜子。

运行:
    streamlit run app.py

与 script.py (v2.0) 的区别（对应 docs/01 与 docs/03）：
  · 能力输入：六个 1—5 分滑块  →  叙事 + 行为证据提取（附证据强度）
  · 兴趣：输入条件             →  待验证的输出
  · 新增：避雷筛选（不讨厌优于最喜欢）
  · 新增：投入意愿 → 门控可转换分
  · 新增：动机内化诊断（自主 / 内摄 / 外部）
  · 新增：不可替代性指数 II + 三条生存策略
  · 输出：TOP3 榜单 + 百分比   →  待验证的假设 + 最小实验 + 施工图

数据说明：
  · 6 个专业为人工 + 访谈标注（curated）
  · 其余专业由旧 script.py 数据推导（provisional），报告中会明确降调
"""

import os
import sys

import streamlit as st

# 允许从本文件所在目录导入 zhiyejing 包
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from zhiyejing import (AB_LABELS, DISCLAIMERS, Profile, evaluate,
                       experiencer_or_builder, extract_signature,
                       generate_report, micro_commitment_curve)
from zhiyejing import majors_demand as MD
from zhiyejing.compat import CURATED
from zhiyejing.universe import load_universe_for_engine

# ============================================================
# 页面配置
# ============================================================
st.set_page_config(
    page_title="志业镜 · 从匹配到建构",
    page_icon="🪞",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# 载入专业库（数据与代码分离）
# ============================================================
# 加载逻辑统一收在 zhiyejing.universe，避免「代码换了、某处还指着老文件」。
# 用 load_universe_for_engine：它顺手把补丁注册进引擎，
# 否则 known_majors() 只会返回 6 个人工标注专业而且不报错。
# ============================================================
@st.cache_data(show_spinner=False)
def _load():
    return load_universe_for_engine()


MAJORS_ALL, LOAD_MSG = _load()
PATCHES = MD.PATCHES


# ============================================================
# 侧边栏
# ============================================================
with st.sidebar:
    st.markdown("## 🪞 志业镜")
    st.caption("从「匹配」走向「建构」的志业陪跑智能体")
    st.markdown("---")
    st.markdown("### 📌 我们不会做的事")
    for d in DISCLAIMERS:
        st.markdown(f"- {d}")
    st.markdown("---")
    st.markdown("### 🗂 专业库状态")
    st.caption(LOAD_MSG)
    st.markdown(f"- **人工 + 访谈标注**：{len(CURATED)} 个（完整档案）")
    st.markdown(f"- **由旧数据推导**：{len(PATCHES)} 个（仅骨架，报告中会标注未核实）")
    st.caption("推导规则完全公开，见 `zhiyejing/compat.py`。")
    st.markdown("---")
    st.markdown("### ⚙️ 高级设置")
    use_llm = st.checkbox("启用 DeepSeek 润色报告", value=False)
    api_key = ""
    if use_llm:
        api_key = st.text_input("DeepSeek API Key", type="password",
                                help="在 platform.deepseek.com 获取，仅用于本次会话")
    st.markdown("---")
    st.markdown("### 🔬 分析范围")
    allow_prov = st.checkbox(
        "也分析「未核实」专业", value=False,
        help="默认只在 6 个人工+访谈标注的专业里排序。"
             "打开后会纳入其余 88 个由旧数据推导的专业，"
             "它们全部会带「未核实」标记——因为把估算值和实证值放在同一个"
             "排名里，会让估算压过实证。",
    )
    if allow_prov:
        st.warning("已纳入推导专业。这些专业的需求、代价、不可替代性都是估算，"
                   "请把结论当成「一个方向」而不是「一个结论」。")
    st.markdown("---")
    st.caption("v3.0 · 五分数引擎 · 避雷筛选 · 不可替代性指数")


# ============================================================
# 主页面
# ============================================================
st.markdown("# 🪞 志业镜")
st.markdown("#### 不推荐专业，只帮你把「我该选什么」翻译成三个能回答的问题")
st.markdown(
    "> **我愿意成为谁（志） · 我能付出什么代价（力） · 这个时代还剩多少空间（时）**"
)
st.markdown("---")

with st.expander("📖 先读这一段：为什么我们不改用「给自己打分」（点开）", expanded=False):
    st.markdown(
        """
我们访谈了 12 个人（2 位师长、7 位学长、2 位同龄同学），最反直觉的一条发现是：

> **兴趣不是起点，而是结果。** AI 方向学长的原话是：
> 「意义感是投入的结果，不是原因。**热爱是情绪，情绪会变；习惯和意义感是结构，结构才撑得住。**」

所以这个工具**不问「你喜欢什么」，也不让你给自己打分**。
自评 5 分是一个宣言，不是证据。我们只做三件事：

1. 从你讲的**具体经历**里提取行为线索，并如实标注每条线索的**证据强度**；
2. 让你先回答**「你确定不能接受什么」**——因为选专业的核心工作是排雷，不是找最优；
3. 把结果组织成**待验证的假设 + 最小实验**，而不是一个排名。

**低证据 ≠ 低能力。** 如果你在某项上「只有自我形容、没有例子」，
报告会把它标成「待验证」——意思是「这条还没被验证过」，不是「你不行」。
        """
    )

# ------------------------------------------------------------
# 第零步：避雷（放在最前面，因为它最容易回答）
# ------------------------------------------------------------
st.markdown("### 第零步 · 你确定不能接受什么？")
st.caption("这一步比「你喜欢什么」更容易回答，也更可靠——"
           "因为「做得好才喜欢」和「因为喜欢才做得好」这对因果根本分辨不出来。")
avoid = st.multiselect(
    "选出你确定不想接受的（可多选，也可以一个都不选）",
    MD.AVOID_TAGS, default=[], placeholder="例如：长时间无反馈、大量记忆……",
)

st.markdown("---")

# ------------------------------------------------------------
# 第一步：叙事
# ------------------------------------------------------------
st.markdown("### 第一步 · 讲几件你做过的事")
st.caption("不要评价自己，只讲发生了什么。越具体越好——尤其是你手上的动作和最后的结果。")

with st.expander("八个引导性设问（不用每问都答，挑能答的答）", expanded=True):
    from zhiyejing.skillsig import NARRATIVE_PROMPTS
    for q in NARRATIVE_PROMPTS:
        st.markdown(f"- {q}")

narrative = st.text_area(
    "**你的经历**", height=220,
    placeholder="例如：\n"
                "高二那年班级要办毕业晚会，没人愿意接手，我就自己揽下来了。"
                "我先拉了一个群，把二十几个人的分工列成一张表……\n"
                "有一次朋友和父母吵得很厉害，半夜给我打了两个小时电话，"
                "我没有给建议，就是听她讲，中间问她「那你当时是怎么想的」……",
)
additional = st.text_input(
    "**还有什么想补充的关键词？**（你还会做什么，用逗号分隔即可）",
    placeholder="例如：组织过活动、做过调解、写过公众号",
)

st.markdown("---")

# ------------------------------------------------------------
# 第二步：动机
# ------------------------------------------------------------
st.markdown("### 第二步 · 你选择它的理由，是谁的理由？")
st.caption("这一节不是心理诊断。我们只是把你自己可能说不清的东西命名出来给你看。")
motive_text = st.text_area(
    "**你选择现在这个方向（或倾向的方向），最主要的原因是什么？**", height=100,
    placeholder="例如：网上说这个专业有意思；家里也挺支持的，说这个专业体面……",
)
st.caption("💡 追问自己一句：**如果家里完全反对、也没有任何人知道你的选择，你还会选吗？**")
motive_followup = st.radio(
    "**如果没有任何人知道你的选择，你还会选吗？**",
    ["会", "不会", "不确定"], index=2, horizontal=True,
)

st.markdown("---")

# ------------------------------------------------------------
# 第三步：代价结构
# ------------------------------------------------------------
st.markdown("### 第三步 · 代价结构")
st.caption("能力可以补，代价必须认。这几项问的不是你喜不喜欢，而是**你愿意为它付多少**。")

willingness = {}
wc = st.columns(4)
WEIGHTED_DIMS = [
    ("long_feedback", "长期无反馈耐受", "能在很长时间看不到结果的情况下继续做"),
    ("failure_tolerance", "失败耐受", "反复失败、反复排查同一个问题"),
    ("self_drive", "自驱投入", "没有人给你目标和截止日期时，自己往前走"),
    ("memory", "记忆负荷", "大量需要精确记忆的内容"),
]
for i, (dim, label, help_text) in enumerate(WEIGHTED_DIMS):
    with wc[i]:
        willingness[dim] = st.slider(label, 1, 5, 3, key=f"w_{dim}", help=help_text)

wc2 = st.columns(3)
for i, (dim, label) in enumerate([("cognitive", "认知强度"), ("sensation", "细节分辨"),
                                  ("hands_on", "动手要求")]):
    with wc2[i]:
        willingness[dim] = st.slider(label, 1, 5, 3, key=f"w_{dim}")

st.markdown("---")

# ------------------------------------------------------------
# 第四步：现实约束与愿景
# ------------------------------------------------------------
st.markdown("### 第四步 · 现实约束与愿景")
c1, c2 = st.columns(2)
with c1:
    constraints = st.multiselect(
        "**你目前面临的现实约束？**（只影响可行性与时间表，不影响我们对你能力的判断）",
        ["经济压力", "家庭期待", "地域限制", "成绩限制", "健康"], default=[],
    )
with c2:
    vision = st.text_area("**你希望自己成为一个什么样的人？**", height=100,
                          placeholder="例如：我希望成为一个既懂技术、又不被技术工具化的人……")

st.markdown("**体验者 / 构建者**（来自访谈：要区分自己是「只想爽」还是「想定义规则」）")
builder_answer = st.text_area(
    "玩游戏 / 用软件 / 看比赛时，你更常想「怎么通关」，还是想「这个机制为什么这样设计、"
    "我能不能改」？", height=80, placeholder="随便写几句，不用完整",
)

st.markdown("---")

# ------------------------------------------------------------
# 第五步：四周微坚持（可选）
# ------------------------------------------------------------
st.markdown("### 第五步 · 四周微坚持（可选，但这一栏最值钱）")
st.caption("「我能不能坚持」这个问题，靠想是想不出来的。这里测的不是热情，是**结构**。")
use_curve = st.checkbox("我已经做过四周的记录了", value=False)
curve = None
if use_curve:
    cols = st.columns(4)
    days = []
    for i in range(4):
        with cols[i]:
            days.append(st.number_input(f"第 {i+1} 周完成天数", 0, 7, 3, key=f"d{i}"))
    curve = micro_commitment_curve(days)
    st.info(f"曲线形态：**{curve['structure']}**　{curve['reading']}")
else:
    st.caption("模板：设定一个**不可能失败**的强度（例如每天 20 分钟），"
               "连续四周，只记录完成的天数。别加意志力，加结构。")

st.markdown("---")

# ------------------------------------------------------------
# 生成
# ------------------------------------------------------------
c_left, c_mid, c_right = st.columns([1, 1, 1])
with c_mid:
    generate = st.button("🎯 生成我的志业报告", width="stretch", type="primary")

if generate:
    with st.spinner("正在从你的叙述里提取行为证据……"):
        sig = extract_signature(narrative, motive_text, additional)
        builder = experiencer_or_builder(builder_answer)

        profile = Profile(
            signature=sig,
            willingness=willingness,
            avoid=avoid,
            constraints=constraints,
            interests=[],
            vision=vision or "（未填写）",
            motive_text=motive_text,
            builder=builder,
            curve=curve,
        )

        cands = [m for m in MAJORS_ALL if m in MD.known_majors()]
        hyps = evaluate(profile, cands, top_k=4, allow_provisional=allow_prov)
        report = generate_report(profile, cands, top_k=3, allow_provisional=allow_prov)
        if use_llm and api_key:
            from zhiyejing.llm import enhance_with_llm
            with st.spinner("DeepSeek 正在润色报告……"):
                report = enhance_with_llm(report, profile, api_key)

        st.session_state["report"] = report
        st.session_state["hyps"] = hyps
        st.session_state["profile"] = profile
        st.session_state["sig"] = sig

# ------------------------------------------------------------
# 展示
# ------------------------------------------------------------
if st.session_state.get("report"):
    sig = st.session_state["sig"]
    hyps = st.session_state["hyps"]

    st.markdown("---")
    st.markdown("# 📄 你的志业报告")

    # ---- 能力信号卡（可视化）----
    st.markdown("### 能力信号卡")
    st.caption("★★★ 是**证据的可靠程度**，不是你的能力高低。")
    STARS = {0: "○○○", 1: "●○○", 2: "●●○", 3: "●●●"}
    rows = []
    for k in sig.signals:
        s = sig.signals[k]
        rows.append({
            "能力": AB_LABELS[k],
            "证据强度": STARS[s.evidence],
            "状态": s.status,
            "置信度": s.confidence(),
            "你自己说过的话": (s.evidence_quotes[0][:56] + "…") if s.evidence_quotes else "—",
        })
    st.dataframe(rows, width="stretch", hide_index=True)

    todo = [AB_LABELS[k] for k in sig.signals if sig.signals[k].is_claim_only]
    if todo:
        st.warning(
            f"**需要说清楚的一件事：** 在 {'、'.join(todo)} 这几项上，"
            f"你目前只有自我描述，没有具体经历。\n\n"
            f"这不代表你不行——**只代表这条还没被验证过。**"
        )

    m1, m2, m3 = st.columns(3)
    m1.metric("动机自洽度", f"{sig and st.session_state['profile'].autonomy:.2f}",
              help="内部动机 1.00 → 外部调节 0.20")
    m2.metric("生命主题", " / ".join(sig.themes) if sig.themes else "未识别")
    if sig.counter_quotes:
        m3.metric("反证据", f"{len(sig.counter_quotes)} 条", help=",".join(sig.counter_quotes)[:200])

    # ---- 五分数对照表 ----
    st.markdown("### 五分数向量（不是排名）")
    st.caption("顺序只是参考。同一个综合分，构成不同，人生建议完全不同。")
    table_rows = []
    for h in hyps:
        s = h.scores
        table_rows.append({
            "假设": h.major,
            "数据": "人工标注" if not h.is_provisional else "⚠ 未核实",
            "综合": f"{h.composite:.0%}",
            "潜质": f"{s['potential']:.0%}",
            "可转换": f"{s['transition']:.0%}",
            "动机": f"{s['autonomy']:.0%}",
            "可行": f"{s['feasibility']:.0%}",
            "志业 II": f"{h.ii.get('ii')}" if h.ii.get("ii") is not None else "—",
            "避雷": f"{s['avoidance']:.0%}",
        })
    st.dataframe(table_rows, width="stretch", hide_index=True)

    # ---- 不可替代性 ----
    st.markdown("### 不可替代性分析")
    for h in hyps:
        ii = h.ii
        if ii.get("ii") is None:
            continue
        with st.expander(f"{h.major}　II = {ii['ii']}"
                         + ("　⚠ 未核实" if ii.get("provisional") else "")):
            iv = st.columns(4)
            for i, (k, label) in enumerate(MD.IRREPLACE_LABELS.items()):
                iv[i].metric(label, f"{ii['dims'][k]}/3")
            st.markdown(f"**你的能力组合稀有度**：{ii['rarity']}　"
                        f"（稀有度是乘数，它放大你已获得的一切）")
            st.markdown(f"**最短的一块板**：{ii['weakest_label']}")
            st.info(ii["ai_note"])
            if ii.get("bottleneck"):
                st.caption(f"被压缩得最厉害的部分：{ii['bottleneck']}")
            st.markdown(f"**策略一 · {ii['strategy']['primary_name']}**："
                        f"{ii['strategy']['primary_detail']}")
            st.markdown(f"**策略二 · {ii['strategy']['cross_name']}**："
                        f"{ii['strategy']['cross_detail']}")

    # ---- 完整报告 ----
    st.markdown("---")
    st.markdown(st.session_state["report"])

    st.markdown("---")
    c_dl, c_json, c_reset = st.columns([1, 1, 1])
    import json
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    with c_dl:
        st.download_button("⬇️ 下载报告 (Markdown)",
                           data=st.session_state["report"],
                           file_name=f"zhiyejing_report_{ts}.md",
                           mime="text/markdown", width="stretch")
    with c_json:
        dump = {r["假设"]: r for r in table_rows}
        st.download_button("⬇️ 下载评估数据 (JSON)",
                           data=json.dumps(dump, ensure_ascii=False, indent=2),
                           file_name=f"zhiyejing_data_{ts}.json",
                           mime="application/json", width="stretch")
    with c_reset:
        if st.button("🔄 重新填写", width="stretch"):
            for k in ["report", "hyps", "profile", "sig"]:
                st.session_state.pop(k, None)
            st.rerun()

st.markdown("---")
st.caption("🪞 志业镜 · 专业不是终身枷锁，而是你成为完整的人的一段路径。"
           "本工具不替代专业咨询、心理辅导与个人判断。")
