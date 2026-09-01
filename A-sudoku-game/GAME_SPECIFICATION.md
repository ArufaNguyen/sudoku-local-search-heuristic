# GAME_SPECIFICATION.md — Đặc Tả Game Sudoku (Program A)

> **Tác giả:** Thành viên A — Trương Lê Quốc Việt  
> **Dự án:** Bài tập lớn Trí tuệ Nhân tạo — Giải Sudoku bằng Local Search và Heuristic  
> **Module:** Program A — Sudoku Game & REST API Server (`http://127.0.0.1:8000`)

---

## 1. Mục Tiêu và Phạm Vi Hệ Thống

Program A là một ứng dụng độc lập chạy tại cổng `8000`, chịu trách nhiệm duy nhất về:

1. **Quản lý dữ liệu và trạng thái bàn cờ Sudoku 9×9:** Quản lý fixed mask, phát hiện xung đột (conflict detection), đếm ô trống và cập nhật trạng thái vòng đời trò chơi.
2. **Bảo vệ tính toàn vẹn của bài toán (Fixed Cell Integrity):** Ngăn chặn mọi hành vi thay đổi hoặc xóa các ô đề bài ban đầu (fixed cells).
3. **Cung cấp REST API v1:** Cho phép Program B (Auto Solver / Visualizer) điều khiển bàn cờ hoàn toàn thông qua giao thức HTTP JSON.
4. **Giao diện Web tương tác (Frontend):** Hiển thị trực quan bàn cờ thời gian thực, hỗ trợ người chơi tương tác thủ công và tự động đồng bộ khi Solver B thực hiện giải thuật.

> [!IMPORTANT]
> **Nguyên tắc phân định ranh giới:** Program A **không** chứa bất kỳ thuật toán giải (solver) nào và **không** lưu trữ hay trả về lời giải (solution) qua API. Lời giải được tìm kiếm động bởi Program B và truyền từng bước sang A qua REST API.

---

## 2. Kiến Trúc 3 Lớp (3-Tier Architecture)

Program A được thiết kế phân tách 3 lớp rõ ràng nhằm tối ưu hóa tính độc lập và khả năng kiểm thử:

```
┌───────────────────────────────────────────────────────────────────┐
│                          PROGRAM A (:8000)                        │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  Lớp 3 — Frontend UI Engine (static/)                       │  │
│  │  index.html + style.css + app.js                            │  │
│  │  - Render lưới Sudoku 9×9 phân tách rõ các khối 3×3         │  │
│  │  - Nhận thao tác người chơi (nhập số, xóa số, đổi độ khó)   │  │
│  │  - Polling trạng thái định kỳ 350ms qua REST API            │  │
│  │  - Kỹ thuật DOM Diffing chống mất focus / trỏ chuột         │  │
│  └──────────────────────────────┬──────────────────────────────┘  │
│                                 │ HTTP Request (Same-Origin)      │
│  ┌──────────────────────────────▼──────────────────────────────┐  │
│  │  Lớp 2 — HTTP Adapter (app.py)                              │  │
│  │  ThreadingHTTPServer + SudokuHandler                        │  │
│  │  - Định tuyến các endpoint REST /api/v1/*                   │  │
│  │  - Parse JSON request body & Serialize JSON response        │  │
│  │  - Thiết lập header CORS cho phép Program B (:8001) gọi     │  │
│  │  - Bắt lỗi domain và chuẩn hóa HTTP status code             │  │
│  └──────────────────────────────┬──────────────────────────────┘  │
│                                 │ Python Internal Method Calls    │
│  ┌──────────────────────────────▼──────────────────────────────┐  │
│  │  Lớp 1 — Domain Logic Engine (game.py)                      │  │
│  │  SudokuGame + GameError + validation + conflict detection   │  │
│  │  - Quản lý ma trận board 9×9 và fixed mask boolean          │  │
│  │  - Bảo vệ đa luồng an toàn bằng threading.RLock             │  │
│  │  - Xác định trạng thái PLAYING / CONFLICT / SOLVED          │  │
│  └─────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────┘
                                  ▲
                                  │ REST API v1 (HTTP JSON)
                                  │
                  ┌───────────────────────────────┐
                  │       PROGRAM B (:8001)       │
                  │   Auto Solver & Visualizer    │
                  └───────────────────────────────┘
```

