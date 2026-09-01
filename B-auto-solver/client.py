"""
client.py - Boundary giao tiếp REST giữa Program B và Program A.

Cung cấp class GameClient với đầy đủ phương thức cho tất cả endpoint
của Program A theo hợp đồng API tại PROMPT_ANTIGRAVITY_PROGRAM_B.md mục 1.

Hợp đồng API:
  Base URL : http://127.0.0.1:8000/api/v1
  GET  /health        → kiểm tra A đang hoạt động
  GET  /game/state    → toàn bộ trạng thái (board, fixed, conflicts, status)
  GET  /game/status   → trạng thái rút gọn
  POST /game/move     → gán giá trị vào ô editable
  POST /game/clear    → xóa ô editable
  POST /game/reset    → khôi phục puzzle ban đầu
  POST /game/load     → nạp puzzle mới
  PUT  /game/state    → đồng bộ toàn bộ phần editable từ snapshot

Quy ước:
  - x = row, y = column, cả hai trong 0..8
  - board là list[list[int]], giá trị 0=trống, 1..9=đã điền
  - Lỗi HTTP 400 mang JSON {"error": "<CODE>"} với code là một trong:
    INVALID_BOARD | INVALID_COORDINATE | INVALID_VALUE | FIXED_CELL

TODO: Khi Program A thật sẵn sàng, chạy test_client.py với
      --live flag (xem phần cuối file test) để xác nhận client hoạt động
      đúng với A thật. Không cần thay đổi client.py nếu A tuân thủ
      đúng đặc tả này.
"""

import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

Board = List[List[int]]

DEFAULT_BASE_URL = "http://127.0.0.1:8000/api/v1"
DEFAULT_TIMEOUT = 10  # seconds


class APIError(Exception):
    """
    Lỗi trả về từ Program A (HTTP 400 hoặc lỗi HTTP khác).

    Attributes:
        status_code: HTTP status code (ví dụ 400, 404, 500)
        error_code:  Mã lỗi ổn định trong JSON body, ví dụ "FIXED_CELL"
        message:     Mô tả lỗi đầy đủ
    """
    def __init__(self, status_code: int, error_code: str, message: str = ""):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        super().__init__(f"[HTTP {status_code}] {error_code}: {message}")


class ConnectionError(Exception):
    """Không thể kết nối tới Program A (A chưa chạy hoặc sai địa chỉ)."""
    pass


