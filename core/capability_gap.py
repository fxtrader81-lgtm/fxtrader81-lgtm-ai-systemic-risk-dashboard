"""Factor 02 capability history, relative scores, and legacy compatibility.

No network on page reads. Only the explicit refresh fetches the reviewed CSV.
An immutable measurement history and active record live in a local SQLite file.
The approved all-task cohort engine handles current refresh and validation;
fixed-task helpers remain available to reproduce archived measurements.
"""
from __future__ import annotations

import copy
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import re
import sqlite3
from datetime import datetime, timezone

import requests

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "config" / "capability_baseline.json"
STORE = ROOT / ".local" / "capability_history.sqlite3"
TASKS = ("math_comp", "code_generation", "logic_with_navigation")
TASK_LABELS = ("数学竞赛", "代码生成", "逻辑导航")
SOURCE_URL = "https://raw.githubusercontent.com/LiveBench/new-livebench/main/public/table_2026_06_25.csv"
SOURCE_PAGE = "https://github.com/LiveBench/new-livebench/blob/main/public/table_2026_06_25.csv"
FORMULA_VERSION = "livebench-three-task-relative-v1"


def baseline():
    return json.loads(BASELINE.read_text(encoding="utf-8"))


def _number(value):
    if isinstance(value, bool):
        raise ValueError("成绩不能是布尔值")
    value = float(value)
    if not math.isfinite(value) or not 0 <= value <= 100:
        raise ValueError("成绩必须为0–100的有限数值")
    return value


def gap_state(gap_pct):
    if gap_pct > 12:
        return "SAFE"
    if gap_pct > 6:
        return "WATCH"
    if gap_pct > 2:
        return "WARNING"
    return "CRITICAL"


def measure(closed_scores, open_scores, *, legacy=False):
    """All arithmetic keeps full precision until presentation; legacy is archival."""
    if len(closed_scores) != 3 or len(open_scores) != 3:
        raise ValueError("双方必须各有同样三项完整成绩")
    closed = sum(_number(v) for v in closed_scores) / 3
    opened = sum(_number(v) for v in open_scores) / 3
    return relative_metrics(closed, opened, legacy=legacy)


def relative_metrics(closed, opened, *, legacy=False):
    """Shared gap-to-score rule; inputs may be legacy means or group mean totals."""
    if not all(math.isfinite(v) and v >= 0 for v in (closed, opened)):
        raise ValueError("两组得分必须是非负有限数")
    if closed <= 0:
        raise ValueError("闭源均分必须大于0，不能计算相对差距")
    difference = closed - opened
    signed = difference if legacy else difference / closed * 100
    risk_gap = max(0.0, signed)
    score = max(0.0, min(60.0, (25 - risk_gap) / 25 * 60))
    return {"closed_avg": closed, "open_avg": opened,
            "difference_pp": difference, "signed_gap": signed,
            "risk_gap": risk_gap, "score": score, "contribution": score * .20,
            "state": gap_state(risk_gap)}


def _side(model):
    # Source IDs are candidates, not a license claim or a national capability score.
    if re.fullmatch(r"(?:gpt-\d|claude-)[a-z0-9.\-]*", model):
        return "closed"
    if re.fullmatch(r"(?:deepseek-v\d|qwen\d)[a-z0-9.\-]*", model):
        return "open"
    return None


def parse_catalog(text):
    if len(text.encode("utf-8")) > 2_000_000:
        raise ValueError("来源文件过大，未采用")
    reader = csv.DictReader(io.StringIO(text))
    fields = reader.fieldnames or []
    if len(fields) != len(set(fields)) or not {"model", *TASKS}.issubset(fields):
        raise ValueError("来源字段或固定测试项目发生变化，需人工核验")
    models = {}
    for row in reader:
        model = row.get("model", "")
        if not _side(model):
            continue
        if model in models:
            raise ValueError("来源出现重复模型行，未采用")
        try:
            values = [_number(row[t]) for t in TASKS]
        except (ValueError, TypeError, KeyError):
            continue  # Incomplete candidate is not eligible for a new comparison.
        models[model] = {"side": _side(model), "scores": values}
    if not models:
        raise ValueError("来源没有完整的可比模型成绩")
    return models


def fetch_catalog():
    # Fixed public HTTPS source; never browse arbitrary URLs or run model tests.
    response = requests.get(SOURCE_URL, timeout=15,
                            headers={"Cache-Control": "no-cache"}, stream=True)
    try:
        response.raise_for_status()
        chunks, size = [], 0
        for chunk in response.iter_content(65536):
            size += len(chunk)
            if size > 2_000_000:
                raise ValueError("来源文件过大，未采用")
            chunks.append(chunk)
        content = b"".join(chunks)
    finally:
        response.close()
    text = content.decode("utf-8-sig")
    return {"models": parse_catalog(text),
            "source_sha256": hashlib.sha256(content).hexdigest(),
            "checked_at": datetime.now(timezone.utc).isoformat()}


