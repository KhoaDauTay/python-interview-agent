# Module 6: Python Advanced — Đáp án phỏng vấn Senior AI/Backend Engineer

> Mức độ: Medium → Hard | Phù hợp: Senior Python / AI Engineer roles

---

## Phần 1: Async / Concurrency

---

### Q: asyncio event loop hoạt động như thế nào? Giải thích call stack, event queue, và I/O callbacks.

**Đáp án:**
asyncio là single-threaded concurrency model. Event loop chạy một vòng lặp liên tục:
1. **Call stack**: chứa coroutine đang được thực thi tại thời điểm hiện tại.
2. **I/O polling**: event loop dùng `selectors` (epoll/kqueue) để poll OS xem I/O operation nào đã hoàn tất.
3. **Ready queue**: danh sách các callback/coroutine sẵn sàng để chạy (đã có kết quả I/O hoặc được schedule bằng `call_soon`).
4. Khi coroutine gặp `await`, nó **suspend** và trả quyền kiểm soát lại cho event loop. Event loop chạy task khác trong ready queue cho đến khi I/O callback kích hoạt coroutine ban đầu.

Điều quan trọng: **không có parallelism** — chỉ có concurrency. Tại mỗi thời điểm chỉ có 1 coroutine chạy.

```python
import asyncio
import time

async def fetch_data(name: str, delay: float) -> str:
    print(f"[{name}] Starting, will sleep {delay}s")
    await asyncio.sleep(delay)  # yields control back to event loop
    print(f"[{name}] Done")
    return f"{name} result"

async def main():
    start = time.perf_counter()

    # Both tasks are scheduled — event loop interleaves them
    task1 = asyncio.create_task(fetch_data("A", 1.0))
    task2 = asyncio.create_task(fetch_data("B", 0.5))

    result1 = await task1
    result2 = await task2

    elapsed = time.perf_counter() - start
    print(f"Total: {elapsed:.2f}s")  # ~1.0s, not 1.5s

asyncio.run(main())
```

**Key points:**
- `await asyncio.sleep()` là non-blocking — nhường CPU cho task khác.
- `time.sleep()` trong coroutine là **blocking** — block toàn bộ event loop.
- Event loop dùng `selectors.select()` với timeout để không spin CPU vô ích.
- `asyncio.run()` tạo event loop mới, chạy coroutine, rồi đóng loop.

---

### Q: Phân biệt coroutine, Task, và Future trong asyncio.

**Đáp án:**
- **Coroutine**: hàm được định nghĩa với `async def`. Khi gọi, trả về coroutine object — chưa chạy gì cả. Cần `await` hoặc wrap vào Task để chạy.
- **Task**: subclass của Future, wrap một coroutine và **schedule nó chạy trên event loop ngay lập tức**. Tạo bằng `asyncio.create_task()`.
- **Future**: low-level object đại diện cho một kết quả chưa sẵn sàng. Thường dùng để bridge với callback-based code.

```python
import asyncio

async def compute(x: int) -> int:
    await asyncio.sleep(0.1)
    return x * 2

async def demo_differences():
    # 1. Coroutine object — chưa chạy
    coro = compute(5)
    print(type(coro))  # <class 'coroutine'>

    # 2. Task — scheduled ngay, chạy concurrently
    task = asyncio.create_task(compute(10))
    print(type(task))  # <class '_asyncio.Task'>

    # 3. Future — low-level, thường do framework tạo
    loop = asyncio.get_event_loop()
    future: asyncio.Future[int] = loop.create_future()
    future.set_result(42)
    print(type(future))  # <class '_asyncio.Future'>

    # await coroutine trực tiếp
    result_coro = await coro
    result_task = await task
    result_future = await future

    print(result_coro, result_task, result_future)  # 10 20 42

asyncio.run(demo_differences())
```

**Key points:**
- Tạo Task ngay khi muốn chạy concurrently — đừng `await coro` liên tiếp (sequential).
- `Task` có thể bị cancel bằng `task.cancel()`.
- `Future.set_result()` / `Future.set_exception()` dùng khi integrate với callback APIs.
- `asyncio.ensure_future()` là cách cũ — dùng `asyncio.create_task()` thay thế (Python 3.7+).

---

### Q: asyncio.gather vs asyncio.wait vs asyncio.TaskGroup — khi nào dùng cái nào?

**Đáp án:**
- **`asyncio.gather`**: chạy nhiều coroutine/Task concurrently, trả về list kết quả theo thứ tự. Nếu một task raise exception, mặc định exception propagate ngay (có thể dùng `return_exceptions=True`).
- **`asyncio.wait`**: low-level hơn, trả về 2 set: `done` và `pending`. Linh hoạt hơn — có thể dùng với `FIRST_COMPLETED`, `FIRST_EXCEPTION`, `ALL_COMPLETED`.
- **`asyncio.TaskGroup`**: Python 3.11+, structured concurrency — đảm bảo tất cả tasks đều được cleanup khi có exception. Là cách được khuyến nghị nhất hiện nay.

```python
import asyncio
from typing import Any

async def llm_call(prompt: str, delay: float) -> str:
    await asyncio.sleep(delay)
    if "error" in prompt:
        raise ValueError(f"LLM error for: {prompt}")
    return f"Response to: {prompt}"

# --- gather ---
async def demo_gather():
    results = await asyncio.gather(
        llm_call("question 1", 0.1),
        llm_call("question 2", 0.2),
        llm_call("question 3", 0.3),
        return_exceptions=True,  # lỗi được trả về thay vì propagate
    )
    for r in results:
        if isinstance(r, Exception):
            print(f"Error: {r}")
        else:
            print(r)

# --- wait với FIRST_COMPLETED ---
async def demo_wait():
    tasks = {
        asyncio.create_task(llm_call("q1", 0.5)),
        asyncio.create_task(llm_call("q2", 0.1)),  # nhanh hơn
        asyncio.create_task(llm_call("q3", 0.8)),
    }
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

    # Lấy kết quả task đầu tiên hoàn thành
    first = done.pop()
    print(f"First result: {first.result()}")

    # Cancel phần còn lại
    for t in pending:
        t.cancel()

# --- TaskGroup (Python 3.11+, recommended) ---
async def demo_task_group():
    results: list[str] = []
    try:
        async with asyncio.TaskGroup() as tg:
            t1 = tg.create_task(llm_call("question 1", 0.1))
            t2 = tg.create_task(llm_call("question 2", 0.2))
            t3 = tg.create_task(llm_call("question 3", 0.3))
        # Tất cả tasks đều done khi ra khỏi `async with`
        results = [t1.result(), t2.result(), t3.result()]
    except* ValueError as eg:  # ExceptionGroup (Python 3.11+)
        print(f"Some tasks failed: {eg.exceptions}")

asyncio.run(demo_gather())
```

**Key points:**
- Dùng `TaskGroup` cho production code Python 3.11+ — structured concurrency đảm bảo không leak tasks.
- `gather(return_exceptions=True)` hữu ích khi muốn xử lý partial failures.
- `wait(FIRST_COMPLETED)` dùng khi implement "racing" — lấy kết quả nhanh nhất.
- `gather` giữ thứ tự kết quả theo thứ tự input.

---

### Q: Threading vs Multiprocessing vs Asyncio — khi nào dùng cái nào? GIL tác động thế nào?

**Đáp án:**
- **GIL (Global Interpreter Lock)**: CPython có một lock bảo vệ Python objects. Tại mỗi thời điểm chỉ một thread Python chạy bytecode. GIL được release khi thread đang chờ I/O hoặc gọi C extension (numpy, torch).
- **Threading**: phù hợp với I/O-bound tasks (requests đến DB, HTTP calls). GIL không ảnh hưởng vì threads release GIL khi chờ I/O. Nhưng không tận dụng được multiple CPU cores cho CPU-bound work.
- **Multiprocessing**: mỗi process có Python interpreter riêng, không bị GIL. Phù hợp CPU-bound (xử lý ảnh, encoding, số học). Overhead cao do pickling data giữa processes.
- **Asyncio**: single-threaded, không có overhead của thread/process switching. Phù hợp nhất cho high-concurrency I/O (nhiều LLM API calls, DB queries).

