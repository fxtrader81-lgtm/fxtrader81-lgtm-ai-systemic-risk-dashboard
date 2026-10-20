"""Fixed deployment-tool interest proxy, not observed enterprise deployments."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3

import requests
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / ".local" / "deployment_interest_history.sqlite3"
VERSION = "deployment-tool-stars-v1"
REPOS = (
    ("Ollama", "ollama/ollama", 658928958),
    ("vLLM", "vllm-project/vllm", 599547518),
    ("llama.cpp", "ggml-org/llama.cpp", 612354784),
)
SCOPE_NOTE = "固定Ollama、vLLM、llama.cpp三仓库；llama.cpp旧地址ggerganov/llama.cpp迁移后仓库ID未变。2026-10-19核验原LM Studio地址lmstudio-ai/lmstudio-community返回404，未贡献有效stars，不纳入本期三仓库名单。工具生态不随能力代差六家平台切换。"


def measure(stars):
    if isinstance(stars, bool) or not isinstance(stars, int) or stars < 0:
        raise ValueError("stars必须为非负整数，不用缺失值代替0")
    proxy, state = ((30, "SAFE") if stars < 150_000 else (80, "WATCH") if stars < 300_000
                    else (140, "WARNING") if stars < 500_000 else (220, "CRITICAL"))
    score = max(0, min(100, (proxy-20)/180*100))
    return {"total_stars": stars, "proxy_value": proxy, "score": score,
            "state": state, "contribution": score*.30}


def make_snapshot(rows, checked_at):
    expected = {(name, repo, rid) for name, repo, rid in REPOS}
    if len(rows) != 3 or {(r["name"], r["repo"], r["expected_id"]) for r in rows} != expected:
        raise ValueError("部署工具样本名单不一致")
    validated = []
    for item in rows:
        row = dict(item)
        if not row.get("reason"):
            stars, rid = row.get("stars"), row.get("id")
            if type(stars) is not int or stars < 0:
                row["reason"] = "stars缺失或格式无效"
            elif (type(rid) is not int or rid != row["expected_id"] or
                  not isinstance(row.get("full_name"), str) or row["full_name"].lower() != row["repo"].lower()):
                row["reason"] = "返回仓库身份与固定样本不一致"
        if row.get("reason"):
            row["stars"] = None
        validated.append(row)
    coverage = sum(r["stars"] is not None for r in validated)
    available = coverage == 3
    return {"version": VERSION, "checked_at": checked_at, "rows": validated,
            "available": available, "coverage": coverage,
            "metrics": measure(sum(r["stars"] for r in validated)) if available else None,
            "scope_note": SCOPE_NOTE,
            "formula": "S=sum(3 repo stars); proxy=30/80/140/220 at S<150000/300000/500000; score=clamp((proxy-20)/180*100,0,100); weight=0.30",
            "limitation": "stars是累计开发者关注度，不是企业部署数量、活跃用户数、真实增长率或商业迁移证据；不同仓库用户可能重叠，合计不是去重人数。"}


def _fetch_repo(spec):
    name, repo, rid = spec
    row = {"name": name, "repo": repo, "expected_id": rid,
           "source_url": "https://github.com/"+repo,
           "api_url": "https://api.github.com/repos/"+repo,
           "stars": None, "reason": None}
    try:
        response = requests.get(row["api_url"], timeout=12,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "AI-risk-dashboard/1.0"})
        row["http_status"] = response.status_code
        if response.status_code != 200:
            row["reason"] = f"GitHub HTTP {response.status_code}，本次未取得"
            if response.status_code in (403, 429):
                row["reason"] += "；可能限流或访问受限，稍后独立重试"
        else:
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("仓库响应不是对象")
            row.update(id=data.get("id"), full_name=data.get("full_name"), stars=data.get("stargazers_count"),
                       forks=data.get("forks_count"), description=data.get("description"),
                       repository_updated_at=data.get("updated_at"))
    except (requests.RequestException, ValueError) as exc:
        row["reason"] = f"读取失败（{type(exc).__name__}），本次未取得"
    return row


def archive(snapshot, path=None):
    path = Path(path or STORE)
    path.parent.mkdir(parents=True, exist_ok=True)
    identity = {k: v for k, v in snapshot.items() if k != "checked_at"}
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE IF NOT EXISTS snapshots (id TEXT PRIMARY KEY, checked_at TEXT NOT NULL, payload TEXT NOT NULL)")
        db.execute("INSERT OR IGNORE INTO snapshots VALUES (?, ?, ?)",
            (key, snapshot["checked_at"], json.dumps(snapshot, ensure_ascii=False, sort_keys=True)))


def history(path=None):
    path = Path(path or STORE)
    if not path.exists():
        return []
    with sqlite3.connect(path) as db:
        return [json.loads(r[0]) for r in db.execute("SELECT payload FROM snapshots ORDER BY checked_at DESC, rowid DESC")]


@st.cache_data(ttl=3600)
def load_deployment():
    with ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(_fetch_repo, REPOS))
    result = make_snapshot(rows, datetime.now(timezone.utc).isoformat())
    archive(result)
    return result
