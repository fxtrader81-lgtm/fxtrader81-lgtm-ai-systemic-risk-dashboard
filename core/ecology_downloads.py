"""Downloads of the current three selected CN open-weight models, not all ecosystems."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import urlparse

import requests
import streamlit as st

from core.capability_cohort import fingerprint, parse_metadata

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / ".local" / "ecology_download_history.sqlite3"
VERSION = "capability-selected-three-hf-downloads-v1"
PUBLISHERS = {"DeepSeek": "deepseek-ai", "Alibaba": "Qwen", "Moonshot AI": "moonshotai"}
LEGACY = {
    "detail_models": ["meta-llama/Llama-3.3-70B-Instruct", "deepseek-ai/DeepSeek-V3",
                      "Qwen/Qwen2.5-72B-Instruct", "mistralai/Mistral-Large-Instruct-2411"],
    "overview_models": ["meta-llama/Llama-3.3-70B-Instruct", "deepseek-ai/DeepSeek-V3", "Qwen/Qwen2.5-72B-Instruct"],
    "rule": "下载量<500000/2000000/8000000及以上分别15/40/65/85分；权重15%。旧详情部分失败仍累加，全部失败代入30分；旧总览可用分项重加权。",
    "note": "保留旧名单和规则供追查。此前未保存的下载值、日期和分数不回填；旧四模型和新三模型存在方法断点，不作同口径改善/恶化比较。"}


def selection_request(capability):
    metadata = parse_metadata(capability["raw_metadata"])
    selected = [{"company": row["company"], "model": row["model"],
                 "huggingface": metadata.get(row["model"], {}).get("huggingface"),
                 "capability_release": capability["release"], "capability_revision": capability["revision"]}
                for row in capability["selected"]["open"]]
    if len(selected) != 3 or len({r["company"] for r in selected}) != 3:
        raise ValueError("生态样本必须来自本期三个不同开放权重平台")
    return fingerprint(capability), json.dumps(selected, sort_keys=True)


def model_repo(row):
    url = row.get("huggingface")
    if not isinstance(url, str):
        raise ValueError("本期评测资料缺少官方Hugging Face仓库，不猜测替代型号")
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "huggingface.co" or parsed.query or parsed.fragment:
        raise ValueError("模型仓库链接格式异常")
    repo = parsed.path.strip("/")
    if not re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9_.-]*/[A-Za-z0-9_-][A-Za-z0-9_.-]*", repo):
        raise ValueError("不是模型仓库主页，不读取文件、变体或衍生仓库")
    expected = PUBLISHERS.get(row["company"])
    if not expected or repo.split("/")[0].lower() != expected.lower():
        raise ValueError("平台的官方发布组织尚未核验或与仓库链接不一致")
    return repo


def measure(downloads):
    if type(downloads) is not int or downloads < 0:
        raise ValueError("下载量必须为非负整数；缺失不当作0")
    score, state = ((15,"SAFE") if downloads < 500_000 else (40,"WATCH") if downloads < 2_000_000
                    else (65,"WARNING") if downloads < 8_000_000 else (85,"CRITICAL"))
    return {"total_downloads": downloads, "score": score, "state": state, "contribution": score*.15}


def _fetch_model(item):
    row = dict(item, repo=None, source_url=item.get("huggingface"), api_url=None,
               downloads=None, reason=None, raw=None)
    try:
        row["repo"] = model_repo(item)
        row["source_url"] = "https://huggingface.co/"+row["repo"]
        row["api_url"] = "https://huggingface.co/api/models/"+row["repo"]
        response = requests.get(row["api_url"], timeout=15, headers={"User-Agent":"AI-risk-dashboard/1.0"})
        row["http_status"] = response.status_code
        if response.status_code != 200:
            row["reason"] = f"Hugging Face HTTP {response.status_code}，本次未取得"
        else:
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("模型响应不是对象")
            row["raw"] = {key:data.get(key) for key in ("id","author","downloads","likes","sha","createdAt","lastModified","gated","private")}
            row["downloads"] = data.get("downloads")
    except (requests.RequestException, ValueError) as exc:
        row["reason"] = f"{type(exc).__name__}：{str(exc)[:180]}" if isinstance(exc, ValueError) else f"取数失败（{type(exc).__name__}）"
    return row


def make_snapshot(rows, cohort_key, checked_at):
    if len(rows) != 3 or len({r["company"] for r in rows}) != 3:
        raise ValueError("生态样本不是三家不同平台")
    validated = []
    repos = []
    for item in rows:
        row = dict(item)
        if not row.get("reason"):
            try:
                repo = model_repo(row)
                raw = row.get("raw") or {}
                if row.get("repo") != repo or not isinstance(raw.get("id"),str) or raw["id"].lower() != repo.lower():
                    raise ValueError("返回模型身份与本期官方仓库不一致")
                if raw.get("author") != repo.split("/")[0] or raw.get("private") is not False:
                    raise ValueError("返回模型发布者或公开状态不符合核验条件")
                measure(raw.get("downloads"))
                row["downloads"] = raw["downloads"]
                repos.append(repo.lower())
            except ValueError as exc:
                row["reason"] = str(exc)
        if row.get("reason"):
            row["downloads"] = None
        validated.append(row)
    if len(repos) != len(set(repos)):
        raise ValueError("同一仓库不能在三个平台样本中重复计入")
    coverage = sum(r["downloads"] is not None for r in validated)
    return {"version": VERSION, "cohort_key":cohort_key, "checked_at":checked_at,
            "rows":validated, "coverage":coverage, "available":coverage==3,
            "metrics": measure(sum(r["downloads"] for r in validated)) if coverage==3 else None,
            "window":"Hugging Face downloads字段：最近30天滚动窗口，不是本季度累计或全历史累计。",
            "formula":"D=sum(3 current selected official model repo downloads); D<500000/2000000/8000000/otherwise => 15/40/65/85; weight=0.15",
            "method_break":"从旧固定四模型（旧总览三模型）改为能力代差本期入选的三家中国开放权重模型。旧阈值暂沿用、未重新校准；名单或型号变更产生方法断点，不把分数变化直接当作生态改善/恶化。",
            "limitation":"只代表入选三个确切模型仓库的下载热度，不代表整个平台生态、去重用户、成功部署量或增长速度。HF按特定文件请求计数；仓库新旧、模型体量及下载方式影响比较。相邻30天窗口可能重叠，不能相加当作季度下载量。",
            "sources":["https://huggingface.co/docs/hub/models-download-stats", "https://huggingface.co/docs/huggingface_hub/package_reference/hf_api#huggingface_hub.ModelInfo"]}


def archive(snapshot, path=None):
    path=Path(path or STORE); path.parent.mkdir(parents=True, exist_ok=True)
    identity={k:v for k,v in snapshot.items() if k!="checked_at"}
    key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE IF NOT EXISTS snapshots (id TEXT PRIMARY KEY, checked_at TEXT NOT NULL, payload TEXT NOT NULL)")
        db.execute("INSERT OR IGNORE INTO snapshots VALUES (?, ?, ?)",
                   (key,snapshot["checked_at"],json.dumps(snapshot,ensure_ascii=False,sort_keys=True)))


def history(path=None):
    path=Path(path or STORE)
    if not path.exists(): return []
    with sqlite3.connect(path) as db:
        return [json.loads(r[0]) for r in db.execute("SELECT payload FROM snapshots ORDER BY checked_at DESC, rowid DESC")]


@st.cache_data(ttl=3600)
def get_selected_downloads(cohort_key, selected_json):
    selected=json.loads(selected_json)
    with ThreadPoolExecutor(max_workers=3) as pool:
        rows=list(pool.map(_fetch_model,selected))
    result=make_snapshot(rows,cohort_key,datetime.now(timezone.utc).isoformat())
    archive(result)
    return result


def load_ecology(capability):
    key,selected=selection_request(capability)
    return get_selected_downloads(key,selected)
