"""
game.py — Domain Logic cho Sudoku Game (Program A)
===================================================
Lớp này chịu trách nhiệm duy nhất về:
  - Quản lý board 9x9 và fixed mask.
  - Validation board, tọa độ và giá trị.
  - Phát hiện conflict theo hàng, cột và khối 3x3.
  - Tính toán trạng thái PLAYING / CONFLICT / SOLVED.
  - Thread safety thông qua RLock.

Không chứa bất kỳ thuật toán giải (solver) nào.
Program B chỉ được tương tác với game thông qua REST API của app.py.

Tác giả: Thành viên A — Trương Lê Quốc Việt
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from threading import RLock
from uuid import uuid4


# ---------------------------------------------------------------------------
# Lỗi domain
# ---------------------------------------------------------------------------

class GameError(ValueError):
    """
    Lỗi domain của SudokuGame.

    Attributes
    ----------
    code : str
        Mã lỗi ổn định để HTTP layer trả cho client.
        Các giá trị hợp lệ: INVALID_BOARD, INVALID_COORDINATE,
        INVALID_VALUE, FIXED_CELL.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


# ---------------------------------------------------------------------------
# Hàm tiện ích: validate_board và find_conflicts
# ---------------------------------------------------------------------------

def validate_board(board: object, allow_conflicts: bool = False) -> list[list[int]]:
    """
    Kiểm tra và chuẩn hoá board trước khi đưa vào SudokuGame.

    Parameters
    ----------
    board : object
        Dữ liệu cần kiểm tra — phải là list 9 phần tử, mỗi phần tử
        là list 9 số nguyên trong khoảng 0..9.
    allow_conflicts : bool
        Nếu False (mặc định), board ban đầu có xung đột sẽ bị từ chối.
        Đặt True khi đồng bộ snapshot từ Solver B (hỗ trợ Min-Conflicts).

    Returns
    -------
    list[list[int]]
        Bản sao sạch của board đã được kiểm tra.

    Raises
    ------
    GameError("INVALID_BOARD", ...)
        Nếu kích thước, kiểu dữ liệu, miền giá trị sai,
        hoặc board ban đầu chứa xung đột (khi allow_conflicts=False).
    """
    if not isinstance(board, list) or len(board) != 9:
        raise GameError("INVALID_BOARD", "Board must contain exactly 9 rows")

    clean: list[list[int]] = []
    for row_index, row in enumerate(board):
        if not isinstance(row, list) or len(row) != 9:
            raise GameError(
                "INVALID_BOARD",
                f"Row {row_index} must contain exactly 9 values"
            )
        for col_index, value in enumerate(row):
            # Dùng type() is not int để loại trừ bool (bool là subclass của int)
            if type(value) is not int or not (0 <= value <= 9):
                raise GameError(
                    "INVALID_BOARD",
                    f"Cell ({row_index}, {col_index}) must be an integer from 0 to 9, "
                    f"got {value!r}"
                )
        clean.append(row.copy())

    if not allow_conflicts and find_conflicts(clean):
        raise GameError("INVALID_BOARD", "Initial board contains conflicts")

    return clean


def find_conflicts(board: list[list[int]]) -> list[dict[str, int]]:
    """
    Xác định tất cả ô vi phạm ràng buộc hàng, cột hoặc khối 3x3.

    Một ô được coi là "conflict" nếu giá trị của nó (khác 0) xuất hiện
    nhiều hơn một lần trong cùng hàng, cột hoặc khối 3x3.

    Parameters
    ----------
    board : list[list[int]]
        Ma trận 9x9 đã được validate.

    Returns
    -------
    list[dict[str, int]]
        Danh sách tọa độ các ô bị conflict, sắp xếp tăng dần theo (x, y),
        không trùng lặp. Mỗi phần tử có dạng {"x": row, "y": col}.
    """
    conflict_cells: set[tuple[int, int]] = set()

    # Xây dựng danh sách 27 nhóm: 9 hàng + 9 cột + 9 khối
    groups: list[list[tuple[int, int]]] = []

    # 9 hàng
    groups.extend([[(r, c) for c in range(9)] for r in range(9)])
    # 9 cột
    groups.extend([[(r, c) for r in range(9)] for c in range(9)])
    # 9 khối 3x3
    groups.extend(
        [
            [(r, c) for r in range(br, br + 3) for c in range(bc, bc + 3)]
            for br in range(0, 9, 3)
            for bc in range(0, 9, 3)
        ]
    )

    for group in groups:
        by_value: dict[int, list[tuple[int, int]]] = {}
        for r, c in group:
            val = board[r][c]
            if val != 0:
                by_value.setdefault(val, []).append((r, c))
        for positions in by_value.values():
            if len(positions) > 1:
                conflict_cells.update(positions)

    return [{"x": r, "y": c} for r, c in sorted(conflict_cells)]


# ---------------------------------------------------------------------------
# Bàn cờ mặc định (độ khó Medium — đúng một nghiệm)
# ---------------------------------------------------------------------------

