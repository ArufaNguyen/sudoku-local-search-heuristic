// app.js -- Frontend Program B (AI Solver)
// Logic giu nguyen, chi doi ID DOM de khop voi HTML moi.
'use strict';

const B_API = "";

let state = {
  session: null,
  auto_running: false,
  poll_timer: null,
  fixed_mask: null,
  last_error: null,
};

const $ = id => document.getElementById(id);
const btn = {
  prepare: $("btn-prepare"),
  prev:    $("btn-prev"),
  next:    $("btn-next"),
  auto:    $("btn-auto"),
  pause:   $("btn-pause"),
  reset:   $("btn-reset"),
};

// ── API helper ────────────────────────────────────────────────
async function api(method, path, body = null) {
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (body !== null) opts.body = JSON.stringify(body);
  const res = await fetch(B_API + path, opts);
  return res.json();
}

// ── Board init ────────────────────────────────────────────────
function initBoard() {
  const grid = $("board-grid");
  grid.innerHTML = "";
  for (let r = 0; r < 9; r++) {
    for (let c = 0; c < 9; c++) {
      const cell = document.createElement("div");
      cell.className = "cell";
      cell.id = `cell-${r}-${c}`;
      cell.dataset.r = r;
      cell.dataset.c = c;
      grid.appendChild(cell);
    }
  }
}

// ── Board render ──────────────────────────────────────────────
function renderBoard(tick, sessionData) {
  if (!tick) return;
  const board       = tick.board;
  const fixed       = state.fixed_mask;
  const phase       = tick.phase;
  const currentCell = tick.cell;

  for (let r = 0; r < 9; r++) {
    for (let c = 0; c < 9; c++) {
      const cell = $(`cell-${r}-${c}`);
      const val = board[r][c];
      cell.className = "cell";
      cell.textContent = val !== 0 ? val : "";
      const isFixed   = fixed && fixed[r][c];
      const isCurrent = currentCell && currentCell[0] === r && currentCell[1] === c;
      if (phase === "SOLVED") {
        cell.classList.add("solved");
      } else if (isCurrent && phase === "BACKTRACK") {
        cell.classList.add("backtrack");
      } else if (isCurrent && (phase === "ASSIGN" || phase === "SELECT" || phase === "APPLY")) {
        cell.classList.add("current");
      } else if (isFixed) {
        cell.classList.add("fixed");
      }
    }
  }
}

function renderEmptyBoard(board, fixedMask) {
  for (let r = 0; r < 9; r++) {
    for (let c = 0; c < 9; c++) {
      const cell = $(`cell-${r}-${c}`);
      const val = board[r][c];
      cell.className = "cell";
      cell.textContent = val !== 0 ? val : "";
      if (fixedMask && fixedMask[r][c]) cell.classList.add("fixed");
    }
  }
}

// ── Metrics render ────────────────────────────────────────────
function renderMetrics(sessionData) {
  const ids = ["m-nodes","m-bt","m-depth","m-iter","m-restart","m-moves","m-conf","m-ms"];
  if (!sessionData) {
    ids.forEach(id => $(id).textContent = "—");
    $("tick-desc").textContent = "";
    return;
  }
  const tick = sessionData.tick;
  const fm   = sessionData.final_metrics || {};
  const m    = tick ? (tick.metrics || {}) : {};

  $("m-nodes").textContent   = m.nodes_explored ?? fm.nodes_explored ?? "—";
  $("m-bt").textContent      = m.backtracks     ?? fm.backtracks     ?? "—";
  $("m-depth").textContent   = m.max_depth      ?? fm.max_depth      ?? "—";
  $("m-iter").textContent    = m.iterations     ?? fm.iterations     ?? "—";
  $("m-restart").textContent = m.restarts       ?? fm.restarts       ?? "—";
  $("m-moves").textContent   = m.moves          ?? fm.moves          ?? "—";
  $("m-conf").textContent    = tick ? (tick.conflicts ?? "—") : "—";
  $("m-ms").textContent      = m.elapsed_ms     ?? sessionData.elapsed_ms ?? "—";

  $("tick-desc").textContent = tick ? (tick.description || "") : "";
}

// ── Topbar meta ───────────────────────────────────────────────
function updateTopbarMeta(sessionData) {
  if (!sessionData) {
    $("meta-algo").textContent  = "—";
    $("meta-tick").textContent  = "Tick —";
    $("meta-phase").textContent = "—";
    return;
  }
  const algoMap = {
    backtracking: "Backtracking",
    mrv:          "MRV",
    min_conflicts: "Min-Conflicts",
  };
  $("meta-algo").textContent  = algoMap[sessionData.algorithm] || sessionData.algorithm || "—";
  $("meta-tick").textContent  = `Tick ${sessionData.index + 1}/${sessionData.total_ticks}`;
  $("meta-phase").textContent = sessionData.tick ? sessionData.tick.phase : "—";
}

