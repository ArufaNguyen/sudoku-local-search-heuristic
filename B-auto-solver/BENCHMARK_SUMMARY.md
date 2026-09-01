# BENCHMARK_SUMMARY.md — Tóm Tắt Kết Quả Thực Nghiệm & So Sánh Thuật Toán

> **Tác giả:** Thành viên B — Đào Quốc Thanh  
> **Ngày chạy benchmark:** 2026-08-31  
> **Script thực thi:** `B-auto-solver/benchmark.py`  
> **Dataset đầu vào:** `B-auto-solver/dataset/puzzles.json` (40 puzzle, seed=42)  
> **Tổng số lượt chạy:** 640 lượt (BT × 120, MRV × 120, Min-Conflicts × 400)  
> **Tổng thời gian thực thi:** 1717.5 giây (~28.6 phút)  
> **File dữ liệu thô:** `B-auto-solver/results/results_raw.csv`

---

## 1. Cấu Hình & Tham Số Thực Nghiệm

| Tham số cấu hình | Giá trị thiết lập | Mục đích |
|---|---|---|
| **Bộ dữ liệu (Dataset)** | 40 puzzle độc lập | 10 Easy (46 clues), 10 Medium (38 clues), 10 Hard (32 clues), 10 Expert (27 clues) |
| **BT / MRV Lượt chạy** | 3 lượt / puzzle | Loại bỏ nhiễu hệ điều hành, lấy trung bình thời gian thực thi |
| **Min-Conflicts Lượt chạy** | 10 seeds / puzzle | Đánh giá phân phối xác suất và độ nhạy của khởi tạo ngẫu nhiên ($seeds \in [0..9]$) |
| **BT / MRV Safety Node Limit** | 2,000,000 nodes | Ngăn tràn bộ nhớ nếu thuật toán rơi vào không gian vô hạn |
| **Min-Conflicts Max Iterations** | 1,000 iterations | Giới hạn số vòng lặp tối ưu cục bộ trong mỗi lần thử |
| **Min-Conflicts Max Restarts** | 50 restarts | Giới hạn số lần khởi động lại ngẫu nhiên khi gặp cực tiểu cục bộ |

---

## 2. Bảng Tổng Hợp Chỉ Số Hiệu Năng 3 Thuật Toán

*Trích xuất trực tiếp từ `B-auto-solver/results/results_summary.csv`:*

| Mức độ khó | Thuật toán | Số lượt | Thành công | Tỷ lệ (%) | Runtime Mean (ms) | Runtime Median (ms) | Runtime p95 (ms) | Nodes Explore (Mean) | Backtracks (Mean) | Iterations (Mean) | Restarts (Mean) |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Easy** | Backtracking | 30 | 30 | **100%** | **0.941** | 0.816 | 1.543 | 63.1 | 36.9 | — | — |
| | MRV Heuristic | 30 | 30 | **100%** | 4.047 | 4.187 | 4.634 | 35.0 | 0.0 | — | — |
| | Min-Conflicts | 100 | 100 | **100%** | 233.907 | 69.524 | 1,365.065 | — | — | 146.2 | 0.08 |
| **Medium** | Backtracking | 30 | 30 | **100%** | **2.796** | 1.545 | 7.810 | 207.4 | 213.9 | — | — |
| | MRV Heuristic | 30 | 30 | **100%** | 4.691 | 4.599 | 6.810 | 43.2 | 0.3 | — | — |
| | Min-Conflicts | 100 | 100 | **100%** | 469.889 | 209.051 | 1,772.080 | — | — | 293.6 | 0.11 |
| **Hard** | Backtracking | 30 | 30 | **100%** | 14.861 | 8.174 | 41.067 | 1,355.9 | 1,667.0 | — | — |
| | MRV Heuristic | 30 | 30 | **100%** | **6.304** | 6.064 | 7.191 | 51.3 | 2.7 | — | — |
| | Min-Conflicts | 100 | 100 | **100%** | 2,497.173 | 1,478.754 | 10,759.918 | — | — | 1,457.9 | 1.12 |
| **Expert** | Backtracking | 30 | 30 | **100%** | 364.744 | 113.820 | 1,837.409 | 32,101.4 | 41,550.6 | — | — |
| | MRV Heuristic | 30 | 30 | **100%** | **25.726** | 22.554 | 61.640 | 151.7 | 107.4 | — | — |
| | Min-Conflicts | 100 | 99 | **99%** | 13,846.242 | 7,073.635 | 62,176.807 | — | — | 7,198.6 | 6.68 |

---

