"""Deterministic checks on a final verdict (harness v3).

exp-011 left five wrong verdicts; three were forecast claims judged from
forecast reports (FC017 supported, FC026 refuted). The Skill already said not to
do that, but after 20+ tool calls the model stopped following it. These checks
move the rule from the prompt into the server:

- A supported/refuted verdict must quote, word for word, the cited document
  sentence it rests on (`evidence_quote`). The quote must appear in a document
  read in this episode.
- A claim about the future ("…할 것이다", "will …") may be supported or refuted
  only by a quote that states a settled fact, not a report, estimate or chance.
- Such a claim is never refuted merely for stating a forecast as fact.

Attribution claims ("X는 …할 것으로 전망했다") are about what X said, so they
are exempt from the forecast rules.
"""

from __future__ import annotations

import re
import unicodedata

CLAIM_KINDS = ("fact", "forecast", "attribution")
MAX_QUOTE_CHARS = 400
#: A quote segment shorter than this proves nothing on its own.
MIN_SEGMENT_CHARS = 8

_ATTRIBUTION = re.compile(
    r"것으로\s*(?:\S+\s*)?(?:전망|예상|예측|추정|관측|내다)\S*"
    r"|(?:전망|예상|예측|추정|발표|밝혔|말했)\S*다[.。]?\s*$"
    r"|\b(?:forecasts?|forecasted|projected|predicted|expects?|estimated|said|announced)\b",
    re.I)
_FORECAST = re.compile(r"것이다[.。]?\s*$|\bwill\b|\bgoing to\b|\bis (?:expected|set) to\b", re.I)

#: Words that mark a report of a plan, estimate or chance rather than a settled fact.
HEDGES = (
    "전해졌", "전해진", "알려졌", "알려진", "소식통", "관계자에 따르면", "전망", "예상", "예측",
    "추정", "가능성", "확률", "루머", "유출", "관측", "보인다", "할 듯", "것으로 보",
    "reportedly", "rumor", "rumour", "leak", "expected", "expects", "forecast", "projected",
    "likely", "could", "might", "sources", "people familiar", "analyst", "estimate",
    "probability", "chance", "odds",
)


def detect_claim_kind(text: str) -> str | None:
    """'attribution', 'forecast' or None when the wording does not decide it."""
    if _ATTRIBUTION.search(text or ""):
        return "attribution"
    if _FORECAST.search(text or ""):
        return "forecast"
    return None


def effective_kind(text: str, declared: str | None) -> str:
    """The server's reading wins when it has one, so declaring 'attribution'
    cannot slip a forecast past the rules; otherwise the agent's declaration."""
    detected = detect_claim_kind(text)
    if detected:
        return detected
    return declared if declared in CLAIM_KINDS else "fact"


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "").lower()
    text = re.sub(r"[\"'“”‘’`«»「」『』]", "", text)
    return re.sub(r"\s+", "", text)


def quote_found(quote: str, texts: list[str]) -> bool:
    """Every segment of the quote (split at '…' or '...') appears in one text."""
    segments = [_norm(s) for s in re.split(r"…|\.\.\.", quote or "")]
    segments = [s for s in segments if s]
    if not segments or all(len(s) < MIN_SEGMENT_CHARS for s in segments):
        return False
    for text in texts:
        body = _norm(text)
        if all(s in body for s in segments if len(s) >= MIN_SEGMENT_CHARS):
            return True
    return False


def hedges_in(quote: str) -> list[str]:
    low = (quote or "").lower()
    return [h for h in HEDGES if h in low]


def check_verdict(*, claim_text: str, verdict: str, declared_kind: str | None,
                  quote: str | None, distortion_type: str | None,
                  cited_texts: list[str]) -> tuple[str, str | None]:
    """Returns (claim kind used, refusal message or None)."""
    kind = effective_kind(claim_text, declared_kind)
    if verdict not in ("supported", "refuted"):
        return kind, None
    if kind == "forecast" and verdict == "refuted" and distortion_type == "forecast_as_fact":
        return kind, ("예측 주장을 '전망을 사실처럼 썼다'는 이유로 반박할 수 없습니다. 기준 시점까지 결과가 "
                      "확정된 근거가 없으면 not_enough_evidence로 판정하세요(distortion_type은 그대로 둬도 됩니다).")
    quote = (quote or "").strip()
    if not quote:
        return kind, ("supported/refuted 판정에는 evidence_quote가 필요합니다. 인용한 문서에서 판정을 "
                      "뒷받침하는 문장을 그대로 옮겨 적으세요(최대 400자, 생략은 '…').")
    if len(quote) > MAX_QUOTE_CHARS:
        return kind, f"evidence_quote는 {MAX_QUOTE_CHARS}자 이하로 줄이세요(받은 길이 {len(quote)}자)."
    if not quote_found(quote, cited_texts):
        return kind, ("evidence_quote가 cited_evidence_ids의 문서 본문에 없습니다. 이번 에피소드에서 읽은 "
                      "인용 문서의 문장을 고치지 말고 그대로 옮기세요. 본문을 읽지 않은 문서는 인용할 수 없습니다.")
    if kind == "forecast":
        found = hedges_in(quote)
        if found:
            return kind, ("이 주장은 미래 일에 관한 예측입니다. 인용문이 보도·전망·확률을 전하는 표현"
                          f"({', '.join(found[:3])})을 담고 있어 확정된 사실의 근거가 되지 못합니다. "
                          "기준 시점까지의 공식 확정 발표를 인용하거나, 없으면 not_enough_evidence로 판정하세요.")
    return kind, None
