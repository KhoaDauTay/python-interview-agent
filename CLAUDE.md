# Interview Prep — Claude Code Project

## Mục tiêu
Dự án này dùng để **ôn luyện phỏng vấn kỹ thuật** từ đầu đến cuối, với Teacher agent đóng vai người phỏng vấn/giáo viên.

## Cách dùng nhanh
1. Chạy `/start` → Teacher sẽ hỏi bạn muốn ôn chủ đề gì
2. Chạy `/topic <tên>` → nhảy thẳng vào chủ đề cụ thể
3. Chạy `/hint` → xin gợi ý khi bí
4. Chạy `/answer` → xem đáp án mẫu + giải thích
5. Chạy `/evaluate` → Teacher chấm điểm câu trả lời vừa rồi
6. Chạy `/progress` → xem tiến độ ôn tập

## Nguyên tắc hoạt động
- Mọi câu hỏi đều có **3 cấp độ**: Easy → Medium → Hard
- Teacher sẽ **không tự lộ đáp án** trừ khi bạn gõ `/answer`
- Sau mỗi câu trả lời, Teacher **luôn cho feedback** rõ ràng
- Trả lời bằng **tiếng Việt** hoặc **tiếng Anh** đều được
- Session được lưu vào `sessions/` để review lại

## Chủ đề có sẵn
| File | Chủ đề |
|------|--------|
| `topics/01-data-structures.md` | Data Structures |
| `topics/02-algorithms.md` | Algorithms & Complexity |
| `topics/03-python-backend.md` | Python / FastAPI / Backend |
| `topics/04-system-design.md` | System Design |
| `topics/05-behavioral.md` | Behavioral (STAR method) |

## Quy ước session file
Mỗi phiên ôn tập lưu tại `sessions/YYYY-MM-DD_<topic>.md` với format:
```
# Session: <topic> — <date>
## Q1: <câu hỏi>
**Trả lời của bạn:** ...
**Feedback:** ...
**Điểm:** x/10
```
