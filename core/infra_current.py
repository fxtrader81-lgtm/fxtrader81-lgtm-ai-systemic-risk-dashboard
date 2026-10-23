"""Reviewed infrastructure inputs shared by the detail page and overview."""
from copy import deepcopy
import json
import math
from hashlib import sha256
from pathlib import Path
from core import infra_updates

CONFIG = Path(__file__).resolve().parents[1]/"config/infra_verified.json"


def _number(value, positive=False):
    return (isinstance(value,(float,int)) and not isinstance(value,bool)
            and math.isfinite(value) and (value>0 if positive else value>=0))


def score_infra(inputs):
    keys=("interconnection_queue_months","transformer_lead_time_months","pjm_reserve_margin_pct","ercot_reserve_margin_pct")
    if not all(_number(inputs.get(k),positive=k.endswith("months")) for k in keys):
        return None
    clamp=lambda x:max(0,min(100,x))
    q=clamp((inputs[keys[0]]-12)/36*100)
    t=clamp((inputs[keys[1]]-12)/36*100)
    r=clamp((20-(inputs[keys[2]]+inputs[keys[3]])/2)/12*100)
    return round(q*.45+t*.30+r*.25,1)


def load_infra(path=None):
    config=json.loads(CONFIG.read_text())
    facts={k:deepcopy(config[k]) for k in ("queue","reserve","transformer")}
    records=infra_updates.history(path)
    evidence={e["id"]:e for e in records["evidence"]}
    # A source failure preserves the last verified facts and their original periods.
    # A successfully read but unparseable NEW report is not replaced with an old number.
    for key in facts:
        latest=next((r for c in records["checks"] for r in c["sources"]
                     if r["source_id"]==key and r["status"]=="ok" and "extracted" in evidence.get(r.get("evidence_id"),{})),None)
        if latest:
            item=evidence[latest["evidence_id"]]
            facts[key]=dict(deepcopy(item["extracted"]),url=item["url"],evidence_id=item["id"])
    q=facts["queue"]
    queue=q.get("months") if q.get("kind")=="point" and q.get("period")=="2025" else None
    reserve=facts["reserve"]
    rows={r.get("region"):r for r in reserve.get("rows",[])}
    pjm=ercot=None
    if reserve.get("kind")=="point" and reserve.get("period")=="2026年夏季" and len(rows)==2 and len(reserve.get("rows",[]))==2:
        valid=True
        for name in ("PJM","Texas RE-ERCOT"):
            row=rows.get(name,{})
            v,d,c=(row.get(k) for k in ("anticipated_margin_pct","net_internal_demand_mw","anticipated_resources_mw"))
            valid=valid and all(_number(n) for n in (v,d,c)) and d>0 and abs((c/d-1)*100-v)<=.15
        if valid:
            pjm=rows["PJM"]["anticipated_margin_pct"]
            ercot=rows["Texas RE-ERCOT"]["anticipated_margin_pct"]
    policy=deepcopy(config.get("transformer_scenario",{}))
    transformer=facts["transformer"]
    scenario_valid=(policy.get("kind")=="upper_bound_stress_scenario" and policy.get("months")==48
                    and transformer.get("kind")=="qualitative_upper_extent"
                    and transformer.get("described_max_months")==48)
    inputs={"interconnection_queue_months":queue if _number(queue,True) else None,
            "transformer_lead_time_months":48 if scenario_valid else None,
            "pjm_reserve_margin_pct":pjm,"ercot_reserve_margin_pct":ercot,
            "updated":"2025年建成项目 / 2026年夏季；变压器48月上限情景（资料观察期未明确）" if scenario_valid else "2025年建成项目 / 2026年夏季；变压器情景证据待核验"}
    score=score_infra(inputs)
    snapshot={"inputs":inputs,"facts":facts,"score":score,"available":score is not None,
            "scenario":dict(policy,evidence_valid=scenario_valid),
            "method_note":"本期变压器采用用户确认的48月交付压力上限情景，不是平均交期；原公式/权重不变。原43月及两地旧裕度无出处/字段，现采用IR至COD中位时长和夏季ARM，新旧存在口径断点；不能把分差解释为市场突然变化。",
            "missing_reason":"" if score is not None else "必要输入或48月情景证据缺失/变化，N/A；不补旧值、不改权重，不自动换成新的交期上限。"}
    payload=infra_updates._json(snapshot)
    with infra_updates._connect(path) as conn:
        stored=dict(snapshot,adopted_at=infra_updates._now().isoformat())
        conn.execute("INSERT OR IGNORE INTO input_versions VALUES (?,?)",(sha256(payload.encode()).hexdigest(),infra_updates._json(stored)))
    return snapshot
