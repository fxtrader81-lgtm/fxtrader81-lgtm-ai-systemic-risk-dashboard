"""Reviewed full-task, three-company comparison. Remote JS is parsed, never run."""
from __future__ import annotations

import ast
import csv
from datetime import date, datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess

import requests

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "config" / "capability_platforms.json"
SEED = ROOT / "config" / "capability_full_baseline.json"
REPO = "https://github.com/LiveBench/new-livebench.git"
RAW_ROOT = "https://raw.githubusercontent.com/LiveBench/new-livebench/"
VERSION = "livebench-all-tasks-top3-relative-v2"
RULE = "当期全部测试列等权相加；每公司选一个完整型号/档位最高总分；美国闭源、中国开放权重各取前三家公司；分别平均后算相对差距"


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class LiteralReader:
    """Small non-executing parser for JS data literals, not a JavaScript runtime."""
    token = re.compile(r'''\s+|//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[A-Za-z_$][\w$]*|-?\d+(?:\.\d+)?|[{}\[\]:,]''')

    def __init__(self, text):
        self.text, self.pos = text, 0

    def next(self):
        while True:
            match = self.token.match(self.text, self.pos)
            if not match:
                raise ValueError("来源元数据不是可解析的数据字面量，需核验")
            self.pos = match.end()
            token = match.group()
            if token.isspace() or token.startswith(("//", "/*")):
                continue
            return token

    def value(self, token=None, depth=0):
        if depth > 20:
            raise ValueError("来源元数据嵌套过深")
        token = self.next() if token is None else token
        if token in ("{", "["):
            result = {} if token == "{" else []
            close = "}" if token == "{" else "]"
            next_token = self.next()
            while next_token != close:
                if isinstance(result, dict):
                    key = self.value(next_token, depth+1) if next_token.startswith(('"', "'")) else next_token
                    if not isinstance(key, str) or key in result or self.next() != ":":
                        raise ValueError("来源元数据键重复或格式变化")
                    result[key] = self.value(depth=depth+1)
                else:
                    result.append(self.value(next_token, depth+1))
                sep = self.next()
                if sep == close:
                    break
                if sep != ",":
                    raise ValueError("来源元数据结构变化")
                next_token = self.next()
            return result
        if token.startswith('"'):
            return json.loads(token)
        if token.startswith("'"):
            return ast.literal_eval(token)
        if token in ("true", "false", "null"):
            return {"true": True, "false": False, "null": None}[token]
        if re.fullmatch(r"-?\d+(?:\.\d+)?", token):
            return float(token)
        raise ValueError("来源包含非数据表达式，不执行远程代码")


def parse_metadata(text):
    match = re.search(r"export\s+const\s+modelLinks\s*=\s*", text)
    if not match:
        raise ValueError("找不到公开模型元数据")
    data = LiteralReader(text[match.end():]).value()
    if not isinstance(data, dict):
        raise ValueError("模型元数据不是映射")
    expanded = {}
    for model, item in data.items():
        if not isinstance(item, dict):
            raise ValueError("模型元数据格式变化")
        expanded[model] = {k: item[k] for k in (
            "organization", "displayName", "version", "openweight", "huggingface", "url", "finetune") if k in item}
    for model, item in data.items():
        for variant in item.get("variants", []):
            name = variant.get("rawName")
            if not isinstance(name, str) or name in expanded:
                raise ValueError("模型档位重复或标识缺失")
            expanded[name] = {**expanded[model], **{k: v for k, v in variant.items() if k != "rawName"}}
    return expanded


def parse_full_csv(text):
    from core.capability_gap import _number
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    fields = reader.fieldnames or []
    if not fields or fields[0] != "model" or len(fields) != len(set(fields)) or len(fields) < 2:
        raise ValueError("CSV字段重复、缺失或格式变化")
    tasks, rows, seen = fields[1:], [], set()
    for row in reader:
        model = row.get("model")
        if not model or model in seen or None in row:
            raise ValueError("CSV模型重复、缺失或行列数错误")
        seen.add(model)
        scores, missing = {}, []
        for task in tasks:
            try:
                scores[task] = _number(row[task])
            except (TypeError, ValueError, KeyError):
                missing.append(task)
        rows.append({"model": model, "scores": scores, "missing": missing})
    if not rows:
        raise ValueError("CSV没有模型成绩")
    return tasks, rows


