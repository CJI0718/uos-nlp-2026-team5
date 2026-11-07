"""Run logging, deterministic tool cache and cost accounting.

Three requirements from the team docs drive this module:

- evaluation.md section 7: '매 요청/도구 결과를 즉시 append-only 기록하고
  재시작 시 완료 사례를 중복 호출하지 않는다.' A crash must not re-spend
  budget on episodes that already finished.
- Q35 and the C2 API note: cached replay and live results are reported
  separately. Every observation records which one it was.
- Tool caches contain article text, so they live under data/cache/, which
  .gitignore already excludes. Run logs stay lean enough to commit.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from task_a.schema import AgentResult
from task_a.tools import ToolBackend

CACHE_VERSION = 1

#: Sentinel for 'not in cache'. A cached empty list or empty string is a real
#: response worth replaying, so None cannot serve this role.
MISSING = object()


def cache_key(tool: str, args: dict) -> str:
    """Canonical, order-independent key so the same call always hits."""
    canonical = json.dumps({"tool": tool, "args": args}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]


@dataclass(frozen=True)
class RunConfig:
    """Everything needed to tell two runs apart. Recorded on every result row."""

    run_id: str
    condition: str                       # C0 | C1 | C2
    policy: str                          # react | fixed_workflow | closed_book
    model_id: str
    prompt_version: str
    data_version: str
    seed: int = 0
    code_commit: str | None = None
    replay: bool = False                 # True when served from cache
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class ToolCache:
    """JSON-lines cache of tool observations, keyed by canonical arguments."""

    def __init__(self, path: str | Path, enabled: bool = True) -> None:
        self.path = Path(path)
        self.enabled = enabled
        self.hits = 0
        self.misses = 0
        self._memory: dict[str, dict] = {}
        if self.enabled and self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    row = json.loads(line)
                    self._memory[row["key"]] = row

    def get(self, key: str):
        """Return the cached raw response, or MISSING when not cached.

        MISSING distinguishes 'never seen' from a cached empty response, which
        is a legitimate provider result worth replaying.
        """
        if not self.enabled:
            return MISSING
        row = self._memory.get(key)
        if row is None:
            self.misses += 1
            return MISSING
        self.hits += 1
        return row["raw"]

    def put(self, key: str, tool: str, args: dict, raw) -> None:
        """Store the provider's raw response, not a shaped ToolResult.

        The registry does the shaping, so a cache hit and a live call yield
        byte-identical observations. That is what makes replay comparable.
        """
        if not self.enabled:
            return
        row = {
            "cache_version": CACHE_VERSION,
            "key": key,
            "tool": tool,
            "args": args,
            "raw": raw,
            "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }
        self._memory[key] = row
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    def stats(self) -> dict:
        total = self.hits + self.misses
        return {"entries": len(self._memory), "hits": self.hits, "misses": self.misses,
                "hit_rate": round(self.hits / total, 4) if total else None}


class CachingBackend:
    """Wraps any ToolBackend. Only external calls are cached.

    search_corpus and lookup are already deterministic given a frozen index, so
    caching them would only hide index changes. web_search and fetch_url are not
    deterministic - that is the whole reason replay exists.
    """

    EXTERNAL_TOOLS = ("search_web", "fetch_url")

    def __init__(self, inner: ToolBackend, cache: ToolCache) -> None:
        self.inner = inner
        self.cache = cache
        self.served_from_cache = 0
        self.fetched_live = 0

    def search_corpus(self, query: str, top_k: int):
        return self.inner.search_corpus(query, top_k)

    def lookup(self, evidence_id: str):
        return self.inner.lookup(evidence_id) if hasattr(self.inner, "lookup") else None

    def web_search(self, query: str, top_k: int) -> list[dict]:
        return self._cached_call("search_web", {"query": query, "top_k": top_k},
                                 lambda: self.inner.web_search(query, top_k))

    def fetch(self, url: str) -> str:
        return self._cached_call("fetch_url", {"url": url}, lambda: self.inner.fetch(url))

    def _cached_call(self, tool: str, args: dict, call):
        key = cache_key(tool, args)
        cached = self.cache.get(key)
        if cached is not MISSING:
            self.served_from_cache += 1
            return cached
        raw = call()
        self.fetched_live += 1
        self.cache.put(key, tool, args, raw)
        return raw


class RunLog:
    """Append-only episode log, and the resume set that prevents re-spending."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._done: set[str] = set()
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    row = json.loads(line)
                    self._done.add(self.episode_key(row["result"]["claim_id"],
                                                    row["config"]["policy"],
                                                    row["config"]["seed"]))

    @staticmethod
    def episode_key(claim_id: str, policy: str, seed: int) -> str:
        return f"{claim_id}|{policy}|{seed}"

    def is_done(self, claim_id: str, policy: str, seed: int) -> bool:
        return self.episode_key(claim_id, policy, seed) in self._done

    def append(self, config: RunConfig, result: AgentResult) -> None:
        row = {"config": config.to_dict(), "result": result.to_dict()}
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        self._done.add(self.episode_key(result.claim_id, config.policy, config.seed))

    def load(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines()
                if line.strip()]

    def __len__(self) -> int:
        return len(self._done)


def summarise_usage(rows: list[dict]) -> dict:
    """Per-run cost totals. Index and judge costs are reported separately."""
    totals = {"episodes": len(rows), "input_tokens": 0, "output_tokens": 0,
              "cached_tokens": 0, "llm_calls": 0, "tool_calls": 0,
              "external_calls": 0, "cost_usd": 0.0, "elapsed_ms": 0}
    for row in rows:
        usage = row["result"]["usage"]
        for key in totals:
            if key in usage:
                totals[key] += usage[key]
    totals["cost_usd"] = round(totals["cost_usd"], 6)
    if totals["episodes"]:
        totals["mean_cost_usd_per_episode"] = round(
            totals["cost_usd"] / totals["episodes"], 6)
        totals["mean_tool_calls_per_episode"] = round(
            totals["tool_calls"] / totals["episodes"], 3)
    return totals
