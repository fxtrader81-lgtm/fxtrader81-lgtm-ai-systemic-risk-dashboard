"""Fixed regional proxy medians and endpoint sensitivity; original scoring unchanged."""
from contextlib import closing
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import sqlite3
from statistics import median

CONFIG = Path(__file__).resolve().parents[1] / "config/energy_cost_verified.json"
CLUSTER_CONFIG = Path(__file__).resolve().parents[1] / "config/energy_cluster_prices.json"
STORE = Path(__file__).resolve().parents[1] / ".local/energy_cost_history.sqlite3"
REFERENCE_CONFIG = Path(__file__).resolve().parents[1] / "config/energy_reference_prices.json"


RATIO_BANDS = ((.8, "SAFE", 15), (.6, "WATCH", 40), (.4, "WARNING", 60), (0, "CRITICAL", 85))


def ratio_rating(ratio):
    if isinstance(ratio, bool) or not isinstance(ratio, (int, float)) or not math.isfinite(ratio) or ratio <= 0:
        return None
    return next((state, score) for lower, state, score in RATIO_BANDS if ratio >= lower)


def reference_comparison(data, opex_pct=None, legacy=False):
    """Endpoint medians, not midpoints or a statistical confidence interval."""
    result = dict(available=False, us_price=None, cn_price=None, ratio=None, score=None,
                  ratio_range=None, score_range=None, missing_reason="固定样本/汇率不完整或无效")
    positive = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v > 0
    fx = data.get("fx", {}).get("cny_per_usd")
    if not positive(fx):
        return result
    groups = {}
    for country, expected in data.get("expected", {}).items():
        rows = [r for r in data.get("rows", []) if r.get("country") == country]
        if len(rows) != len(expected) or len(set(expected)) != len(expected) or {r.get("id") for r in rows} != set(expected) or len(rows) < 2:
            return result
        if any(not positive(r.get("low")) or not positive(r.get("high")) or r["low"] > r["high"] or r.get("currency") != ("CNY" if country == "CN" else "USD") for r in rows):
            return result
        scale = fx if country == "CN" else 1
        groups[country] = [median(r[k] / scale for r in rows) for k in ("low", "high")]
    if set(groups) != {"CN", "US"}:
        return result
    cn, us = groups["CN"], groups["US"]
    ratios = [cn[0] / us[1], cn[1] / us[0]]
    ratings = [ratio_rating(r) for r in ratios]
    scores = sorted([score_cost(us[1], cn[0], opex_pct), score_cost(us[0], cn[1], opex_pct)] if legacy else [r[1] for r in ratings], key=lambda v: -1 if v is None else v)
    if any(v is None for v in scores):
        return result
    # A single contribution is safe only when both endpoints yield the same rounded score.
    return dict(result, available=scores[0] == scores[1], us_price=us[0] if us[0] == us[1] else None,
                cn_price=cn[0] if cn[0] == cn[1] else None, cn_price_range=cn, us_price_range=us,
                ratio_range=ratios, score_range=scores, score=scores[0] if scores[0] == scores[1] else None,
                state=ratings[0][0] if ratings[0][0] == ratings[1][0] else "N/A",
                state_range=[r[0] for r in ratings],
                missing_reason="" if scores[0] == scores[1] else "区间得分不同，展示范围，不擅自选择单点计入整页")


def score_cost(us_price, cn_price, opex_pct):
    values = (us_price, cn_price, opex_pct)
    if any(isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) for v in values):
        return None
    if us_price <= 0 or cn_price <= 0 or not 0 <= opex_pct <= 100:
        return None
    clamp = lambda x: max(0, min(100, x))
    return round(.55 * clamp((.6-cn_price/us_price)/.4*100) + .45 * clamp((opex_pct-10)/25*100), 1)


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def _save(record, path=None):
    target = Path(path or STORE)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = _json(record)
    with closing(sqlite3.connect(str(target))) as conn, conn:
        conn.execute("CREATE TABLE IF NOT EXISTS versions (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        conn.execute("INSERT OR IGNORE INTO versions VALUES (?, ?)", (
            sha256(payload.encode()).hexdigest(),
            _json(dict(record, adopted_at=datetime.now(timezone.utc).isoformat()))))


def load_industrial_background(path=None):
    data = json.loads(CONFIG.read_text())
    rows = data.get("rows", [])
    valid = len(rows) == 2 and {r.get("country") for r in rows} == {"US", "CN"}
    prices = {}
    for r in rows:
        value = r.get("usd_mwh")
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value <= 0:
            valid = False
        else:
            prices[r["country"]] = value/1000
    us, cn = prices.get("US"), prices.get("CN")
    score = score_cost(us, cn, data.get("opex_pct")) if valid else None
    current = dict(data, us_price=us, cn_price=cn, ratio=cn/us if valid else None,
                   score=score, available=score is not None)
    _save({"id": "legacy-static-2025-01", "classification": "旧静态输入，出处未核验；仅供追溯",
           "us_price": .079, "cn_price": .028, "opex_pct": 15,
           "score": score_cost(.079, .028, 15), "recorded_period": "2025-01",
           "caveat": "原美国PPA/商业电价标签混用，中国西部工业谷价，非同口径；不是历史完整ESRI。"}, path)
    _save(current, path)
    return current


def load_cost(path=None):
    """Preserve past methods; calculate the approved fixed regional proxy basket."""
    background = load_industrial_background(path)
    data = json.loads(CLUSTER_CONFIG.read_text())
    current = dict(data, background=background, us_price=None, cn_price=None, ratio=None,
                   score=None, available=False, opex_pct=background["opex_pct"],
                   opex_classification=background["opex_classification"],
                   period="各集群分别列示，尚未形成同期间成对样本")
    _save(current, path)
    reference = json.loads(REFERENCE_CONFIG.read_text())
    latest = dict(reference, background=background, prior_cluster_evidence=data,
                  opex_pct=background["opex_pct"], opex_classification=background["opex_classification"])
    latest.update(reference_comparison(reference, latest["opex_pct"]))
    old = dict(latest)
    old.update(reference_comparison(reference, latest["opex_pct"], legacy=True))
    # Recreate the prior payload exactly: it remains an immutable method version.
    old.pop("state", None)
    old.pop("state_range", None)
    _save(old, path)
    latest.update(id="regional-ratio-bands-v2-2026-10-22", method_version="ratio-bands-v2",
                  scoring_policy="R≥0.80 SAFE/15；0.60≤R<0.80 WATCH/40；0.40≤R<0.60 WARNING/60；0<R<0.40 CRITICAL/85。管理阈值与档位分值，非行业标准或风险概率；15%OpEx不再参与评分。")
    _save(latest, path)
    return latest


def history(path=None):
    target = Path(path or STORE)
    if not target.exists():
        return []
    with closing(sqlite3.connect(str(target))) as conn:
        return [json.loads(r[0]) for r in conn.execute("SELECT payload FROM versions ORDER BY rowid DESC")]
