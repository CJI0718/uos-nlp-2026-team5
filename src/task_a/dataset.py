"""Parse the team's 50 annotated cases out of evaluation.md section 9.8.

The Markdown is the source of truth and is never edited by this module; it is
read-only input. Output is split three ways so the agent can never see gold:

    claims.jsonl    agent-visible: claim text, dates, source excerpt
    gold.jsonl      scorer-only: verdict, rationale, evaluation points
    evidence.jsonl  scorer-only: reference sources and their check status
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

CASE_HEADING = re.compile(r"^#### (?P<case_id>FC\d{3})\s*$", re.M)
FIELD_LINE = re.compile(r"^- \*\*(?P<key>[^*]+)\*\*:\s*(?P<value>.*)$")
SECTION_LINE = re.compile(r"^\*\*(?P<title>[^*]+)\*\*(?::\s*(?P<inline>.*))?$")
LINK_ITEM = re.compile(r"^- \[(?P<title>[^\]]*)\]\((?P<url>[^)]*)\)(?P<note>.*)$")
SUB_FIELD = re.compile(r"^\s+- (?P<key>[^:]+):\s*(?P<value>.*)$")
BULLET = re.compile(r"^- (?P<text>.+)$")
TABLE_ROW = re.compile(r"^\| \[(?P<case_id>FC\d{3})\][^|]*\| (?P<kind>[^|]+) \|.*\| (?P<label>[^|]+) \|\s*$")
MD_LINK = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")

LABEL_MAP = {
    "지지": "supported",
    "반박": "refuted",
    "근거 부족": "not_enough_evidence",
    "판정 보류": None,  # a review state, not a fourth label
}

# Split groups documented in evaluation.md section 9.6. Cases outside these are
# their own group; the 47-group total is a team figure, not derivable from text.
DOCUMENTED_GROUPS = {
    "FC032": "grp_mistral_announcement",
    "FC034": "grp_mistral_announcement",
    "FC015": "grp_model_size_units",
    "FC019": "grp_model_size_units",
    "FC020": "grp_model_size_units",
}

# Sections a solver must not see: they state what to check or what is wrong.
SCORER_ONLY_SECTIONS = frozenset({
    "글의 맥락 — 요약", "평가 포인트", "판정 범위와 주의사항",
    "근거 부족 판단의 조사 범위",
})
# Matched by prefix: the transcript heading varies. FC040/FC042 are Spanish
# posts transcribed from the platform's Korean translation, so they read
# '입력 본문 — 플랫폼에 표시된 한국어 번역 전사' instead of '작성자 본문 전사'.
AGENT_INPUT_PREFIXES = ("입력 본문 —",)
AGENT_INPUT_EXACT = ("첨부 자료의 판독 가능한 문구", "선정 주장과 관련된 짧은 원문 발췌")


@dataclass
class ParsedCase:
    case_id: str
    title: str = ""
    fields: dict[str, str] = field(default_factory=dict)
    sections: dict[str, list[str]] = field(default_factory=dict)
    evidence: list[dict] = field(default_factory=list)


def split_cases(text: str) -> list[tuple[str, str]]:
    """Return (case_id, block_text) for each `#### FCnnn` heading."""
    matches = list(CASE_HEADING.finditer(text))
    out = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[match.end():end]
        # Trim the trailing separator that closes each case.
        block = re.split(r"^---\s*$", block, maxsplit=1, flags=re.M)[0]
        out.append((match.group("case_id"), block))
    return out


# A title line is entirely bold with nothing after it, e.g. '**FC044 제목**'.
# Colons are allowed inside (FC044 has one); the `$` anchor is what separates a
# title from a section header carrying inline text such as '**입력 본문 확보**: ...'.
TITLE_ONLY = re.compile(r"^\*\*(?P<title>.+?)\*\*$")


def parse_case(case_id: str, block: str) -> ParsedCase:
    """Parse one `#### FCnnn` block.

    The title line is a bare `**...**` and would otherwise be mistaken for a
    section header, which pushes every top-level field into a section. It is
    consumed first so that `- **key**: value` lines stay fields.
    """
    case = ParsedCase(case_id=case_id)
    lines = [ln for ln in block.splitlines() if ln.strip()]
    current_section = None
    in_evidence = False
    start = 0

    for i, line in enumerate(lines):
        title_match = TITLE_ONLY.match(line.strip())
        if title_match:
            case.title = title_match.group("title").strip()
            start = i + 1
            break

    for line in lines[start:]:
        heading = SECTION_LINE.match(line)
        if heading and not line.startswith("- "):
            title = heading.group("title").strip()
            current_section = title
            in_evidence = title == "근거 자료"
            if heading.group("inline"):
                # `**입력 본문 확보**: ...` is a field, not a body section.
                case.fields[title] = heading.group("inline").strip()
                current_section = None
                in_evidence = False
            else:
                case.sections.setdefault(title, [])
            continue

        field_match = FIELD_LINE.match(line)
        if field_match and current_section is None and not in_evidence:
            case.fields[field_match.group("key").strip()] = field_match.group("value").strip()
            continue

        if in_evidence:
            link = LINK_ITEM.match(line)
            if link:
                case.evidence.append({
                    "title": link.group("title").strip(),
                    "url": link.group("url").strip(),
                    "note": link.group("note").strip().lstrip("—-").strip(),
                })
                continue
            sub = SUB_FIELD.match(line)
            if sub and case.evidence:
                case.evidence[-1][sub.group("key").strip()] = sub.group("value").strip()
                continue

        if current_section is not None:
            case.sections[current_section].append(line)

    return case


def _clean(lines: list[str]) -> str:
    """Join a section's raw lines, dropping blockquote markers."""
    out = []
    for line in lines:
        text = line.strip()
        if text.startswith(">"):
            text = text.lstrip(">").strip()
        out.append(text)
    return "\n".join(out).strip()


