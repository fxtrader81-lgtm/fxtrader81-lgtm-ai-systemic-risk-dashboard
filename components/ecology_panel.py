"""Current selected-model download evidence and immutable local history."""
import json
import streamlit as st
from components.ui import evidence_table
from core.ecology_downloads import LEGACY


def render_ecology_evidence(snapshot):
    st.markdown(evidence_table("本期入选三模型下载热度", ["平台", "能力评测型号", "官方模型仓库", "近30天下载", "覆盖状态", "仓库创建时间"],
        [(r["company"],r["model"],r.get("repo") or "未核验",f"{r['downloads']:,}" if r["downloads"] is not None else "N/A",
          r.get("reason") or "有效",(r.get("raw") or {}).get("createdAt") or "未提供") for r in snapshot["rows"]]),unsafe_allow_html=True)
    st.caption(f"下载量采集时间 {snapshot['checked_at']} · 覆盖{snapshot['coverage']}/3 · 跟随本期能力名单自动取数，缓存1小时；打开或重新加载页面时过期重取。")
    st.write(snapshot["window"])
    st.write(snapshot["limitation"])
    m=snapshot["metrics"]
    if m:
        terms="＋".join(f"{r['downloads']:,}" for r in snapshot["rows"])
        st.write(f"近30天下载合计D＝{terms}＝{m['total_downloads']:,}；按原分档得{m['score']}分／{m['state']}；×15%贡献{m['contribution']:.2f}分。")
    else:
        st.warning("本期三个官方模型未全部取得有效下载数：不填0，不以两家代替三家，不代入原预设30分。完整OSCI暂不可用。")
    st.info(snapshot["method_break"])
    st.markdown(evidence_table("暂沿用的原研究分档",["三模型下载合计D", "分项分数", "状态"],
        [("D < 500,000",15,"SAFE"),("500,000 ≤ D < 2,000,000",40,"WATCH"),
         ("2,000,000 ≤ D < 8,000,000",65,"WARNING"),("D ≥ 8,000,000",85,"CRITICAL")]),unsafe_allow_html=True)
    for row in snapshot["rows"]:
        if row.get("repo"):
            st.markdown(f"[{row['company']}：模型仓库]({row['source_url']}) · [API原始统计]({row['api_url']})")
    st.markdown(f"[HF下载计数规则]({snapshot['sources'][0]}) · [近30天统计字段说明]({snapshot['sources'][1]})")


def render_ecology_history(snapshot,records):
    st.markdown(evidence_table("模型下载热度采集记录",["采集时间UTC", "能力评测版次", "入选模型", "覆盖", "近30天下载合计", "分项分数", "状态"],
        [(r["checked_at"],r["rows"][0]["capability_release"]," / ".join(x["model"] for x in r["rows"]),f"{r['coverage']}/3",
          f"{r['metrics']['total_downloads']:,}" if r["metrics"] else "N/A",r["metrics"]["score"] if r["metrics"] else "N/A",
          r["metrics"]["state"] if r["metrics"] else "N/A") for r in records]),unsafe_allow_html=True)
    with st.expander("旧版样本与规则资料（不是历史实测成绩）",expanded=False):
        st.markdown(evidence_table("原固定名单",["旧详情四模型", "是否进入旧总览"],
            [(model,"是" if model in LEGACY["overview_models"] else "否") for model in LEGACY["detail_models"]]),unsafe_allow_html=True)
        st.write(LEGACY["rule"])
        st.caption(LEGACY["note"])
    st.caption("新采集记录本地追加留存、同来源内容去重，失败不覆盖旧有效记录。不回填未保存的历史，不把滚动30天窗口合计为季度量；云端临时磁盘重建不保证保留，请下载备份。")
    st.download_button("下载生态速度历史与原始资料",json.dumps({"current":snapshot,"records":records,"legacy":LEGACY},ensure_ascii=False,indent=2),
        file_name="ecology-download-history.json",mime="application/json",key="download_ecology_history")
