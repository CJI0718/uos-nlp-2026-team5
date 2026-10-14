"""Check catalogue consistency and local links. Standard library only; no API calls."""
import json
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "docs" / "research"


class CatalogueParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "a" and "href" in attrs:
            self.links.append(attrs["href"])


def check_local_link(base, target):
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return
    path = (base / unquote(parsed.path)).resolve()
    assert path.is_relative_to(ROOT), f"Link escapes repository: {target}"
    assert path.exists(), f"Missing local link: {base} -> {target}"


def main():
    data = json.loads((RESEARCH / "candidates.json").read_text(encoding="utf-8"))
    refs = {r["id"]: r for r in data["references"]}
    themes = {t["id"]: t for t in data["themes"]}
    tasks = {t["id"]: t for t in data["tasks"]}
    assert len(refs) == len(data["references"]), "Duplicate reference ID"
    assert len(themes) == len(data["themes"]), "Duplicate theme ID"
    assert len(tasks) == len(data["tasks"]), "Duplicate task ID"
    assert len({r["url"] for r in refs.values()}) == len(refs), "Duplicate source URL"
    for t in tasks.values():
        assert t["theme"] in themes, t["id"]
        assert sum(n for _, n in t["data"]) == 50, t["id"]
        assert all(isinstance(n, int) and n > 0 for _, n in t["data"]), t["id"]
        assert all(r in refs for r in t["refs"]), t["id"]
        assert 0 <= t["calls"][0] <= t["calls"][1], t["id"]
    for th in themes.values():
        assert all(r in refs for r in th["papers"]), th["id"]
    for r in refs.values():
        assert r["url"].startswith("https://"), r["id"]
    markdown = (RESEARCH / "candidates.md").read_text(encoding="utf-8")
    html = (RESEARCH / "research_catalog.html").read_text(encoding="utf-8")
    parser = CatalogueParser()
    parser.feed(html)
    ids = set(parser.ids)
    assert len(ids) == len(parser.ids), "Duplicate HTML anchor ID"
    for task_id in tasks:
        assert f"### {task_id}. " in markdown, task_id
        assert f"task-{task_id}" in ids, task_id
    for ref_id in refs:
        assert f"### {ref_id}. " in markdown, ref_id
        assert f"ref-{ref_id}" in ids, ref_id
    for link in parser.links:
        if link.startswith("#"):
            assert link[1:] in ids, f"Broken HTML fragment: {link}"
        check_local_link(RESEARCH, link)
    assert f"{len(tasks)}개" in markdown and f"{len(tasks)}개" in html
    assert "{TASK_COUNT}" not in html, "Unrendered template variable"
    for path in [ROOT / "README.md", RESEARCH / "README.md",
                 RESEARCH / "candidates.md", RESEARCH / "multimodal_comparison.md"]:
        source = path.read_text(encoding="utf-8")
        for target in re.findall(r"\]\(([^\s)]+)\)", source):
            check_local_link(path.parent, target)
    print(json.dumps({"tasks": len(tasks), "references": len(refs),
                      "tasks_per_theme": dict(Counter(t["theme"] for t in tasks.values())),
                      "case_partition": "all 50", "local_links": "pass",
                      "html_anchors": "pass", "network_or_model_calls": 0},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
