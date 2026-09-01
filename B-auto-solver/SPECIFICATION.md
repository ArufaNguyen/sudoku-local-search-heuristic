# SPECIFICATION.md — Program B: Auto Solver / Algorithm Visualizer

> **Tác giả:** Thành viên B — Đào Quốc Thanh  
> **Dự án:** Bài tập lớn Trí tuệ Nhân tạo — Giải Sudoku bằng Local Search và Heuristic  
> **Module:** Program B — AI Auto Solver & Visualizer (`http://127.0.0.1:8001`)

---

## 1. Tổng Quan Hệ Thống

Program B là module **giải và trực quan hoá** thuật toán Sudoku, chạy độc lập tại cổng `8001`. Program B không lưu trữ trạng thái cố định của bàn cờ — B **đọc trạng thái từ Program A** qua REST API, thực hiện giải bằng các thuật toán AI cục bộ, sau đó **đồng bộ từng bước hoặc snapshot** ngược lại sang A.

```
┌─────────────────────────────────────────────────────────┐
│                   Program B (port 8001)                 │
│                                                         │
│  ┌──────────────┐   ┌──────────────┐                    │
│  │  solvers.py  │   │    app.py    │◄──── HTTP Polling  │
│  │ (BT/MRV/MC)  │──►│ (State Mach) │      (400ms UI)    │
│  └──────────────┘   └──────┬───────┘                    │
│  ┌──────────────┐          │                            │
│  │  client.py   │◄─────────┘                            │
│  │ (GameClient) │  REST calls (move, clear, replace)    │
│  └──────┬───────┘                                       │
└─────────┼───────────────────────────────────────────────┘
          ▼
    Program A (port 8000) — Nguồn dữ liệu đề bài
```

---

## 2. Kiến Trúc và Trách Nhiệm Module

| File / Thư mục | Trách nhiệm chính |
|---|---|
| `solvers.py` | Cài đặt 3 thuật toán (Backtracking, MRV, Min-Conflicts) + Tick Recorder + Thu thập Metrics |
| `client.py` | `GameClient` — Boundary giao tiếp REST API v1 với Program A |
| `app.py` | `BApp` State Machine + `AutoRunner` backend worker thread + HTTP Server (:8001) |
| `static/` | Frontend Visualizer (HTML/CSS/JS) — Điều khiển Next, Previous, Auto, Pause, Reset |
| `dataset/` | Chứa `puzzles.json` (40 puzzle chuẩn, 10 puzzle cho mỗi mức độ khó) |
| `benchmark.py` | Pipeline thực nghiệm 640 lượt chạy + Xuất 5 file CSV + Sinh 3 biểu đồ PNG |
| `results/` | Lưu trữ dữ liệu thô (`results_raw.csv`), bảng tổng hợp và biểu đồ phân tích |

---

## 3. Đặc Tả Ba Thuật Toán Giải Sudoku

### 3.1. Thuật toán 1: Backtracking (Exact Search — Baseline)

- **Nguyên lý:** Tìm kiếm theo chiều sâu (Depth-First Search - DFS) đệ quy. Duyệt tìm ô trống đầu tiên theo thứ tự quét hàng-cột (row-major order), dùng `candidates()` để lọc các giá trị hợp lệ $1..9$, thử từng giá trị và quay lui (backtrack) khi gặp ngõ cụt.
- **Điều kiện dừng an toàn:** `max_nodes = 2,000,000` (ở chế độ benchmark) hoặc `100,000` (ở chế độ visualizer).
- **Phân loại Tick:**
  - `SELECT`: Chọn ô trống kế tiếp theo thứ tự quét hàng-cột.
  - `ASSIGN`: Gán giá trị hợp lệ vào ô trống. $\rightarrow$ Kèm `api_action: {"type": "move", "x": r, "y": c, "value": v}`.
  - `BACKTRACK`: Nhánh tìm kiếm thất bại, xóa giá trị ô về 0. $\rightarrow$ Kèm `api_action: {"type": "clear", "x": r, "y": c}`.
  - `SOLVED` / `FAILED`: Hoàn tất tìm kiếm.

### 3.2. Thuật toán 2: Backtracking kết hợp Heuristic MRV (Fail-First)

- **Nguyên lý:** Cùng cơ chế quay lui như Backtracking nhưng ở bước chọn biến (`SELECT`), thuật toán tính domain của tất cả các ô trống còn lại và chọn ô có **ít giá trị khả dĩ nhất (Minimum Remaining Values)**.
- **Tối ưu Fail-First:** Nếu phát hiện bất kỳ ô trống nào có số lượng candidates bằng 0, nhánh tìm kiếm được kết luận thất bại ngay lập tức mà không cần thử tiếp các nhánh con.
- **Đặc điểm thực nghiệm:** MRV tốn chi phí $O(N^2)$ để tính domain tại mỗi node. Vì vậy, ở các bài Easy/Medium, MRV có thể tốn nhiều thời gian hơn Backtracking thuần do overhead tính toán. Tuy nhiên, từ Hard đến Expert, **MRV vượt trội hoàn toàn**, cắt giảm tới **99.53% số node** cần duyệt.

