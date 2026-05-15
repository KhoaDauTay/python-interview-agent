# Session: Async & Distributed Systems — 2026-05-13
**Level:** Mid | **Mode:** Study (không quiz, không chấm điểm)
**Topics covered:** Python OOP → Async → FastAPI internals → Distributed Lock → Temporal → Design Patterns

---

## PART 1: Python OOP

### 4 Nguyên tắc OOP
| Principle | Mô tả | Analogy |
|-----------|-------|---------|
| **Encapsulation** | Ẩn data, expose qua methods | Tủ thuốc có khóa |
| **Inheritance** | Class con thừa hưởng class cha | Gen di truyền |
| **Polymorphism** | Cùng interface, hành vi khác nhau | Nút Play trên remote |
| **Abstraction** | Ẩn complexity, expose interface | Lái xe không cần biết động cơ |

### `_var` vs `__var` vs `__var__`
| Cú pháp | Ý nghĩa | Enforce? |
|---------|---------|---------|
| `_var` | Protected — convention | ❌ chỉ là tín hiệu |
| `__var` | Name mangling → `_ClassName__var` | ✅ Python đổi tên |
| `__var__` | Dunder/magic method | Không phải private! |

### `@property` và `@abstractmethod`
- `@property` = getter trông như attribute, có thể thêm `@x.setter` để validate
- `@abstractmethod` = subclass BẮT BUỘC implement, không thể instantiate ABC trực tiếp
- **CV link:** RAG pipeline base classes ở Spartan = abstract class thực tế

---

## PART 2: Async/Await — Cơ chế cốt lõi

### Event Loop là gì?
- **1 thread duy nhất** chạy nhiều coroutines
- Khi gặp `await` → coroutine nhường quyền → event loop chạy coroutine khác
- CPU = 0% khi tất cả coroutines đang chờ I/O (dùng `epoll`/`kqueue`)

### Tại sao async chỉ hợp với I/O, không phải CPU?
```
I/O-bound: CPU nhàn rỗi trong lúc chờ mạng/disk → async tận dụng thời gian đó
CPU-bound: CPU chạy 100% liên tục, không có await → event loop bị BLOCK hoàn toàn
```

### ProcessPool vs ThreadPool vs Celery
| | ThreadPool | ProcessPool | Celery |
|--|-----------|-------------|--------|
| Bypass GIL? | ❌ | ✅ | ✅ |
| Dùng cho | I/O blocking sync | CPU-bound | Long-running / distributed |
| Survive crash | ❌ | ❌ | ✅ (broker lưu) |

### GIL hoạt động thế nào?
- GIL = 1 lock toàn cục trong CPython, chỉ 1 thread cầm GIL tại 1 thời điểm
- Khi thread chờ I/O (syscall) → Python **tự động release GIL** → thread khác chạy
- CPU-bound → GIL không release → các threads tranh nhau → chậm hơn 1 thread

---

## PART 3: FastAPI Async Internals

### ASGI — Nền tảng của FastAPI
```
Client → Uvicorn (ASGI server + uvloop) → Starlette (routing + middleware) → Your endpoint
```

### `async def` vs `def` endpoint
```
async def → chạy trực tiếp trên event loop → zero overhead
def       → FastAPI wrap trong anyio.to_thread.run_sync() → separate thread
```

### DANGER: Blocking trong `async def`
```
requests.get() trong async def → BLOCK event loop → tất cả requests khác freeze
Fix: dùng httpx (async), hoặc run_in_executor(), hoặc dùng def endpoint
```

### Request lifecycle
```
TCP arrive → HTTP parse → Middleware chain → DI resolve → Endpoint → Cleanup (yield deps)
```

### Background Tasks
- Chạy SAU khi response đã sent, trên cùng event loop
- Giới hạn: cùng process → server restart → mất task
- Celery tốt hơn cho long-running vì broker persist task

---

## PART 4: asyncio.Lock & Distributed Lock

### asyncio primitives
| Primitive | Dùng khi |
|-----------|---------|
| `asyncio.Lock` | 1 coroutine vào critical section |
| `asyncio.Semaphore` | N coroutines đồng thời (rate limiting) |
| `asyncio.Event` | Signal "sự kiện đã xảy ra" |
| `asyncio.Queue` | Producer/consumer pattern |

### Tại sao cần Distributed Lock?
- `asyncio.Lock` chỉ trong 1 process
- Nhiều servers → không biết nhau → cần external coordinator (Redis)

### Redis Distributed Lock — cơ chế
```
SET key value NX EX 30
  NX = chỉ set nếu key CHƯA tồn tại (atomic)
  EX = tự expire sau 30s (phòng crash không release)
Release: dùng Lua script để atomic check-and-delete (tránh xóa nhầm lock người khác)
```

### GC Pause Problem — vấn đề không có giải pháp hoàn hảo
```
Process bị suspend hoàn toàn (kể cả watchdog)
→ TTL expired → người khác acquire lock → 2 workers trong critical section
```

**Giải pháp:**
| Giải pháp | GC Pause safe? | Khi dùng |
|-----------|---------------|---------|
| TTL lớn + Watchdog | Partial | Task < TTL/3 |
| Fencing Token | ✅ | Storage support version |
| Idempotency | ✅ | **Best practice mọi lúc** |
| Temporal/Saga | ✅ | Long-running workflows |

