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
from urllib.parse import quote, urlsplit, urlunsplit

from task_a.article import decode_body, extract_article, strip_html
from task_a.tools import check_url

USER_AGENT = "uos-nlp-team5-factcheck-agent/0.1 (academic research)"
#: Raw bytes read per page. News pages are often several hundred KB of markup.
MAX_DOWNLOAD_BYTES = 4 * 1024 * 1024
#: Extracted text kept per page; the agent pages through it with read_evidence.
MAX_PAGE_TEXT_CHARS = 100_000
_DDG_RESULT_RE = re.compile(
    r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="(?P<url>[^"]+)"[^>]*>(?P<title>.*?)</a>'
    r'(?:.*?<a[^>]+class="[^"]*result__snippet[^"]*"[^>]*>(?P<snippet>.*?)</a>)?',
    re.I | re.S,
)


#: Only these keys are taken from a .env file; nothing else is imported.
ENV_FILE_KEYS = ("TAVILY_API_KEY",)


def load_env_file(path, keys: tuple[str, ...] = ENV_FILE_KEYS) -> list[str]:
    """Set allow-listed keys from a KEY=VALUE file without overriding the environment.

    Returns the names that were set (never the values). A missing file is not
    an error: the key may come from the shell instead.
    """
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except OSError:
        return []
    loaded = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.removeprefix("export ").split("=", 1)
        name, value = name.strip(), value.strip().strip("'\"")
        if name in keys and value and not os.environ.get(name):
            os.environ[name] = value
            loaded.append(name)
    return loaded




def to_ascii_url(url: str) -> str:
    """Percent-encode non-ASCII path/query characters (e.g. Korean slugs)."""
    p = urlsplit(url)
    host = p.hostname.encode("idna").decode("ascii") if p.hostname else ""
    netloc = host + (f":{p.port}" if p.port else "")
    return urlunsplit((p.scheme, netloc, quote(p.path, safe="/%:@!$&'()*+,;=-._~"),
                       quote(p.query, safe="=&%/:+,;@!$'()*-._~"), p.fragment and ""))


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

    def search(self, query: str, top_k: int = 5, end_date: str | None = None) -> list[dict]:
        """`end_date` (YYYY-MM-DD) is passed to Tavily; DuckDuckGo has no date filter."""
        key = self.api_key or os.environ.get("TAVILY_API_KEY")
        mode = self.provider
        if mode == "auto":
            mode = "tavily" if key else "ddg"
        if mode == "tavily":
            if not key:
                raise RuntimeError("TAVILY_API_KEY 환경변수가 설정되지 않았습니다.")
            return self._search_tavily(query, top_k, key, end_date)
        if mode == "ddg":
            return self._search_ddg(query, top_k)
        raise ValueError(f"지원하지 않는 검색 provider: {self.provider!r}")

    def fetch(self, url: str) -> dict:
        """Main text, title and publish date of one page.

        HTML goes through main-content extraction so menus and footers do not
        make different articles from one site look like copies of each other.
        """
        denied = check_url(url, self.allowed_hosts)
        if denied:
            raise PermissionError(denied)
        req = urllib.request.Request(to_ascii_url(url), headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = resp.read(MAX_DOWNLOAD_BYTES)
            content_type = (resp.headers.get("Content-Type") or "").lower()
        raw = decode_body(body, content_type)
        if "html" in content_type or "<html" in raw[:2000].lower():
            art = extract_article(raw, url)
            return {"text": art.text[:MAX_PAGE_TEXT_CHARS], "title": art.title,
                    "published_at": art.published_at, "date_source": art.date_source,
                    "extractor": art.method}
        return {"text": raw[:MAX_PAGE_TEXT_CHARS], "title": "", "published_at": None,
                "extractor": "plain"}

    def _search_tavily(self, query: str, top_k: int, api_key: str,
                       end_date: str | None = None) -> list[dict]:
        body = {
            "api_key": api_key,
            "query": query,
            "max_results": max(1, min(top_k, 20)),   # Tavily's maximum; still one credit
            "include_answer": False,
            "search_depth": "basic",          # 1 credit; never upgraded automatically
            "include_published_date": True,
        }
        if end_date:
            # Undated results are kept (official pages often carry no date);
            # the tool layer drops results dated after the cutoff.
            body["end_date"] = end_date
        payload = json.dumps(body).encode("utf-8")
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
                "published_date": item.get("published_date"),
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
