"""Offline demo: fictional companies and events, a fake web, and a scripted agent.

SYNTHETIC. Every organisation, page and event here is invented (".example"
domains) and written for this demo; no real article text is used. Dates are
relative to today so the demo always shows upcoming events.

Five cases, one per policy outcome:
  NOVA     official page confirms the claimed KST time        -> auto_added
  PIXEL    claim drops the time zone; official CET time        -> auto_added (corrected)
  STARFALL release date only in two copies of one article;
           the official page is empty (JS-rendered)           -> pending_approval (one source group)
  ORBIT    rumour only                                         -> tracking
  QUASAR   time only in an undated search snippet              -> pending_approval (RW10 failure)
"""

from __future__ import annotations

import json
import time
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from assistant.llm import ChatReply, ScriptedClient, ToolCall

KST = ZoneInfo("Asia/Seoul")
DEMO_DOMAINS = {"tech": ["novalabs.example", "orbitmobile.example", "quasar.example"],
                "game": ["pixelforge.example", "stellargames.example"]}


def _en(d: date) -> str:
    return f"{d:%B} {d.day}, {d.year}"


def _ko(d: date) -> str:
    return f"{d.month}월 {d.day}일"


def _at(d: date, hour: int, zone: str) -> datetime:
    return datetime(d.year, d.month, d.day, hour, 0, tzinfo=ZoneInfo(zone))


