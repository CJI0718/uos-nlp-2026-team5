// Schedule assistant UI. Every string from the server (including web page text)
// goes through esc() or textContent; nothing is inserted as raw HTML.

const $ = (sel) => document.querySelector(sel);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => (
  { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const safeUrl = (u) => (/^https?:\/\//i.test(u || "") ? u : "#");

const STATUS = {
  auto_added: { label: "자동 등록", cls: "ok" },
  added: { label: "승인함", cls: "ok" },
  pending_approval: { label: "승인 대기", cls: "warn" },
  changed: { label: "변경됨", cls: "warn" },
  tracking: { label: "추적 중", cls: "muted" },
  rejected: { label: "제외", cls: "bad" },
  undone: { label: "되돌림", cls: "muted" },
  expired: { label: "만료", cls: "muted" },
  occurred: { label: "지남", cls: "muted" },
  error: { label: "오류", cls: "bad" },
};
const STEP_ICON = {
  info: "▸", search: "⌕", extract: "✦", candidate: "◇", think: "…", read: "▤", calc: "⏱",
  verdict: "⚖", decision: "●", skip: "↷", error: "✕", budget: "⛔", done: "■",
};
const VIEWS = {
  home: { title: "다가오는 일정", sub: "비서가 확인한 일정과 확인 중인 일정입니다." },
  approvals: { title: "승인 대기", sub: "비서가 자동으로 넣지 않은 일정입니다. 이유를 보고 승인하거나 제외하세요." },
  tracking: { title: "추적 중", sub: "아직 공식 발표가 없어 기다리는 일정입니다. 다음 실행 때 다시 확인합니다." },
  runs: { title: "실행 기록", sub: "비서가 언제 무엇을 했는지, 비용과 검색 횟수입니다." },
  settings: { title: "설정", sub: "자동 실행, 예산, 관심사, 모델입니다." },
};

const app = { view: "home", state: null, events: [], threadRun: null };

async function api(path, opts = {}) {
  const res = await fetch(path, {
    ...opts,
    headers: { "Content-Type": "application/json", "X-Requested-With": "assistant", ...(opts.headers || {}) },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

function toast(text) {
  const t = $("#toast");
  t.textContent = text;
  t.classList.remove("hidden");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => t.classList.add("hidden"), 2600);
}

// ---- time helpers ---------------------------------------------------------------
const WEEK = ["일", "월", "화", "수", "목", "금", "토"];
function parseKst(s) {
  if (!s) return null;
  const iso = s.length === 10 ? `${s}T00:00:00+09:00` : `${s.replace(" ", "T")}:00+09:00`;
  return new Date(iso);
}
function dayLabel(s) {
  const d = parseKst(s);
  if (!d) return "날짜 미정";
  const k = new Date(d.getTime() + 9 * 3600e3);
  return `${k.getUTCMonth() + 1}월 ${k.getUTCDate()}일 (${WEEK[k.getUTCDay()]})`;
}
function dday(s) {
  const d = parseKst(s);
  if (!d) return "";
  const today = new Date(new Date().toLocaleString("en-US", { timeZone: "Asia/Seoul" }));
  today.setHours(0, 0, 0, 0);
  const k = new Date(d.getTime() + 9 * 3600e3);
  const target = new Date(k.getUTCFullYear(), k.getUTCMonth(), k.getUTCDate());
  const n = Math.round((target - today) / 864e5);
  return n === 0 ? "오늘" : n > 0 ? `D-${n}` : `D+${-n}`;
}
function clock(ev) {
  if (!ev.start_kst) return "미정";
  return ev.precision === "date" || ev.start_kst.length === 10 ? "종일" : ev.start_kst.slice(11, 16);
}
function localTime(ev) {
  if (!ev.local_tz || ev.local_tz === "Asia/Seoul" || ev.precision === "date" || !ev.start_kst) return "";
  try {
    const d = parseKst(ev.start_kst);
    const f = new Intl.DateTimeFormat("ko-KR", { timeZone: ev.local_tz, month: "numeric", day: "numeric",
      hour: "2-digit", minute: "2-digit", hour12: false, timeZoneName: "short" });
    return `현지 ${f.format(d)}`;
  } catch { return ""; }
}

// ---- rail -------------------------------------------------------------------------
function renderRail() {
  const s = app.state;
  if (!s) return;
  $("#mode-tag").textContent = s.mode === "demo" ? "시연 모드 · 가상 데이터" : `실제 모드 · ${s.model}`;
  $("#badge-approvals").textContent = (s.counts.pending_approval + s.counts.changed) || "";
  $("#badge-tracking").textContent = s.counts.tracking || "";
  const b = s.budget;
  $("#cost-text").textContent = `$${b.spent_usd.toFixed(3)} / $${b.cap_usd.toFixed(2)}`;
  $("#cost-bar").style.width = `${Math.min(100, (b.spent_usd / Math.max(b.cap_usd, 1e-9)) * 100)}%`;
  $("#search-text").textContent = `${b.searches_used} / ${b.cap_searches}`;
  $("#search-bar").style.width = `${Math.min(100, (b.searches_used / Math.max(b.cap_searches, 1)) * 100)}%`;
  const sc = s.schedule;
  let line = sc.enabled ? `자동 실행 <b>매일 ${esc(sc.daily_at)}</b>` : "자동 실행 <b>꺼짐</b>";
  if (sc.once_at) line += `<br>예약 <b>${esc(sc.once_at.slice(11, 16))}</b>에 한 번`;
  $("#sched-line").innerHTML = line;
  const btn = $("#run-btn");
  btn.disabled = s.running;
  btn.textContent = s.running ? "실행 중…" : "지금 실행";
  $("#live-dot").classList.toggle("on", s.running);
  $("#act-sub").textContent = s.running ? "실행 중" : s.last_run ? `마지막 실행 #${s.last_run.id}` : "아직 실행 없음";
}

// ---- views ------------------------------------------------------------------------
function chipsFor(ev) {
  const st = STATUS[ev.status] || { label: ev.status, cls: "muted" };
  const out = [`<span class="chip ${st.cls}">${esc(st.label)}</span>`];
  if (ev.corrected && ev.status !== "tracking") out.push(`<span class="chip accent">정정됨</span>`);
  if (ev.official_url) out.push(`<span class="chip info">공식 출처</span>`);
  return out.join("");
}

function card(ev, { actions = false } = {}) {
  const loc = localTime(ev);
  const reasons = (ev.status === "pending_approval" || ev.status === "changed") && ev.reasons_text?.length
    ? `<div class="reason-list">${ev.reasons_text.map((r) => `<span class="chip warn">${esc(r)}</span>`).join("")}</div>` : "";
  const acts = actions ? `<div class="row-actions">
      <button class="btn small ok" data-act="approve" data-id="${ev.id}">승인</button>
      <button class="btn small bad" data-act="reject" data-id="${ev.id}">제외</button></div>` : "";
  return `<div class="card ${ev.status === "tracking" ? "dim" : ""}" data-open="${ev.id}">
    <div class="time">${esc(clock(ev))}<small>${esc(ev.status === "tracking" ? "미확정" : "한국시간")}</small></div>
    <div><div class="title">${esc(ev.title)}</div>
      <div class="meta">${loc ? `<span>${esc(loc)}</span>` : ""}<span>${esc((ev.claim_text || "").slice(0, 80))}</span></div>${reasons}</div>
    <div class="side">${chipsFor(ev)}${acts}</div></div>`;
}

function groupByDay(events) {
  const groups = new Map();
  for (const ev of events) {
    const key = (ev.start_kst || "").slice(0, 10) || "미정";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(ev);
  }
  return [...groups.entries()];
}

function empty(icon, text) {
  return `<div class="empty"><div class="big">${icon}</div>${text}</div>`;
}

function renderHome() {
  const evs = app.events.filter((e) => ["auto_added", "added", "pending_approval", "changed", "tracking"].includes(e.status));
  if (!evs.length) {
    return empty("◎", "아직 일정이 없어요.<br>왼쪽 아래 <b>지금 실행</b>을 누르면 비서가 행사를 찾아 확인합니다.");
  }
  return groupByDay(evs).map(([day, list]) => `
    <div class="day"><h2>${esc(day === "미정" ? "날짜 미정" : dayLabel(day))}</h2><span class="dday">${esc(dday(day))}</span></div>
    ${list.map((e) => card(e)).join("")}`).join("");
}

function renderList(statuses, actions, icon, text) {
  const evs = app.events.filter((e) => statuses.includes(e.status));
  return evs.length ? evs.map((e) => card(e, { actions })).join("") : empty(icon, text);
}

async function renderRuns() {
  const runs = await api("/api/runs");
  if (!runs.length) return empty("≡", "실행 기록이 없어요.");
  const ko = { ok: "완료", running: "실행 중", failed: "실패", budget_stop: "예산 정지", interrupted: "중단됨" };
  return `<table class="table"><thead><tr><th>#</th><th>시작</th><th>계기</th><th>결과</th><th>상태</th>
    <th>모델</th><th>비용</th><th>검색</th></tr></thead><tbody>
    ${runs.map((r) => `<tr class="click" data-run="${r.id}">
      <td class="mono">${r.id}</td><td class="mono">${esc((r.started_at || "").slice(5, 16).replace("T", " "))}</td>
      <td>${esc(r.trigger)}</td><td>${esc(r.summary || "")}</td>
      <td><span class="chip ${r.status === "ok" ? "ok" : r.status === "running" ? "info" : "warn"}">${esc(ko[r.status] || r.status)}</span></td>
      <td class="mono">${r.llm_calls}회</td><td class="mono">$${Number(r.cost_usd).toFixed(4)}</td>
      <td class="mono">${r.search_calls}회</td></tr>`).join("")}</tbody></table>
    <p class="sub" style="margin-top:10px">줄을 누르면 오른쪽 활동창에 그 실행의 단계가 나옵니다.</p>`;
}

async function renderSettings() {
  const s = await api("/api/settings");
  const sc = s.schedule, b = s.budget;
  const keys = Object.entries(s.secrets).map(([k, v]) =>
    `<span class="chip ${v ? "ok" : "bad"}">${esc(k)} ${v ? "있음" : "없음"}</span>`).join("");
  const interests = s.interests.map((i) => `<div class="box" style="padding:12px">
      <b>${esc(i.name)}</b> ${i.enabled ? '<span class="chip ok">켜짐</span>' : '<span class="chip">꺼짐</span>'}
      <p style="margin:6px 0 4px">공식 출처로 인정하는 도메인</p>
      <div class="tags">${i.official_domains.map((d) => `<span class="chip">${esc(d)}</span>`).join("")}</div></div>`).join("");
  return `<div class="settings">
    <div class="box"><h3>자동 실행</h3>
      <p>앱 서버가 켜져 있는 동안 정해진 시각에 혼자 실행합니다. 서버를 끄면 멈춥니다.</p>
      <div class="field"><label>매일 실행</label>
        <label class="switch"><input type="checkbox" id="s-enabled" ${sc.enabled ? "checked" : ""}><span></span></label></div>
      <div class="field"><label>실행 시각</label><input id="s-time" value="${esc(sc.daily_at)}" placeholder="09:00"></div>
      <div class="field"><label>한 번만 예약</label><input id="s-mins" type="number" min="1" value="3"> 분 뒤
        <button class="btn small" id="s-once">예약</button>
        ${sc.once_at ? `<span class="chip accent">${esc(sc.once_at.slice(11, 16))} 예정</span>
        <button class="btn small" id="s-cancel">취소</button>` : ""}</div></div>
    <div class="box"><h3>예산</h3><p>상한에 닿으면 실행을 멈추고 기록합니다. 재시도는 하지 않습니다.</p>
      <div class="field"><label>하루 모델 비용($)</label><input id="b-cost" type="number" step="0.1" value="${b.daily_cost_usd}"></div>
      <div class="field"><label>하루 웹 검색(회)</label><input id="b-search" type="number" value="${b.daily_searches}"></div>
      <div class="field"><label></label><button class="btn primary small" id="b-save">저장</button></div></div>
    <div class="box"><h3>관심사</h3><p>키워드 편집은 다음 단계에서 추가합니다.</p>${interests}</div>
    <div class="box"><h3>모델</h3><p>${esc(s.llm.model)} · ${esc(s.llm.base_url)}</p><div class="tags">${keys}</div></div>
  </div>`;
}

async function render() {
  const v = VIEWS[app.view];
  $("#view-title").textContent = v.title;
  $("#view-sub").textContent = v.sub;
  $("#view-actions").innerHTML = app.view === "home"
    ? `<a class="btn small" href="/api/export.ics">일정 .ics 내보내기</a>` : "";
  let html = "";
  if (app.view === "home") html = renderHome();
  if (app.view === "approvals") html = renderList(["pending_approval", "changed"], true, "◐", "승인할 일정이 없어요.");
  if (app.view === "tracking") html = renderList(["tracking"], false, "◌", "추적 중인 일정이 없어요.");
  if (app.view === "runs") html = await renderRuns();
  if (app.view === "settings") html = await renderSettings();
  $("#view").innerHTML = html;
  if (app.view === "settings") bindSettings();
}

function bindSettings() {
  const put = async (body, msg) => {
    try { await api("/api/settings", { method: "PUT", body: JSON.stringify(body) }); toast(msg); await refresh(); }
    catch (e) { toast(e.message); }
  };
  $("#s-enabled").onchange = (e) => put({ schedule: { enabled: e.target.checked } },
    e.target.checked ? "매일 자동 실행을 켰어요." : "자동 실행을 껐어요.");
  $("#s-time").onchange = (e) => put({ schedule: { daily_at: e.target.value } }, "실행 시각을 바꿨어요.");
  $("#s-once").onclick = () => put({ schedule: { run_in_minutes: Number($("#s-mins").value) } },
    "예약했어요. 시간이 되면 혼자 실행합니다.");
  const cancel = $("#s-cancel");
  if (cancel) cancel.onclick = () => put({ schedule: { cancel_once: true } }, "예약을 취소했어요.");
  $("#b-save").onclick = () => put({ budget: { daily_cost_usd: Number($("#b-cost").value),
    daily_searches: Number($("#b-search").value) } }, "예산을 저장했어요.");
}

// ---- drawer -----------------------------------------------------------------------
async function openEvent(id) {
  const ev = await api(`/api/events/${id}`);
  const loc = localTime(ev);
  const ACT = { auto_added: ["undo"], added: ["undo"], pending_approval: ["approve", "reject"],
    changed: ["approve", "reject"], undone: ["approve", "reject"], tracking: ["reject"], error: ["reject"] };
  const LABEL = { approve: ["승인해서 일정에 넣기", "ok"], reject: ["제외", "bad"], undo: ["일정에서 빼기(되돌리기)", ""] };
  const actions = (ACT[ev.status] || []).map((a) =>
    `<button class="btn ${LABEL[a][1]}" data-act="${a}" data-id="${ev.id}">${LABEL[a][0]}</button>`).join("");
  const evidence = (ev.evidence || []).map((e) => `<div class="ev">
      <div>${e.official ? '<span class="chip info">공식</span> ' : ""}${e.cited ? '<span class="chip accent">인용</span> ' : ""}
      ${e.derivative ? '<span class="chip warn">2차 문서</span> ' : ""}<b>${esc(e.title || "(제목 없음)")}</b></div>
      <div class="u"><a href="${esc(safeUrl(e.url))}" target="_blank" rel="noopener noreferrer">${esc(e.url)}</a></div>
      <div class="sub">발행 ${esc(e.published_at || "미상")} · 출처군 ${esc(e.provenance_group || "-")}</div>
      ${e.quote ? `<q>${esc(e.quote)}</q>` : ""}</div>`).join("") || `<p class="sub">읽은 문서가 없습니다.</p>`;
  const timeline = (ev.decisions || []).map((d) =>
    `<div>${esc((d.created_at || "").slice(5, 16).replace("T", " "))} · ${esc(d.actor === "user" ? "나" : "비서")} ·
      ${esc(STATUS[d.to_status]?.label || d.to_status)}${d.reason ? ` — ${esc(d.reason)}` : ""}</div>`).join("");
  $("#drawer-panel").innerHTML = `
    <button class="close" data-close aria-label="닫기">×</button>
    <div>${chipsFor(ev)}</div>
    <h2>${esc(ev.title)}</h2>
    <div class="big-time">${esc(ev.start_kst ? `${dayLabel(ev.start_kst)} ${clock(ev)}` : "일시 미정")}
      <small>${esc(ev.status === "tracking" ? "주장된 일시(아직 확인 안 됨)" : "한국시간")}${loc ? " · " + esc(loc) : ""}</small></div>
    ${ev.reasons_text?.length ? `<div class="reason-list" style="margin-top:12px">${ev.reasons_text.map((r) =>
      `<span class="chip warn">${esc(r)}</span>`).join("")}</div>` : ""}
    <dl class="kv">
      <dt>사용자가 본 주장</dt><dd>${esc(ev.claim_text)}</dd>
      <dt>판정</dt><dd>${esc({ supported: "지지", refuted: "반박(정정)", not_enough_evidence: "근거 부족" }[ev.verdict] || ev.verdict || "-")}</dd>
      ${ev.correction ? `<dt>정정</dt><dd>${esc(ev.correction)}</dd>` : ""}
      <dt>판정 이유</dt><dd>${esc(ev.justification || "-")}</dd>
      ${ev.gate_error ? `<dt>게이트</dt><dd>${esc(ev.gate_error)}</dd>` : ""}
      ${ev.source_url ? `<dt>처음 본 글</dt><dd><a href="${esc(safeUrl(ev.source_url))}" target="_blank" rel="noopener noreferrer">${esc(ev.source_url)}</a></dd>` : ""}
    </dl>
    <div class="drawer-actions">${actions}${ev.start_kst ? `<a class="btn" href="/api/events/${ev.id}.ics">.ics 내려받기</a>` : ""}</div>
    <div class="section-title">근거 (읽은 문서)</div>${evidence}
    <div class="section-title">기록</div><div class="timeline">${timeline}</div>`;
  $("#drawer").classList.remove("hidden");
  $("#drawer").setAttribute("aria-hidden", "false");
}
function closeDrawer() {
  $("#drawer").classList.add("hidden");
  $("#drawer").setAttribute("aria-hidden", "true");
}

// ---- activity feed ----------------------------------------------------------------
function stepHtml(s) {
  return `<div class="step ${esc(s.kind)}"><span class="k">${esc(STEP_ICON[s.kind] || "·")}</span>
    <div><div class="l">${esc(s.label)}</div>${s.detail ? `<div class="d">${esc(s.detail)}</div>` : ""}</div></div>`;
}
function threadEl(runId, meta = "") {
  let el = document.querySelector(`.thread[data-run="${runId}"]`);
  if (!el) {
    el = document.createElement("div");
    el.className = "thread";
    el.dataset.run = runId;
    el.innerHTML = `<div class="thread-head"><b>실행 #${esc(runId)}</b><span>${esc(meta)}</span></div><div class="steps"></div>`;
    $("#act-feed").prepend(el);
  }
  return el;
}
async function showRun(runId) {
  const run = await api(`/api/runs/${runId}`);
  $("#act-feed").innerHTML = "";
  const el = threadEl(run.id, `${(run.started_at || "").slice(5, 16).replace("T", " ")} · ${run.trigger}`);
  el.querySelector(".steps").innerHTML = run.steps.map(stepHtml).join("");
  app.threadRun = run.id;
}
function appendStep(s) {
  if (app.threadRun !== s.run_id) {
    $("#act-feed").innerHTML = "";
    app.threadRun = s.run_id;
  }
  const el = threadEl(s.run_id, "지금");
  el.querySelector(".steps").insertAdjacentHTML("beforeend", stepHtml(s));
  const feed = $("#act-feed");
  feed.scrollTop = feed.scrollHeight;
}

// ---- data + events ------------------------------------------------------------------
async function refresh() {
  [app.state, app.events] = await Promise.all([api("/api/state"), api("/api/events")]);
  renderRail();
  await render();
}

let refreshTimer = null;
function softRefresh() {
  clearTimeout(refreshTimer);
  refreshTimer = setTimeout(() => refresh().catch(() => {}), 250);
}

function connectStream() {
  const es = new EventSource("/api/stream");
  es.onmessage = (m) => {
    const msg = JSON.parse(m.data);
    if (msg.type === "step") appendStep(msg);
    if (msg.type === "run_started") { app.state && (app.state.running = true); renderRail(); }
    if (msg.type === "event_changed" || msg.type === "run_finished" || msg.type === "run_started") softRefresh();
    if (msg.type === "run_finished") toast("비서가 실행을 마쳤어요.");
    if (msg.type === "notice") toast(msg.text);
  };
  es.onerror = () => { es.close(); setTimeout(connectStream, 3000); };
}

document.addEventListener("click", async (e) => {
  const t = e.target.closest("[data-view],[data-open],[data-act],[data-close],[data-run],#run-btn");
  if (!t) return;
  if (t.matches("[data-act]")) {
    e.stopPropagation();
    try {
      await api(`/api/events/${t.dataset.id}/${t.dataset.act}`, { method: "POST" });
      toast({ approve: "일정에 넣었어요.", reject: "제외했어요.", undo: "일정에서 뺐어요." }[t.dataset.act]);
      closeDrawer();
      await refresh();
    } catch (err) { toast(err.message); }
    return;
  }
  if (t.matches("[data-view]")) {
    app.view = t.dataset.view;
    document.querySelectorAll("#nav button").forEach((b) => b.classList.toggle("active", b === t));
    await render();
  } else if (t.matches("[data-open]")) {
    await openEvent(t.dataset.open);
  } else if (t.matches("[data-close]")) {
    closeDrawer();
  } else if (t.matches("[data-run]")) {
    await showRun(t.dataset.run);
  } else if (t.id === "run-btn") {
    try { await api("/api/runs", { method: "POST" }); toast("비서가 일을 시작했어요."); }
    catch (err) { toast(err.message); }
    softRefresh();
  }
});
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeDrawer(); });

(async function init() {
  await refresh();
  if (app.state?.last_run) await showRun(app.state.last_run.id);
  connectStream();
  // A link like /#event=3 opens that event (handy for presentation bookmarks).
  const m = location.hash.match(/event=(\d+)/);
  if (m) await openEvent(m[1]).catch(() => {});
})();
