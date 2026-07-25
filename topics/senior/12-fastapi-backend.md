# Module 12: FastAPI & Backend Patterns — Đáp án phỏng vấn Senior AI Engineer

> Mục tiêu: Nắm vững FastAPI patterns cho AI services: async, streaming, background jobs, performance.

---

## PHẦN 1: FastAPI Architecture

---

### Q1: Lifespan events là gì? Tại sao quan trọng cho AI services?

**Trả lời:**

Lifespan events cho phép chạy code khi app start và shutdown. Thay thế cho `@app.on_event("startup")` deprecated.

**Tại sao quan trọng cho AI services:**
- Khởi tạo LLM clients một lần (không tạo mới mỗi request)
- Warm up DB connection pool
- Load ML models vào memory
- Cleanup gracefully khi shutdown (drain connections, flush metrics)

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
import anthropic
import openai
import httpx
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import redis.asyncio as redis

# Global state
_app_state: dict = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup/shutdown lifecycle management.
    Code before yield = startup, code after yield = shutdown.
    """
    # === STARTUP ===
    print("Starting up AI service...")

    # 1. Initialize LLM clients with connection pooling
    _app_state["anthropic"] = anthropic.AsyncAnthropic(
        max_retries=3,
        timeout=anthropic.Timeout(60.0, connect=5.0),
    )

    _app_state["openai"] = openai.AsyncOpenAI(
        max_retries=3,
        timeout=openai.Timeout(connect=5.0, read=60.0, write=10.0, pool=5.0),
        http_client=httpx.AsyncClient(
            limits=httpx.Limits(
                max_connections=50,
                max_keepalive_connections=10,
                keepalive_expiry=30.0
            )
        )
    )

    # 2. Initialize DB connection pool
    engine = create_async_engine(
        "postgresql+asyncpg://user:pass@localhost/db",
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,       # Test connections before use
        pool_recycle=3600,        # Recycle connections after 1 hour
    )
    _app_state["engine"] = engine
    _app_state["session_factory"] = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # 3. Initialize Redis
    _app_state["redis"] = redis.Redis(
        host="localhost",
        port=6379,
        decode_responses=True,
        max_connections=20
    )

    # 4. Warm up: test connections
    try:
        await _app_state["redis"].ping()
        print("Redis connected")
    except Exception as e:
        print(f"Redis connection failed: {e}")

    print("Startup complete.")

    yield  # App runs here

    # === SHUTDOWN ===
    print("Shutting down AI service...")

    await _app_state["anthropic"].close()
    await _app_state["openai"].close()
    await _app_state["engine"].dispose()
    await _app_state["redis"].aclose()

    print("Shutdown complete.")

app = FastAPI(
    title="AI Service",
    version="1.0.0",
    lifespan=lifespan
)
```

---

### Q2: Dependency Injection trong FastAPI — request scope vs app scope

**Trả lời:**

**Dependency scopes:**
- **Request scope** (default): Tạo mới mỗi request, cleanup sau mỗi request
- **App scope**: Tạo một lần khi startup (dùng lifespan hoặc module-level)

```python
from fastapi import FastAPI, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

# === APP SCOPE: LLM Client (one instance for entire app lifetime) ===
def get_llm_client(request: Request) -> anthropic.AsyncAnthropic:
    """App-scoped: reuse singleton from lifespan."""
    return request.app.state.anthropic  # hoac tu _app_state dict

# === REQUEST SCOPE: DB Session (new per request, auto-cleanup) ===
async def get_db_session(request: Request) -> AsyncSession:
    """Request-scoped: new session per request, auto-close."""
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        yield session
        # Session auto-closed after request

# === Dependency chaining ===
async def get_current_user(
    token: str,
    db: AsyncSession = Depends(get_db_session)
) -> User:
    """Depends on db_session."""
    user = await db.execute(select(User).where(User.token == token))
    user = user.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user

async def get_current_active_user(
    user: User = Depends(get_current_user)
) -> User:
    """Depends on get_current_user (chaining)."""
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user

# Type aliases for cleaner signatures
LLMClient = Annotated[anthropic.AsyncAnthropic, Depends(get_llm_client)]
DBSession = Annotated[AsyncSession, Depends(get_db_session)]
CurrentUser = Annotated[User, Depends(get_current_active_user)]

# === Using in endpoints ===
@app.post("/analyze")
async def analyze_document(
    request_body: AnalyzeRequest,
    llm: LLMClient,
    db: DBSession,
    user: CurrentUser
):
    # All dependencies resolved automatically
    response = await llm.messages.create(
        model="claude-haiku-3-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": request_body.text}]
    )
    return {"result": response.content[0].text, "user": user.id}
```

---

### Q3: Middleware patterns cho AI services

**Trả lời:**

```python
import time
import uuid
import logging
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware

app = FastAPI()
logger = logging.getLogger(__name__)

# === 1. CORS Middleware ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.company.com"],  # Production: specific origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

# === 2. GZip Middleware ===
app.add_middleware(GZipMiddleware, minimum_size=1000)  # Compress responses > 1KB

# === 3. Request ID Middleware ===
class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Add to request state (accessible in handlers)
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add to response headers
        response.headers["X-Request-ID"] = request_id

        return response

app.add_middleware(RequestIDMiddleware)

# === 4. Timing + Logging Middleware ===
class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()

        response = await call_next(request)

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        request_id = getattr(request.state, "request_id", "unknown")

        logger.info(
            "Request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(elapsed_ms, 2),
            }
        )

        response.headers["X-Response-Time-Ms"] = str(round(elapsed_ms, 2))

        return response

app.add_middleware(TimingMiddleware)

# === 5. Auth Middleware ===
from jose import JWTError, jwt

class AuthMiddleware(BaseHTTPMiddleware):
    PUBLIC_PATHS = {"/health", "/docs", "/openapi.json", "/metrics"}

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.PUBLIC_PATHS:
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return Response(
                content='{"detail": "Missing authorization header"}',
                status_code=401,
                media_type="application/json"
            )

        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            request.state.user_id = payload.get("sub")
        except JWTError:
            return Response(
                content='{"detail": "Invalid token"}',
                status_code=401,
                media_type="application/json"
            )

        return await call_next(request)

app.add_middleware(AuthMiddleware)

# === Router organization for AI services ===
from fastapi import APIRouter

# Separate routers by domain
completions_router = APIRouter(prefix="/completions", tags=["completions"])
jobs_router = APIRouter(prefix="/jobs", tags=["jobs"])
rag_router = APIRouter(prefix="/rag", tags=["rag"])

app.include_router(completions_router)
app.include_router(jobs_router)
app.include_router(rag_router)
```

---

## PHẦN 2: Async Deep Dive

---

### Q4: Blocking calls trong async — run_in_executor pattern

**Trả lời:**

**Vấn đề:** Gọi blocking code (sync I/O, CPU-bound) trong async function → block entire event loop → tất cả requests bị chậm

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from fastapi import FastAPI
import time

app = FastAPI()

# === BAD: Blocking call in async handler ===
@app.get("/bad-example")
async def bad_handler():
    # Blocks event loop! No other requests can be processed during this!
    time.sleep(5)           # Blocking I/O
    result = sync_heavy_computation()  # Blocking CPU
    return {"result": result}

# === GOOD: run_in_executor for blocking calls ===
thread_pool = ThreadPoolExecutor(max_workers=10)
process_pool = ProcessPoolExecutor(max_workers=4)

@app.get("/good-example-io")
async def good_handler_io():
    """For blocking I/O (file ops, sync DB, legacy libs)."""
    loop = asyncio.get_event_loop()

    # Run in thread pool (I/O-bound blocking operations)
    result = await loop.run_in_executor(
        thread_pool,
        sync_io_operation,  # The blocking function
        "argument"          # Arguments
    )
    return {"result": result}

@app.get("/good-example-cpu")
async def good_handler_cpu():
    """For CPU-bound operations (ML inference, image processing)."""
    loop = asyncio.get_event_loop()

    # Run in process pool (CPU-bound - bypasses GIL)
    result = await loop.run_in_executor(
        process_pool,
        cpu_intensive_function,
        data
    )
    return {"result": result}

# Real-world: Legacy sync HTTP library
import requests  # Blocking library

@app.get("/legacy-api")
async def call_legacy_api(url: str):
    loop = asyncio.get_event_loop()

    def _sync_call():
        response = requests.get(url, timeout=30)  # Sync, blocking
        return response.json()

    result = await loop.run_in_executor(thread_pool, _sync_call)
    return result

# Rule of thumb:
# IO-bound sync code  --> ThreadPoolExecutor (I/O releases GIL)
# CPU-bound code      --> ProcessPoolExecutor (bypasses GIL)
# Async-native code   --> await directly (httpx, asyncpg, aiofiles)
```

---

### Q5: SQLAlchemy Async — AsyncSession và asyncpg

**Trả lời:**

```python
from sqlalchemy.ext.asyncio import (
    create_async_engine, AsyncSession, AsyncEngine
)
from sqlalchemy.orm import sessionmaker, selectinload, joinedload
from sqlalchemy import select, update, delete
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import Optional
import uuid

# === Models ===
class Base(DeclarativeBase):
    pass

class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    status: Mapped[str] = mapped_column(default="pending")
    user_id: Mapped[uuid.UUID] = mapped_column()
    results: Mapped[list["JobResult"]] = relationship(back_populates="job")

class JobResult(Base):
    __tablename__ = "job_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column()
    content: Mapped[str] = mapped_column()
    job: Mapped["Job"] = relationship(back_populates="results")

# === Async Engine Setup ===
engine = create_async_engine(
    "postgresql+asyncpg://user:pass@localhost/db",
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=False  # Set True for debugging SQL
)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False  # Important for async: prevents lazy-loading after commit
)

# === Repository Pattern ===
class JobRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: uuid.UUID) -> Job:
        job = Job(user_id=user_id)
        self.session.add(job)
        await self.session.flush()  # Get ID without committing
        return job

    async def get_by_id(self, job_id: uuid.UUID) -> Optional[Job]:
        result = await self.session.execute(
            select(Job).where(Job.id == job_id)
        )
        return result.scalar_one_or_none()

    async def get_with_results(self, job_id: uuid.UUID) -> Optional[Job]:
        """Eager load results to avoid N+1."""
        result = await self.session.execute(
            select(Job)
            .options(selectinload(Job.results))  # Eager load
            .where(Job.id == job_id)
        )
        return result.scalar_one_or_none()

    async def update_status(self, job_id: uuid.UUID, status: str):
        await self.session.execute(
            update(Job)
            .where(Job.id == job_id)
            .values(status=status)
        )

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0
    ) -> list[Job]:
        result = await self.session.execute(
            select(Job)
            .where(Job.user_id == user_id)
            .order_by(Job.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

# === Usage in FastAPI endpoint ===
@app.post("/jobs")
async def create_job(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    async with db.begin():  # Transaction
        repo = JobRepository(db)
        job = await repo.create(user_id)
    return {"job_id": str(job.id)}

# === N+1 Problem Fix ===
# BAD: N+1 query
async def bad_get_jobs_with_results(db: AsyncSession) -> list[Job]:
    result = await db.execute(select(Job))
    jobs = result.scalars().all()

    for job in jobs:
        # Each access triggers a new SELECT query!
        _ = await job.awaitable_attrs.results  # N separate queries!

    return jobs

# GOOD: Eager loading
async def good_get_jobs_with_results(db: AsyncSession) -> list[Job]:
    result = await db.execute(
        select(Job).options(selectinload(Job.results))  # One JOIN query
    )
    return list(result.scalars().all())
```

---

### Q6: httpx.AsyncClient — tại sao không dùng requests?

**Trả lời:**

```python
import httpx
import asyncio

# === WHY NOT requests in async code ===
# requests is synchronous - blocks the event loop!
import requests
async def bad_http_call():
    # This BLOCKS - no other coroutines can run while waiting
    response = requests.get("https://api.example.com/data")  # BLOCKS EVENT LOOP
    return response.json()

# === httpx.AsyncClient - proper async HTTP ===
async def good_http_call():
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com/data")  # NON-BLOCKING
        return response.json()

# === Production pattern: Singleton client with connection pooling ===
_http_client: httpx.AsyncClient | None = None

def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=5.0,   # Connection timeout
                read=30.0,     # Read timeout
                write=10.0,    # Write timeout
                pool=5.0       # Pool timeout
            ),
            limits=httpx.Limits(
                max_connections=100,
                max_keepalive_connections=20,
                keepalive_expiry=30.0
            ),
            headers={"User-Agent": "MyAIService/1.0"}
        )
    return _http_client

# === Parallel HTTP calls with httpx ===
async def fetch_multiple_endpoints(urls: list[str]) -> list[dict]:
    client = get_http_client()

    async def fetch_one(url: str) -> dict:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()

    results = await asyncio.gather(
        *[fetch_one(url) for url in urls],
        return_exceptions=True
    )
    return results

# === Retry with httpx ===
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True
)
async def resilient_http_call(url: str) -> dict:
    client = get_http_client()
    response = await client.get(url)
    response.raise_for_status()
    return response.json()
```

---

### Q7: Celery vs BackgroundTasks — khi nào dùng cái nào?

**Trả lời:**

```
                    BackgroundTasks          Celery
Duration            < 30 seconds             Minutes to hours
Persistence         No (lost on restart)     Yes (persisted in broker)
Retry               Manual                   Built-in with backoff
Monitoring          None                     Flower, Datadog
Scheduling          No                       Celery Beat (cron)
Cross-service       No (in-process)          Yes (distributed workers)
Overhead            Zero                     Redis/RabbitMQ broker needed
Use case            Quick notifications      Long-running AI jobs, pipelines
```

**BackgroundTasks (simple, in-process):**
```python
from fastapi import BackgroundTasks

def send_email_notification(email: str, content: str):
    """Quick task, max ~30s, OK to lose on restart."""
    smtp_client.send(to=email, body=content)

@app.post("/analyze")
async def analyze(
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks
):
    # Process immediately
    result = quick_analysis(request.text)

    # Fire-and-forget: send notification
    background_tasks.add_task(
        send_email_notification,
        request.email,
        f"Analysis complete: {result[:100]}"
    )

    return {"result": result}
```

**Celery (production-grade distributed tasks):**
```python
from celery import Celery
from kombu import Queue

celery_app = Celery(
    "ai_tasks",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1"
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_expires=3600,
    task_queues=[
        Queue("high_priority", routing_key="high"),
        Queue("default", routing_key="default"),
        Queue("low_priority", routing_key="low"),
    ],
    task_default_queue="default",
    worker_concurrency=4,
    task_acks_late=True,       # Acknowledge after completion (not receipt)
    worker_prefetch_multiplier=1  # Process one task at a time per worker
)

@celery_app.task(
    bind=True,
    name="process_document",
    max_retries=3,
    default_retry_delay=60,
    queue="default"
)
def process_document(self, job_id: str, document: str):
    """Long-running document processing task."""
    try:
        # Update status
        update_job_status(job_id, "processing")

        # LLM call (can take minutes)
        result = call_llm_sync(document)

        update_job_status(job_id, "completed", result=result)
        return {"job_id": job_id, "status": "completed"}

    except RateLimitError as exc:
        # Retry after rate limit reset
        raise self.retry(exc=exc, countdown=60)
    except Exception as exc:
        update_job_status(job_id, "failed", error=str(exc))
        raise

# Dispatch from FastAPI
@app.post("/process")
async def submit_processing(request: ProcessRequest):
    job_id = str(uuid.uuid4())
    create_job_record(job_id)

    # Send to Celery
    process_document.apply_async(
        args=[job_id, request.document],
        task_id=job_id,       # Use job_id as task_id for deduplication
        countdown=0,
        expires=3600          # Task expires if not started within 1 hour
    )

    return {"job_id": job_id}
```

---

### Q8: asyncio.Semaphore cho concurrent LLM calls

**Trả lời:**

```python
import asyncio
from openai import AsyncOpenAI

client = AsyncOpenAI()

# Global semaphore: limit concurrent LLM calls to avoid rate limits
LLM_SEMAPHORE = asyncio.Semaphore(10)  # max 10 concurrent calls

async def rate_limited_llm_call(prompt: str, model: str = "gpt-4o-mini") -> str:
    """LLM call with semaphore to prevent rate limit errors."""
    async with LLM_SEMAPHORE:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

async def process_batch(prompts: list[str]) -> list[str]:
    """Process many prompts with controlled concurrency."""
    tasks = [rate_limited_llm_call(p) for p in prompts]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results

# Per-user semaphore for fairness
from collections import defaultdict

user_semaphores: dict[str, asyncio.Semaphore] = defaultdict(
    lambda: asyncio.Semaphore(3)  # max 3 concurrent per user
)

async def user_bounded_call(user_id: str, prompt: str) -> str:
    async with user_semaphores[user_id]:
        return await rate_limited_llm_call(prompt)
```

---

## PHẦN 3: Streaming Response

---

### Q9: StreamingResponse với async generator — LLM to SSE

**Trả lời:**

**SSE Format:**
```
data: {"type": "token", "text": "Hello"}\n\n
data: {"type": "token", "text": " world"}\n\n
data: {"type": "done", "usage": {"input_tokens": 10, "output_tokens": 5}}\n\n
```

```python
import json
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import anthropic

app = FastAPI()
client = anthropic.AsyncAnthropic()

class ChatRequest(BaseModel):
    message: str
    model: str = "claude-haiku-3-5"
    max_tokens: int = 1024

async def llm_stream_generator(request: ChatRequest, request_id: str):
    """
    Async generator that yields SSE-formatted events.
    """
    try:
        async with client.messages.stream(
            model=request.model,
            max_tokens=request.max_tokens,
            messages=[{"role": "user", "content": request.message}]
        ) as stream:
            async for event in stream:
                if hasattr(event, 'type'):
                    if event.type == "content_block_delta":
                        if hasattr(event.delta, 'text'):
                            payload = {
                                "type": "token",
                                "text": event.delta.text,
                                "request_id": request_id
                            }
                            yield f"data: {json.dumps(payload)}\n\n"

                    elif event.type == "message_stop":
                        # Send final usage stats
                        message = await stream.get_final_message()
                        payload = {
                            "type": "done",
                            "request_id": request_id,
                            "usage": {
                                "input_tokens": message.usage.input_tokens,
                                "output_tokens": message.usage.output_tokens
                            }
                        }
                        yield f"data: {json.dumps(payload)}\n\n"

    except Exception as e:
        error_payload = {
            "type": "error",
            "error": str(e),
            "request_id": request_id
        }
        yield f"data: {json.dumps(error_payload)}\n\n"

@app.post("/completions/stream")
async def stream_completion(request: ChatRequest, http_request: Request):
    request_id = getattr(http_request.state, "request_id", str(uuid.uuid4()))

    return StreamingResponse(
        llm_stream_generator(request, request_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",      # Disable nginx buffering
            "X-Request-ID": request_id
        }
    )

# Frontend JavaScript to consume SSE:
# const response = await fetch('/completions/stream', {method: 'POST', body: JSON.stringify({message: 'Hello'})});
# const reader = response.body.getReader();
# while (true) {
#   const {done, value} = await reader.read();
#   if (done) break;
#   const text = new TextDecoder().decode(value);
#   // Parse SSE events from text
# }
```

---

### Q10: WebSocket cho bidirectional streaming

**Trả lời:**

```python
from fastapi import WebSocket, WebSocketDisconnect
import json
import anthropic

client = anthropic.AsyncAnthropic()

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        self.active_connections.pop(client_id, None)

    async def send_json(self, client_id: str, data: dict):
        ws = self.active_connections.get(client_id)
        if ws:
            await ws.send_json(data)

manager = ConnectionManager()

@app.websocket("/ws/chat/{client_id}")
async def websocket_chat(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    conversation_history = []

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            user_message = data.get("message", "")

            conversation_history.append({
                "role": "user",
                "content": user_message
            })

            # Stream response back to client
            full_response = ""
            async with client.messages.stream(
                model="claude-haiku-3-5",
                max_tokens=1024,
                messages=conversation_history
            ) as stream:
                async for text in stream.text_stream:
                    full_response += text
                    await websocket.send_json({
                        "type": "token",
                        "text": text
                    })

            # Add assistant response to history
            conversation_history.append({
                "role": "assistant",
                "content": full_response
            })

            await websocket.send_json({
                "type": "done",
                "full_response": full_response
            })

    except WebSocketDisconnect:
        manager.disconnect(client_id)
        print(f"Client {client_id} disconnected")
    except Exception as e:
        await websocket.send_json({"type": "error", "error": str(e)})
        manager.disconnect(client_id)
```

---

## PHẦN 4: Background Jobs — Celery Advanced

---

### Q11: Celery Beat — crontab, duplicate run bug, fix với RedBeat

**Trả lời:**

**Celery Beat setup:**
```python
from celery import Celery
from celery.schedules import crontab

app = Celery("ai_service", broker="redis://localhost:6379/0")

app.conf.beat_schedule = {
    # Generate daily reports at midnight UTC
    "daily-report": {
        "task": "tasks.generate_daily_report",
        "schedule": crontab(hour=0, minute=0),
    },
    # Refresh embeddings every 6 hours
    "refresh-embeddings": {
        "task": "tasks.refresh_vector_index",
        "schedule": crontab(minute=0, hour="*/6"),
    },
    # Health check every minute
    "health-check": {
        "task": "tasks.system_health_check",
        "schedule": 60.0,  # Every 60 seconds
    },
}

@app.task(name="tasks.generate_daily_report")
def generate_daily_report():
    """Generate and email daily usage report."""
    # ... implementation ...
    pass
```

**BUG: Duplicate runs khi có nhiều Beat instances:**
```
Problem:
  Deploy 3 ECS tasks for the worker service
  Each task runs its OWN Celery Beat instance
  Result: daily-report chạy 3 lần thay vì 1 lần!

  Pod 1 Beat: 00:00:00 -> triggers generate_daily_report
  Pod 2 Beat: 00:00:00 -> triggers generate_daily_report  <- DUPLICATE!
  Pod 3 Beat: 00:00:00 -> triggers generate_daily_report  <- DUPLICATE!
```

**Fix 1: RedBeat (recommended cho production):**
```bash
pip install redbeat
```

```python
from redbeat import RedBeatScheduler

app.conf.update(
    beat_scheduler="redbeat.RedBeatScheduler",
    beat_max_loop_interval=5,
    redbeat_redis_url="redis://localhost:6379/0",
    redbeat_lock_timeout=10 * 60,  # 10 minute lock
)

# RedBeat stores schedule in Redis with distributed lock
# Only ONE Beat instance can hold the lock at a time
# Others wait -> no duplicate runs
```

**Fix 2: Single Beat deployment (simpler but less resilient):**
```yaml
# ECS Task Definition: separate Beat service
# api-workers: desiredCount=3 (no Beat)
# celery-beat: desiredCount=1  (single Beat instance)

# In terraform:
resource "aws_ecs_service" "celery_beat" {
  name            = "celery-beat"
  desired_count   = 1  # ALWAYS exactly 1
  # ...
}
```

---

### Q12: Retry với exponential backoff + Idempotency

**Trả lời:**

```python
from celery import Celery
from celery.utils.log import get_task_logger
import hashlib
import redis

app = Celery("tasks", broker="redis://localhost:6379/0")
logger = get_task_logger(__name__)
redis_client = redis.Redis()

# === Exponential Backoff Retry ===
@app.task(
    bind=True,
    name="process_llm_job",
    max_retries=5,
    # Exponential backoff: 1min, 2min, 4min, 8min, 16min
    default_retry_delay=60,
)
def process_llm_job(self, job_id: str, prompt: str):
    try:
        result = call_llm_api(prompt)
        save_result(job_id, result)
        return result
    except RateLimitError as exc:
        # Linear backoff for rate limits
        retry_after = getattr(exc, 'retry_after', 60)
        raise self.retry(exc=exc, countdown=retry_after)
    except TemporaryError as exc:
        # Exponential backoff
        retry_in = 2 ** self.request.retries * 60  # 60s, 120s, 240s...
        logger.warning(f"Temporary error, retry {self.request.retries} in {retry_in}s")
        raise self.retry(exc=exc, countdown=retry_in)
    except PermanentError as exc:
        # Don't retry permanent errors
        logger.error(f"Permanent error for job {job_id}: {exc}")
        save_error(job_id, str(exc))
        return None  # Mark as handled

# === Idempotency with task_id deduplication ===
IDEMPOTENCY_TTL = 86400  # 24 hours

def idempotent_task(task_func):
    """Decorator: ensure task runs only once per idempotency_key."""
    def wrapper(self, idempotency_key: str, *args, **kwargs):
        cache_key = f"task:done:{idempotency_key}"

        # Check if already processed
        if redis_client.get(cache_key):
            logger.info(f"Task {idempotency_key} already processed, skipping")
            return redis_client.get(f"task:result:{idempotency_key}")

        result = task_func(self, idempotency_key, *args, **kwargs)

        # Mark as done
        redis_client.setex(cache_key, IDEMPOTENCY_TTL, "1")
        redis_client.setex(
            f"task:result:{idempotency_key}",
            IDEMPOTENCY_TTL,
            str(result)
        )
        return result

    return wrapper

@app.task(bind=True, name="send_webhook")
@idempotent_task
def send_webhook(self, idempotency_key: str, url: str, payload: dict):
    """Idempotent webhook: won't send twice even if retried."""
    import httpx
    with httpx.Client() as client:
        response = client.post(url, json=payload, timeout=30)
        response.raise_for_status()
    return {"status": "sent", "status_code": response.status_code}