```python
import asyncio
import threading
import multiprocessing
import time
import numpy as np
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

# --- I/O-bound: Asyncio wins ---
async def io_bound_async(n: int):
    await asyncio.sleep(0.1)  # simulate I/O
    return n

async def run_async(count: int):
    start = time.perf_counter()
    await asyncio.gather(*[io_bound_async(i) for i in range(count)])
    print(f"Asyncio {count} tasks: {time.perf_counter() - start:.2f}s")

# --- CPU-bound: Multiprocessing wins ---
def cpu_intensive(size: int) -> float:
    """Numpy giải phóng GIL, nhưng pure Python thì không."""
    arr = np.random.randn(size, size)
    return float(np.linalg.det(arr))

def run_with_threads(count: int, size: int):
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(cpu_intensive, [size] * count))
    print(f"ThreadPool: {time.perf_counter() - start:.2f}s")

def run_with_processes(count: int, size: int):
    start = time.perf_counter()
    with ProcessPoolExecutor(max_workers=4) as executor:
        list(executor.map(cpu_intensive, [size] * count))
    print(f"ProcessPool: {time.perf_counter() - start:.2f}s")

# AI workload example: parallel embedding generation
async def embed_documents_async(docs: list[str]) -> list[list[float]]:
    """
    LLM/embedding calls: dùng asyncio để gọi nhiều API calls concurrently.
    Model inference local (CPU-bound): dùng ProcessPoolExecutor.
    """
    semaphore = asyncio.Semaphore(10)  # max 10 concurrent calls

    async def embed_one(doc: str) -> list[float]:
        async with semaphore:
            await asyncio.sleep(0.05)  # simulate API call
            return [0.1, 0.2, 0.3]   # fake embedding

    return await asyncio.gather(*[embed_one(doc) for doc in docs])
```

**Key points:**
- **AI API calls** (OpenAI, Anthropic): dùng Asyncio — I/O-bound, có thể gọi 100s requests concurrently.
- **Local model inference** (Torch): dùng Multiprocessing hoặc chạy inference server riêng.
- **Numpy/Scipy operations**: Threading có thể OK vì C extensions release GIL.
- Python 3.13 đang thực nghiệm "free-threaded" mode (no GIL) — watch out!

---

### Q: Tại sao `requests` block event loop? Dùng `httpx.AsyncClient` và `run_in_executor` như thế nào?

**Đáp án:**
`requests` dùng blocking socket calls. Khi gọi `requests.get()` trong coroutine, nó **block toàn bộ event loop** — không có task nào khác chạy được trong thời gian đó. `httpx.AsyncClient` dùng async I/O nên nhường control cho event loop khi chờ network.

`run_in_executor` cho phép chạy blocking function trong thread pool, không block event loop.

```python
import asyncio
import httpx
import requests
from concurrent.futures import ThreadPoolExecutor

# BAD: blocks event loop
async def bad_fetch(url: str) -> str:
    # requests.get() là blocking — toàn bộ event loop bị freeze!
    response = requests.get(url)
    return response.text

# GOOD: httpx async client
async def good_fetch_httpx(url: str) -> str:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text

# GOOD: reuse client (recommended for production)
_http_client: httpx.AsyncClient | None = None

async def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )
    return _http_client

# GOOD: wrap legacy blocking code with run_in_executor
async def fetch_with_executor(url: str) -> str:
    """Dùng khi không thể thay thế requests (legacy SDK, etc.)"""
    loop = asyncio.get_running_loop()
    # Chạy blocking call trong thread pool — không block event loop
    response = await loop.run_in_executor(None, requests.get, url)
    return response.text

# Custom executor for CPU-bound work
_executor = ThreadPoolExecutor(max_workers=4)

async def run_cpu_task(data: list[float]) -> float:
    import math
    def heavy_compute(nums: list[float]) -> float:
        return sum(math.sqrt(abs(x)) for x in nums * 1000)

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(_executor, heavy_compute, data)
    return result

# Production pattern: fetch multiple URLs concurrently
async def fetch_multiple(urls: list[str]) -> list[str]:
    async with httpx.AsyncClient() as client:
        tasks = [client.get(url) for url in urls]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        results = []
        for resp in responses:
            if isinstance(resp, Exception):
                results.append(f"Error: {resp}")
            else:
                results.append(resp.text)
        return results
```

**Key points:**
- Bất kỳ blocking call nào (file I/O, `time.sleep`, blocking SDK) đều nên wrap bằng `run_in_executor`.
- `httpx.AsyncClient` nên được reuse (connection pooling) thay vì tạo mới mỗi request.
- Với LLM SDKs: `openai.AsyncOpenAI`, `anthropic.AsyncAnthropic` đều có async version.
- `aiofiles` cho async file I/O.

---

### Q: Dùng asyncio.Semaphore để rate-limit concurrent LLM calls như thế nào?

**Đáp án:**
Semaphore giới hạn số coroutine chạy đồng thời. Khi gọi LLM API, cần rate-limit để tránh bị 429 (rate limit exceeded) và kiểm soát chi phí.

```python
import asyncio
import time
from dataclasses import dataclass
from typing import AsyncIterator
import httpx

@dataclass
class LLMRateLimiter:
    max_concurrent: int = 10       # max concurrent requests
    requests_per_minute: int = 60  # RPM limit

    def __post_init__(self):
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        self._request_times: list[float] = []

    async def acquire(self):
        await self._semaphore.acquire()
        # Simple sliding window rate limit
        now = time.monotonic()
        self._request_times = [t for t in self._request_times if now - t < 60]
        if len(self._request_times) >= self.requests_per_minute:
            wait_time = 60 - (now - self._request_times[0])
            if wait_time > 0:
                await asyncio.sleep(wait_time)
        self._request_times.append(time.monotonic())

    def release(self):
        self._semaphore.release()

# Global rate limiter
_limiter = LLMRateLimiter(max_concurrent=5, requests_per_minute=50)

async def call_llm_with_rate_limit(prompt: str) -> str:
    await _limiter.acquire()
    try:
        async with httpx.AsyncClient() as client:
            # Simulate LLM API call
            await asyncio.sleep(0.1)
            return f"Response to: {prompt[:50]}"
    finally:
        _limiter.release()

# Cleaner pattern with context manager
class LLMSemaphore:
    def __init__(self, max_concurrent: int):
        self._sem = asyncio.Semaphore(max_concurrent)
        self._call_count = 0

    async def __aenter__(self):
        await self._sem.acquire()
        self._call_count += 1
        return self

    async def __aexit__(self, *args):
        self._sem.release()

llm_sem = LLMSemaphore(max_concurrent=10)

async def process_documents(docs: list[str]) -> list[str]:
    """Process nhiều documents với rate limiting."""
    async def process_one(doc: str) -> str:
        async with llm_sem:
            await asyncio.sleep(0.05)  # simulate API call
            return f"Processed: {doc[:30]}"

    return await asyncio.gather(*[process_one(doc) for doc in docs])

# Batch processing pattern
async def process_in_batches(
    items: list[str],
    batch_size: int = 10,
    delay_between_batches: float = 1.0,
) -> list[str]:
    results = []
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batch_results = await asyncio.gather(
            *[call_llm_with_rate_limit(item) for item in batch]
        )
        results.extend(batch_results)
        if i + batch_size < len(items):
            await asyncio.sleep(delay_between_batches)
    return results
```

**Key points:**
- `asyncio.Semaphore(n)` cho phép tối đa n coroutine acquire đồng thời.
- Luôn dùng `try/finally` hoặc `async with` để đảm bảo release.
- Kết hợp Semaphore + exponential backoff để xử lý 429 responses.
- `asyncio.BoundedSemaphore` raise error nếu release nhiều hơn acquire.

---

## Phần 2: Python Internals

---

### Q: Giải thích Protocol, TypeVar, Generic, Literal, TypedDict, Annotated trong Python type hints.

**Đáp án:**
Type hints nâng cao cho phép viết code type-safe, self-documenting, và IDE-friendly — đặc biệt quan trọng trong AI projects với nhiều abstractions.

