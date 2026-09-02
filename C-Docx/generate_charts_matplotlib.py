"""Sinh ba biểu đồ dùng trong báo cáo Task C từ kết quả benchmark của B.

Chạy từ thư mục gốc project:
    python C-Docx/generate_charts_matplotlib.py

Ảnh được ghi vào C-Docx/charts/. Script chỉ đọc CSV kết quả do Program B
cung cấp và không phụ thuộc đường dẫn tuyệt đối trên máy.
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SUMMARY_CSV = PROJECT_ROOT / "B-auto-solver" / "results" / "results_summary.csv"
CHARTS_DIR = Path(__file__).resolve().parent / "charts"

DIFFICULTIES = ["easy", "medium", "hard", "expert"]
DISPLAY_NAMES = ["Easy", "Medium", "Hard", "Expert"]
ALGORITHMS = ["backtracking", "mrv", "min_conflicts"]
LABELS = {
    "backtracking": "Backtracking",
    "mrv": "MRV",
    "min_conflicts": "Min-Conflicts",
}
COLORS = {
    "backtracking": "#C43D3D",
    "mrv": "#2E8B57",
    "min_conflicts": "#2F6BBD",
}


def load_summary() -> dict[tuple[str, str], dict[str, float]]:
    """Đọc đủ 12 nhóm độ khó - thuật toán từ results_summary.csv."""
    data: dict[tuple[str, str], dict[str, float]] = {}
    with SUMMARY_CSV.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            key = (row["difficulty"], row["algorithm"])
            data[key] = {
                column: float(value)
                for column, value in row.items()
                if column not in {"difficulty", "algorithm"}
            }

    expected = {
        (difficulty, algorithm)
        for difficulty in DIFFICULTIES
        for algorithm in ALGORITHMS
    }
    if set(data) != expected:
        raise RuntimeError(
            f"CSV phải có đúng 12 nhóm độ khó - thuật toán; nhận được {len(data)}."
        )
    return data


def create_axes(title: str, ylabel: str):
    """Tạo khung biểu đồ thống nhất với phong cách của báo cáo."""
    figure, axes = plt.subplots(figsize=(7.5, 4), dpi=120)
    figure.patch.set_facecolor("white")
    axes.set_facecolor("#FAFBFC")
    axes.set_title(title, fontsize=13, fontweight="bold", pad=12)
    axes.set_ylabel(ylabel, fontsize=10)
    axes.spines[["top", "right"]].set_visible(False)
    axes.grid(axis="y", color="#D8DDE3", linewidth=0.8, alpha=0.8)
    axes.set_axisbelow(True)
    return figure, axes


def save_chart(figure, filename: str) -> None:
    figure.tight_layout(pad=1.1)
    figure.savefig(
        CHARTS_DIR / filename,
        dpi=120,
        facecolor="white",
        bbox_inches=None,
    )
    plt.close(figure)


def draw_runtime_chart(data) -> None:
    """Hình 3.1: thời gian chạy trung bình theo độ khó."""
    figure, axes = create_axes(
        "Thời gian chạy trung bình theo độ khó",
        "Thời gian trung bình (ms, thang log)",
    )
    x_positions = list(range(len(DIFFICULTIES)))
    width = 0.24

    for algorithm_index, algorithm in enumerate(ALGORITHMS):
        values = [data[(difficulty, algorithm)]["mean_ms"] for difficulty in DIFFICULTIES]
        positions = [x + (algorithm_index - 1) * width for x in x_positions]
        bars = axes.bar(
            positions,
            values,
            width,
            label=LABELS[algorithm],
            color=COLORS[algorithm],
            edgecolor="white",
            linewidth=0.6,
        )
        for bar, value in zip(bars, values):
            label = f"{value:,.1f}" if value >= 10 else f"{value:.2f}"
            axes.annotate(
                label,
                (bar.get_x() + bar.get_width() / 2, value),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=7,
            )

    axes.set_yscale("log")
    axes.set_xticks(x_positions, DISPLAY_NAMES)
    axes.set_xlabel("Mức độ khó", fontsize=10)
    axes.legend(frameon=False, ncol=3, loc="upper left", fontsize=8)
    save_chart(figure, "runtime_by_difficulty.png")


def draw_nodes_chart(data) -> None:
    """Hình 3.2: số node của Backtracking và MRV."""
    figure, axes = create_axes(
        "Không gian tìm kiếm: Backtracking và MRV",
        "Số node trung bình (thang log)",
    )
    x_positions = list(range(len(DIFFICULTIES)))
    width = 0.34

    for algorithm_index, algorithm in enumerate(["backtracking", "mrv"]):
        values = [
            data[(difficulty, algorithm)]["mean_nodes"]
            for difficulty in DIFFICULTIES
        ]
        positions = [x + (algorithm_index - 0.5) * width for x in x_positions]
        bars = axes.bar(
            positions,
            values,
            width,
            label=LABELS[algorithm],
            color=COLORS[algorithm],
            edgecolor="white",
            linewidth=0.6,
        )
        for bar, value in zip(bars, values):
            axes.annotate(
                f"{value:,.1f}",
                (bar.get_x() + bar.get_width() / 2, value),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=7,
            )

    axes.set_yscale("log")
    axes.set_xticks(x_positions, DISPLAY_NAMES)
    axes.set_xlabel("Mức độ khó", fontsize=10)
    axes.legend(frameon=False, ncol=2, loc="upper left", fontsize=8)
    save_chart(figure, "heuristic_nodes.png")


def draw_success_rate_chart(data) -> None:
    """Hình 3.3: tỷ lệ thành công của Min-Conflicts."""
    figure, axes = create_axes(
        "Tỷ lệ thành công của Min-Conflicts",
        "Tỷ lệ thành công (%)",
    )
    values = [
        data[(difficulty, "min_conflicts")]["success_rate"] * 100
        for difficulty in DIFFICULTIES
    ]
    bars = axes.bar(
        DISPLAY_NAMES,
        values,
        width=0.58,
        color=["#2E8B57" if value == 100 else "#E39C25" for value in values],
        edgecolor="white",
        linewidth=0.7,
    )
    for bar, value in zip(bars, values):
        axes.text(
            bar.get_x() + bar.get_width() / 2,
            value + 1.2,
            f"{value:.0f}%",
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="bold",
        )

    axes.set_ylim(0, 108)
    axes.set_xlabel("Mức độ khó", fontsize=10)
    save_chart(figure, "local_search_success_rate.png")


def main() -> None:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.labelcolor": "#263238",
            "xtick.color": "#37474F",
            "ytick.color": "#37474F",
            "text.color": "#263238",
        }
    )
    data = load_summary()
    draw_runtime_chart(data)
    draw_nodes_chart(data)
    draw_success_rate_chart(data)
    print(f"Generated 3 charts from {SUMMARY_CSV.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
