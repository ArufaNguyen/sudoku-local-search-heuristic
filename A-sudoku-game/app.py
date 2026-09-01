"""
app.py — HTTP Adapter cho Sudoku Game (Program A)
==================================================
Chịu trách nhiệm:
  - Chạy ThreadingHTTPServer tại 127.0.0.1:8000.
  - Phục vụ static frontend từ thư mục static/.
  - Điều phối REST API v1: chuyển request thành lời gọi SudokuGame.
  - Xử lý CORS, error handling và logging.

Chỉ dùng Python standard library — không cần cài thêm gói nào.
Khởi chạy:
    python A-sudoku-game/app.py

Tác giả: Thành viên A — Trương Lê Quốc Việt
"""

from __future__ import annotations

import json
import random
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

# Đảm bảo thư mục chứa app.py nằm trong sys.path để import game
sys.path.insert(0, str(Path(__file__).resolve().parent))
from game import GameError, SudokuGame

# ---------------------------------------------------------------------------
# Hằng số
# ---------------------------------------------------------------------------

HOST = "127.0.0.1"
PORT = 8000
API_PREFIX = "/api/v1"

# Thư mục gốc chứa app.py và thư mục static/
ROOT = Path(__file__).resolve().parent

# Dataset puzzle từ B-auto-solver (nằm cùng cấp với A-sudoku-game/)
PUZZLES_PATH = ROOT.parent / "B-auto-solver" / "dataset" / "puzzles.json"