```python
from typing import (
    TypeVar, Generic, Literal, Annotated, Protocol, runtime_checkable,
    TypedDict, Any
)
from dataclasses import dataclass

# --- Protocol: structural subtyping (duck typing with types) ---
@runtime_checkable
class Retriever(Protocol):
    """Bất kỳ class nào implement 2 methods này đều là Retriever."""
    async def retrieve(self, query: str, top_k: int) -> list[str]: ...
    def get_collection_name(self) -> str: ...

class VectorDBRetriever:
    """Không cần kế thừa Retriever — chỉ cần implement đúng interface."""
    async def retrieve(self, query: str, top_k: int) -> list[str]:
        return [f"doc_{i}" for i in range(top_k)]

    def get_collection_name(self) -> str:
        return "my_collection"

# runtime_checkable cho phép isinstance check
retriever = VectorDBRetriever()
print(isinstance(retriever, Retriever))  # True

# --- TypeVar và Generic ---
T = TypeVar("T")
InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")

class Pipeline(Generic[InputT, OutputT]):
    """Type-safe pipeline."""
    def __init__(self, steps: list[Any]):
        self.steps = steps

    def run(self, input: InputT) -> OutputT:
        result = input
        for step in self.steps:
            result = step(result)
        return result  # type: ignore

# --- Literal: chỉ cho phép giá trị cụ thể ---
ModelName = Literal["gpt-4", "gpt-3.5-turbo", "claude-3-opus", "claude-3-sonnet"]
EmbeddingModel = Literal["text-embedding-ada-002", "text-embedding-3-small"]

def create_llm_client(model: ModelName) -> Any:
    # type checker sẽ error nếu truyền sai tên model
    ...

# --- TypedDict: typed dictionary ---
class LLMConfig(TypedDict):
    model: ModelName
    temperature: float
    max_tokens: int
    system_prompt: str

class LLMConfigPartial(TypedDict, total=False):
    """total=False: tất cả keys đều optional."""
    temperature: float
    max_tokens: int

# --- Annotated: metadata cho type hints ---
from pydantic import Field
from typing import Annotated

# Dùng với Pydantic
PositiveFloat = Annotated[float, Field(gt=0)]
BoundedStr = Annotated[str, Field(min_length=1, max_length=1000)]

# Custom metadata
class RateLimit:
    def __init__(self, calls_per_minute: int):
        self.calls_per_minute = calls_per_minute

RateLimitedEndpoint = Annotated[str, RateLimit(60)]

# Annotated với FastAPI
from fastapi import FastAPI, Depends, Query

app = FastAPI()

async def get_search_params(
    query: Annotated[str, Query(min_length=1, max_length=200, description="Search query")],
    top_k: Annotated[int, Query(ge=1, le=100, description="Number of results")] = 10,
):
    return {"query": query, "top_k": top_k}
```

**Key points:**
- `Protocol` preferred hơn ABC khi muốn structural typing (không cần kế thừa).
- `Generic[T]` cho phép viết type-safe containers và utilities.
- `Literal` rất hữu ích để constrain model names, environment names.
- `TypedDict` tốt hơn `dict[str, Any]` khi làm việc với JSON responses.
- `Annotated` là foundation của FastAPI validation và Pydantic field metadata.

---

### Q: Pydantic v2 — field_validator, model_validator, computed_field, discriminated union là gì?

**Đáp án:**
Pydantic v2 (Rust core) nhanh hơn v1 đáng kể và có API thay đổi. Là backbone của FastAPI và nhiều AI frameworks.

```python
from pydantic import (
    BaseModel, Field, field_validator, model_validator,
    computed_field, ConfigDict, model_serializer, AliasChoices
)
from pydantic import discriminator_alias_path
from typing import Annotated, Literal, Union
from datetime import datetime

# --- field_validator ---
class DocumentChunk(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    content: str = Field(min_length=1, max_length=10_000)
    source: str
    chunk_index: int = Field(ge=0)
    embedding: list[float] | None = None

    @field_validator("source")
    @classmethod
    def validate_source_format(cls, v: str) -> str:
        """Validator chạy sau type coercion."""
        if not v.startswith(("http://", "https://", "file://", "s3://")):
            raise ValueError(f"source phải là URL hợp lệ, nhận: {v}")
        return v.lower()

    @field_validator("embedding")
    @classmethod
    def validate_embedding_dim(cls, v: list[float] | None) -> list[float] | None:
        if v is not None and len(v) not in (768, 1536, 3072):
            raise ValueError(f"Embedding dim phải là 768/1536/3072, nhận: {len(v)}")
        return v

# --- model_validator ---
class LLMRequest(BaseModel):
    model: str
    messages: list[dict]
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int | None = None
    stream: bool = False
    tools: list[dict] | None = None

    @model_validator(mode="after")
    def validate_consistency(self) -> "LLMRequest":
        """Chạy sau khi toàn bộ model đã được parse."""
        if self.tools and self.stream:
            raise ValueError("Tool use không hỗ trợ streaming mode")
        if self.max_tokens is None:
            # Set default dựa vào model
            self.max_tokens = 4096 if "gpt-4" in self.model else 2048
        return self

    @model_validator(mode="before")
    @classmethod
    def normalize_messages(cls, data: dict) -> dict:
        """Chạy trước khi parse — nhận raw dict."""
        if isinstance(data.get("messages"), str):
            data["messages"] = [{"role": "user", "content": data["messages"]}]
        return data

# --- computed_field ---
class RAGDocument(BaseModel):
    content: str
    source_url: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)

    @computed_field  # type: ignore[misc]
    @property
    def word_count(self) -> int:
        return len(self.content.split())

    @computed_field  # type: ignore[misc]
    @property
    def domain(self) -> str:
        from urllib.parse import urlparse
        return urlparse(self.source_url).netloc

# --- Discriminated Union ---
class TextContent(BaseModel):
    type: Literal["text"]
    text: str

class ImageContent(BaseModel):
    type: Literal["image"]
    url: str
    width: int
    height: int

class ToolCallContent(BaseModel):
    type: Literal["tool_call"]
    tool_name: str
    arguments: dict

# Discriminated union trên field "type"
MessageContent = Annotated[
    Union[TextContent, ImageContent, ToolCallContent],
    Field(discriminator="type")
]

class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: MessageContent | list[MessageContent]

# Parse: Pydantic tự chọn đúng subtype dựa vào "type" field
msg = Message(
    role="user",
    content={"type": "image", "url": "https://...", "width": 800, "height": 600}
)
print(type(msg.content))  # ImageContent
```

**Key points:**
- `field_validator` với `mode="before"` chạy trước type coercion.
- `model_validator(mode="after")` nhận instance đã validate.
- `computed_field` xuất hiện trong `.model_dump()` và JSON serialization.
- Discriminated union nhanh hơn Union thường (Pydantic biết ngay subtype nào để parse).
- `model_config = ConfigDict(...)` thay thế class `Config` của Pydantic v1.

---

### Q: Viết retry decorator với functools.wraps và parameterized decorator.

**Đáp án:**
Decorator pattern là kỹ năng Python core. Parameterized decorator (decorator nhận arguments) và async-compatible retry là điều thường gặp trong AI projects.

```python
import asyncio
import functools
import logging
import time
from typing import TypeVar, Callable, Any, Type

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

# --- Basic decorator với functools.wraps ---
def log_calls(func: F) -> F:
    @functools.wraps(func)  # giữ metadata: __name__, __doc__, __annotations__
    def wrapper(*args, **kwargs):
        logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
        result = func(*args, **kwargs)
        logger.debug(f"{func.__name__} returned {result}")
        return result
    return wrapper  # type: ignore

# --- Parameterized decorator ---
def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
):
    """
    Decorator factory: retry(max_attempts=3) trả về decorator thực sự.
    Support cả sync và async functions.
    """
    def decorator(func: F) -> F:
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                current_delay = delay
                last_exception: Exception | None = None
                for attempt in range(1, max_attempts + 1):
                    try:
                        return await func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        if attempt == max_attempts:
                            logger.error(
                                f"{func.__name__} failed after {max_attempts} attempts"
                            )
                            raise
                        logger.warning(
                            f"{func.__name__} attempt {attempt} failed: {e}. "
                            f"Retrying in {current_delay:.1f}s..."
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                raise last_exception  # type: ignore
            return async_wrapper  # type: ignore
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                current_delay = delay
                last_exception: Exception | None = None
                for attempt in range(1, max_attempts + 1):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        if attempt == max_attempts:
                            raise
                        logger.warning(f"Attempt {attempt} failed: {e}")
                        time.sleep(current_delay)
                        current_delay *= backoff
                raise last_exception  # type: ignore
            return sync_wrapper  # type: ignore
    return decorator

# Usage
@retry(max_attempts=3, delay=0.5, backoff=2.0, exceptions=(httpx.HTTPError,))
async def call_embedding_api(text: str) -> list[float]:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/embeddings",
            json={"input": text, "model": "text-embedding-3-small"},
        )
        response.raise_for_status()
        return response.json()["data"][0]["embedding"]

# --- Context manager: __enter__/__exit__ ---
class Timer:
    def __init__(self, name: str = ""):
        self.name = name
        self.elapsed: float = 0.0

    def __enter__(self) -> "Timer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.elapsed = time.perf_counter() - self._start
        print(f"[{self.name}] elapsed: {self.elapsed:.3f}s")
        return False  # không suppress exception

# --- asynccontextmanager ---
from contextlib import asynccontextmanager
from typing import AsyncIterator

@asynccontextmanager
async def managed_llm_session(model: str) -> AsyncIterator[dict]:
    """Resource management cho LLM sessions."""
    print(f"Opening session for {model}")
    session = {"model": model, "calls": 0}
    try:
        yield session
    except Exception as e:
        print(f"Session error: {e}")
        raise
    finally:
        print(f"Closing session. Total calls: {session['calls']}")

async def use_session():
    async with managed_llm_session("gpt-4") as session:
        session["calls"] += 1
        await asyncio.sleep(0.1)
```

