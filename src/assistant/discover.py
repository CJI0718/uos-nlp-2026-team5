"""Find candidate events: web search per interest, then LLM extraction to JSON.

Extraction only proposes claims; nothing found here reaches the schedule
without verification. Candidates whose source URL was not in the search
results, whose date is malformed or already past, are dropped.
"""

from __future__ import annotations

import inspect
import json
import re
from datetime import date, timedelta
from typing import Callable
from zoneinfo import ZoneInfo

from assistant.budget import Budget
from assistant.llm import ChatClient
from assistant.verify import Candidate

_START = re.compile(r"^\d{4}-\d{2}-\d{2}( \d{2}:\d{2})?$")
MAX_SNIPPET_CHARS = 500

EXTRACT_SYSTEM = """너는 웹 검색 결과에서 앞으로 열릴 행사·발표·쇼케이스·출시 일정을 찾는다. JSON만 출력한다.
형식: {{"events": [{{"name": "공식 행사명(원문 표기, 예: Nintendo Direct)", "title_ko": "한국어 제목",
"claim_text": "그 결과가 말하는 일정 주장 한 문장(한국어, 날짜·시각·시간대 포함)",
"start": "YYYY-MM-DD" 또는 "YYYY-MM-DD HH:MM" (결과에 적힌 현지 시각 그대로),
"tz": "IANA 시간대(예: America/Los_Angeles)" 또는 null, "source_url": "그 결과의 url"}}]}}
규칙: 결과에 날짜가 적힌 일정만 뽑는다. 오늘({today}) 이전 일정은 뺀다. 추측하거나 계산해서 바꾸지 않는다.
같은 행사는 한 번만. 최대 {limit}개. 관심 분야: {interest}."""


Emit = Callable[..., None]


def fill_query(template: str, today: str) -> str:
    """Fill {month} {next_month} {year} {next_year} with English month names."""
    d = date.fromisoformat(today)
    nxt = (d.replace(day=1) + timedelta(days=32)).replace(day=1)
    return template.format(month=d.strftime("%B"), next_month=nxt.strftime("%B"),
                           year=d.year, next_year=d.year + 1)


def search_interest(web, interest: dict, budget: Budget, emit: Emit, per_interest: int,
                    today: str, recent_days: int = 21) -> list[dict]:
    results, seen = [], set()
    since = (date.fromisoformat(today) - timedelta(days=recent_days)).isoformat()
    takes_start = "start_date" in inspect.signature(web.search).parameters
    for template in interest["queries"][:per_interest]:
        query = fill_query(template, today)
        budget.check_search()
        try:
            hits = web.search(query, top_k=6, **({"start_date": since} if takes_start else {}))
        except Exception as exc:   # recorded, not retried
            emit("error", f"검색 실패: {query}", str(exc)[:200])
            continue
        finally:
            budget.charge_search()
        emit("search", f"찾기: {query}", f"결과 {len(hits)}건")
        for h in hits:
            if h.get("url") and h["url"] not in seen:
                seen.add(h["url"])
                results.append(h)
    return results


def extract_candidates(client: ChatClient, budget: Budget, interest: dict, results: list[dict],
                       today: str, limit: int, emit: Emit) -> list[Candidate]:
    if not results:
        return []
    view = [{"title": r.get("title", ""), "url": r["url"], "published": r.get("published_date"),
             "snippet": (r.get("snippet") or "")[:MAX_SNIPPET_CHARS]} for r in results]
    messages = [
        {"role": "system", "content": EXTRACT_SYSTEM.format(today=today, limit=limit,
                                                             interest=interest["name"])},
        {"role": "user", "content": json.dumps({"results": view}, ensure_ascii=False)},
    ]
    budget.check_llm()
    reply = client.complete(messages, json_mode=True)
    budget.charge_llm(reply.usage)
    try:
        items = json.loads(reply.content or "{}").get("events") or []
    except (json.JSONDecodeError, AttributeError):
        emit("error", "후보 추출 결과를 해석하지 못함", (reply.content or "")[:200])
        return []
    urls = {r["url"]: r for r in results}
    out, seen, dropped = [], set(), {}
    items = items if isinstance(items, list) else []
    for item in items:
        cand, why = _candidate(item, interest["id"], urls, today)
        if cand is None:
            dropped[why] = dropped.get(why, 0) + 1
            continue
        key = (cand.name.lower(), cand.start[:10])
        if key not in seen:
            seen.add(key)
            out.append(cand)
    drop_text = ", ".join(f"{DROP_KO.get(k, k)} {n}" for k, n in dropped.items())
    emit("extract", f"후보 {len(out)}건 ({interest['name']})",
         (f"모델 제안 {len(items)}건" + (f" · 제외: {drop_text}" if drop_text else "") + ". "
          + ", ".join(f"{c.title_ko} {c.start}" for c in out))[:300])
    return out[:limit]


DROP_KO = {"format": "형식 오류", "date": "날짜 형식 오류", "url": "검색 결과에 없는 주소",
           "past": "지난 일정"}


def _candidate(item, interest_id: str, urls: dict, today: str) -> tuple[Candidate | None, str]:
    if not isinstance(item, dict):
        return None, "format"
    name = str(item.get("name") or "").strip()
    start = re.sub(r"\s+", " ", str(item.get("start") or "").replace("T", " ")).strip()[:16]
    url = str(item.get("source_url") or "").strip()
    if not name:
        return None, "format"
    if not _START.match(start):
        return None, "date"
    if url not in urls:
        return None, "url"
    if start[:10] < today:
        return None, "past"
    hit = urls[url]
    tz = str(item.get("tz") or "").strip() or None
    if tz:
        try:
            ZoneInfo(tz)
        except Exception:
            tz = None   # an unknown zone name is dropped, not guessed
    return Candidate(
        interest=interest_id, name=name[:120],
        title_ko=str(item.get("title_ko") or name).strip()[:120],
        claim_text=str(item.get("claim_text") or f"{name}은 {start}에 열린다.").strip()[:500],
        start=start, tz=tz, source_url=url,
        excerpt=(hit.get("snippet") or "")[:MAX_SNIPPET_CHARS]), "ok"
