# COMPLEXITY_ANALYSIS.md — Phân Tích Độ Phức Tạp & Đối Chiếu Thực Nghiệm

> **Tác giả:** Thành viên B — Đào Quốc Thanh  
> **Dự án:** Bài tập lớn Trí tuệ Nhân tạo — Giải Sudoku bằng Local Search và Heuristic  
> **Nguồn số liệu thực nghiệm:** Chạy 640 lượt benchmark chính thức (`B-auto-solver/benchmark.py`) trên tập 40 puzzle chuẩn (`dataset/puzzles.json`).

---

## 1. Ký Hiệu Toán Học & Định Nghĩa

| Ký hiệu | Ý nghĩa trong bài toán Sudoku |
|:---:|---|
| $N$ | Kích thước cạnh bàn cờ ($N = 9$) |
| $n = N^2$ | Tổng số ô trên bàn cờ ($n = 81$) |
| $m$ | Số ô trống cần điền ($35 \le m \le 54$ tùy theo độ khó) |
| $b$ | Hệ số phân nhánh trung bình (Branching Factor — số candidates trung bình mỗi ô) |
| $I$ | Số vòng lặp tối ưu cục bộ tối đa trong mỗi lần thử (Max Iterations = 1,000) |
| $R$ | Số lần khởi động lại ngẫu nhiên tối đa (Max Restarts = 50) |

---

## 2. Phân Tích Độ Phức Tạp Lý Thuyết

### 2.1. Thuật toán Backtracking Thuần (DFS Cơ Sở)

- **Thời gian trường hợp xấu nhất (Worst-Case Time Complexity):**
  $$T_{\text{BT-worst}} = O(9^m)$$
  Với mỗi ô trống trong số $m$ ô, thuật toán có thể phải thử tối đa 9 giá trị. Ở mức độ khó **Expert** ($m = 54$), không gian tìm kiếm lý thuyết lên tới $9^{54} \approx 1.47 \times 10^{51}$ trạng thái.
- **Thời gian trường hợp tốt nhất (Best-Case Time Complexity):**
  $$T_{\text{BT-best}} = O(m)$$
  Xảy ra khi mỗi ô trống chỉ có duy nhất 1 ứng viên hợp lệ và không bao giờ phải quay lui.
- **Độ phức tạp không gian (Space Complexity):**
  $$S_{\text{BT}} = O(m)$$
  Bộ nhớ stack đệ quy tỷ lệ tuyến tính với độ sâu tìm kiếm tối đa $m \le 81$, hoàn toàn nhỏ gọn và an toàn cho bộ nhớ.

---

### 2.2. Thuật toán Backtracking kết hợp Heuristic MRV

- **Thời gian trường hợp xấu nhất (Worst-Case Time Complexity):**
  $$T_{\text{MRV-worst}} = O(9^m)$$
  > [!NOTE]
  > **Nguyên lý lý thuyết:** Heuristic MRV **không làm thay đổi độ phức tạp trường hợp xấu nhất** trong ký pháp $O$. Nếu mọi ô trống đều có cùng số lượng ứng viên khả dĩ, thứ tự chọn ô không thay đổi cấu trúc cây tìm kiếm xấu nhất.

- **Chi phí phụ trội tại mỗi node (Selection Overhead):**
  $$\Delta T_{\text{select}} = O(N^2) = O(81) \text{ mỗi node}$$
  Tại mỗi bước chọn biến, MRV phải quét qua tất cả các ô trống còn lại và tính toán tập `candidates()` tương ứng.
- **Lợi ích thực tế — Nguyên lý Fail-First:**
  - MRV ưu tiên chọn các ô có miền giá trị hẹp nhất ($b$ nhỏ nhất).
  - Nếu xuất hiện ngõ cụt ($b = 0$), MRV phát hiện ngay tại đỉnh cây và cắt tỉa toàn bộ cây con bên dưới.
  - Thuật toán làm giảm mạnh hệ số phân nhánh thực tế $b_{\text{eff}} \ll 9$, đưa không gian tìm kiếm thực tế về $O(b_{\text{eff}}^m)$.

---

### 2.3. Thuật toán Local Search — Min-Conflicts

- **Độ phức tạp mỗi vòng lặp (Per-Iteration Time Complexity):**
  - Khởi tạo hoán vị theo hàng: $O(N^2) = O(81)$ thao tác.
  - Tìm các ô có xung đột: $O(N^2) = O(81)$.
  - Đánh giá các phép hoán đổi cùng hàng: Có tối đa $O(N)$ ô editable cùng hàng, mỗi phép hoán đổi tốn $O(N)$ để tính toán lại xung đột cột và khối 3×3 $\rightarrow$ Chi phí mỗi vòng lặp là $O(N^3) = O(729)$.
- **Tổng chi phí thời gian theo ngân sách (Budget Time Complexity):**
  $$T_{\text{MC-budget}} = O\big((R + 1) \times I \times N^3\big)$$
  Với $R = 50, I = 1,000, N = 9 \rightarrow$ Ngân sách tối đa khoảng $3.7 \times 10^7$ phép toán cơ bản.
- **Độ phức tạp không gian (Space Complexity):**
  $$S_{\text{MC}} = O(N^2) = O(81)$$
  Chỉ lưu trữ ma trận bàn cờ hiện tại và danh sách các ô cố định.
- **Tính Không Đầy Đủ (Incompleteness):** Min-Conflicts là thuật toán tìm kiếm cục bộ không đầy đủ (incomplete). Thuật toán có thể bị kẹt trong các cực tiểu cục bộ sâu (deep local minima) hoặc cao nguyên (plateau) và không tìm ra nghiệm trong giới hạn ngân sách $I \times R$.

