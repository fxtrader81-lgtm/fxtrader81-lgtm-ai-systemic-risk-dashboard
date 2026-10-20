"""Native, dark-theme-scoped inspection of capability-aligned token prices."""
import json
import streamlit as st
from components.ui import evidence_table


def price(value):
    return f"${value:.6f}" if value is not None else "N/A"


def render_price_evidence(snapshot, capability):
    rows = [("美国闭源" if r["group"] == "closed" else "中国开放权重",
             r["company"], r["model"], r["price_id"] or "未核验", price(r["input_per_m"]),
             price(r["output_per_m"]), r["reason"] or "输入价有效") for r in snapshot["rows"]]
    st.markdown(evidence_table("本期六型号Token单价", ["分组", "平台", "评测型号/档位", "定价目录型号", "输入/百万Token", "输出/百万Token（不计分）", "状态"], rows), unsafe_allow_html=True)
    st.write(snapshot["basis"])
    st.caption(f"评测版本 {capability['release']} · 价格采集时间 {snapshot['checked_at']} · 输入覆盖 {snapshot['coverage']}/6。价格不是评测发布当日的历史价，也不是完成同一任务的实际成本。")
    m = snapshot["metrics"]
    if m:
        c = "＋".join(f"{r['input_per_m']:.6f}" for r in snapshot["rows"] if r["group"] == "closed")
        o = "＋".join(f"{r['input_per_m']:.6f}" for r in snapshot["rows"] if r["group"] == "open")
        st.write(f"美国闭源输入均价＝（{c}）÷3＝${m['closed_avg']:.6f}/百万Token。")
        st.write(f"中国开放权重输入均价＝（{o}）÷3＝${m['open_avg']:.6f}/百万Token。")
        st.write(f"R＝{m['open_avg']:.6f}÷{m['closed_avg']:.6f}×100%＝{m['ratio']:.4f}%；压缩幅度P＝max(0,100－R)＝{m['compression']:.4f}%。")
        st.write(f"价格分＝clamp[(P－10)÷50×100,0,100]＝{m['score']:.4f}；×35%贡献{m['contribution']:.4f}。按原比例阈值状态为{m['state']}；分数满分不等于状态必为CRITICAL，保留原有两套映射。")
    else:
        st.warning(snapshot.get("error") or "本期同型号输入价未全部取得，不能把剩余两家均值当作三家，也不使用旧型号补价。完整OSCI暂不可用。")
    with st.expander("型号对应关系与原始定价条件", expanded=False):
        for r in snapshot["rows"]:
            st.write(f"{r['model']} → {r['price_id'] or '未映射'}：{r['mapping_note']}")
            st.markdown(f"[查看价格来源]({r['source_url']})")
        st.caption("若目录含overrides，可能存在长上下文、时段等差异；本比较只使用目录基础prompt价，不冒充所有条件下同价。完整pricing字段随下载保存。")


def render_price_history(snapshot, records):
    st.markdown(evidence_table("已保存的价格采集记录", ["采集时间UTC", "输入覆盖", "闭源均价", "开放权重均价", "价格比例", "价格状态"],
        [(s["checked_at"], f"{s['coverage']}/6", price(s["metrics"]["closed_avg"]) if s["metrics"] else "N/A",
          price(s["metrics"]["open_avg"]) if s["metrics"] else "N/A",
          f"{s['metrics']['ratio']:.4f}%" if s["metrics"] else "N/A",
          s["metrics"]["state"] if s["metrics"] else "N/A") for s in records]), unsafe_allow_html=True)
    st.caption("历史记录从本次改造开始留存；此前未保存的价格不回填。样本或目录条件变化不能直接解释为同口径降价。历史存当前部署本地磁盘，云端重建不保证持久，请下载备份。")
    st.download_button("下载本期价格与历史原始资料", json.dumps({"current": snapshot, "records": records}, ensure_ascii=False, indent=2), file_name="model-price-history.json", mime="application/json", key="download_price_evidence")
