"""
solvers.py - Module triển khai 3 thuật toán giải Sudoku cho Program B:
1. Backtracking (cơ sở)
2. Backtracking kết hợp MRV (Minimum Remaining Values heuristic)
3. Min-Conflicts (Local Search theo hàng)

Bao gồm:
- Hàm bổ trợ: candidates, count_conflicts, total_conflicts, is_solved
- Cơ chế ghi nhận Tick (Tick Recorder) cho visualizer
- Thu thập metrics: runtime, nodes_explored, backtracks, max_depth, iterations, restarts, moves
- Dataclass SolveResult và Tick
"""

from __future__ import annotations
import copy
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

Board = List[List[int]]


@dataclass
class Tick:
    """Đại diện cho một bước trạng thái của thuật toán phục vụ visualizer."""
    index: int
    algorithm: str
    phase: str  # SELECT, ASSIGN, BACKTRACK, INITIALIZE, APPLY, RESTART, SOLVED, FAILED
    board: Board
    cell: Optional[Tuple[int, int]] = None
    value: Optional[int] = None
    candidates: Optional[List[int]] = None
    conflicts: Optional[int] = None
    depth: int = 0
    metrics: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    api_action: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "algorithm": self.algorithm,
            "phase": self.phase,
            "board": self.board,
            "cell": list(self.cell) if self.cell else None,
            "value": self.value,
            "candidates": self.candidates,
            "conflicts": self.conflicts,
            "depth": self.depth,
            "metrics": self.metrics,
            "description": self.description,
            "api_action": self.api_action,
        }


@dataclass
class SolveResult:
    """Kết quả thực thi thuật toán giải Sudoku."""
    algorithm: str
    success: bool
    board: Optional[Board] = None
    elapsed_ms: float = 0.0
    nodes_explored: int = 0
    backtracks: int = 0
    max_depth: int = 0
    iterations: int = 0
    restarts: int = 0
    moves: int = 0
    ticks: List[Tick] = field(default_factory=list)
    stopped_reason: str = "solved"  # solved, node_limit, no_solution, budget_exhausted

    def to_dict(self) -> Dict[str, Any]:
        return {
            "algorithm": self.algorithm,
            "success": self.success,
            "board": self.board,
            "elapsed_ms": self.elapsed_ms,
            "nodes_explored": self.nodes_explored,
            "backtracks": self.backtracks,
            "max_depth": self.max_depth,
            "iterations": self.iterations,
            "restarts": self.restarts,
            "moves": self.moves,
            "tick_count": len(self.ticks),
            "stopped_reason": self.stopped_reason,
        }


# ==============================================================================
# HÀM BỔ TRỢ RÀNG BUỘC VÀ XUNG ĐỘT (CONSTRAINTS & CONFLICTS)
# ==============================================================================

