# Báo Cáo Kỹ Thuật (Technical Report) — Sudoku Game (Program A)

> **Tác giả:** Thành viên A — Trương Lê Quốc Việt  
> **Dự án:** Bài tập lớn Trí tuệ Nhân tạo — Giải Sudoku bằng Local Search và Heuristic  
> **Module:** Program A — Sudoku Game & REST API Server (`http://127.0.0.1:8000`)

---

## 1. Kiến Trúc Hệ Thống Tổng Thể (Architecture Overview)

### 1.1. Mô hình Hai Tiến trình Độc lập (Two-Process Decoupled Architecture)

Hệ thống được thiết kế phân tách hoàn toàn thành 2 tiến trình độc lập hoạt động song song trên nền tảng mạng cục bộ:

```
┌─────────────────────────────────────────────────────────┐
│                    PROGRAM A (:8000)                    │
│                 Sudoku Game & State Server              │
│                                                         │
│  - Quản lý Board 9×9, Fixed Mask & Conflicts            │
│  - Bảo vệ tính toàn vẹn của bài toán (Fixed Cell Rule)  │
│  - REST API Adapter v1 (ThreadingHTTPServer)            │
│  - Frontend Web UI (Glassmorphism Dark Theme)           │
│  - 350ms Polling Engine với DOM Diffing                 │
└───────────────────────────▲─────────────────────────────┘
                            │
                            │ HTTP/1.1 REST API v1 (JSON Payload)
                            │ GET  /api/v1/game/state
                            │ POST /api/v1/game/move
                            │ POST /api/v1/game/clear
                            │ POST /api/v1/game/reset
                            │ PUT  /api/v1/game/state
                            │
┌───────────────────────────▼─────────────────────────────┐
│                    PROGRAM B (:8001)                    │
│                Auto Solver & Visualizer                 │
│                                                         │
│  - Thuật toán Backtracking thuần (Trạng thái cơ sở)     │
│  - Thuật toán Heuristic MRV (Minimum Remaining Values)  │
│  - Thuật toán Local Search Min-Conflicts (Khởi tạo đầy) │
│  - Bộ đệm Tick Recorder & Tự động chạy nền (Auto Run)   │
│  - HTTP GameClient tương tác với Program A              │
└─────────────────────────────────────────────────────────┘
```

### 1.2. Nguyên tắc Ranh giới và Phân định Quyền hạn

1. **A là nguồn chân lý duy nhất về trạng thái (Single Source of Truth):**
   - Program A chịu trách nhiệm duy nhất về bàn cờ thực tế. Mọi thay đổi dữ liệu phải được thực hiện thông qua các mutation method có kiểm tra ràng buộc.
2. **Không phụ thuộc tầng mã nguồn (Zero Code-coupling):**
   - Program B không import `game.py`, không gọi hàm trực tiếp và không chia sẻ bộ nhớ với Program A. Mọi giao tiếp diễn ra qua HTTP request.
3. **Không lưu trước nghiệm (No Precomputed Solutions):**
   - Program A hoàn toàn không biết cách giải một bàn cờ Sudoku. Lời giải được tạo ra động bởi các thuật toán AI của Program B.
4. **Hỗ trợ tối đa cho Local Search:**
   - Để thuật toán Min-Conflicts có thể thử nghiệm các trạng thái trung gian, Program A chấp nhận các move có xung đột mà không raise exception, đồng thời chuyển trạng thái hệ thống thành `CONFLICT`.

---

## 2. Thiết Kế Tầng Domain & Cơ Chế An Toàn Đa Luồng

### 2.1. Cấu trúc Thực thể `SudokuGame`

`SudokuGame` là đối tượng trung tâm quản lý toàn bộ trạng thái game, gồm các thành phần:

| Thuộc tính | Kiểu | Mô tả |
|---|---|---|
| `initial_board` | `list[list[int]]` | Bản sao bất biến của đề bài ban đầu |
| `current_board` | `list[list[int]]` | Ma trận 9×9 đang chơi trong phiên |
| `fixed` | `list[list[bool]]` | Fixed mask (True = ô đề bài cố định) |
| `game_id` | `str` | UUID phiên chơi (ví dụ: `game-7f3b8a1c`) |
| `test_id` | `str` | Mã bài toán trong dataset (ví dụ: `medium_01`) |
| `difficulty` | `str` | Độ khó (`easy`, `medium`, `hard`, `expert`) |

### 2.2. Cơ chế An toàn Đa luồng (Thread-Safety)

Do server phục vụ mỗi HTTP request trên một thread riêng biệt, xung đột tài nguyên có thể xảy ra khi:
- Frontend A đang Polling định kỳ.
- Người chơi đang nhập số trên giao diện Web.
- Solver B đang gửi liên tục các bước giải với tốc độ cao.

**Giải pháp:** Sử dụng `threading.RLock` (Reentrant Lock) bao bọc mọi phương thức đọc/ghi dữ liệu. `RLock` cho phép cùng một luồng acquire khóa nhiều lần lồng nhau mà không bị deadlock.

---

## 3. Kiến Trúc Giao Diện & Cơ Chế Đồng Bộ Thời Gian Thực

### 3.1. Giao diện Web Người Dùng (Modern Glassmorphism UI)

Giao diện được xây dựng bằng HTML5 semantic, CSS Grid và Vanilla JavaScript:
- **Lưới CSS Grid 9×9:** Phân tách rõ ràng giữa các khối 3×3 bằng đường viền nổi bật.
- **Trực quan hóa 3 loại ô:** Ô đề bài (`fixed-cell`), ô người chơi/solver điền (`cell`), và ô xung đột (`bad`).
- **Hệ thống Status Badge:** Đổi màu động theo trạng thái (`PLAYING`, `CONFLICT`, `SOLVED`).
- **Chọn độ khó:** 4 mức Easy / Medium / Hard / Expert, tải ngẫu nhiên puzzle tương ứng từ dataset.

