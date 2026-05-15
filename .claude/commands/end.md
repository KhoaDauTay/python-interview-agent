# /end — Kết thúc phiên ôn tập

Thực hiện trực tiếp (KHÔNG spawn Teacher agent):

**BƯỚC 1 — Tìm session file hôm nay:**
- Glob `sessions/interview/` tìm file có tên bắt đầu bằng `currentDate` từ context
- Nếu không có file hôm nay, lấy file được sửa gần nhất trong `sessions/interview/`

**BƯỚC 2 — Đọc session file**, phân tích:
- Đếm số câu Q đã làm (tìm pattern `## Q<n>:`)
- Tính điểm trung bình (tìm pattern `**Điểm:** X/10`)
- Tổng hợp điểm mạnh và điểm yếu từ các Feedback section

**BƯỚC 3 — Append tổng kết vào cuối session file:**

```
---
## TỔNG KẾT PHIÊN
**Kết thúc:** {DATE}
**Số câu đã làm:** X
**Điểm trung bình:** X.X/10

### Điểm mạnh
- [rút ra từ các câu điểm ≥ 7]

### Cần cải thiện
- [rút ra từ các câu điểm < 7 và thiếu sót trong feedback]

### Tiếp theo nên ôn
- [2-3 topic/concept cụ thể dựa trên kết quả phiên này]
```

**BƯỚC 4 — Hiển thị tổng kết ra màn hình** (giống format trên).

**BƯỚC 5 — In lời chúc** kết thúc phiên ngắn gọn.

$ARGUMENTS
