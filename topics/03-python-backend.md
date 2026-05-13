# Python / FastAPI / Backend — Question Bank
> CV context: Khoa — Backend AI Engineer, FastAPI + Django + Celery + async, PostgreSQL + Redis + ClickHouse, AWS ECS/Lambda, GitHub Actions, Sentry.

---

## SECTION 1: Python Fundamentals & OOP (Domain 7)

### PY-E01: Python GIL
**Câu hỏi:** GIL trong Python là gì? Ảnh hưởng gì đến multithreading?
**Keywords:** Global Interpreter Lock, CPU-bound vs I/O-bound, multiprocessing
**Follow-up:** "Khi nào dùng threading, khi nào dùng multiprocessing? FastAPI dùng cái gì?"

### PY-E02: List Comprehension vs Generator
**Câu hỏi:** Phân biệt list comprehension và generator expression. Khi nào dùng generator?
**Keywords:** lazy evaluation, memory efficient, `yield`, iterator protocol
**Follow-up:** "Với file 10GB text, bạn đọc từng dòng bằng gì? Tại sao không dùng `readlines()`?"

### PY-E03: Decorator
**Câu hỏi:** Decorator trong Python là gì? Viết một decorator đo thời gian chạy hàm.
**Keywords:** higher-order function, `functools.wraps`, closure
**Expected code:**
```python
import time, functools
def timer(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        print(f"{func.__name__} took {time.perf_counter()-start:.4f}s")
        return result
    return wrapper
```

### PY-M01: OOP trong Python
**Câu hỏi:** Giải thích 4 tính chất OOP. Cho ví dụ từ project thực tế của bạn.
**Keywords:** encapsulation, inheritance, polymorphism, abstraction, `@property`, `@abstractmethod`
**Follow-up:** "Python có `private` thật sự không? `_var` vs `__var` khác gì?"
**CV link:** "Bạn build Python project template với base classes cho RAG pipeline — base class đó implement abstract methods gì?"

### PY-M02: Pydantic v2
**Câu hỏi:** Pydantic v2 khác gì v1? Kể các tính năng mới quan trọng nhất.
**Keywords:** `model_validator`, `field_validator`, `model_config`, Rust core, `@computed_field`
**Follow-up:** "Serialize Enum trong Pydantic v2 thế nào? `model_config` thay thế `class Config` như thế nào?"

### PY-M03: Python memory model
**Câu hỏi:** Python quản lý memory thế nào? Reference counting + garbage collection?
**Keywords:** reference counting, cyclic GC, `gc` module, memory leak, `weakref`
**Follow-up:** "Circular reference gây vấn đề gì trong long-running FastAPI app? Sentry giúp detect memory leak không?"

---

## SECTION 2: Async Programming & Concurrency (Domain 5)

### ASYNC-E01: Async/Await cơ bản
**Câu hỏi:** Asyncio hoạt động thế nào trong Python? Phân biệt coroutine, task, future.
**Keywords:** event loop, non-blocking I/O, `await`, `asyncio.gather`, cooperative multitasking, single-threaded
**Follow-up:** "Khi nào async KHÔNG giúp được gì? (CPU-bound tasks)"

### ASYNC-M01: FastAPI async patterns
**Câu hỏi:** Trong FastAPI, `async def` vs `def` endpoint khác nhau thế nào internally?
**Keywords:** threadpool executor, uvicorn, starlette, blocking calls in async context
**Expected answer:** `def` → FastAPI chạy trong threadpool. `async def` → chạy trực tiếp trên event loop.
**Follow-up:** "Nếu gọi synchronous DB call trong `async def`, điều gì xảy ra?"

### ASYNC-M02: Background Tasks & Celery
**Câu hỏi:** Phân biệt FastAPI `BackgroundTasks` và Celery. Khi nào dùng cái nào?
**Keywords:** in-process vs distributed, retry, result backend, broker (Redis/RabbitMQ), persistence
**CV link:** "Bạn dùng FastAPI BackgroundTasks + Celery ở Atrix AI — tại sao cần cả hai? LLM inference offload thế nào?"
**Follow-up:** "Celery Beat scheduling bug bạn fix ở Sidecardata — nguyên nhân gì? Exponential backoff giải quyết vấn đề gì?"