def build(today: date | None = None) -> dict:
    """Pages, search results and the agent script, all dated from `today`."""
    t = today or datetime.now(KST).date()
    pub = lambda n: (t - timedelta(days=n)).isoformat()   # noqa: E731

    nova_day = t + timedelta(days=15)
    nova = _at(nova_day, 10, "America/Los_Angeles")
    nova_kst = nova.astimezone(KST)
    pixel_day = t + timedelta(days=9)
    pixel = _at(pixel_day, 15, "Europe/Paris")
    pixel_kst = pixel.astimezone(KST)
    star_day = t + timedelta(days=60)
    orbit_day = t + timedelta(days=40)
    quasar_day = t + timedelta(days=20)

    pages = {
        "https://novalabs.example/newsroom/horizon-keynote": {
            "title": "Nova Labs announces Horizon keynote",
            "published_at": pub(2),
            "text": (f"Nova Labs today announced its Horizon keynote. The event will be streamed live on "
                     f"{_en(nova_day)} at {nova:%-I} a.m. {nova.tzname()} from the Nova campus. "
                     "The company will introduce its next generation of devices. " * 2)},
        "https://technews.example/nova-horizon-kst": {
            "title": "노바랩스 호라이즌 키노트 한국시간 안내",
            "published_at": pub(1),
            "text": (f"노바랩스가 호라이즌 키노트를 연다. 한국시간으로 {_ko(nova_kst.date())} 오전 {nova_kst:%-I}시에 "
                     "시작한다고 회사가 밝혔다. 신제품 공개가 예상된다. " * 2)},
        "https://pixelforge.example/news/showcase": {
            "title": "Pixel Forge Showcase returns",
            "published_at": pub(3),
            "text": (f"The Pixel Forge Showcase airs on {_en(pixel_day)} at {pixel:%-I} p.m. {pixel.tzname()}. "
                     "Expect around forty minutes of announcements from our studios. " * 2)},
        "https://gameblog.example/pixel-forge-showcase": {
            "title": "픽셀포지 쇼케이스 일정 정리",
            "published_at": pub(2),
            "text": (f"픽셀포지 쇼케이스가 {_ko(pixel_day)} 오후 {pixel:%-I}시에 방송된다. "
                     "신작 발표가 이어질 예정이다. " * 2)},
        "https://stellargames.example/starfall": {"title": "Starfall", "published_at": None, "text": ""},
        "https://gamenews-a.example/starfall-date": {
            "title": "Starfall release date revealed",
            "published_at": pub(4),
            "text": (f"Stellar Games said Starfall will launch on {_en(star_day)} for consoles and PC. "
                     "Pre-orders open later this month according to the studio announcement. " * 3)},
        "https://gamenews-b.example/starfall": {
            "title": "Starfall launches soon",
            "published_at": pub(4),
            "text": (f"Stellar Games said Starfall will launch on {_en(star_day)} for consoles and PC. "
                     "Pre-orders open later this month according to the studio announcement. " * 3)},
        "https://rumor.example/orbit-unpacked": {
            "title": "오르빗 언팩, 다음 달 열릴 듯",
            "published_at": pub(1),
            "text": (f"업계에 따르면 오르빗모바일은 {_ko(orbit_day)} 언팩 행사를 열 것으로 보인다. "
                     "회사는 아직 일정을 공식 발표하지 않았다. " * 2)},
        "https://devblog.example/quasar-devday": {
            "title": "Quasar DevDay is coming",
            "published_at": pub(2),
            "text": (f"Quasar DevDay is coming on {_en(quasar_day)}! The agenda is not out yet, "
                     "but we expect sessions on the new SDK. " * 2)},
    }
    results = {
        "tech": [
            {"title": "노바랩스 호라이즌 키노트 한국시간 안내", "url": "https://technews.example/nova-horizon-kst",
             "snippet": f"한국시간 {_ko(nova_kst.date())} 오전 {nova_kst:%-I}시 시작", "published_date": pub(1)},
            {"title": "오르빗 언팩, 다음 달 열릴 듯", "url": "https://rumor.example/orbit-unpacked",
             "snippet": f"업계에 따르면 {_ko(orbit_day)} 언팩 예상", "published_date": pub(1)},
            {"title": "Quasar DevDay is coming", "url": "https://devblog.example/quasar-devday",
             "snippet": f"Quasar DevDay on {_en(quasar_day)}", "published_date": pub(2)},
        ],
        "game": [
            {"title": "픽셀포지 쇼케이스 일정 정리", "url": "https://gameblog.example/pixel-forge-showcase",
             "snippet": f"{_ko(pixel_day)} 오후 {pixel:%-I}시 방송", "published_date": pub(2)},
            {"title": "Starfall release date revealed", "url": "https://gamenews-a.example/starfall-date",
             "snippet": f"Starfall will launch on {_en(star_day)}", "published_date": pub(4)},
        ],
        "nova": [{"title": "Nova Labs announces Horizon keynote",
                  "url": "https://novalabs.example/newsroom/horizon-keynote",
                  "snippet": f"{_en(nova_day)} at {nova:%-I} a.m. {nova.tzname()}", "published_date": pub(2)}],
        "pixel": [{"title": "Pixel Forge Showcase returns", "url": "https://pixelforge.example/news/showcase",
                   "snippet": f"{_en(pixel_day)} at {pixel:%-I} p.m. {pixel.tzname()}", "published_date": pub(3)}],
        "starfall": [
            {"title": "Starfall", "url": "https://stellargames.example/starfall", "snippet": "",
             "published_date": None},
            {"title": "Starfall launches soon", "url": "https://gamenews-b.example/starfall",
             "snippet": f"launch on {_en(star_day)}", "published_date": pub(4)}],
        "orbit": [{"title": "오르빗 언팩, 다음 달 열릴 듯", "url": "https://rumor.example/orbit-unpacked",
                   "snippet": "공식 발표 없음", "published_date": pub(1)}],
        "quasar": [{"title": "Quasar DevDay 7pm KST livestream", "url": "https://social.example/post/123",
                    "snippet": f"Quasar DevDay {_en(quasar_day)} 7 p.m. KST livestream", "published_date": None}],
    }

    nova_kst_s = nova_kst.strftime("%Y-%m-%d %H:%M")
    pixel_kst_s = pixel_kst.strftime("%Y-%m-%d %H:%M")
    candidates = {
        "tech": [
            {"name": "Nova Labs Horizon Keynote", "title_ko": "노바랩스 호라이즌 키노트",
             "claim_text": f"노바랩스 호라이즌 키노트는 한국시간 {_ko(nova_kst.date())} 오전 {nova_kst:%-I}시에 열린다.",
             "start": nova_kst_s, "tz": "Asia/Seoul", "source_url": "https://technews.example/nova-horizon-kst"},
            {"name": "Orbit Mobile Unpacked", "title_ko": "오르빗모바일 언팩",
             "claim_text": f"오르빗모바일 언팩은 {_ko(orbit_day)}에 열린다.", "start": orbit_day.isoformat(),
             "tz": None, "source_url": "https://rumor.example/orbit-unpacked"},
            {"name": "Quasar DevDay", "title_ko": "퀘이사 데브데이",
             "claim_text": f"퀘이사 데브데이는 한국시간 {_ko(quasar_day)} 오후 7시에 열린다.",
             "start": f"{quasar_day.isoformat()} 19:00", "tz": "Asia/Seoul",
             "source_url": "https://devblog.example/quasar-devday"},
        ],
        "game": [
            {"name": "Pixel Forge Showcase", "title_ko": "픽셀포지 쇼케이스",
             "claim_text": f"픽셀포지 쇼케이스는 {_ko(pixel_day)} 오후 {pixel:%-I}시에 방송된다.",
             "start": f"{pixel_day.isoformat()} {pixel:%H}:00", "tz": None,
             "source_url": "https://gameblog.example/pixel-forge-showcase"},
            {"name": "Starfall", "title_ko": "스타폴 출시",
             "claim_text": f"스텔라게임즈의 스타폴은 {_ko(star_day)} 출시된다.", "start": star_day.isoformat(),
             "tz": None, "source_url": "https://gamenews-a.example/starfall-date"},
        ],
    }

    def finish(**kw):
        base = {"abstain": False, "stop_reason": "evidence_sufficient"}
        return ("finish_verification", {**base, **kw})

    scripts = {
        "노바랩스": [
            ("search_web", {"query": "Nova Labs Horizon keynote official"}),
            ("fetch_url", {"url": "https://novalabs.example/newsroom/horizon-keynote"}),
            ("calculate_comparison", {"op": "tz_convert", "time": nova.strftime("%Y-%m-%d %H:%M"),
                                      "from_tz": "America/Los_Angeles", "to_tz": "KST"}),
            finish(verdict="supported", cited_evidence_ids=["https://novalabs.example/newsroom/horizon-keynote"],
                   justification=f"공식 뉴스룸: {_en(nova_day)} {nova:%-I} a.m. {nova.tzname()} = {nova_kst_s} KST",
                   distortion_type="none", event_start_kst=nova_kst_s),
        ],
        "픽셀포지": [
            ("search_web", {"query": "Pixel Forge Showcase official time"}),
            ("fetch_url", {"url": "https://pixelforge.example/news/showcase"}),
            ("calculate_comparison", {"op": "tz_convert", "time": pixel.strftime("%Y-%m-%d %H:%M"),
                                      "from_tz": "Europe/Paris", "to_tz": "KST"}),
            finish(verdict="refuted", cited_evidence_ids=["https://pixelforge.example/news/showcase"],
                   justification=f"공식 시각은 파리 기준 오후 {pixel:%-I}시({pixel.tzname()})다. 기사는 시간대를 빼고 썼다.",
                   correction=f"한국시간 {pixel_kst_s}", distortion_type="timezone_or_date_error",
                   event_start_kst=pixel_kst_s),
        ],
        "스타폴": [
            ("search_web", {"query": "Starfall release date Stellar Games official"}),
            ("fetch_url", {"url": "https://stellargames.example/starfall"}),
            ("fetch_url", {"url": "https://gamenews-a.example/starfall-date"}),
            ("fetch_url", {"url": "https://gamenews-b.example/starfall"}),
            finish(verdict="supported", cited_evidence_ids=["https://gamenews-a.example/starfall-date",
                                                            "https://gamenews-b.example/starfall"],
                   justification="공식 페이지 본문이 비어 있어, 두 기사로 출시일을 확인했다.",
                   distortion_type="none", event_start_kst=star_day.isoformat()),
        ],
        "오르빗": [
            ("search_web", {"query": "Orbit Mobile Unpacked official invitation"}),
            ("fetch_url", {"url": "https://rumor.example/orbit-unpacked"}),
            finish(verdict="not_enough_evidence", abstain=True,
                   cited_evidence_ids=["https://rumor.example/orbit-unpacked"],
                   justification="업계 전망 기사뿐이고 공식 초대장이 없다.", stop_reason="no_further_tools_helpful",
                   distortion_type="forecast_as_fact"),
        ],
        "퀘이사": [
            ("search_web", {"query": "Quasar DevDay time"}),
            ("fetch_url", {"url": "https://devblog.example/quasar-devday"}),
            finish(verdict="supported", cited_evidence_ids=["https://devblog.example/quasar-devday"],
                   justification="블로그에 날짜가 있고, 시각은 검색 결과의 게시물에 7 p.m. KST로 나온다.",
                   distortion_type="none", event_start_kst=f"{quasar_day.isoformat()} 19:00"),
        ],
    }
    return {"pages": pages, "results": results, "candidates": candidates, "scripts": scripts}