def select_cohorts(tasks, rows, metadata, policy):
    ranked, excluded = {"closed": {}, "open": {}}, []
    for row in rows:
        model, why = row["model"], None
        info = metadata.get(model)
        org = policy["platforms"].get(info.get("organization")) if info else None
        side = None
        if not info or not org:
            why = "平台或国别待核验"
        elif row["missing"]:
            why = "缺失/无效测试成绩：" + ", ".join(row["missing"])
        elif org["country"] == "CN" and info.get("openweight") is True:
            side = "open"
        elif (org["country"] == "US" and info.get("openweight") is not True
              and re.fullmatch(org.get("closed_pattern", r"(?!)"), model)):
            side = "closed"
        else:
            why = "不符合美国闭源／中国开放权重分组（或开放方式待核验）"
        if why:
            excluded.append({"model": model, "reason": why})
            continue
        entry = {**row, "company": org["company"], "country": org["country"],
                 "openness": "closed" if side == "closed" else "openweight",
                 "total": sum(row["scores"][t] for t in tasks), "metadata": info,
                 "classification_source": org["source"]}
        company = entry["company"]
        previous = ranked[side].get(company)
        # Full-row maximum, deterministic identity tie-break; never mix subtask winners.
        if previous is None or (-entry["total"], model) < (-previous["total"], previous["model"]):
            ranked[side][company] = entry
    output = {}
    for side, values in ranked.items():
        output[side] = sorted(values.values(), key=lambda v: (-v["total"], v["company"], v["model"]))
        if len(output[side]) < 3:
            raise ValueError(f"{'美国闭源' if side == 'closed' else '中国开放权重'}不足三家完整平台，保留上次有效结果")
    return output, excluded


def make_full_snapshot(csv_text, metadata_text, categories, *, revision, release, checked_at, policy=None):
    from core.capability_gap import relative_metrics
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("未能锁定Git提交版本")
    date.fromisoformat(release)
    tasks, rows = parse_full_csv(csv_text)
    if (not isinstance(categories, dict) or not categories or
            not all(isinstance(v, list) for v in categories.values())):
        raise ValueError("测试分类元数据格式异常")
    described = [t for values in categories.values() for t in values]
    if len(set(described)) != len(described) or set(described) != set(tasks):
        raise ValueError("CSV列与官方测试项分类不一致，不把未知列当成绩求和")
    policy = policy or json.loads(POLICY.read_text(encoding="utf-8"))
    metadata = parse_metadata(metadata_text)
    ranking, excluded = select_cohorts(tasks, rows, metadata, policy)
    closed, opened = ranking["closed"][:3], ranking["open"][:3]
    metrics = relative_metrics(sum(e["total"] for e in closed)/3, sum(e["total"] for e in opened)/3)
    metrics["difference_points"] = metrics.pop("difference_pp")
    filename = "table_" + release.replace("-", "_") + ".csv"
    return {"formula_version": VERSION, "rule": RULE, "source": "LiveBench官方原始成绩／本项目全任务等权口径",
            "release": release, "revision": revision, "checked_at": checked_at, "model_evaluated_at": None,
            "source_url": RAW_ROOT + revision + "/public/" + filename,
            "source_page": "https://github.com/LiveBench/new-livebench/blob/"+revision+"/public/"+filename,
            "source_sha256": digest(csv_text), "metadata_sha256": digest(metadata_text),
            "policy_sha256": digest(json.dumps(policy, sort_keys=True)), "policy": policy,
            "tasks": tasks, "task_count": len(tasks), "raw_csv": csv_text,
            "raw_metadata": metadata_text, "categories": categories,
            "rankings": ranking, "selected": {"closed": closed, "open": opened},
            "excluded": excluded, "row_count": len(rows), "metrics": metrics,
            "closed_model": "美国闭源前三平台", "open_model": "中国开放权重前三平台",
            "caveat": "同代指同一评测版本、同一读取截止；不声称发布日期相同。按测试总分选各平台最高完整型号/档位，不保证最新型号。不是官方综合分，不等于整体国家能力或实际商业替代。跨版本题目可能变化。"}


