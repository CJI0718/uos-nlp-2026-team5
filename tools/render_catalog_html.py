"""Build the offline research atlas from reviewed JSON. Standard library only."""
import json
import re
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "research"
DATA = json.loads((DOC / "candidates.json").read_text(encoding="utf-8"))
GUIDE = json.loads((DOC / "atlas_guide.json").read_text(encoding="utf-8"))
REFS = {r["id"]: r for r in DATA["references"]}
THEMES = {t["id"]: t for t in GUIDE["themes"]}
ASSETS = Path(__file__).parent / "atlas"
DIFF = {"D1": "비교적 낮음", "D2": "중간", "D3": "높음"}


def e(value):
    return escape(str(value), quote=True)


def ul(items):
    return "<ul>" + "".join(f"<li>{e(x)}</li>" for x in items) + "</ul>"


def cites(ids):
    return " ".join(f'<a class="ref-chip" href="#ref-{e(r)}">{e(r)}</a>' for r in ids)


def table(heads, rows):
    return '<div class="table-scroll" tabindex="0"><table><thead><tr>' + "".join(
        f"<th>{e(h)}</th>" for h in heads
    ) + "</tr></thead><tbody>" + "".join(
        "<tr>" + "".join(f"<td>{v}</td>" for v in row) + "</tr>" for row in rows
    ) + "</tbody></table></div>"


def md_inline(text):
    # Escape source first: archived Markdown cannot inject HTML or scripts.
    text = e(text)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^\s)]+|[A-Za-z0-9_./-]+\.md|research_catalog\.html)\)",
                  r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"&#x60;([^&]+?)&#x60;", r"<code>\1</code>", text)
    text = re.sub(r"\x60([^\x60]+)\x60", r"<code>\1</code>", text)
    return text


def md_block(source):
    """Small safe renderer for the three checked-in research notes."""
    out, paragraph, in_code, code, rows = [], [], False, [], []

    def flush():
        if paragraph:
            out.append("<p>" + "<br>".join(paragraph) + "</p>")
            paragraph.clear()
        if rows:
            heads = rows[0]
            body = [r for r in rows[1:] if not all(re.fullmatch(r"[-: ]+", c) for c in r)]
            out.append(table(heads, [[md_inline(c) for c in r] for r in body]))
            rows.clear()

    for line in source.splitlines():
        if line.startswith(("~~~", chr(96) * 3)):
            flush()
            if in_code:
                out.append("<pre>" + e("\n".join(code)) + "</pre>")
                code.clear()
            in_code = not in_code
            continue
        if in_code:
            code.append(line)
            continue
        if line.startswith("|"):
            if paragraph:
                out.append("<p>" + "<br>".join(paragraph) + "</p>")
                paragraph.clear()
            rows.append([c.strip() for c in line.strip("|").split("|")])
            continue
        if not line.strip():
            flush()
        elif line.startswith("#"):
            flush()
            match = re.match(r"(#+)\s+(.*)", line)
            if match:
                level = min(len(match[1]) + 2, 6)
                out.append(f"<h{level}>{md_inline(match[2])}</h{level}>")
        elif line.strip() == "---":
            flush()
            out.append("<hr>")
        else:
            paragraph.append(md_inline(line))
    flush()
    return "".join(out)


def theory(g):
    concepts = "".join(
        f'<div class="concept"><h4>{e(term)}</h4><p>{e(desc)}</p><p class="small">실험 연결 · {e(ex)}</p></div>'
        for term, desc, ex in g["concepts"]
    )
    related = [t for t in DATA["tasks"] if t["theme"] == g["id"]]
    cards = "".join(f'<a class="topic-link" href="#task-{e(t["id"])}"><b>{e(t["id"])}</b> {e(t["title"])}</a>'
                    for t in related)
    return f"""
    <details class="theory-card" id="{e(g['slug'])}">
      <summary><span class="eyebrow">{e(g['eyebrow'])}</span><h3>{e(g['id'])}</h3>
        <span>{e(g['lead'])}</span><span class="count">{len(related)}개 후보 · 배경 펼치기</span></summary>
      <div class="detail-body">
        <div class="flow" aria-label="과정">{''.join(f'<span>{e(x)}</span>' for x in g['flow'])}</div>
        <div class="concept-grid">{concepts}</div>
        <h4>검증할 가설</h4><p>{e(g['hypothesis'])}</p>
        <div class="two-col"><div><h4>통제할 조건</h4>{ul(g['controls'])}</div>
        <div><h4>팀 토론 질문</h4>{ul(g['questions'])}</div></div>
        <p class="callout"><b>작게 시작하기</b> · {e(g['minimum'])}</p>
        <p>연결 논문 {cites(g['papers'])}</p><div class="topic-links">{cards}</div>
      </div>
    </details>"""


