"""Inspectable interest-proxy evidence, styled by the existing shared scope."""
import json
import streamlit as st
from components.ui import evidence_table


def render_deployment_evidence(snapshot):
    st.markdown(evidence_table("自主部署工具关注度（不是实际部署量）",
        ["工具", "固定仓库", "累计stars", "覆盖状态", "数据来源"],
        [(r["name"], r["repo"], f"{r['stars']:,}" if r["stars"] is not None else "N/A",
          r.get("reason") or "有效", r["source_url"]) for r in snapshot["rows"]]), unsafe_allow_html=True)
    st.caption(f"采集时间 {snapshot['checked_at']} · 完整仓库覆盖 {snapshot['coverage']}/3 · 自动取数，缓存1小时；打开或重新加载页面时过期重取。")
    st.write(snapshot["limitation"])
    st.write(snapshot["scope_note"])
    m = snapshot["metrics"]
    if m:
        terms = "＋".join(f"{r['stars']:,}" for r in snapshot["rows"])
        st.write(f"累计星标S＝{terms}＝{m['total_stars']:,}。内部映射值＝{m['proxy_value']}（不是{m['proxy_value']}%增长率）。")
        st.write(f"分项＝clamp[({m['proxy_value']}－20)÷180×100,0,100]＝{m['score']:.4f}；×30%贡献{m['contribution']:.4f}；按原stars分档状态为{m['state']}。")
    else:
        st.warning("本次未取得完整三仓库数据：不按剩余仓库计算、不填0、不代入预设分。完整OSCI暂不可用，历史有效记录保留供查看但不冒充本次结果。")
    st.markdown(evidence_table("原有映射与评分规则（保留）", ["累计stars S", "内部映射值（非增速）", "分项分数", "状态"],
        [("S < 150,000", "30", "5.5556", "SAFE"), ("150,000 ≤ S < 300,000", "80", "33.3333", "WATCH"),
         ("300,000 ≤ S < 500,000", "140", "66.6667", "WARNING"), ("S ≥ 500,000", "220", "100", "CRITICAL")]), unsafe_allow_html=True)
    st.caption("这些是本项目既有研究阈值，未由实际企业部署或收入数据校准。累计关注度可能维持高位，即使新增关注已经放缓；本轮不加入30/90天增速评分。")
    for row in snapshot["rows"]:
        st.markdown(f"[{row['name']}：查看GitHub原始数据]({row['api_url']})")


def render_deployment_history(snapshot, records):
    st.markdown(evidence_table("部署工具关注度采集记录", ["采集时间UTC", "覆盖", "累计stars", "状态", "分项分数", "30%贡献"],
        [(r["checked_at"], f"{r['coverage']}/3", f"{r['metrics']['total_stars']:,}" if r["metrics"] else "N/A",
          r["metrics"]["state"] if r["metrics"] else "N/A", f"{r['metrics']['score']:.4f}" if r["metrics"] else "N/A",
          f"{r['metrics']['contribution']:.4f}" if r["metrics"] else "N/A") for r in records]), unsafe_allow_html=True)
    st.caption("从本次改造开始留存；不回填不存在的历史，不生成虚构30/90天增速。按来源记录去重，失败记录不覆盖旧有效记录。历史存当前部署本地磁盘，云端重建不保证保留，请下载备份。")
    st.download_button("下载部署动能历史与原始资料", json.dumps({"current": snapshot, "records": records}, ensure_ascii=False, indent=2),
        file_name="deployment-interest-history.json", mime="application/json", key="download_deployment_history")
