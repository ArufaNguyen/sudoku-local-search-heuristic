# TEST_PLAN.md — Kế Hoạch & Ma Trận Kiểm Thử Hệ Thống

> **Tác giả:** Thành viên B — Đào Quốc Thanh  
> **Dự án:** Bài tập lớn Trí tuệ Nhân tạo — Giải Sudoku bằng Local Search và Heuristic  
> **Phạm vi:** Kiểm thử toàn diện Domain, Thuật toán, API Client, Tick Engine và Dataset

---

## 1. Mục Tiêu Kiểm Thử

Kế hoạch kiểm thử bảo đảm tính đúng đắn và độ tin cậy của toàn bộ hệ thống trước khi thực hiện benchmark và thuyết trình:

1. **Tính đúng đắn của Domain Game (Program A):** Bảo vệ tuyệt đối các ô cố định (fixed cells), phát hiện xung đột chính xác trên 27 nhóm ràng buộc, và chuyển đổi trạng thái vòng đời trò chơi đúng quy tắc.
2. **Tính đúng đắn của 3 Thuật toán Giải (Program B):**
   - **Backtracking:** Luôn tìm ra nghiệm hợp lệ hoặc báo không có nghiệm.
   - **MRV Heuristic:** Luôn tìm ra nghiệm đúng và số lượng nodes khám phá luôn $\le$ Backtracking thuần trên cùng một bài toán.
   - **Min-Conflicts:** Khởi tạo đúng hoán vị theo hàng, tìm kiếm nghiệm tối ưu và dừng an toàn khi đạt giới hạn ngân sách.
3. **Tính nhất quán của Tick Engine:** Mọi tick có `api_action` khi áp dụng lên bàn cờ đều tái hiện chính xác ma trận snapshot trong `tick.board`.
4. **An toàn Đa luồng (Concurrency & Thread-Safety):** Worker thread `AutoRunner` chạy ổn định trong backend, không bị race condition và dừng chính xác khi gọi `pause()`.
5. **Tính toàn vẹn của Dataset:** Đủ 40 puzzle, phân bổ đều 4 mức độ khó, không trùng lặp và mỗi bài toán có đúng 1 nghiệm duy nhất.

---

## 2. Các Lệnh Chạy Kiểm Thử Tự Động

```powershell
# 1. Chạy toàn bộ Unit Tests tự động từ thư mục gốc dự án:
python -m unittest discover -s tests -v

# 2. Chạy bộ HTTP Smoke Tests kiểm tra API qua mạng:
python A-sudoku-game/test_api.py
```

**Tiêu chí hoàn thành:** Toàn bộ test suite đạt kết quả **100% PASSED** (không có FAIL, không có ERROR).

---

## 3. Danh Mục Các Test Suite Chi Tiết

### 3.1. Domain & API State Tests (`tests/test_game.py` — 67 Tests)

| Nhóm Test Class | Số lượng | Trọng tâm kiểm tra |
|---|:---:|---|
| `TestFixedCellIsProtected` | 6 | Ngăn chặn `move` và `clear` trên ô đề bài cố định; giữ nguyên giá trị ô sau khi ném lỗi `FIXED_CELL`. |
| `TestConflictingMoveIsAcceptedAndReported` | 4 | Chấp nhận move gây xung đột ở ô editable; cập nhật danh sách `conflicts` và đổi trạng thái thành `CONFLICT`. |
| `TestReplacePreservesFixedCells` | 5 | Từ chối các snapshot `replace` cố tình thay đổi giá trị của bất kỳ ô fixed nào; bảo vệ tính bất biến của đề bài. |
| `TestReplaceAllowsConflicts` | 5 | Chấp nhận snapshot chứa xung đột ở ô editable (cho Min-Conflicts); xác nhận chuyển sang `SOLVED` khi nạp snapshot đúng hoàn toàn. |
| `TestInvalidCoordinatesAndValues` | 27 | Kiểm tra toàn diện tọa độ âm, tọa độ $>8$, kiểu float, chuỗi, boolean, None, giá trị ngoài khoảng $1..9$. |
| `TestResetAndLoad` | 16 | Khôi phục bàn cờ về puzzle ban đầu qua `reset()`; nạp puzzle mới qua `load()`, sinh `game_id` UUID mới và tính lại fixed mask. |

---

### 3.2. Thuật Toán & Tick Recorder Tests (`B-auto-solver/solvers.py`)

