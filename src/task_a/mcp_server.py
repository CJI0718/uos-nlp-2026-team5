"""Method A Adapter: MCP Server & Stateful Agent Bridge for Task A + Missions.

Allows ANY existing AI agent (Antigravity, Claude Code, Cursor, Codex, etc.) to
solve Task A claims and execute verification-gated follow-up missions while:
1. Enforcing strict answer-leakage isolation (never opens `gold.jsonl` or
   `evaluation.md`).
2. Enforcing arm constraints (`C0` closed-book, `C1` fixed corpus, `C2` corpus +
   external web) and per-episode tool budgets.
3. Automatically writing standard `RunLog` JSONL records so `scripts/score_run.py`
   can grade the external agent's run identically to `runner.py`.
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from task_a.missions import ALL_MISSIONS, MissionExecutor
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
    last_mission: dict | None = None


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
    ) -> None:
        if "gold" in str(claims_path).lower() or "evaluation.md" in str(claims_path).lower():
            raise PermissionError("정답 누출 차단: 에이전트 환경은 gold 또는 evaluation.md를 열 수 없습니다.")

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
            prompt_version="skill-v1",
            data_version="claims-2026-11-07",
        )
        self.log = RunLog(out_path)
        self.max_tool_calls = max_tool_calls
        self.max_external_calls = max_external_calls

        corpus_units: list[EvidenceUnit] = []
        if arm != "C0" and corpus_path and Path(corpus_path).exists():
            corpus_units = [
                EvidenceUnit(**{k: v for k, v in r.items() if k in EvidenceUnit.__dataclass_fields__})
                for r in read_jsonl(corpus_path)
            ]

        tok = KiwiTokenizer() if tokenizer == "kiwi" else BigramTokenizer()
        web = web_provider if arm == "C2" else None
        base_backend = CorpusBackend(corpus_units, tok, web=web)
        if cache_path is not None:
            self.backend = CachingBackend(base_backend, ToolCache(cache_path, enabled=True))
        else:
            self.backend = base_backend

        self.registry = ToolRegistry(self.backend)
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
            result = self.finish_episode(args)
            return {"status": "finished", "result": result.to_dict()}

        if name == "execute_mission":
            return self._run_mission_tool(ep, args)

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

    def _run_mission_tool(self, ep: ActiveEpisode, args: dict) -> dict:
        res = self.missions.execute_mission(
            claim_id=ep.claim.claim_id,
            mission_type=str(args.get("mission_type", "no_op")),
            verdict=str(args.get("verdict", "")),
            title=str(args.get("title", ep.claim.claim_id)),
            summary=str(args.get("summary", "")),
            cited_evidence_ids=args.get("cited_evidence_ids") or [],
            abstain=bool(args.get("abstain", False)),
            correction=args.get("correction"),
            distortion_type=args.get("distortion_type"),
            event_start_kst=args.get("event_start_kst"),
            tracking_condition=args.get("tracking_condition"),
            tracking_queries=args.get("tracking_queries"),
        )
        if res.status == ToolStatus.OK:
            ep.last_mission = res.payload
        return {
            "status": res.status.value,
            "observation": res.observation,
            "mission": res.payload,
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
        mission_output = args.get("mission_output") or ep.last_mission
        mission_type = args.get("mission_type") or (
            ep.last_mission.get("mission_type") if ep.last_mission else None
        )

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
            "name": "execute_mission",
            "description": (
                "검증 결과를 바탕으로 후속 업무(Mission) 또는 장기 추적을 실행합니다. "
                "검증 게이팅: 미확인(NEI/abstain) 정보로는 실행형 미션이 차단되며, "
                "반박(refuted)된 정보는 반드시 correction(정정 사실)을 포함해야 합니다."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "mission_type": {"type": "string", "enum": sorted(ALL_MISSIONS)},
                    "verdict": {"type": "string", "enum": ["supported", "refuted", "not_enough_evidence"]},
                    "abstain": {"type": "boolean"},
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                    "cited_evidence_ids": {"type": "array", "items": {"type": "string"}},
                    "correction": {"type": "string"},
                    "distortion_type": {"type": "string"},
                    "event_start_kst": {"type": "string", "description": "event_manager용 KST 시각 (YYYY-MM-DD HH:MM)"},
                    "tracking_condition": {"type": "string", "description": "continuous_tracking용 재검증 조건"},
                    "tracking_queries": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["mission_type", "verdict", "title", "summary"],
            },
        })
        tools.append({
            "name": FINISH_TOOL,
            "description": "검증 에피소드를 종료하고 최종 판정·근거·왜곡 분석·후속 미션 결과를 제출합니다.",
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
