# Kịch bản thuyết trình F — Trần Tấn Tài

Phạm vi: slide 9–14 — thiết kế benchmark, kết quả chính, demo trực tiếp A+B và kết luận.
Thời lượng mục tiêu: 7–8 phút trình bày + 3–4 phút demo.

Nguồn số liệu: `B-auto-solver/results/results_summary.csv`, `heuristic_effectiveness.csv`,
`local_search_comparison.csv`, `complexity_trend.csv`, `BENCHMARK_SUMMARY.md`
(chạy ngày 2026-08-31, script `benchmark.py`).


---

## Nhận lời từ E

"Tiếp theo, em xin trình bày cách nhóm tổ chức thực nghiệm, các kết quả benchmark chính và phần demo trực tiếp hệ thống A–B."

## Slide 9 — Thiết kế benchmark (1 phút)

"Nhóm dùng bộ dữ liệu 40 puzzle độc lập, chia đều 4 mức độ khó: Easy, Medium, Hard, Expert — mỗi mức 10 đề, với số ô trống trung bình lần lượt là 35, 43, 49 và 54 ô, tương ứng 46, 38, 32 và 27 ô gợi ý (clue). Backtracking và MRV mỗi thuật toán chạy 3 lượt trên mỗi đề để giảm nhiễu thời gian đo. Min-Conflicts chạy 10 seed khởi tạo ngẫu nhiên trên mỗi đề để đánh giá độ nhạy với điều kiện khởi tạo. Tổng cộng nhóm thu được 640 lượt chạy: 120 lượt Backtracking, 120 lượt MRV và 400 lượt Min-Conflicts, trong khoảng 28,6 phút thực thi. Giới hạn an toàn: 2 triệu node cho Backtracking/MRV, 1.000 iteration và 50 restart cho Min-Conflicts."

## Slide 10 — Thời gian chạy (1 phút)

"Biểu đồ `runtime_by_difficulty.png` dùng trục log vì chênh lệch thời gian giữa các thuật toán khá lớn. Ở hai mức dễ — Easy và Medium — Backtracking thực ra nhanh hơn MRV, vì chi phí tính domain của heuristic tạo overhead trong khi không gian tìm kiếm còn nhỏ. Nhưng từ mức Hard trở đi, MRV vượt lên rõ rệt: ở Hard, MRV nhanh hơn Backtracking khoảng 2,36 lần; ở Expert, MRV chỉ mất trung bình khoảng 25,7 mili giây so với 364,7 mili giây của Backtracking — nhanh hơn khoảng 14,2 lần. Đây chính là điểm giao thoa — crossover point — nằm giữa Medium và Hard. Trong khi đó Min-Conflicts luôn là thuật toán chậm nhất trong cả 4 mức, ở Expert trung bình mất tới gần 13,8 giây mỗi lượt."

## Slide 11 — Không gian tìm kiếm (55 giây)

"Đây là bằng chứng trực tiếp cho vai trò của heuristic, thể hiện ở biểu đồ `heuristic_nodes.png`. Ở mức Expert, Backtracking duyệt trung bình khoảng 32.101 node, trong khi MRV chỉ khoảng 152 node — giảm tới 99,53%. Khi độ khó tăng từ Easy lên Expert, số node của Backtracking tăng gần 509 lần, còn MRV chỉ tăng khoảng 4,3 lần. Điều này giải thích vì sao MRV có thời gian ổn định hơn nhiều: bằng cách luôn chọn ô còn ít giá trị hợp lệ nhất để thử trước, MRV phát hiện nhánh vô vọng sớm hơn, trước khi cây tìm kiếm kịp phình to."

## Slide 12 — Tỷ lệ thành công Local Search (55 giây)

