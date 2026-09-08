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
| `TestConflictingMoveIsAcceptedAndReported` | 8 | Chấp nhận move gây xung đột ở ô editable; cập nhật danh sách `conflicts`, duy trì state và xóa conflict đúng cách. |
| `TestReplacePreservesFixedCells` | 5 | Từ chối các snapshot `replace` cố tình thay đổi giá trị của bất kỳ ô fixed nào; bảo vệ tính bất biến của đề bài. |
| `TestReplaceAllowsConflicts` | 5 | Chấp nhận snapshot chứa xung đột ở ô editable (cho Min-Conflicts); xác nhận chuyển sang `SOLVED` khi nạp snapshot đúng hoàn toàn. |
| `TestInvalidCoordinatesAndValues` | 27 | Kiểm tra toàn diện tọa độ âm, tọa độ $>8$, kiểu float, chuỗi, boolean, None, giá trị ngoài khoảng $1..9$. |
| `TestResetAndLoad` | 16 | Khôi phục bàn cờ về puzzle ban đầu qua `reset()`; nạp puzzle mới qua `load()`, sinh `game_id` UUID mới và tính lại fixed mask. |

---

### 3.2. Thuật Toán & Tick Recorder Tests (`tests/test_solvers.py` — 7 Tests)

| Tên Test Case | Mục đích kiểm tra |
|---|---|
| `test_candidates` | Hàm `candidates(board, r, c)` trả về chính xác tập giá trị hợp lệ $1..9$ không trùng hàng, cột, khối. Trả về `[]` nếu ô đã có số. |
| `test_count_conflicts_and_is_solved` | Hàm `count_conflicts()` đếm đúng số vi phạm; `is_solved()` trả về `True` khi và chỉ khi bàn cờ đầy và 0 xung đột. |
| `test_backtracking_solves_correctly` | Backtracking giải chính xác puzzle mẫu; bàn cờ kết quả thỏa mãn mọi ràng buộc Sudoku. |
| `test_mrv_solves_correctly_and_explores_fewer_or_equal_nodes` | MRV giải đúng puzzle kiểm tra và số node duyệt thỏa mãn $\text{nodes}(MRV) \le \text{nodes}(BT)$ trên cùng puzzle đó. |
| `test_min_conflicts_solves_sample` | Min-Conflicts giải thành công puzzle Easy với seed cố định trong ngân sách 1,000 iterations $\times$ 50 restarts. |
| `test_tick_consistency_and_api_action` | Với mọi tick sinh ra có `api_action`, trạng thái bàn cờ sau khi áp dụng action khớp hoàn toàn với `tick.board`. |
| `test_record_ticks_flag` | Khi `record_ticks=False` (chạy benchmark), `ticks` rỗng để tiết kiệm bộ nhớ; khi `record_ticks=True` (visualizer), thu thập đầy đủ các bước. |

---

### 3.3. REST Client Tests (`tests/test_client.py` — 27 Tests)

Các test dùng mock HTTP server A để kiểm tra hợp đồng REST một cách cách ly, bao gồm các nhóm sau:

| Nhóm hành vi được kiểm tra | Mục đích kiểm tra |
|---|---|
| Health và availability | `health()`/`is_alive()` trả đúng kết quả khi mock A online và khi không có server. |
| State và fixed mask | `get_state()` trả đúng cấu trúc, board 9×9, miền giá trị và fixed mask. |
| Move và clear | Kiểm tra editable/fixed cell, conflict, tọa độ và giá trị không hợp lệ. |
| Reset, load và replace | Khôi phục state, nạp puzzle, thay editable cells và chặn thay clue. |
| Lỗi HTTP/domain | Chuyển response lỗi của A thành `APIError` với mã `FIXED_CELL`, `INVALID_VALUE`, `INVALID_BOARD`, ... |
| Lỗi kết nối | Ném `ClientConnectionError` hoặc trả `False` an toàn khi Program A chưa chạy. |

---

### 3.4. Backend AutoRunner & State Machine Tests (`tests/test_backend_autorun.py` — 13 Tests)

| Nhóm hành vi được kiểm tra | Mục đích kiểm tra |
|---|---|
| Health và prepare | Kiểm tra B health; tạo session Backtracking/MRV có tick và thay thế session cũ. |
| Next và Previous | Kiểm tra tăng/giảm index, hành vi tại đầu/cuối lịch sử tick. |
| Auto chạy nền | Xác nhận index tự tăng khi không có request frontend và tốc độ worker được áp dụng. |
| Pause và Reset | Pause đóng băng index; Reset xóa session và dừng worker đang chạy. |

---

### 3.5. Dataset Integrity Tests (`tests/test_dataset.py` — 11 Tests)

| Tên Test Case | Tiêu chuẩn kiểm tra |
|---|---|
| `test_total_count_is_40` | File dataset chứa chính xác **40 puzzle**. |
| `test_distribution_per_level` | Phân bổ chính xác **10 puzzle cho mỗi mức** (Easy, Medium, Hard, Expert). |
| `test_clue_count_matches_spec` | Số lượng clue cố định đúng chuẩn: Easy=46, Medium=38, Hard=32, Expert=27. |
| `test_solution_is_valid_for_all_puzzles` | Toàn bộ 40 solution đi kèm đều là nghiệm Sudoku hoàn chỉnh và hợp lệ (`is_solved() == True`). |
| `test_sampled_puzzles_have_unique_solution` | Lấy 2 puzzle mỗi mức (8 puzzle) và xác nhận đúng **1 nghiệm duy nhất** bằng `count_solutions(board, limit=2) == 1`; pipeline benchmark còn kiểm tra uniqueness cho đủ 40 puzzle. |
| `test_no_duplicate_puzzles` | Không có 2 puzzle nào bị trùng lặp trong toàn bộ tập dữ liệu 40 bài. |

### 3.6. Benchmark Pipeline Tests (`tests/test_benchmark.py` — 14 Tests)

Bao phủ validation dataset, kết quả chạy rút gọn, phép aggregate và schema của năm file CSV: `results_raw.csv`, `results_summary.csv`, `heuristic_effectiveness.csv`, `local_search_comparison.csv`, `complexity_trend.csv`.

---

## 4. Kết Quả Kiểm Thử Thực Tế Đạt Được

```powershell
# Chạy Unit Tests
python -m unittest discover -s tests -v
# Output xác minh ngày 01/09/2026: Ran 139 tests — OK (100% PASSED)

# Chạy Smoke Tests API
python A-sudoku-game/test_api.py
# Output: 43 PASSED | 0 FAILED (100% PASSED)
```

**Tổng kết xác minh ngày 01/09/2026:** Bộ `unittest discover` có **139 test** và đạt 139/139. Ngoài suite này, script HTTP smoke test đạt riêng **43/43** trên một Program A thật chạy ở cổng cách ly; các request không tác động vào phiên A đang mở của người dùng.