# === Dead Letter Queue pattern ===
app.conf.task_routes = {
    "tasks.process_llm_job": {"queue": "default"},
    "tasks.send_webhook": {"queue": "default"},
}

# In Redis/RabbitMQ: configure DLQ
# SQS equivalent: after maxReceiveCount=3 -> send to DLQ
# DLQ consumer: alerts, manual review, re-queue after fix
```

---

## PHẦN 5: API Design for AI

---

### Q13: Async job submission pattern

**Trả lời:**

**Pattern:** POST (submit) → GET status polling → GET result

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from enum import Enum
import uuid
from datetime import datetime

class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class JobSubmission(BaseModel):
    document: str
    task_type: str = "summarize"
    webhook_url: str | None = None  # Optional callback

class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    created_at: datetime
    estimated_time_seconds: int | None = None

class JobResult(BaseModel):
    job_id: str
    status: JobStatus
    result: str | None = None
    error: str | None = None
    completed_at: datetime | None = None
    usage: dict | None = None

@app.post("/jobs", response_model=JobResponse, status_code=202)
async def submit_job(
    submission: JobSubmission,
    db: DBSession,
    user: CurrentUser
) -> JobResponse:
    """
    202 Accepted: job submitted but not yet processed.
    Returns job_id for status polling.
    """
    job_id = str(uuid.uuid4())

    # Persist to DB
    await create_job_record(db, job_id, user.id, submission.dict())

    # Queue for processing
    process_document.apply_async(
        args=[job_id, submission.document, submission.task_type],
        task_id=job_id,
        kwargs={"webhook_url": submission.webhook_url}
    )

    return JobResponse(
        job_id=job_id,
        status=JobStatus.QUEUED,
        created_at=datetime.utcnow(),
        estimated_time_seconds=30
    )

@app.get("/jobs/{job_id}", response_model=JobResult)
async def get_job_status(
    job_id: str,
    db: DBSession,
    user: CurrentUser
) -> JobResult:
    """Poll for job status and result."""
    job = await get_job_from_db(db, job_id, user.id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobResult(
        job_id=job_id,
        status=job.status,
        result=job.result if job.status == JobStatus.COMPLETED else None,
        error=job.error if job.status == JobStatus.FAILED else None,
        completed_at=job.completed_at,
        usage=job.usage
    )

@app.get("/jobs", response_model=list[JobResult])
async def list_jobs(
    db: DBSession,
    user: CurrentUser,
    status: JobStatus | None = None,
    limit: int = 20,
    offset: int = 0
) -> list[JobResult]:
    """List jobs for current user with pagination."""
    jobs = await list_user_jobs(db, user.id, status, limit, offset)
    return [JobResult(**job.dict()) for job in jobs]

# Webhook callback (when job completes)
@app.task(name="notify_webhook")
def notify_webhook(job_id: str, webhook_url: str, result: dict):
    import httpx
    with httpx.Client() as client:
        client.post(
            webhook_url,
            json={"job_id": job_id, "status": "completed", **result},
            headers={"X-Webhook-Secret": WEBHOOK_SECRET},
            timeout=10
        )
```