def cost_description(t):
    low, high = t["calls"]
    if t.get("cost_exception"):
        return e(t["extra"])
    mult = t.get("multiplier", 2 if t["id"] == "A1" else 1)
    text = f"50사례 × 3조건 × 1반복 가정: {150 * low * mult:,}–{150 * high * mult:,}회."
    if mult > 1:
        text += " paired 입력 2배 포함."
    return e(text + " 실측·의무 횟수 아님. " + t["extra"])


def candidate(t):
    ident = e(t["id"])
    related = "".join(f'<a class="ref-chip" href="#task-{e(x)}">{e(x)}</a>' for x in t.get("related", []))
    rl = ""
    if "observation" in t:
        rl = table(["정책 관찰", "행동", "보상 제안"],
                   [[e(t["observation"]), e(t["actions"]), e(t["reward"])]])
    bins = "".join(f'<span>{e(label)} <b>{n}</b></span>' for label, n in t["data"])
    search = e(" ".join([t["id"], t["theme"], t["title"], t["problem"], t["task"],
                         t["example"], " ".join(t["metrics"]), " ".join(t["extensions"])]).lower())
    unit = t.get("unit", "기본 평가 사례 50개")
    return f"""
    <details class="task-card" id="task-{ident}" data-id="{ident}" data-theme="{e(t['theme'])}"
        data-difficulty="{e(t['difficulty'])}" data-search="{search}">
      <summary><span class="task-id">{ident}</span><span class="summary-title">{e(t['title'])}
        <small>{e(t['theme'])} · {e(t['difficulty'])} {e(DIFF[t['difficulty']])} · {e(unit)}</small></span>
        <span class="new-tag">{'NEW · 10.23' if t.get('added_at') == '2026-10-23' else '기존 후보'}</span></summary>
      <div class="detail-body">
        <div class="card-toolbar"><button class="pick" data-pick="{ident}" aria-pressed="false">비교에 담기</button>
        <a href="#{e(THEMES[t['theme']]['slug'])}">배경 이론 보기</a>
        <a href="#team">토론 공간</a></div>
        <h4>문제 · 왜 이 업무인가?</h4><p>{e(t['problem'])}</p>
        <h4>Agent가 할 일</h4><p>{e(t['task'])}</p>
        <blockquote>{e(t['example'])}</blockquote>{rl}
        <h4>평가 50개 구성안 <span class="small">아직 작성·실행하지 않은 설계</span></h4>
        <div class="bins">{bins}<strong>합계 50</strong></div>
        <p><b>정답과 평가 단위</b> · {e(t['gold'])}</p>
        <div class="two-col"><div><h4>비교 조건</h4>{ul(t['compare'])}</div>
          <div><h4>평가 지표</h4>{ul(t['metrics'])}</div></div>
        <h4>구현 · 비용</h4><p>{e(t['difficulty'])} {e(DIFF[t['difficulty']])}.
        요청 가정 {t['calls'][0]}–{t['calls'][1]}회 / {e(unit)}·조건.</p>
        <p class="small">{cost_description(t)}</p>
        <p class="warning"><b>해석 주의</b> · {e(t['pitfall'])}</p>
        <h4>뻗어나갈 방향</h4>{ul(t['extensions'])}
        <p>관련 논문 {cites(t['refs'])}</p>
        {f'<p>겹치는 관심 · {related}</p>' if related else ''}
      </div>
    </details>"""