def resolve_revision():
    result = subprocess.run(["git", "ls-remote", REPO, "refs/heads/main"],
                            capture_output=True, text=True, check=True, timeout=20)
    revision = result.stdout.split()[0] if result.stdout.split() else ""
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("无法锁定公开仓库提交")
    return revision


def _read(revision, path):
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("无效提交")
    response = requests.get(RAW_ROOT+revision+"/"+path, timeout=15, stream=True,
                            headers={"Cache-Control": "no-cache"})
    try:
        response.raise_for_status()
        pieces, size = [], 0
        for chunk in response.iter_content(65536):
            size += len(chunk)
            if size > 2_000_000:
                raise ValueError("来源文件超过大小限制")
            pieces.append(chunk)
        return b"".join(pieces).decode("utf-8-sig")
    finally:
        response.close()


def fetch_latest_snapshot():
    revision = resolve_revision()
    constants = _read(revision, "src/lib/constants.js")
    match = re.search(r"export\s+const\s+RELEASES\s*=\s*\[([\s\S]*?)\]", constants)
    if not match:
        raise ValueError("评测版本清单格式变化")
    releases = re.findall(r'["\'](\d{4}-\d{2}-\d{2})["\']', match[1])
    today = datetime.now(timezone.utc).date()
    releases = [r for r in releases if date.fromisoformat(r) <= today]
    if not releases:
        raise ValueError("没有有效公开评测版本")
    release = max(releases)
    suffix = release.replace("-", "_")
    csv_text = _read(revision, f"public/table_{suffix}.csv")
    metadata = _read(revision, "src/Table/modelLinks.js")
    categories = json.loads(_read(revision, f"public/categories_{suffix}.json"))
    return make_full_snapshot(csv_text, metadata, categories, revision=revision, release=release,
                              checked_at=datetime.now(timezone.utc).isoformat())


def validate_snapshot(snapshot):
    return make_full_snapshot(snapshot["raw_csv"], snapshot["raw_metadata"], snapshot["categories"],
        revision=snapshot["revision"], release=snapshot["release"], checked_at=snapshot["checked_at"], policy=snapshot["policy"])


def fingerprint(snapshot):
    return digest(json.dumps({k: snapshot[k] for k in
        ("formula_version", "release", "source_sha256", "metadata_sha256", "policy_sha256")}, sort_keys=True))


def describe_change(previous, current):
    if previous.get("formula_version") != VERSION:
        return ["方法换代：由旧三任务/单模型对比改为全任务/三平台；不能把分数变化解释为能力改善或恶化。"]
    notes = []
    if previous["release"] != current["release"]:
        notes.append(f"评测版本：{previous['release']} → {current['release']}，题目或配置可能变化。")
    added, removed = set(current["tasks"])-set(previous["tasks"]), set(previous["tasks"])-set(current["tasks"])
    if added or removed:
        notes.append("任务变化：新增 "+(", ".join(sorted(added)) or "无")+"；移除 "+(", ".join(sorted(removed)) or "无"))
    for side in ("closed", "open"):
        before = {r["company"]: r for r in previous["selected"][side]}
        after = {r["company"]: r for r in current["selected"][side]}
        for company in sorted(before.keys() | after.keys()):
            if company not in before:
                notes.append(f"{company}进入前三，型号{after[company]['model']}。")
            elif company not in after:
                notes.append(f"{company}退出前三。")
            elif before[company]["model"] != after[company]["model"]:
                notes.append(f"{company}入选型号：{before[company]['model']} → {after[company]['model']}。")
            elif before[company]["total"] != after[company]["total"]:
                notes.append(f"{company}总分：{before[company]['total']:.3f} → {after[company]['total']:.3f}；需结合评测版本判断。")
    return notes or ["入选平台、型号和总分未变；来源其他记录或分类资料有更新。"]
