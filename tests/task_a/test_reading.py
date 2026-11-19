"""Main-text extraction and publish dates, for the corpus builder and fetch_url."""

from __future__ import annotations

from task_a.article import extract_article
from task_a.mcp_server import AgentEnvironment
from task_a.provenance import containment, shingles
from task_a.schema import write_jsonl

# Many Korean news sites mark menus and footers with plain <div>s, not <nav>/<footer>,
# so tag-name rules alone do not remove them.
NAV = ("<div class='gnb'>" + " | ".join(f"<a href='/s{i}'>섹션 메뉴 {i} 바로가기</a>" for i in range(40))
       + "</div>")
FOOTER = ("<div id='site-bottom'>" + "회사소개 광고문의 개인정보처리방침 청소년보호정책 이메일무단수집거부 "
          "서울특별시 중구 세종대로 한빛경제신문사 대표전화 02-000-0000 " * 6 + "</div>")
RELATED = ("<div class='ranking'><h3>많이 본 뉴스</h3><ul>"
           + "".join(f"<li><a href='/n{i}'>오늘의 인기 기사 제목 {i}번 바로 보기</a></li>" for i in range(20))
           + "</ul></div>")


def news_page(title: str, body: str, meta_date: str | None = None) -> str:
    meta = f'<meta property="article:published_time" content="{meta_date}">' if meta_date else ""
    paras = "".join(f"<p>{s}</p>" for s in body.split("\n"))
    return (f"<html><head><title>{title}</title>{meta}</head><body>{NAV}"
            f"<div class='content'><div class='article_body'><h1>{title}</h1>{paras}</div></div>"
            f"{RELATED}{FOOTER}</body></html>")


ARTICLE_A = ("루미엘전자가 신형 스마트폰 루미엘 S5의 사전예약을 3월 12일 오전 10시부터 받는다고 밝혔다.\n"
             "사전예약 고객에게는 저장용량 업그레이드 혜택을 제공하며, 정식 출시는 3월 21일이다.\n"
             "회사 측은 이번 모델이 6.4인치 화면과 2억 화소 카메라를 탑재했다고 설명했다.\n"
             "가격은 전작과 같은 115만 원으로 책정됐고, 색상은 검정·은색·청록 세 가지로 나온다.\n"
             "업계에서는 경쟁사 신제품 출시 일정과 겹치지 않도록 예약 시점을 앞당긴 것으로 보고 있다.")
ARTICLE_B = ("서울시는 다음 달 1일부터 시내버스 기본요금을 1,500원에서 1,650원으로 올린다고 발표했다.\n"
             "교통카드 환승 할인은 그대로 유지되며, 청소년과 어린이 요금은 동결된다.\n"
             "시는 연료비와 인건비 상승으로 운송 적자가 커졌다고 인상 배경을 설명했다.\n"
             "마을버스 요금도 같은 날 1,200원에서 1,300원으로 함께 오르며, 심야버스는 별도로 조정된다.\n"
             "시민단체는 요금 인상 전에 노선 효율화와 재정 지원 확대를 먼저 검토해야 한다고 주장했다.")


# --- main-text extraction -----------------------------------------------------

def test_menus_and_footers_are_left_out_of_the_body():
    art = extract_article(news_page("루미엘 S5 사전예약", ARTICLE_A, "2025-03-05T09:00:00+09:00"))
    assert art.method == "trafilatura"
    assert "3월 12일 오전 10시" in art.text
    assert "섹션 메뉴" not in art.text and "개인정보처리방침" not in art.text
    assert art.published_at == "2025-03-05T09:00:00+09:00" and art.date_source == "meta"


def test_two_articles_from_one_site_are_not_grouped_as_copies():
    """With menus left in, unrelated articles from one site look like reprints."""
    a, b = news_page("A", ARTICLE_A), news_page("B", ARTICLE_B)
    from task_a.article import _strip_boilerplate, strip_html

    # Tag stripping alone keeps the shared menus, footer and related list.
    assert containment(shingles(strip_html(a)), shingles(strip_html(b))) >= 0.4
    assert containment(shingles(_strip_boilerplate(a)), shingles(_strip_boilerplate(b))) >= 0.4
    assert extract_article(a).method == "trafilatura"
    # Main-text extraction leaves only the articles, which share nothing.
    assert containment(shingles(extract_article(a).text), shingles(extract_article(b).text)) < 0.1


def test_short_pages_fall_back_to_tag_stripping():
    art = extract_article("<html><body><p>짧은 공지: 3월 12일 10시.</p></body></html>")
    assert art.method == "strip" and "3월 12일 10시" in art.text


def test_date_without_a_meta_tag_is_marked_as_inferred():
    page = news_page("공지", ARTICLE_A).replace(
        "<div class='content'>", "<div class='content'><p class='date'>입력 2025-03-06 09:12</p>", 1)
    art = extract_article(page, "https://news.example/2025/03/06/notice")
    assert art.published_at and art.published_at.startswith("2025-03-0")
    assert art.date_source == "htmldate"


# --- fetch_url ----------------------------------------------------------------

LONG = "".join(f"[{i:03d}] 서론 문단입니다. " for i in range(400)) + "핵심 문장: 발표는 2025년 7월 8일 10시."


def _env(tmp_path, web=None, cutoff=None):
    claims = tmp_path / "claims.jsonl"
    claim = {"claim_id": "FC900", "text": "발표는 7월 8일 10시다."}
    if cutoff:
        claim["evidence_cutoff"] = cutoff
    write_jsonl(claims, [claim])
    corpus = tmp_path / "corpus.jsonl"
    write_jsonl(corpus, [{"evidence_id": "DOC_long", "title": "긴 문서", "text": LONG},
                         {"evidence_id": "DOC_short", "title": "짧은 문서", "text": "짧은 본문"}])
    kw = {"arm": "C2", "web_provider": web, "cache_path": tmp_path / "cache.jsonl"} if web else {}
    return AgentEnvironment(claims_path=claims, corpus_path=corpus, out_path=tmp_path / "run.jsonl",
                            missions_dir=tmp_path / "m", tokenizer="bigram", **kw)


class _Web:
    def __init__(self, pages):
        self.pages = pages
        self.fetches = 0

    def search(self, query, top_k, end_date=None):
        return []

    def fetch(self, url):
        self.fetches += 1
        return self.pages[url]


def test_pages_published_after_the_cutoff_cannot_be_read(tmp_path):
    web = _Web({"https://news.example/late": {"text": "결과 기사", "published_at": "2025-08-01",
                                              "date_source": "meta"},
                "https://docs.example/p": {"text": "문서 본문", "published_at": "2025-06-30",
                                           "date_source": "htmldate"}})
    env = _env(tmp_path, web, cutoff="2025-07-05T00:00:00+09:00")
    env.start_episode("FC900")
    late = env.call_tool("fetch_url", {"url": "https://news.example/late"})
    assert late["status"] == "blocked" and "2025-08-01" in late["observation"]
    assert "https://news.example/late" not in env.active.read_evidence_ids

    inferred = env.call_tool("fetch_url", {"url": "https://docs.example/p"})["observation"]
    assert "추정한 날짜" in inferred


def test_plain_string_providers_still_work(tmp_path):
    env = _env(tmp_path, _Web({"https://x.example/": "본문 텍스트"}))
    env.start_episode("FC900")
    res = env.call_tool("fetch_url", {"url": "https://x.example/"})
    assert res["status"] == "ok" and "본문 텍스트" in res["observation"] and "발행: 미상" in res["observation"]
