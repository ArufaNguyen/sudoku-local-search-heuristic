"""
mock_server_a.py — Mock server tối thiểu giả lập Program A cho mục đích test client.py.

QUAN TRỌNG: Đây là MOCK TẠM THỜI, chỉ dùng để chạy tests/test_client.py
khi Program A chưa sẵn sàng. Khi A thật đã chạy được:
  1. Chạy lại test_client.py với cờ --live để test với A thật.
  2. File mock_server_a.py này KHÔNG được dùng trong demo thật.

Mock server mô phỏng đúng:
  - Tất cả 8 endpoint của A (GET health/state/status; POST move/clear/reset/load; PUT state)
  - Quy ước x=row, y=col trong 0..8
  - Mã lỗi ổn định: INVALID_BOARD, INVALID_COORDINATE, INVALID_VALUE, FIXED_CELL
  - A chấp nhận move gây CONFLICT (không từ chối) để hỗ trợ Min-Conflicts
  - Trạng thái: PLAYING / CONFLICT / SOLVED
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import List, Optional

Board = List[List[int]]

# Puzzle mẫu dùng làm trạng thái mặc định của mock
_DEFAULT_PUZZLE: Board = [
    [5, 3, 0, 0, 7, 0, 0, 0, 0],
    [6, 0, 0, 1, 9, 5, 0, 0, 0],
    [0, 9, 8, 0, 0, 0, 0, 6, 0],
    [8, 0, 0, 0, 6, 0, 0, 0, 3],
    [4, 0, 0, 8, 0, 3, 0, 0, 1],
    [7, 0, 0, 0, 2, 0, 0, 0, 6],
    [0, 6, 0, 0, 0, 0, 2, 8, 0],
    [0, 0, 0, 4, 1, 9, 0, 0, 5],
    [0, 0, 0, 0, 8, 0, 0, 7, 9],
]


def _clone(board: Board) -> Board:
    return [row[:] for row in board]


def _find_conflicts(board: Board) -> List[List[int]]:
    """Tìm danh sách ô đang vi phạm (trùng hàng, cột, hoặc khối)."""
    conflict_set = set()
    for r in range(9):
        seen: dict = {}
        for c in range(9):
            v = board[r][c]
            if v == 0:
                continue
            if v in seen:
                conflict_set.add((r, c))
                conflict_set.add((r, seen[v]))
            else:
                seen[v] = c
    for c in range(9):
        seen = {}
        for r in range(9):
            v = board[r][c]
            if v == 0:
                continue
            if v in seen:
                conflict_set.add((r, c))
                conflict_set.add((seen[v], c))
            else:
                seen[v] = r
    for br in range(0, 9, 3):
        for bc in range(0, 9, 3):
            seen = {}
            for dr in range(3):
                for dc in range(3):
                    r, c = br + dr, bc + dc
                    v = board[r][c]
                    if v == 0:
                        continue
                    if v in seen:
                        conflict_set.add((r, c))
                        conflict_set.add(seen[v])
                    else:
                        seen[v] = (r, c)
    return [[r, c] for r, c in sorted(conflict_set)]


def _compute_status(board: Board, conflicts: List) -> str:
    full = all(board[r][c] != 0 for r in range(9) for c in range(9))
    if full and not conflicts:
        return "SOLVED"
    if conflicts:
        return "CONFLICT"
    return "PLAYING"


class MockGameState:
    """Trạng thái bàn cờ dùng chung cho mock server (thread-safe)."""

    def __init__(self, puzzle: Board):
        self._lock = threading.Lock()
        self._initial = _clone(puzzle)
        self._fixed = [[puzzle[r][c] != 0 for c in range(9)] for r in range(9)]
        self._board = _clone(puzzle)
        self._puzzle_id = "mock-1"
        self._difficulty = "easy"

    def snapshot(self) -> dict:
        with self._lock:
            board = _clone(self._board)
            fixed = [row[:] for row in self._fixed]
            conflicts = _find_conflicts(board)
            status = _compute_status(board, conflicts)
            return {
                "board": board,
                "fixed": fixed,
                "conflicts": conflicts,
                "status": status,
                "id": self._puzzle_id,
                "difficulty": self._difficulty,
            }

    def move(self, x: int, y: int, value: int) -> dict:
        with self._lock:
            if self._fixed[x][y]:
                return {"error": "FIXED_CELL", "message": f"Cell ({x},{y}) is fixed."}
            self._board[x][y] = value
            return None  # None = success

    def clear(self, x: int, y: int) -> dict:
        with self._lock:
            if self._fixed[x][y]:
                return {"error": "FIXED_CELL", "message": f"Cell ({x},{y}) is fixed."}
            self._board[x][y] = 0
            return None

    def reset(self) -> None:
        with self._lock:
            self._board = _clone(self._initial)

    def load(self, board: Board, puzzle_id, difficulty: str) -> Optional[dict]:
        with self._lock:
            self._initial = _clone(board)
            self._fixed = [[board[r][c] != 0 for c in range(9)] for r in range(9)]
            self._board = _clone(board)
            self._puzzle_id = puzzle_id
            self._difficulty = difficulty
        return None

    def replace(self, board: Board) -> Optional[dict]:
        """PUT /game/state — chỉ cập nhật các ô editable; từ chối nếu thay đổi ô fixed."""
        with self._lock:
            for r in range(9):
                for c in range(9):
                    if self._fixed[r][c] and board[r][c] != self._initial[r][c]:
                        return {"error": "FIXED_CELL", "message": f"Cannot overwrite fixed cell ({r},{c})."}
            for r in range(9):
                for c in range(9):
                    if not self._fixed[r][c]:
                        self._board[r][c] = board[r][c]
        return None


def _validate_coord(x, y) -> Optional[dict]:
    if not isinstance(x, int) or not isinstance(y, int):
        return {"error": "INVALID_COORDINATE", "message": "x and y must be integers."}
    if not (0 <= x <= 8 and 0 <= y <= 8):
        return {"error": "INVALID_COORDINATE", "message": f"Coordinates ({x},{y}) out of range 0..8."}
    return None


def _validate_value(value) -> Optional[dict]:
    if not isinstance(value, int) or not (1 <= value <= 9):
        return {"error": "INVALID_VALUE", "message": f"Value {value!r} must be an integer in 1..9."}
    return None


def _validate_board(board) -> Optional[dict]:
    if not isinstance(board, list) or len(board) != 9:
        return {"error": "INVALID_BOARD", "message": "Board must be a 9x9 list."}
    for row in board:
        if not isinstance(row, list) or len(row) != 9:
            return {"error": "INVALID_BOARD", "message": "Each row must have 9 elements."}
        for v in row:
            if not isinstance(v, int) or not (0 <= v <= 9):
                return {"error": "INVALID_BOARD", "message": f"Value {v!r} out of range 0..9."}
    return None


class MockAHandler(BaseHTTPRequestHandler):
    """HTTP request handler cho Mock Program A."""

    # game_state được inject từ ngoài vào khi tạo server
    game_state: MockGameState = None

    def log_message(self, fmt, *args):
        pass  # Tắt access log để test output sạch

    def _send_json(self, code: int, data: dict):
        body = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> Optional[dict]:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except Exception:
            return None

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/v1/health":
            self._send_json(200, {"status": "ok"})

        elif path == "/api/v1/game/state":
            self._send_json(200, self.game_state.snapshot())

        elif path == "/api/v1/game/status":
            snap = self.game_state.snapshot()
            self._send_json(200, {
                "status": snap["status"],
                "id": snap["id"],
                "difficulty": snap["difficulty"],
            })

        else:
            self._send_json(404, {"error": "NOT_FOUND"})

    def do_POST(self):
        path = self.path.split("?")[0]
        body = self._read_body()
        if body is None:
            self._send_json(400, {"error": "INVALID_BOARD", "message": "Invalid JSON body."})
            return

        if path == "/api/v1/game/move":
            x, y, value = body.get("x"), body.get("y"), body.get("value")
            err = _validate_coord(x, y) or _validate_value(value)
            if err:
                self._send_json(400, err)
                return
            err = self.game_state.move(x, y, value)
            if err:
                self._send_json(400, err)
                return
            self._send_json(200, self.game_state.snapshot())

        elif path == "/api/v1/game/clear":
            x, y = body.get("x"), body.get("y")
            err = _validate_coord(x, y)
            if err:
                self._send_json(400, err)
                return
            err = self.game_state.clear(x, y)
            if err:
                self._send_json(400, err)
                return
            self._send_json(200, self.game_state.snapshot())

        elif path == "/api/v1/game/reset":
            self.game_state.reset()
            self._send_json(200, self.game_state.snapshot())

        elif path == "/api/v1/game/load":
            board = body.get("board")
            err = _validate_board(board)
            if err:
                self._send_json(400, err)
                return
            self.game_state.load(board, body.get("id", ""), body.get("difficulty", ""))
            self._send_json(200, self.game_state.snapshot())

        else:
            self._send_json(404, {"error": "NOT_FOUND"})

    def do_PUT(self):
        path = self.path.split("?")[0]
        if path != "/api/v1/game/state":
            self._send_json(404, {"error": "NOT_FOUND"})
            return
        body = self._read_body()
        if body is None:
            self._send_json(400, {"error": "INVALID_BOARD", "message": "Invalid JSON body."})
            return
        board = body.get("board")
        err = _validate_board(board)
        if err:
            self._send_json(400, err)
            return
        err = self.game_state.replace(board)
        if err:
            self._send_json(400, err)
            return
        self._send_json(200, self.game_state.snapshot())


class MockServerA:
    """
    Mock Program A server chạy trong thread nền.

    MOCK TẠM THỜI — chỉ dùng để test client.py khi A chưa sẵn sàng.

    Sử dụng:
        server = MockServerA(port=18000)
        server.start()
        # ... chạy test ...
        server.stop()
    """

    def __init__(self, port: int = 18000, puzzle: Optional[Board] = None):
        self.port = port
        self._game_state = MockGameState(puzzle or _DEFAULT_PUZZLE)
        self._thread: Optional[threading.Thread] = None
        self._httpd: Optional[HTTPServer] = None

    def start(self):
        """Khởi động mock server trong một thread daemon."""
        handler_cls = type("Handler", (MockAHandler,), {"game_state": self._game_state})
        self._httpd = HTTPServer(("127.0.0.1", self.port), handler_cls)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop mock server and release socket."""
        if self._httpd:
            self._httpd.shutdown()
            self._httpd.server_close()  # Release the socket immediately
            self._httpd = None
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/api/v1"