## 3. Đánh Giá Hiệu Quả Heuristic MRV so với Backtracking

*Trích xuất trực tiếp từ `B-auto-solver/results/heuristic_effectiveness.csv`:*

| Mức độ khó | BT Nodes (Mean) | MRV Nodes (Mean) | **Mức Giảm Node (%)** | BT Runtime (ms) | MRV Runtime (ms) | **Mức Giảm Thời Gian (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Easy** | 63.1 | 35.0 | **44.53%** | 0.941 | 4.047 | -330.07% *(Overhead domain)* |
| **Medium** | 207.4 | 43.2 | **79.17%** | 2.796 | 4.691 | -67.78% *(Overhead domain)* |
| **Hard** | 1,355.9 | 51.3 | **96.22%** | 14.861 | 6.304 | **+57.58%** *(MRV nhanh hơn 2.36×)* |
| **Expert** | 32,101.4 | 151.7 | **99.53%** | 364.744 | 25.726 | **+92.95%** *(MRV nhanh hơn 14.18×)* |

### Nhận định Kỹ thuật:
1. **Khả năng cắt tỉa vượt bậc:** Ở mức độ khó **Expert**, heuristic MRV giúp giảm từ 32,101.4 node xuống chỉ còn **151.7 node** (giảm **99.53%**).
2. **Khắc phục bùng nổ tổ hợp:** Backtracking tăng số node gấp **508.7 lần** khi chuyển từ Easy lên Expert, trong khi MRV chỉ tăng từ 35.0 node lên 151.7 node (tăng vỏn vẹn **4.3 lần**).
3. **Crossover Point:** Nằm giữa Medium và Hard. Từ mức Hard trở đi, thời gian tiết kiệm do cắt tỉa nhánh áp đảo hoàn toàn chi phí tính toán domain $O(N^2)$.

---

## 4. Phân Tích Thực Nghiệm Local Search (Min-Conflicts)

*Trích xuất từ `B-auto-solver/results/local_search_comparison.csv`:*

- **Khả năng giải quyết:** Đạt tỷ lệ thành công tuyệt đối **100%** trên các mức Easy, Medium, Hard và đạt **99%** trên mức Expert.
- **Trường hợp thất bại duy nhất:**
  - **Bài toán:** Puzzle ID 32 (Độ khó Expert, 27 clues, 54 ô trống).
  - **Seed khởi tạo:** 5.
  - **Số iterations đã chạy:** 51,000 iterations (= 1,000 iters × 50 restarts — cạn kiệt ngân sách).
  - **Thời gian dừng:** 91,837.8 ms (~91.8 giây) với trạng thái `budget_exhausted`.
- **Ý nghĩa khoa học:** Minh chứng thực nghiệm khẳng định Min-Conflicts là giải thuật **incomplete**, rất nhạy với cấu hình ban đầu và dễ rơi vào cực tiểu cục bộ trên các bài toán có ràng buộc chặt chẽ.

---

## 5. Danh Mục Biểu Đồ Trực Quan Hóa (Charts Artifacts)

Bộ 3 biểu đồ chuẩn được sinh tự động bởi `benchmark.py`, lưu tại thư mục `B-auto-solver/results/charts/`:

| Tên Biểu Đồ | File Đường Dẫn | Nội Dung Phân Tích |
|---|---|---|
| **Thời Gian Chạy Theo Độ Khó** | [`runtime_by_difficulty.png`](results/charts/runtime_by_difficulty.png) | Bar chart: So sánh Mean Runtime (ms) giữa 3 thuật toán theo 4 cấp độ khó. Thể hiện rõ crossover point tại mức Hard. |
| **Hiệu Quả Giảm Node của MRV** | [`heuristic_nodes.png`](results/charts/heuristic_nodes.png) | Bar chart (Log scale): Minh họa mức giảm 99.53% số node giữa Backtracking thuần và MRV Heuristic trên mức Expert. |
| **Tỷ Lệ Thành Công Min-Conflicts** | [`local_search_success_rate.png`](results/charts/local_search_success_rate.png) | Bar chart: Tỷ lệ giải thành công (%) của Min-Conflicts trên 4 cấp độ khó (100% ở Easy/Medium/Hard, 99% ở Expert). |

---

## 6. Lệnh Tái Lập Kết Quả (Reproducibility)

Để tái lập toàn bộ số liệu và sinh lại 5 file CSV cùng 3 biểu đồ PNG:

```powershell
# Chạy pipeline benchmark từ thư mục gốc:
python B-auto-solver/benchmark.py
```
