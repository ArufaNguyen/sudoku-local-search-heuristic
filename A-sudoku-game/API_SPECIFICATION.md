# API Specification — Program A (REST API v1)

> **Tác giả:** Thành viên A — Trương Lê Quốc Việt  
> **Dự án:** Bài tập lớn Trí tuệ Nhân tạo — Giải Sudoku bằng Local Search và Heuristic  
> **Base URL:** `http://127.0.0.1:8000/api/v1`  
> **Giao thức:** HTTP/1.1 (JSON Payload, UTF-8)

---

## 1. Thông Tin Tổng Quan

| Thuộc tính | Giá trị |
|---|---|
| **Base URL** | `http://127.0.0.1:8000/api/v1` |
| **Giao thức** | HTTP/1.1 (RESTful JSON) |
| **Content-Type** | `application/json; charset=utf-8` |
| **CORS** | `Access-Control-Allow-Origin: *` (Cho phép gọi cross-origin từ Program B tại `http://127.0.0.1:8001`) |
| **Xác thực** | Không yêu cầu (Giao tiếp mạng nội bộ Local IPC) |

---

## 2. Quy Ước Tọa Độ và Định Dạng Dữ Liệu

```
Ma trận bàn cờ Sudoku 9×9:
          y=0   y=1   y=2   y=3   y=4   y=5   y=6   y=7   y=8   (Cột - Column)
       ┌─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┐
  x=0  │ (0,0)│ (0,1)│ (0,2)│ (0,3)│ (0,4)│ (0,5)│ (0,6)│ (0,7)│ (0,8)│
  x=1  │ (1,0)│ (1,1)│ (1,2)│ (1,3)│ (1,4)│ (1,5)│ (1,6)│ (1,7)│ (1,8)│
  x=2  │ (2,0)│ (2,1)│ (2,2)│ (2,3)│ (2,4)│ (2,5)│ (2,6)│ (2,7)│ (2,8)│
       ├─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┤
  ...  │ ... │ ... │ ... │ ... │ ... │ ... │ ... │ ... │ ... │
       ├─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┤
  x=8  │ (8,0)│ (8,1)│ (8,2)│ (8,3)│ (8,4)│ (8,5)│ (8,6)│ (8,7)│ (8,8)│
       └─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┘
 (Hàng - Row)
```

- `x`: Chỉ số **Hàng** (Row index), kiểu `int`, phạm vi hợp lệ: $0 \le x \le 8$.
- `y`: Chỉ số **Cột** (Column index), kiểu `int`, phạm vi hợp lệ: $0 \le y \le 8$.
- `num` / `value`: Giá trị điền vào ô, kiểu `int`, phạm vi: $1 \le num \le 9$.
- `0`: Đại diện cho ô trống trong ma trận bàn cờ.

---

## 3. Bảng Tổng Hợp 8 Endpoints REST API v1

| Method | Endpoint | Request Body | HTTP Status | Mô tả nghiệp vụ |
|---|---|---|:---:|---|
| `GET` | `/health` | Không | 200 | Kiểm tra trạng thái hoạt động của Game Service A. |
| `GET` | `/game/state` | Không | 200 | Lấy toàn bộ trạng thái hiện tại (board, fixed, fixed_mask, conflicts, status). |
| `GET` | `/game/status` | Không | 200 | Lấy trạng thái rút gọn (status, empty_cells, conflict_count). |
| `POST` | `/game/move` | `{"x": int, "y": int, "num": int}` | 200 / 400 | Điền một giá trị vào ô editable; chấp nhận move xung đột. |
| `POST` | `/game/clear` | `{"x": int, "y": int}` | 200 / 400 | Xóa một ô editable về giá trị 0. Chặn xóa ô fixed. |
| `POST` | `/game/reset` | `{}` hoặc Không | 200 | Khôi phục toàn bộ editable cells về 0 theo đề bài gốc. |
| `POST` | `/game/load` | `{"test_id": str, "difficulty": str, "board": int[9][9]}` | 200 / 400 | Nạp puzzle mới, tính lại fixed mask và sinh game_id mới. |
| `PUT` | `/game/state` | `{"board": int[9][9]}` | 200 / 400 | Đồng bộ toàn bộ ma trận editable từ snapshot của Solver B. |

---

## 4. Chi Tiết Từng Endpoint

### 4.1. `GET /health`
Kiểm tra service A có đang hoạt động và sẵn sàng nhận kết nối.

- **Request:** Không có body.
- **Response 200 (OK):**
  ```json
  {
    "success": true,
    "service": "sudoku-game",
    "version": "1.0"
  }
  ```

---

### 4.2. `GET /game/state`
Lấy toàn bộ snapshot dữ liệu bàn cờ hiện tại. Được frontend polling mỗi 350ms và được Program B gọi trước khi bắt đầu giải.

