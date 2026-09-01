"""
app.py — HTTP server cho Program B (Auto Solver / Algorithm Visualizer).
Chạy tại http://127.0.0.1:8001

Endpoints:
  GET  /                   → serve static/index.html
  GET  /static/<file>      → static assets
  GET  /api/health         → {"status": "ok", "program": "B"}
  GET  /api/session        → current session state (index, tick, metrics, auto_running)
  POST /api/prepare        → {algorithm, max_nodes?, max_iterations?, max_restarts?, seed?}
  POST /api/next           → advance 1 tick; apply api_action to A if present
  POST /api/previous       → go back 1 tick; sync board snapshot to A
  POST /api/auto/start     → {speed: float}  start background worker thread
  POST /api/auto/pause     → stop worker thread, freeze index
  POST /api/reset          → {reset_game?: bool}  stop auto, clear session

Design:
  - Auto Run chay trong thread Python backend (threading.Thread + Event + Lock).
  - Frontend chi polling /api/session — khong dung JS timer cho tick logic.
  - Tat ca thay doi index deu di qua advance_locked() co Lock de tranh race condition.
"""

import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── Path setup ────────────────────────────────────────────────────────────────
B_DIR = Path(__file__).resolve().parent
if str(B_DIR) not in sys.path:
    sys.path.insert(0, str(B_DIR))

from client import APIError, GameClient
from client import ConnectionError as ClientConnectionError
from solvers import Board, SolveResult, Tick, solve

STATIC_DIR = B_DIR / "static"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8001
DEFAULT_A_URL = "http://127.0.0.1:8000/api/v1"


# ==============================================================================
# SESSION
# ==============================================================================

class BSession:
    """Holds the solve result and tick replay state for one Prepare cycle."""

    def __init__(self, result: SolveResult, initial_board: Optional[Board] = None, fixed_mask: Optional[List[List[bool]]] = None):
        self.result = result
        self.index: int = -1  # -1 = chua phat tick nao (initial state)
        self.initial_board: Optional[Board] = initial_board
        self.fixed_mask: Optional[List[List[bool]]] = fixed_mask

    @property
    def ticks(self) -> List[Tick]:
        return self.result.ticks

    @property
    def total(self) -> int:
        return len(self.ticks)

    @property
    def current_tick(self) -> Optional[Tick]:
        if 0 <= self.index < self.total:
            return self.ticks[self.index]
        return None

    def state_dict(self) -> Dict[str, Any]:
        tick = self.current_tick
        return {
            "index": self.index,
            "total_ticks": self.total,
            "algorithm": self.result.algorithm,
            "solve_success": self.result.success,
            "stopped_reason": self.result.stopped_reason,
            "elapsed_ms": self.result.elapsed_ms,
            "initial_board": self.initial_board,
            "fixed_mask": self.fixed_mask,
            "final_metrics": {
                "nodes_explored": self.result.nodes_explored,
                "backtracks": self.result.backtracks,
                "max_depth": self.result.max_depth,
                "iterations": self.result.iterations,
                "restarts": self.result.restarts,
                "moves": self.result.moves,
            },
            "tick": tick.to_dict() if tick else None,
        }


# ==============================================================================
# AUTO RUNNER — background thread (không dùng JS timer)
# ==============================================================================

