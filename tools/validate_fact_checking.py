"""Validate research documents only. No network, model calls, or experiments."""
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/research/fact_checking"


def validate():
    data = json.loads((DOC / "papers.json").read_text(encoding="utf-8"))
    papers = data["papers"]
    log = json.loads((DOC / "research_log.json").read_text(encoding="utf-8"))
    assert len(papers) == 35
    assert len({p["id"] for p in papers}) == 35
    assert len({p["url"] for p in papers}) == 35
    assert sum(p["kind"] == "paper" for p in papers) == 34
    assert sum(p["kind"] == "thesis" for p in papers) == 1
    assert log["search_calls"] == len(log["queries"])
    assert log["requested_result_items"] == sum(q["numResults"] for q in log["queries"])
    assert log["selected_academic_works"] == len(papers)
    assert log["execution"]["experimental_llm_calls"] == 0
    assert not log["execution"]["api_key_use"]
    literature = (DOC / "literature.md").read_text(encoding="utf-8")
    for paper in papers:
        for key in ["authors", "title", "publication", "theme", "paper_finding",
                    "team_application", "limitation", "verification_level", "reuse_status"]:
            assert paper[key], (paper["id"], key)
        assert paper["year"] <= 2026
        assert paper["execution_status"] == "not_reproduced"
        assert paper["url"] in log["unique_fetch_urls"], paper["id"]
        assert f'### {paper["id"]}. {paper["title"]}' in literature
        assert f'<a id="{paper["id"].lower()}"></a>' in literature
        assert f'- **저자:** {paper["authors"]}' in literature
    files = list(DOC.glob("*.md")) + [
        ROOT / "README.md", ROOT / "docs/research/README.md",
        ROOT / "docs/decisions/README.md",
        ROOT / "docs/decisions/001-fact-checking-direction.md",
    ]
    links = 0
    for file in files:
        text = file.read_text(encoding="utf-8")
        assert not re.search(r"(?:[CD]:[\\/]Users|D:[\\/]Vaults|sk-or-v1-[A-Za-z0-9]+)", text)
        for target in re.findall(r"\]\(([^\s)]+)\)", text):
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc:
                continue
            dest = (file.parent / unquote(parsed.path)).resolve() if parsed.path else file
            assert dest.is_relative_to(ROOT) and dest.exists(), (file, target)
            if parsed.fragment:
                # All local fragment links in this packet use explicit FC anchors.
                content = dest.read_text(encoding="utf-8")
                assert f'id="{unquote(parsed.fragment)}"' in content, (file, target)
            links += 1
    evaluation = (DOC / "evaluation.md").read_text(encoding="utf-8")
    bins = re.findall(r"^\| (?:직접 문장|복수 근거|게시일|수치|범위).*\| (\d+) \| (\d+) \| (\d+) \| (\d+) \|$", evaluation, re.M)
    assert len(bins) == 5
    assert all(sum(map(int, row[:3])) == int(row[3]) for row in bins)
    assert sum(int(row[3]) for row in bins) == 50
    assert "큰 방향 합의" in (ROOT / "README.md").read_text(encoding="utf-8")
    print(json.dumps({"academic_works": len(papers), "papers": 34, "theses": 1,
                      "local_links_checked": links, "proposed_case_total": 50,
                      "network_or_model_calls": 0, "status": "pass"}, ensure_ascii=False))


if __name__ == "__main__":
    validate()