### ASYNC-M03: Concurrency control
**Câu hỏi:** Race condition là gì? Làm thế nào tránh trong async Python?
**Keywords:** `asyncio.Lock`, `asyncio.Semaphore`, atomic operations, Redis distributed lock
**Follow-up:** "Nếu 2 Celery worker cùng chạy 1 task scheduled — bạn phòng tránh thế nào? (hint: Celery Beat bug)"
**CV link:** "Describe the duplicate pipeline runs bug you fixed at Sidecardata. Root cause? Solution?"

### ASYNC-H01: Temporal Workflow design
**Câu hỏi:** Workflow orchestration là gì? Tại sao Temporal tốt hơn cron job thuần?
**Keywords:** durability, replay, activities vs workflows, determinism, retry/heartbeat policy
**Follow-up:** "Workflow determinism constraint nghĩa là gì? Ví dụ vi phạm? Tại sao `datetime.now()` không được dùng trong workflow?"
**CV link:** "Bạn xử lý 10,000+ doc batches với Temporal ở Spartan — retry/heartbeat được configure thế nào?"

---

## SECTION 3: REST API & Backend Development (Domain 2)

### API-E01: HTTP Methods & Status Codes
**Câu hỏi:** Khi nào dùng POST vs PUT vs PATCH? Phân biệt 200, 201, 204, 400, 401, 403, 404, 422, 500.
**Keywords:** idempotent, safe methods, partial update, semantic HTTP
**Expected answer:**
- `POST` → create, non-idempotent
- `PUT` → full replace, idempotent
- `PATCH` → partial update
- `204` → success no content (DELETE)
- `422` → validation error (FastAPI default)
- `401` → unauthenticated, `403` → unauthorized

### API-E02: RESTful API design conventions
**Câu hỏi:** Đặt tên endpoints theo RESTful chuẩn. Đưa ra ví dụ cho resource "documents".
**Keywords:** noun not verb, plural, nested resources, versioning `/api/v1/`
**Expected answer:**
```
GET    /api/v1/documents          → list
POST   /api/v1/documents          → create
GET    /api/v1/documents/{id}     → get one
PUT    /api/v1/documents/{id}     → full update
PATCH  /api/v1/documents/{id}     → partial update
DELETE /api/v1/documents/{id}     → delete
```

### API-M01: FastAPI Dependency Injection
**Câu hỏi:** Dependency Injection trong FastAPI hoạt động thế nào? Cho ví dụ DB session + auth.
**Keywords:** `Depends()`, shared DB connection, auth middleware, testability, lifespan
**Expected code:**
```python
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session

async def get_current_user(token: str = Depends(oauth2_scheme), db = Depends(get_db)):
    # validate token, fetch user
    ...

@router.get("/documents/{id}")
async def get_document(id: int, db = Depends(get_db), user = Depends(get_current_user)):
    ...
```
**Follow-up:** "Middleware vs Dependency — khi nào dùng cái nào?"

### API-M02: Authentication & Authorization
**Câu hỏi:** Giải thích OAuth2 + JWT flow. `access_token` vs `refresh_token` khác nhau thế nào?
**Keywords:** JWT structure (header.payload.signature), Bearer token, expiry, refresh flow, RBAC
**CV link:** "Bạn implement OAuth2, JWT, Casbin RBAC ở DG External — Casbin giải quyết gì mà JWT không làm được?"
**Follow-up:** "JWT bị đánh cắp thì xử lý thế nào? Token revocation strategy?"

### API-M03: Error handling & API structure
**Câu hỏi:** Làm thế nào để design consistent error response format cho REST API?
**Keywords:** error envelope, `HTTPException`, custom exception handler, RFC 7807 Problem Details
**Expected code:**
```python
from fastapi import Request
from fastapi.responses import JSONResponse

class AppError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        self.code = code
        self.message = message
        self.status = status

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status,
        content={"error": {"code": exc.code, "message": exc.message}}
    )
```

### API-M04: FastAPI middleware & rate limiting
**Câu hỏi:** Implement một rate limiting middleware trong FastAPI.
**Keywords:** `@asynccontextmanager`, startup/shutdown, `Middleware`, `Request.state`, Redis sliding window
**Follow-up:** "Token bucket vs sliding window counter — trade-off?"

---

## SECTION 4: Database & Data Handling (Domain 3)

