# Kịch bản thuyết trình F — Trần Tấn Tài

Phạm vi: slide 9–14 — thiết kế benchmark, kết quả chính, demo trực tiếp A+B và kết luận.
Thời lượng mục tiêu: 7–8 phút trình bày + 3–4 phút demo.

Nguồn số liệu: `B-auto-solver/results/results_summary.csv`, `heuristic_effectiveness.csv`,
`local_search_comparison.csv`, `complexity_trend.csv`, `BENCHMARK_SUMMARY.md`
(chạy ngày 2026-08-31, script `benchmark.py`).

> Ghi chú: số liệu trong bản này là số liệu benchmark **thật** của nhóm, khác với số liệu tham khảo
> trong `TASK.md` (98,87% / 64%) — vì đó là số ví dụ của `final sample/`, không phải kết quả của nhóm mình.

---

## Nhận lời từ E

"Tiếp theo, em xin trình bày cách nhóm tổ chức thực nghiệm, các kết quả benchmark chính và phần demo trực tiếp hệ thống A–B."

## Slide 9 — Thiết kế benchmark (45–50 giây)

"Nhóm test trên 40 đề Sudoku, chia đều 4 mức độ khó từ Easy đến Expert, mỗi mức 10 đề — số ô trống tăng dần từ 35 ở Easy lên 54 ở Expert. Backtracking và MRV mỗi thuật toán chạy 3 lần trên mỗi đề để đo runtime ổn định hơn. Min-Conflicts chạy 10 seed khởi tạo ngẫu nhiên mỗi đề, vì kết quả của nó phụ thuộc điểm khởi đầu. Tổng cộng 640 lượt chạy, có giới hạn an toàn để không bị treo: 2 triệu node cho Backtracking/MRV, 51.000 iteration cho Min-Conflicts."

## Slide 10 — Thời gian chạy (45–50 giây)

"Biểu đồ dùng trục log vì chênh lệch giữa các thuật toán rất lớn. Ở Easy và Medium, Backtracking thực ra nhanh hơn MRV — vì đề còn dễ, chi phí tính heuristic của MRV chưa đáng. Nhưng từ Hard trở đi, MRV vượt hẳn: ở Expert, MRV chỉ mất 25,7 ms so với 364,7 ms của Backtracking, nhanh hơn khoảng 14 lần. Đây là điểm giao thoa giữa Medium và Hard. Min-Conflicts luôn chậm nhất, gần 13,8 giây ở Expert."

## Slide 11 — Không gian tìm kiếm (40–45 giây)

"Đây là bằng chứng trực tiếp cho vai trò của heuristic. Ở Expert, Backtracking duyệt trung bình khoảng 32.000 node, còn MRV chỉ khoảng 150 node — giảm tới 99,53%. Vì MRV luôn chọn ô còn ít giá trị hợp lệ nhất để thử trước, nó phát hiện đường cụt sớm hơn, trước khi cây tìm kiếm kịp phình to."

## Slide 12 — Tỷ lệ thành công Local Search (40–45 giây)

"Min-Conflicts đạt tỷ lệ thành công 100% ở ba mức Easy, Medium, Hard, và 99% ở Expert. Trường hợp thất bại duy nhất là một đề Expert cụ thể, khi thuật toán chạy hết toàn bộ ngân sách 51.000 iteration mà không hội tụ — đúng với đặc điểm không đảm bảo (incomplete) của Local Search, dù xác suất thành công tổng thể vẫn rất cao."

## Slide 13 — Demo trực tiếp (3–4 phút)

### Chuẩn bị trước khi thuyết trình

```powershell
# Mở hai terminal tại project root, nơi chứa TASK.md.

# Terminal 1
python A-sudoku-game/app.py

# Terminal 2
python B-auto-solver/app.py
```

Mở sẵn hai tab trình duyệt:
- Game A: `http://127.0.0.1:8000`
- Solver B: `http://127.0.0.1:8001`

Checklist kiểm tra trước khi lên trình bày:
1. A và B đều phản hồi bình thường (health check).
2. A đang có một puzzle chưa giải.
3. B Prepare được với thuật toán MRV.
4. Next làm index tăng và board bên A thay đổi tương ứng.
5. Auto chạy ổn định, không đứng giữa chừng.
6. Chuyển sang tab khác 2–3 giây rồi quay lại B, index vẫn tiếp tục tăng.
7. Pause dừng đúng tại index hiện tại, không bị lệch.

### Lời nói và thao tác