**Key points:**
- `functools.wraps` giữ `__name__`, `__doc__`, `__annotations__` — quan trọng cho debugging và introspection.
- Parameterized decorator = decorator factory (function returns decorator).
- Kiểm tra `asyncio.iscoroutinefunction()` để support cả sync và async.
- `asynccontextmanager` dùng `yield` thay vì `__enter__`/`__exit__`.

---

### Q: Generator và yield from — giải thích lazy evaluation và ứng dụng trong AI.

**Đáp án:**
Generator là iterator mà Python tạo lazily — không tính toán tất cả values ngay lập tức. Quan trọng khi xử lý large datasets và streaming LLM responses.

```python
from typing import Iterator, AsyncIterator, Generator
import asyncio

# --- Basic generator ---
def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> Iterator[str]:
    """Lazy chunking — không load toàn bộ text vào memory cùng lúc."""
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        yield text[start:end]
        start = end - overlap if end < len(text) else end

# --- yield from: delegate to sub-generator ---
def process_multiple_files(file_paths: list[str]) -> Iterator[str]:
    for path in file_paths:
        with open(path, "r") as f:
            content = f.read()
        yield from chunk_text(content)  # delegate, không cần loop

# --- Generator pipeline ---
def read_lines(path: str) -> Iterator[str]:
    with open(path) as f:
        yield from f  # file object là iterator

def filter_empty(lines: Iterator[str]) -> Iterator[str]:
    for line in lines:
        if line.strip():
            yield line.strip()

def to_uppercase(lines: Iterator[str]) -> Iterator[str]:
    yield from (line.upper() for line in lines)

def pipeline(path: str) -> Iterator[str]:
    """Lazy pipeline — không allocate toàn bộ file vào memory."""
    lines = read_lines(path)
    lines = filter_empty(lines)
    lines = to_uppercase(lines)
    yield from lines

# --- Async generator: LLM streaming ---
async def stream_llm_response(prompt: str) -> AsyncIterator[str]:
    """Simulate streaming response từ LLM."""
    words = f"This is a streaming response to: {prompt}".split()
    for word in words:
        await asyncio.sleep(0.05)  # simulate network latency
        yield word + " "

async def consume_stream():
    full_response = ""
    async for token in stream_llm_response("tell me about asyncio"):
        print(token, end="", flush=True)
        full_response += token
    print()
    return full_response

# --- Generator as coroutine (send values) ---
def running_average() -> Generator[float, float, str]:
    """Generator nhận values qua .send()"""
    total = 0.0
    count = 0
    value = yield 0.0  # first yield
    while True:
        if value is None:
            return f"Final average: {total/count:.2f}"
        total += value
        count += 1
        value = yield total / count

def use_running_average():
    gen = running_average()
    next(gen)  # prime the generator
    print(gen.send(10.0))  # 10.0
    print(gen.send(20.0))  # 15.0
    print(gen.send(30.0))  # 20.0
```

**Key points:**
- Generators dùng O(1) memory thay vì O(n) — quan trọng khi xử lý triệu documents.
- `yield from` delegates và propagates exceptions.
- Async generators (`async def` + `yield`) là foundation của streaming LLM APIs.
- Generator pipeline: mỗi bước lazy, chỉ pull data khi cần.

---

### Q: Dataclass vs NamedTuple vs Pydantic — khi nào dùng cái nào?

**Đáp án:**
Ba cách tạo structured data trong Python, mỗi cái có tradeoff khác nhau:

```python
from dataclasses import dataclass, field, asdict
from typing import NamedTuple
from pydantic import BaseModel, Field
import sys

# --- NamedTuple: immutable, lightweight, tuple-compatible ---
class EmbeddingResult(NamedTuple):
    vector: list[float]
    model: str
    token_count: int
    latency_ms: float

result = EmbeddingResult(vector=[0.1, 0.2], model="ada-002", token_count=10, latency_ms=50.0)
print(result[0])           # tuple indexing works
print(result.vector)       # attribute access works
x, model, tokens, _ = result  # unpacking works

# --- Dataclass: mutable, feature-rich, no validation ---
@dataclass
class RetrievalResult:
    document: str
    score: float
    source: str
    metadata: dict = field(default_factory=dict)
    # field(repr=False) để không hiện trong repr
    _cache: dict = field(default_factory=dict, repr=False, compare=False)

    def __post_init__(self):
        # Light validation — không phải production-grade
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"Score phải trong [0,1], nhận {self.score}")

    @property
    def is_high_confidence(self) -> bool:
        return self.score > 0.8

@dataclass(frozen=True)  # immutable như NamedTuple
class CacheKey:
    query: str
    top_k: int
    model: str

# --- Pydantic: validation, serialization, API layer ---
class RAGRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=5, ge=1, le=50)
    filter_metadata: dict | None = None

    model_config = {"frozen": True}  # immutable after creation

# --- Khi nào dùng gì ---
# NamedTuple: internal data, return types, pattern matching, hashable keys
# Dataclass: internal models, mutable state, khi không cần validation
# Pydantic: API request/response, config, bất kỳ external input nào

# Memory comparison
import sys
nt = EmbeddingResult([0.1]*1536, "ada", 10, 50.0)
dc = RetrievalResult("text", 0.9, "url")
pm = RAGRequest(query="test", top_k=5)

# Pydantic objects có overhead hơn
print(f"NamedTuple: {sys.getsizeof(nt)} bytes")
print(f"Dataclass: {sys.getsizeof(dc)} bytes")
```

**Key points:**
- **NamedTuple**: dùng cho return types, hashable (có thể dùng làm dict key), memory-efficient.
- **Dataclass**: dùng cho internal domain objects, config classes, không cần validation.
- **Pydantic**: dùng cho bất kỳ data nào đến từ external (HTTP request, JSON file, env vars).
- `@dataclass(frozen=True)` ~ NamedTuple nhưng không tuple-compatible.
- `__slots__` trong dataclass giảm memory: `@dataclass(slots=True)` (Python 3.10+).

---

## Phần 3: Python Patterns trong AI Projects

---

### Q: Dependency Injection với FastAPI Depends — ví dụ inject LLM client.

**Đáp án:**
FastAPI's `Depends` là DI framework nhẹ, hỗ trợ async, có thể nest dependencies. Quan trọng cho testability và resource management.