def make_snapshot(catalog, closed_model, open_model):
    models = catalog["models"]
    if closed_model not in models or open_model not in models:
        raise ValueError("所选型号没有完整三项成绩；保留上次有效结果")
    if models[closed_model]["side"] != "closed" or models[open_model]["side"] != "open":
        raise ValueError("闭源与开放权重的对比方向错误")
    result = baseline()
    result.pop("legacy")
    result.update(closed_model=closed_model, open_model=open_model,
                  closed_scores=models[closed_model]["scores"],
                  open_scores=models[open_model]["scores"],
                  checked_at=catalog["checked_at"], source_sha256=catalog["source_sha256"])
    # Do not silently relabel another selected version as the 1017 update.
    result["caveat"] = ("型号以公开结果表标识为准，不自动等同于API当前别名；"
                        "评测版本日期不等于模型测试日期。三个任务不能代表整体智能或实际商业替代。")
    result["metrics"] = measure(result["closed_scores"], result["open_scores"])
    result["formula_version"] = FORMULA_VERSION
    return result


def _connect(path=None):
    path = Path(path) if path is not None else STORE
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS records (
            fingerprint TEXT PRIMARY KEY, payload TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS current_record (
            id INTEGER PRIMARY KEY CHECK(id=1), fingerprint TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS refresh_status (
            id INTEGER PRIMARY KEY CHECK(id=1), checked_at TEXT, message TEXT);
    """)
    return conn


def adopt(snapshot, path=None):
    """Commit only complete, valid comparisons; identical reads add no history row."""
    item = copy.deepcopy(snapshot)
    from core import capability_cohort as cohort
    if item.get("formula_version") == cohort.VERSION:
        item = cohort.validate_snapshot(item)
        key = cohort.fingerprint(item)
        previous = current_snapshot(path)
        item["change_notes"] = cohort.describe_change(previous, item)
    else:
        if tuple(item["tasks"]) != TASKS or item["source_url"] != SOURCE_URL:
            raise ValueError("旧版历史资料的测试项目或来源变化")
        if _side(item["closed_model"]) != "closed" or _side(item["open_model"]) != "open":
            raise ValueError("模型对比方向错误")
        item["metrics"] = measure(item["closed_scores"], item["open_scores"])
        item["formula_version"] = FORMULA_VERSION
        identity = {k: item[k] for k in ("closed_model", "open_model", "tasks",
                                        "closed_scores", "open_scores", "release", "formula_version")}
        key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    conn = _connect(path)
    try:
        with conn:
            added = conn.execute("INSERT OR IGNORE INTO records VALUES (?,?,?)",
                                 (key, json.dumps(item, ensure_ascii=False), item["checked_at"])).rowcount
            conn.execute("INSERT OR REPLACE INTO current_record VALUES (1,?)", (key,))
        return bool(added)
    finally:
        conn.close()


def current_snapshot(path=None):
    conn = _connect(path)
    try:
        row = conn.execute("SELECT payload FROM records JOIN current_record USING(fingerprint)").fetchone()
    finally:
        conn.close()
    if row:
        item = json.loads(row[0])
        if item.get("formula_version") != "livebench-all-tasks-top3-relative-v2":
            item["metrics"] = measure(item["closed_scores"], item["open_scores"])
        return item
    item = baseline()
    item.pop("legacy")
    adopt(item, path)
    return current_snapshot(path)


def history(path=None):
    conn = _connect(path)
    try:
        return [json.loads(row[0]) for row in conn.execute(
            "SELECT payload FROM records ORDER BY created_at DESC, rowid DESC")]
    finally:
        conn.close()


def record_refresh(message, path=None):
    conn = _connect(path)
    try:
        with conn:
            conn.execute("INSERT OR REPLACE INTO refresh_status VALUES (1,?,?)",
                         (datetime.now(timezone.utc).isoformat(), message))
    finally:
        conn.close()


def last_refresh(path=None):
    conn = _connect(path)
    try:
        return conn.execute("SELECT checked_at,message FROM refresh_status WHERE id=1").fetchone()
    finally:
        conn.close()


def ensure_full_baseline(path=None):
    """One-time local migration, retaining every previous immutable history row."""
    from core import capability_cohort as cohort
    current = current_snapshot(path)
    if current.get("formula_version") == cohort.VERSION or not cohort.SEED.exists():
        return current
    adopt(json.loads(cohort.SEED.read_text(encoding="utf-8")), path)
    return current_snapshot(path)
