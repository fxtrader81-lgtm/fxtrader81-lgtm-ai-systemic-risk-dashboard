"""Low-frequency source inspection; never adopts unreviewed numerical inputs."""
from datetime import datetime, timedelta, timezone
from contextlib import contextmanager
from hashlib import sha256
from html.parser import HTMLParser
import json
import io
from pathlib import Path
import re
import sqlite3
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests

STORE = Path(__file__).resolve().parents[1] / ".local/infra_updates.sqlite3"
INTERVAL_DAYS = 90
SOURCES = (
    {"id": "queue", "name": "LBNL 并网排队", "url": "https://eta-publications.lbl.gov/sites/default/files/2026-06/queued_up_2026_edition.pdf",
     "marker": "queue", "cadence": "年度发布；发电/储能项目，不是数据中心接电等待时间"},
    {"id": "reserve", "name": "NERC 可靠性评估", "url": "https://www.nerc.com/globalassets/our-work/assessments/nerc_sra_2026.pdf",
     "marker": "assessment", "cadence": "夏季、冬季及长期评估分别按年发布，不能直接混用"},
    {"id": "transformer", "name": "DOE 大型电力变压器", "url": "https://www.energy.gov/oe/distribution-transformer-webinar-text-alternative",
     "marker": "transformer", "cadence": "报告/专题发布；尚未确认固定月度或季度数值序列"},
)


def _now():
    return datetime.now(timezone.utc)


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


