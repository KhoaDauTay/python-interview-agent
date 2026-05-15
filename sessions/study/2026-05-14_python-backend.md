# Session: Python/Backend — 2026-05-14
**Level:** Mixed | **Mode:** Study
**Topics covered:** Async/Celery, REST API, Database, OLAP & Time-series DB

---

## PART 1: Async/Celery

### Event Loop
- Vòng lặp vô hạn cho phép 1 thread xử lý hàng nghìn connections đồng thời
- Khi task chờ I/O → "park" nó, chạy task khác
- Analogy: đầu bếp không đứng chờ nước sôi mà đi làm việc khác

### async/await vs Threading vs Multiprocessing

| Aspect | async/await | Threading | Multiprocessing |
|--------|-------------|-----------|-----------------|
| Concurrency | Cooperative | Preemptive | True parallelism |
| GIL | No issue | Blocked cho CPU | Bypasses GIL |
| Memory | ~KB/task | ~MB/thread | ~MB/process |
| Best for | I/O-bound | I/O-bound | CPU-bound |

### Celery Architecture
```
[Client/API] → push → [Broker: Redis/RabbitMQ] → pull → [Workers] → store → [Result Backend]
```
- **Broker**: Redis (simple/fast) vs RabbitMQ (robust, complex routing)
- **Worker pools**: prefork (multiprocessing), eventlet/gevent (async I/O)
- **Result Backend**: optional, chỉ cần khi client query kết quả

### BackgroundTasks vs Celery

| Criteria | BackgroundTasks | Celery |
|----------|-----------------|--------|
| Duration | < 30s | Any |
| Retry | No | Yes |
| Persistence | No (lost on crash) | Yes |
| Setup | Zero | Medium |

Rule: task **must not be lost** → Celery. Logging, simple cleanup → BackgroundTasks.

### Celery Beat — Vấn đề thực tế (KHÔNG phải 2 Beat instances — hiếm gặp, waste resource)

**1. Task Timeout + Retry Overlap**
- Task chạy lâu hơn interval → Beat schedule task mới trong khi task cũ vẫn chạy
- Fix: distributed lock hoặc `expires` option

```python
@app.task(bind=True)
def daily_report(self):
    lock_key = "lock:daily_report"
    if not redis.set(lock_key, 1, nx=True, ex=600):
        return "Skipped — previous run still active"
    try:
        pass  # logic
    finally:
        redis.delete(lock_key)
```

**2. Task không Idempotent**
- Task chạy 2 lần (bất kỳ lý do) → duplicate records, double charge
- Fix: guard clause + row lock

```python
@app.task
def charge_user(order_id: int):
    with transaction.atomic():
        order = Order.objects.select_for_update().get(id=order_id)
        if order.status == "paid":
            return "Already processed"
        payment_gateway.charge(order.total)
        order.status = "paid"
        order.save()
```

**3. Beat Drift/Missed Tasks sau Crash**
- Mặc định: sau restart Beat bỏ qua tất cả tasks bị missed
- Fix: `django-celery-beat` lưu schedule vào DB

**4. Clock Skew**
- Servers khác nhau có giờ lệch vài giây → monitoring/alerting confusion
- Fix: luôn dùng UTC + NTP sync

---

## PART 2: REST API

### HTTP Methods & Idempotency

| Method | Idempotent? | Dùng khi |
|--------|-------------|---------|
| GET | Có | Đọc data |
| POST | Không | Tạo mới |
| PUT | Có | Replace toàn bộ |
| PATCH | Không* | Update một phần |
| DELETE | Có | Xóa |

### Status Codes
```
200 OK, 201 Created, 204 No Content
400 Bad Request, 401 Unauthenticated, 403 Unauthorized, 404 Not Found
409 Conflict, 422 Validation Error (FastAPI default), 500 Internal
```
**Hay nhầm:** 401 = "không biết bạn là ai", 403 = "biết nhưng không có quyền"

### RESTful Naming
```
GET    /api/v1/documents          → list
POST   /api/v1/documents          → create
GET    /api/v1/documents/{id}     → get one
PUT    /api/v1/documents/{id}     → full update
PATCH  /api/v1/documents/{id}     → partial update
DELETE /api/v1/documents/{id}     → delete
```
Dùng **noun**, không dùng verb. Luôn prefix `/api/v1/`.

### FastAPI Dependency Injection
```python
async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session  # Session tự đóng sau request

async def get_current_user(token = Depends(oauth2_scheme), db = Depends(get_db)):
    user = await validate_token(token, db)
    if not user:
        raise HTTPException(401)
    return user
```

**Middleware vs Dependency:**
| | Middleware | Dependency |
|--|-----------|------------|
| Scope | Tất cả requests | Chỉ routes dùng nó |
| Dùng cho | Logging, CORS, rate limit | Auth, DB session |