class AutoRunner:
    """
    Background worker thread cho Auto Run.

    Thiet ke: thread Python backend goi advance_fn() lien tuc theo toc do da chon.
    Frontend chi polling /api/session. Auto Run khong bi dung khi nguoi dung chuyen tab.
    """

    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        # Lock dung chung voi next/previous de tranh race condition
        self.lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, advance_fn, speed: float):
        """
        Khoi dong Auto Run.
        advance_fn(): callable → returns True neu con tick tiep theo
        speed: so tick/giay (float)
        """
        if self.is_running:
            return
        self._stop_event.clear()
        interval = 1.0 / max(speed, 0.1)

        def worker():
            while not self._stop_event.is_set():
                has_more = advance_fn()
                if not has_more:
                    break
                # Sleep chia nho de stop_event co the ngat nhanh
                deadline = time.perf_counter() + interval
                while not self._stop_event.is_set():
                    remaining = deadline - time.perf_counter()
                    if remaining <= 0:
                        break
                    self._stop_event.wait(timeout=min(remaining, 0.05))

        self._thread = threading.Thread(target=worker, daemon=True, name="B-AutoRunner")
        self._thread.start()

    def pause(self):
        """Dat co dung va doi thread ket thuc (blocking)."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None


# ==============================================================================
# BAPP — core state machine
# ==============================================================================

class BApp:
    """Core state machine cua Program B."""

    def __init__(self, a_base_url: str = DEFAULT_A_URL, a_timeout: int = 10):
        self.client = GameClient(a_base_url, a_timeout)
        self._session: Optional[BSession] = None
        self._session_lock = threading.Lock()
        self._auto = AutoRunner()

    # ── Session accessors ──────────────────────────────────────────────────

    @property
    def session(self) -> Optional[BSession]:
        with self._session_lock:
            return self._session

    def _set_session(self, s: Optional[BSession]):
        with self._session_lock:
            self._session = s

    # ── Apply api_action to A ─────────────────────────────────────────────

    def _apply_api_action(self, action: Dict[str, Any]):
        """Gui api_action sang Program A thong qua client. Tat loi neu A khong san sang."""
        if not action:
            return
        try:
            t = action.get("type")
            if t == "move":
                self.client.move(action["x"], action["y"], action["value"])
            elif t == "clear":
                self.client.clear(action["x"], action["y"])
            elif t == "replace":
                self.client.replace(action["board"])
        except (APIError, ClientConnectionError):
            pass  # Khong crash B neu A co loi nhat thoi

    # ── advance_locked() — dung chung cho Next va AutoRunner ──────────────

    def _advance_locked(self) -> bool:
        """
        Tang index them 1 va apply api_action neu co. Thread-safe voi Auto Lock.
        Returns True neu con tick tiep theo, False neu da het.
        """
        with self._auto.lock:
            s = self.session
            if s is None:
                return False
            next_idx = s.index + 1
            if next_idx >= s.total:
                return False
            s.index = next_idx
            tick = s.ticks[next_idx]
            if tick.api_action:
                self._apply_api_action(tick.api_action)
            return next_idx < s.total - 1

    # ── Public actions ─────────────────────────────────────────────────────

    def prepare(self, algorithm: str, **opts) -> Dict[str, Any]:
        """Dung Auto, lay board tu A, chay solver, luu session moi."""
        self._auto.pause()

        try:
            state = self.client.get_state()
        except (APIError, ClientConnectionError) as exc:
            return {"error": f"Cannot reach Program A: {exc}"}

        board = state["board"]
        fixed_mask = state.get("fixed") or state.get("fixed_mask")

        allowed_keys = {"max_nodes", "max_iterations", "max_restarts", "seed"}
        solve_opts = {k: v for k, v in opts.items() if k in allowed_keys}
        solve_opts["record_ticks"] = True

        result = solve(algorithm, board, **solve_opts)
        session = BSession(result, initial_board=board, fixed_mask=fixed_mask)
        self._set_session(session)

        return {
            "success": True,
            "algorithm": result.algorithm,
            "solve_success": result.success,
            "total_ticks": session.total,
            "stopped_reason": result.stopped_reason,
        }

    def next_tick(self) -> Dict[str, Any]:
        """Phat 1 tick ke tiep; apply api_action neu co."""
        with self._auto.lock:
            s = self.session
            if s is None:
                return {"error": "No session. Call Prepare first."}
            next_idx = s.index + 1
            if next_idx >= s.total:
                return {"done": True, "index": s.index, "total_ticks": s.total}
            s.index = next_idx
            tick = s.ticks[next_idx]
            if tick.api_action:
                self._apply_api_action(tick.api_action)

        return {"ok": True, **self._session_state_unsafe()}

    def previous_tick(self) -> Dict[str, Any]:
        """Lui 1 tick, dong bo board snapshot tuong ung sang A."""
        with self._auto.lock:
            s = self.session
            if s is None:
                return {"error": "No session. Call Prepare first."}

            if s.index < 0:
                return {"at_start": True, "index": -1}

            if s.index == 0:
                s.index = -1
                try:
                    self.client.reset()
                except (APIError, ClientConnectionError):
                    pass
                return {"ok": True, "at_start": True, "index": -1}

            s.index -= 1
            tick = s.ticks[s.index]
            try:
                self.client.replace(tick.board)
            except (APIError, ClientConnectionError):
                pass

        return {"ok": True, **self._session_state_unsafe()}

    def auto_start(self, speed: float = 2.0) -> Dict[str, Any]:
        """Bat Auto Run: khoi dong worker thread."""
        if self.session is None:
            return {"error": "No session. Call Prepare first."}
        if self._auto.is_running:
            return {"ok": True, "message": "Already running."}
        self._auto.start(self._advance_locked, speed=speed)
        return {"ok": True, "speed": speed}

    def auto_pause(self) -> Dict[str, Any]:
        """Tat Auto Run: doi thread ket thuc, tra index hien tai."""
        self._auto.pause()  # blocking join
        s = self.session
        return {
            "ok": True,
            "paused_at_index": s.index if s else -1,
            "auto_running": False,  # Thread da ket thuc sau pause()
        }

    def reset(self, reset_game: bool = False) -> Dict[str, Any]:
        """Dung Auto, xoa session, tuy chon reset A."""
        self._auto.pause()
        self._set_session(None)
        if reset_game:
            try:
                self.client.reset()
            except (APIError, ClientConnectionError):
                pass
        return {"ok": True}

    def _session_state_unsafe(self) -> Dict[str, Any]:
        """Lay session state — goi khi da co lock hoac khong can lock."""
        s = self._session  # direct access, caller holds lock
        if s is None:
            return {"session": None, "auto_running": self._auto.is_running}
        return {"session": s.state_dict(), "auto_running": self._auto.is_running}

    def session_state(self) -> Dict[str, Any]:
        """Lay session state thread-safe (dung cho polling)."""
        s = self.session
        if s is None:
            return {"session": None, "auto_running": self._auto.is_running}
        return {"session": s.state_dict(), "auto_running": self._auto.is_running}


# ==============================================================================
# HTTP HANDLER
# ==============================================================================

def _make_handler(app: BApp):
    class BHandler(BaseHTTPRequestHandler):

        def log_message(self, fmt, *args):
            pass  # Tat access log

        def _send_json(self, code: int, data: dict):
            body = json.dumps(data, default=str).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def _send_file(self, path: Path):
            ext = path.suffix.lower()
            ctype = {
                ".html": "text/html; charset=utf-8",
                ".css": "text/css",
                ".js": "application/javascript",
            }.get(ext, "text/plain")
            try:
                body = path.read_bytes()
            except FileNotFoundError:
                self._send_json(404, {"error": "File not found"})
                return
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _read_body(self) -> dict:
            n = int(self.headers.get("Content-Length", 0))
            if n == 0:
                return {}
            try:
                return json.loads(self.rfile.read(n))
            except Exception:
                return {}

        def do_OPTIONS(self):
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def do_GET(self):
            p = self.path.split("?")[0]
            if p in ("/", "/index.html"):
                self._send_file(STATIC_DIR / "index.html")
            elif p.startswith("/static/"):
                self._send_file(STATIC_DIR / p[len("/static/"):])
            elif p == "/api/session":
                self._send_json(200, app.session_state())
            elif p == "/api/health":
                self._send_json(200, {"status": "ok", "program": "B"})
            else:
                self._send_json(404, {"error": "Not found"})

        def do_POST(self):
            p = self.path.split("?")[0]
            body = self._read_body()

            if p == "/api/prepare":
                algo = body.get("algorithm", "backtracking")
                opts = {k: body[k] for k in
                        ("max_nodes", "max_iterations", "max_restarts", "seed")
                        if k in body}
                self._send_json(200, app.prepare(algo, **opts))

            elif p == "/api/next":
                self._send_json(200, app.next_tick())

            elif p == "/api/previous":
                self._send_json(200, app.previous_tick())

            elif p == "/api/auto/start":
                self._send_json(200, app.auto_start(speed=float(body.get("speed", 2.0))))

            elif p == "/api/auto/pause":
                self._send_json(200, app.auto_pause())

            elif p == "/api/reset":
                self._send_json(200, app.reset(reset_game=bool(body.get("reset_game", False))))

            else:
                self._send_json(404, {"error": "Not found"})

    return BHandler


# ==============================================================================
# SERVER LIFECYCLE
# ==============================================================================

def start_server(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    a_base_url: str = DEFAULT_A_URL,
    a_timeout: int = 10,
):
    """
    Khoi dong Program B HTTP server trong thread daemon.
    Returns (httpd, thread, app_instance).
    De dung: httpd.shutdown() + httpd.server_close().
    """
    bapp = BApp(a_base_url=a_base_url, a_timeout=a_timeout)
    handler_cls = _make_handler(bapp)
    httpd = HTTPServer((host, port), handler_cls)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True, name="B-HTTP")
    thread.start()
    return httpd, thread, bapp


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Program B — Auto Solver / Visualizer")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--a-url", default=DEFAULT_A_URL, dest="a_url")
    args = parser.parse_args()

    print(f"[B] Starting at http://{args.host}:{args.port}")
    print(f"[B] Program A expected at {args.a_url}")
    print("[B] Open http://127.0.0.1:8001 in your browser. Press Ctrl+C to stop.")

    bapp = BApp(a_base_url=args.a_url)
    httpd = HTTPServer((args.host, args.port), _make_handler(bapp))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[B] Shutting down...")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
