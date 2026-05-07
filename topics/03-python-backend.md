# Python / FastAPI / Backend — Question Bank

## EASY

### PY-E01: Python GIL
**Câu hỏi:** GIL trong Python là gì? Ảnh hưởng gì đến multithreading?
**Keywords:** Global Interpreter Lock, CPU-bound vs I/O-bound, multiprocessing
**Follow-up:** "Khi nào dùng threading, khi nào dùng multiprocessing?"

### PY-E02: List Comprehension vs Generator
**Câu hỏi:** Phân biệt list comprehension và generator expression. Khi nào dùng generator?
**Keywords:** lazy evaluation, memory efficient, `yield`, iterator protocol
**Follow-up:** "Với file 10GB, bạn đọc dòng từng dòng bằng gì? Tại sao?"

### PY-E03: Decorator
**Câu hỏi:** Decorator trong Python là gì? Viết một decorator đo thời gian chạy hàm.
**Keywords:** higher-order function, `functools.wraps`, closure
**Expected code:**
```python
import time
import functools

def timer(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        print(f"{func.__name__} took {end - start:.4f}s")
        return result
    return wrapper
```

---

## MEDIUM

### PY-M01: Async/Await
**Câu hỏi:** Asyncio hoạt động thế nào trong Python? Phân biệt coroutine, task, future.
**Keywords:** event loop, non-blocking I/O, `await`, `asyncio.gather`, cooperative multitasking
**Follow-up:** "Khi nào async KHÔNG giúp được gì? (CPU-bound tasks)"

### PY-M02: FastAPI dependency injection
**Câu hỏi:** Dependency Injection trong FastAPI hoạt động thế nào? Ví dụ use-case?
**Keywords:** `Depends()`, shared DB connection, auth middleware, testability
**Follow-up:** "Làm thế nào để mock dependency trong unit test?"

### PY-M03: Pydantic v2
**Câu hỏi:** Pydantic v2 khác gì v1? Kể các tính năng mới quan trọng nhất.
**Keywords:** `model_validator`, `field_validator`, `model_config`, Rust core, `@computed_field`
**Follow-up:** "Serialize Enum trong Pydantic v2 thế nào?"

### PY-M04: Database connection pooling
**Câu hỏi:** Connection pooling là gì? Tại sao quan trọng trong web server?
**Keywords:** pool size, max overflow, SQLAlchemy pool, asyncpg
**Follow-up:** "Pool size tối ưu nên là bao nhiêu? Tính thế nào?"

### PY-M05: Caching strategies
**Câu hỏi:** Kể các caching strategy phổ biến. Cache invalidation khó ở điểm nào?
**Keywords:** TTL, LRU, write-through, write-behind, cache stampede, Redis

---

## HARD

### PY-H01: Python memory model
**Câu hỏi:** Python quản lý memory thế nào? Reference counting + garbage collection?
**Keywords:** reference counting, cyclic GC, `gc` module, `__del__`, memory leak
**Follow-up:** "Circular reference gây vấn đề gì? Python giải quyết thế nào?"

### PY-H02: FastAPI middleware & lifespan
**Câu hỏi:** Implement một rate limiting middleware trong FastAPI. Sử dụng lifespan event.
**Keywords:** `@asynccontextmanager`, startup/shutdown, `Middleware`, `Request.state`
**Follow-up:** "Middleware vs Dependency — khi nào dùng cái nào?"

### PY-H03: Temporal Workflow design
**Câu hỏi:** Workflow orchestration là gì? Tại sao Temporal tốt hơn cron job thuần?
**Keywords:** durability, replay, activities vs workflows, determinism, retry policy
**Follow-up:** "Workflow determinism constraint nghĩa là gì? Ví dụ vi phạm?"

### PY-H04: ClickHouse design
**Câu hỏi:** ClickHouse phù hợp cho workload nào? ReplacingMergeTree giải quyết gì?
**Keywords:** OLAP, columnar, ReplacingMergeTree, deduplication, eventual consistency
**Follow-up:** "Khi nào FINAL keyword cần thiết trong ClickHouse query?"