DEFAULT_BOARD: list[list[int]] = [
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


# ---------------------------------------------------------------------------
# Lớp chính: SudokuGame
# ---------------------------------------------------------------------------

@dataclass
class SudokuGame:
    """
    Quản lý toàn bộ trạng thái một ván Sudoku 9x9.

    Attributes
    ----------
    initial_board : list[list[int]]
        Puzzle ban đầu — dùng để xác định fixed mask và reset.
    test_id : str
        Định danh puzzle trong dataset (ví dụ: "medium_01").
    difficulty : str
        Độ khó của puzzle ("easy" | "medium" | "hard" | "expert").

    Các thuộc tính được khởi tạo trong __post_init__:
        game_id       : str               — UUID ngắn định danh phiên chơi.
        current_board : list[list[int]]   — Trạng thái bàn cờ hiện tại.
        fixed         : list[list[bool]]  — True nếu ô đó là ô đề bài.
        lock          : RLock             — Bảo vệ đa luồng.
    """

    initial_board: list[list[int]] = field(
        default_factory=lambda: deepcopy(DEFAULT_BOARD)
    )
    test_id: str = "medium_01"
    difficulty: str = "medium"

    def __post_init__(self) -> None:
        # Thread lock — phải khởi tạo trước khi validate (validate có thể raise)
        self.lock: RLock = RLock()

        # Sinh game_id ngẫu nhiên
        self.game_id: str = f"game-{uuid4().hex[:8]}"

        # Validate và chuẩn hoá board ban đầu (không cho phép conflict ban đầu)
        self.initial_board = validate_board(self.initial_board)

        # Sao chép trạng thái hiện tại
        self.current_board: list[list[int]] = deepcopy(self.initial_board)

        # Xây dựng fixed mask: True nếu ô ban đầu khác 0
        self.fixed: list[list[bool]] = [
            [value != 0 for value in row]
            for row in self.initial_board
        ]

    # -----------------------------------------------------------------------
    # Phương thức nội bộ
    # -----------------------------------------------------------------------

    def _compute_summary(self) -> tuple[list[dict[str, int]], int, str]:
        """
        Tính conflict, số ô trống và trạng thái hiện tại.

        Returns
        -------
        (conflicts, empty_cells, status)
            status là một trong: "PLAYING", "CONFLICT", "SOLVED".

        Lưu ý: Phải được gọi bên trong lock.
        """
        conflicts = find_conflicts(self.current_board)
        empty = sum(
            value == 0
            for row in self.current_board
            for value in row
        )
        if conflicts:
            status = "CONFLICT"
        elif empty == 0:
            status = "SOLVED"
        else:
            status = "PLAYING"
        return conflicts, empty, status

    def _validate_coordinate(self, x: object, y: object) -> tuple[int, int]:
        """
        Kiểm tra x, y là số nguyên trong khoảng 0..8.

        Raises
        ------
        GameError("INVALID_COORDINATE", ...)
        """
        if (
            type(x) is not int
            or type(y) is not int
            or not (0 <= x <= 8)
            or not (0 <= y <= 8)
        ):
            raise GameError(
                "INVALID_COORDINATE",
                "x and y must be integers in the range 0 to 8"
            )
        return int(x), int(y)

    # -----------------------------------------------------------------------
    # API công khai: đọc trạng thái
    # -----------------------------------------------------------------------

    def state(self) -> dict:
        """
        Trả về toàn bộ trạng thái game (dùng cho GET /game/state).

        Returns
        -------
        dict
            {
                "success": True,
                "game_id": str,
                "test_id": str,
                "difficulty": str,
                "board": list[list[int]],
                "fixed": list[list[bool]],
                "status": "PLAYING" | "CONFLICT" | "SOLVED",
                "empty_cells": int,
                "conflicts": [{"x": int, "y": int}, ...]
            }
        """
        with self.lock:
            conflicts, empty, status = self._compute_summary()
            return {
                "success": True,
                "game_id": self.game_id,
                "test_id": self.test_id,
                "difficulty": self.difficulty,
                "board": deepcopy(self.current_board),
                "fixed": deepcopy(self.fixed),
                "fixed_mask": deepcopy(self.fixed),
                "status": status,
                "empty_cells": empty,
                "conflicts": conflicts,
            }

    def status(self) -> dict:
        """
        Trả về trạng thái rút gọn (dùng cho GET /game/status).

        Returns
        -------
        dict
            {
                "success": True,
                "status": str,
                "empty_cells": int,
                "conflict_count": int
            }
        """
        with self.lock:
            conflicts, empty, status = self._compute_summary()
            return {
                "success": True,
                "status": status,
                "empty_cells": empty,
                "conflict_count": len(conflicts),
            }

    # -----------------------------------------------------------------------
    # API công khai: mutation
    # -----------------------------------------------------------------------

    def move(self, x: object, y: object, num: object) -> dict:
        """
        Điền giá trị vào ô editable.

        Cho phép move gây trùng lặp để Solver B (Min-Conflicts) có thể
        biểu diễn trạng thái trung gian. Trạng thái "CONFLICT" sẽ được
        tính và trả về cho client.

        Parameters
        ----------
        x : int
            Hàng (0..8).
        y : int
            Cột (0..8).
        num : int
            Giá trị điền vào (1..9).

        Returns
        -------
        dict
            Trạng thái rút gọn kèm danh sách conflicts sau khi move.

        Raises
        ------
        GameError("INVALID_COORDINATE")
            Nếu x hoặc y nằm ngoài 0..8.
        GameError("INVALID_VALUE")
            Nếu num không phải số nguyên trong 1..9.
        GameError("FIXED_CELL")
            Nếu ô (x, y) là ô đề bài.
        """
        r, c = self._validate_coordinate(x, y)

        if type(num) is not int or not (1 <= num <= 9):
            raise GameError(
                "INVALID_VALUE",
                "num must be an integer from 1 to 9"
            )

        with self.lock:
            if self.fixed[r][c]:
                raise GameError(
                    "FIXED_CELL",
                    f"Cell ({r}, {c}) is a fixed clue and cannot be changed"
                )
            self.current_board[r][c] = num
            # Trả status + conflicts để client biết ngay sau mỗi move
            result = self.status()
            result["conflicts"] = find_conflicts(self.current_board)
            return result

    def clear(self, x: object, y: object) -> dict:
        """
        Xóa giá trị của ô editable (đặt về 0).

        Parameters
        ----------
        x : int
            Hàng (0..8).
        y : int
            Cột (0..8).

        Returns
        -------
        dict
            Trạng thái rút gọn sau khi xóa.

        Raises
        ------
        GameError("INVALID_COORDINATE")
        GameError("FIXED_CELL")
        """
        r, c = self._validate_coordinate(x, y)

        with self.lock:
            if self.fixed[r][c]:
                raise GameError(
                    "FIXED_CELL",
                    f"Cell ({r}, {c}) is a fixed clue and cannot be cleared"
                )
            self.current_board[r][c] = 0
            return self.status()

    def reset(self) -> dict:
        """
        Khôi phục bàn cờ về trạng thái puzzle ban đầu.

        Returns
        -------
        dict
            Full state sau khi reset.
        """
        with self.lock:
            self.current_board = deepcopy(self.initial_board)
            return self.state()

    def load(
        self,
        test_id: object,
        difficulty: object,
        board: object,
    ) -> dict:
        """
        Nạp puzzle mới vào game.

        Tính lại fixed mask dựa trên puzzle mới. Sinh game_id mới
        để phân biệt với phiên chơi cũ.

        Parameters
        ----------
        test_id : str
            Định danh puzzle (ví dụ: "hard_03").
        difficulty : str
            Độ khó ("easy" | "medium" | "hard" | "expert").
        board : list[list[int]]
            Puzzle mới — không được có xung đột ban đầu.

        Returns
        -------
        dict
            Full state sau khi load.

        Raises
        ------
        GameError("INVALID_BOARD")
            Nếu board không hợp lệ.
        """
        clean = validate_board(board, allow_conflicts=False)

        with self.lock:
            self.game_id = f"game-{uuid4().hex[:8]}"
            self.test_id = str(test_id) if test_id is not None else "custom"
            self.difficulty = str(difficulty) if difficulty is not None else "custom"
            self.initial_board = clean
            self.current_board = deepcopy(clean)
            self.fixed = [
                [value != 0 for value in row]
                for row in clean
            ]
            return self.state()

    def replace(self, board: object) -> dict:
        """
        Đồng bộ toàn bộ phần editable từ snapshot của Solver B.

        Cho phép board snapshot chứa conflict (đây là trạng thái trung gian
        của thuật toán Min-Conflicts). Tuy nhiên, tuyệt đối không được thay
        đổi giá trị của bất kỳ ô fixed nào.

        Parameters
        ----------
        board : list[list[int]]
            Snapshot bàn cờ từ Solver B.

        Returns
        -------
        dict
            Full state sau khi đồng bộ.

        Raises
        ------
        GameError("INVALID_BOARD")
            Nếu board không đúng cấu trúc / kiểu dữ liệu.
        GameError("FIXED_CELL")
            Nếu snapshot cố thay đổi giá trị của ô fixed.
        """
        # Validate cấu trúc và kiểu dữ liệu, cho phép conflict
        clean = validate_board(board, allow_conflicts=True)

        with self.lock:
            # Bảo vệ tất cả ô fixed
            for r in range(9):
                for c in range(9):
                    if self.fixed[r][c] and clean[r][c] != self.initial_board[r][c]:
                        raise GameError(
                            "FIXED_CELL",
                            f"Fixed cell ({r}, {c}) cannot be modified in replace snapshot"
                        )
            self.current_board = clean
            return self.state()