```python
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from typing import Annotated
import httpx

app = FastAPI()

# --- LLM Client dependency ---
class LLMClient:
    def __init__(self, api_key: str, model: str, http_client: httpx.AsyncClient):
        self.api_key = api_key
        self.model = model
        self._http = http_client

    async def complete(self, prompt: str, **kwargs) -> str:
        # Simulate API call
        return f"[{self.model}] Response to: {prompt[:50]}"

    async def embed(self, text: str) -> list[float]:
        return [0.1] * 1536

class VectorDB:
    def __init__(self, connection_string: str):
        self.conn = connection_string

    async def search(self, vector: list[float], top_k: int) -> list[dict]:
        return [{"content": f"doc_{i}", "score": 0.9 - i*0.1} for i in range(top_k)]

# --- Dependency functions ---
_http_client: httpx.AsyncClient | None = None

async def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=30.0)
    return _http_client

async def get_llm_client(
    http_client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
) -> LLMClient:
    import os
    return LLMClient(
        api_key=os.environ.get("OPENAI_API_KEY", "test-key"),
        model="gpt-4",
        http_client=http_client,
    )

async def get_vector_db() -> VectorDB:
    import os
    return VectorDB(os.environ.get("VECTOR_DB_URL", "localhost:6333"))

# --- Nested dependency: RAG pipeline ---
class RAGPipeline:
    def __init__(self, llm: LLMClient, db: VectorDB):
        self.llm = llm
        self.db = db

    async def query(self, question: str, top_k: int = 5) -> str:
        embedding = await self.llm.embed(question)
        docs = await self.db.search(embedding, top_k)
        context = "\n".join(d["content"] for d in docs)
        return await self.llm.complete(f"Context: {context}\n\nQ: {question}")

async def get_rag_pipeline(
    llm: Annotated[LLMClient, Depends(get_llm_client)],
    db: Annotated[VectorDB, Depends(get_vector_db)],
) -> RAGPipeline:
    return RAGPipeline(llm=llm, db=db)

# --- FastAPI endpoint ---
class QueryRequest(BaseModel):
    question: str
    top_k: int = 5

@app.post("/query")
async def query_endpoint(
    request: QueryRequest,
    rag: Annotated[RAGPipeline, Depends(get_rag_pipeline)],
) -> dict:
    answer = await rag.query(request.question, request.top_k)
    return {"question": request.question, "answer": answer}

# --- Lifespan management ---
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    global _http_client
    _http_client = httpx.AsyncClient(timeout=30.0)
    yield
    # shutdown
    if _http_client:
        await _http_client.aclose()

app = FastAPI(lifespan=lifespan)
```

**Key points:**
- Dependencies được cache trong request scope mặc định (chỉ gọi 1 lần/request).
- `Depends` có thể dùng với class (`Depends(MyClass)`) — gọi `__init__`.
- Dùng `lifespan` để manage long-lived resources (HTTP clients, DB connections).
- Trong tests: `app.dependency_overrides[get_llm_client] = mock_llm_client`.

---

### Q: Thiết kế Abstract Base Class cho RAG components — Retriever, Reranker interface.

**Đáp án:**
ABC cho phép định nghĩa interface contracts, enforce implementation, và enable strategy switching. Kết hợp với Protocol cho flexibility tối đa.

```python
from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable, NamedTuple
from dataclasses import dataclass

# --- Domain models ---
@dataclass(frozen=True)
class Document:
    content: str
    doc_id: str
    source: str
    metadata: dict

@dataclass
class RetrievalResult:
    document: Document
    score: float
    rank: int

# --- Abstract Base Classes ---
class BaseRetriever(ABC):
    """ABC: enforce interface và cung cấp shared logic."""

    @abstractmethod
    async def retrieve(self, query: str, top_k: int = 10) -> list[RetrievalResult]:
        """Retrieve relevant documents for a query."""
        ...

    @abstractmethod
    async def add_documents(self, documents: list[Document]) -> None:
        """Add documents to the retriever's index."""
        ...

    @abstractmethod
    async def delete_documents(self, doc_ids: list[str]) -> None:
        """Delete documents by ID."""
        ...

    # Shared logic (không abstract) — tái dùng ở mọi subclass
    async def retrieve_and_format(self, query: str, top_k: int = 10) -> str:
        results = await self.retrieve(query, top_k)
        return "\n\n".join(
            f"[{r.rank}] (score={r.score:.3f}) {r.document.content}"
            for r in results
        )

class BaseReranker(ABC):
    @abstractmethod
    async def rerank(
        self,
        query: str,
        results: list[RetrievalResult],
        top_n: int = 5,
    ) -> list[RetrievalResult]:
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...

# --- Concrete implementations ---
class VectorRetriever(BaseRetriever):
    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        self._index: dict[str, Document] = {}

    async def retrieve(self, query: str, top_k: int = 10) -> list[RetrievalResult]:
        # Simulate vector search
        docs = list(self._index.values())[:top_k]
        return [
            RetrievalResult(document=doc, score=0.9 - i*0.05, rank=i+1)
            for i, doc in enumerate(docs)
        ]

    async def add_documents(self, documents: list[Document]) -> None:
        for doc in documents:
            self._index[doc.doc_id] = doc

    async def delete_documents(self, doc_ids: list[str]) -> None:
        for doc_id in doc_ids:
            self._index.pop(doc_id, None)

class CrossEncoderReranker(BaseReranker):
    def __init__(self, model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self._model_name = model

    @property
    def model_name(self) -> str:
        return self._model_name

    async def rerank(
        self, query: str, results: list[RetrievalResult], top_n: int = 5
    ) -> list[RetrievalResult]:
        # Simulate reranking scores
        reranked = sorted(results, key=lambda r: r.score, reverse=True)
        return [
            RetrievalResult(document=r.document, score=r.score, rank=i+1)
            for i, r in enumerate(reranked[:top_n])
        ]

# --- RAG Pipeline dùng abstractions ---
class RAGPipeline:
    def __init__(
        self,
        retriever: BaseRetriever,
        reranker: BaseReranker | None = None,
    ):
        self._retriever = retriever
        self._reranker = reranker

    async def run(self, query: str, top_k: int = 10, rerank_top_n: int = 5) -> list[RetrievalResult]:
        results = await self._retriever.retrieve(query, top_k)
        if self._reranker:
            results = await self._reranker.rerank(query, results, rerank_top_n)
        return results
```

**Key points:**
- ABC enforce implementation — `TypeError` khi instantiate class chưa implement abstract methods.
- `@property @abstractmethod` cho phép enforce abstract properties.
- Kết hợp ABC với Protocol: ABC cho internal hierarchy, Protocol cho external interfaces.
- Dùng ABC khi muốn shared implementation (template method pattern).

---

### Q: Strategy Pattern cho LLM provider switching và Builder Pattern cho prompt.

**Đáp án:**
Strategy pattern cho phép swap LLM providers (OpenAI, Anthropic, Ollama) mà không thay đổi business logic. Builder pattern giúp tạo prompts phức tạp một cách có cấu trúc.

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator

# --- Strategy Pattern: LLM Provider ---
@dataclass
class LLMResponse:
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    finish_reason: str

