"""Main-text and publish-date extraction from an HTML page.

Used by both the C1 corpus builder and the C2 `fetch_url` tool, so a page reads
the same whichever way it reached the agent.

Why main-text extraction matters here: provenance grouping compares the body
text of documents. When menus, footers and "related articles" lists stay in the
text, two different articles from one site share most of their characters and
are wrongly grouped as copies (containment 0.6-0.98 was observed on real pages).

Order of preference:
- Body: Trafilatura's main-content extraction; the tag-stripping fallback is
  used when Trafilatura is missing or returns too little text.
- Date: an explicit publish-time meta tag (keeps the time of day), then
  htmldate (JSON-LD, URL, header patterns; not the article body). On
  documentation pages htmldate usually finds a "last updated" date. That is the
  date of the version fetched, so a page updated after the evidence cutoff is
  treated as after the cutoff.
"""

from __future__ import annotations

import html as html_lib
import json
import re
from dataclasses import dataclass

try:  # optional at import time so the offline core still loads without it
    import trafilatura
    from htmldate import find_date
except ImportError:  # pragma: no cover - exercised only without the dependency
    trafilatura = None
    find_date = None

#: Below this many characters a Trafilatura result is treated as a miss.
MIN_MAIN_TEXT_CHARS = 200
#: A body shorter than this is checked against the page's embedded data.
SHORT_BODY_CHARS = 1000
_NEXT_DATA_RE = re.compile(r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>', re.I | re.S)
_NEXT_F_RE = re.compile(r'self\.__next_f\.push\(\[1,\s*("(?:[^"\\]|\\.)*")\]\)', re.S)
_JSON_STRING_RE = re.compile(r'"(?:[^"\\]|\\.){40,}"', re.S)
_MARKUP_RE = re.compile(r"<(p|br|li|h[1-6]|div|span|strong|sup)\b", re.I)

_SCRIPT_STYLE_RE = re.compile(r"<(script|style|noscript)[^>]*>.*?</\1>", re.I | re.S)
_BOILERPLATE_RE = re.compile(
    r"<(head|script|style|noscript|svg|nav|header|footer|aside|form|template)\b[^>]*>.*?</\1\s*>",
    re.I | re.S)
_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
_META_RE = re.compile(r"<meta\b[^>]*>", re.I)
_ATTR_RE = re.compile(r'([a-zA-Z_:.-]+)\s*=\s*("([^"]*)"|\'([^\']*)\')')
_JSONLD_DATE_RE = re.compile(r'"datePublished"\s*:\s*"([^"]+)"')
_CHARSET_RE = re.compile(rb"<meta[^>]+charset\s*=\s*[\"']?([A-Za-z0-9_-]+)", re.I)
_TIME_RE = re.compile(r"<time\b[^>]*\bdatetime\s*=\s*[\"']([^\"']+)[\"']", re.I)

PUBLISHED_META = ("article:published_time", "og:published_time", "datepublished",
                  "pubdate", "publishdate", "date", "dc.date", "dc.date.issued",
                  "citation_publication_date", "citation_date")
TITLE_META = ("og:title", "twitter:title", "citation_title")


@dataclass
class Article:
    title: str
    text: str
    published_at: str | None = None
    #: "trafilatura", "strip" or "page_data" - which body extractor produced `text`.
    method: str = "strip"
    #: "meta" (a publish-time tag) or "htmldate" (inferred; on documentation
    #: pages this is often a "last updated" date) or None.
    date_source: str | None = None


def decode_body(body: bytes, content_type: str) -> str:
    """Bytes to text: the HTTP charset, then a <meta charset>, then UTF-8."""
    charset = None
    m = re.search(r"charset=([A-Za-z0-9_-]+)", content_type)
    if m:
        charset = m.group(1)
    else:
        m2 = _CHARSET_RE.search(body[:4096])
        if m2:
            charset = m2.group(1).decode("ascii", "ignore")
    for enc in (charset, "utf-8"):
        if not enc:
            continue
        try:
            return body.decode(enc)
        except (LookupError, UnicodeDecodeError):
            continue
    return body.decode("utf-8", errors="replace")


def strip_html(raw_html: str) -> str:
    """Remove scripts and tags; collapse whitespace."""
    cleaned = _SCRIPT_STYLE_RE.sub(" ", raw_html or "")
    cleaned = _TAG_RE.sub(" ", cleaned)
    cleaned = html_lib.unescape(cleaned)
    return _WS_RE.sub(" ", cleaned).strip()


def meta_tags(raw: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for tag in _META_RE.findall(raw):
        attrs = {k.lower(): (v1 if v1 else v2) for k, _, v1, v2 in _ATTR_RE.findall(tag)}
        key = (attrs.get("property") or attrs.get("name") or attrs.get("itemprop") or "").lower()
        if key and "content" in attrs and key not in out:
            out[key] = html_lib.unescape(attrs["content"]).strip()
    return out


def _explicit_date(raw: str, meta: dict[str, str]) -> str | None:
    published = next((meta[k] for k in PUBLISHED_META if meta.get(k)), None)
    if not published:
        m = _JSONLD_DATE_RE.search(raw) or _TIME_RE.search(raw)
        published = m.group(1) if m else None
    return published


def _strip_boilerplate(raw: str) -> str:
    body = _COMMENT_RE.sub(" ", raw)
    body = _BOILERPLATE_RE.sub(" ", body)
    return strip_html(body)


def _main_text(raw: str, url: str | None) -> str | None:
    if trafilatura is None:
        return None
    try:
        text = trafilatura.extract(raw, url=url, include_comments=False, include_tables=True,
                                   deduplicate=True, with_metadata=False)
    except Exception:  # a parser failure on one page falls back, never aborts
        return None
    if not text:
        return None
    text = _WS_RE.sub(" ", text).strip()
    return text if len(text) >= MIN_MAIN_TEXT_CHARS else None


def _found_date(raw: str, url: str | None) -> str | None:
    if find_date is None:
        return None
    try:
        # extensive_search would also scan the body, where an article's *event*
        # date (e.g. "on 12 March") could be taken for its publish date.
        return find_date(raw, url=url, original_date=True, extensive_search=False)
    except Exception:
        return None


def _page_data_text(raw: str) -> str | None:
    """Readable text from a Next.js page's embedded data.

    Some sites ship the article only in script data and render it in the
    browser, so the HTML body holds the menu alone (exp-005 FC021: Nintendo
    Korea's press release, 395 characters of navigation, no price). Two forms
    are read: the `__NEXT_DATA__` JSON (pages router) and the
    `self.__next_f.push([1, "..."])` stream (app router). Rich-text fields -
    strings carrying HTML markup - are collected in document order and their
    tags removed; ids, URLs and class names are left out.
    """
    sources: list[str] = []
    m = _NEXT_DATA_RE.search(raw)
    if m:
        sources.append(m.group(1))
    for chunk in _NEXT_F_RE.finditer(raw):
        try:
            sources.append(json.loads(chunk.group(1)))
        except ValueError:
            continue
    if not sources:
        return None
    seen, parts = set(), []
    for literal in _JSON_STRING_RE.finditer("\n".join(sources)):
        try:
            value = json.loads(literal.group(0))
        except ValueError:
            continue
        if not isinstance(value, str) or not _MARKUP_RE.search(value):
            continue
        text = strip_html(value)
        if len(text) >= 20 and " " in text and text not in seen:
            seen.add(text)
            parts.append(text)
    return "\n".join(parts) if parts else None


def extract_article(raw: str, url: str | None = None) -> Article:
    meta = meta_tags(raw)
    title = next((meta[k] for k in TITLE_META if meta.get(k)), "")
    if not title:
        m = _TITLE_RE.search(raw)
        title = strip_html(m.group(1)) if m else ""
    published, date_source = _explicit_date(raw, meta), "meta"
    if not published:
        published, date_source = _found_date(raw, url), "htmldate"
    date_source = date_source if published else None
    main = _main_text(raw, url)
    article = (Article(title, main, published, "trafilatura", date_source) if main is not None
               else Article(title, _strip_boilerplate(raw), published, "strip", date_source))
    if len(article.text) < SHORT_BODY_CHARS:
        data_text = _page_data_text(raw)
        if data_text and len(data_text) > 2 * len(article.text):
            return Article(title, data_text, published, "page_data", date_source)
    return article