---

### Q14: Pagination cho long outputs

**Trả lời:**

```python
from pydantic import BaseModel
from typing import TypeVar, Generic

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int
    has_more: bool

    @classmethod
    def create(cls, items: list[T], total: int, limit: int, offset: int):
        return cls(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            has_more=offset + len(items) < total
        )

class DocumentChunk(BaseModel):
    chunk_id: str
    content: str
    page_number: int
    token_count: int

@app.get("/jobs/{job_id}/chunks", response_model=PaginatedResponse[DocumentChunk])
async def get_job_chunks(
    job_id: str,
    limit: int = 10,
    offset: int = 0,
    db: DBSession = Depends(get_db_session),
    user: CurrentUser = Depends(get_current_active_user)
):
    """Get processed document chunks with pagination."""
    total = await count_chunks(db, job_id)
    chunks = await get_chunks(db, job_id, limit=limit, offset=offset)

    return PaginatedResponse.create(
        items=chunks,
        total=total,
        limit=limit,
        offset=offset
    )
```

---

## PHẦN 6: Performance

---

### Q15: DB connection pooling settings — best practices

**Trả lời:**

```python
from sqlalchemy.ext.asyncio import create_async_engine

# Production settings
engine = create_async_engine(
    "postgresql+asyncpg://user:pass@db-host/dbname",

    # Pool size: number of persistent connections
    pool_size=10,           # Base connections (matches DB max_connections / num_workers)

    # Max overflow: extra connections allowed during spikes
    max_overflow=20,        # Total max = pool_size + max_overflow = 30

    # Pool timeout: how long to wait for connection from pool
    pool_timeout=30,        # Raise exception after 30s wait

    # Connection recycling: prevent stale connections
    pool_recycle=3600,      # Recycle connections every hour

    # Pre-ping: test connection before use (catches dropped connections)
    pool_pre_ping=True,

    # Statement cache size (asyncpg-specific optimization)
    connect_args={
        "statement_cache_size": 1000,   # Cache prepared statements
        "command_timeout": 60,          # Per-query timeout
    }
)

# Formula for pool_size:
# pool_size = (num_worker_processes * num_threads_per_worker) * 0.5
# For async FastAPI: pool_size = num_ECS_tasks * 5 (conservative)
# 3 ECS tasks -> pool_size=15, max_overflow=10 -> max 75 connections total
```