"Biểu đồ `local_search_success_rate.png` cho thấy Min-Conflicts đạt tỷ lệ thành công 100% ở cả ba mức Easy, Medium, Hard, và 99% ở Expert — tức 99 trên 100 lượt chạy tìm được lời giải. Trường hợp thất bại duy nhất rơi vào đúng một đề Expert cụ thể (54 ô trống) với một seed khởi tạo cụ thể: thuật toán chạy hết toàn bộ ngân sách — 1.000 iteration nhân 50 restart, tức 51.000 iteration — và dừng ở trạng thái `budget_exhausted` sau khoảng 91,8 giây. Điều này là bằng chứng thực nghiệm cho tính không đầy đủ — incomplete — của Local Search: nó có thể chạm cực tiểu cục bộ (local minimum) và không đảm bảo hội tụ trong mọi trường hợp, dù xác suất thành công tổng thể vẫn rất cao."

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

1. "Đầu tiên, đây là chương trình A — nơi giữ trạng thái bàn cờ Sudoku." *(Chọn hoặc tải một puzzle trên tab A.)*
2. Chuyển sang tab B: "Em chọn thuật toán MRV và bấm Prepare. B đọc đúng trạng thái hiện tại từ A qua REST API."
3. Bấm Next 3–5 lần: "Mỗi lần bấm chỉ phát ra một tick — ta thấy rõ phase hiện tại, ô đang xét, giá trị đang thử và các chỉ số metrics đi kèm."
4. Bấm Auto: "Khi chạy tự động, backend liên tục phát tick mà không cần bấm thủ công."
5. Chuyển sang tab A trong 2–3 giây rồi quay lại tab B: "Số bước và trạng thái vẫn tiếp tục thay đổi dù tab B mất focus — đây chính là phần Auto Run chạy nền (backend thread), không phụ thuộc vào việc tab có đang mở hay không."
6. Nếu còn thời gian: Reset rồi Prepare lại với Min-Conflicts: "Ở đây ta thấy phase CONFLICT và số iteration tăng dần — minh hoạ cách Local Search cải thiện dần lời giải thay vì xây dựng từng ô như Backtracking/MRV."

### Phương án dự phòng nếu demo gặp lỗi

- Nếu B không Prepare được: kiểm tra Terminal 1 có đang chạy A ở cổng 8000 không.
- Nếu trạng thái lệch giữa A và B: refresh tab A trước, sau đó refresh tab B rồi Prepare lại.
- Nếu demo trực tiếp không thể tiếp tục: quay lại slide 10–12, vì kết quả benchmark đã được lưu và kiểm chứng độc lập, không phụ thuộc vào demo sống.
- Không tự ý thay đổi số liệu hoặc tuyên bố demo thành công nếu trạng thái thực tế không thay đổi.

## Slide 14 — Kết luận (1 phút)

"Từ thực nghiệm trên 640 lượt chạy, nhóm rút ra bốn kết luận. Một, Backtracking là baseline chính xác và complete, nhưng chi phí tăng rất nhanh khi đề khó — tăng gần 509 lần số node từ Easy lên Expert. Hai, MRV giữ nguyên tính đúng đắn của Backtracking nhưng giảm tới 99,53% số node ở mức Expert, đồng thời có thời gian chạy ổn định nhất trong cả 4 mức, nên đây là lựa chọn chính của hệ thống khi cần độ tin cậy tuyệt đối. Ba, Min-Conflicts thể hiện rõ tư tưởng Local Search — đạt tỷ lệ thành công rất cao, 100% ở ba mức đầu và 99% ở Expert — nhưng vẫn tồn tại nguy cơ chạm cực tiểu cục bộ và cạn ngân sách, như trường hợp thất bại duy nhất nhóm ghi nhận được. Bốn, heuristic là công cụ thu hẹp không gian tìm kiếm hiệu quả, còn Local Search tạo ra sự đánh đổi giữa tốc độ hội tụ trung bình và độ tin cậy tuyệt đối — hai hướng tiếp cận bổ sung cho nhau chứ không thay thế hoàn toàn nhau."

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