"""Render the reviewed proposal catalogue as GitHub-readable Markdown. No API calls."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
research = root / "docs" / "research"
data = json.loads((research / "candidates.json").read_text(encoding="utf-8"))
refs = {r["id"]: r for r in data["references"]}
lines = [f"# AI Agents 연구 후보 {len(data['tasks'])}개", "", f"최초 조사: {data.get('initial_date', data['date'])}. 최근 추가: {data['date']}. 주제 미선정 · 실험 미실행.", "", "이 문서는 원논문/공식 자료를 탐색해 만든 연구 제안입니다. 모든 논문 전문 정독이나 구현 재현을 했다는 뜻이 아닙니다. 최근 추가가 기존 논문 전체의 재검증을 뜻하지는 않습니다.", "", "각 후보의 50개는 작성할 평가 사례 구성안이며, 이미 데이터가 존재한다는 뜻이 아닙니다.", "", "D1=비교적 낮음, D2=중간, D3=높음. 호출량은 사례당·조건당 계획용 추정으로 구축·judge 비용은 별도입니다.", "", "새 주제: [멀티모달 입력·기호/도구 생성 비교 설계와 논문 메모](multimodal_comparison.md)", ""]
for theme in data["themes"]:
    lines += ["## " + theme["title"], "", theme["question"], ""]
    for t in data["tasks"]:
        if t["theme"] != theme["id"]:
            continue
        assert sum(n for _, n in t["data"]) == 50
        lines += ["### " + t["id"] + ". " + t["title"], "", "- **문제:** " + t["problem"], "- **업무:** " + t["task"], "- **예시:** " + t["example"], "- **50개 구성:** " + " / ".join(label + " " + str(n) + "개" for label, n in t["data"]), "- **정답 정보:** " + t["gold"], "- **비교 조건:** " + " / ".join(t["compare"]), "- **주요 지표:** " + " / ".join(t["metrics"]), "- **구현 부담:** " + t["difficulty"], "- **호출 추정:** 사례당·조건당 " + str(t["calls"][0]) + "–" + str(t["calls"][1]) + "회. " + t["extra"], "- **주의:** " + t["pitfall"], "- **확장:** " + " / ".join(t["extensions"]), "- **참고:** " + ", ".join("[" + rid + " " + refs[rid]["title"] + "](" + refs[rid]["url"] + ")" for rid in t["refs"]), ""]
paper_count = sum(r['id'].startswith('P') for r in data['references'])
lines += ["## 참고자료의 확인 수준", "", f"아래에는 논문 {paper_count}편과 아이디어 자료 {len(refs) - paper_count}건이 포함됩니다. 학회/저널, 워크숍/포스터, preprint, 실무 아이디어를 구분합니다.", ""]
for ref in data["references"]:
    lines += ["### " + ref["id"] + ". " + ref["title"], "", "- " + ref["venue"], "- [원문](" + ref["url"] + ")", "- 연결 아이디어: " + ref["idea"], "- 주의: " + ref["caveat"], ""]
    if "authors" in ref:
        lines += ["- 저자: " + ref["authors"], "- 확인일: " + ref["verified_at"], "- 확인 수준: " + ref["verification"], ""]
(research / "candidates.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
print(f"Rendered {len(data['tasks'])} proposals; all case partitions sum to 50. No experiments executed.")