---

### Q16: Redis cache decorator pattern

**Trả lời:**

```python
import functools
import json
import hashlib
from typing import Callable, Any
import redis.asyncio as redis
from fastapi import Request

redis_client = redis.Redis(host="localhost", decode_responses=True)

def cached(ttl: int = 300, key_prefix: str = ""):
    """
    Async cache decorator with Redis.
    Cache key = prefix + hash(function_name + args + kwargs)
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key
            key_data = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            cache_key = f"{key_prefix}:{hashlib.md5(key_data.encode()).hexdigest()}"

            # Try cache
            cached_value = await redis_client.get(cache_key)
            if cached_value:
                return json.loads(cached_value)

            # Cache miss: call function
            result = await func(*args, **kwargs)

            # Store in cache
            await redis_client.setex(
                cache_key,
                ttl,
                json.dumps(result, default=str)
            )

            return result
        return wrapper
    return decorator

# Usage
@cached(ttl=600, key_prefix="rag:search")
async def semantic_search(query: str, top_k: int = 5) -> list[dict]:
    """Cached RAG search - same query returns cached results for 10 min."""
    embedding = await get_embedding(query)
    results = await vector_db.search(embedding, top_k=top_k)
    return results

@cached(ttl=3600, key_prefix="user:profile")
async def get_user_profile(user_id: str) -> dict:
    """Cache user profiles for 1 hour."""
    async with get_db_session() as db:
        user = await db.execute(select(User).where(User.id == user_id))
        return user.scalar_one().to_dict()

# Cache invalidation
async def invalidate_user_cache(user_id: str):
    """Invalidate all cache keys for a user."""
    pattern = f"user:profile:*"
    keys = await redis_client.keys(pattern)
    if keys:
        await redis_client.delete(*keys)
```