def candidates(board: Board, row: int, col: int) -> List[int]:
    """
    Trả về danh sách các giá trị hợp lệ (1..9) cho ô (row, col)
    không vi phạm ràng buộc trên hàng, cột và khối 3x3.
    """
    if board[row][col] != 0:
        return []

    used = set()
    # Kiểm tra hàng và cột
    for i in range(9):
        if board[row][i] != 0:
            used.add(board[row][i])
        if board[i][col] != 0:
            used.add(board[i][col])

    # Kiểm tra khối 3x3
    box_r = (row // 3) * 3
    box_c = (col // 3) * 3
    for r in range(box_r, box_r + 3):
        for c in range(box_c, box_c + 3):
            if board[r][c] != 0:
                used.add(board[r][c])

    return [v for v in range(1, 10) if v not in used]


def count_conflicts(board: Board, row: int, col: int) -> int:
    """
    Đếm số ô KHÁC đang trùng giá trị với ô (row, col) trên hàng, cột hoặc khối 3x3.
    Không đếm trùng lặp ô. Nếu ô hiện tại là 0, trả về 0.
    """
    val = board[row][col]
    if val == 0:
        return 0

    conflicting_cells = set()

    # Kiểm tra hàng
    for c in range(9):
        if c != col and board[row][c] == val:
            conflicting_cells.add((row, c))

    # Kiểm tra cột
    for r in range(9):
        if r != row and board[r][col] == val:
            conflicting_cells.add((r, col))

    # Kiểm tra khối 3x3
    box_r = (row // 3) * 3
    box_c = (col // 3) * 3
    for r in range(box_r, box_r + 3):
        for c in range(box_c, box_c + 3):
            if (r != row or c != col) and board[r][c] == val:
                conflicting_cells.add((r, c))

    return len(conflicting_cells)


def total_conflicts(board: Board) -> int:
    """
    Tính tổng số xung đột trên toàn bàn cờ.
    Trả về tổng số ô vi phạm (mỗi cặp ô trùng nhau tính 2 lần trong sum count_conflicts,
    ở đây trả về tổng số xung đột thực tế / 2 hoặc tổng đếm).
    Để phục vụ đánh giá hàm mục tiêu của Min-Conflicts, ta dùng tổng số cặp xung đột.
    """
    total = 0
    for r in range(9):
        for c in range(9):
            if board[r][c] != 0:
                total += count_conflicts(board, r, c)
    return total // 2


def is_solved(board: Board) -> bool:
    """Kiểm tra bàn cờ đã đầy (không còn ô 0) và không có bất kỳ xung đột nào."""
    for r in range(9):
        for c in range(9):
            if board[r][c] == 0:
                return False
    return total_conflicts(board) == 0


def clone_board(board: Board) -> Board:
    """Deep copy ma trận bàn cờ 9x9."""
    return [row[:] for row in board]


# ==============================================================================
# THUẬT TOÁN 1 & 2: BACKTRACKING & MRV
# ==============================================================================

def solve_backtracking(
    board: Board,
    use_mrv: bool = False,
    max_nodes: int = 200000,
    record_ticks: bool = False,
) -> SolveResult:
    """
    Giải Sudoku bằng Backtracking chuẩn hoặc Backtracking kết hợp Heuristic MRV.

    - use_mrv = False: duyệt ô trống đầu tiên theo thứ tự row-major.
    - use_mrv = True: chọn ô có domain (candidates) nhỏ nhất (Fail-First).
      Lưu ý: MRV không làm thay đổi worst-case exponential O(9^m),
      chỉ làm giảm branching factor trung bình trong thực tế.
    """
    start_time = time.perf_counter()
    working_board = clone_board(board)
    algorithm_name = "mrv" if use_mrv else "backtracking"

    nodes_explored = 0
    backtracks = 0
    max_depth = 0
    ticks: List[Tick] = []
    tick_index = 0

    def add_tick(
        phase: str,
        cell: Optional[Tuple[int, int]] = None,
        value: Optional[int] = None,
        cand_list: Optional[List[int]] = None,
        depth: int = 0,
        desc: str = "",
        api_action: Optional[Dict[str, Any]] = None,
    ):
        nonlocal tick_index
        if not record_ticks:
            return
        tick_index += 1
        metrics_snap = {
            "nodes_explored": nodes_explored,
            "backtracks": backtracks,
            "max_depth": max_depth,
            "elapsed_ms": round((time.perf_counter() - start_time) * 1000, 2),
        }
        ticks.append(
            Tick(
                index=tick_index,
                algorithm=algorithm_name,
                phase=phase,
                board=clone_board(working_board),
                cell=cell,
                value=value,
                candidates=cand_list,
                conflicts=0,
                depth=depth,
                metrics=metrics_snap,
                description=desc,
                api_action=api_action,
            )
        )

    def select_unassigned_cell() -> Optional[Tuple[int, int, List[int]]]:
        """Chọn ô trống kế tiếp theo Backtracking (row-major) hoặc MRV."""
        if not use_mrv:
            for r in range(9):
                for c in range(9):
                    if working_board[r][c] == 0:
                        cands = candidates(working_board, r, c)
                        return (r, c, cands)
            return None

        # MRV: Duyệt tất cả ô trống, chọn ô có ít candidates nhất
        best_cell = None
        min_candidates_len = 10
        best_cands: List[int] = []

        for r in range(9):
            for c in range(9):
                if working_board[r][c] == 0:
                    cands = candidates(working_board, r, c)
                    cands_len = len(cands)
                    # Tối ưu Fail-First: Nếu phát hiện ô có domain rỗng, trả về ngay lập tức
                    if cands_len == 0:
                        return (r, c, [])
                    if cands_len < min_candidates_len:
                        min_candidates_len = cands_len
                        best_cell = (r, c)
                        best_cands = cands

        if best_cell is not None:
            return (best_cell[0], best_cell[1], best_cands)
        return None

    def backtrack(depth: int) -> bool:
        nonlocal nodes_explored, backtracks, max_depth
        if depth > max_depth:
            max_depth = depth

        selected = select_unassigned_cell()
        if selected is None:
            # Không còn ô trống nào -> Đã giải xong
            return True

        row, col, cands = selected
        nodes_explored += 1

        if nodes_explored > max_nodes:
            return False

        add_tick(
            phase="SELECT",
            cell=(row, col),
            cand_list=cands,
            depth=depth,
            desc=f"Chọn ô ({row}, {col}) có miền giá trị khả dĩ: {cands}",
        )

        if not cands:
            # Ngõ cụt (dead end)
            backtracks += 1
            return False

        for val in cands:
            working_board[row][col] = val
            add_tick(
                phase="ASSIGN",
                cell=(row, col),
                value=val,
                cand_list=cands,
                depth=depth,
                desc=f"Thử gán giá trị {val} vào ô ({row}, {col})",
                api_action={"type": "move", "x": row, "y": col, "value": val},
            )

            if backtrack(depth + 1):
                return True

            if nodes_explored > max_nodes:
                return False

            # Quay lui (backtrack)
            working_board[row][col] = 0
            backtracks += 1
            add_tick(
                phase="BACKTRACK",
                cell=(row, col),
                value=0,
                depth=depth,
                desc=f"Quay lui: Xóa giá trị tại ô ({row}, {col})",
                api_action={"type": "clear", "x": row, "y": col},
            )

        return False

    success = backtrack(0)
    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 3)

    if success:
        stopped_reason = "solved"
        add_tick(
            phase="SOLVED",
            depth=max_depth,
            desc="Đã giải xong Sudoku thành công!",
        )
    elif nodes_explored > max_nodes:
        stopped_reason = "node_limit"
        add_tick(
            phase="FAILED",
            depth=max_depth,
            desc=f"Dừng lại: Vượt quá giới hạn an toàn {max_nodes} nodes.",
        )
    else:
        stopped_reason = "no_solution"
        add_tick(
            phase="FAILED",
            depth=max_depth,
            desc="Không tìm thấy nghiệm hợp lệ cho bài toán.",
        )

    return SolveResult(
        algorithm=algorithm_name,
        success=success,
        board=working_board if success else None,
        elapsed_ms=elapsed_ms,
        nodes_explored=nodes_explored,
        backtracks=backtracks,
        max_depth=max_depth,
        ticks=ticks,
        stopped_reason=stopped_reason,
    )


# ==============================================================================
# THUẬT TOÁN 3: MIN-CONFLICTS (LOCAL SEARCH)
# ==============================================================================

def solve_min_conflicts(
    board: Board,
    max_iterations: int = 1000,
    max_restarts: int = 50,
    seed: Optional[int] = None,
    record_ticks: bool = False,
) -> SolveResult:
    """
    Giải Sudoku bằng Local Search (Min-Conflicts Heuristic) theo hàng:
    1. Giữ nguyên các ô fixed (clues gốc).
    2. Khởi tạo: Mỗi hàng điền các ô trống bằng hoán vị ngẫu nhiên của các chữ số còn thiếu.
       -> Đảm bảo mỗi hàng luôn hợp lệ (row-consistent).
    3. Tìm các ô editable đang gây xung đột ở cột hoặc khối 3x3.
    4. Chọn ngẫu nhiên một ô có xung đột.
    5. Đánh giá các phép đổi giá trị (swap) với các ô editable khác CÙNG HÀNG.
    6. Chọn phép đổi tối thiểu hóa tổng xung đột (chọn ngẫu nhiên khi hòa điểm để tránh chu trình).
    7. Lặp lại cho đến khi hết xung đột hoặc vượt ngân sách (restarts/iterations).

    Min-Conflicts là thuật toán không đầy đủ (incomplete). Failure là bằng chứng
    thực nghiệm quan trọng của Local Search.
    """
    start_time = time.perf_counter()
    rng = random.Random(seed)

    # Xác định các ô cố định (fixed cells)
    fixed_mask = [[board[r][c] != 0 for c in range(9)] for r in range(9)]

    # Lưu danh sách các vị trí editable theo từng hàng
    editable_in_row = [
        [c for c in range(9) if not fixed_mask[r][c]] for r in range(9)
    ]

    working_board: Board = [[0] * 9 for _ in range(9)]
    ticks: List[Tick] = []
    tick_index = 0
    total_moves = 0
    total_iterations = 0

    def add_tick(
        phase: str,
        cell: Optional[Tuple[int, int]] = None,
        value: Optional[int] = None,
        conflicts_val: Optional[int] = None,
        depth_val: int = 0,
        desc: str = "",
        api_action: Optional[Dict[str, Any]] = None,
    ):
        nonlocal tick_index
        if not record_ticks:
            return
        tick_index += 1
        metrics_snap = {
            "iterations": total_iterations,
            "restarts": restart_count,
            "moves": total_moves,
            "conflicts": conflicts_val if conflicts_val is not None else total_conflicts(working_board),
            "elapsed_ms": round((time.perf_counter() - start_time) * 1000, 2),
        }
        ticks.append(
            Tick(
                index=tick_index,
                algorithm="min_conflicts",
                phase=phase,
                board=clone_board(working_board),
                cell=cell,
                value=value,
                conflicts=conflicts_val,
                depth=depth_val,
                metrics=metrics_snap,
                description=desc,
                api_action=api_action,
            )
        )

    def initialize_board() -> None:
        """Điền ngẫu nhiên các số còn thiếu theo từng hàng để hàng không có xung đột."""
        for r in range(9):
            fixed_nums = {board[r][c] for c in range(9) if fixed_mask[r][c]}
            missing_nums = [n for n in range(1, 10) if n not in fixed_nums]
            rng.shuffle(missing_nums)

            # Đặt clue gốc vào
            for c in range(9):
                if fixed_mask[r][c]:
                    working_board[r][c] = board[r][c]

            # Điền các số còn thiếu vào các ô editable
            for idx, c in enumerate(editable_in_row[r]):
                working_board[r][c] = missing_nums[idx]

    restart_count = 0

    while restart_count <= max_restarts:
        initialize_board()
        current_conflicts = total_conflicts(working_board)

        if restart_count > 0:
            add_tick(
                phase="RESTART",
                conflicts_val=current_conflicts,
                depth_val=restart_count,
                desc=f"Khởi động lại (Restart {restart_count}/{max_restarts}) với cấu hình ngẫu nhiên mới.",
                api_action={"type": "replace", "board": clone_board(working_board)},
            )
        else:
            add_tick(
                phase="INITIALIZE",
                conflicts_val=current_conflicts,
                depth_val=0,
                desc="Khởi tạo trạng thái ban đầu: Mỗi hàng là một hoán vị không xung đột.",
                api_action={"type": "replace", "board": clone_board(working_board)},
            )

        if current_conflicts == 0:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 3)
            add_tick(
                phase="SOLVED",
                conflicts_val=0,
                depth_val=restart_count,
                desc="Đã giải xong Sudoku bằng Min-Conflicts!",
            )
            return SolveResult(
                algorithm="min_conflicts",
                success=True,
                board=working_board,
                elapsed_ms=elapsed_ms,
                iterations=total_iterations,
                restarts=restart_count,
                moves=total_moves,
                ticks=ticks,
                stopped_reason="solved",
            )

        # Lặp tối ưu cục bộ trong lần thử hiện tại
        for _ in range(max_iterations):
            total_iterations += 1

            # Tìm tất cả các ô editable đang có xung đột (ở cột hoặc khối 3x3)
            conflicted_cells = []
            for r in range(9):
                for c in editable_in_row[r]:
                    if count_conflicts(working_board, r, c) > 0:
                        conflicted_cells.append((r, c))

            if not conflicted_cells:
                # Không còn ô nào xung đột -> Đã giải được
                elapsed_ms = round((time.perf_counter() - start_time) * 1000, 3)
                add_tick(
                    phase="SOLVED",
                    conflicts_val=0,
                    depth_val=restart_count,
                    desc="Đã tìm thấy trạng thái tối ưu không còn xung đột!",
                )
                return SolveResult(
                    algorithm="min_conflicts",
                    success=True,
                    board=working_board,
                    elapsed_ms=elapsed_ms,
                    iterations=total_iterations,
                    restarts=restart_count,
                    moves=total_moves,
                    ticks=ticks,
                    stopped_reason="solved",
                )

            # Chọn ngẫu nhiên một ô đang có xung đột
            r, c1 = rng.choice(conflicted_cells)
            c1_conflicts = count_conflicts(working_board, r, c1)

            add_tick(
                phase="SELECT",
                cell=(r, c1),
                value=working_board[r][c1],
                conflicts_val=c1_conflicts,
                depth_val=restart_count,
                desc=f"Chọn ô xung đột ({r}, {c1}) giá trị {working_board[r][c1]} (xung đột: {c1_conflicts})",
            )

            other_editables = [c for c in editable_in_row[r] if c != c1]
            if not other_editables:
                continue

            # Đánh giá các phép đổi giá trị (swap) với các ô editable khác cùng hàng
            best_candidates = []
            min_score = float("inf")

            for c2 in other_editables:
                # Thử đổi giá trị
                working_board[r][c1], working_board[r][c2] = working_board[r][c2], working_board[r][c1]
                score = total_conflicts(working_board)
                # Hoàn tác
                working_board[r][c1], working_board[r][c2] = working_board[r][c2], working_board[r][c1]

                if score < min_score:
                    min_score = score
                    best_candidates = [c2]
                elif score == min_score:
                    best_candidates.append(c2)

            # Chọn một ứng viên tốt nhất (ngẫu nhiên nếu hòa điểm)
            chosen_c2 = rng.choice(best_candidates)

            # Áp dụng phép hoán đổi
            working_board[r][c1], working_board[r][chosen_c2] = working_board[r][chosen_c2], working_board[r][c1]
            total_moves += 1
            new_conflicts = total_conflicts(working_board)

            add_tick(
                phase="APPLY",
                cell=(r, c1),
                value=working_board[r][c1],
                conflicts_val=new_conflicts,
                depth_val=restart_count,
                desc=f"Đổi vị trí ({r}, {c1}) <-> ({r}, {chosen_c2}). Tổng xung đột mới: {new_conflicts}",
                api_action={"type": "replace", "board": clone_board(working_board)},
            )

            if new_conflicts == 0:
                elapsed_ms = round((time.perf_counter() - start_time) * 1000, 3)
                add_tick(
                    phase="SOLVED",
                    conflicts_val=0,
                    depth_val=restart_count,
                    desc="Đã giải xong Sudoku bằng Min-Conflicts!",
                )
                return SolveResult(
                    algorithm="min_conflicts",
                    success=True,
                    board=working_board,
                    elapsed_ms=elapsed_ms,
                    iterations=total_iterations,
                    restarts=restart_count,
                    moves=total_moves,
                    ticks=ticks,
                    stopped_reason="solved",
                )

        restart_count += 1

    # Hết ngân sách restarts mà chưa tìm ra nghiệm (Failure hợp lệ của Local Search)
    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 3)
    add_tick(
        phase="FAILED",
        conflicts_val=total_conflicts(working_board),
        depth_val=restart_count,
        desc=f"Hết ngân sách ({max_restarts} restarts, {total_iterations} iterations). Local Search không hội tụ.",
    )

    return SolveResult(
        algorithm="min_conflicts",
        success=False,
        board=working_board,
        elapsed_ms=elapsed_ms,
        iterations=total_iterations,
        restarts=max_restarts,
        moves=total_moves,
        ticks=ticks,
        stopped_reason="budget_exhausted",
    )


# ==============================================================================
# DISPATCHER
# ==============================================================================

def solve(algorithm: str, board: Board, **kwargs) -> SolveResult:
    """Dispatcher điều phối thực thi 1 trong 3 thuật toán."""
    algo = algorithm.lower().strip()
    if algo == "backtracking":
        return solve_backtracking(board, use_mrv=False, **kwargs)
    elif algo == "mrv":
        return solve_backtracking(board, use_mrv=True, **kwargs)
    elif algo in ("min_conflicts", "min-conflicts", "minconflicts", "local_search"):
        return solve_min_conflicts(board, **kwargs)
    else:
        raise ValueError(f"Thuật toán không hỗ trợ: '{algorithm}'. Chỉ hỗ trợ 'backtracking', 'mrv', 'min_conflicts'.")
