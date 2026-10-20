"""Price only the six reviewed capability models; never substitute relatives."""
import hashlib
import json
import math
from pathlib import Path
import sqlite3
from datetime import datetime, timezone

import requests
import streamlit as st

from core.capability_cohort import fingerprint, parse_metadata

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "config" / "price_model_links.json"
STORE = ROOT / ".local" / "model_price_history.sqlite3"
SOURCE = "https://openrouter.ai/api/v1/models"


def cohort_request(capability):
    metadata = parse_metadata(capability["raw_metadata"])
    selected = [{"group": group, "company": row["company"], "model": row["model"],
                 "capability_release": capability["release"], "capability_revision": capability["revision"],
                 "evidence": metadata.get(row["model"], {})}
                for group in ("closed", "open") for row in capability["selected"][group]]
    return fingerprint(capability), json.dumps(selected, sort_keys=True)


def per_million(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value) * 1_000_000
    except (ValueError, TypeError, OverflowError):
        return None
    return result if math.isfinite(result) and result >= 0 else None


def calculate_prices(selected, catalog, policy, *, cohort_key, checked_at, error=None):
    entries = catalog.get("data", []) if isinstance(catalog, dict) else []
    index = {}
    for item in entries:
        if isinstance(item, dict):
            index.setdefault(item.get("id"), []).append(item)
    rows = []
    for item in selected:
        link = policy["models"].get(item["model"])
        row = dict(item, price_id=link["id"] if link else None,
                   mapping_note=link.get("note", "") if link else "新型号尚未核验价格映射，不猜测替代。",
                   input_per_m=None, output_per_m=None, raw_pricing=None, reason=error)
        matches = index.get(row["price_id"], [])
        if not error:
            if not link:
                row["reason"] = "未核验同型号价格映射"
            elif link.get("required_huggingface") and item["evidence"].get("huggingface") != link["required_huggingface"]:
                row["reason"] = "本期型号证据与已审核别名不一致"
            elif len(matches) != 1:
                row["reason"] = "同型号价格未上架或记录重复"
            else:
                pricing = matches[0].get("pricing") or {}
                row.update(input_per_m=per_million(pricing.get("prompt")),
                           output_per_m=per_million(pricing.get("completion")), raw_pricing=pricing)
                if row["input_per_m"] is None:
                    row["reason"] = "输入价格缺失或无效"
        row["source_url"] = "https://openrouter.ai/" + row["price_id"] if row["price_id"] else SOURCE
        rows.append(row)
    sides = {g: [r for r in rows if r["group"] == g] for g in ("closed", "open")}
    available = all(len(rs) == 3 and len({r["company"] for r in rs}) == 3
                    and all(r["input_per_m"] is not None and not r["reason"] for r in rs)
                    for rs in sides.values())
    metrics = None
    if available:
        closed = sum(r["input_per_m"] for r in sides["closed"])/3
        opened = sum(r["input_per_m"] for r in sides["open"])/3
        if closed <= 0:
            available = False
            error = "闭源平均输入价为0，无法作为分母"
        else:
            ratio = opened/closed*100
            compression = max(0, 100-ratio)
            # Preserve the original page's formula and boundary semantics.
            state = "SAFE" if compression < 30 else "WATCH" if compression < 55 else "WARNING" if compression < 75 else "CRITICAL"
            score = max(0, min(100, (compression-10)/50*100))
            metrics = {"closed_avg": closed, "open_avg": opened, "ratio": ratio,
                       "compression": compression, "score": score, "state": state,
                       "contribution": score*.35}
    return {"cohort_key": cohort_key, "checked_at": checked_at, "source": SOURCE,
            "formula": "R=mean(open input price)/mean(closed input price)*100; P=max(0,100-R); score=clamp((P-10)/50*100,0,100); weight=0.35; state by P<30/55/75",
            "policy_version": policy["version"], "rows": rows, "available": available,
            "coverage": sum(r["input_per_m"] is not None and not r["reason"] for r in rows),
            "metrics": metrics, "error": error,
            "basis": "USD/百万Token；OpenRouter目录基础输入价prompt；输出completion只展示。不使用缓存价、batch、latest或另一型号；目录基础价不代表所有路由/长上下文/时段的实际账单。"}


def archive(snapshot, path=None):
    path = Path(path or STORE)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(snapshot, ensure_ascii=False, sort_keys=True)
    identity = {k: v for k, v in snapshot.items() if k != "checked_at"}
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE IF NOT EXISTS snapshots (id TEXT PRIMARY KEY, checked_at TEXT NOT NULL, payload TEXT NOT NULL)")
        db.execute("INSERT OR IGNORE INTO snapshots VALUES (?, ?, ?)", (key, snapshot["checked_at"], payload))


def history(path=None):
    path = Path(path or STORE)
    if not path.exists():
        return []
    with sqlite3.connect(path) as db:
        return [json.loads(r[0]) for r in db.execute("SELECT payload FROM snapshots ORDER BY checked_at DESC, rowid DESC")]


@st.cache_data(ttl=3600)
def get_selected_prices(cohort_key, selected_json, policy_json):
    error = None
    catalog = {}
    try:
        response = requests.get(SOURCE, timeout=15)
        response.raise_for_status()
        catalog = response.json()
        if not isinstance(catalog, dict) or not isinstance(catalog.get("data"), list):
            raise ValueError("模型目录格式异常")
    except (requests.RequestException, ValueError) as exc:
        error = f"价格目录读取失败（{type(exc).__name__}）"
    result = calculate_prices(json.loads(selected_json), catalog, json.loads(policy_json),
        cohort_key=cohort_key, checked_at=datetime.now(timezone.utc).isoformat(), error=error)
    archive(result)
    return result


def load_prices(capability):
    key, selection = cohort_request(capability)
    return get_selected_prices(key, selection, POLICY.read_text(encoding="utf-8"))
