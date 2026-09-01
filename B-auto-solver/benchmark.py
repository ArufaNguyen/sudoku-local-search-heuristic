"""
benchmark.py - Chay 640 luot thu nghiem va xuat ket qua.

Theo PROMPT_ANTIGRAVITY_PROGRAM_B.md muc 7:
  - Backtracking : 3 lan / puzzle x 40 puzzle = 120 run
  - MRV          : 3 lan / puzzle x 40 puzzle = 120 run
  - Min-Conflicts: 10 seed co dinh / puzzle x 40 puzzle = 400 run
  Tong: 640 raw run (giu ca run that bai)

Xuat:
  results/results_raw.csv
  results/results_summary.csv
  results/heuristic_effectiveness.csv
  results/local_search_comparison.csv
  results/complexity_trend.csv
  results/charts/runtime_by_difficulty.png
  results/charts/heuristic_nodes.png  (log scale)
  results/charts/local_search_success_rate.png

Chay: python B-auto-solver/benchmark.py
       hoac: python benchmark.py  (tu trong thu muc B-auto-solver/)
"""

import csv
import json
import math
import statistics
import sys
import time
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
B_DIR = Path(__file__).resolve().parent
if str(B_DIR) not in sys.path:
    sys.path.insert(0, str(B_DIR))

from solvers import solve, is_solved, candidates

DATASET_JSON  = B_DIR / "dataset" / "puzzles.json"
RESULTS_DIR   = B_DIR / "results"
CHARTS_DIR    = RESULTS_DIR / "charts"

DIFFICULTIES  = ["easy", "medium", "hard", "expert"]

# ── Tham so benchmark ─────────────────────────────────────────────────────────
BT_RUNS_PER_PUZZLE  = 3       # Backtracking & MRV: 3 lan / puzzle
MC_SEEDS_PER_PUZZLE = 10      # Min-Conflicts: 10 seed co dinh / puzzle
MC_SEEDS            = list(range(10))  # seed 0..9

BT_MAX_NODES        = 2_000_000  # Budget node cho BT / MRV (benchmark - cao hon interactive)
MC_MAX_ITERATIONS   = 1000    # Budget iteration cho moi restart
MC_MAX_RESTARTS     = 50      # Budget restart cho moi run

# ==============================================================================
# PHAN 1: VALIDATE DATASET
# ==============================================================================

def _count_solutions(board, limit=2):
    """Dem nghiem bang backtracking (dung de validate)."""
    from solvers import candidates as cands

    empty = [(r, c) for r in range(9) for c in range(9) if board[r][c] == 0]
    count = [0]

    def bt(idx):
        if count[0] >= limit:
            return
        if idx == len(empty):
            count[0] += 1
            return
        r, c = empty[idx]
        for v in cands(board, r, c):
            board[r][c] = v
            bt(idx + 1)
            board[r][c] = 0

    bt(0)
    return count[0]


def validate_dataset(puzzles):
    """
    Validate 40 puzzle truoc khi chay benchmark.
    Tra ve (ok, error_msg).
    """
    print("Validating dataset...", flush=True)

    if len(puzzles) != 40:
        return False, f"Expected 40 puzzles, got {len(puzzles)}"

    by_level = {}
    for p in puzzles:
        by_level.setdefault(p["difficulty"], []).append(p)

    for level in DIFFICULTIES:
        if len(by_level.get(level, [])) != 10:
            return False, f"Expected 10 puzzles for '{level}', got {len(by_level.get(level, []))}"

    # Kiem tra nghiem duy nhat (lay mau 1 puzzle / muc de nhanh)
    for level in DIFFICULTIES:
        p = by_level[level][0]
        board = [row[:] for row in p["board"]]
        n = _count_solutions(board, limit=2)
        if n != 1:
            return False, f"Puzzle {p['id']} ({level}) has {n} solutions, expected 1"

    print(f"  Dataset OK: 40 puzzles, 10 per difficulty, unique solutions verified.", flush=True)
    return True, ""


# ==============================================================================
# PHAN 2: CHAY TUNG RUN
# ==============================================================================

def run_exact(puzzle, algorithm, run_id):
    """Chay 1 run Backtracking hoac MRV, tra ve dict row."""
    board = [row[:] for row in puzzle["board"]]
    result = solve(algorithm, board, max_nodes=BT_MAX_NODES, record_ticks=False)
    return {
        "puzzle_id":      puzzle["id"],
        "difficulty":     puzzle["difficulty"],
        "algorithm":      algorithm,
        "run_id":         run_id,
        "seed":           "",
        "success":        result.success,
        "elapsed_ms":     round(result.elapsed_ms, 4),
        "nodes_explored": result.nodes_explored,
        "backtracks":     result.backtracks,
        "max_depth":      result.max_depth,
        "iterations":     0,
        "restarts":       0,
        "moves":          0,
        "stopped_reason": result.stopped_reason,
    }


def run_min_conflicts(puzzle, seed):
    """Chay 1 run Min-Conflicts voi seed co dinh, tra ve dict row."""
    board = [row[:] for row in puzzle["board"]]
    result = solve(
        "min_conflicts", board,
        max_iterations=MC_MAX_ITERATIONS,
        max_restarts=MC_MAX_RESTARTS,
        seed=seed,
        record_ticks=False,
    )
    return {
        "puzzle_id":      puzzle["id"],
        "difficulty":     puzzle["difficulty"],
        "algorithm":      "min_conflicts",
        "run_id":         seed,
        "seed":           seed,
        "success":        result.success,
        "elapsed_ms":     round(result.elapsed_ms, 4),
        "nodes_explored": 0,
        "backtracks":     0,
        "max_depth":      0,
        "iterations":     result.iterations,
        "restarts":       result.restarts,
        "moves":          result.moves,
        "stopped_reason": result.stopped_reason,
    }