### Fencing Token — giải pháp đúng về lý thuyết
```
Mỗi lock acquire → nhận token tăng dần (33, 34, 35...)
Resource server reject request có token <= token đã xử lý
GC pause → lock expired → C2 nhận token 34 → C1 resume với token 33 → REJECTED
```

### Performance Lock vs Correctness Lock
```
Performance: Race xảy ra → hơi lãng phí, nhưng data vẫn đúng
             → Redis NX đủ (cache stampede, rate limit, pipeline duplicate)

Correctness: Race xảy ra → data sai, tiền mất
             → Cần Fencing Token + resource validation
             → Hoặc Optimistic Lock (version column) + Idempotency
             (payment deduction, inventory management)
```

**Martin Kleppmann:** *"If you need distributed locks for correctness, the only safe solution is fencing tokens + resource-side validation."*

---

## PART 5: Temporal → Design Patterns Map

### Map
```
Temporal Concept          →  Underlying Pattern
─────────────────────────────────────────────────
Durable State             →  Event Sourcing
Automatic Retry           →  Retry Pattern + Circuit Breaker
Exactly-once execution    →  Idempotency Key + Outbox Pattern
Durable Timers            →  Persistent Scheduler Pattern
Workflow orchestration    →  Saga Pattern (Orchestration)
Activity isolation        →  Command Pattern
Determinism constraint    →  Pure Function / Side-effect isolation
```

### 1. Event Sourcing
- Lưu events (đã xảy ra gì), không lưu state (đang là gì)
- Events: Immutable + Ordered + Complete
- Crash → load events → rebuild state → resume
- Giống sổ kế toán — chỉ thêm dòng, không xóa

### 2. Retry Pattern + Circuit Breaker
- **Retry:** Exponential backoff + jitter, phân biệt retryable vs non-retryable
- **Circuit Breaker:** CLOSED → OPEN (fail fast) → HALF_OPEN (test recovery)
- Retry = kiên nhẫn với lỗi nhỏ. Circuit Breaker = biết dừng khi hệ thống sập

### 3. Idempotency Key + Outbox Pattern
- **Idempotency:** Client gửi key, server check đã xử lý chưa → skip nếu rồi
- **Outbox:** Write DB + event trong 1 transaction → background relay publish
- Đảm bảo: event không bao giờ mất, không bao giờ duplicate

### 4. Persistent Scheduler
- Timer = data trong DB, không phải in-memory
- Process tắt → timer vẫn còn → restart → tiếp tục
- Components: Timer Store + Scheduler (polling) + Executor

### 5. Saga Pattern (Orchestration)
- Central orchestrator biết toàn bộ flow (như nhạc trưởng)
- Failure → chạy compensating transactions ngược lại
- Compensating transaction phải idempotent
- **vs Choreography:** Event-driven, không có central coordinator (khó debug hơn)

### 6. Command Pattern
- Đóng gói 1 operation thành unit độc lập (input/output rõ ràng)
- Retry/test/distribute từng command riêng lẻ
- Không biết context xung quanh → loosely coupled

### 7. Pure Function / Side-effect Isolation
- Pure function: f(x) luôn = y với cùng x, không side effects
- Tách "logic điều phối" (pure) khỏi "side effects" (impure)
- Deterministic → có thể replay

---

## PART 6: Core Knowledge Design Flow

### 3 Trụ cột CS
```
MEMORY + PROCESS/THREAD + NETWORK
→ Mọi vấn đề distributed system đều bắt nguồn từ đây
```

### Dependency Learning Order
```
OS Fundamentals (process/thread/memory/IO)
    ↓
Concurrency + Async + Networking
    ↓
Distributed Problems (failure/latency/partial failure)
    ↓
Reliability + Consistency + Scalability patterns
    ↓
System Design (Temporal/Kafka/Microservices = bundle of patterns)
```

### 3 Câu hỏi khi đọc bất kỳ pattern nào
```
1. WHAT CAN FAIL?      → Vấn đề gì đang được giải quyết?
2. WHAT IS THE TRADE-OFF? → Đánh đổi gì lấy gì?
3. WHAT ARE THE BOUNDARIES? → Khi nào dùng, khi nào không?
```

### Core Insight
```
Không có pattern nào mới được phát minh sau năm 1990.
Temporal, Kafka, Kubernetes = các patterns cũ được implement tốt hơn.
Hiểu patterns → không bao giờ bị lock-in vào 1 tool cụ thể.
```

---

## CV Links Summary (Khoa)
| Project | Concept | Chi tiết |
|---------|---------|---------|
| Spartan | Temporal + Event Sourcing | 10,000+ doc batches, retry/heartbeat |
| Spartan | Abstract class | RAG pipeline base classes |
| Atrix AI | Celery + BackgroundTasks | LLM inference offload |
| Atrix AI | Semaphore | Rate limit OpenAI API calls |
| Sidecardata | Distributed Lock | Celery Beat duplicate fix (87%→99%+) |
| Sidecardata | N+1 / Index | ORM optimization (800ms→200ms) |
| DG External | FastAPI async | PostgreSQL session per request |
