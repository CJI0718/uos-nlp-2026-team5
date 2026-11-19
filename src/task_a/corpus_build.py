"""Build the agent-visible C1 corpus from the original source documents.

The reference file `data/task_a/evidence.jsonl` is scorer-only: its rows are
human summaries with judgement phrasing and claim IDs. The agent must instead
search the original pages. This module fetches each distinct `source_url`
named there, extracts the page text, and writes three files:

    corpus_c1.jsonl            agent-visible documents (evidence_id, title, text, ...)
    corpus_c1.gold_map.jsonl   scorer-only: document id -> reference evidence / claim ids
    corpus_c1.report.json      per-URL fetch outcome, including failures

Nothing is filled in for a page that could not be fetched or yielded too
little text; it is reported as failed and left out. Document ids are a hash of
the URL, so they reveal nothing about which claim a page belongs to.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urlsplit

from task_a.article import decode_body, extract_article
from task_a.tools import check_url
from task_a.web import USER_AGENT, readable_url, to_ascii_url

MIN_TEXT_CHARS = 300
MAX_TEXT_CHARS = 100_000
MAX_DOWNLOAD_BYTES = 8 * 1024 * 1024

@dataclass
class Fetched:
    url: str
    status: str                 # "ok" or a failure code
    content_type: str = ""
    body: bytes = b""
    detail: str = ""


@dataclass
class Extracted:
    title: str
    text: str
    published_at: str | None = None
    source_type: str = "html"
    extractor: str = ""
    date_source: str | None = None


@dataclass
class BuildResult:
    corpus: list[dict] = field(default_factory=list)
    gold_map: list[dict] = field(default_factory=list)
    report: list[dict] = field(default_factory=list)


def doc_id_for(url: str) -> str:
    """Opaque, stable id. Carries no claim id and no hint of the claim."""
    return "DOC_" + hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]


# --------------------------------------------------------------------------
# Fetching
# --------------------------------------------------------------------------

def http_fetch(url: str, timeout: float = 20.0) -> Fetched:
    denied = check_url(url, None)
    if denied:
        return Fetched(url, "blocked_url", detail=denied)
    try:
        request_url = to_ascii_url(readable_url(url))
    except (UnicodeError, ValueError) as exc:
        return Fetched(url, "blocked_url", detail=f"URL 인코딩 실패: {exc}")
    req = urllib.request.Request(request_url, headers={"User-Agent": USER_AGENT,
                                               "Accept": "text/html,application/pdf,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(MAX_DOWNLOAD_BYTES)
            ctype = (resp.headers.get("Content-Type") or "").lower()
    except urllib.error.HTTPError as exc:
        return Fetched(url, "http_error", detail=f"HTTP {exc.code}")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return Fetched(url, "network_error", detail=str(getattr(exc, "reason", exc))[:200])
    except Exception as exc:  # one bad page must not abort the whole build
        return Fetched(url, "network_error", detail=f"{type(exc).__name__}: {exc}"[:200])
    return Fetched(url, "ok", ctype, body)


# --------------------------------------------------------------------------
# Extraction
# --------------------------------------------------------------------------

def extract_html(raw: str, url: str | None = None) -> Extracted:
    art = extract_article(raw, url)
    return Extracted(title=art.title, text=art.text, published_at=art.published_at,
                     extractor=art.method, date_source=art.date_source)


def extract_pdf(body: bytes) -> Extracted | None:
    if not shutil.which("pdftotext"):
        return None
    with tempfile.TemporaryDirectory() as tmp:
        src = f"{tmp}/doc.pdf"
        with open(src, "wb") as fh:
            fh.write(body)
        try:
            proc = subprocess.run(["pdftotext", "-enc", "UTF-8", src, "-"],
                                  capture_output=True, timeout=60, check=True)
        except (OSError, subprocess.SubprocessError):
            return None
    text = re.sub(r"\s+", " ", proc.stdout.decode("utf-8", errors="replace")).strip()
    first = next((ln.strip() for ln in proc.stdout.decode("utf-8", "replace").splitlines()
                  if ln.strip()), "")
    return Extracted(title=first[:200], text=text, source_type="pdf")


def extract(fetched: Fetched) -> Extracted | None:
    is_pdf = "pdf" in fetched.content_type or fetched.body[:5] == b"%PDF-"
    if is_pdf:
        return extract_pdf(fetched.body)
    raw = decode_body(fetched.body, fetched.content_type)
    if "html" in fetched.content_type or "<html" in raw[:2000].lower():
        return extract_html(raw, fetched.url)
    text = re.sub(r"\s+", " ", raw).strip()
    return Extracted(title="", text=text, source_type="text")


# --------------------------------------------------------------------------
# Building
# --------------------------------------------------------------------------

def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    v = value.strip().replace("Z", "+00:00")
    for candidate in (v, v[:10]):
        try:
            dt = datetime.fromisoformat(candidate)
        except ValueError:
            continue
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return None


def build_corpus(
    evidence_rows: Iterable[dict],
    claims: Iterable[dict],
    fetch: Callable[[str], Fetched],
    *,
    extra_urls: Iterable[str] = (),
    delay: float = 0.0,
    now: str | None = None,
) -> BuildResult:
    """Fetch each distinct URL once and return corpus, gold map and report.

    `fetch` is injected so tests never touch the network.
    """
    cutoffs = {c["claim_id"]: _parse_time(c.get("evidence_cutoff")) for c in claims}
    by_url: dict[str, dict] = {}
    for row in evidence_rows:
        url = (row.get("source_url") or "").strip()
        if not url:
            continue
        entry = by_url.setdefault(url, {"reference_evidence_ids": [], "claim_ids": []})
        entry["reference_evidence_ids"].append(row["evidence_id"])
        if row["claim_id"] not in entry["claim_ids"]:
            entry["claim_ids"].append(row["claim_id"])
    for url in extra_urls:
        url = url.strip()
        if url and not url.startswith("#"):
            by_url.setdefault(url, {"reference_evidence_ids": [], "claim_ids": []})

    retrieved_at = now or datetime.now(timezone.utc).isoformat(timespec="seconds")
    result = BuildResult()
    seen_hashes: dict[str, str] = {}
    for i, (url, entry) in enumerate(by_url.items()):
        if i and delay:
            time.sleep(delay)
        doc_id = doc_id_for(url)
        record = {"evidence_id": doc_id, "source_url": url, **entry}
        fetched = fetch(url)
        status, detail, ext = fetched.status, fetched.detail, None
        if status == "ok":
            ext = extract(fetched)
            if ext is None:
                status, detail = "extract_failed", fetched.content_type or "unknown type"
            elif len(ext.text) < MIN_TEXT_CHARS:
                status, detail = "too_short", f"{len(ext.text)} chars (동적 페이지일 수 있음)"
        if status == "ok":
            content_hash = hashlib.sha256(ext.text.encode("utf-8")).hexdigest()
            published = _parse_time(ext.published_at)
            limits = [cutoffs.get(c) for c in entry["claim_ids"] if cutoffs.get(c)]
            if published and limits and published > min(limits):
                status, detail = "after_cutoff", f"published_at {ext.published_at} ({ext.date_source})"
            elif content_hash in seen_hashes:
                status, detail = "duplicate_text", f"same text as {seen_hashes[content_hash]}"
            else:
                seen_hashes[content_hash] = doc_id
        record.update(status=status, detail=detail)
        if status == "ok":
            truncated = len(ext.text) > MAX_TEXT_CHARS
            result.corpus.append({
                "evidence_id": doc_id,
                "title": ext.title or urlsplit(url).netloc,
                "text": ext.text[:MAX_TEXT_CHARS],
                "source_url": url,
                "publisher": urlsplit(url).hostname,
                "source_type": ext.source_type,
                "published_at": ext.published_at,
                "content_hash": content_hash,
                "retrieved_at": retrieved_at,
            })
            record.update(chars=len(ext.text), truncated=truncated, extractor=ext.extractor or None)
            result.gold_map.append({k: record[k] for k in
                                    ("evidence_id", "source_url", "reference_evidence_ids", "claim_ids")})
        result.report.append(record)
    return result


def summarize(result: BuildResult, claims: Iterable[dict]) -> dict:
    """Counts per status and the claims left with no fetched source document."""
    statuses: dict[str, int] = {}
    for rec in result.report:
        statuses[rec["status"]] = statuses.get(rec["status"], 0) + 1
    covered = {c for row in result.gold_map for c in row["claim_ids"]}
    referenced = {c for rec in result.report for c in rec["claim_ids"]}
    all_claims = [c["claim_id"] for c in claims]
    return {
        "urls": len(result.report),
        "documents": len(result.corpus),
        "status_counts": dict(sorted(statuses.items())),
        "claims_with_document": len(covered),
        "claims_referenced": len(referenced),
        "claims_without_document": sorted(c for c in all_claims if c in referenced and c not in covered),
        "claims_without_reference_url": sorted(c for c in all_claims if c not in referenced),
    }


def write_outputs(result: BuildResult, summary: dict, out_path) -> dict[str, str]:
    from pathlib import Path

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    stem = out.with_suffix("")
    paths = {"corpus": out, "gold_map": Path(f"{stem}.gold_map.jsonl"),
             "report": Path(f"{stem}.report.json")}
    for key in ("corpus", "gold_map"):
        with paths[key].open("w", encoding="utf-8") as fh:
            for row in getattr(result, key):
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    paths["report"].write_text(json.dumps({"summary": summary, "urls": result.report},
                                          ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {k: str(v) for k, v in paths.items()}