1. *(Chọn puzzle trên tab A.)* "Đây là A — nơi giữ trạng thái bàn cờ."
2. Chuyển tab B: "Em chọn MRV, bấm Prepare — B đọc đúng trạng thái từ A qua API."
3. Bấm Next vài lần: "Mỗi lần bấm là một tick — thấy rõ ô đang xét và giá trị đang thử."
4. Bấm Auto: "Giờ backend tự phát tick liên tục, không cần bấm tay."
5. Chuyển qua tab A 2–3 giây rồi quay lại: "Vẫn chạy tiếp — vì Auto Run nằm ở backend, không phụ thuộc tab có mở hay không."
6. *(Nếu còn thời gian)* Đổi sang Min-Conflicts: "Đây là cách sửa lỗi dần trên toàn bàn, khác hẳn kiểu đào-sâu-lùi-lại của MRV."

### Phương án dự phòng nếu demo gặp lỗi

- Nếu B không Prepare được: kiểm tra Terminal 1 có đang chạy A ở cổng 8000 không.
- Nếu trạng thái lệch giữa A và B: refresh tab A trước, sau đó refresh tab B rồi Prepare lại.
- Nếu demo trực tiếp không thể tiếp tục: quay lại slide 10–12, vì kết quả benchmark đã được lưu và kiểm chứng độc lập, không phụ thuộc vào demo sống.
- Không tự ý thay đổi số liệu hoặc tuyên bố demo thành công nếu trạng thái thực tế không thay đổi.

## Slide 14 — Kết luận (1 phút)

"Tóm lại nhóm rút ra ba điểm. Một, Backtracking đúng và đầy đủ nhưng chi phí tăng rất nhanh khi đề khó. Hai, MRV giữ nguyên độ chính xác đó nhưng giảm tới 99,53% số node ở Expert, nên là lựa chọn chính khi cần độ tin cậy tuyệt đối. Ba, Min-Conflicts minh hoạ rõ tư tưởng Local Search với tỷ lệ thành công rất cao, nhưng vẫn có nguy cơ không hội tụ như trường hợp thất bại đã ghi nhận. Heuristic giúp thu hẹp không gian tìm kiếm, còn Local Search đánh đổi tốc độ trung bình với độ tin cậy tuyệt đối — hai hướng bổ sung cho nhau."

## Câu chốt

"Nhóm em xin kết thúc phần trình bày và sẵn sàng trả lời câu hỏi."

## Câu hỏi F nên chuẩn bị trả lời

**Vì sao ở Easy/Medium, MRV lại chậm hơn Backtracking?**
Vì ở các mức dễ, không gian tìm kiếm còn nhỏ nên chi phí tính toán domain của MRV (kiểm tra giá trị hợp lệ cho từng ô, độ phức tạp khoảng O(N²) mỗi bước) tạo ra overhead lớn hơn lợi ích cắt tỉa mang lại. Chỉ khi không gian tìm kiếm đủ lớn (từ Hard trở đi) thì lợi ích cắt tỉa mới vượt qua chi phí tính toán — đó là điểm giao thoa (crossover point).

**Vì sao Min-Conflicts chậm hơn MRV dù là Local Search?**
Vì mỗi bước Min-Conflicts phải đánh giá lại xung đột trên toàn bàn cờ, có thể cần nhiều restart khi rơi vào cực tiểu cục bộ, và với đề khó số iteration cần thiết tăng rất nhanh (từ 146 ở Easy lên gần 7.199 ở Expert). Local Search không mặc định nhanh hơn — hiệu quả của nó phụ thuộc vào hàm đánh giá và cấu trúc không gian trạng thái của bài toán.

**Kết quả runtime có phải số tuyệt đối không?**
Không. Runtime phụ thuộc vào máy và môi trường chạy cụ thể lúc benchmark. Kết luận đáng tin hơn là các xu hướng đo được trong cùng một môi trường: tỷ lệ giảm node của MRV, tỷ lệ thành công của Min-Conflicts, và thứ tự tương đối về tốc độ giữa ba thuật toán theo từng mức độ khó.

**Trường hợp Min-Conflicts thất bại xảy ra như thế nào?**
Đúng một lượt trong 400 lượt chạy: một đề Expert (54 ô trống) với seed khởi tạo số 5, thuật toán chạy hết toàn bộ ngân sách cho phép (1.000 iteration × 50 restart = 51.000 iteration, khoảng 91,8 giây) mà không tìm được lời giải hợp lệ, dừng ở trạng thái `budget_exhausted`.