### DB-E01: ACID properties
**Câu hỏi:** ACID là gì? Giải thích từng property với ví dụ thực tế.
**Keywords:** Atomicity, Consistency, Isolation, Durability, transaction rollback
**Follow-up:** "Isolation levels: Read Committed vs Repeatable Read vs Serializable khác gì?"

### DB-M01: Query optimization & Indexing
**Câu hỏi:** Index hoạt động thế nào? Khi nào thêm index, khi nào không?
**Keywords:** B-tree index, composite index, covering index, write overhead, EXPLAIN ANALYZE
**CV link:** "Bạn tối ưu Django ORM queries ở Sidecardata từ 800ms xuống 200ms — describe the specific indexes you added và tại sao?"
**Follow-up:** "Index trên column có low cardinality (e.g. boolean) có giúp ích không? Tại sao?"

### DB-M02: N+1 problem & ORM optimization
**Câu hỏi:** N+1 query problem là gì? Cách fix trong Django và SQLAlchemy?
**Keywords:** `select_related`, `prefetch_related`, `joinedload`, `selectinload`, eager loading
**Expected code:**
```python
# Django - BAD (N+1)
docs = Document.objects.all()
for doc in docs:
    print(doc.author.name)  # N queries!

# GOOD
docs = Document.objects.select_related('author').all()  # 1 query with JOIN
```

### DB-M03: PostgreSQL trong production
**Câu hỏi:** Connection pooling là gì? Tại sao quan trọng trong web server? Pool size tối ưu?
**Keywords:** pool size = (2 × CPU cores) + 1, max overflow, SQLAlchemy pool, asyncpg, PgBouncer
**Follow-up:** "Async vs sync DB driver (asyncpg vs psycopg2) — khi nào dùng cái nào với FastAPI?"

### DB-M04: Caching strategies
**Câu hỏi:** Kể các caching strategy phổ biến. Cache invalidation khó ở điểm nào?
**Keywords:** TTL, LRU, write-through, write-behind, cache stampede, Redis, `cache-aside`
**CV link:** "Bạn dùng Redis caching ở dự án nào? Cache stampede (thundering herd) là gì và bạn xử lý thế nào?"

### DB-H01: ClickHouse design
**Câu hỏi:** ClickHouse phù hợp cho workload nào? ReplacingMergeTree giải quyết gì?
**Keywords:** OLAP, columnar, ReplacingMergeTree, deduplication, eventual consistency, FINAL keyword
**CV link:** "Bạn dùng ClickHouse ở Sidecardata — describe schema design và tại sao chọn ClickHouse thay vì PostgreSQL cho use case đó?"

---

## SECTION 5: Design Patterns (Domain 4)

### DP-E01: MVC Pattern
**Câu hỏi:** MVC là gì? Trong Django và FastAPI, các layer tương ứng với gì?
**Keywords:** Model (data), View (presentation), Controller (business logic), separation of concerns
**Expected answer:**
- Django: Model → ORM, View → views.py (business logic), Template → presentation
- FastAPI: Router → Controller, Service → Business Logic, Schema → Model (Pydantic), ORM → Model

### DP-M01: Repository Pattern
**Câu hỏi:** Repository Pattern là gì? Tại sao dùng nó thay vì gọi DB trực tiếp trong endpoint?
**Keywords:** abstraction layer, testability, swap storage backend, dependency inversion
**Expected code:**
```python
from abc import ABC, abstractmethod

class DocumentRepository(ABC):
    @abstractmethod
    async def get(self, id: int) -> Document: ...
    @abstractmethod
    async def create(self, doc: DocumentCreate) -> Document: ...

class PostgresDocumentRepository(DocumentRepository):
    def __init__(self, db: AsyncSession):
        self.db = db
    async def get(self, id: int) -> Document:
        return await self.db.get(Document, id)
```
**Follow-up:** "Bạn đã apply Repository pattern trong project nào? Test có dễ hơn không?"

### DP-M02: Singleton Pattern
**Câu hỏi:** Singleton trong Python implement thế nào? Tại sao nó controversial?
**Keywords:** `__new__`, module-level singleton, metaclass, thread-safety issue, global state problem
**Expected code:**
```python
class DatabasePool:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.pool = create_pool()
        return cls._instance
```
**CV link:** "FastAPI lifespan context manager thực chất là Singleton pattern cho shared resources — bạn đã dùng pattern này không?"

