# WorldQuant Interview Prep — Đề cương tổng hợp

> Folder này dành riêng cho phỏng vấn **Software Engineer tại WorldQuant** — quant hedge fund, khác hoàn toàn với AI company thông thường.

---

## WorldQuant cần gì?

```
"Intellectual horsepower first and foremost"
— Không có roadmap, cần người tự build nó.
```

**Core focus của role:**
- Xây **data pipelines** cho financial market data (không phải user-facing product)
- Xây **computational frameworks** chạy quant strategies ở scale
- **Phục vụ quant researchers** — turn ideas thành production systems
- **Python ở mức expert** — hiểu performance, concurrency, memory

---

## Interview Format (dự đoán)

| Round | Nội dung | Chuẩn bị |
|-------|----------|----------|
| Round 1 | Coding — LeetCode Medium/Hard | `01-dsa-full.md` |
| Round 2 | System Design | `03-data-pipeline-quant.md` + `topics/senior/14-system-design-ai.md` (Design 6) |
| Round 3 | Python Deep Dive | `02-python-performance.md` + `topics/senior/06-python-advanced.md` (Phần 4) |
| Round 4 | Technical Discussion | Tất cả files bên dưới |

---

## Files trong folder này

| File | Nội dung | Ưu tiên |
|------|----------|---------|
| `01-dsa-full.md` | DSA full: Arrays → Graphs → DP. Lý thuyết + template + code | **MUST** |
| `02-python-performance.md` | GIL, NumPy, Pandas, multiprocessing, profiling | **MUST** |
| `03-data-pipeline-quant.md` | Financial data: OHLCV, corporate actions, ClickHouse, ETL | **HIGH** |

---

## Files trong `topics/senior/` cũng cần đọc

| File | Section liên quan |
|------|------------------|
| `06-python-advanced.md` | **Phần 4** (Python Performance mới thêm) + Phần 1 (asyncio) |
| `14-system-design-ai.md` | **Design 6** (Financial Data Pipeline) + Temporal section |
| `13-monitoring-cicd.md` | CI/CD — JD đề cập rõ |
| `12-fastapi-backend.md` | Async patterns, Celery, background jobs |

---

## Key concepts WorldQuant phỏng vấn sẽ hỏi

### Must know trước khi vào phòng

**DSA:**
- Two pointers, sliding window, prefix sum
- HashMap patterns (two sum, grouping, frequency count)
- BFS/DFS trên graphs
- Dynamic Programming: bottom-up tabulation
- Binary search variants

**Python:**
- GIL và khi nào nó là vấn đề
- `ProcessPoolExecutor` cho CPU-bound quant computation
- NumPy vectorization (tại sao không dùng Python loop)
- Pandas memory optimization (dtypes, chunking)

**System Design:**
- Data pipeline: ingest → validate → store → serve
- Point-in-time correctness (look-ahead bias)
- Corporate action adjustment (splits, dividends)
- ClickHouse vs TimescaleDB tradeoffs
- Batch vs streaming cho market data

**Domain basics** (không cần deep, chỉ cần communicate với researchers):
- OHLCV = Open, High, Low, Close, Volume
- Alpha = predictive signal cho market returns
- Backtesting = test strategy trên historical data
- Sharpe ratio = return / risk (higher = better)
- Look-ahead bias = dùng data chưa có tại thời điểm giao dịch → invalid backtest

---

## Câu hỏi behavioral WorldQuant hay hỏi

1. *"Tell me about a time you improved the performance of a data pipeline significantly."*
2. *"Describe a complex system you built from scratch. What would you do differently?"*
3. *"How do you work with researchers/data scientists who are not engineers?"*
4. *"How do you handle a situation where the data you're getting is inconsistent or corrupted?"*
5. *"We value intellectual curiosity — what's a technical problem you explored out of pure interest recently?"*

---

## Lộ trình ôn nhanh (nếu phỏng vấn trong 1-2 ngày)

```
Day 1 (sáng): 01-dsa-full.md → Arrays, HashMap, Two Pointers, Stack
Day 1 (chiều): 01-dsa-full.md → Trees, Graphs, DP basics
Day 1 (tối): 02-python-performance.md → GIL, multiprocessing, NumPy

Day 2 (sáng): 03-data-pipeline-quant.md toàn bộ
Day 2 (chiều): topics/senior/14 → Design 6 (Financial Pipeline)
Day 2 (tối): Mock interview coding + system design
```