### 3.3. Thuật toán 3: Local Search — Min-Conflicts (Heuristic Stochastic)

- **Nguyên lý:**
  1. **Khởi tạo (INITIALIZE):** Giữ nguyên các ô đề bài (`fixed`). Với mỗi hàng, điền hoán vị ngẫu nhiên của các chữ số còn thiếu $\rightarrow$ Đảm bảo **ràng buộc hàng luôn được thỏa mãn $100\%$ ngay từ đầu**.
  2. **Vòng lặp tối ưu cục bộ (Conflict Loop):**
     - Đếm xung đột trên các cột và khối 3×3.
     - Chọn ngẫu nhiên một ô editable đang có xung đột $(r, c_1)$.
     - Thử đổi chỗ $(r, c_1)$ với mọi ô editable khác $(r, c_2)$ cùng hàng $r$.
     - Chọn phép hoán đổi giúp giảm tổng xung đột toàn bàn cờ nhiều nhất (Min-Conflicts).
  3. **Khởi động lại ngẫu nhiên (Random Restart):** Khi lặp hết `max_iterations` mà chưa tìm thấy nghiệm, thuật toán khởi động lại từ một cấu hình ngẫu nhiên mới.
- **Phân loại Tick:**
  - `INITIALIZE` / `RESTART`: Trạng thái bàn cờ ban đầu hoặc sau khi restart. $\rightarrow$ Kèm `api_action: {"type": "replace", "board": snapshot}`.
  - `SELECT`: Chọn ô đang vi phạm xung đột.
  - `APPLY`: Áp dụng phép hoán đổi giá trị tối ưu. $\rightarrow$ Kèm `api_action: {"type": "replace", "board": snapshot}`.
  - `SOLVED` / `FAILED`: Đạt 0 xung đột hoặc cạn kiệt ngân sách tìm kiếm.

---

## 4. Thiết Kế Hệ Thống Tick (Tick Engine)

Mỗi Tick là một đơn vị trạng thái tại một bước thực thi của thuật toán, gồm các trường:

| Trường | Kiểu dữ liệu | Mô tả |
|---|---|---|
| `index` | `int` | Thứ tự bước (bắt đầu từ 0) |
| `algorithm` | `str` | `"backtracking"`, `"mrv"`, hoặc `"min_conflicts"` |
| `phase` | `str` | `SELECT`, `ASSIGN`, `BACKTRACK`, `INITIALIZE`, `APPLY`, `RESTART`, `SOLVED`, `FAILED` |
| `board` | `list[list[int]]` | Snapshot ma trận bàn cờ 9×9 sau khi thực hiện hành động |
| `cell` | `tuple[int, int]` | Tọa độ ô đang xét `(row, col)` |
| `value` | `int` | Giá trị đang gán hoặc hoán đổi |
| `candidates` | `list[int]` | Danh sách miền giá trị khả dĩ (dùng cho MRV) |
| `conflicts` | `int` | Tổng số xung đột hiện tại (dùng cho Min-Conflicts) |
| `depth` | `int` | Độ sâu đệ quy (BT/MRV) hoặc số lần Restart (MC) |
| `metrics` | `dict` | Snapshot các chỉ số: nodes_explored, backtracks, elapsed_ms, ... |
| `description` | `str` | Mô tả hành động bằng ngôn ngữ tự nhiên |
| `api_action` | `dict` | Lệnh đồng bộ gửi sang Program A (`move`, `clear`, hoặc `replace`) |

---

## 5. Kết Quả Giải Thuật (`SolveResult`)

Sau khi giải xong, hàm `solve()` trả về đối tượng `SolveResult` chứa:

| Trường | Kiểu | Mô tả |
|---|---|---|
| `algorithm` | `str` | Tên thuật toán |
| `success` | `bool` | `True` nếu giải thành công |
| `board` | `list[list[int]]` | Bàn cờ kết quả (hoặc `None` nếu thất bại) |
| `elapsed_ms` | `float` | Thời gian chạy (mili-giây) |
| `nodes_explored` | `int` | Tổng số node đã duyệt (BT / MRV) |
| `backtracks` | `int` | Tổng số lần quay lui (BT / MRV) |
| `max_depth` | `int` | Độ sâu đệ quy tối đa (BT / MRV) |
| `iterations` | `int` | Tổng số vòng lặp cục bộ (Min-Conflicts) |
| `restarts` | `int` | Tổng số lần khởi động lại (Min-Conflicts) |
| `moves` | `int` | Tổng số phép hoán đổi đã thực hiện (Min-Conflicts) |
| `ticks` | `list[Tick]` | Danh sách toàn bộ các tick ghi nhận |
| `stopped_reason` | `str` | `"solved"`, `"node_limit"`, `"no_solution"`, `"budget_exhausted"` |

---

## 6. Máy Trạng Thái `BApp` và Backend AutoRunner

### 6.1. Vòng đời Phiên làm việc (Session Lifecycle)