# ==============================================================================
# PHAN 3: TONG HOP THONG KE
# ==============================================================================

def _percentile(data, pct):
    """Tinh percentile cua data (list float)."""
    if not data:
        return 0.0
    s = sorted(data)
    idx = (len(s) - 1) * pct / 100.0
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (idx - lo)


def aggregate(rows, key_difficulty=None, key_algorithm=None):
    """Loc va tinh thong ke cho tap rows theo difficulty va algorithm."""
    subset = [r for r in rows
              if (key_difficulty is None or r["difficulty"] == key_difficulty)
              and (key_algorithm  is None or r["algorithm"]  == key_algorithm)]
    if not subset:
        return None

    ms_list    = [r["elapsed_ms"]     for r in subset]
    nodes_list = [r["nodes_explored"] for r in subset]
    bt_list    = [r["backtracks"]     for r in subset]
    dep_list   = [r["max_depth"]      for r in subset]
    iter_list  = [r["iterations"]     for r in subset]
    rest_list  = [r["restarts"]       for r in subset]
    mov_list   = [r["moves"]          for r in subset]
    ok_list    = [r["success"]        for r in subset]

    n       = len(subset)
    n_ok    = sum(ok_list)

    def safe_mean(lst):
        return statistics.mean(lst) if lst else 0.0
    def safe_median(lst):
        return statistics.median(lst) if lst else 0.0
    def safe_std(lst):
        return statistics.stdev(lst) if len(lst) >= 2 else 0.0

    return {
        "n_runs":        n,
        "n_success":     n_ok,
        "success_rate":  round(n_ok / n, 4) if n else 0,
        "mean_ms":       round(safe_mean(ms_list), 3),
        "median_ms":     round(safe_median(ms_list), 3),
        "std_ms":        round(safe_std(ms_list), 3),
        "p95_ms":        round(_percentile(ms_list, 95), 3),
        "mean_nodes":    round(safe_mean(nodes_list), 1),
        "mean_backtracks": round(safe_mean(bt_list), 1),
        "mean_depth":    round(safe_mean(dep_list), 2),
        "mean_iterations": round(safe_mean(iter_list), 1),
        "mean_restarts": round(safe_mean(rest_list), 2),
        "mean_moves":    round(safe_mean(mov_list), 1),
    }


# ==============================================================================
# PHAN 4: XUAT CSV
# ==============================================================================

RAW_FIELDS = [
    "puzzle_id", "difficulty", "algorithm", "run_id", "seed",
    "success", "elapsed_ms", "nodes_explored", "backtracks", "max_depth",
    "iterations", "restarts", "moves", "stopped_reason",
]

SUMMARY_FIELDS = [
    "difficulty", "algorithm",
    "n_runs", "n_success", "success_rate",
    "mean_ms", "median_ms", "std_ms", "p95_ms",
    "mean_nodes", "mean_backtracks", "mean_depth",
    "mean_iterations", "mean_restarts", "mean_moves",
]


def write_results_raw(rows, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=RAW_FIELDS)
        w.writeheader()
        w.writerows(rows)


def write_results_summary(rows, path):
    algos = ["backtracking", "mrv", "min_conflicts"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS)
        w.writeheader()
        for diff in DIFFICULTIES:
            for algo in algos:
                agg = aggregate(rows, diff, algo)
                if agg:
                    w.writerow({"difficulty": diff, "algorithm": algo, **agg})


