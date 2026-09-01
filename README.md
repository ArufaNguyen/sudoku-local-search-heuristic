# BÀI TẬP LỚN TRÍ TUỆ NHÂN TẠO 2026 — SUDOKU AI PROJECT

> **Chủ đề:** Giải Sudoku bằng Local Search và Heuristic

---

## 1. Hướng Dẫn Khởi Chạy Nhanh

### 1.1. Khởi chạy toàn bộ hệ thống (A + B)

Tự động khởi động cả 2 server và mở 2 tab trình duyệt cho Game A và Solver B:

```powershell
python A-sudoku-game/START_ALL.py
```

### 1.2. Khởi chạy riêng từng chương trình

```powershell
# Terminal 1 — Khởi chạy Program A (Sudoku Game & REST API Server :8000)
python A-sudoku-game/START_A.py

# Terminal 2 — Khởi chạy Program B (AI Auto Solver & Visualizer :8001)
python A-sudoku-game/START_B.py
```

### 1.3. Khởi chạy trực tiếp (Không qua launcher)

```powershell
# Terminal 1:
python A-sudoku-game/app.py

# Terminal 2:
python B-auto-solver/app.py
```

---

## 2. Điểm Truy Cập Dịch Vụ (Endpoints & URLs)

| Dịch vụ                            | URL Truy Cập                    | Chức năng chính                                                                  |
| ------------------------------------ | -------------------------------- | ----------------------------------------------------------------------------------- |
| **Program A — Game UI**       | `http://127.0.0.1:8000`        | Bàn cờ Sudoku người chơi, đổi độ khó, hiển thị move AI thời gian thực |
| **Program A — REST API**      | `http://127.0.0.1:8000/api/v1` | Cung cấp 8 API endpoints điều khiển bàn cờ theo chuẩn JSON                   |
| **Program B — AI Visualizer** | `http://127.0.0.1:8001`        | Điều khiển giải: Prepare, Next, Previous, Auto Run, Pause, Reset                |

---

## 3. Bản Đồ Tài Liệu & Đặc Tả Kỹ Thuật (Documentation Sitemap)