- **Request:** Không có body.
- **Response 200 (OK):**
  ```json
  {
    "success": true,
    "game_id": "game-7f3b8a1c",
    "test_id": "medium_01",
    "difficulty": "medium",
    "board": [
      [5, 3, 0, 0, 7, 0, 0, 0, 0],
      [6, 0, 0, 1, 9, 5, 0, 0, 0],
      [0, 9, 8, 0, 0, 0, 0, 6, 0],
      [8, 0, 0, 0, 6, 0, 0, 0, 3],
      [4, 0, 0, 8, 0, 3, 0, 0, 1],
      [7, 0, 0, 0, 2, 0, 0, 0, 6],
      [0, 6, 0, 0, 0, 0, 2, 8, 0],
      [0, 0, 0, 4, 1, 9, 0, 0, 5],
      [0, 0, 0, 0, 8, 0, 0, 7, 9]
    ],
    "fixed": [
      [true,  true,  false, false, true,  false, false, false, false],
      [true,  false, false, true,  true,  true,  false, false, false],
      [false, true,  true,  false, false, false, false, true,  false],
      [true,  false, false, false, true,  false, false, false, true],
      [true,  false, false, true,  false, true,  false, false, true],
      [true,  false, false, false, true,  false, false, false, true],
      [false, true,  false, false, false, false, true,  true,  false],
      [false, false, false, true,  true,  true,  false, false, true],
      [false, false, false, false, true,  false, false, true,  true]
    ],
    "fixed_mask": [
      [true,  true,  false, false, true,  false, false, false, false],
      [true,  false, false, true,  true,  true,  false, false, false],
      [false, true,  true,  false, false, false, false, true,  false],
      [true,  false, false, false, true,  false, false, false, true],
      [true,  false, false, true,  false, true,  false, false, true],
      [true,  false, false, false, true,  false, false, false, true],
      [false, true,  false, false, false, false, true,  true,  false],
      [false, false, false, true,  true,  true,  false, false, true],
      [false, false, false, false, true,  false, false, true,  true]
    ],
    "status": "PLAYING",
    "empty_cells": 51,
    "conflicts": []
  }
  ```

---

### 4.3. `GET /game/status`
Lấy thông tin trạng thái rút gọn (dùng để kiểm tra nhanh tiến trình).

- **Request:** Không có body.
- **Response 200 (OK):**
  ```json
  {
    "success": true,
    "status": "PLAYING",
    "empty_cells": 51,
    "conflict_count": 0
  }
  ```

---

### 4.4. `POST /game/move`
Gán một giá trị vào ô editable $(x, y)$. Hỗ trợ cả key `num` và `value`.

- **Request Body:**
  ```json
  {
    "x": 0,
    "y": 2,
    "num": 4
  }
  ```
- **Response 200 (Move Hợp lệ - Không xung đột):**
  ```json
  {
    "success": true,
    "status": "PLAYING",
    "empty_cells": 50,
    "conflict_count": 0,
    "conflicts": []
  }
  ```
- **Response 200 (Move Xung đột - Phục vụ Local Search / Min-Conflicts):**
  ```json
  {
    "success": true,
    "status": "CONFLICT",
    "empty_cells": 50,
    "conflict_count": 2,
    "conflicts": [
      {"x": 0, "y": 0},
      {"x": 0, "y": 2}
    ]
  }
  ```
- **Response 400 (Lỗi cố tình sửa ô Fixed):**
  ```json
  {
    "success": false,
    "error": "FIXED_CELL",
    "message": "Cell (0, 0) is a fixed clue and cannot be changed"
  }
  ```

---

### 4.5. `POST /game/clear`
Xóa một ô editable về giá trị 0 (được gọi khi solver Backtrack hoặc người chơi xóa ô).

- **Request Body:**
  ```json
  {
    "x": 0,
    "y": 2
  }
  ```
- **Response 200 (OK):**
  ```json
  {
    "success": true,
    "status": "PLAYING",
    "empty_cells": 51,
    "conflict_count": 0
  }
  ```
- **Response 400 (Lỗi xóa ô Fixed):**
  ```json
  {
    "success": false,
    "error": "FIXED_CELL",
    "message": "Cell (0, 0) is a fixed clue and cannot be cleared"
  }
  ```

---

### 4.6. `POST /game/reset`
Khôi phục toàn bộ bàn cờ về puzzle ban đầu (xóa sạch toàn bộ các ô editable đã điền).

- **Request Body:** `{}` hoặc rỗng.
- **Response 200 (OK):** Trả về toàn bộ Full State (cấu trúc tương tự `GET /game/state`).

---

### 4.7. `POST /game/load`
Nạp một puzzle Sudoku mới vào trò chơi. Hệ thống sẽ tính lại fixed mask và sinh `game_id` mới. Hỗ trợ cả key `test_id` và `id`.