def _load_puzzles_db() -> list[dict]:
    """Đọc puzzles.json của B. Trả list rỗng nếu file chưa tồn tại."""
    if not PUZZLES_PATH.exists():
        return []
    try:
        with PUZZLES_PATH.open(encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        # Một số format lưu dạng {"puzzles": [...]}
        if isinstance(data, dict) and "puzzles" in data:
            return data["puzzles"]
        return []
    except Exception:
        return []


# Instance SudokuGame duy nhất — chia sẻ giữa tất cả request (thread-safe qua RLock)
GAME = SudokuGame()


# ---------------------------------------------------------------------------
# Request Handler
# ---------------------------------------------------------------------------

class SudokuHandler(SimpleHTTPRequestHandler):
    """
    Request handler xử lý cả REST API v1 lẫn static file.

    Luồng xử lý:
      - Nếu path bắt đầu bằng /api/v1 -> định tuyến API.
      - Còn lại -> SimpleHTTPRequestHandler phục vụ file từ static/.
    """

    def __init__(self, *args, **kwargs):
        # Trỏ SimpleHTTPRequestHandler về thư mục static/
        super().__init__(*args, directory=str(ROOT / "static"), **kwargs)

    # -----------------------------------------------------------------------
    # Logging
    # -----------------------------------------------------------------------

    def log_message(self, fmt: str, *args) -> None:
        """Ghi log kèm prefix [A] để dễ phân biệt với output của Program B."""
        print(f"[A] {self.address_string()} - {fmt % args}")

    # -----------------------------------------------------------------------
    # Tiện ích nội bộ
    # -----------------------------------------------------------------------

    def _send_json(self, status_code: int, payload: dict) -> None:
        """
        Ghi response JSON với CORS headers.

        Parameters
        ----------
        status_code : int
            HTTP status code (200, 400, 404, ...).
        payload : dict
            Dữ liệu sẽ được serialize thành JSON UTF-8.
        """
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self._add_cors_headers()
        self.end_headers()
        self.wfile.write(data)

    def _add_cors_headers(self) -> None:
        """Thêm CORS headers để B (chạy ở cổng khác) có thể gọi API."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _read_json_body(self) -> dict:
        """
        Đọc và parse request body thành dict.

        Returns
        -------
        dict
            Body đã parse (trả {} nếu body rỗng).

        Raises
        ------
        GameError("INVALID_JSON", ...)
            Nếu body không phải JSON hợp lệ hoặc không phải JSON object.
        """
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            parsed = json.loads(raw or b"{}")
            if not isinstance(parsed, dict):
                raise ValueError("Body must be a JSON object")
            return parsed
        except (ValueError, json.JSONDecodeError) as exc:
            raise GameError(
                "INVALID_JSON",
                f"Request body must be a valid JSON object: {exc}"
            ) from exc

    def _get_path(self) -> str:
        """Trả về path đã strip trailing slash."""
        return urlparse(self.path).path.rstrip("/")

    # -----------------------------------------------------------------------
    # CORS Preflight
    # -----------------------------------------------------------------------

    def do_OPTIONS(self) -> None:
        """
        Xử lý CORS preflight request.
        Trình duyệt gửi OPTIONS trước POST/PUT cross-origin.
        """
        self.send_response(204)
        self._add_cors_headers()
        self.end_headers()

    # -----------------------------------------------------------------------
    # GET handler
    # -----------------------------------------------------------------------

    def do_GET(self) -> None:
        """
        Xử lý GET request.
        - Nếu path thuộc API -> định tuyến nội bộ.
        - Ngược lại -> SimpleHTTPRequestHandler phục vụ file tĩnh.
        """
        path = self._get_path()

        # --- API routes ---
        if path == f"{API_PREFIX}/health":
            return self._send_json(200, {
                "success": True,
                "service": "sudoku-game",
                "version": "1.0",
            })

        if path == f"{API_PREFIX}/game/state":
            return self._send_json(200, GAME.state())

        if path == f"{API_PREFIX}/game/status":
            return self._send_json(200, GAME.status())

        if path == f"{API_PREFIX}/puzzles":
            """Trả danh sách puzzle theo difficulty từ dataset B."""
            puzzles = _load_puzzles_db()
            # Trả summary (không trả board đầy đủ để giảm payload)
            summary: dict[str, list] = {
                "easy": [], "medium": [], "hard": [], "expert": []
            }
            for i, p in enumerate(puzzles):
                diff = str(p.get("difficulty", "")).lower()
                if diff in summary:
                    summary[diff].append({
                        "index": i,
                        "id": p.get("id", p.get("test_id", f"{diff}_{i:02d}")),
                        "difficulty": diff,
                        "clues": sum(
                            1 for row in p.get("board", p.get("puzzle", []))
                            for v in row if v != 0
                        ),
                    })
            return self._send_json(200, {
                "success": True,
                "total": len(puzzles),
                "difficulties": list(summary.keys()),
                "puzzles": summary,
                "dataset_loaded": PUZZLES_PATH.exists(),
            })

        # Nếu path bắt đầu bằng /api/v1 nhưng không khớp route nào -> 404
        if path.startswith(API_PREFIX):
            return self._send_json(404, {
                "success": False,
                "error": "NOT_FOUND",
                "message": f"GET {path} is not a valid API endpoint",
            })

        # --- Static files ---
        super().do_GET()

    # -----------------------------------------------------------------------
    # POST / PUT handler (mutation)
    # -----------------------------------------------------------------------

    def _dispatch_mutation(self, method: str) -> None:
        """
        Điều phối POST và PUT request tới đúng phương thức SudokuGame.

        Parameters
        ----------
        method : str
            "POST" hoặc "PUT".
        """
        path = self._get_path()

        # Chỉ xử lý path thuộc /api/v1
        if not path.startswith(API_PREFIX):
            return self._send_json(404, {
                "success": False,
                "error": "NOT_FOUND",
                "message": f"{method} {path} is not a valid API endpoint",
            })

        try:
            body = self._read_json_body()

            # Bảng định tuyến: (method, path) -> callable
            routes: dict[tuple[str, str], callable] = {
                # ------ POST ------
                ("POST", f"{API_PREFIX}/game/move"): lambda: GAME.move(
                    body.get("x"),
                    body.get("y"),
                    body.get("num") if body.get("num") is not None else (
                        body.get("value") if body.get("value") is not None else body.get("val")
                    ),
                ),
                ("POST", f"{API_PREFIX}/game/clear"): lambda: GAME.clear(
                    body.get("x"), body.get("y")
                ),
                ("POST", f"{API_PREFIX}/game/reset"): GAME.reset,
                ("POST", f"{API_PREFIX}/game/load"): lambda: GAME.load(
                    body.get("test_id") or body.get("id") or body.get("puzzle_id") or "custom",
                    body.get("difficulty") or "custom",
                    body.get("board") or body.get("puzzle"),
                ),
                ("POST", f"{API_PREFIX}/game/new"): lambda: self._handle_new_game(body),
                # ------ PUT ------
                ("PUT", f"{API_PREFIX}/game/state"): lambda: GAME.replace(
                    body.get("board")
                ),
            }

            action = routes.get((method, path))
            if action is None:
                return self._send_json(404, {
                    "success": False,
                    "error": "NOT_FOUND",
                    "message": f"{method} {path} is not a valid API endpoint",
                })

            result = action()
            self._send_json(200, result)

        except GameError as exc:
            self._send_json(400, {
                "success": False,
                "error": exc.code,
                "message": str(exc),
            })

    def _handle_new_game(self, body: dict) -> dict:
        """
        Load ngẫu nhiên một puzzle theo difficulty từ dataset B.

        Body: { "difficulty": "easy" | "medium" | "hard" | "expert" }
        Nếu không truyền difficulty, chọn ngẫu nhiên.
        """
        puzzles = _load_puzzles_db()
        if not puzzles:
            raise GameError(
                "INVALID_BOARD",
                "Dataset not found. Run B-auto-solver/dataset/generate_dataset.py first."
            )

        requested = str(body.get("difficulty", "")).lower().strip()
        valid_levels = {"easy", "medium", "hard", "expert"}

        if requested and requested not in valid_levels:
            raise GameError(
                "INVALID_BOARD",
                f"difficulty must be one of: {sorted(valid_levels)}"
            )

        # Lọc puzzle theo độ khó
        pool = [
            p for p in puzzles
            if not requested or str(p.get("difficulty", "")).lower() == requested
        ]
        if not pool:
            raise GameError(
                "INVALID_BOARD",
                f"No puzzles found for difficulty='{requested}'"
            )

        picked = random.choice(pool)

        # Hỗ trợ cả key 'board' lẫn 'puzzle' (tùy format puzzles.json)
        board_data = picked.get("board") or picked.get("puzzle")
        if not board_data:
            raise GameError("INVALID_BOARD", "Selected puzzle has no board data")

        diff    = str(picked.get("difficulty", requested or "custom")).lower()
        test_id = str(picked.get("id", picked.get("test_id", f"{diff}_rnd")))

        return GAME.load(test_id, diff, board_data)

    def do_POST(self) -> None:
        """Xử lý tất cả POST request."""
        self._dispatch_mutation("POST")

    def do_PUT(self) -> None:
        """Xử lý tất cả PUT request."""
        self._dispatch_mutation("PUT")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), SudokuHandler)

    print("=" * 55)
    print("  Sudoku Game — Program A")
    print("=" * 55)
    print(f"  Game UI  :  http://{HOST}:{PORT}")
    print(f"  REST API :  http://{HOST}:{PORT}{API_PREFIX}")
    print()
    print("  Endpoints:")
    print(f"    GET  {API_PREFIX}/health")
    print(f"    GET  {API_PREFIX}/game/state")
    print(f"    GET  {API_PREFIX}/game/status")
    print(f"    GET  {API_PREFIX}/puzzles")
    print(f"    POST {API_PREFIX}/game/move   (x, y, num)")
    print(f"    POST {API_PREFIX}/game/clear  (x, y)")
    print(f"    POST {API_PREFIX}/game/reset")
    print(f"    POST {API_PREFIX}/game/new    (difficulty)")
    print(f"    POST {API_PREFIX}/game/load   (test_id, difficulty, board)")
    print(f"    PUT  {API_PREFIX}/game/state  (board)")
    dataset_ok = "OK" if PUZZLES_PATH.exists() else "NOT FOUND"
    print(f"  Dataset  :  {PUZZLES_PATH.name}  [{dataset_ok}]")
    print("=" * 55)
    print("  Press Ctrl+C to stop.")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[A] Shutting down server...")
        server.server_close()
        print("[A] Server stopped.")
