"""Reviewed rack-reference scenario, shared by detail and overview.

No network polling: new hardware references require a reviewed new revision.
History is append-only and retains both inputs and the scoring rule in force.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "aof_references.json"
STORE = ROOT / ".local" / "aof_history.sqlite3"
RULE = {
    "version": "aof-original-v1",
    "weight": 0.25,
    "formula": "AOF=round(rack_kw/baseline_kw,2)",
    "scoring": "AOF<1.5:0; <2.5:round((AOF-1.5)*33); <3.5:round(33+(AOF-2.5)*34); otherwise:round(min(100,67+(AOF-3.5)/0.5*33))",
    "state_cutoffs": [1.5, 2.5, 3.5],
    "note": "沿用项目原研究阈值，未按本次机柜方案重新校准；高功率参考可能长期饱和100分。",
}
LIMITATION = "AOF是特定机柜方案对固定旧机房容量情景的适配压力，不是全市场实际部署、资产减值比例或会计减值证据。更换参考机柜产生口径断点，不能将新旧分差解释为同期市场突然恶化。"


def _positive(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError("AOF功率必须为有限正数，缺失值不能填0或默认值")


def score_aof(aof):
    _positive(aof)
    if aof < 1.5:
        return 0, "green", "↗", "SAFE"
    if aof < 2.5:
        return round((aof-1.5)*33), "yellow", "→", "WATCH"
    if aof < 3.5:
        return round(33+(aof-2.5)*34), "orange", "↘", "WARNING"
    return round(min(100, 67+(aof-3.5)/0.5*33)), "red", "↓", "CRITICAL"


def make_snapshot(reference):
    _positive(reference["rack_kw"])
    _positive(reference["baseline_kw"])
    ratio = round(reference["rack_kw"]/reference["baseline_kw"], 2)
    score, color, arrow, state = score_aof(ratio)
    return {"reference": deepcopy(reference), "rule": deepcopy(RULE), "limitation": LIMITATION,
            "metrics": {"aof": ratio, "score": score, "color": color, "arrow": arrow,
                        "state": state, "contribution": score*RULE["weight"]}}


def _encoded(snapshot):
    return json.dumps(snapshot, ensure_ascii=False, sort_keys=True, allow_nan=False)


def archive(snapshot, path=None):
    path = Path(path or STORE)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _encoded(snapshot)
    digest = hashlib.sha256(payload.encode()).hexdigest()
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE IF NOT EXISTS snapshots (id TEXT PRIMARY KEY, digest TEXT NOT NULL, archived_at TEXT NOT NULL, payload TEXT NOT NULL)")
        existing = db.execute("SELECT digest FROM snapshots WHERE id=?", (snapshot["reference"]["id"],)).fetchone()
        if existing and existing[0] != digest:
            raise ValueError("AOF历史版本不可覆盖：变更参数、来源或规则请建立新id")
        db.execute("INSERT OR IGNORE INTO snapshots VALUES (?, ?, ?, ?)",
                   (snapshot["reference"]["id"], digest, datetime.now(timezone.utc).isoformat(), payload))


def history(path=None):
    path = Path(path or STORE)
    if not path.exists():
        return []
    with sqlite3.connect(path) as db:
        return [dict(json.loads(payload), archived_at=at) for payload, at in db.execute(
            "SELECT payload, archived_at FROM snapshots ORDER BY rowid DESC")]


def load_aof(path=None, config=None):
    catalog = json.loads(Path(config or CONFIG).read_text(encoding="utf-8"))
    records = catalog["records"]
    ids = [row["id"] for row in records]
    if len(set(ids)) != len(ids) or catalog["active_id"] not in ids:
        raise ValueError("AOF参考版本重复或本期版本缺失")
    # Validate the complete catalog before writing anything; a bad new reference
    # never silently replaces the active reading with an old valid measurement.
    snapshots = [make_snapshot(row) for row in records]
    for snapshot in snapshots:
        archive(snapshot, path)
    return next(s for s in snapshots if s["reference"]["id"] == catalog["active_id"])