// ── Status badge ──────────────────────────────────────────────
function updateBadge(sessionData) {
  const badge = $("board-status-badge");
  if (!sessionData) { badge.textContent = "READY"; badge.className = "status-chip status--playing"; return; }
  const phase = sessionData.tick ? sessionData.tick.phase : null;
  if (phase === "SOLVED" || sessionData.solve_success) {
    badge.textContent = "SOLVED"; badge.className = "status-chip status--solved";
  } else if (phase === "FAILED") {
    badge.textContent = "FAILED"; badge.className = "status-chip status--failed";
  } else {
    badge.textContent = (sessionData.algorithm || "").toUpperCase();
    badge.className = "status-chip status--playing";
  }
}

// ── Buttons ───────────────────────────────────────────────────
function updateButtons(data) {
  const hasSession = data && data.session !== null;
  const running    = data && data.auto_running;
  const sessionD   = hasSession ? data.session : null;
  const atEnd      = sessionD && sessionD.index >= sessionD.total_ticks - 1;
  const atStart    = !sessionD || sessionD.index < 0;
  btn.prev.disabled   = !hasSession || atStart || running;
  btn.next.disabled   = !hasSession || atEnd   || running;
  btn.auto.disabled   = !hasSession || atEnd   || running;
  btn.pause.disabled  = !running;
  btn.reset.disabled  = !hasSession && !running;
}

// ── Status text ───────────────────────────────────────────────
function updateStatusText(data) {
  const el = $("status-text");
  if (state.last_error && (!data || !data.session)) {
    el.innerHTML = `<span style="color:#fda4af">⚠ ${state.last_error}</span>`;
    return;
  }
  if (!data || !data.session) {
    el.textContent = "Chưa có session. Nhấn Prepare để bắt đầu."; return;
  }
  const s = data.session;
  if (data.auto_running) {
    el.textContent = `Auto đang chạy... Tick ${s.index + 1}/${s.total_ticks}`;
  } else if (s.solve_success) {
    el.textContent = `Đã giải xong! Tổng ${s.total_ticks} ticks.`;
  } else if (s.stopped_reason === "budget_exhausted") {
    el.textContent = `Min-Conflicts: hết ngân sách (${s.total_ticks} ticks).`;
  } else {
    el.textContent = `Tick ${s.index + 1}/${s.total_ticks} — ${(s.algorithm||"").toUpperCase()}`;
  }
}

// ── Apply full state ──────────────────────────────────────────
function applyState(data) {
  state.auto_running = data.auto_running;
  const sessionD = data.session;
  updateButtons(data);
  updateStatusText(data);
  if (sessionD) {
    if (sessionD.fixed_mask) state.fixed_mask = sessionD.fixed_mask;
    updateBadge(sessionD);
    updateTopbarMeta(sessionD);
    renderMetrics(sessionD);
    if (sessionD.tick) {
      renderBoard(sessionD.tick, sessionD);
    } else if (sessionD.initial_board) {
      renderEmptyBoard(sessionD.initial_board, state.fixed_mask);
    }
  } else {
    updateBadge(null);
    updateTopbarMeta(null);
    renderMetrics(null);
  }
}

// ── Polling ───────────────────────────────────────────────────
function startPolling() {
  if (state.poll_timer) return;
  state.poll_timer = setInterval(async () => {
    try {
      const data = await api("GET", "/api/session");
      applyState(data);
    } catch (_) {}
  }, 400);
}

// ── Event handlers ────────────────────────────────────────────
btn.prepare.addEventListener("click", async () => {
  btn.prepare.disabled = true;
  $("status-text").textContent = "Đang chạy solver...";
  const algo = $("algo-select").value;
  const resp = await api("POST", "/api/prepare", { algorithm: algo });
  if (resp.error) {
    state.last_error = resp.error;
    updateStatusText(null);
    btn.prepare.disabled = false;
    return;
  }
  state.last_error = null;
  const sessionData = await api("GET", "/api/session");
  state.fixed_mask = null;
  btn.prepare.disabled = false;
  applyState(sessionData);
});

btn.next.addEventListener("click", async () => {
  const resp = await api("POST", "/api/next");
  applyState(resp);
});

btn.prev.addEventListener("click", async () => {
  const resp = await api("POST", "/api/previous");
  applyState(resp);
});

btn.auto.addEventListener("click", async () => {
  const speed = parseFloat($("speed-select").value);
  await api("POST", "/api/auto/start", { speed });
});

btn.pause.addEventListener("click", async () => {
  btn.pause.disabled = true;
  await api("POST", "/api/auto/pause");
  const data = await api("GET", "/api/session");
  applyState(data);
});

btn.reset.addEventListener("click", async () => {
  await api("POST", "/api/reset", { reset_game: true });
  state.fixed_mask = null;
  const data = await api("GET", "/api/session");
  applyState(data);
  for (let r = 0; r < 9; r++)
    for (let c = 0; c < 9; c++) {
      const cell = $(`cell-${r}-${c}`);
      cell.className = "cell"; cell.textContent = "";
    }
});

// ── Init ──────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  initBoard();
  startPolling();
});