---

## 3. Quy Tắc Trạng Thái và Dữ Liệu Bàn Cờ

### 3.1. Kích thước Ma trận và Miền Giá trị
- Bàn cờ luôn là ma trận vuông **9 × 9** (gồm 81 ô).
- Mỗi ô chứa một số nguyên (`int`) trong tập $\{0, 1, 2, 3, 4, 5, 6, 7, 8, 9\}$:
  - `0`: Đại diện cho **ô trống** (empty cell).
  - `1..9`: Đại diện cho **giá trị đã điền**.
- Mọi kiểu dữ liệu khác (`float`, `str`, `bool`, `None`, số ngoài $0..9$) đều bị từ chối với mã lỗi `INVALID_BOARD` hoặc `INVALID_VALUE`.

### 3.2. Quy tắc Bảo vệ Ô Đề Bài (Fixed Cells Protection)
- Khi một puzzle được khởi tạo hoặc nạp mới qua `load()`, Program A xây dựng ma trận boolean **fixed mask** 9×9.
- `fixed[r][c] = True` khi và chỉ khi `initial_board[r][c] != 0`.
- **Tính bất biến:** Mọi thao tác ghi đè (`move`), xóa (`clear`) hoặc thay thế snapshot (`replace`) tác động lên ô có `fixed[r][c] == True` đều bị chặn tuyệt đối và trả về mã lỗi `FIXED_CELL` (HTTP 400).
- Fixed mask chỉ được tạo lại khi nạp một đề bài mới qua `POST /game/load` hoặc `POST /game/new`.

### 3.3. Cơ chế Chấp Nhận Xung Đột (Conflict Acceptance cho Local Search)
- Trong Sudoku truyền thống, nước đi gây trùng lặp bị cấm. Tuy nhiên, để hỗ trợ thuật toán **Local Search (Min-Conflicts)** của Program B:
  - Program A **chấp nhận các nước đi gây xung đột** tại các ô editable.
  - Khi điền một số $v \in [1..9]$ vào ô $(r, c)$ trùng lặp với hàng, cột hoặc khối 3×3, nước đi vẫn được thực hiện thành công (HTTP 200) và giá trị được ghi nhận vào bàn cờ.
  - Hệ thống cập nhật danh sách tọa độ `conflicts` và chuyển trạng thái game sang `CONFLICT`.
- **Lý do kỹ thuật:** Thuật toán Min-Conflicts khởi tạo trạng thái đầy đủ có xung đột, sau đó liên tục hoán đổi vị trí để giảm dần xung đột. Nếu Program A từ chối move xung đột, Solver B sẽ không thể biểu diễn các bước chuyển trạng thái trung gian.

### 3.4. Định nghĩa 3 Trạng thái Vòng Đời Game (`GameStatus`)

Sau mỗi hành động thay đổi dữ liệu bàn cờ, trạng thái được tính toán theo quy trình ưu tiên:

| Trạng thái | Điều kiện xác định | Ý nghĩa |
|---|---|---|
| `CONFLICT` | $\text{len}(conflicts) > 0$ | Bàn cờ đang có ít nhất một cặp ô trùng lặp giá trị trên cùng hàng, cột hoặc khối 3×3. *(Được ưu tiên kiểm tra trước)* |
| `SOLVED` | $\text{len}(conflicts) == 0$ **và** $\text{empty\_cells} == 0$ | Bàn cờ đã điền kín toàn bộ 81 ô và hoàn toàn hợp lệ theo luật Sudoku. |
| `PLAYING` | $\text{len}(conflicts) == 0$ **và** $\text{empty\_cells} > 0$ | Bàn cờ chưa điền đầy nhưng các ô đã điền không vi phạm bất kỳ ràng buộc nào. |