@contextmanager
def _connect(path=None):
    path = Path(path or STORE)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.execute("CREATE TABLE IF NOT EXISTS evidence (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
    conn.execute("CREATE TABLE IF NOT EXISTS checks (id INTEGER PRIMARY KEY, started TEXT, finished TEXT, status TEXT, payload TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS baselines (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
    conn.execute("CREATE TABLE IF NOT EXISTS input_versions (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
    try:
        with conn:
            yield conn
    finally:
        conn.close()


class SourceReadError(ValueError):
    """A safe user-facing message generated locally, never arbitrary response text."""


class _Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.texts = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "nav", "footer"):
            self.skip += 1
        if tag == "a" and not self.skip:
            href = dict(attrs).get("href", "")
            if re.search(r"\.(?:pdf|xlsx?|csv)(?:[?#]|$)", href, re.I):
                self.links.append(href)

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "nav", "footer"):
            self.skip = max(0, self.skip - 1)

    def handle_data(self, data):
        if not self.skip:
            self.texts.append(data)


def fetch_source(source):
    """Inspect fixed official entry points, not a claim to exhaustive/latest data."""
    response = requests.get(source["url"], timeout=(5, 20), headers={"User-Agent": "AI-risk-dashboard source-check/1.0"})
    response.raise_for_status()
    host = urlsplit(response.url).hostname or ""
    allowed = urlsplit(source["url"]).hostname
    if host != allowed:
        raise SourceReadError("官方入口跳转到其他域名，待核验")
    if len(response.content) > (25_000_000 if source["url"].endswith(".pdf") else 4_000_000):
        raise SourceReadError("来源页面超出检查大小限制")
    page = _Page()
    if source["url"].endswith(".pdf"):
        from pypdf import PdfReader
        if not response.content.startswith(b"%PDF-"):
            raise SourceReadError("未取得PDF原始报告")
        reader = PdfReader(io.BytesIO(response.content))
        pages = [p.extract_text() or "" for p in reader.pages]
        text = "\n".join(pages)
        raw = {"pdf_sha256": sha256(response.content).hexdigest(), "pages": pages}
    else:
        page.feed(response.text)
        text = re.sub(r"\s+", " ", " ".join(page.texts)).strip()
        raw = {"raw_html": response.text}
    if len(text) < 300 or source["marker"] not in text.lower():
        raise SourceReadError("未取得可核验正文（可能是动态页面或访问限制）")
    if re.search(r"verify you are human|access denied|just a moment|captcha", text, re.I):
        raise SourceReadError("来源返回访问验证页面")
    links = []
    for link in page.links:
        parts = urlsplit(urljoin(source["url"], link))
        if parts.scheme == "https" and not parts.username and not parts.password:
            links.append(urlunsplit((parts.scheme, parts.netloc, parts.path, "", "")))
    content = {"source_id": source["id"], "url": source["url"], "text": text,
               "document_links": sorted(set(links)), "parser_version": 2}
    return dict(content, id=sha256(_json(content).encode()).hexdigest(),
                extracted=extract_numeric_evidence(source["id"], text), **raw)


def extract_numeric_evidence(source_id, text):
    """Parse auditable facts, preserving bounds and unknowns rather than choosing a score input."""
    normalized = re.sub(r"\s+", " ", text)
    if source_id == "queue":
        exact = re.search(r"median project built in (20\d{2}) took (\d+(?:\.\d+)?) months from the interconnection request to commercial operations", normalized, re.I)
        if exact:
            return {"kind":"point", "months":float(exact[2]), "period":exact[1],
                    "definition":"发电/储能项目IR至COD中位时长；不是数据中心接电等待时间，也非纯审核耗时",
                    "display":f"{float(exact[2]):g}个月（{exact[1]}年建成项目中位时长）",
                    "quote":exact[0],"score_input":None,"review":"原43月的统计定义无出处，不能假定同口径"}
        match = re.search(r"median duration from IR to COD was over (\d+(?:\.\d+)?) years for projects built in (20\d{2})", normalized, re.I)
        if match:
            return {"kind": "lower_bound", "months_gt": float(match[1])*12,
                    "period": match[2], "definition": "发电/储能项目IR至COD中位时长；不是数据中心接电等待时间",
                    "display": f"超过{float(match[1])*12:g}个月（{match[2]}年建成项目）",
                    "quote": match[0], "score_input": None, "review": "原43月的统计定义无出处，不能假定同口径"}
    if source_id == "reserve":
        rows = []
        for region in ("PJM", "Texas RE-ERCOT"):
            match = re.search(re.escape(region)+r"\s+Demand, Resource, and Reserve Margins 2025 SRA 2026 SRA(.*?)(?=Reference Margin Level)", normalized)
            if not match:
                return {"kind": "unparsed", "display": "报告字段或版本变化，待核验", "score_input": None}
            section = match[1]
            margin = re.search(r"Anticipated Reserve Margin ([\d.]+)% ([\d.]+)%", section)
            demand = re.search(r"Net Internal Demand ([\d,]+) ([\d,]+)", section)
            capacity = re.search(r"Anticipated Resources ([\d,]+) ([\d,]+)", section)
            if not all((margin, demand, capacity)):
                return {"kind": "unparsed", "display": "报告缺必要字段，待核验", "score_input": None}
            d, c = int(demand[2].replace(",", "")), int(capacity[2].replace(",", ""))
            value = float(margin[2])
            if d <= 0 or abs((c/d-1)*100-value) > .15:
                raise SourceReadError("备用裕度与资源/需求复算不符，拒绝采用")
            rows.append({"region":region,"anticipated_margin_pct":value,"net_internal_demand_mw":d,
                         "anticipated_resources_mw":c,"prior_same_report_pct":float(margin[1]),"excerpt":section.strip()})
        return {"kind":"point", "period":"2026年夏季", "definition":"Anticipated Reserve Margin；不是Reference Margin Level或晚间风险小时裕度",
                "display":f"PJM {rows[0]['anticipated_margin_pct']}% / ERCOT {rows[1]['anticipated_margin_pct']}%（2026夏季）",
                "rows":rows, "score_input":None,"review":"原16.5%/12.8%未注明季节及字段；采用前需确认统一为夏季ARM"}
    if source_id == "transformer":
        match = re.search(r"Large transformers for substations and generators have lead times growing from three to as much as four years", normalized, re.I)
        if match:
            return {"kind":"qualitative_upper_extent", "display":"大型变压器交期由3年延长，最高可达4年；不是全国均值",
                    "described_start_months":36,"described_max_months":48,"period":None,
                    "definition":"DOE研讨会发言描述；不能当成36–48月统计区间或取42月平均",
                    "quote":match[0],"score_input":None,"review":"缺单一可用统计值，需要确定采用情景还是仅作参考"}
    return {"kind":"unparsed", "display":"资料已取得，未匹配固定数值字段，待核验", "score_input":None}


def record_baseline(inputs, path=None):
    """Retain existing code inputs as legacy, not as newly verified measurements."""
    baseline = {"inputs": dict(inputs), "classification": "legacy_unverified",
                "note": "旧版代码静态值；updated是旧录入标记，不是已核验的观察期或发布日期。",
                "rule": "q=clamp((排队月数-12)/36*100); t=clamp((交期月数-12)/36*100); r=clamp((20-(PJM+ERCOT)/2)/12*100); 分项=round(q*45%+t*30%+r*25%,1); 整页权重40%"}
    key = sha256(_json(baseline).encode()).hexdigest()
    with _connect(path) as conn:
        conn.execute("INSERT OR IGNORE INTO baselines VALUES (?,?)", (key, _json(baseline)))


def history(path=None):
    with _connect(path) as conn:
        checks = [{"id": r[0], "started": r[1], "finished": r[2], "status": r[3],
                   "sources": json.loads(r[4] or "[]")} for r in conn.execute("SELECT * FROM checks ORDER BY id DESC")]
        return {"checks": checks,
                "evidence": [json.loads(r[0]) for r in conn.execute("SELECT payload FROM evidence ORDER BY rowid DESC")],
                "input_versions": [json.loads(r[0]) for r in conn.execute("SELECT payload FROM input_versions ORDER BY rowid DESC")],
                "baselines": [json.loads(r[0]) for r in conn.execute("SELECT payload FROM baselines ORDER BY rowid")]}


def reminder(records, now=None):
    now = now or _now()
    success = next((c for c in records["checks"] if c["status"] == "success"), None)
    last = datetime.fromisoformat(success["finished"]) if success else None
    due = last + timedelta(days=INTERVAL_DAYS) if last else None
    return {"last_success": last, "next_due": due, "due": due is None or now >= due}


def check_sources(path=None, fetcher=None, now=None):
    """One shared short lease prevents parallel clicks; failures remain retryable."""
    started = now or _now()
    fetcher = fetcher or fetch_source
    with _connect(path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        busy = conn.execute("SELECT started FROM checks WHERE status='running'").fetchall()
        if any(started - datetime.fromisoformat(r[0]) < timedelta(minutes=5) for r in busy):
            return {"status": "busy"}
        conn.execute("UPDATE checks SET status='interrupted', finished=? WHERE status='running'", (started.isoformat(),))
        check_id = conn.execute("INSERT INTO checks(started,status) VALUES (?, 'running')", (started.isoformat(),)).lastrowid
    rows, evidence = [], []
    try:
        for source in SOURCES:
            try:
                item = fetcher(source)
                # Reject incomplete/custom fetcher results before recording success.
                expected = sha256(_json({k: item[k] for k in ("source_id", "url", "text", "document_links", "parser_version")}).encode()).hexdigest()
                if item["id"] != expected or item["source_id"] != source["id"] or item["url"] != source["url"]:
                    raise ValueError("来源证据标识不匹配")
                evidence.append(item)
                rows.append({"source_id": source["id"], "status": "ok", "evidence_id": item["id"]})
            except Exception as exc:
                # Do not expose request URLs/headers or other potentially sensitive exception content.
                if isinstance(exc, SourceReadError):
                    reason = str(exc)
                elif isinstance(exc, requests.HTTPError) and exc.response is not None:
                    reason = f"来源返回 HTTP {exc.response.status_code}"
                elif isinstance(exc, requests.Timeout):
                    reason = "来源读取超时"
                elif isinstance(exc, requests.RequestException):
                    reason = "来源网络请求失败"
                else:
                    reason = "来源证据校验未通过"
                rows.append({"source_id": source["id"], "status": "failed", "error": type(exc).__name__, "reason": reason})
        status = "success" if all(r["status"] == "ok" for r in rows) else "failed"
        with _connect(path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            for item in evidence:
                previous = None
                for payload, in conn.execute("SELECT payload FROM checks WHERE id<? ORDER BY id DESC", (check_id,)):
                    previous = next((r["evidence_id"] for r in json.loads(payload or "[]")
                                     if r["source_id"] == item["source_id"] and r["status"] == "ok"), None)
                    if previous:
                        break
                row = next(r for r in rows if r["source_id"] == item["source_id"])
                row["comparison"] = "first" if not previous else "unchanged" if previous == item["id"] else "changed"
                conn.execute("INSERT OR IGNORE INTO evidence VALUES (?,?)", (item["id"], _json(item)))
            finished = (now or _now()).isoformat()
            conn.execute("UPDATE checks SET finished=?,status=?,payload=? WHERE id=?", (finished, status, _json(rows), check_id))
        return {"status": status, "sources": rows}
    except Exception:
        with _connect(path) as conn:
            conn.execute("UPDATE checks SET status='failed',finished=? WHERE id=?", ((now or _now()).isoformat(), check_id))
        raise
