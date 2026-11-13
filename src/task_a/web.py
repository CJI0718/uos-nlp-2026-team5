"""External web search and URL fetching for the C2 condition.

Supports:
1. Tavily Search API (when `TAVILY_API_KEY` is set; 1,000 free searches/month).
2. Keyless DuckDuckGo HTML fallback (when no API key is needed/set).
3. Safe HTTP/HTTPS text fetching with SSRF host validation (`check_url`) and
   HTML boilerplate stripping.

Per AGENTS.md, no live network call is made unless the caller explicitly
constructs and invokes a live C2 provider.
"""

from __future__ import annotations

import html
import json
import os
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass

from task_a.tools import MAX_FETCH_CHARS, check_url

USER_AGENT = "uos-nlp-team5-factcheck-agent/0.1 (academic research)"
_SCRIPT_STYLE_RE = re.compile(r"<(script|style|noscript)[^>]*>.*?</\1>", re.I | re.S)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_DDG_RESULT_RE = re.compile(
    r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="(?P<url>[^"]+)"[^>]*>(?P<title>.*?)</a>'
    r'(?:.*?<a[^>]+class="[^"]*result__snippet[^"]*"[^>]*>(?P<snippet>.*?)</a>)?',
    re.I | re.S,
)


def strip_html(raw_html: str) -> str:
    """Convert raw HTML into compact plain text suitable for tool observations."""
    cleaned = _SCRIPT_STYLE_RE.sub(" ", raw_html or "")
    cleaned = _TAG_RE.sub(" ", cleaned)
    cleaned = html.unescape(cleaned)
    return _WS_RE.sub(" ", cleaned).strip()


def _unwrap_ddg_url(href: str) -> str:
    parsed = urllib.parse.urlsplit(href)
    if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
        qs = urllib.parse.parse_qs(parsed.query)
        if "uddg" in qs and qs["uddg"]:
            return qs["uddg"][0]
    return href


@dataclass
class LiveWebProvider:
    """C2 WebProvider implementation with Tavily API + keyless fallback."""

    provider: str = "auto"  # "auto" | "tavily" | "ddg"
    api_key: str | None = None
    timeout: float = 15.0
    allowed_hosts: frozenset[str] | None = None

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        key = self.api_key or os.environ.get("TAVILY_API_KEY")
        mode = self.provider
        if mode == "auto":
            mode = "tavily" if key else "ddg"
        if mode == "tavily":
            if not key:
                raise RuntimeError("TAVILY_API_KEY 환경변수가 설정되지 않았습니다.")
            return self._search_tavily(query, top_k, key)
        if mode == "ddg":
            return self._search_ddg(query, top_k)
        raise ValueError(f"지원하지 않는 검색 provider: {self.provider!r}")

    def fetch(self, url: str) -> str:
        denied = check_url(url, self.allowed_hosts)
        if denied:
            raise PermissionError(denied)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            raw = resp.read(MAX_FETCH_CHARS * 8).decode("utf-8", errors="replace")
            content_type = (resp.headers.get("Content-Type") or "").lower()
        if "html" in content_type or "<html" in raw[:500].lower():
            return strip_html(raw)[:MAX_FETCH_CHARS]
        return raw[:MAX_FETCH_CHARS]

    def _search_tavily(self, query: str, top_k: int, api_key: str) -> list[dict]:
        payload = json.dumps({
            "api_key": api_key,
            "query": query,
            "max_results": max(1, min(top_k, 10)),
            "include_answer": False,
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.tavily.com/search",
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        out = []
        for item in data.get("results", [])[:top_k]:
            out.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("content", ""),
            })
        return out

    def _search_ddg(self, query: str, top_k: int) -> list[dict]:
        encoded = urllib.parse.urlencode({"q": query})
        url = f"https://html.duckduckgo.com/html/?{encoded}"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            page = resp.read().decode("utf-8", errors="replace")
        hits = []
        for match in _DDG_RESULT_RE.finditer(page):
            target_url = _unwrap_ddg_url(html.unescape(match.group("url")))
            title = strip_html(match.group("title") or "")
            snippet = strip_html(match.group("snippet") or "")
            if target_url and title:
                hits.append({"title": title, "url": target_url, "snippet": snippet})
            if len(hits) >= top_k:
                break
        return hits
