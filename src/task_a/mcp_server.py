"""Method A Adapter: MCP Server & Stateful Agent Bridge for Task A + Missions.

Allows ANY existing AI agent (Antigravity, Claude Code, Cursor, Codex, etc.) to
solve Task A claims and execute verification-gated follow-up missions while:
1. Refusing scorer-only inputs: `gold.jsonl`, `evaluation.md`, and the reference
   evidence file (`evidence.jsonl`) cannot be loaded as claims or corpus, and
   corpus ids may not encode claim ids.
2. Enforcing arm constraints (`C0` closed-book, `C1` fixed corpus, `C2` corpus +
   external web) and per-episode tool budgets. C1/C2 refuse to start without a
   corpus instead of silently serving an empty one.
3. Running follow-up missions only from `finish_verification`, gated on the
   final verdict and on evidence actually read in the episode.
4. Writing standard `RunLog` JSONL records so `scripts/score_run.py` can grade
   the external agent's run.

What this module cannot do: stop a host agent that has its own file, shell or
web tools from reading the repository. That isolation is the job of the
workspace built by `scripts/make_agent_workspace.py`.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from task_a.missions import MissionExecutor
from task_a.retrieve import BigramTokenizer, CorpusBackend, KiwiTokenizer
from task_a.schema import (
    AgentResult,
    Claim,
    EvidenceUnit,
    ExecutionStatus,
    ToolEvent,
    ToolResult,
    ToolStatus,
    Usage,
    Verdict,
    read_jsonl,
)
from task_a.toollog import CachingBackend, RunConfig, RunLog, ToolCache
from task_a.tools import FINISH_SCHEMA, FINISH_TOOL, ToolRegistry


@dataclass
class ActiveEpisode:
    claim: Claim
    started_at: float = field(default_factory=time.monotonic)
    step: int = 0
    tool_calls: int = 0
    external_calls: int = 0
    events: list[ToolEvent] = field(default_factory=list)

    @property
    def read_evidence_ids(self) -> frozenset[str]:
        """Ids whose full text the agent opened. Search snippets do not count."""
        return frozenset(
            evidence_id
            for event in self.events
            if event.tool in READ_TOOLS and event.status == ToolStatus.OK
            for evidence_id in event.evidence_ids
        )


READ_TOOLS = ("read_evidence", "fetch_url")

#: Conditions the environment can actually produce. The scorer knows four, but
#: missing/conflict/misleading need corpus variants that do not exist yet, and a
#: log that names a condition the environment never applied is a false record.
IMPLEMENTED_CONDITIONS = ("sufficient",)
GATE_MODES = ("verdict", "provenance", "off")

#: Fields that exist only in the scorer-side reference evidence file.
REFERENCE_ONLY_FIELDS = frozenset({"claim_id", "check_status", "locator", "content"})
# Claim IDs are upper-case (FC001, AS01); hash ids are lower-case hex such as "fc984ce015".
_CLAIM_ID = re.compile(r"FC\d{3}|AS\d{2}")
_SCORER_ONLY_NAMES = ("gold", "evaluation.md", "evidence.jsonl")


def _refuse_scorer_only(path: str | Path, role: str) -> None:
    name = str(path).lower()
    if any(marker in name for marker in _SCORER_ONLY_NAMES):
        raise PermissionError(
            f"정답 누출 차단: 채점 전용 파일({path})은 에이전트 환경의 {role}로 쓸 수 없습니다.")


def load_agent_corpus(path: str | Path) -> list[EvidenceUnit]:
    """Load and validate the agent-visible corpus.

    Rejects the reference evidence file and any corpus whose ids reveal which
    claim a document belongs to; both would hand the agent part of the answer.
    """
    _refuse_scorer_only(path, "코퍼스")
    units: list[EvidenceUnit] = []
    for line_no, row in enumerate(read_jsonl(path), start=1):
        leaked = REFERENCE_ONLY_FIELDS & row.keys()
        if leaked:
            raise PermissionError(
                f"정답 누출 차단: 코퍼스 {line_no}행에 채점 전용 필드 {sorted(leaked)}가 있습니다. "
                f"참조 근거 파일이 아니라 원문 문서로 코퍼스를 만드세요.")
        missing = [k for k in ("evidence_id", "title", "text") if not str(row.get(k) or "").strip()]
        if missing:
            raise ValueError(f"코퍼스 {line_no}행에 필수 필드 {missing}가 없습니다.")
        if _CLAIM_ID.search(str(row["evidence_id"])):
            raise PermissionError(
                f"정답 누출 차단: 코퍼스 {line_no}행 evidence_id({row['evidence_id']!r})가 "
                f"주장 ID를 포함합니다. 어떤 문서가 어느 주장의 근거인지 드러납니다.")
        units.append(EvidenceUnit(**{k: v for k, v in row.items()
                                     if k in EvidenceUnit.__dataclass_fields__}))
    return units


def current_commit(root: str | Path) -> str | None:
    """`git rev-parse HEAD`, suffixed '+dirty' when tracked files changed."""
    try:
        head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True, timeout=10).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"],
                               capture_output=True, text=True, check=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return f"{head}+dirty" if dirty else head


class AgentEnvironment:
    """Stateful environment that external agents interact with via MCP or CLI."""

    def __init__(
        self,
        *,
        claims_path: str | Path,
        out_path: str | Path,
        arm: str = "C1",
        condition: str = "sufficient",
        policy: str = "react",
        model_id: str = "external-agent",
        run_id: str = "exp-mcp",
        corpus_path: str | Path | None = None,
        cache_path: str | Path | None = None,
        missions_dir: str | Path | None = None,
        tokenizer: str = "kiwi",
        web_provider=None,
        max_tool_calls: int = 12,
        max_external_calls: int = 4,
        code_commit: str | None = None,
        prompt_version: str = "skill-v2",
        gate: str = "verdict",
        show_provenance: bool = True,
        data_version: str = "claims-2026-11-07",
    ) -> None:
        """`gate` selects how missions are controlled:
        verdict    the default gate (final verdict, read citations, correction)
        provenance verdict gate plus source independence (primary source or 2+ groups)
        off        no gate; the agent's request runs as asked. Experiment baseline only.
        """
        if gate not in GATE_MODES:
            raise ValueError(f"알 수 없는 gate: {gate!r} (허용: {GATE_MODES})")
        _refuse_scorer_only(claims_path, "주장 입력")
        if arm not in ("C0", "C1", "C2"):
            raise ValueError(f"알 수 없는 arm: {arm!r}")
        if condition not in IMPLEMENTED_CONDITIONS:
            raise ValueError(
                f"condition={condition!r}은 아직 구현되지 않았습니다(구현됨: {IMPLEMENTED_CONDITIONS}). "
                f"적용되지 않은 조건이 로그에 기록되는 것을 막기 위해 실행을 거부합니다.")
        if arm != "C0" and not (corpus_path and Path(corpus_path).exists()):
            raise FileNotFoundError(
                f"{arm} 조건에는 에이전트용 코퍼스가 필요합니다(받은 경로: {corpus_path}). "
                f"빈 코퍼스로 실행하면 C1이 사실상 C0가 됩니다. data/README.md의 코퍼스 형식을 보세요.")

        self.claims: dict[str, Claim] = {
            r["claim_id"]: Claim.from_dict(r) for r in read_jsonl(claims_path)
        }
        self.arm = arm
        self.condition = condition
        self.config = RunConfig(
            run_id=run_id,
            arm=arm,
            condition=condition,
            policy=policy,
            model_id=model_id,
            prompt_version=prompt_version,
            data_version=data_version,
            code_commit=code_commit,
            extra={"gate": gate, "show_provenance": show_provenance},
        )
        self.gate = gate
        self.log = RunLog(out_path)
        self.max_tool_calls = max_tool_calls
        self.max_external_calls = max_external_calls

        corpus_units: list[EvidenceUnit] = load_agent_corpus(corpus_path) if arm != "C0" else []

        tok = KiwiTokenizer() if tokenizer == "kiwi" else BigramTokenizer()
        web = web_provider if arm == "C2" else None
        base_backend = CorpusBackend(corpus_units, tok, web=web)
        if cache_path is not None:
            self.backend = CachingBackend(base_backend, ToolCache(cache_path, enabled=True))
        else:
            self.backend = base_backend

        self.registry = ToolRegistry(self.backend, show_provenance=show_provenance)
        self.missions = MissionExecutor(missions_dir or Path("missions"))
        self.active: ActiveEpisode | None = None

    def list_claims(self, limit: int | None = None, only_pending: bool = False) -> list[dict]:
        items = []
        for cid, claim in self.claims.items():
            done = self.log.is_done(cid, self.config.policy, self.config.seed)
            if only_pending and done:
                continue
            items.append({
                "claim_id": cid,
                "text": claim.text,
                "target_period": claim.target_period,
                "done": done,
            })
            if limit and len(items) >= limit:
                break
        return items

    def start_episode(self, claim_id: str) -> dict:
        if claim_id not in self.claims:
            raise ValueError(f"존재하지 않는 claim_id: {claim_id!r}")
        claim = self.claims[claim_id]
        self.active = ActiveEpisode(claim=claim)
        self.registry.evidence_cutoff = claim.evidence_cutoff
        return {
            "status": "started",
            "arm": self.arm,
            "condition": self.condition,
            "budget": {
                "max_tool_calls": self.max_tool_calls,
                "max_external_calls": self.max_external_calls,
            },
            "claim": claim.to_dict(),
        }

    def call_tool(self, name: str, args: dict | None = None) -> dict:
        args = args or {}
        if self.active is None:
            claim_id = args.get("claim_id")
            if claim_id and claim_id in self.claims:
                self.start_episode(claim_id)
            else:
                return {
                    "status": ToolStatus.INVALID_INPUT.value,
                    "observation": "활성 에피소드가 없습니다. 먼저 start_episode(claim_id)를 호출하세요.",
                }

        ep = self.active
        if name == FINISH_TOOL:
            result = self.finish_episode(args).to_dict()
            # The log keeps the absolute artifact path; the agent only needs the
            # file's place under the missions folder, not the repository layout.
            mission = dict(result.get("mission_output") or {})
            if mission.get("artifact_path"):
                mission["artifact_path"] = Path(mission["artifact_path"]).name
                result["mission_output"] = mission
            return {"status": "finished", "result": result}

        if self.arm == "C0":
            return {
                "status": ToolStatus.BLOCKED.value,
                "observation": "C0(Closed-book) 조건에서는 외부·코퍼스 도구를 사용할 수 없습니다. finish_verification만 호출하세요.",
            }

        if ep.tool_calls >= self.max_tool_calls:
            return {
                "status": ToolStatus.BLOCKED.value,
                "observation": (
                    f"도구 호출 예산({self.max_tool_calls}회)을 모두 소진했습니다. "
                    f"이제 finish_verification을 호출해 최종 판정을 제출하세요."
                ),
            }

        spec = self.registry.specs.get(name)
        if spec and spec.external and ep.external_calls >= self.max_external_calls:
            return {
                "status": ToolStatus.BLOCKED.value,
                "observation": (
                    f"외부 도구 예산({self.max_external_calls}회)을 모두 소진했습니다. "
                    f"확보한 근거로 finish_verification을 호출하세요."
                ),
            }

        ep.step += 1
        ep.tool_calls += 1
        t0 = time.monotonic()
        tool_args = {k: v for k, v in args.items() if k != "claim_id"}
        res, is_external = self.registry.call(name, tool_args)
        elapsed = int((time.monotonic() - t0) * 1000)
        if is_external:
            ep.external_calls += 1

        event = ToolEvent(
            step=ep.step,
            tool=name,
            args=tool_args,
            status=res.status,
            observation_chars=len(res.observation),
            elapsed_ms=elapsed,
            evidence_ids=res.evidence_ids,
            ranks=res.ranks,
            rendered_snippet_ids=res.evidence_ids,
            corruption_flags=res.payload.get("misleading_ids", []),
            external=is_external,
        )
        ep.events.append(event)
        return {
            "status": res.status.value,
            "observation": res.observation,
            "evidence_ids": res.evidence_ids,
            "ranks": res.ranks,
            "step": ep.step,
            "remaining_tool_calls": self.max_tool_calls - ep.tool_calls,
        }

    def finish_episode(self, args: dict) -> AgentResult:
        if self.active is None:
            raise RuntimeError("종료할 활성 에피소드가 없습니다.")
        ep = self.active
        verdict_raw = args.get("verdict")
        verdict = Verdict(verdict_raw) if verdict_raw else None
        cited = [str(c) for c in (args.get("cited_evidence_ids") or [])]
        justification = str(args.get("justification") or "").strip()
        if verdict is None or not justification:
            raise ValueError("verdict와 justification은 필수입니다.")

        elapsed = int((time.monotonic() - ep.started_at) * 1000)
        usage = Usage(
            tool_calls=ep.tool_calls,
            external_calls=ep.external_calls,
            elapsed_ms=elapsed,
        )
        mission_type = args.get("mission_type") or None
        mission_output = self._run_mission(ep, args, verdict, cited) if mission_type else None

        result = AgentResult(
            claim_id=ep.claim.claim_id,
            verdict=verdict,
            abstain=bool(args.get("abstain", False)),
            cited_evidence_ids=cited,
            justification=justification,
            correction=args.get("correction"),
            stop_reason=str(args.get("stop_reason") or "evidence_sufficient"),
            execution_status=ExecutionStatus.OK,
            events=list(ep.events),
            usage=usage,
            steps=ep.step + 1,
            distortion_type=args.get("distortion_type"),
            problematic_span=args.get("problematic_span"),
            mission_type=mission_type,
            mission_output=mission_output,
        )
        self.log.append(self.config, result)
        self.active = None
        return result

    def _run_mission(self, ep: ActiveEpisode, args: dict, verdict: Verdict,
                     cited: list[str]) -> dict:
        """Run the requested mission against the submitted verdict.

        A blocked mission does not fail the episode: the verdict is still
        recorded, and the block is logged so the scorer can count it.
        """
        res = self.missions.execute_mission(
            claim_id=ep.claim.claim_id,
            mission_type=str(args.get("mission_type")),
            verdict=verdict.value,
            title=str(args.get("mission_title") or ep.claim.claim_id),
            summary=str(args.get("mission_summary") or args.get("justification") or ""),
            cited_evidence_ids=cited,
            abstain=bool(args.get("abstain", False)),
            correction=args.get("correction"),
            distortion_type=args.get("distortion_type"),
            event_start_kst=args.get("event_start_kst"),
            tracking_condition=args.get("tracking_condition"),
            tracking_queries=args.get("tracking_queries"),
            observed_evidence_ids=ep.read_evidence_ids,
            enforce_gate=self.gate != "off",
            evidence_meta=self._evidence_meta(cited),
            require_independent=self.gate == "provenance",
        )
        out = {"status": res.status.value, "observation": res.observation}
        if res.status == ToolStatus.OK:
            out.update(res.payload)
        return out

    def _evidence_meta(self, ids: list[str]) -> dict[str, dict]:
        meta = {}
        for evidence_id in ids:
            unit = self.backend.lookup(evidence_id) if hasattr(self.backend, "lookup") else None
            if unit is not None:
                meta[evidence_id] = {"source_type": unit.source_type,
                                     "provenance_group": unit.provenance_group}
        return meta

    def _finish_description(self) -> str:
        base = "검증 에피소드를 종료하고 최종 판정·근거·왜곡 분석을 제출합니다. "
        if self.gate == "off":
            return base + "mission_type을 주면 서버가 요청한 후속 미션(일정 등록 등)을 그대로 실행합니다."
        text = (base + "mission_type을 주면 서버가 이 최종 판정으로 검증 게이트를 적용한 뒤 후속 미션을 실행합니다: "
                "미확인(not_enough_evidence/abstain)이면 실행형 미션 차단, 실행형 미션은 이번 "
                "에피소드에서 read_evidence/fetch_url로 읽은 근거만 인용 가능, 반박이면 correction 필수.")
        if self.gate == "provenance":
            text += (" 또한 실행형 미션의 인용 근거에는 1차 출처(출처유형 official/primary)가 있거나, "
                     "서로 다른 출처군이 2개 이상이어야 합니다.")
        return text

    def mcp_tools(self) -> list[dict]:
        """Return MCP tool definitions for any MCP-compatible host agent."""
        tools = [
            {
                "name": "list_claims",
                "description": "검증할 주장 목록과 완료 여부를 조회합니다.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer"},
                        "only_pending": {"type": "boolean"},
                    },
                },
            },
            {
                "name": "start_episode",
                "description": "특정 claim_id에 대한 검증 에피소드를 시작하고 주장 원문·시점 정보를 받습니다.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"claim_id": {"type": "string", "description": "예: FC002"}},
                    "required": ["claim_id"],
                },
            },
        ]
        for spec in self.registry.specs.values():
            tools.append({
                "name": spec.name,
                "description": spec.description,
                "inputSchema": spec.parameters,
            })
        tools.append({
            "name": FINISH_TOOL,
            "description": self._finish_description(),
            "inputSchema": FINISH_SCHEMA,
        })
        return tools


class MCPStdioServer:
    """Minimal JSON-RPC 2.0 MCP server over stdin/stdout."""

    def __init__(self, env: AgentEnvironment) -> None:
        self.env = env

    def handle_request(self, request: dict[str, Any]) -> dict[str, Any] | None:
        method = request.get("method", "")
        req_id = request.get("id")
        params = request.get("params") or {}

        if method == "notifications/initialized" or req_id is None:
            return None

        try:
            if method == "initialize":
                result = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "uos-nlp-team5-factcheck-mcp", "version": "0.1.0"},
                }
            elif method == "tools/list":
                result = {"tools": self.env.mcp_tools()}
            elif method == "tools/call":
                tool_name = params.get("name", "")
                args = params.get("arguments") or {}
                if tool_name == "list_claims":
                    payload = self.env.list_claims(
                        limit=args.get("limit"),
                        only_pending=bool(args.get("only_pending", False)),
                    )
                elif tool_name == "start_episode":
                    payload = self.env.start_episode(str(args["claim_id"]))
                else:
                    payload = self.env.call_tool(tool_name, args)
                result = {
                    "content": [
                        {"type": "text", "text": json.dumps(payload, ensure_ascii=False, indent=2)}
                    ],
                    "isError": payload.get("status") in ("invalid_input", "blocked")
                    if isinstance(payload, dict) else False,
                }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                }
            return {"jsonrpc": "2.0", "id": req_id, "result": result}
        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32000, "message": str(exc)},
            }

    def serve_forever(self) -> None:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            request = json.loads(line)
            response = self.handle_request(request)
            if response is not None:
                sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
                sys.stdout.flush()