def _bullets(lines: list[str]) -> list[str]:
    items = []
    for line in lines:
        match = BULLET.match(line.strip())
        if match:
            items.append(match.group("text").strip())
    return items


def agent_input_body(case: ParsedCase) -> str | None:
    """The excerpt/transcript the solver may see. Excludes gold-only sections.

    Section order is preserved so the attachment text stays after the post it
    belongs to. The heading is kept in the body because it records provenance -
    a platform translation is not the author's original wording.
    """
    parts = []
    for name, lines in case.sections.items():
        if not (name.startswith(AGENT_INPUT_PREFIXES) or name in AGENT_INPUT_EXACT):
            continue
        body = _clean(lines)
        if body:
            parts.append(f"[{name}]\n{body}")
    return "\n\n".join(parts) if parts else None


def source_url(case: ParsedCase) -> str | None:
    raw = case.fields.get("입력 글", "")
    match = MD_LINK.search(raw)
    return match.group(2) if match else (raw or None)


def parse_source_kinds(text: str) -> dict[str, str]:
    """Read the section 9.7 index table for each case's source kind."""
    kinds = {}
    for line in text.splitlines():
        match = TABLE_ROW.match(line)
        if match:
            kinds[match.group("case_id")] = match.group("kind").strip()
    return kinds


def to_records(case: ParsedCase, source_kind: str | None = None) -> dict:
    """Split one parsed case into claim / gold / evidence records."""
    label_text = case.fields.get("참조 판정", "").strip()
    if label_text not in LABEL_MAP:
        raise ValueError(f"{case.case_id}: unknown 참조 판정 {label_text!r}")
    label = LABEL_MAP[label_text]
    pending = label is None

    language = "en" if source_kind and "영어" in source_kind else "ko"
    if source_kind in ("Threads", "X"):
        language = "mixed"

    claim = {
        "claim_id": case.case_id,
        "text": case.fields.get("선정 주장", "").strip(),
        "family_id": DOCUMENTED_GROUPS.get(case.case_id, f"solo_{case.case_id}"),
        "language": language,
        "source_url": source_url(case),
        "source_type": source_kind,
        "claim_date": case.fields.get("게시 시점"),
        "target_period": case.fields.get("검증 대상 기간·버전"),
        "evidence_cutoff": "2026-10-30T01:37:43+09:00",
        "input_body": agent_input_body(case),
    }

    gold = {
        "claim_id": case.case_id,
        "label": label,
        "label_text": label_text,
        "rationale": case.fields.get("판정 이유", "").strip(),
        "review_status": "pending" if pending else "draft",
        # 주장 위치 is annotator metadata, not solver input: for FC044 it reads
        # '기사 제목의 10월 24일; 본문의 10월 14일과 비교', which states the answer.
        "claim_location": case.fields.get("주장 위치"),
        "context_summary": _clean(case.sections.get("글의 맥락 — 요약", [])) or None,
        "evaluation_points": _bullets(case.sections.get("평가 포인트", [])),
        "scope_notes": _bullets(case.sections.get("판정 범위와 주의사항", [])),
        "nei_investigation": _clean(case.sections.get("근거 부족 판단의 조사 범위", [])) or None,
        "sufficient_evidence_ids": [],
    }

    evidence_rows = []
    for i, item in enumerate(case.evidence, start=1):
        evidence_id = f"EV_{case.case_id}_{i}"
        gold["sufficient_evidence_ids"].append(evidence_id)
        evidence_rows.append({
            "evidence_id": evidence_id,
            "claim_id": case.case_id,
            "title": item.get("title"),
            "source_url": item.get("url"),
            "content": item.get("내용"),
            "locator": item.get("확인 위치"),
            "check_status": item.get("자료 확인 상태"),
            "note": item.get("note") or None,
        })

    return {"claim": claim, "gold": gold, "evidence": evidence_rows}


def extract(markdown: str) -> dict[str, list[dict]]:
    kinds = parse_source_kinds(markdown)
    claims, golds, evidence = [], [], []
    for case_id, block in split_cases(markdown):
        records = to_records(parse_case(case_id, block), kinds.get(case_id))
        claims.append(records["claim"])
        golds.append(records["gold"])
        evidence.extend(records["evidence"])
    return {"claims": claims, "gold": golds, "evidence": evidence}
