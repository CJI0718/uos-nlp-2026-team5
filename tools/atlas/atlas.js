"use strict";
(() => {
  const data = JSON.parse(document.getElementById("atlas-data").textContent);
  const byId = new Map(data.tasks.map(t => [t.id, t]));
  const $ = id => document.getElementById(id);
  const cards = [...document.querySelectorAll(".task-card")], papers = [...document.querySelectorAll(".ref-item")];
  const KEY = "uos-team5-research-atlas-v1";
  let selected = [], notes = {}, teamNote = "", storageOK = true, toastTimer;
  try {
    const state = JSON.parse(localStorage.getItem(KEY) || "{}");
    selected = Array.isArray(state.selected) ? [...new Set(state.selected.filter(x => byId.has(x)))].slice(0, 4) : [];
    notes = state.notes && typeof state.notes === "object" && !Array.isArray(state.notes) ? state.notes : {};
    teamNote = typeof state.teamNote === "string" ? state.teamNote : "";
  } catch (_) { storageOK = false; }
  function status() {
    $("storage-status").textContent = storageOK
      ? "이 브라우저에 자동 저장됩니다. 팀원과 자동 동기화되지 않습니다."
      : "브라우저 저장소를 사용할 수 없습니다. 화면을 닫기 전에 Markdown으로 내보내세요.";
  }
  function save() {
    try { localStorage.setItem(KEY, JSON.stringify({ selected, notes, teamNote })); }
    catch (_) { storageOK = false; }
    status();
  }
  function toast(text) {
    $("toast").textContent = text; $("toast").classList.add("show");
    clearTimeout(toastTimer); toastTimer = setTimeout(() => $("toast").classList.remove("show"), 3000);
  }
  function filter() {
    const words = $("task-search").value.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
    const theme = $("theme-filter").value, difficulty = $("difficulty-filter").value;
    let count = 0;
    for (const card of cards) {
      const show = words.every(w => card.dataset.search.includes(w))
        && (!theme || card.dataset.theme === theme) && (!difficulty || card.dataset.difficulty === difficulty);
      card.hidden = !show; if (show) count++;
    }
    $("result-count").textContent = count + " / " + cards.length + "개 후보";
    $("empty-results").hidden = count !== 0;
  }
  function filterPapers() {
    const words = $("paper-search").value.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
    let count = 0;
    papers.forEach(p => { p.hidden = !words.every(w => p.dataset.search.includes(w)); if (!p.hidden) count++; });
    $("paper-count").textContent = count + " / " + papers.length + "건";
  }
  function element(tag, text, cls) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (cls) node.className = cls;
    return node;
  }
  function renderSelection() {
    document.querySelectorAll("[data-pick]").forEach(b => {
      const active = selected.includes(b.dataset.pick);
      b.setAttribute("aria-pressed", String(active)); b.textContent = active ? "비교에서 빼기" : "비교에 담기";
    });
    $("selection-count").textContent = "선택 " + selected.length + " / 4";
    const comparison = $("comparison"), noteBox = $("candidate-notes");
    comparison.replaceChildren(); noteBox.replaceChildren();
    if (!selected.length) {
      comparison.className = "callout"; comparison.textContent = "아직 선택한 후보가 없습니다.";
      noteBox.append(element("p", "후보를 비교에 담으면 후보별 논의 메모가 나타납니다.")); return;
    }
    comparison.className = "table-scroll"; comparison.tabIndex = 0;
    const table = element("table", undefined, "compare-table"), thead = element("thead"), header = element("tr");
    header.append(element("th", "비교 축"));
    for (const id of selected) {
      const th = element("th"), a = element("a", id + " · " + byId.get(id).title);
      a.href = "#task-" + id; th.append(a); header.append(th);
    }
    thead.append(header); table.append(thead);
    const body = element("tbody");
    const fields = [["질문", "problem"], ["Agent 업무", "task"], ["평가 단위", "unit"], ["비교 조건", "compare"],
      ["지표", "metrics"], ["구현", "difficulty"], ["비용·학습", "extra"], ["가장 큰 위험", "pitfall"]];
    for (const [title, key] of fields) {
      const row = element("tr"); row.append(element("th", title));
      for (const id of selected) {
        const t = byId.get(id), cell = element("td"), value = t[key] || "기본 평가 사례 50개";
        if (Array.isArray(value)) { const list = element("ul"); value.forEach(x => list.append(element("li", x))); cell.append(list); }
        else cell.textContent = value;
        row.append(cell);
      }
      body.append(row);
    }
    table.append(body); comparison.append(table);
    for (const id of selected) {
      const box = element("article", undefined, "panel note-card");
      box.append(element("h3", id + " · " + byId.get(id).title));
      const label = element("label", "관심 이유 · 우려점 · 다음 확인"), area = element("textarea");
      area.rows = 4; area.value = typeof notes[id] === "string" ? notes[id] : "";
      area.placeholder = "성공 상태를 채점할 수 있을까? 강한 기준선은? 궁금한 실패는?";
      area.addEventListener("input", () => { notes[id] = area.value; save(); });
      label.append(area); box.append(label); noteBox.append(box);
    }
  }
  document.addEventListener("click", event => {
    const button = event.target.closest("[data-pick]");
    if (!button) return;
    const id = button.dataset.pick;
    if (selected.includes(id)) selected = selected.filter(x => x !== id);
    else if (selected.length < 4) selected.push(id);
    else { toast("최대 4개까지 비교할 수 있습니다. 먼저 하나를 빼주세요."); return; }
    save(); renderSelection();
  });
  $("clear-selection").addEventListener("click", () => { selected = []; save(); renderSelection(); });
  $("task-search").addEventListener("input", filter);
  $("theme-filter").addEventListener("change", filter);
  $("difficulty-filter").addEventListener("change", filter);
  $("paper-search").addEventListener("input", filterPapers);
  $("reset-filters").addEventListener("click", () => {
    $("task-search").value = $("theme-filter").value = $("difficulty-filter").value = ""; filter();
  });
  $("expand-visible").addEventListener("click", () => cards.forEach(c => { if (!c.hidden) c.open = true; }));
  $("collapse-all").addEventListener("click", () => cards.forEach(c => c.open = false));
  function navigateHash() {
    let id;
    try { id = decodeURIComponent(location.hash.slice(1)); } catch (_) { return; }
    const target = $(id);
    if (!target) return;
    if (target.matches(".task-card")) {
      $("task-search").value = $("theme-filter").value = $("difficulty-filter").value = ""; filter();
    }
    if (target.matches(".ref-item")) { $("paper-search").value = ""; filterPapers(); }
    if (target.tagName === "DETAILS") target.open = true;
    for (let p = target.parentElement; p; p = p.parentElement) if (p.tagName === "DETAILS") p.open = true;
    requestAnimationFrame(() => target.scrollIntoView({ block: "start" }));
  }
  window.addEventListener("hashchange", navigateHash);
  document.addEventListener("click", event => {
    const a = event.target.closest('a[href^="#"]');
    if (a && a.getAttribute("href") === location.hash) navigateHash();
  });
  function budget() {
    const ids = ["budget-cases", "budget-conditions", "budget-repeats", "budget-calls"];
    const values = ids.map(id => Number($(id).value));
    if (ids.some(id => !$(id).checkValidity()) || values.some(v => !Number.isFinite(v) || v < 0)) {
      $("budget-result").textContent = "유효한 범위의 숫자를 입력해주세요."; return;
    }
    const episodes = values[0] * values[1] * values[2], calls = episodes * values[3];
    $("budget-result").textContent = episodes.toLocaleString("ko-KR") + " episodes · " + calls.toLocaleString("ko-KR") + " 모델 요청 가정";
  }
  ["budget-cases", "budget-conditions", "budget-repeats", "budget-calls"].forEach(id => $(id).addEventListener("input", budget));
  $("team-note").value = teamNote;
  $("team-note").addEventListener("input", () => { teamNote = $("team-note").value; save(); });
  $("export-notes").addEventListener("click", () => {
    const lines = ["# NLP 5조 연구 주제 논의", "", "후보집 버전: " + data.date, "", "큰 방향은 팩트체크 Agent. 세부 태스크·모델·예산 미확정. 아래 후보는 탐색 기록이며 실험 결과가 아님.", ""];
    for (const id of selected) {
      const t = byId.get(id);
      lines.push("## " + id + ". " + t.title, "", "- 연구 질문: " + t.problem, "- 업무: " + t.task,
        "- 평가 단위: " + (t.unit || "기본 평가 사례 50개"), "- 주요 지표: " + t.metrics.join(" / "),
        "- 우려: " + t.pitfall, "- 참고 ID: " + t.refs.join(", "), "", "### 논의 메모", "", notes[id] || "(미작성)", "");
    }
    lines.push("## 팀 전체 메모", "", teamNote || "(미작성)", "", "## 선택에서 제외했지만 보존된 메모", "");
    for (const [id, note] of Object.entries(notes)) {
      if (!selected.includes(id) && byId.has(id) && typeof note === "string" && note.trim())
        lines.push("### " + id + ". " + byId.get(id).title, "", note, "");
    }
    lines.push("공유 위치: GitHub PR 또는 Issue. 파일 생성은 자동 게시가 아닙니다.", "");
    const blob = new Blob(["\uFEFF" + lines.join("\n")], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob), a = element("a");
    a.href = url; a.download = "team5-topic-discussion-" + data.date + ".md";
    document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 1500);
    toast("Markdown 파일을 내려받았습니다. PR 또는 Issue에서 팀원과 공유하세요.");
  });
  let printState = null;
  function beforePrint() {
    if (printState) return;
    const details = [...document.querySelectorAll("details")], hidden = [...document.querySelectorAll("[hidden]")];
    printState = { details: details.map(d => [d, d.open]), hidden };
    details.forEach(d => d.open = true); cards.forEach(c => c.hidden = false); papers.forEach(p => p.hidden = false);
  }
  function afterPrint() {
    if (!printState) return;
    printState.details.forEach(([d, open]) => d.open = open); printState.hidden.forEach(d => d.hidden = true);
    printState = null; filter(); filterPapers();
  }
  window.addEventListener("beforeprint", beforePrint); window.addEventListener("afterprint", afterPrint);
  $("print-atlas").addEventListener("click", () => { beforePrint(); window.print(); });
  status(); filter(); filterPapers(); renderSelection(); budget(); navigateHash();
})();
