# -*- coding: utf-8 -*-
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

"""
generate_dataset.py - Generate 40 Sudoku puzzles dataset for Program B.

Đặc tả (theo PROMPT_ANTIGRAVITY_PROGRAM_B.md mục 6):
- 40 puzzle không trùng nhau.
- 10 puzzle mỗi mức:
    Easy   : 46 clue / 35 ô trống
    Medium : 38 clue / 43 ô trống
    Hard   : 32 clue / 49 ô trống
    Expert : 27 clue / 54 ô trống
- Mỗi puzzle phải có ĐÚNG MỘT nghiệm duy nhất (kiểm tra bằng count_solutions).
- `solution` chỉ dùng để validate/benchmark, KHÔNG truyền vào solve_*().

Thuật toán sinh:
1. Sinh một full board hợp lệ ngẫu nhiên bằng backtracking có xáo trộn ứng viên.
2. Xóa dần từng ô theo thứ tự ngẫu nhiên.
3. Sau mỗi lần xóa, kiểm tra count_solutions(board, limit=2).
   - Nếu == 1: tiếp tục xóa.
   - Nếu >  1: hoàn tác ô đó (không xóa được), bỏ qua và thử ô khác.
4. Lặp đến khi đạt đúng số ô trống mục tiêu của mức đó.

Chạy trực tiếp:
    python B-auto-solver/dataset/generate_dataset.py
    python B-auto-solver/dataset/generate_dataset.py --seed 2024 --output B-auto-solver/dataset/puzzles.json
"""

import argparse
import json
import random
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

Board = List[List[int]]

# ==============================================================================
# THUẬT TOÁN BỔ TRỢ NỘI BỘ (không phụ thuộc solvers.py để tránh vòng import)
# ==============================================================================