```
[Chưa có Session]
       │
       ▼ POST /api/prepare
[Session khởi tạo, index = -1]
       │
       ├──► POST /api/next      ──► index tăng 1, gửi api_action sang A
       ├──► POST /api/previous  ──► index giảm 1, đồng bộ snapshot sang A
       ├──► POST /api/auto/start──► Khởi động AutoRunner background thread
       ├──► POST /api/auto/pause──► Dừng AutoRunner, đóng băng index
       └──► POST /api/reset     ──► Xóa session, tùy chọn reset Program A
```

### 6.2. Thiết kế Luồng Chạy Nền `AutoRunner`

- `AutoRunner` được triển khai bằng một Python background thread (`threading.Thread` với cờ `daemon=True`).
- Thread gọi hàm `_advance_locked()` lặp lại theo chu kỳ $T = \frac{1}{\text{speed}}$ giây.
- Sử dụng `threading.Lock` dung hòa truy cập giữa `next`, `previous`, và `auto_start` để loại bỏ hoàn toàn race condition.
- **Pause an toàn:** Phương thức `pause()` kích hoạt `_stop_event.set()` và thực hiện `join(timeout=3)` dạng blocking join, bảo đảm index không bị nhảy sau khi trả về response.
- **Ưu điểm:** Auto Run hoàn toàn không phụ thuộc vào `setInterval` hay `setTimeout` của JavaScript, giúp quá trình giải **không bao giờ bị gián đoạn hay throttle khi người dùng chuyển sang tab khác**.

---

## 7. Danh Mục REST API của Program B

| Method | Endpoint | Request Body | Mô tả nghiệp vụ |
|---|---|---|---|
| `GET` | `/api/health` | Không | Kiểm tra Program B đang hoạt động (`{"status":"ok","program":"B"}`). |
| `GET` | `/api/session` | Không | Lấy trạng thái session hiện tại (dùng cho frontend polling). |
| `POST` | `/api/prepare` | `{"algorithm": str, ...}` | Đọc đề bài từ A, giải thuật toán, tạo session và danh sách tick. |
| `POST` | `/api/next` | Không | Tiến 1 tick, áp dụng `api_action` sang Program A. |
| `POST` | `/api/previous` | Không | Lùi 1 tick, khôi phục snapshot tương ứng sang Program A. |
| `POST` | `/api/auto/start` | `{"speed": float}` | Khởi động worker thread chạy tự động với tốc độ cấu hình. |
| `POST` | `/api/auto/pause` | Không | Dừng worker thread, giữ nguyên vị trí tick hiện tại. |
| `POST` | `/api/reset` | `{"reset_game": bool}` | Xóa session hiện tại, tùy chọn reset bàn cờ Program A. |
| `GET` | `/` | Không | Phục vụ trang giao diện `static/index.html`. |
| `GET` | `/static/<file>` | Không | Phục vụ các tài nguyên tĩnh CSS, JS. |

---

## 8. Hợp Đồng Giao Tiếp với Program A (`GameClient`)

Class `GameClient` trong `client.py` đóng gói toàn bộ các lời gọi HTTP sang Program A:

| Phương thức Client | Endpoint tương ứng ở Program A | Mô tả chức năng |
|---|---|---|
| `health()` | `GET /api/v1/health` | Kiểm tra kết nối Program A |
| `get_state()` | `GET /api/v1/game/state` | Đọc toàn bộ board, fixed mask và conflicts |
| `get_status()` | `GET /api/v1/game/status` | Đọc trạng thái rút gọn |
| `move(x, y, value)` | `POST /api/v1/game/move` | Gán giá trị vào ô editable (gửi cả `num` và `value`) |
| `clear(x, y)` | `POST /api/v1/game/clear` | Xóa ô editable về 0 khi backtrack |
| `replace(board)` | `PUT /api/v1/game/state` | Đồng bộ toàn bộ ma trận snapshot cho Min-Conflicts |
| `reset()` | `POST /api/v1/game/reset` | Khôi phục bàn cờ về đề bài gốc |
| `load(board, id, diff)` | `POST /api/v1/game/load` | Nạp puzzle mới vào Program A |

---

## 9. Bộ Dữ Liệu Thực Nghiệm (Dataset)

Dataset chính thức nằm tại `B-auto-solver/dataset/puzzles.json` gồm **40 bài toán**:

| Mức độ khó (Difficulty) | Số Clues cố định | Số ô trống ($m$) | Số lượng Puzzle | Đảm bảo nghiệm |
|---|:---:|:---:|:---:|:---:|
| **Easy** | 46 | 35 | 10 | Đúng 1 nghiệm duy nhất |
| **Medium** | 38 | 43 | 10 | Đúng 1 nghiệm duy nhất |
| **Hard** | 32 | 49 | 10 | Đúng 1 nghiệm duy nhất |
| **Expert** | 27 | 54 | 10 | Đúng 1 nghiệm duy nhất |

- Tất cả 40 puzzle đều được xác thực nghiệm duy nhất thông qua hàm `count_solutions(board, limit=2) == 1`.