### 3.2. Động cơ Polling & Kỹ thuật DOM Diffing

Để giao diện A tự động phản ánh các bước giải của Solver B mà không làm gián đoạn người dùng:

```
[Interval 350ms] ──► Fetch GET /game/state
                        │
                stateKey = board_hash + status
                        │
                stateKey có thay đổi?
               ┌─────────┴─────────┐
              Có                  Không
               │                   │
               ▼                   ▼
        Cập nhật DOM         Bỏ qua Render
        (Vẽ lại Board)       (Giữ Focus/Con trỏ)
```

1. **DOM Diffing qua `stateKey`:** Tránh hủy và vẽ lại DOM mỗi 350ms khi bàn cờ không đổi. Điều này giúp người chơi không bao giờ bị mất dấu con trỏ chuột hoặc mất focus khi đang nhập số.
2. **Generation Counter chống Race Condition mạng:** Mỗi chu kỳ Polling tăng biến thế hệ `pollGeneration`. Khi response trả về, hệ thống kiểm tra nếu thế hệ response đã cũ hơn thế hệ hiện tại thì bỏ qua, tránh tình trạng response cũ ghi đè dữ liệu mới.

---

## 4. Hướng Dẫn Tích Hợp với Program B (`GameClient`)

Khi triển khai Program B, client giao tiếp với Program A theo các mẫu sau:

**Quy trình Giải Backtracking / MRV theo từng Tick:**
1. Kiểm tra kết nối (`GET /health`) và đọc đề bài (`GET /game/state`).
2. Thuật toán phát hiện bước gán (ASSIGN) → gọi `POST /game/move`.
3. Thuật toán quay lui (BACKTRACK) → gọi `POST /game/clear`.

**Quy trình Giải Min-Conflicts theo Snapshot:**
1. Min-Conflicts khởi tạo bàn cờ đầy đủ và thay đổi hàng loạt ô.
2. Mỗi khi có thay đổi lớn hoặc hoàn tất swap, đồng bộ toàn bộ snapshot sang A qua `PUT /game/state`.

---

## 5. Kết Quả Kiểm Thử (Verification & Testing Matrix)

Hệ thống đã vượt qua quy trình kiểm thử 2 lớp nghiêm ngặt:

### 5.1. Unit Tests (`tests/test_game.py`) — **67/67 PASSED**

| Nhóm Kiểm Thử | Số Lượng | Trọng Tâm Xác Minh |
|---|:---:|---|
| `TestFixedCellIsProtected` | 6 | Ngăn chặn `move`, `clear` trên ô đề bài; giữ nguyên giá trị sau lỗi. |
| `TestConflictingMoveIsAcceptedAndReported` | 4 | Chấp nhận move xung đột; kiểm tra danh sách tọa độ conflict; giải phóng khi xóa. |
| `TestReplacePreservesFixedCells` | 5 | Từ chối snapshot sửa đổi ô fixed; đảm bảo tính toàn vẹn dữ liệu. |
| `TestReplaceAllowsConflicts` | 5 | Chấp nhận snapshot chứa xung đột ở ô editable; xác nhận `SOLVED` khi giải đúng. |
| `TestInvalidCoordinatesAndValues` | 27 | Kiểm tra tọa độ âm, tọa độ $>8$, giá trị float, string, bool, None, giá trị $>9$. |
| `TestResetAndLoad` | 16 | Khôi phục trạng thái puzzle ban đầu, nạp puzzle mới, sinh UUID mới. |

```powershell
python -m unittest tests.test_game -v
# Kết quả: Ran 67 tests in 0.017s — OK
```

### 5.2. HTTP Smoke Tests (`A-sudoku-game/test_api.py`) — **43/43 PASSED**

- Xác nhận HTTP Status 200 cho các request hợp lệ.
- Xác nhận HTTP Status 400 và chuẩn mã lỗi JSON (`FIXED_CELL`, `INVALID_COORDINATE`, `INVALID_VALUE`, `INVALID_BOARD`, `INVALID_JSON`).
- Xác nhận HTTP Status 404 cho các route không tồn tại.

```powershell
python A-sudoku-game/test_api.py
# Kết quả: 43 PASSED | 0 FAILED
```

---

## 6. Tổng Kết Danh Mục Bàn Giao — Thành Viên A

| Hạng mục | File / Vị trí | Mô tả |
|---|---|---|
| **Domain Logic** | `A-sudoku-game/game.py` | Quản lý board, fixed mask, conflict detection, thread-safe |
| **REST API Adapter** | `A-sudoku-game/app.py` | HTTP server + routing 8 endpoints REST API v1 |
| **Frontend UI Engine** | `A-sudoku-game/static/` | Giao diện Sudoku, polling 350ms, DOM diffing |
| **Đặc tả Game** | `A-sudoku-game/GAME_SPECIFICATION.md` | Luật game, fixed cell, conflict acceptance |
| **Đặc tả API** | `A-sudoku-game/API_SPECIFICATION.md` | Đặc tả chi tiết 8 REST API endpoints v1 |
| **Báo cáo Kỹ thuật** | `A-sudoku-game/TECHNICAL_REPORT.md` | Báo cáo kiến trúc, đa luồng, kết quả kiểm thử |
| **Launchers** | `A-sudoku-game/START_A.py`, `START_ALL.py` | Bộ script khởi động nhanh hệ thống |
| **Unit Tests** | `tests/test_game.py` | 67 automated unit tests |
| **API Smoke Tests** | `A-sudoku-game/test_api.py` | 43 automated network tests |