def bibliography():
    out = []
    for r in DATA["references"]:
        linked = [t for t in DATA["tasks"] if r["id"] in t["refs"]]
        date = r.get("verified_at", "2026-10-11 초기 조사 기록")
        verification = r.get("verification", "기존 원논문/공식 자료 선별 메모. 이번 업데이트에서 전문 재검증·재현하지 않음.")
        kind = "논문" if r["id"].startswith("P") else "공식 문서" if r["id"].startswith("D") else "아이디어"
        searchable = e(" ".join([r["id"], r["title"], r["venue"], r["idea"], r["caveat"]]).lower())
        out.append(f"""
        <article class="ref-item" id="ref-{e(r['id'])}" data-search="{searchable}">
          <div class="ref-top"><span class="task-id">{e(r['id'])}</span><span class="badge">{kind}</span>
            <span class="small">{e(r['venue'])}</span></div>
          <h3><a href="{e(r['url'])}" target="_blank" rel="noopener noreferrer">{e(r['title'])} ↗</a></h3>
          <p><b>문제와 연결 아이디어</b> · {e(r['idea'])}</p>
          <p><b>해석 경계</b> · {e(r['caveat'])}</p>
          <p class="small">확인일 {e(date)} · {e(verification)}</p>
          <p class="small">후보로 돌아가기 {' '.join(f'<a class="ref-chip" href="#task-{e(t["id"])}">{e(t["id"])}</a>' for t in linked) or '배경 자료'}</p>
        </article>""")
    return "".join(out)


def main():
    tasks, refs = DATA["tasks"], DATA["references"]
    counts = (len(tasks), len(GUIDE["themes"]), sum(r["id"].startswith("P") for r in refs))
    overview = table(["분류", "핵심 질문", "후보"], [
        [f'<a href="#{e(g["slug"])}">{e(g["id"])}</a>', e(g["hypothesis"]),
         str(sum(t["theme"] == g["id"] for t in tasks))]
        for g in GUIDE["themes"]])
    overlaps = table(["연결 ID", "차이를 읽는 법"], [
        [" ".join(f'<a class="ref-chip" href="#task-{e(i)}">{e(i)}</a>' for i in row[:-1]), e(row[-1])]
        for row in GUIDE["overlaps"]])
    metrics = table(["지표", "뜻·계산", "주의"], [[e(x) for x in row] for row in GUIDE["metrics"]])
    appendices = []
    for filename, title in [
        ("multimodal_comparison.md", "10.14 · 멀티모달 표현·생성 경로의 상세 비교"),
        ("agent_tasks_20261023.md", "10.23 · 에이전트가 필요한 업무 7가지"),
        ("rl_multimodal_20261023.md", "10.23 · 강화학습과 멀티모달 연계 6가지"),
    ]:
        appendices.append(f'<details class="archive"><summary>{e(title)}</summary><div class="detail-body">'
                          f'<p><a href="{filename}">GitHub용 Markdown 원문</a></p>'
                          + md_block((DOC / filename).read_text(encoding="utf-8")) + "</div></details>")
    payload = json.dumps({"tasks": tasks, "date": DATA["date"]}, ensure_ascii=False).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    replacements = {
        "STYLE": (ASSETS / "atlas.css").read_text(encoding="utf-8"),
        "SCRIPT": (ASSETS / "atlas.js").read_text(encoding="utf-8"),
        "DATE": e(DATA["date"]), "TASK_COUNT": str(counts[0]), "THEME_COUNT": str(counts[1]),
        "PAPER_COUNT": str(counts[2]), "REF_COUNT": str(len(refs)),
        "OVERVIEW": overview, "THEORY": "".join(theory(g) for g in GUIDE["themes"]),
        "TASKS": "".join(candidate(t) for t in tasks), "OVERLAPS": overlaps,
        "METRICS": metrics, "PAPERS": bibliography(), "ARCHIVES": "".join(appendices),
        "MEETING": ul(GUIDE["meeting"]), "PAYLOAD": payload,
        "THEME_OPTIONS": "".join(f'<option value="{e(g["id"])}">{e(g["id"])}</option>' for g in GUIDE["themes"]),
        "THEME_NAV": "".join(f'<a href="#{e(g["slug"])}">{e(g["id"])}</a>' for g in GUIDE["themes"])
    }
    html = (ASSETS / "shell.html").read_text(encoding="utf-8")
    for key, value in replacements.items():
        html = html.replace("@@" + key + "@@", value)
    assert not re.search(r"@@[A-Z_]+@@", html), "Unresolved template token"
    html = "\n".join(line.rstrip() for line in html.splitlines()) + "\n"
    out = DOC / "research_catalog.html"
    out.write_text(html, encoding="utf-8", newline="\n")
    print(json.dumps({"output": str(out), "tasks": len(tasks), "references": len(refs),
                      "bytes": out.stat().st_size, "external_runtime_dependencies": 0}, ensure_ascii=False))


if __name__ == "__main__":
    main()
