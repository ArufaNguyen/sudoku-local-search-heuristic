"""Generate and insert the Program A/B architecture figure into the report."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


def box(ax, x, y, width, height, title, detail, face, edge="#29465B"):
    patch = FancyBboxPatch(
        (x, y), width, height,
        boxstyle="round,pad=0.018,rounding_size=0.025",
        linewidth=1.6, edgecolor=edge, facecolor=face,
    )
    ax.add_patch(patch)
    ax.text(x + width / 2, y + height * 0.64, title, ha="center", va="center",
            fontsize=12.5, fontweight="bold", color="#17324D")
    ax.text(x + width / 2, y + height * 0.30, detail, ha="center", va="center",
            fontsize=9.2, color="#263746", linespacing=1.25)


def arrow(ax, start, end, color="#385A6B", label=None, label_offset=(0, 0)):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=15,
                                linewidth=1.7, color=color, shrinkA=4, shrinkB=4))
    if label:
        mx = (start[0] + end[0]) / 2 + label_offset[0]
        my = (start[1] + end[1]) / 2 + label_offset[1]
        ax.text(mx, my, label, ha="center", va="center", fontsize=9,
                color=color, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.18", facecolor="white", edgecolor="none", alpha=0.92))


def create_figure(output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(13.2, 6.2), dpi=220)
    fig.patch.set_facecolor("white")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.5, 0.955, "KIẾN TRÚC HAI CHƯƠNG TRÌNH SUDOKU ĐỘC LẬP",
            ha="center", va="center", fontsize=16, fontweight="bold", color="#17324D")

    # Program A lane
    ax.add_patch(FancyBboxPatch((0.035, 0.53), 0.93, 0.34,
                               boxstyle="round,pad=0.012,rounding_size=0.02",
                               facecolor="#F5F9FC", edgecolor="#7DA2B8", linewidth=1.2))
    ax.text(0.055, 0.835, "PROGRAM A · CỔNG 8000", fontsize=10.5,
            fontweight="bold", color="#2A607A", va="center")
    box(ax, 0.075, 0.61, 0.18, 0.16, "Browser A", "Sudoku UI\nPolling trạng thái", "#E8F3FA")
    box(ax, 0.39, 0.61, 0.22, 0.16, "Game State A", "SudokuGame + RLock\nmove / clear / replace", "#DDEFF8")
    box(ax, 0.745, 0.61, 0.18, 0.16, "REST API v1", "10 endpoint\n/api/v1", "#CFE8F5")
    arrow(ax, (0.255, 0.69), (0.39, 0.69), label="HTTP / polling", label_offset=(0, 0.045))
    arrow(ax, (0.61, 0.69), (0.745, 0.69), label="adapter", label_offset=(0, 0.045))

    # Program B lane
    ax.add_patch(FancyBboxPatch((0.035, 0.10), 0.93, 0.34,
                               boxstyle="round,pad=0.012,rounding_size=0.02",
                               facecolor="#F7FBF5", edgecolor="#84A97A", linewidth=1.2))
    ax.text(0.055, 0.405, "PROGRAM B · CỔNG 8001", fontsize=10.5,
            fontweight="bold", color="#47733C", va="center")
    box(ax, 0.075, 0.18, 0.18, 0.16, "Browser B", "Start / Pause\nPrevious / Next", "#EDF7E9", edge="#587B50")
    box(ax, 0.36, 0.18, 0.25, 0.16, "Solver & Auto Worker", "Backtracking · MRV\nMin-Conflicts · Tick", "#E2F2DC", edge="#587B50")
    box(ax, 0.745, 0.18, 0.18, 0.16, "GameClient B", "REST client duy nhất\nkết nối sang A", "#D6EDCE", edge="#587B50")
    arrow(ax, (0.255, 0.26), (0.36, 0.26), color="#587B50", label="điều khiển", label_offset=(0, 0.045))
    arrow(ax, (0.61, 0.26), (0.745, 0.26), color="#587B50", label="action / state", label_offset=(0, 0.045))

    # Cross-process REST boundary.
    ax.add_patch(FancyArrowPatch((0.835, 0.34), (0.835, 0.61), arrowstyle="<|-|>",
                                mutation_scale=15, linewidth=2.2, color="#C36A2D",
                                shrinkA=2, shrinkB=2))
    ax.text(0.86, 0.475, "HTTP REST\n127.0.0.1:8000/api/v1", ha="left", va="center",
            fontsize=9.2, fontweight="bold", color="#A14E1C")
    ax.text(0.5, 0.035, "Ranh giới bắt buộc: Program B không import game.py và không đọc nghiệm của Program A",
            ha="center", va="center", fontsize=9.5, fontstyle="italic", color="#4D5961")

    fig.savefig(output, bbox_inches="tight", pad_inches=0.12, facecolor="white")
    plt.close(fig)


def main() -> None:
    output = Path(__file__).resolve().parent / "images" / "hinh_2_1_kien_truc_ab.png"
    create_figure(output)
    print(output)


if __name__ == "__main__":
    main()
