# Session: Data Structures — 2026-05-07
- Cấp độ: Senior
- Thời gian dự kiến: 60 phút
- Chủ đề: Data Structures

## Khung thời gian
| Phần | Thời gian |
|------|-----------|
| Warm-up | 5 phút |
| Core (Medium → Hard) | 35 phút |
| Deep dive / Trade-off | 15 phút |
| Wrap-up | 5 phút |

---

## Q1 (Warm-up)
**Câu hỏi:** Giải thích sự khác biệt giữa `dict` trong CPython 3.7+ và một hash table truyền thống. Vì sao Python dict lại preserve insertion order trong khi vẫn đảm bảo O(1) lookup?

**Trả lời của bạn:**
Hash table kiểu truyền thống có một storage bucket để các index sau khi hash giá trị. hash("name", "khoa") = 3 thì lưu ở index 3, các index của vẫn empty. nên khi lấy data là O(1). Với dict, python chia ra làm 2 storage. Indices table và Entries table. Table Indices lưu insertion order, table còn lại dựa trên index để lưu bucket data ("name", "khoa"). Khi lookup chỉ cần hash key -> Index tìm trong index entries table sẽ lookup là đc với O(1)

**Đã dùng /hint:** Có (-2 điểm khi chấm)

**Feedback:**

**Điểm:** /10
