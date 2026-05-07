# /progress — Xem tiến độ ôn tập

Hiển thị tổng kết toàn bộ quá trình ôn luyện.

Teacher sẽ đọc tất cả file trong `sessions/` và `progress.json` để tổng hợp:

```
📈 TIẾN ĐỘ ÔN TẬP
──────────────────────────────
Tổng số session: X
Tổng câu đã luyện: X câu

📚 Theo chủ đề:
  Data Structures : ██████░░░░ 60% (12/20 câu)
  Algorithms      : ████░░░░░░ 40% (8/20 câu)
  Python/Backend  : ███████░░░ 70% (14/20 câu)
  System Design   : ██░░░░░░░░ 20% (4/20 câu)
  Behavioral      : █████░░░░░ 50% (5/10 câu)

🏆 Điểm trung bình: X.X/10

💪 Điểm mạnh:
  - [topic/skill]

🎯 Cần tập trung thêm:
  - [topic/skill]

📅 Session gần nhất: YYYY-MM-DD
```

Nếu `$ARGUMENTS` có "session" (ví dụ: `/progress session`), chỉ tổng kết session hiện tại.

$ARGUMENTS
