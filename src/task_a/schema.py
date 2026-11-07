"""Task A data model.

Field names follow docs/research/fact_checking/evaluation.md section 6 and
tools.md section 3. Gold is kept out of every type the agent can observe.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path


class Verdict(str, Enum):
    """The three task labels. NEI is a gold label, not an agent excuse."""

    SUPPORTED = "supported"
    REFUTED = "refuted"
    NOT_ENOUGH_EVIDENCE = "not_enough_evidence"


class ExecutionStatus(str, Enum):
    """Technical outcome, kept separate from fact-checking outcome.

    evaluation.md: '실행 실패를 통계에서 조용히 제거하지 않는다.'
    """

    OK = "ok"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    PARSE_ERROR = "parse_error"
    BUDGET_EXCEEDED = "budget_exceeded"
    PROVIDER_ERROR = "provider_error"


class ToolStatus(str, Enum):
    """tools.md section 4. `empty` means no results, never 'claim is false'."""

    OK = "ok"
    EMPTY = "empty"
    INVALID_INPUT = "invalid_input"
    SOURCE_UNAVAILABLE = "source_unavailable"
    RATE_LIMITED = "rate_limited"
    TIMED_OUT = "timed_out"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class Claim:
    """What the agent is allowed to see. No gold fields here."""

    claim_id: str
    text: str
    family_id: str | None = None
    language: str = "ko"
    source_url: str | None = None
    source_type: str | None = None
    claim_date: str | None = None
    target_period: str | None = None
    evidence_cutoff: str | None = None
    input_body: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Claim:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass(frozen=True)
class Gold:
    """Scorer-only. Never passed to the agent or to any tool."""

    claim_id: str
    label: Verdict | None
    rationale: str | None = None
    review_status: str = "draft"
    numeric_constraints: list[str] = field(default_factory=list)
    sufficient_evidence_ids: list[str] = field(default_factory=list)

    @property
    def is_graded(self) -> bool:
        """판정 보류 cases are excluded from label metrics, not relabelled."""
        return self.label is not None and self.review_status != "pending"


@dataclass(frozen=True)
class EvidenceUnit:
    """A retrievable document in the fixed corpus.

    `provenance_group` separates document count from source independence:
    ten reprints of one press release are not ten independent sources.
    """

    evidence_id: str
    title: str
    text: str
    source_url: str | None = None
    publisher: str | None = None
    source_type: str | None = None
    provenance_group: str | None = None
    published_at: str | None = None
    document_validity: str = "valid"
    claim_evidence_relation: str | None = None
    evidence_condition: str | None = None
    content_hash: str | None = None

    @property
    def is_misleading(self) -> bool:
        return self.document_validity == "misleading"


@dataclass
class ToolResult:
    status: ToolStatus
    observation: str
    payload: dict = field(default_factory=dict)
    evidence_ids: list[str] = field(default_factory=list)
    ranks: list[int] = field(default_factory=list)


@dataclass
class ToolEvent:
    """One tool call, with everything Q36 requires to recompute the metrics."""

    step: int
    tool: str
    args: dict
    status: ToolStatus
    observation_chars: int
    elapsed_ms: int
    evidence_ids: list[str] = field(default_factory=list)
    ranks: list[int] = field(default_factory=list)
    rendered_snippet_ids: list[str] = field(default_factory=list)
    corruption_flags: list[str] = field(default_factory=list)
    external: bool = False
    error: str | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    llm_calls: int = 0
    tool_calls: int = 0
    external_calls: int = 0
    cost_usd: float = 0.0
    elapsed_ms: int = 0

    def add(self, other: Usage) -> None:
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.cached_tokens += other.cached_tokens
        self.llm_calls += other.llm_calls
        self.tool_calls += other.tool_calls
        self.external_calls += other.external_calls
        self.cost_usd += other.cost_usd
        self.elapsed_ms += other.elapsed_ms


@dataclass
class AgentResult:
    """One episode. The scorer reads this and nothing else."""

    claim_id: str
    verdict: Verdict | None
    abstain: bool
    cited_evidence_ids: list[str]
    justification: str
    correction: str | None
    stop_reason: str
    execution_status: ExecutionStatus
    events: list[ToolEvent] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    steps: int = 0
    error: str | None = None

    @property
    def searched_externally(self) -> bool:
        return any(e.external for e in self.events)

    @property
    def valid_verdict(self) -> bool:
        """Recovery/Harm only count pairs where both arms produced a verdict."""
        return self.verdict is not None and self.execution_status == ExecutionStatus.OK

    def to_dict(self) -> dict:
        return {
            "claim_id": self.claim_id,
            "verdict": self.verdict.value if self.verdict else None,
            "abstain": self.abstain,
            "cited_evidence_ids": self.cited_evidence_ids,
            "justification": self.justification,
            "correction": self.correction,
            "stop_reason": self.stop_reason,
            "execution_status": self.execution_status.value,
            "steps": self.steps,
            "error": self.error,
            "events": [e.to_dict() for e in self.events],
            "usage": asdict(self.usage),
        }


def read_jsonl(path: str | Path) -> list[dict]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def write_jsonl(path: str | Path, rows: list[dict]) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return len(rows)