| Tên Test Case | Mục đích kiểm tra |
|---|---|
| `test_candidates_valid_domain` | Hàm `candidates(board, r, c)` trả về chính xác tập giá trị hợp lệ $1..9$ không trùng hàng, cột, khối. Trả về `[]` nếu ô đã có số. |
| `test_count_conflicts_and_is_solved` | Hàm `count_conflicts()` đếm đúng số vi phạm; `is_solved()` trả về `True` khi và chỉ khi bàn cờ đầy và 0 xung đột. |
| `test_backtracking_correctness` | Backtracking giải chính xác các puzzle mẫu; bàn cờ kết quả thỏa mãn mọi ràng buộc Sudoku. |
| `test_mrv_heuristic_superiority` | MRV giải đúng puzzle và số node duyệt thỏa mãn $\text{nodes}(MRV) \le \text{nodes}(BT)$ trên mọi bài toán kiểm tra. |
| `test_min_conflicts_solves_sample` | Min-Conflicts giải thành công puzzle Easy với seed cố định trong ngân sách 1,000 iterations $\times$ 50 restarts. |
| `test_tick_snapshot_consistency` | Với mọi tick sinh ra có `api_action`, trạng thái bàn cờ sau khi áp dụng action khớp hoàn toàn với `tick.board`. |
| `test_record_ticks_flag` | Khi `record_ticks=False` (chạy benchmark), `ticks` rỗng để tiết kiệm bộ nhớ; khi `record_ticks=True` (visualizer), thu thập đầy đủ các bước. |

---

### 3.3. REST Client & Integration Tests (`B-auto-solver/client.py`)

| Tên Test Case | Mục đích kiểm tra |
|---|---|
| `test_health_endpoint` | `client.health()` trả về `{"success": true, "service": "sudoku-game"}` khi server A đang chạy. |
| `test_get_state_and_fixed_mask` | `client.get_state()` trả về đúng ma trận `board`, `fixed`, `fixed_mask`, `status`, `empty_cells`, `conflicts`. |
| `test_move_and_clear_integration` | `client.move()` và `client.clear()` cập nhật dữ liệu trên Program A thời gian thực. |
| `test_replace_snapshot_integration` | `client.replace()` gửi toàn bộ snapshot ma trận bàn cờ sang A thành công. |
| `test_error_handling_api_error` | Bắt đúng `APIError` khi gửi tọa độ hoặc giá trị sai quy cách; trích xuất chính xác mã lỗi HTTP 400 (`FIXED_CELL`, `INVALID_VALUE`, ...). |
| `test_connection_error_resilience` | Bắt đúng `ConnectionError` khi Program A chưa chạy; Program B không bị crash đột ngột. |

---

### 3.4. Backend AutoRunner & State Machine Tests (`B-auto-solver/app.py`)

| Tên Test Case | Mục đích kiểm tra |
|---|---|
| `test_session_lifecycle` | Vòng đời session: `prepare` tạo session mới $\rightarrow$ `next` tăng index $\rightarrow$ `previous` giảm index $\rightarrow$ `reset` xóa session. |
| `test_autorunner_background_execution` | `AutoRunner` chạy trên backend thread độc lập; chỉ số tick tự động tăng theo tốc độ được cấu hình. |
| `test_autorunner_blocking_pause` | Khi gọi `pause()`, thread dừng ngay lập tức và index được đóng băng hoàn toàn. |
| `test_thread_lock_safety` | Các thao tác `next`, `previous`, và `auto_start` sử dụng chung `threading.Lock` để loại trừ race condition. |

---

### 3.5. Dataset Integrity Tests (`B-auto-solver/dataset/puzzles.json`)

| Tên Test Case | Tiêu chuẩn kiểm tra |
|---|---|
| `test_total_puzzle_count` | File dataset chứa chính xác **40 puzzle**. |
| `test_difficulty_distribution` | Phân bổ chính xác **10 puzzle cho mỗi mức** (Easy, Medium, Hard, Expert). |
| `test_clue_distribution` | Số lượng clue cố định đúng chuẩn: Easy=46, Medium=38, Hard=32, Expert=27. |
| `test_solution_validity` | Toàn bộ 40 solution đi kèm đều là nghiệm Sudoku hoàn chỉnh và hợp lệ (`is_solved() == True`). |
| `test_single_unique_solution` | Mỗi puzzle kiểm tra có đúng **1 nghiệm duy nhất** (`count_solutions(board, limit=2) == 1`). |
| `test_puzzle_uniqueness` | Không có 2 puzzle nào bị trùng lặp trong toàn bộ tập dữ liệu 40 bài. |

---

## 4. Kết Quả Kiểm Thử Thực Tế Đạt Được

```powershell
# Chạy Unit Tests
python -m unittest discover -s tests -v
# Output: Ran 67 tests in 0.017s — OK (100% PASSED)

# Chạy Smoke Tests API
python A-sudoku-game/test_api.py
# Output: 43 PASSED | 0 FAILED (100% PASSED)
```

**Tổng kết:** Cả hai bộ kiểm thử với **110 bài test tự động** đều vượt qua xuất sắc, khẳng định toàn bộ hệ thống sẵn sàng cho thực nghiệm benchmark và thuyết trình.