- **Request Body:**
  ```json
  {
    "test_id": "hard_05",
    "difficulty": "hard",
    "board": [
      [0, 0, 0, 2, 6, 0, 7, 0, 1],
      [6, 8, 0, 0, 7, 0, 0, 9, 0],
      [1, 9, 0, 0, 0, 4, 5, 0, 0],
      [8, 2, 0, 1, 0, 0, 0, 4, 0],
      [0, 0, 4, 6, 0, 2, 9, 0, 0],
      [0, 5, 0, 0, 0, 3, 0, 2, 8],
      [0, 0, 9, 3, 0, 0, 0, 7, 4],
      [0, 4, 0, 0, 5, 0, 0, 3, 6],
      [7, 0, 3, 0, 1, 8, 0, 0, 0]
    ]
  }
  ```
- **Response 200 (OK):** Trả về Full State mới với `status: "PLAYING"`.
- **Response 400 (Bad Request):** `INVALID_BOARD` nếu puzzle ban đầu sai định dạng hoặc chứa xung đột sẵn.

---

### 4.8. `PUT /game/state`
Đồng bộ toàn bộ ma trận bàn cờ từ snapshot của Solver B (dùng cho thuật toán Min-Conflicts khi thay đổi nhiều ô cùng lúc hoặc khi rollback bằng Previous).

- **Request Body:**
  ```json
  {
    "board": [
      [5, 3, 4, 6, 7, 8, 9, 1, 2],
      [6, 7, 2, 1, 9, 5, 3, 4, 8],
      "... (ma trận 9x9 đầy đủ)"
    ]
  }
  ```
- **Quy tắc kiểm tra:**
  - Mọi ô có `fixed == True` phải giữ nguyên giá trị đề bài ban đầu.
  - Các ô editable được phép chứa giá trị xung đột (conflict).
- **Response 200 (OK):** Trả về Full State sau khi cập nhật.
- **Response 400 (Fixed Modified):** Nếu có bất kỳ ô fixed nào bị thay đổi giá trị so với đề bài $\rightarrow$ ném lỗi `FIXED_CELL`.

---

## 5. Cấu Trúc Response & Danh Mục Mã Lỗi (Error Codes)

### 5.1. Định Dạng Chuẩn
- **Thành công (HTTP 200):**
  ```json
  {
    "success": true,
    "...": "dữ liệu tương ứng của endpoint"
  }
  ```
- **Thất bại (HTTP 400 / 404):**
  ```json
  {
    "success": false,
    "error": "<ERROR_CODE>",
    "message": "<Mô tả chi tiết nguyên nhân lỗi>"
  }
  ```

### 5.2. Danh Mục Mã Lỗi Ổn Định

| HTTP Status | Mã lỗi (`error`) | Nguyên nhân kích hoạt |
|:---:|---|---|
| `400` | `INVALID_JSON` | Body request không thể parse JSON hoặc không phải JSON object. |
| `400` | `INVALID_BOARD` | Ma trận bàn cờ không đúng 9×9, sai kiểu dữ liệu, chứa giá trị ngoài $0..9$, hoặc có xung đột ban đầu khi `load`. |
| `400` | `INVALID_COORDINATE` | Tọa độ `x` hoặc `y` không phải kiểu nguyên hoặc nằm ngoài phạm vi $0..8$. |
| `400` | `INVALID_VALUE` | Giá trị `num` / `value` không phải số nguyên hoặc nằm ngoài phạm vi $1..9$. |
| `400` | `FIXED_CELL` | Thao tác `move`, `clear` hoặc `replace` cố tình thay đổi giá trị của ô đề bài cố định. |
| `404` | `NOT_FOUND` | Gọi sai đường dẫn URL không thuộc danh mục API v1 đã công bố. |

---

## 6. Ranh Giới Tích Hợp giữa Program A và Program B

> [!CAUTION]
> **Boundary Rule Bắt buộc:** Program B **tuyệt đối không được** import module của Program A hoặc truy cập trực tiếp vào bộ nhớ tiến trình A. Mọi tương tác bắt buộc phải qua HTTP REST API.

**Hành động hợp lệ (B thực hiện):**
- Khởi tạo HTTP GameClient trỏ tới `http://127.0.0.1:8000/api/v1`.
- Gọi `GET /game/state` để đọc bàn cờ ban đầu và fixed mask.
- Gửi `POST /game/move` hoặc `POST /game/clear` theo từng tick (Backtracking / MRV).
- Gửi `PUT /game/state` khi chạy Min-Conflicts snapshot hoặc khi thực hiện Previous.
- Bắt `APIError` (HTTP 400) để xử lý ngoại lệ an toàn.

**Hành động bị cấm:**
- Import bất kỳ file `.py` nào của Program A (`game.py`, `app.py`).
- Đọc/ghi trực tiếp vào biến nội bộ của Program A.
- Yêu cầu Program A cung cấp lời giải (solution).