### DP-M03: Factory Pattern
**Câu hỏi:** Factory Pattern là gì? Cho ví dụ trong context LLM integration.
**Keywords:** object creation abstraction, open/closed principle, switch providers without changing caller
**Expected code:**
```python
class LLMFactory:
    @staticmethod
    def create(provider: str, **kwargs):
        if provider == "openai":
            return OpenAIClient(**kwargs)
        elif provider == "anthropic":
            return AnthropicClient(**kwargs)
        raise ValueError(f"Unknown provider: {provider}")
```
**CV link:** "Bạn integrate cả OpenAI GPT và LLaMA ở Atrix AI — bạn có dùng Factory hay strategy pattern để switch không?"

---

## SECTION 6: CI/CD, Monitoring & Logging (Domain 6)

### CICD-E01: CI/CD pipeline overview
**Câu hỏi:** CI/CD pipeline gồm những bước gì? Mô tả pipeline của bạn ở dự án gần nhất.
**Keywords:** build → test → lint → deploy, GitHub Actions, artifact, environment (dev/staging/prod)
**CV link:** "GitHub Actions CI/CD bạn setup ở Atrix AI — pipeline có những stages gì? Deploy lên ECS như thế nào?"
**Follow-up:** "Blue/green deployment vs rolling update — trade-off?"

### CICD-M01: Monitoring & Observability
**Câu hỏi:** Phân biệt Monitoring, Logging, và Tracing. Bạn dùng tool nào trong production?
**Keywords:** Sentry (error tracking), Grafana (metrics), structured logging, distributed tracing, alerting
**CV link:** "Bạn dùng Sentry ở Atrix AI — mô tả một incident bạn debug bằng Sentry. Từ alert đến root cause mất bao lâu?"
**Follow-up:** "Structured logging (JSON format) vs plain text — tại sao structured tốt hơn?"

### CICD-M02: Logging best practices
**Câu hỏi:** Làm thế nào setup logging chuẩn trong FastAPI? Log level nào dùng ở đâu?
**Keywords:** `logging` module, log levels (DEBUG/INFO/WARNING/ERROR/CRITICAL), correlation ID, request tracing
**Expected code:**
```python
import logging, uuid
from fastapi import Request

logger = logging.getLogger(__name__)

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    correlation_id = str(uuid.uuid4())
    request.state.correlation_id = correlation_id
    logger.info(f"Request started", extra={"correlation_id": correlation_id, "path": request.url.path})
    response = await call_next(request)
    logger.info(f"Request completed", extra={"correlation_id": correlation_id, "status": response.status_code})
    return response
```

### CICD-M03: AWS deployment
**Câu hỏi:** Phân biệt ECS, Lambda, và EC2. Bạn chọn cái nào cho FastAPI app?
**Keywords:** serverless vs container, cold start, scaling, cost model, ECS Fargate vs EC2 launch type
**CV link:** "Bạn deploy cả ECS + Lambda ở Atrix AI — use case của mỗi loại là gì? Tại sao LLM inference không dùng Lambda?"

---

## SECTION 7: Operations & Troubleshooting (Domain 8)

### OPS-M01: Debugging production issues
**Câu hỏi:** Khi API response time tăng đột ngột lên 10x, bạn debug như thế nào? (Step by step)
**Keywords:** metrics first, identify spike time, DB slow queries, N+1, cache miss, connection pool exhausted
**Expected approach:**
1. Check Grafana/Sentry → xác định thời điểm và endpoint bị ảnh hưởng
2. DB slow query log → `EXPLAIN ANALYZE`
3. Check connection pool metrics
4. Check cache hit rate
5. Review recent deployments (git log)
**CV link:** "Bạn optimize từ 800ms → 200ms ở Sidecardata — describe the debugging process bước đầu tiên là gì?"

### OPS-M02: Celery troubleshooting
**Câu hỏi:** Celery task bị stuck hoặc không chạy — bạn diagnose thế nào?
**Keywords:** `celery inspect active`, broker connectivity, result backend, task retry, dead letter queue
**CV link:** "Describe the Celery Beat duplicate runs bug — how did you detect it? What was the fix?"

### OPS-M03: Incident response mindset
**Câu hỏi:** Khi production đột ngột bị down, bạn làm gì trong 5 phút đầu?
**Keywords:** assess impact → communicate → rollback vs fix forward → RCA (root cause analysis)
**Follow-up:** "Rollback vs hotfix — khi nào chọn cái nào?"