```
                       [Thực hiện Action]
                               │
                               ▼
                    Quét 27 nhóm ràng buộc
                     (find_conflicts(board))
                               │
                      Có xung đột không?
                     ┌─────────┴─────────┐
                   Có                  Không
                     │                   │
                     ▼                   ▼
             Trạng thái:          Số ô trống == 0?
             "CONFLICT"          ┌───────┴───────┐
                                Đúng            Sai
                                 │               │
                                 ▼               ▼
                            Trạng thái:     Trạng thái:
                             "SOLVED"        "PLAYING"
```

---

## 4. Thuật Toán Phát Hiện Xung Đột (`find_conflicts`)

Hệ thống quét đồng thời **27 nhóm ràng buộc** của bàn cờ Sudoku:
1. **9 Hàng:** $\text{Row}_r = \{(r, c) \mid c \in [0..8]\}, \quad \forall r \in [0..8]$
2. **9 Cột:** $\text{Col}_c = \{(r, c) \mid r \in [0..8]\}, \quad \forall c \in [0..8]$
3. **9 Khối 3×3:** $\text{Block}_k = \{(r, c) \mid r \in [3i..3i+2], c \in [3j..3j+2]\}, \quad k = 3i+j, \; i, j \in [0..2]$

**Quy trình thuật toán:**
- Với mỗi nhóm trong 27 nhóm, nhóm các tọa độ có cùng giá trị $v \neq 0$.
- Nếu giá trị $v$ xuất hiện $\ge 2$ lần trong cùng một nhóm, toàn bộ các tọa độ chứa $v$ trong nhóm đó được thêm vào tập hợp `conflict_cells`.
- Kết quả trả về danh sách tọa độ duy nhất `[{"x": row, "y": col}, ...]`, được sắp xếp tăng dần theo `(x, y)`.

---

## 5. Danh Mục Phương Thức Domain (`SudokuGame`)

| Phương thức | Tham số | Kết quả trả về | Mô tả nghiệp vụ |
|---|---|---|---|
| `state()` | Không | `dict` (Full State) | Lấy toàn bộ thông tin bàn cờ, fixed mask, fixed, conflicts, status, metadata. |
| `status()` | Không | `dict` (Summary) | Lấy thông tin rút gọn: status, empty_cells, conflict_count. |
| `move(x, y, num)` | `x, y, num: int` | `dict` | Gán giá trị `num` vào ô editable $(x, y)$. Chấp nhận conflict. |
| `clear(x, y)` | `x, y: int` | `dict` | Xóa ô $(x, y)$ về giá trị `0`. Chặn ô fixed. |
| `reset()` | Không | `dict` (Full State) | Khôi phục toàn bộ editable cells về `0`, giữ nguyên fixed cells. |
| `load(test_id, difficulty, board)` | `test_id, difficulty: str`, `board: list` | `dict` (Full State) | Nạp puzzle mới, tính lại fixed mask, sinh `game_id` UUID mới. |
| `replace(board)` | `board: list[list[int]]` | `dict` (Full State) | Đồng bộ toàn bộ phần editable từ snapshot của Solver B. |

---

## 6. Hướng Dẫn Khởi Chạy & Kiểm Thử

### 6.1. Yêu cầu Môi trường
- **Python Version:** Python 3.9 trở lên.
- **Thư viện phụ thuộc:** 100% Python Standard Library (`http.server`, `json`, `urllib`, `threading`, `copy`, `uuid`). Không cần cài thêm bất kỳ package bên ngoài nào.

### 6.2. Lệnh khởi chạy

```powershell
# Chạy trực tiếp từ thư mục gốc dự án:
python A-sudoku-game/app.py

# Hoặc chạy thông qua Launcher tự động:
python A-sudoku-game/START_A.py
```

### 6.3. Điểm truy cập
- **Giao diện Web:** `http://127.0.0.1:8000`
- **REST API v1 Base URL:** `http://127.0.0.1:8000/api/v1`
- **Health Check Endpoint:** `http://127.0.0.1:8000/api/v1/health`