class DemoWeb:
    """search/fetch over the fixtures, shaped like task_a.web.LiveWebProvider."""

    def __init__(self, data: dict) -> None:
        self.data = data

    def search(self, query: str, top_k: int = 5, end_date: str | None = None) -> list[dict]:
        q = query.lower()
        for key in ("nova", "pixel", "starfall", "orbit", "quasar"):
            if key in q:
                return self.data["results"][key][:top_k]
        topic = "game" if "game" in q else "tech"
        return self.data["results"][topic][:top_k]

    def fetch(self, url: str) -> dict:
        page = self.data["pages"].get(url)
        if page is None:
            raise OSError("demo: 없는 페이지")
        return {"text": page["text"], "title": page["title"], "published_at": page["published_at"],
                "date_source": "meta", "extractor": "demo", "fetched_url": url}


def demo_client(data: dict, delay_s: float = 0.0) -> ScriptedClient:
    """A scripted agent that follows each case's tool sequence."""

    def responder(messages, tools, json_mode) -> ChatReply:
        if delay_s:
            time.sleep(delay_s)
        if json_mode:
            topic = "game" if "게임" in messages[0]["content"] else "tech"
            return ChatReply(content=json.dumps({"events": data["candidates"][topic]}, ensure_ascii=False))
        claim = messages[1]["content"]
        script = next((s for k, s in data["scripts"].items() if k in claim), None)
        if script is None:
            return ChatReply(content="", tool_calls=[ToolCall("x", "finish_verification", {
                "verdict": "not_enough_evidence", "abstain": True, "cited_evidence_ids": [],
                "justification": "시연 대본 없음", "stop_reason": "no_further_tools_helpful"})])
        done = sum(1 for m in messages if m.get("role") == "tool")
        name, args = script[min(done, len(script) - 1)]
        thought = {0: "공식 출처를 먼저 찾아볼게요."}.get(done, "")
        return ChatReply(content=thought, tool_calls=[ToolCall(f"call_{done}", name, args)])

    return ScriptedClient(responder, model="demo-scripted")


def demo_settings(settings: dict) -> dict:
    """Default settings with the demo's fictional official domains and topic queries."""
    out = json.loads(json.dumps(settings))
    for interest in out["interests"]:
        interest["official_domains"] = DEMO_DOMAINS.get(interest["id"], []) + interest["official_domains"]
        interest["queries"] = (["game showcase release date announced"] if interest["id"] == "game"
                               else ["tech event date announced"])
    return out