class GameClient:
    """
    Client giao tiếp REST với Program A.

    Sử dụng thư viện chuẩn Python (urllib) — không cần cài đặt package ngoài.
    Tất cả phương thức đều đồng bộ (blocking). Nếu A trả lỗi 400, ném APIError.
    Nếu không kết nối được, ném ConnectionError.
    """

    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: int = DEFAULT_TIMEOUT):
        """
        Args:
            base_url: Base URL của Program A, mặc định http://127.0.0.1:8000/api/v1
            timeout:  Timeout tính bằng giây cho mỗi request.
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # -----------------------------------------------------------------------
    # Phương thức nội bộ
    # -----------------------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Thực hiện một HTTP request, trả về dict từ JSON response.

        Args:
            method: "GET", "POST" hoặc "PUT"
            path:   Đường dẫn endpoint (ví dụ "/health")
            body:   Dict sẽ được encode thành JSON body (chỉ dùng với POST/PUT)

        Returns:
            Dict chứa nội dung JSON từ response của A.

        Raises:
            APIError:        A trả HTTP 400 hoặc HTTP lỗi khác.
            ConnectionError: Không kết nối được (URLError/OSError).
        """
        url = self.base_url + path
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        req = urllib.request.Request(url, data=data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read()
                if not raw:
                    return {}
                return json.loads(raw)

        except urllib.error.HTTPError as exc:
            # A trả HTTP lỗi — cố đọc body JSON để lấy error code
            raw = exc.read()
            error_code = "UNKNOWN_ERROR"
            message = str(exc)
            try:
                payload = json.loads(raw)
                error_code = payload.get("error", error_code)
                message = payload.get("message", message)
            except Exception:
                pass
            raise APIError(exc.code, error_code, message)

        except (urllib.error.URLError, OSError) as exc:
            raise ConnectionError(
                f"Không thể kết nối tới Program A tại {self.base_url}. "
                f"Hãy kiểm tra A đang chạy. Chi tiết: {exc}"
            ) from exc

    # -----------------------------------------------------------------------
    # Public API — tương ứng 1-1 với endpoint của Program A
    # -----------------------------------------------------------------------

    def health(self) -> Dict[str, Any]:
        """
        GET /health
        Kiểm tra Program A đang hoạt động.

        Returns:
            Dict chứa ít nhất {"status": "ok"}
        """
        return self._request("GET", "/health")

    def get_state(self) -> Dict[str, Any]:
        """
        GET /game/state
        Lấy toàn bộ trạng thái bàn cờ hiện tại.

        Returns:
            Dict gồm:
              board     : list[list[int]] — ma trận 9x9, 0=trống, 1..9=đã điền
              fixed     : list[list[bool]] — mask ô cố định ban đầu
              conflicts : list[list[int,int]] — danh sách ô đang vi phạm
              status    : str — "PLAYING" | "CONFLICT" | "SOLVED"
        """
        return self._request("GET", "/game/state")

    def get_status(self) -> Dict[str, Any]:
        """
        GET /game/status
        Lấy trạng thái rút gọn.

        Returns:
            Dict gồm ít nhất {"status": "PLAYING"|"CONFLICT"|"SOLVED"}
        """
        return self._request("GET", "/game/status")

    def move(self, x: int, y: int, value: int) -> Dict[str, Any]:
        return self._request("POST", "/game/move", {"x": x, "y": y, "value": value, "num": value})

    def clear(self, x: int, y: int) -> Dict[str, Any]:
        """
        POST /game/clear
        Xóa giá trị tại ô editable (đặt về 0).

        Args:
            x: row trong 0..8
            y: column trong 0..8

        Returns:
            Dict trạng thái sau khi xóa.

        Raises:
            APIError(INVALID_COORDINATE): x hoặc y ngoài 0..8
            APIError(FIXED_CELL):         ô (x,y) là ô cố định ban đầu
        """
        return self._request("POST", "/game/clear", {"x": x, "y": y})

    def reset(self) -> Dict[str, Any]:
        """
        POST /game/reset
        Khôi phục bàn cờ về trạng thái puzzle ban đầu (xóa tất cả editable cells).

        Returns:
            Dict trạng thái sau khi reset.
        """
        return self._request("POST", "/game/reset", {})

    def load(self, board: Board, puzzle_id: Any = None, difficulty: str = "") -> Dict[str, Any]:
        """
        POST /game/load
        Nạp puzzle mới vào Program A.

        Args:
            board:      Ma trận 9x9 puzzle mới (0=trống, 1..9=clue cố định)
            puzzle_id:  ID của puzzle (string hoặc int, tùy A quy định)
            difficulty: Mức độ khó ("easy"/"medium"/"hard"/"expert")

        Returns:
            Dict trạng thái sau khi nạp puzzle mới.

        Raises:
            APIError(INVALID_BOARD): board không hợp lệ (kích thước, giá trị, ...)
        """
        payload: Dict[str, Any] = {"board": board}
        if puzzle_id is not None:
            payload["id"] = puzzle_id
        if difficulty:
            payload["difficulty"] = difficulty
        return self._request("POST", "/game/load", payload)

    def replace(self, board: Board) -> Dict[str, Any]:
        """
        PUT /game/state
        Đồng bộ toàn bộ phần editable của bàn cờ A bằng snapshot từ B.
        Dùng khi Min-Conflicts thực hiện swap (thay đổi đồng thời nhiều ô),
        hoặc khi Previous cần rollback về trạng thái cũ.

        Args:
            board: Ma trận 9x9 snapshot board từ B
                   (A sẽ chỉ cập nhật các ô editable, từ chối nếu thay đổi ô cố định)

        Returns:
            Dict trạng thái sau khi đồng bộ.

        Raises:
            APIError(FIXED_CELL):    Snapshot thay đổi ô cố định ban đầu
            APIError(INVALID_BOARD): Board không hợp lệ
        """
        return self._request("PUT", "/game/state", {"board": board})

    # -----------------------------------------------------------------------
    # Convenience helpers
    # -----------------------------------------------------------------------

    def is_alive(self) -> bool:
        """Trả về True nếu Program A đang chạy và phản hồi health check."""
        try:
            resp = self.health()
            return resp.get("status") == "ok"
        except (APIError, ConnectionError):
            return False

    def get_board(self) -> Board:
        """Shortcut: lấy chỉ board hiện tại (list[list[int]])."""
        return self.get_state()["board"]

    def get_fixed_mask(self) -> List[List[bool]]:
        """Shortcut: lấy chỉ fixed mask (list[list[bool]])."""
        return self.get_state()["fixed"]