def _candidates_gen(board: Board, row: int, col: int) -> List[int]:
    """Trả về danh sách giá trị 1..9 không vi phạm ràng buộc hàng/cột/khối."""
    used: set = set()
    for c in range(9):
        if board[row][c]:
            used.add(board[row][c])
    for r in range(9):
        if board[r][col]:
            used.add(board[r][col])
    br, bc = (row // 3) * 3, (col // 3) * 3
    for r in range(br, br + 3):
        for c in range(bc, bc + 3):
            if board[r][c]:
                used.add(board[r][c])
    return [v for v in range(1, 10) if v not in used]


def _clone(board: Board) -> Board:
    return [row[:] for row in board]


# ==============================================================================
# SINH FULL BOARD HỢP LỆ NGẪU NHIÊN
# ==============================================================================

def generate_full_board(rng: random.Random) -> Board:
    """
    Sinh một full board Sudoku hợp lệ ngẫu nhiên bằng backtracking
    với ứng viên được xáo trộn ngẫu nhiên tại mỗi bước.
    """
    board: Board = [[0] * 9 for _ in range(9)]

    def fill(pos: int) -> bool:
        if pos == 81:
            return True
        r, c = divmod(pos, 9)
        cands = _candidates_gen(board, r, c)
        rng.shuffle(cands)
        for v in cands:
            board[r][c] = v
            if fill(pos + 1):
                return True
            board[r][c] = 0
        return False

    fill(0)
    return board


# ==============================================================================
# ĐẾM NGHIỆM (dừng sớm tại limit)
# ==============================================================================

def count_solutions(board: Board, limit: int = 2) -> int:
    """
    Đếm số nghiệm của board Sudoku.
    Dừng sớm khi tìm đủ `limit` nghiệm (không cần đếm hết).
    Dùng để xác nhận puzzle có đúng một nghiệm duy nhất.
    """
    count = [0]

    def solve(b: Board) -> None:
        if count[0] >= limit:
            return
        # Tìm ô trống đầu tiên
        for r in range(9):
            for c in range(9):
                if b[r][c] == 0:
                    for v in _candidates_gen(b, r, c):
                        b[r][c] = v
                        solve(b)
                        b[r][c] = 0
                        if count[0] >= limit:
                            return
                    return
        # Không còn ô trống → tìm được một nghiệm
        count[0] += 1

    working = _clone(board)
    solve(working)
    return count[0]


# ==============================================================================
# SINH MỘT PUZZLE TỪ FULL BOARD
# ==============================================================================

def generate_puzzle(full_board: Board, target_empty: int, rng: random.Random) -> Optional[Board]:
    """
    Tạo puzzle bằng cách xóa dần ô từ full_board cho đến khi đạt target_empty ô trống.
    Sau mỗi lần xóa, kiểm tra nghiệm duy nhất; hoàn tác nếu tạo ra nhiều nghiệm.
    Trả về puzzle nếu thành công, None nếu không đủ ô để xóa.
    """
    puzzle = _clone(full_board)
    cells = list(range(81))
    rng.shuffle(cells)

    current_empty = 0

    for pos in cells:
        if current_empty >= target_empty:
            break
        r, c = divmod(pos, 9)
        if puzzle[r][c] == 0:
            continue
        saved = puzzle[r][c]
        puzzle[r][c] = 0
        if count_solutions(puzzle, limit=2) == 1:
            current_empty += 1
        else:
            puzzle[r][c] = saved  # hoàn tác

    if current_empty < target_empty:
        return None

    return puzzle


# ==============================================================================
# SINH TOÀN BỘ DATASET
# ==============================================================================

DIFFICULTY_SPECS: Dict[str, Dict] = {
    "easy":   {"clue_count": 46, "empty_count": 35},
    "medium": {"clue_count": 38, "empty_count": 43},
    "hard":   {"clue_count": 32, "empty_count": 49},
    "expert": {"clue_count": 27, "empty_count": 54},
}

PUZZLES_PER_LEVEL = 10


def board_to_key(board: Board) -> str:
    """Biến board thành chuỗi để kiểm tra trùng lặp."""
    return "".join(str(v) for row in board for v in row)


def generate_dataset(seed: int = 42) -> List[Dict]:
    """
    Sinh 40 puzzle Sudoku đảm bảo:
    - 10 puzzle mỗi mức (easy/medium/hard/expert)
    - Không trùng nhau
    - Mỗi puzzle có đúng 1 nghiệm
    - solution được lưu kèm (chỉ dùng để validate/benchmark)
    """
    rng = random.Random(seed)
    dataset: List[Dict] = []
    seen_keys: set = set()
    puzzle_id = 1

    for difficulty, spec in DIFFICULTY_SPECS.items():
        target_empty = spec["empty_count"]
        count = 0
        attempts = 0
        max_attempts = target_empty * 100  # Giới hạn an toàn

        print(f"  [{difficulty.upper()}] Generating {PUZZLES_PER_LEVEL} puzzles (clue={spec['clue_count']}, empty={target_empty})...")

        while count < PUZZLES_PER_LEVEL and attempts < max_attempts:
            attempts += 1

            # Bước 1: Sinh full board hợp lệ ngẫu nhiên
            full = generate_full_board(rng)

            # Bước 2: Xóa dần đến mức độ mong muốn
            puzzle = generate_puzzle(full, target_empty, rng)

            if puzzle is None:
                continue

            # Bước 3: Kiểm tra trùng lặp
            key = board_to_key(puzzle)
            if key in seen_keys:
                continue

            # Bước 4: Xác nhận một nghiệm duy nhất (double-check)
            if count_solutions(puzzle, limit=2) != 1:
                continue

            # Đếm số clue thực tế
            actual_clues = sum(1 for r in range(9) for c in range(9) if puzzle[r][c] != 0)
            actual_empty = 81 - actual_clues

            seen_keys.add(key)
            dataset.append({
                "id": puzzle_id,
                "difficulty": difficulty,
                "clue_count": actual_clues,
                "empty_count": actual_empty,
                "board": puzzle,
                "solution": full,
            })
            puzzle_id += 1
            count += 1
            print(f"    [{difficulty.upper()}] Puzzle {count}/{PUZZLES_PER_LEVEL} OK (clue={actual_clues}, empty={actual_empty}, attempt={attempts})", flush=True)

        if count < PUZZLES_PER_LEVEL:
            raise RuntimeError(
                f"Cannot generate {PUZZLES_PER_LEVEL} puzzles for level '{difficulty}' "
                f"after {max_attempts} attempts. Try a different seed."
            )

    return dataset


# ==============================================================================
# ENTRY POINT
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="Sinh 40 puzzle Sudoku cho bộ dataset Program B.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed để tái lập kết quả (mặc định: 42).")
    parser.add_argument(
        "--output",
        type=str,
        default=str(Path(__file__).parent / "puzzles.json"),
        help="Đường dẫn xuất file puzzles.json.",
    )
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Generating dataset (seed={args.seed})...")
    t0 = time.perf_counter()

    dataset = generate_dataset(seed=args.seed)

    elapsed = time.perf_counter() - t0
    print(f"\nTotal: {len(dataset)} puzzles generated in {elapsed:.2f}s")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print(f"Saved to: {output_path}")

    # Print distribution
    from collections import Counter
    dist = Counter(p["difficulty"] for p in dataset)
    for level in ["easy", "medium", "hard", "expert"]:
        print(f"  {level:8s}: {dist.get(level, 0)} puzzles")


if __name__ == "__main__":
    main()