### JWT Flow
1. Login → server trả `access_token` (ngắn hạn) + `refresh_token` (dài hạn)
2. Request → Header `Authorization: Bearer <token>`
3. Hết hạn → dùng `refresh_token` lấy `access_token` mới

JWT payload không được encrypt, chỉ được sign. Casbin xử lý "được làm gì", JWT xử lý "là ai".

### Consistent Error Response
```python
@app.exception_handler(AppError)
async def handler(request, exc: AppError):
    return JSONResponse(status_code=exc.status,
        content={"error": {"code": exc.code, "message": exc.message}})
```

---

## PART 3: Database

### ACID
- **Atomicity**: all or nothing — transaction rollback nếu bất kỳ bước nào fail
- **Consistency**: DB từ trạng thái hợp lệ → trạng thái hợp lệ, constraints không vi phạm
- **Isolation**: transactions song song không thấy kết quả của nhau cho đến khi commit
- **Durability**: sau commit, data tồn tại dù server crash (PostgreSQL dùng WAL)

**Isolation levels:**
| Level | Dirty Read | Non-repeatable Read | Phantom Read |
|-------|-----------|---------------------|--------------|
| Read Committed (default) | Không | Có | Có |
| Repeatable Read | Không | Không | Có |
| Serializable | Không | Không | Không |

### Indexing
- B-tree index: O(log n) thay vì O(n) full scan
- **Nên thêm:** WHERE/JOIN/ORDER BY columns, foreign keys, high cardinality columns
- **Không nên:** low cardinality (boolean), bảng nhỏ < 10k rows, column hay UPDATE
- **Composite index:** thứ tự quan trọng — `(user_id, created_at)` không dùng được nếu chỉ filter `created_at`
- Tool: `EXPLAIN ANALYZE` — thấy "Seq Scan" → cần index

### N+1 Problem
```python
# BAD: 1 + N queries
docs = Document.objects.all()
for doc in docs: print(doc.author.name)

# GOOD Django: 1 query với JOIN
docs = Document.objects.select_related('author').all()

# GOOD SQLAlchemy
result = await db.execute(select(Document).options(joinedload(Document.author)))
```
Rule: thấy vòng lặp truy cập relationship → nghi ngờ N+1 ngay.

### Connection Pooling
- Tạo sẵn N connections, tái sử dụng — tránh overhead tạo connection mới mỗi request
- **Formula:** `pool_size = (2 × CPU cores) + 1`
- asyncpg (async) nhanh hơn psycopg2 (sync) ~3x, dùng với FastAPI async

### Caching Strategies
- **Cache-aside** (lazy): check cache → miss → query DB → set cache
- **Write-through**: update cache đồng thời khi write DB
- **Write-behind**: write cache trước, async flush DB sau (nhanh nhất, nguy cơ mất data)

**Cache Stampede:** Cache hết hạn → N requests cùng lúc miss → N queries DB
Fix: mutex lock khi set cache (chỉ 1 request vào DB, các request khác đợi)

### ClickHouse (Sidecardata)
- OLAP, columnar storage — tốt cho analytics/aggregate trên billions rows
- **ReplacingMergeTree**: deduplication async, cần `FINAL` để đảm bảo dedup khi query

---

## PART 4: OLAP & Time-series DB (bonus)

### OLTP vs OLAP

| | OLTP | OLAP |
|--|------|------|
| Query | "User 42 có order nào?" | "Doanh thu tháng 3 theo tỉnh?" |
| Rows/query | 1-100 | Triệu đến tỷ |
| Write | Liên tục, từng row | Batch |
| DB | PostgreSQL, MySQL | ClickHouse, BigQuery |

### Tại sao Columnar nhanh hơn cho Analytics
- Row-based: query 2 columns nhưng phải đọc toàn bộ row
- Columnar: chỉ đọc đúng columns cần → 10-100x nhanh hơn cho aggregation
- Compress tốt hơn vì cùng kiểu data nằm liền nhau

### Time-series DB
- Subtype của OLAP — tối ưu cho data có timestamp, append-only, query theo time range
- Hay cần downsampling: average mỗi 5 phút thay vì từng giây

| DB | Dùng cho |
|----|----------|
| InfluxDB | Metrics, IoT |
| TimescaleDB | Metrics + SQL quen thuộc (PostgreSQL extension) |
| Prometheus | Infrastructure metrics, pull-based, không long-term storage |
| ClickHouse | Analytics + time-series versatile |

**TimescaleDB** tự động partition bảng thành **chunks** theo thời gian → query chỉ đọc chunks liên quan, bỏ qua phần còn lại.

**Tại sao không dùng PostgreSQL cho time-series ở scale lớn:**
- Write amplification cao (row + indexes + WAL)
- Table bloat khi data cũ không delete
- Không có built-in downsampling

**Liên kết CV:**
- Sidecardata dùng ClickHouse cho analytics/events (append-only, aggregate trên time range)
- Atrix AI dùng Grafana → query time-series backend (Prometheus/InfluxDB)