class LLMStrategy(ABC):
    """Strategy interface."""

    @abstractmethod
    async def complete(self, messages: list[dict], **kwargs) -> LLMResponse:
        ...

    @abstractmethod
    async def stream(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        ...

    @property
    @abstractmethod
    def model_id(self) -> str:
        ...

class OpenAIStrategy(LLMStrategy):
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self._model = model
        self._api_key = api_key

    @property
    def model_id(self) -> str:
        return self._model

    async def complete(self, messages: list[dict], **kwargs) -> LLMResponse:
        # Real implementation would use openai.AsyncOpenAI
        return LLMResponse(
            content="OpenAI response",
            model=self._model,
            input_tokens=100,
            output_tokens=50,
            finish_reason="stop",
        )

    async def stream(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        for word in "OpenAI streaming response".split():
            yield word + " "

class AnthropicStrategy(LLMStrategy):
    def __init__(self, api_key: str, model: str = "claude-3-sonnet-20240229"):
        self._model = model
        self._api_key = api_key

    @property
    def model_id(self) -> str:
        return self._model

    async def complete(self, messages: list[dict], **kwargs) -> LLMResponse:
        return LLMResponse(
            content="Anthropic response",
            model=self._model,
            input_tokens=100,
            output_tokens=50,
            finish_reason="end_turn",
        )

    async def stream(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        for word in "Anthropic streaming response".split():
            yield word + " "

class LLMContext:
    """Context: sử dụng strategy và cho phép swap runtime."""

    def __init__(self, strategy: LLMStrategy):
        self._strategy = strategy

    def set_strategy(self, strategy: LLMStrategy) -> None:
        self._strategy = strategy

    async def complete(self, messages: list[dict], **kwargs) -> LLMResponse:
        return await self._strategy.complete(messages, **kwargs)

    async def stream(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        return self._strategy.stream(messages, **kwargs)

# --- Builder Pattern: Prompt Builder ---
@dataclass
class Prompt:
    system: str
    messages: list[dict] = field(default_factory=list)
    tools: list[dict] = field(default_factory=list)
    max_tokens: int = 2048
    temperature: float = 0.7

class PromptBuilder:
    """Builder pattern: build Prompt step by step."""

    def __init__(self):
        self._system: str = ""
        self._messages: list[dict] = []
        self._tools: list[dict] = []
        self._max_tokens: int = 2048
        self._temperature: float = 0.7
        self._examples: list[tuple[str, str]] = []

    def with_system(self, system: str) -> "PromptBuilder":
        self._system = system
        return self  # method chaining

    def with_role(self, role: str) -> "PromptBuilder":
        self._system += f"\n\nYou are a {role}."
        return self

    def with_context(self, context: str) -> "PromptBuilder":
        self._messages.append({
            "role": "system",
            "content": f"<context>\n{context}\n</context>",
        })
        return self

    def with_few_shot_examples(self, examples: list[tuple[str, str]]) -> "PromptBuilder":
        for user_msg, assistant_msg in examples:
            self._messages.extend([
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": assistant_msg},
            ])
        return self

    def with_user_message(self, message: str) -> "PromptBuilder":
        self._messages.append({"role": "user", "content": message})
        return self

    def with_tools(self, tools: list[dict]) -> "PromptBuilder":
        self._tools = tools
        return self

    def with_temperature(self, temperature: float) -> "PromptBuilder":
        self._temperature = temperature
        return self

    def with_max_tokens(self, max_tokens: int) -> "PromptBuilder":
        self._max_tokens = max_tokens
        return self

    def build(self) -> Prompt:
        if not self._system:
            raise ValueError("System prompt is required")
        if not self._messages:
            raise ValueError("At least one message is required")
        return Prompt(
            system=self._system,
            messages=self._messages,
            tools=self._tools,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
        )

# Usage
prompt = (
    PromptBuilder()
    .with_system("You are a helpful assistant specialized in Python.")
    .with_role("senior Python engineer")
    .with_context("The codebase uses FastAPI, Pydantic v2, and asyncio.")
    .with_few_shot_examples([
        ("What is a coroutine?", "A coroutine is a function defined with `async def`..."),
    ])
    .with_user_message("Explain asyncio.gather vs asyncio.wait")
    .with_temperature(0.3)
    .with_max_tokens(1000)
    .build()
)
```

**Key points:**
- Strategy pattern: interface chung, swap implementation tại runtime.
- Builder pattern: ngăn "telescoping constructor" với nhiều optional params.
- Method chaining (fluent interface) làm Builder dễ đọc hơn.
- `build()` nên validate và raise nếu required fields thiếu.

---

### Q: Implement Singleton pattern cho LLM client thread-safe và tenacity retry.

**Đáp án:**
Singleton đảm bảo chỉ có 1 instance LLM client (connection pool, token budget tracking). Thread-safe implementation cần lock. Tenacity là thư viện retry mạnh mẽ hơn custom decorator.

```python
import threading
import asyncio
from typing import ClassVar
import httpx

# --- Thread-safe Singleton ---
class LLMClientSingleton:
    _instance: ClassVar["LLMClientSingleton | None"] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def __new__(cls) -> "LLMClientSingleton":
        if cls._instance is None:
            with cls._lock:
                # Double-checked locking
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_connections=50),
        )
        self._total_tokens = 0
        self._token_lock = threading.Lock()

    def track_tokens(self, tokens: int) -> None:
        with self._token_lock:
            self._total_tokens += tokens

    @property
    def total_tokens_used(self) -> int:
        with self._token_lock:
            return self._total_tokens

    async def close(self) -> None:
        await self._http_client.aclose()

    @classmethod
    def reset(cls) -> None:
        """Chỉ dùng trong tests."""
        with cls._lock:
            cls._instance = None

# Async-native singleton với asyncio.Lock
class AsyncLLMClientSingleton:
    _instance: ClassVar["AsyncLLMClientSingleton | None"] = None
    _async_lock: ClassVar[asyncio.Lock | None] = None

    @classmethod
    async def get_instance(cls) -> "AsyncLLMClientSingleton":
        if cls._async_lock is None:
            cls._async_lock = asyncio.Lock()
        if cls._instance is None:
            async with cls._async_lock:
                if cls._instance is None:
                    instance = cls.__new__(cls)
                    await instance._initialize()
                    cls._instance = instance
        return cls._instance

    async def _initialize(self) -> None:
        self._client = httpx.AsyncClient()
        self._call_count = 0

    async def call(self, prompt: str) -> str:
        self._call_count += 1
        return f"Response #{self._call_count}"

# --- Tenacity retry ---
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log,
    RetryError,
)
import logging

logger = logging.getLogger(__name__)

class RateLimitError(Exception):
    pass

class ServerError(Exception):
    pass

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=60),
    retry=retry_if_exception_type((RateLimitError, ServerError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    after=after_log(logger, logging.DEBUG),
    reraise=True,  # raise original exception sau max attempts
)
async def call_llm_with_tenacity(prompt: str) -> str:
    """Tenacity tự động retry với exponential backoff."""
    import random
    if random.random() < 0.3:  # simulate 30% failure rate
        raise RateLimitError("429 Too Many Requests")
    return f"Response: {prompt[:50]}"

# Custom retry condition
from tenacity import retry_if_result

def is_empty_response(result: str) -> bool:
    return not result or result.strip() == ""

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5),
    retry=(
        retry_if_exception_type(RateLimitError) |
        retry_if_result(is_empty_response)
    ),
)
async def call_with_result_check(prompt: str) -> str:
    return ""  # sẽ bị retry vì empty

# Usage
async def main():
    try:
        result = await call_llm_with_tenacity("What is asyncio?")
        print(result)
    except RetryError as e:
        print(f"All retries failed: {e}")

    # Singleton usage
    client1 = LLMClientSingleton()
    client2 = LLMClientSingleton()
    print(client1 is client2)  # True
```

**Key points:**
- Double-checked locking trong `__new__` cho thread-safe singleton.
- `asyncio.Lock` cho async context — không dùng `threading.Lock` trong async code.
- Tenacity cung cấp `stop_after_attempt`, `wait_exponential`, `retry_if_exception_type` — linh hoạt hơn custom decorator.
- Kết hợp retry conditions với `|` (OR) hoặc `&` (AND).
- Luôn cung cấp `reset()` classmethods để test có thể reset singleton.

---

### Q: Memory management với __slots__ và reference counting trong Python.

**Đáp án:**
Python dùng reference counting + cyclic garbage collector. `__slots__` thay thế `__dict__` để giảm memory — quan trọng khi tạo hàng triệu object (embedding vectors, tokens).

```python
import sys
import gc
from dataclasses import dataclass

# --- Regular class vs __slots__ ---
class RegularEmbedding:
    def __init__(self, vector: list[float], doc_id: str):
        self.vector = vector
        self.doc_id = doc_id
        # Python tạo __dict__ = {'vector': ..., 'doc_id': ...}
        # Mỗi instance có overhead của dict

class SlottedEmbedding:
    __slots__ = ("vector", "doc_id")  # chỉ cho phép các attributes này

    def __init__(self, vector: list[float], doc_id: str):
        self.vector = vector
        self.doc_id = doc_id
        # Không có __dict__ — memory layout như C struct

# Memory comparison
regular = RegularEmbedding([0.1] * 10, "doc_1")
slotted = SlottedEmbedding([0.1] * 10, "doc_1")

print(f"Regular: {sys.getsizeof(regular)} bytes")  # ~48 bytes + dict overhead
print(f"Slotted: {sys.getsizeof(slotted)} bytes")  # ~56 bytes but no __dict__
print(f"Regular __dict__: {sys.getsizeof(regular.__dict__)} bytes")  # ~232 bytes!

# --- Dataclass với slots (Python 3.10+) ---
@dataclass(slots=True)
class TokenBatch:
    tokens: list[int]
    attention_mask: list[int]
    doc_id: str

# --- Reference counting ---
import ctypes

def ref_count(obj) -> int:
    return ctypes.c_long.from_address(id(obj)).value

x = [1, 2, 3]
print(f"After creation: {ref_count(x)}")    # 2 (x + function arg)

y = x
print(f"After y = x: {ref_count(x)}")      # 3

del y
print(f"After del y: {ref_count(x)}")      # 2