Tất cả các tài liệu kỹ thuật đã được biên soạn và cập nhật đầy đủ theo yêu cầu của [`TASK.md`](<file:///d:/Documents/Visual%20Code/BTL%20Tri%20tue%20nhan%20tao/TASK.md>) và [`TASK_DETAIL.md`](<file:///d:/Documents/Visual%20Code/BTL%20Tri%20tue%20nhan%20tao/TASK_DETAIL.md>):

### Phân hệ Program A (`A-sudoku-game/`)

- [`GAME_SPECIFICATION.md`](<file:///d:/Documents/Visual%20Code/BTL%20Tri%20tue%20nhan%20tao/A-sudoku-game/GAME_SPECIFICATION.md>): Đặc tả luật chơi, kiến trúc 3 lớp, quy tắc ô fixed và cơ chế chấp nhận conflict cho Local Search.
- [`API_SPECIFICATION.md`](<file:///d:/Documents/Visual%20Code/BTL%20Tri%20tue%20nhan%20tao/A-sudoku-game/API_SPECIFICATION.md>): Đặc tả chi tiết 8 REST API endpoints v1, quy ước tọa độ, cấu trúc JSON và danh mục mã lỗi.
- [`TECHNICAL_REPORT.md`](<file:///d:/Documents/Visual%20Code/BTL%20Tri%20tue%20nhan%20tao/A-sudoku-game/TECHNICAL_REPORT.md>): Báo cáo kỹ thuật tổng hợp về an toàn đa luồng (`threading.RLock`), động cơ polling 350ms với DOM diffing, và kết quả kiểm thử.

### Phân hệ Program B (`B-auto-solver/`)

- [`SPECIFICATION.md`](<file:///d:/Documents/Visual%20Code/BTL%20Tri%20tue%20nhan%20tao/B-auto-solver/SPECIFICATION.md>): Đặc tả 3 thuật toán (Backtracking, MRV, Min-Conflicts), thiết kế hệ thống Tick, và backend `AutoRunner` thread.
- [`TEST_PLAN.md`](<file:///d:/Documents/Visual%20Code/BTL%20Tri%20tue%20nhan%20tao/B-auto-solver/TEST_PLAN.md>): Kế hoạch và ma trận kiểm thử tự động cho domain, thuật toán, client và dataset.
- [`COMPLEXITY_ANALYSIS.md`](<file:///d:/Documents/Visual%20Code/BTL%20Tri%20tue%20nhan%20tao/B-auto-solver/COMPLEXITY_ANALYSIS.md>): Phân tích độ phức tạp lý thuyết vs thực nghiệm, hiện tượng điểm giao thoa (crossover point) và tính không đầy đủ của Local Search.
- [`BENCHMARK_SUMMARY.md`](<file:///d:/Documents/Visual%20Code/BTL%20Tri%20tue%20nhan%20tao/B-auto-solver/BENCHMARK_SUMMARY.md>): Bảng tổng hợp kết quả 640 lượt chạy benchmark, mức giảm 99.53% node của MRV và danh mục biểu đồ phân tích.

---

## 4. Kiểm Thử và Thực Nghiệm (Testing & Benchmark)

### 4.1. Chạy toàn bộ Unit Tests tự động (67 Tests)

```powershell
python -m unittest discover -s tests -v
```

### 4.2. Chạy HTTP Smoke Tests kiểm tra API (43 Tests)

```powershell
python A-sudoku-game/test_api.py
```

### 4.3. Chạy Pipeline Benchmark 640 lượt

```powershell
python B-auto-solver/benchmark.py
```

---

## 5. Cấu Trúc Thư Mục Dự Án

```
├── A-sudoku-game/
│   ├── app.py                   # HTTP Server + REST API v1 Adapter
│   ├── game.py                  # Domain Logic Engine (Board, Fixed, Conflicts, RLock)
│   ├── static/                  # Frontend UI (index.html, style.css, app.js)
│   ├── START_A.py               # Launcher khởi động Program A
│   ├── START_B.py               # Launcher khởi động Program B
│   ├── START_ALL.py             # Launcher khởi động đồng thời A + B
│   ├── test_api.py              # Suite 43 HTTP Smoke Tests
│   ├── GAME_SPECIFICATION.md    # Đặc tả luật game & vòng đời trạng thái
│   ├── API_SPECIFICATION.md     # Đặc tả 8 REST API v1 endpoints
│   └── TECHNICAL_REPORT.md      # Báo cáo kỹ thuật phân hệ A
│
├── B-auto-solver/
│   ├── app.py                   # BApp State Machine + AutoRunner Thread
│   ├── solvers.py               # Thuật toán BT, MRV, Min-Conflicts + Tick Recorder
│   ├── client.py                # GameClient REST client giao tiếp với A
│   ├── benchmark.py             # Pipeline 640-run benchmark & xuất dữ liệu
│   ├── dataset/
│   │   └── puzzles.json         # 40 bài toán chuẩn (10 bài x 4 mức độ khó)
│   ├── results/
│   │   ├── results_raw.csv      # Dữ liệu thô 640 lượt chạy
│   │   ├── results_summary.csv  # Bảng tổng hợp các chỉ số hiệu năng
│   │   ├── heuristic_effectiveness.csv
│   │   ├── local_search_comparison.csv
│   │   ├── complexity_trend.csv
│   │   └── charts/              # 3 biểu đồ PNG phân tích thuật toán
│   ├── SPECIFICATION.md         # Đặc tả phân hệ B & Tick Engine
│   ├── TEST_PLAN.md             # Kế hoạch & ma trận kiểm thử
│   ├── COMPLEXITY_ANALYSIS.md   # Phân tích độ phức tạp lý thuyết & thực nghiệm
│   └── BENCHMARK_SUMMARY.md     # Tóm tắt kết quả thực nghiệm benchmark
│
├── tests/
│   ├── test_game.py             # 67 Unit Tests tự động
│   └── run_demo.py              # Script demo tích hợp
│
├── TASK.md                      # Phân công nhiệm vụ & Mốc thời gian
├── TASK_DETAIL.md               # Hướng dẫn kỹ thuật chi tiết A–F
└── README.md                    # Hướng dẫn tổng quan & Bản đồ dự án
```

---

## 6. Yêu Cầu Môi Trường

- **Python:** Phiên bản **3.9** trở lên.
- **Thư viện phụ thuộc:** **100% Python Standard Library** — Hoàn toàn không cần cài đặt thêm bất kỳ thư viện ngoài (pip package) nào.
