/**
 * app.js -- Frontend Sudoku Game (Program A)
 * - Polling /game/state moi 350ms (hien thi move tu AI)
 * - DOM diffing de khong re-render khi state khong doi
 * - Chon do kho: Easy / Medium / Hard / Expert
 */
'use strict';

const API   = '/api/v1';
const POLL  = 350;
const $     = id => document.getElementById(id);

let lastKey = '';
let gen     = 0;
let activeDiff = '';

/* ---- API helper ---- */
async function api(path, opts = {}) {
  const res = await fetch(API + path, {
    headers: { 'Content-Type': 'application/json' }, ...opts
  });
  const data = await res.json();
  if (!res.ok) {
    const e = new Error(data.message || 'API error');
    e.code = data.error; throw e;
  }
  return data;
}

/* ---- Render board ---- */
function render(state) {
  const key = JSON.stringify(state.board) + state.status;
  const changed = key !== lastKey;
  lastKey = key;

  /* topbar meta */
  $('meta-id').textContent     = '#' + (state.test_id || '?');
  $('meta-diff').textContent   = cap(state.difficulty) || '?';
  $('meta-empty').textContent  = (state.empty_cells ?? '?') + ' ô trống';

  const conflEl = $('meta-conflicts');
  const cnt = state.conflicts?.length ?? 0;
  conflEl.textContent = cnt + ' xung đột';
  conflEl.hidden = cnt === 0;

  const st = $('game-status');
  st.textContent = state.status || '?';
  st.className = 'status-chip status--' + (state.status || 'playing').toLowerCase();

  if (!changed) return;

  /* redraw board */
  const boardEl = $('board');
  boardEl.innerHTML = '';
  const bad = new Set((state.conflicts||[]).map(c => c.x+','+c.y));

  for (let x = 0; x < 9; x++) {
    for (let y = 0; y < 9; y++) {
      const v = state.board[x][y];
      const fixed = state.fixed[x][y];
      const isBad = bad.has(x+','+y);
      const inp = document.createElement('input');
      inp.type = 'text'; inp.inputMode = 'numeric'; inp.maxLength = 1;
      inp.value = v ? String(v) : '';
      inp.readOnly = fixed;
      inp.setAttribute('role', 'gridcell');
      const cls = ['cell'];
      if (fixed) cls.push('fixed-cell');
      if (isBad) cls.push('bad');
      inp.className = cls.join(' ');
      if (!fixed) {
        inp.addEventListener('keydown', e => onKey(e, x, y));
        inp.addEventListener('change',  e => onChange(e, x, y, inp));
      }
      boardEl.appendChild(inp);
    }
  }
}

/* ---- Cell handlers ---- */
async function onKey(e, x, y) {
  const d = parseInt(e.key, 10);
  if (e.key === 'Delete' || e.key === 'Backspace' || e.key === '0') {
    e.preventDefault(); await doClear(x, y); return;
  }
  if (!isNaN(d) && d >= 1 && d <= 9) {
    e.preventDefault(); await doMove(x, y, d); return;
  }
  const allow = ['Tab','ArrowUp','ArrowDown','ArrowLeft','ArrowRight'];
  if (!allow.includes(e.key) && !e.ctrlKey && !e.metaKey) e.preventDefault();
}

async function onChange(e, x, y, inp) {
  const n = parseInt(inp.value.trim(), 10);
  if (!inp.value.trim()) { await doClear(x, y); return; }
  if (!isNaN(n) && n >= 1 && n <= 9) await doMove(x, y, n);
  else { lastKey = ''; await refresh(); }
}

async function doMove(x, y, num) {
  try {
    await api('/game/move', { method:'POST', body: JSON.stringify({x,y,num}) });
    lastKey = ''; await refresh();
  } catch(err) { showToast(err.message); lastKey=''; await refresh(); }
}

async function doClear(x, y) {
  try {
    await api('/game/clear', { method:'POST', body: JSON.stringify({x,y}) });
    lastKey = ''; await refresh();
  } catch(err) { lastKey=''; await refresh(); }
}

/* ---- Refresh ---- */
async function refresh() {
  const g = ++gen;
  try {
    const state = await api('/game/state');
    if (g !== gen) return;
    setDot(true);
    render(state);
  } catch {
    if (g !== gen) return;
    setDot(false);
  }
}

/* ---- API dot ---- */
function setDot(on) {
  const el = $('api-dot');
  el.className = 'api-dot ' + (on ? 'api-dot--on' : 'api-dot--off');
}

/* ---- Difficulty ---- */
function setDiffMsg(msg, type='') {
  const el = $('diff-msg');
  if (!msg) { el.hidden = true; return; }
  el.hidden = false;
  el.className = 'diff-msg' + (type ? ' '+type : '');
  el.textContent = msg;
}

function highlightDiff(diff) {
  activeDiff = diff;
  ['easy','medium','hard','expert'].forEach(d => {
    const b = $('btn-'+d);
    if (b) b.classList.toggle('is-active', d === diff);
  });
}

async function loadDiff(diff) {
  const btns = ['easy','medium','hard','expert'].map(d => $('btn-'+d));
  btns.forEach(b => b && (b.disabled = true));
  setDiffMsg('Đang tải ' + cap(diff) + '...', 'loading');
  try {
    const state = await api('/game/new', {
      method: 'POST', body: JSON.stringify({difficulty: diff})
    });
    highlightDiff(diff);
    lastKey = ''; await refresh();
    const clues = 81 - (state.empty_cells ?? 0);
    setDiffMsg('Puzzle ' + state.test_id + ' (' + clues + ' ô clue)', 'ok');
    setTimeout(() => setDiffMsg(''), 3000);
  } catch(err) {
    highlightDiff('');
    setDiffMsg(err.message || 'Không tìm thấy dataset!', 'err');
  } finally {
    btns.forEach(b => b && (b.disabled = false));
  }
}

/* ---- Toast ---- */
function showToast(msg) {
  const t = document.createElement('div');
  t.className = 'toast'; t.textContent = msg || 'Lỗi!';
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 2200);
}

/* ---- Util ---- */
function cap(s) {
  if (!s) return '';
  return s[0].toUpperCase() + s.slice(1).toLowerCase();
}

/* ---- Init ---- */
document.addEventListener('DOMContentLoaded', () => {
  $('btn-reset').addEventListener('click', async () => {
    try {
      await api('/game/reset', { method:'POST', body:'{}' });
      lastKey = ''; setDiffMsg('');
      await refresh();
    } catch(err) { console.error(err); }
  });

  ['easy','medium','hard','expert'].forEach(diff => {
    const b = $('btn-'+diff);
    if (b) b.addEventListener('click', () => loadDiff(diff));
  });

  refresh();
  setInterval(refresh, POLL);
});