# --- Circular reference + gc ---
class Node:
    def __init__(self, value):
        self.value = value
        self.next: "Node | None" = None

    def __del__(self):
        print(f"Node {self.value} deleted")

# Circular reference — không được freed bởi ref counting
a = Node(1)
b = Node(2)
a.next = b
b.next = a  # circular!

del a, b
# Nodes không bị xóa ngay — cần gc.collect()
gc.collect()  # garbage collector xử lý cycles

# --- Memory-efficient pattern cho large datasets ---
class EmbeddingStore:
    """Sử dụng slots và weak references để giảm memory."""
    __slots__ = ("_store", "_max_size")

    def __init__(self, max_size: int = 10_000):
        self._store: dict[str, list[float]] = {}
        self._max_size = max_size

    def add(self, doc_id: str, embedding: list[float]) -> None:
        if len(self._store) >= self._max_size:
            # Simple LRU: xóa entry đầu tiên
            oldest = next(iter(self._store))
            del self._store[oldest]
        self._store[doc_id] = embedding

    def get(self, doc_id: str) -> list[float] | None:
        return self._store.get(doc_id)
```

**Key points:**
- `__slots__` tiết kiệm ~30-50% memory khi có hàng triệu instances.
- Không thể thêm attributes mới vào slotted class.
- `weakref` module cho phép tham chiếu object mà không tăng ref count.
- Cyclic garbage collector chạy tự động nhưng có thể trigger bằng `gc.collect()`.
- `sys.getsizeof()` không đếm recursive size (dùng `pympler` cho accurate measurement).

---

## Bonus: Interview Rapid-fire Questions

### Q: Phân biệt `__init__` vs `__new__` vs `__post_init__`

**Đáp án:**
- `__new__`: class method, tạo và trả về instance mới. Chạy trước `__init__`. Dùng cho Singleton, immutable objects.
- `__init__`: instance method, initialize object đã được tạo. Không trả về gì (return None).
- `__post_init__`: chỉ có trong `@dataclass`. Gọi tự động sau `__init__` được generate.

```python
class Singleton:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, value: int):
        self.value = value  # __init__ gọi mỗi lần, __new__ chỉ gọi lần đầu

from dataclasses import dataclass

@dataclass
class Config:
    host: str
    port: int
    url: str = ""

    def __post_init__(self):
        # Validation và computed fields sau khi __init__ chạy
        if self.port < 0 or self.port > 65535:
            raise ValueError(f"Invalid port: {self.port}")
        self.url = f"http://{self.host}:{self.port}"
```

**Key points:**
- `__new__` ít khi cần override — chỉ dùng cho metaclass, immutable types, Singleton.
- `__post_init__` phổ biến trong dataclass để validate và compute derived fields.

---

### Q: `*args` và `**kwargs` forwarding, và keyword-only arguments

```python
from typing import Any

def wrapper(func):
    def inner(*args: Any, **kwargs: Any) -> Any:
        print(f"Before: args={args}, kwargs={kwargs}")
        return func(*args, **kwargs)
    return inner

# Keyword-only arguments (sau *)
def create_embedding(
    text: str,
    *,                          # tất cả sau * là keyword-only
    model: str = "ada-002",
    normalize: bool = True,
    batch_size: int = 100,
) -> list[float]:
    return [0.1] * 1536

# Phải gọi với keyword:
create_embedding("hello", model="ada-002", normalize=False)
# create_embedding("hello", "ada-002")  # TypeError!

# Positional-only (trước /)
def distance(x: float, y: float, /, metric: str = "cosine") -> float:
    return 0.0

distance(1.0, 2.0, metric="euclidean")  # OK
# distance(x=1.0, y=2.0)  # TypeError — x, y are positional-only
```

**Key points:**
- `*` trong signature bắt buộc caller phải dùng keyword args — API rõ ràng hơn.
- `/` trong signature (Python 3.8+) cho positional-only params.
- Kết hợp: `def f(pos_only, /, normal, *, kw_only)`.

---

*Tổng hợp: Module 6 bao gồm 15+ code examples thực tế từ Async/Concurrency, Python Internals đến Design Patterns cho AI projects. Phù hợp cho vị trí Senior Python/AI Engineer.*

---

## Phần 4: Python Performance — Quant Engineering (WorldQuant focus)

> Section này dành cho roles đòi hỏi xử lý dữ liệu lớn: quant trading, data engineering, financial systems.

---

### Q: GIL là gì? Khi nào nó là vấn đề, khi nào không?

**Đáp án:**

GIL (Global Interpreter Lock) là mutex trong CPython ngăn nhiều thread thực thi Python bytecode đồng thời.

```
Thread 1: [====GIL====]  ........  [====GIL====]
Thread 2: ............  [====GIL====]  ...........
           ^ Chỉ 1 thread giữ GIL tại một thời điểm
```

**Khi GIL KHÔNG phải vấn đề:**
- I/O-bound tasks: GIL được release khi thread đang chờ I/O (network, disk)
- Calls to C extensions: NumPy, Pandas release GIL trong computation → threads thực sự song song
- asyncio: single-threaded, không cần GIL

**Khi GIL LÀ vấn đề:**
- CPU-bound pure Python code (loops, calculations)
- Cannot get true parallelism with threading for CPU-bound work

**Fix:**
```python
# CPU-bound → dùng multiprocessing (separate process = separate GIL)
from concurrent.futures import ProcessPoolExecutor

def compute_alpha(stock_data: list[float]) -> float:
    # Heavy CPU computation
    return sum(x**2 for x in stock_data) / len(stock_data)

with ProcessPoolExecutor(max_workers=8) as executor:
    # 8 processes, each with own GIL, true parallelism
    results = list(executor.map(compute_alpha, all_stocks_data))
```

---

### Q: asyncio vs threading vs multiprocessing — chọn cái nào?

**Đáp án:**

```
Task type          → Tool                    → Why
─────────────────────────────────────────────────────────────
I/O-bound async    → asyncio                 → Event loop, zero thread overhead
I/O-bound sync     → ThreadPoolExecutor      → GIL released during I/O
CPU-bound          → ProcessPoolExecutor     → Bypasses GIL, true parallelism
Mixed I/O + CPU    → asyncio + ProcessPool   → Async for I/O, process for compute
```

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import time

# === Pattern 1: asyncio cho I/O-bound (HTTP, DB) ===
async def fetch_stock_price(symbol: str) -> float:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"https://api.market.com/price/{symbol}")
        return resp.json()["price"]

async def fetch_all_prices(symbols: list[str]) -> list[float]:
    return await asyncio.gather(*[fetch_stock_price(s) for s in symbols])
    # 1000 symbols fetched concurrently, ~same time as 1

# === Pattern 2: ThreadPoolExecutor cho blocking I/O ===
def read_csv_file(path: str) -> pd.DataFrame:
    return pd.read_csv(path)  # Blocking I/O

async def load_all_files(paths: list[str]) -> list[pd.DataFrame]:
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=10) as pool:
        tasks = [loop.run_in_executor(pool, read_csv_file, p) for p in paths]
        return await asyncio.gather(*tasks)

# === Pattern 3: ProcessPoolExecutor cho CPU-bound ===
def backtest_strategy(params: dict) -> dict:
    """CPU-intensive: simulates strategy over 10 years of data."""
    prices = load_prices(params["symbol"])
    signals = compute_signals(prices, params)
    returns = simulate_trades(signals, prices)
    return {"sharpe": compute_sharpe(returns), "params": params}

def parallel_backtest(param_grid: list[dict]) -> list[dict]:
    """Backtest 1000 parameter combinations in parallel."""
    with ProcessPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(backtest_strategy, param_grid))
    return sorted(results, key=lambda x: x["sharpe"], reverse=True)

# Benchmark: 1000 backtests
# Sequential:    1000 × 0.5s = 500s
# 8 processes:   1000 × 0.5s / 8 = 62.5s  (8x speedup)
```

---

### Q: NumPy vectorization — tại sao nhanh hơn Python loop?

**Đáp án:**

Python loop chậm vì: boxing/unboxing Python objects, interpreter overhead, dynamic typing.
NumPy nhanh vì: C implementation, SIMD instructions, contiguous memory layout, no boxing.