---

## Quick Reference

```
FASTAPI PATTERNS QUICK REFERENCE
=======================================================

Lifespan:       asynccontextmanager -> yield -> cleanup
                Use for: LLM clients, DB engines, Redis

Dependency scope:
  App scope:    module-level or app.state (one per app lifetime)
  Request scope: Depends(generator) with yield (auto-cleanup)

Async rules:
  Async I/O:    await directly (httpx, asyncpg, aiofiles)
  Sync I/O:     loop.run_in_executor(thread_pool, sync_fn)
  CPU-bound:    loop.run_in_executor(process_pool, cpu_fn)
  NEVER:        requests lib in async code (blocks event loop)

Streaming:      StreamingResponse + async generator
SSE format:     "data: {json}\n\n"
WebSocket:      @app.websocket("/ws/{id}")

Celery vs BackgroundTasks:
  BackgroundTasks:  < 30s, OK to lose on restart, simple
  Celery:           Long-running, retry, scheduling, distributed

Celery Beat bug: Multiple instances -> duplicate runs
Fix:             RedBeat (distributed lock) OR single Beat container

DB Connection Pool (SQLAlchemy async):
  pool_size=10, max_overflow=20, pool_pre_ping=True, pool_recycle=3600
  expire_on_commit=False for AsyncSession!

N+1 fix: selectinload() or joinedload() in query

Rate limiting: asyncio.Semaphore for concurrent LLM calls
=======================================================
```