---

## 3. Đối Chiếu Thực Nghiệm & Phân Tích Đột Phá

Dữ liệu được trích xuất từ 640 lượt chạy benchmark (`B-auto-solver/results/`):

### 3.1. Hiệu quả Cắt Tỉa Không Gian Tìm Kiếm của MRV

| Mức độ khó (Difficulty) | Ô trống ($m$) | Backtracking Nodes (Mean) | MRV Nodes (Mean) | **Tỷ lệ Giảm Node (%)** |
|---|:---:|:---:|:---:|:---:|
| **Easy** | 35 | 63.1 | 35.0 | **44.53%** |
| **Medium** | 43 | 207.4 | 43.2 | **79.17%** |
| **Hard** | 49 | 1,355.9 | 51.3 | **96.22%** |
| **Expert** | 54 | 32,101.4 | 151.7 | **99.53%** |

```
Tăng trưởng số Node trung bình theo Độ Khó:
Expert : [BT: 32,101.4 nodes] ========================================►
         [MRV: 151.7 nodes]   |
Hard   : [BT: 1,355.9 nodes]  ====►
         [MRV: 51.3 nodes]    |
Medium : [BT: 207.4 nodes]    =►
         [MRV: 43.2 nodes]    |
Easy   : [BT: 63.1 nodes]     ►
         [MRV: 35.0 nodes]    |
```

> [!TIP]
> **Điểm nhấn cốt lõi:** Tại mức **Expert**, Backtracking thuần phải duyệt trung bình **32,101 node**, trong khi MRV chỉ cần duyệt **151.7 node** — giảm tới **211.6 lần** số trạng thái cần khám phá.

---

### 3.2. Đánh Đổi Thời Gian Thực Thi (Runtime Trade-off & Crossover Point)

| Mức độ khó | Backtracking Runtime (ms) | MRV Runtime (ms) | Min-Conflicts Runtime (ms) | Thuật toán tối ưu nhất |
|---|:---:|:---:|:---:|:---:|
| **Easy** | **0.941 ms** | 4.047 ms | 233.907 ms | **Backtracking** |
| **Medium** | **2.796 ms** | 4.691 ms | 469.889 ms | **Backtracking** |
| **Hard** | 14.861 ms | **6.304 ms** | 2,497.173 ms | **MRV** *(nhanh hơn 2.36×)* |
| **Expert** | 364.744 ms | **25.726 ms** | 13,846.242 ms | **MRV** *(nhanh hơn 14.18×)* |

#### Phân tích Hiện tượng Điểm Giao Thoa (Crossover Point):
1. **Tại Easy và Medium ($m \le 43$):** Backtracking thuần nhanh hơn MRV (0.94ms vs 4.05ms). Chi phí tính toán miền giá trị $O(N^2)$ tại mỗi node của MRV lớn hơn lợi ích tiết kiệm vài chục node quay lui.
2. **Điểm giao thoa (Crossover Point):** Nằm tại khoảng $m \approx 43 - 49$ (giữa Medium và Hard). Khi số ô trống vượt qua ngưỡng này, cây tìm kiếm của Backtracking bùng nổ hàm mũ.
3. **Tại Hard và Expert ($m \ge 49$):** Lợi ích cắt tỉa 96%–99.5% cây tìm kiếm áp đảo hoàn toàn overhead tính toán, giúp MRV chạy nhanh hơn Backtracking từ **2.36 lần đến 14.18 lần**.

---

### 3.3. Đánh Giá Thực Nghiệm Thuật Toán Min-Conflicts

| Mức độ khó | Số Lượt Chạy | Thành Công | Thất Bại | **Tỷ lệ Thành Công** | Số Iterations trung bình | Số Restarts trung bình |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Easy** | 100 | 100 | 0 | **100.0%** | 146.2 | 0.08 |
| **Medium** | 100 | 100 | 0 | **100.0%** | 293.6 | 0.11 |
| **Hard** | 100 | 100 | 0 | **100.0%** | 1,457.9 | 1.12 |
| **Expert** | 100 | 99 | 1 | **99.0%** | 7,198.6 | 6.68 |

#### Bằng chứng Thực Nghiệm về Tính Không Đầy Đủ (Incompleteness):
- Tại mức **Expert**, trong lượt chạy với **Puzzle ID 32** (seed = 5):
  - Thuật toán đã thực hiện đủ **51,000 iterations** (1,000 iterations $\times$ 50 restarts) mà vẫn chưa giải quyết hết xung đột cuối cùng.
  - Sau 91,837.8 ms (~91.8 giây), thuật toán dừng với lý do `budget_exhausted`.
- **Kết luận:** Đây là minh chứng thực nghiệm xác thực rằng Local Search không bảo đảm tìm ra nghiệm trên các bài toán có không gian ràng buộc quá chặt chẽ (tightly-constrained CSPs).

---

## 4. Kết Luận Tổng Hợp So Sánh

1. **Backtracking:** Thích hợp nhất cho bài toán nhỏ và dễ ($m \le 43$) nhờ chi phí mỗi bước cực nhẹ, nhưng không có khả năng mở rộng (non-scalable) cho bài toán khó.
2. **Backtracking + MRV:** Là giải pháp cân bằng và mạnh mẽ nhất cho CSP. Heuristic Fail-First giúp kiểm soát triệt để sự bùng nổ tổ hợp trên bài toán khó.
3. **Min-Conflicts:** Khả thi trên các bài toán Sudoku từ Easy đến Hard, nhưng có độ biến thiên thời gian (variance) rất lớn và không bảo đảm tìm ra nghiệm trên bài toán Expert.