```python
import numpy as np
import time

prices = np.random.uniform(100, 200, size=10_000_000)  # 10M prices

# === BAD: Python loop ===
def moving_avg_loop(prices: list, window: int) -> list:
    result = []
    for i in range(window - 1, len(prices)):
        result.append(sum(prices[i-window+1:i+1]) / window)
    return result

# === GOOD: NumPy vectorized ===
def moving_avg_numpy(prices: np.ndarray, window: int) -> np.ndarray:
    # np.cumsum trick: O(n) computation, fully vectorized
    cumsum = np.cumsum(np.insert(prices, 0, 0))
    return (cumsum[window:] - cumsum[:-window]) / window

# Benchmark
start = time.perf_counter()
_ = moving_avg_loop(prices.tolist(), 20)
print(f"Loop: {time.perf_counter()-start:.2f}s")   # ~15s

start = time.perf_counter()
_ = moving_avg_numpy(prices, 20)
print(f"NumPy: {time.perf_counter()-start:.3f}s")  # ~0.05s  → 300x faster

# === Vectorized patterns for financial data ===

# Daily returns (% change)
returns = np.diff(prices) / prices[:-1]           # Vectorized, no loop

# Z-score normalization
z_scores = (prices - prices.mean()) / prices.std()

# Rolling correlation (use stride tricks for performance)
def rolling_std(arr: np.ndarray, window: int) -> np.ndarray:
    shape = arr.shape[:-1] + (arr.shape[-1] - window + 1, window)
    strides = arr.strides + (arr.strides[-1],)
    rolling = np.lib.stride_tricks.as_strided(arr, shape=shape, strides=strides)
    return rolling.std(axis=-1)

# Boolean masking (avoid if/else loops)
buy_signals = (returns > 0.02) & (volume > volume.mean())  # Element-wise
filtered_prices = prices[buy_signals]  # Fancy indexing, no loop
```

---

### Q: Pandas performance — các lỗi phổ biến và cách fix

**Đáp án:**

```python
import pandas as pd
import numpy as np

df = pd.DataFrame({
    "symbol": ["AAPL"] * 1_000_000,
    "price": np.random.uniform(100, 200, 1_000_000),
    "volume": np.random.randint(1000, 1_000_000, 1_000_000),
    "sector": np.random.choice(["Tech", "Finance", "Health"], 1_000_000)
})

# === ANTI-PATTERN 1: iterrows() ===
# Cực chậm: converts each row to Series (boxing overhead)
def bad_compute_return(df):
    results = []
    for _, row in df.iterrows():   # O(n) Python iterations
        results.append(row["price"] * 0.01)
    return results

# FIX: vectorize
def good_compute_return(df):
    return df["price"] * 0.01     # Single C-level operation

# Benchmark: iterrows = 45s, vectorize = 0.003s → 15,000x faster

# === ANTI-PATTERN 2: apply() when vectorize possible ===
bad = df["price"].apply(lambda x: x * 0.01)   # Python function per row
good = df["price"] * 0.01                      # C-level

# apply() is OK for: string ops, complex custom logic, row-wise with multiple cols
df["signal"] = df.apply(
    lambda row: "buy" if row["price"] > 150 and row["volume"] > 500_000 else "hold",
    axis=1
)
# Better:
df["signal"] = np.where(
    (df["price"] > 150) & (df["volume"] > 500_000), "buy", "hold"
)

# === MEMORY OPTIMIZATION: dtypes ===
print(df.memory_usage(deep=True).sum() / 1e6, "MB")  # Before: ~85 MB

# Downcast numerics
df["price"] = pd.to_numeric(df["price"], downcast="float")   # float64 → float32
df["volume"] = pd.to_numeric(df["volume"], downcast="integer")  # int64 → int32

# Categorical for low-cardinality strings (huge savings)
df["symbol"] = df["symbol"].astype("category")  # 1M strings → enum integers
df["sector"] = df["sector"].astype("category")

print(df.memory_usage(deep=True).sum() / 1e6, "MB")  # After: ~18 MB → 5x reduction

# === CHUNKING for files larger than RAM ===
def process_large_csv(path: str, chunk_size: int = 100_000) -> pd.DataFrame:
    results = []
    for chunk in pd.read_csv(path, chunksize=chunk_size):
        # Process each chunk without loading full file
        chunk_result = chunk.groupby("symbol")["price"].mean()
        results.append(chunk_result)
    return pd.concat(results).groupby(level=0).mean()
```

---

### Q: "You have 500M rows of tick data to process in Python. What's your approach?"

**Đáp án chuẩn WorldQuant-style:**

```
Step 1: Không load toàn bộ vào memory
  → Chunked processing với pandas hoặc dùng Dask/Polars

Step 2: Format hiệu quả
  → Convert CSV → Parquet (columnar, compressed, 5-10x smaller)
  → Parquet hỗ trợ predicate pushdown (chỉ đọc rows/columns cần)

Step 3: Vectorize toàn bộ computation
  → NumPy/Pandas vectorization, tránh loops
  → Dùng numba @jit cho custom computations

Step 4: Parallelize nếu cần
  → ProcessPoolExecutor: split data by symbol/date, parallel processing
  → Dask: distributed pandas trên multiple cores/machines
```

```python
import dask.dataframe as dd
import pyarrow.parquet as pq
import pyarrow as pa

# === Convert tick data to Parquet ===
def csv_to_parquet(input_csv: str, output_parquet: str):
    for i, chunk in enumerate(pd.read_csv(input_csv, chunksize=1_000_000)):
        # Optimize dtypes per chunk
        chunk["price"] = chunk["price"].astype("float32")
        chunk["volume"] = chunk["volume"].astype("int32")
        chunk["symbol"] = chunk["symbol"].astype("category")

        # Write to partitioned Parquet
        table = pa.Table.from_pandas(chunk)
        pq.write_to_dataset(
            table,
            root_path=output_parquet,
            partition_cols=["symbol"],  # Partition by symbol for fast lookups
        )

# === Dask for out-of-core processing ===
def analyze_with_dask(parquet_path: str) -> pd.DataFrame:
    ddf = dd.read_parquet(parquet_path, engine="pyarrow")

    # Dask builds lazy computation graph
    result = (
        ddf
        .assign(returns=ddf["price"].pct_change())
        .groupby("symbol")["returns"]
        .agg(["mean", "std"])
    )

    # Only executes here (.compute() triggers actual processing)
    return result.compute()  # Distributes across all CPU cores automatically

# === numba for custom numeric code ===
from numba import jit
import numpy as np

@jit(nopython=True, parallel=True)  # Compiles to machine code, SIMD parallel
def compute_ema(prices: np.ndarray, alpha: float) -> np.ndarray:
    result = np.empty_like(prices)
    result[0] = prices[0]
    for i in range(1, len(prices)):
        result[i] = alpha * prices[i] + (1 - alpha) * result[i-1]
    return result

# First call: ~0.5s (JIT compilation)
# Subsequent calls: microseconds (pre-compiled machine code)
```

---

### Quick Reference: Python Performance

```
PICK YOUR TOOL
════════════════════════════════════════════════════════
I/O-bound (async-native):   asyncio + await
I/O-bound (blocking libs):  ThreadPoolExecutor
CPU-bound:                   ProcessPoolExecutor
Numeric compute:             NumPy / Numba @jit
Large DataFrames:            Dask / Polars
Out-of-core data:            Parquet + chunked reads

NUMPY PATTERNS
════════════════════════════════════════════════════════
Returns:          np.diff(prices) / prices[:-1]
Z-score:          (arr - arr.mean()) / arr.std()
Rolling mean:     cumsum trick (O(n), no loop)
Boolean mask:     arr[(arr > threshold) & (arr < cap)]
Clip:             np.clip(arr, lower, upper)

PANDAS ANTI-PATTERNS → FIX
════════════════════════════════════════════════════════
iterrows()        → Vectorized column ops or np.where
apply(lambda)     → Vectorized when possible
string object     → .astype("category") for low-cardinality
float64           → float32 (half memory, same precision for prices)
int64             → int32 or int16 where range allows
Load full file    → read_csv(chunksize=N) or Dask

MEMORY REDUCTION CHECKLIST
  ✓ category dtype for symbol/sector columns
  ✓ float32 instead of float64 for prices
  ✓ __slots__ for custom objects created at scale
  ✓ Parquet instead of CSV (5-10x compression)
  ✓ Generators instead of lists for pipelines
════════════════════════════════════════════════════════
```