def write_heuristic_effectiveness(rows, path):
    """% giam node cua MRV so voi Backtracking theo difficulty."""
    fields = [
        "difficulty",
        "bt_mean_nodes", "mrv_mean_nodes", "node_reduction_pct",
        "bt_mean_ms", "mrv_mean_ms", "ms_reduction_pct",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for diff in DIFFICULTIES:
            bt  = aggregate(rows, diff, "backtracking")
            mrv = aggregate(rows, diff, "mrv")
            if not bt or not mrv:
                continue
            node_red = (
                round((1 - mrv["mean_nodes"] / bt["mean_nodes"]) * 100, 2)
                if bt["mean_nodes"] > 0 else 0.0
            )
            ms_red = (
                round((1 - mrv["mean_ms"] / bt["mean_ms"]) * 100, 2)
                if bt["mean_ms"] > 0 else 0.0
            )
            w.writerow({
                "difficulty":         diff,
                "bt_mean_nodes":      bt["mean_nodes"],
                "mrv_mean_nodes":     mrv["mean_nodes"],
                "node_reduction_pct": node_red,
                "bt_mean_ms":         bt["mean_ms"],
                "mrv_mean_ms":        mrv["mean_ms"],
                "ms_reduction_pct":   ms_red,
            })


def write_local_search_comparison(rows, path):
    """So sanh Min-Conflicts voi exact search theo difficulty."""
    fields = [
        "difficulty", "algorithm",
        "mean_ms", "median_ms", "std_ms",
        "success_rate", "mean_iterations", "mean_restarts", "mean_moves",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for diff in DIFFICULTIES:
            for algo in ["backtracking", "mrv", "min_conflicts"]:
                agg = aggregate(rows, diff, algo)
                if agg:
                    w.writerow({
                        "difficulty":      diff,
                        "algorithm":       algo,
                        "mean_ms":         agg["mean_ms"],
                        "median_ms":       agg["median_ms"],
                        "std_ms":          agg["std_ms"],
                        "success_rate":    agg["success_rate"],
                        "mean_iterations": agg["mean_iterations"],
                        "mean_restarts":   agg["mean_restarts"],
                        "mean_moves":      agg["mean_moves"],
                    })


def write_complexity_trend(rows, puzzles_by_diff, path):
    """Xu huong do phuc tap theo difficulty (empty cells vs metrics)."""
    EMPTY_COUNT = {"easy": 35, "medium": 43, "hard": 49, "expert": 54}
    CLUE_COUNT  = {"easy": 46, "medium": 38, "hard": 32, "expert": 27}
    fields = [
        "difficulty", "empty_count", "clue_count",
        "bt_mean_nodes", "mrv_mean_nodes",
        "mc_mean_iterations",
        "bt_mean_ms", "mrv_mean_ms", "mc_mean_ms",
        "mc_success_rate",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for diff in DIFFICULTIES:
            bt  = aggregate(rows, diff, "backtracking")
            mrv = aggregate(rows, diff, "mrv")
            mc  = aggregate(rows, diff, "min_conflicts")
            w.writerow({
                "difficulty":        diff,
                "empty_count":       EMPTY_COUNT[diff],
                "clue_count":        CLUE_COUNT[diff],
                "bt_mean_nodes":     bt["mean_nodes"]     if bt  else 0,
                "mrv_mean_nodes":    mrv["mean_nodes"]    if mrv else 0,
                "mc_mean_iterations":mc["mean_iterations"] if mc else 0,
                "bt_mean_ms":        bt["mean_ms"]        if bt  else 0,
                "mrv_mean_ms":       mrv["mean_ms"]       if mrv else 0,
                "mc_mean_ms":        mc["mean_ms"]        if mc  else 0,
                "mc_success_rate":   mc["success_rate"]   if mc  else 0,
            })


# ==============================================================================
# PHAN 5: BIEU DO PNG
# ==============================================================================

def _try_import_matplotlib():
    try:
        import matplotlib
        matplotlib.use("Agg")  # Non-interactive backend
        import matplotlib.pyplot as plt
        return plt
    except ImportError:
        return None


def _try_import_pillow():
    try:
        from PIL import Image, ImageDraw, ImageFont
        return Image, ImageDraw, ImageFont
    except ImportError:
        return None


# ==============================================================================
# PURE STDLIB PNG WRITER (khong can thu vien ngoai)
# ==============================================================================

import struct
import zlib as _zlib

def _png_write(path, pixels, w, h):
    """
    Ghi file PNG tu mang pixels (list of list of (R,G,B) tuples).
    Khong phu thuoc thu vien ngoai — chi dung struct + zlib.
    """
    def _chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        c += struct.pack(">I", _zlib.crc32(tag + data) & 0xFFFFFFFF)
        return c

    raw = b""
    for row in pixels:
        raw += b"\x00"  # filter type = None
        for r, g, b in row:
            raw += bytes([r, g, b])

    compressed = _zlib.compress(raw, 9)
    png  = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += _chunk(b"IDAT", compressed)
    png += _chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


def _make_charts_stdlib(rows, charts_dir):
    """
    Ve 3 bieu do PNG bang stdlib thuan tuy (rect, line, text khong co font fancy).
    Dung bitmap ASCII rendering cho ky tu so.
    """
    W, H = 900, 480
    BG    = (25, 25, 40)
    WHITE = (210, 210, 210)
    GRAY  = (90, 90, 110)
    ALGO_COLORS = [
        (220, 60, 60),   # BT - red
        (46, 200, 100),  # MRV - green
        (52, 140, 220),  # MC - blue
    ]

    def _new_canvas():
        return [[BG for _ in range(W)] for _ in range(H)]

    def _fill_rect(px, x0, y0, x1, y1, color):
        for y in range(max(0, y0), min(H, y1 + 1)):
            for x in range(max(0, x0), min(W, x1 + 1)):
                px[y][x] = color

    def _draw_hline(px, y, x0, x1, color):
        for x in range(max(0, x0), min(W, x1 + 1)):
            if 0 <= y < H:
                px[y][x] = color

    def _draw_vline(px, x, y0, y1, color):
        for y in range(max(0, y0), min(H, y1 + 1)):
            if 0 <= x < W:
                px[y][x] = color

    # 5x7 bitmap font cho chu so va mot so ky tu co ban
    _FONT = {
        '0': [0b01110,0b10001,0b10011,0b10101,0b11001,0b10001,0b01110],
        '1': [0b00100,0b01100,0b00100,0b00100,0b00100,0b00100,0b01110],
        '2': [0b01110,0b10001,0b00001,0b00110,0b01000,0b10000,0b11111],
        '3': [0b11111,0b00001,0b00010,0b00110,0b00001,0b10001,0b01110],
        '4': [0b00010,0b00110,0b01010,0b10010,0b11111,0b00010,0b00010],
        '5': [0b11111,0b10000,0b11110,0b00001,0b00001,0b10001,0b01110],
        '6': [0b00110,0b01000,0b10000,0b11110,0b10001,0b10001,0b01110],
        '7': [0b11111,0b00001,0b00010,0b00100,0b01000,0b01000,0b01000],
        '8': [0b01110,0b10001,0b10001,0b01110,0b10001,0b10001,0b01110],
        '9': [0b01110,0b10001,0b10001,0b01111,0b00001,0b00010,0b01100],
        '.': [0b00000,0b00000,0b00000,0b00000,0b00000,0b00110,0b00110],
        '%': [0b11000,0b11001,0b00010,0b00100,0b01000,0b10011,0b00011],
        'k': [0b10000,0b10000,0b10010,0b10100,0b11000,0b10100,0b10010],
        'm': [0b00000,0b00000,0b11010,0b10101,0b10101,0b10001,0b10001],
        's': [0b00000,0b01110,0b10000,0b01100,0b00010,0b10010,0b01100],
        ' ': [0]*7,
        '-': [0b00000,0b00000,0b00000,0b11111,0b00000,0b00000,0b00000],
        'B': [0b11110,0b10001,0b10001,0b11110,0b10001,0b10001,0b11110],
        'T': [0b11111,0b00100,0b00100,0b00100,0b00100,0b00100,0b00100],
        'M': [0b10001,0b11011,0b10101,0b10001,0b10001,0b10001,0b10001],
        'R': [0b11110,0b10001,0b10001,0b11110,0b10100,0b10010,0b10001],
        'V': [0b10001,0b10001,0b10001,0b10001,0b01010,0b01010,0b00100],
        'C': [0b01110,0b10001,0b10000,0b10000,0b10000,0b10001,0b01110],
        'E': [0b11111,0b10000,0b10000,0b11110,0b10000,0b10000,0b11111],
        'a': [0b00000,0b01110,0b00001,0b01111,0b10001,0b10011,0b01101],
        'd': [0b00001,0b00001,0b01101,0b10011,0b10001,0b10011,0b01101],
        'e': [0b00000,0b01110,0b10001,0b11111,0b10000,0b10001,0b01110],
        'f': [0b00011,0b00100,0b01110,0b00100,0b00100,0b00100,0b00100],
        'g': [0b00000,0b01101,0b10011,0b10001,0b01111,0b00001,0b01110],
        'h': [0b10000,0b10000,0b10110,0b11001,0b10001,0b10001,0b10001],
        'i': [0b00100,0b00000,0b01100,0b00100,0b00100,0b00100,0b01110],
        'l': [0b01100,0b00100,0b00100,0b00100,0b00100,0b00100,0b01110],
        'n': [0b00000,0b00000,0b10110,0b11001,0b10001,0b10001,0b10001],
        'o': [0b00000,0b01110,0b10001,0b10001,0b10001,0b10001,0b01110],
        'p': [0b00000,0b11110,0b10001,0b11110,0b10000,0b10000,0b10000],
        'r': [0b00000,0b00000,0b10110,0b11001,0b10000,0b10000,0b10000],
        't': [0b00100,0b00100,0b01110,0b00100,0b00100,0b00101,0b00010],
        'u': [0b00000,0b00000,0b10001,0b10001,0b10001,0b10011,0b01101],
        'x': [0b00000,0b00000,0b10001,0b01010,0b00100,0b01010,0b10001],
        'y': [0b00000,0b00000,0b10001,0b10001,0b01111,0b00001,0b01110],
        'z': [0b00000,0b00000,0b11111,0b00010,0b00100,0b01000,0b11111],
        'A': [0b00100,0b01010,0b10001,0b11111,0b10001,0b10001,0b10001],
        'D': [0b11110,0b10001,0b10001,0b10001,0b10001,0b10001,0b11110],
        'G': [0b01110,0b10001,0b10000,0b10111,0b10001,0b10001,0b01110],
        'H': [0b10001,0b10001,0b10001,0b11111,0b10001,0b10001,0b10001],
        'I': [0b01110,0b00100,0b00100,0b00100,0b00100,0b00100,0b01110],
        'L': [0b10000,0b10000,0b10000,0b10000,0b10000,0b10000,0b11111],
        'N': [0b10001,0b11001,0b10101,0b10011,0b10001,0b10001,0b10001],
        'O': [0b01110,0b10001,0b10001,0b10001,0b10001,0b10001,0b01110],
        'P': [0b11110,0b10001,0b10001,0b11110,0b10000,0b10000,0b10000],
        'S': [0b01111,0b10000,0b10000,0b01110,0b00001,0b00001,0b11110],
        'W': [0b10001,0b10001,0b10001,0b10101,0b10101,0b11011,0b10001],
        'X': [0b10001,0b10001,0b01010,0b00100,0b01010,0b10001,0b10001],
        'Y': [0b10001,0b10001,0b01010,0b00100,0b00100,0b00100,0b00100],
        'Z': [0b11111,0b00001,0b00010,0b00100,0b01000,0b10000,0b11111],
        '/': [0b00001,0b00010,0b00100,0b01000,0b10000,0b00000,0b00000],
        '(': [0b00010,0b00100,0b01000,0b01000,0b01000,0b00100,0b00010],
        ')': [0b01000,0b00100,0b00010,0b00010,0b00010,0b00100,0b01000],
        ':': [0b00000,0b00110,0b00110,0b00000,0b00110,0b00110,0b00000],
        ',': [0b00000,0b00000,0b00000,0b00000,0b00110,0b00110,0b01000],
        '+': [0b00000,0b00100,0b00100,0b11111,0b00100,0b00100,0b00000],
        '>': [0b01000,0b00100,0b00010,0b00001,0b00010,0b00100,0b01000],
        '<': [0b00001,0b00010,0b00100,0b01000,0b00100,0b00010,0b00001],
        '=': [0b00000,0b00000,0b11111,0b00000,0b11111,0b00000,0b00000],
    }

    def _draw_text(px, text, sx, sy, color=WHITE, scale=1):
        cx = sx
        for ch in str(text):
            bitmap = _FONT.get(ch, _FONT.get(' ', [0]*7))
            for row_i, bits in enumerate(bitmap):
                for col_i in range(5):
                    if bits & (1 << (4 - col_i)):
                        for dy in range(scale):
                            for dx in range(scale):
                                ry = sy + row_i * scale + dy
                                rx = cx + col_i * scale + dx
                                if 0 <= rx < W and 0 <= ry < H:
                                    px[ry][rx] = color
            cx += (6 * scale)
        return cx

    def _bar_chart(filename, title, series_data, ylabel="",
                   log_scale=False, bar_colors_override=None):
        """
        series_data: list of (label, list_of_4_values, color)
        """
        px = _new_canvas()
        ml, mr, mt, mb = 80, 20, 40, 50
        pw = W - ml - mr
        ph = H - mt - mb

        n_groups  = 4  # DIFFICULTIES
        n_series  = len(series_data)
        group_gap = 10
        group_w   = (pw - group_gap * (n_groups - 1)) // n_groups
        bar_gap   = 2
        bar_w     = max(4, (group_w - bar_gap * (n_series - 1)) // n_series)

        all_vals = [v for _, vals, _ in series_data for v in vals if v > 0]
        max_val  = max(all_vals) if all_vals else 1

        import math as _m
        if log_scale:
            log_max = _m.ceil(_m.log10(max(max_val, 1))) + 0.3
            def to_y(v):
                if v <= 0:
                    return mt + ph
                lv = _m.log10(max(v, 0.01))
                frac = lv / log_max
                return int(mt + ph * (1.0 - max(0.0, min(frac, 1.0))))
        else:
            def to_y(v):
                frac = v / max_val if max_val > 0 else 0
                return int(mt + ph * (1.0 - max(0.0, min(frac, 1.0))))

        # Axes
        _draw_vline(px, ml, mt, mt + ph, GRAY)
        _draw_hline(px, mt + ph, ml, ml + pw, GRAY)

        # Grid lines (5 horizontal)
        for gi in range(1, 6):
            gy = mt + int(ph * gi / 5)
            _draw_hline(px, gy, ml + 1, ml + pw, (50, 50, 65))

        # Bars
        for gi, diff in enumerate(DIFFICULTIES):
            gx = ml + gi * (group_w + group_gap)
            for si, (slabel, svals, scolor) in enumerate(series_data):
                v  = svals[gi]
                bx = gx + si * (bar_w + bar_gap)
                by = to_y(v)
                col = bar_colors_override[gi] if bar_colors_override else scolor
                _fill_rect(px, bx, by, bx + bar_w - 1, mt + ph - 1, col)
                # Value label above bar
                lbl = f"{v:.0f}" if v >= 10 else f"{v:.1f}"
                _draw_text(px, lbl, bx, max(by - 10, mt + 2),
                           color=WHITE, scale=1)
            # X-axis diff label
            _draw_text(px, diff[:4], gx, mt + ph + 5, color=WHITE, scale=1)

        # Y-axis label
        _draw_text(px, ylabel[:10], 2, mt + ph // 2, color=GRAY, scale=1)

        # Title
        _draw_text(px, title[:60], ml, 10, color=WHITE, scale=1)

        # Legend
        for si, (slabel, _, scolor) in enumerate(series_data):
            lx = ml + si * 120
            _fill_rect(px, lx, H - 30, lx + 10, H - 22, scolor)
            _draw_text(px, slabel[:10], lx + 14, H - 30, color=WHITE, scale=1)

        _png_write(charts_dir / filename, px, W, H)
        print(f"  [Chart] {filename} (stdlib PNG)", flush=True)

    # Chart 1: Runtime
    series1 = []
    for si, algo in enumerate(["backtracking", "mrv", "min_conflicts"]):
        agg_vals = [(aggregate(rows, d, algo)["mean_ms"] if aggregate(rows, d, algo) else 0)
                    for d in DIFFICULTIES]
        labels = {"backtracking": "BT", "mrv": "MRV", "min_conflicts": "MC"}
        series1.append((labels[algo], agg_vals, ALGO_COLORS[si]))
    _bar_chart("runtime_by_difficulty.png",
               "Runtime ms by Difficulty", series1, ylabel="ms")

    # Chart 2: Nodes log scale
    series2 = []
    for si, algo in enumerate(["backtracking", "mrv"]):
        agg_vals = [max(aggregate(rows, d, algo)["mean_nodes"] if aggregate(rows, d, algo) else 1, 1)
                    for d in DIFFICULTIES]
        labels = {"backtracking": "BT", "mrv": "MRV"}
        series2.append((labels[algo], agg_vals, ALGO_COLORS[si]))
    _bar_chart("heuristic_nodes.png",
               "Nodes BT vs MRV (log)", series2,
               ylabel="nodes", log_scale=True)

    # Chart 3: MC success rate
    sr_vals = [(aggregate(rows, d, "min_conflicts")["success_rate"] * 100
                if aggregate(rows, d, "min_conflicts") else 0)
               for d in DIFFICULTIES]
    sr_colors = [
        (46, 200, 100) if v >= 80 else (240, 150, 20) if v >= 50 else (220, 60, 60)
        for v in sr_vals
    ]
    _bar_chart("local_search_success_rate.png",
               "MC Success Rate %",
               [("MC%", sr_vals, ALGO_COLORS[2])],
               ylabel="%", bar_colors_override=sr_colors)


def _make_charts_matplotlib(plt, rows, charts_dir):
    """Ve bieu do dung matplotlib."""
    diffs = DIFFICULTIES
    algos = ["backtracking", "mrv", "min_conflicts"]
    algo_labels = {"backtracking": "Backtracking", "mrv": "MRV", "min_conflicts": "Min-Conflicts"}
    colors = {"backtracking": "#e74c3c", "mrv": "#2ecc71", "min_conflicts": "#3498db"}

    # ── Chart 1: Runtime by difficulty ────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(9, 5))
    x = range(len(diffs))
    bar_w = 0.25
    for i, algo in enumerate(algos):
        vals = []
        for diff in diffs:
            agg = aggregate(rows, diff, algo)
            vals.append(agg["mean_ms"] if agg else 0)
        offset = (i - 1) * bar_w
        bars = ax.bar([xi + offset for xi in x], vals, bar_w,
                      label=algo_labels[algo], color=colors[algo], alpha=0.85)
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                    f"{v:.1f}", ha="center", va="bottom", fontsize=7)
    ax.set_xticks(list(x))
    ax.set_xticklabels([d.capitalize() for d in diffs])
    ax.set_xlabel("Difficulty")
    ax.set_ylabel("Mean Runtime (ms)")
    ax.set_title("Mean Runtime by Difficulty and Algorithm")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(charts_dir / "runtime_by_difficulty.png", dpi=120)
    plt.close()
    print("  [Chart] runtime_by_difficulty.png", flush=True)

    # ── Chart 2: Nodes log scale ──────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(9, 5))
    bar_w = 0.35
    for i, algo in enumerate(["backtracking", "mrv"]):
        vals = [max(aggregate(rows, d, algo)["mean_nodes"] if aggregate(rows, d, algo) else 1, 1)
                for d in diffs]
        offset = (i - 0.5) * bar_w
        ax.bar([xi + offset for xi in range(len(diffs))], vals, bar_w,
               label=algo_labels[algo], color=colors[algo], alpha=0.85)
    ax.set_yscale("log")
    ax.set_xticks(list(range(len(diffs))))
    ax.set_xticklabels([d.capitalize() for d in diffs])
    ax.set_xlabel("Difficulty")
    ax.set_ylabel("Mean Nodes Explored (log scale)")
    ax.set_title("Nodes Explored: Backtracking vs MRV (Log Scale)")
    ax.legend()
    ax.grid(axis="y", alpha=0.3, which="both")
    plt.tight_layout()
    plt.savefig(charts_dir / "heuristic_nodes.png", dpi=120)
    plt.close()
    print("  [Chart] heuristic_nodes.png", flush=True)

    # ── Chart 3: MC success rate ──────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(7, 4))
    vals = [(aggregate(rows, d, "min_conflicts")["success_rate"] * 100)
            if aggregate(rows, d, "min_conflicts") else 0 for d in diffs]
    bar_colors = ["#2ecc71" if v >= 80 else "#f39c12" if v >= 50 else "#e74c3c" for v in vals]
    bars = ax.bar([d.capitalize() for d in diffs], vals, color=bar_colors, alpha=0.85, width=0.5)
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                f"{v:.1f}%", ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax.set_ylim(0, 115)
    ax.set_xlabel("Difficulty")
    ax.set_ylabel("Success Rate (%)")
    ax.set_title("Min-Conflicts Success Rate by Difficulty")
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(charts_dir / "local_search_success_rate.png", dpi=120)
    plt.close()
    print("  [Chart] local_search_success_rate.png", flush=True)


def _make_charts_pillow(pil_modules, rows, charts_dir):
    """Ve bieu do don gian dung Pillow (fallback khi khong co matplotlib)."""
    Image, ImageDraw, ImageFont = pil_modules

    W, H = 900, 500
    BG   = (30, 30, 46)
    WHITE = (220, 220, 220)
    GRAY  = (80, 80, 100)
    COLORS = [
        (231, 76, 60),    # red - backtracking
        (46, 204, 113),   # green - mrv
        (52, 152, 219),   # blue - min_conflicts
    ]

    def _make_bar_chart(filename, title, series, labels, y_label,
                        log_scale=False, bar_colors=None):
        """series = list of (name, values_per_diff)"""
        img  = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)

        margin_l, margin_r, margin_t, margin_b = 90, 30, 50, 60
        plot_w = W - margin_l - margin_r
        plot_h = H - margin_t - margin_b

        n_groups = len(DIFFICULTIES)
        n_series = len(series)
        group_w  = plot_w // n_groups
        bar_w    = max(1, (group_w - 10) // n_series)

        # Compute max value
        all_vals = [v for _, vals in series for v in vals if v > 0]
        if not all_vals:
            all_vals = [1]
        max_val = max(all_vals)
        if log_scale:
            import math as _m
            log_max = _m.log10(max(max_val, 1)) + 0.5
            def to_y(v):
                if v <= 0:
                    return margin_t + plot_h
                lv = _m.log10(max(v, 0.1))
                frac = lv / log_max
                return int(margin_t + plot_h * (1 - max(0, min(frac, 1))))
        else:
            def to_y(v):
                frac = v / max_val if max_val > 0 else 0
                return int(margin_t + plot_h * (1 - max(0, min(frac, 1))))

        # Title
        draw.text((W // 2 - len(title) * 4, 10), title, fill=WHITE)

        # Axes
        draw.line([(margin_l, margin_t), (margin_l, margin_t + plot_h),
                   (margin_l + plot_w, margin_t + plot_h)], fill=GRAY, width=2)

        # Bars
        for gi, diff in enumerate(DIFFICULTIES):
            gx = margin_l + gi * group_w + 5
            for si, (sname, svals) in enumerate(series):
                v   = svals[gi]
                bx  = gx + si * bar_w
                by  = to_y(v)
                col = bar_colors[gi] if bar_colors else COLORS[si % len(COLORS)]
                draw.rectangle([bx, by, bx + bar_w - 2, margin_t + plot_h], fill=col)
                # Value label
                if v > 0:
                    lbl = f"{v:.0f}" if v >= 10 else f"{v:.1f}"
                    draw.text((bx + 1, max(by - 12, margin_t)), lbl, fill=WHITE)
            # X label
            draw.text((gx + group_w // 2 - 15, margin_t + plot_h + 5), diff.capitalize(), fill=WHITE)

        # Legend
        for si, (sname, _) in enumerate(series):
            lx = margin_l + si * 130
            draw.rectangle([lx, H - 20, lx + 12, H - 10], fill=COLORS[si % len(COLORS)])
            draw.text((lx + 15, H - 22), sname, fill=WHITE)

        # Y label
        draw.text((5, H // 2 - 30), y_label[:15], fill=GRAY)

        img.save(charts_dir / filename)
        print(f"  [Chart] {filename}", flush=True)

    # Chart 1: Runtime
    runtime_series = []
    for algo in ["backtracking", "mrv", "min_conflicts"]:
        vals = [(aggregate(rows, d, algo)["mean_ms"] if aggregate(rows, d, algo) else 0)
                for d in DIFFICULTIES]
        runtime_series.append((algo[:3].upper(), vals))
    _make_bar_chart("runtime_by_difficulty.png",
                    "Mean Runtime by Difficulty (ms)",
                    runtime_series, DIFFICULTIES, "ms")

    # Chart 2: Nodes log scale
    nodes_series = []
    for algo in ["backtracking", "mrv"]:
        vals = [max(aggregate(rows, d, algo)["mean_nodes"] if aggregate(rows, d, algo) else 1, 1)
                for d in DIFFICULTIES]
        nodes_series.append((algo[:3].upper(), vals))
    _make_bar_chart("heuristic_nodes.png",
                    "Nodes Explored: BT vs MRV (log scale)",
                    nodes_series, DIFFICULTIES, "nodes (log)", log_scale=True)

    # Chart 3: MC success rate
    sr_vals = [(aggregate(rows, d, "min_conflicts")["success_rate"] * 100)
               if aggregate(rows, d, "min_conflicts") else 0 for d in DIFFICULTIES]
    sr_colors = [(46, 204, 113) if v >= 80 else (243, 156, 18) if v >= 50 else (231, 76, 60)
                 for v in sr_vals]
    _make_bar_chart("local_search_success_rate.png",
                    "Min-Conflicts Success Rate (%)",
                    [("MC", sr_vals)], DIFFICULTIES, "Success Rate %",
                    bar_colors=sr_colors)


def make_charts(rows, charts_dir):
    charts_dir.mkdir(parents=True, exist_ok=True)

    plt = _try_import_matplotlib()
    if plt is not None:
        _make_charts_matplotlib(plt, rows, charts_dir)
        return

    pil = _try_import_pillow()
    if pil is not None:
        print("  [INFO] matplotlib not available, using Pillow fallback for charts.", flush=True)
        _make_charts_pillow(pil, rows, charts_dir)
        return

    print("  [INFO] Using stdlib PNG writer (no external dependencies).", flush=True)
    _make_charts_stdlib(rows, charts_dir)


# ==============================================================================
# PHAN 6: IN TERMINAL SUMMARY
# ==============================================================================

def print_summary(rows):
    print()
    print("=" * 68)
    print("  BENCHMARK SUMMARY")
    print("=" * 68)

    # ── Heuristic effectiveness (MRV vs BT) ───────────────────────────────────
    print()
    print("  Node Reduction: MRV vs Backtracking")
    print(f"  {'Difficulty':<10} {'BT nodes':>12} {'MRV nodes':>12} {'Reduction':>10}  {'BT ms':>8}  {'MRV ms':>8}")
    print(f"  {'-'*10} {'-'*12} {'-'*12} {'-'*10}  {'-'*8}  {'-'*8}")
    for diff in DIFFICULTIES:
        bt  = aggregate(rows, diff, "backtracking")
        mrv = aggregate(rows, diff, "mrv")
        if bt and mrv:
            red_pct = (1 - mrv["mean_nodes"] / bt["mean_nodes"]) * 100 if bt["mean_nodes"] > 0 else 0
            print(f"  {diff.capitalize():<10} {bt['mean_nodes']:>12,.0f} {mrv['mean_nodes']:>12,.0f}"
                  f" {red_pct:>9.1f}%  {bt['mean_ms']:>7.1f}ms  {mrv['mean_ms']:>7.1f}ms")

    # ── Min-Conflicts success rate ─────────────────────────────────────────────
    print()
    print("  Min-Conflicts Success Rate")
    print(f"  {'Difficulty':<10} {'Success':>8} {'Total':>7} {'Rate':>8}  {'Mean iters':>12}  {'Mean ms':>8}")
    print(f"  {'-'*10} {'-'*8} {'-'*7} {'-'*8}  {'-'*12}  {'-'*8}")
    for diff in DIFFICULTIES:
        mc = aggregate(rows, diff, "min_conflicts")
        if mc:
            print(f"  {diff.capitalize():<10} {mc['n_success']:>8} {mc['n_runs']:>7}"
                  f" {mc['success_rate']*100:>7.1f}%  {mc['mean_iterations']:>12,.1f}  {mc['mean_ms']:>7.1f}ms")

    # ── Full runtime table ─────────────────────────────────────────────────────
    print()
    print("  Runtime Summary (mean ms)")
    print(f"  {'Difficulty':<10} {'BT':>9} {'MRV':>9} {'MC':>9}")
    print(f"  {'-'*10} {'-'*9} {'-'*9} {'-'*9}")
    for diff in DIFFICULTIES:
        bt  = aggregate(rows, diff, "backtracking")
        mrv = aggregate(rows, diff, "mrv")
        mc  = aggregate(rows, diff, "min_conflicts")
        bt_ms  = f"{bt['mean_ms']:>8.1f}" if bt  else "       —"
        mrv_ms = f"{mrv['mean_ms']:>8.1f}" if mrv else "       —"
        mc_ms  = f"{mc['mean_ms']:>8.1f}" if mc  else "       —"
        print(f"  {diff.capitalize():<10} {bt_ms} {mrv_ms} {mc_ms}")

    print()
    print("=" * 68)


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    # ── Kiem tra thu vien matplotlib ─────────────────────────────────────────
    has_matplotlib = _try_import_matplotlib() is not None

    # ── Tao thu muc output ────────────────────────────────────────────────────
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)

    # ── Doc dataset ───────────────────────────────────────────────────────────
    if not DATASET_JSON.exists():
        print(f"ERROR: {DATASET_JSON} not found.", file=sys.stderr)
        print("Run: python dataset/generate_dataset.py --seed 42", file=sys.stderr)
        sys.exit(1)

    with open(DATASET_JSON, encoding="utf-8") as f:
        puzzles = json.load(f)

    # ── Validate ──────────────────────────────────────────────────────────────
    ok, err = validate_dataset(puzzles)
    if not ok:
        print(f"VALIDATION FAILED: {err}", file=sys.stderr)
        sys.exit(1)

    by_diff = {d: [p for p in puzzles if p["difficulty"] == d] for d in DIFFICULTIES}

    # ── Chay 640 run ──────────────────────────────────────────────────────────
    print()
    print("=" * 68)
    print("  Running 640 benchmark experiments")
    print(f"  BT/MRV: {BT_RUNS_PER_PUZZLE} runs/puzzle x 40 puzzles = {BT_RUNS_PER_PUZZLE*40*2} runs")
    print(f"  MC    : {MC_SEEDS_PER_PUZZLE} seeds/puzzle x 40 puzzles = {MC_SEEDS_PER_PUZZLE*40} runs")
    print("=" * 68)

    all_rows = []
    total_runs = 0
    t_start = time.perf_counter()

    # ── Backtracking ──────────────────────────────────────────────────────────
    print("\n[1/3] Backtracking ...", flush=True)
    for diff in DIFFICULTIES:
        puzz_list = by_diff[diff]
        for p in puzz_list:
            for run_i in range(BT_RUNS_PER_PUZZLE):
                row = run_exact(p, "backtracking", run_i)
                all_rows.append(row)
                total_runs += 1
                status = "OK" if row["success"] else "FAIL"
                print(f"  [{diff[:2].upper()}] {p['id']} run={run_i} | "
                      f"{row['elapsed_ms']:8.2f} ms | "
                      f"nodes={row['nodes_explored']:>8,} | "
                      f"bt={row['backtracks']:>6,} | {status}", flush=True)

    # ── MRV ───────────────────────────────────────────────────────────────────
    print(f"\n[2/3] MRV ...", flush=True)
    for diff in DIFFICULTIES:
        puzz_list = by_diff[diff]
        for p in puzz_list:
            for run_i in range(BT_RUNS_PER_PUZZLE):
                row = run_exact(p, "mrv", run_i)
                all_rows.append(row)
                total_runs += 1
                status = "OK" if row["success"] else "FAIL"
                print(f"  [{diff[:2].upper()}] {p['id']} run={run_i} | "
                      f"{row['elapsed_ms']:8.2f} ms | "
                      f"nodes={row['nodes_explored']:>8,} | "
                      f"bt={row['backtracks']:>6,} | {status}", flush=True)

    # ── Min-Conflicts ─────────────────────────────────────────────────────────
    print(f"\n[3/3] Min-Conflicts (10 seeds x 40 puzzles) ...", flush=True)
    for diff in DIFFICULTIES:
        puzz_list = by_diff[diff]
        diff_ok = 0
        for p in puzz_list:
            for seed in MC_SEEDS:
                row = run_min_conflicts(p, seed)
                all_rows.append(row)
                total_runs += 1
                if row["success"]:
                    diff_ok += 1
                status = "OK" if row["success"] else "FAIL"
                print(f"  [{diff[:2].upper()}] {p['id']} seed={seed:2d} | "
                      f"{row['elapsed_ms']:8.2f} ms | "
                      f"iters={row['iterations']:>5,} | "
                      f"rest={row['restarts']:>3} | {status}", flush=True)
        diff_total = len(puzz_list) * MC_SEEDS_PER_PUZZLE
        print(f"  --> {diff.upper()}: {diff_ok}/{diff_total} success "
              f"({diff_ok/diff_total*100:.1f}%)", flush=True)

    t_elapsed = time.perf_counter() - t_start
    print(f"\nDone: {total_runs} runs in {t_elapsed:.1f}s "
          f"(avg {t_elapsed/total_runs*1000:.1f}ms/run)", flush=True)

    # ── Xuat CSV ──────────────────────────────────────────────────────────────
    print("\nExporting CSV files ...", flush=True)

    p_raw = RESULTS_DIR / "results_raw.csv"
    write_results_raw(all_rows, p_raw)
    print(f"  {p_raw.name}: {total_runs} rows", flush=True)

    p_sum = RESULTS_DIR / "results_summary.csv"
    write_results_summary(all_rows, p_sum)
    print(f"  {p_sum.name}", flush=True)

    p_he = RESULTS_DIR / "heuristic_effectiveness.csv"
    write_heuristic_effectiveness(all_rows, p_he)
    print(f"  {p_he.name}", flush=True)

    p_ls = RESULTS_DIR / "local_search_comparison.csv"
    write_local_search_comparison(all_rows, p_ls)
    print(f"  {p_ls.name}", flush=True)

    p_ct = RESULTS_DIR / "complexity_trend.csv"
    write_complexity_trend(all_rows, by_diff, p_ct)
    print(f"  {p_ct.name}", flush=True)

    # ── Ve bieu do ────────────────────────────────────────────────────────────
    print("\nGenerating charts ...", flush=True)
    make_charts(all_rows, CHARTS_DIR)

    # ── In terminal summary (con so bao cao) ──────────────────────────────────
    print_summary(all_rows)

    # ── Liet ke file da tao ───────────────────────────────────────────────────
    print("Files created:")
    for f in sorted(RESULTS_DIR.rglob("*")):
        if f.is_file():
            sz = f.stat().st_size
            print(f"  {f.relative_to(B_DIR)}  ({sz:,} bytes)")


if __name__ == "__main__":
    main()
