# Module 11: Latency & Cost Optimization — Đáp án phỏng vấn Senior AI Engineer

> Mục tiêu: Nắm vững các kỹ thuật tối ưu latency và cost khi xây dựng LLM-based systems ở production.

---

## PHẦN 1: LLM Latency Metrics

---

### Q1: Giải thích TTFT và E2E latency. Khi nào dùng metric nào?

**Trả lời:**

**TTFT (Time To First Token)**
- Thời gian từ lúc gửi request đến lúc nhận token đầu tiên
- Bao gồm: network RTT + queue time + prefill computation
- Quyết định trải nghiệm "snappy" của user khi dùng streaming
- Target: **< 500ms** cho interactive apps

**E2E Latency (End-to-End)**
- Thời gian từ request đến khi nhận full response
- = TTFT + (decode_time × output_tokens)
- Quan trọng hơn với batch jobs, non-streaming APIs

**Khi nào dùng cái nào:**
- Interactive chat → tối ưu TTFT trước (user thấy text đang chảy ra)
- Document processing batch → tối ưu E2E throughput
- Voice assistant → cả hai đều critical (TTFT < 300ms để tránh awkward silence)

```
Timeline:
|---network---|---queue---|---prefill---|---decode---decode---decode---|
^                                       ^                              ^
Request sent                         First token                 Last token
|<------------- TTFT ----------------->|
|<--------------------------------- E2E Latency -----------------------|
```

---

### Q2: P50/P95/P99 percentile latency — tại sao không dùng average?

**Trả lời:**

**Vấn đề với average:**
```
Request latencies: [100ms, 110ms, 105ms, 98ms, 5000ms]
Average: 1082ms  ← bị outlier pull lên, không reflect trải nghiệm thực
P99: 5000ms      ← 1% users chờ 5 giây
P95: 5000ms      ← đỉnh điểm
P50: 105ms       ← median experience
```

**Cách đọc:**
- **P50 (median)**: 50% request xong trong X ms — trải nghiệm trung bình
- **P95**: 95% request xong trong X ms — trải nghiệm tốt nhất của 95% users
- **P99**: 99% xong trong X ms — "tail latency", quan trọng cho SLA
- **P99.9**: "three nines" — 1 trong 1000 requests

**SLA thực tế cho LLM APIs:**
```
TTFT:  P50 < 300ms, P95 < 800ms, P99 < 2000ms
E2E:   P50 < 3s,    P95 < 10s,   P99 < 30s
```

**Datadog query để xem percentiles:**
```python
# DogStatsD histogram tự động tính percentiles
statsd.histogram("llm.ttft.ms", ttft_ms, tags=[f"model:{model}"])

# Datadog sẽ expose: llm.ttft.ms.p50, .p95, .p99, .max, .avg, .count
```

---

### Q3: Tại sao streaming quan trọng cho UX?

**Trả lời:**

**Psychological latency vs actual latency:**
- User cảm thấy app "nhanh" dù response 10s nếu text bắt đầu xuất hiện ngay lập tức
- Streaming cho phép user đọc text trong khi model vẫn đang generate
- Non-streaming 10s = user stare at spinner → frustrated
- Streaming: TTFT 500ms → user thấy text ngay → perceived latency gần bằng 0

**Use case breakdown:**
```
Scenario 1: 500 token response, non-streaming
  User experience: ████████████████████ 8 seconds (blank screen)

Scenario 2: 500 token response, streaming (20 tok/s)
  User experience: |████ 500ms blank| then text flows for 25s
  Perceived wait: ~500ms (TTFT)
```

**Khi KHÔNG nên dùng streaming:**
- Structured JSON output (cần full response để parse)
- Downstream processing (chạy thêm logic sau khi nhận full text)
- Batch jobs (không có real-time user)

---

## PHẦN 2: Latency Optimization

---

### Q4: Prompt caching hoạt động như thế nào? Claude vs OpenAI khác gì nhau?

**Trả lời:**

**Claude Prompt Caching (Anthropic):**
```python
import anthropic

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1024,
    system=[
        {
            "type": "text",
            "text": "Ban la AI assistant chuyen ve phan tich tai lieu phap ly...",
        },
        {
            "type": "text",
            "text": LARGE_DOCUMENT_CONTENT,  # 50,000 tokens
            "cache_control": {"type": "ephemeral"}  # danh dau cache
        }
    ],
    messages=[
        {"role": "user", "content": "Tom tat dieu khoan 3.2"}
    ]
)

# Response headers chua cache info
# anthropic-cache-creation-input-tokens: 51000
# anthropic-cache-read-input-tokens: 0  (first call, cache miss)

# Call thu 2 voi cung system prompt:
# anthropic-cache-read-input-tokens: 51000  <- cache hit!
```

**Quy tắc Claude caching:**
- **Minimum**: 1,024 tokens để eligible cho caching
- **TTL**: 5 phút (refresh nếu hit trong 5 phút)
- **Cost savings**: 90% cheaper cho cached tokens (cache read = 10% of base price)
- **Cache creation**: 25% more expensive (one-time cost)
- **Break-even**: 1 cache creation + N reads → profitable after ~1 hit

```
Cost comparison (Claude Sonnet):
  Normal input:       $3.00/M tokens
  Cache creation:     $3.75/M tokens (+25%)
  Cache read:         $0.30/M tokens (-90%)

  For 10 requests with 50K token system prompt:
  Without cache: 10 x 50K x $3.00/M = $1.50
  With cache:    1 x 50K x $3.75/M + 9 x 50K x $0.30/M = $0.19 + $0.14 = $0.33
  Savings: 78%!
```

**OpenAI Auto-caching:**
```python
from openai import OpenAI

client = OpenAI()

# OpenAI tu dong cache — khong can config gi dac biet
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": LARGE_SYSTEM_PROMPT},  # >= 1024 tokens
        {"role": "user", "content": "Question here"}
    ]
)

# Check cache usage
usage = response.usage
print(f"Prompt tokens: {usage.prompt_tokens}")
print(f"Cached tokens: {usage.prompt_tokens_details.cached_tokens}")  # cache hit count
```

**Quy tắc OpenAI caching:**
- **Minimum**: 1,024 tokens prefix phải match
- **Matching**: prefix-based (đầu conversation phải giống nhau)
- **Discount**: 50% cheaper cho cached portion
- **TTL**: vài phút đến vài giờ (không được document chính xác)
- **Tự động**: không cần opt-in, tự xảy ra

**Bảng so sánh:**
```
Feature          | Claude                  | OpenAI
-----------------|-------------------------|------------------
Min tokens       | 1,024                   | 1,024
Savings          | 90% on cached           | 50% on cached
TTL              | 5 min (refresh on hit)  | Not published
Control          | Explicit cache_control  | Automatic (prefix)
Granularity      | Mark specific blocks    | Prefix matching only
```

---

### Q5: Bảng so sánh models — khi nào chọn model nào?

**Trả lời:**

```
Model               | Input $/M | Output $/M | Context  | Avg Latency | Best For
--------------------|-----------|------------|----------|-------------|----------------------------
GPT-4o              | $2.50     | $10.00     | 128K     | ~2-5s TTFT  | Complex reasoning, vision
GPT-4o-mini         | $0.15     | $0.60      | 128K     | ~0.5-1s     | Simple tasks, high volume
Claude Sonnet 4.5   | $3.00     | $15.00     | 200K     | ~1-3s       | Long docs, nuanced writing
Claude Haiku 3.5    | $0.80     | $4.00      | 200K     | ~0.5s       | Fast responses, routing
Gemini 1.5 Flash    | $0.075    | $0.30      | 1M       | ~0.5s       | Very long context, cheap
Gemini 1.5 Pro      | $1.25     | $5.00      | 2M       | ~2-4s       | Massive context tasks
```

**Decision framework:**
```python
def select_model(task_type: str, input_tokens: int, quality_required: str) -> str:
    # Simple classification, intent detection
    if task_type == "routing" and input_tokens < 500:
        return "claude-haiku-3-5"  # fastest, cheapest

    # Document summarization > 100K tokens
    if input_tokens > 100_000:
        return "gemini-1.5-flash"  # 1M context, cheapest

    # High quality generation
    if quality_required == "high" and task_type in ["writing", "analysis"]:
        return "claude-sonnet-4-5"

    # Default workhorse
    return "gpt-4o-mini"
```

---

### Q6: Async parallel LLM calls — fan-out pattern

**Trả lời:**

**Pattern co ban — Sequential (BAD):**
```python
# Sequential: 3 x 2s = 6s total
async def analyze_document_bad(chunks: list[str]) -> list[str]:
    results = []
    for chunk in chunks:
        result = await call_llm(chunk)  # 2s each
        results.append(result)
    return results  # 6s for 3 chunks
```

**Fan-out pattern (GOOD):**
```python
import asyncio
import anthropic
from typing import Optional

client = anthropic.AsyncAnthropic()

async def call_llm_with_retry(
    prompt: str,
    model: str = "claude-haiku-3-5",
    max_retries: int = 3
) -> str:
    for attempt in range(max_retries):
        try:
            response = await client.messages.create(
                model=model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except anthropic.RateLimitError:
            wait = 2 ** attempt  # exponential backoff
            await asyncio.sleep(wait)
    raise Exception("Max retries exceeded")

async def analyze_document_parallel(chunks: list[str]) -> list[str]:
    # Limit concurrency de khong bi rate limit
    semaphore = asyncio.Semaphore(10)  # max 10 concurrent calls

    async def bounded_call(chunk: str) -> str:
        async with semaphore:
            return await call_llm_with_retry(chunk)

    # Fan-out: tat ca chunks chay song song
    tasks = [bounded_call(chunk) for chunk in chunks]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Handle partial failures
    processed = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            processed.append(f"Error processing chunk {i}: {result}")
        else:
            processed.append(result)

    return processed

# Example: 3 chunks, each 2s -> total ~2s (not 6s)
async def main():
    chunks = ["chunk1...", "chunk2...", "chunk3..."]
    results = await analyze_document_parallel(chunks)
    # Time: ~2s instead of 6s
```

**Advanced: Fan-out voi progress tracking:**
```python
import asyncio
from dataclasses import dataclass
from enum import Enum

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"

@dataclass
class ChunkResult:
    chunk_id: int
    status: TaskStatus
    result: Optional[str] = None
    error: Optional[str] = None

async def analyze_with_progress(
    chunks: list[str],
    progress_callback=None
) -> list[ChunkResult]:
    results = [ChunkResult(i, TaskStatus.PENDING) for i in range(len(chunks))]
    semaphore = asyncio.Semaphore(5)

    async def process_chunk(chunk_id: int, chunk: str):
        results[chunk_id].status = TaskStatus.RUNNING
        if progress_callback:
            await progress_callback(results)

        async with semaphore:
            try:
                text = await call_llm_with_retry(chunk)
                results[chunk_id].status = TaskStatus.DONE
                results[chunk_id].result = text
            except Exception as e:
                results[chunk_id].status = TaskStatus.FAILED
                results[chunk_id].error = str(e)

        if progress_callback:
            await progress_callback(results)

    await asyncio.gather(*[
        process_chunk(i, chunk) for i, chunk in enumerate(chunks)
    ])
    return results
```

---

### Q7: Streaming + sentence chunking de tranh TTS artifacts

**Trả lời:**

**Problem:** LLM streams token by token, nhung TTS can full sentences

```python
import anthropic
import asyncio
from collections.abc import AsyncIterator

client = anthropic.AsyncAnthropic()

async def stream_sentences(prompt: str) -> AsyncIterator[str]:
    """
    Stream LLM output va yield tung sentence hoan chinh.
    Dung cho voicebot: moi sentence -> TTS ngay lap tuc.
    """
    buffer = ""
    sentence_endings = {'.', '!', '?'}

    async with client.messages.stream(
        model="claude-haiku-3-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    ) as stream:
        async for text_chunk in stream.text_stream:
            buffer += text_chunk

            # Check for sentence boundaries
            while True:
                end_pos = -1
                for i, char in enumerate(buffer):
                    if char in sentence_endings:
                        if i + 1 < len(buffer) and buffer[i+1] == ' ':
                            end_pos = i + 1
                            break
                        elif i + 1 == len(buffer):
                            end_pos = i + 1
                            break

                if end_pos == -1:
                    break

                sentence = buffer[:end_pos].strip()
                buffer = buffer[end_pos:].strip()

                if sentence:
                    yield sentence

    # Flush remaining buffer
    if buffer.strip():
        yield buffer.strip()

# FastAPI SSE endpoint
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()

@app.get("/stream-chat")
async def stream_chat(message: str):
    async def generate():
        async for sentence in stream_sentences(message):
            import json
            data = json.dumps({"type": "sentence", "text": sentence})
            yield f"data: {data}\n\n"
        yield 'data: {"type": "done"}\n\n'

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )
```

---

### Q8: Connection pooling — AsyncOpenAI singleton pattern

**Trả lời:**

**Van de:** Tao client moi moi request → overhead ket noi, khong tai dung connections

```python
# BAD: Tao client moi moi request
async def bad_handler(request):
    client = AsyncOpenAI()  # tao moi moi lan -> slow, resource waste
    response = await client.chat.completions.create(...)
    return response

# GOOD: Singleton pattern voi lifespan
from contextlib import asynccontextmanager
from fastapi import FastAPI
import openai
import anthropic
import httpx

# Global clients
_openai_client: openai.AsyncOpenAI | None = None
_anthropic_client: anthropic.AsyncAnthropic | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _openai_client, _anthropic_client

    # Startup: khoi tao clients mot lan
    _openai_client = openai.AsyncOpenAI(
        max_retries=3,
        timeout=openai.Timeout(
            connect=5.0,
            read=60.0,
            write=10.0,
            pool=10.0
        ),
        http_client=httpx.AsyncClient(
            limits=httpx.Limits(
                max_connections=100,
                max_keepalive_connections=20,
                keepalive_expiry=30.0
            )
        )
    )

    _anthropic_client = anthropic.AsyncAnthropic(
        max_retries=3,
        timeout=anthropic.Timeout(60.0, connect=5.0)
    )

    yield  # app chay o day

    # Shutdown: cleanup
    await _openai_client.close()
    await _anthropic_client.close()

app = FastAPI(lifespan=lifespan)

def get_openai_client() -> openai.AsyncOpenAI:
    if _openai_client is None:
        raise RuntimeError("OpenAI client not initialized")
    return _openai_client

# Dependency injection
from fastapi import Depends

async def complete(
    prompt: str,
    client: openai.AsyncOpenAI = Depends(get_openai_client)
) -> str:
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content
```

---

## PHẦN 3: Cost Optimization

---

### Q9: Token counting voi tiktoken — tai sao quan trong?

**Trả lời:**

**Dung tiktoken de estimate cost truoc khi gui request:**

```python
import tiktoken
from typing import Optional

# OpenAI token counting
def count_tokens_openai(text: str, model: str = "gpt-4o") -> int:
    """Count tokens cho OpenAI models."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")  # fallback
    return len(encoding.encode(text))

def count_chat_tokens(messages: list[dict], model: str = "gpt-4o") -> int:
    """Count tokens cho chat completion format."""
    encoding = tiktoken.encoding_for_model(model)

    tokens_per_message = 3  # every message has start/role/content/end
    tokens_per_name = 1

    total = 3  # every reply is primed with start assistant message
    for message in messages:
        total += tokens_per_message
        for key, value in message.items():
            total += len(encoding.encode(value))
            if key == "name":
                total += tokens_per_name

    return total

# Cost estimation
COST_PER_M_TOKENS = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "claude-sonnet-4-5": {"input": 3.00, "output": 15.00},
    "claude-haiku-3-5": {"input": 0.80, "output": 4.00},
}

def estimate_cost(
    prompt: str,
    model: str = "gpt-4o-mini",
    expected_output_tokens: int = 500
) -> dict:
    input_tokens = count_tokens_openai(prompt, model)
    costs = COST_PER_M_TOKENS.get(model, COST_PER_M_TOKENS["gpt-4o-mini"])

    input_cost = (input_tokens / 1_000_000) * costs["input"]
    output_cost = (expected_output_tokens / 1_000_000) * costs["output"]

    return {
        "input_tokens": input_tokens,
        "estimated_output_tokens": expected_output_tokens,
        "input_cost_usd": round(input_cost, 6),
        "output_cost_usd": round(output_cost, 6),
        "total_cost_usd": round(input_cost + output_cost, 6),
        "model": model
    }

# Usage: Guard expensive calls
async def safe_llm_call(prompt: str, max_cost_usd: float = 0.01) -> str:
    estimate = estimate_cost(prompt)

    if estimate["total_cost_usd"] > max_cost_usd:
        raise ValueError(
            f"Estimated cost ${estimate['total_cost_usd']:.4f} exceeds limit ${max_cost_usd}"
            f" (input: {estimate['input_tokens']} tokens)"
        )

    client = get_openai_client()
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content
```

---

### Q10: Semantic caching — kien truc va implementation

**Trả lời:**

**Kien truc semantic cache:**
```
User Query
    |
    v
[Embed Query] <- text-embedding-3-small ($0.02/M)
    |
    v
[Redis Vector Search]
    |
    +-- cosine_sim > 0.95? --> Return cached response (0ms, $0)
    |
    +-- Cache miss --> [LLM API] --> Store (embedding, response) in Redis --> Return
```

**Implementation voi Redis:**
```python
import json
import hashlib
import numpy as np
import redis.asyncio as redis
from openai import AsyncOpenAI
import struct

client = AsyncOpenAI()
redis_client = redis.Redis(host="localhost", port=6379, decode_responses=False)

CACHE_TTL = 3600  # 1 hour
SIMILARITY_THRESHOLD = 0.95

async def get_embedding(text: str) -> list[float]:
    """Get embedding tu OpenAI."""
    response = await client.embeddings.create(
        input=text,
        model="text-embedding-3-small"  # 1536 dims, $0.02/M tokens
    )
    return response.data[0].embedding

def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Tinh cosine similarity giua 2 vectors."""
    a_arr = np.array(a)
    b_arr = np.array(b)
    return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))

def embedding_to_bytes(embedding: list[float]) -> bytes:
    return struct.pack(f"{len(embedding)}f", *embedding)

def bytes_to_embedding(data: bytes) -> list[float]:
    n = len(data) // 4
    return list(struct.unpack(f"{n}f", data))

async def semantic_cache_get(query: str) -> str | None:
    """
    Tim trong cache voi semantic similarity.
    Returns cached response neu co similar query.
    """
    query_embedding = await get_embedding(query)

    cache_keys = await redis_client.keys("cache:embedding:*")

    best_similarity = 0.0
    best_response_key = None

    for key in cache_keys:
        cached_bytes = await redis_client.get(key)
        if cached_bytes is None:
            continue

        cached_embedding = bytes_to_embedding(cached_bytes)
        similarity = cosine_similarity(query_embedding, cached_embedding)

        if similarity > best_similarity:
            best_similarity = similarity
            best_response_key = key.decode().replace("embedding:", "response:")

    if best_similarity >= SIMILARITY_THRESHOLD and best_response_key:
        cached_response = await redis_client.get(best_response_key)
        if cached_response:
            return json.loads(cached_response)

    return None

async def semantic_cache_set(query: str, response: str):
    """Luu query + response vao semantic cache."""
    query_embedding = await get_embedding(query)

    query_hash = hashlib.md5(query.encode()).hexdigest()[:16]
    embedding_key = f"cache:embedding:{query_hash}"
    response_key = f"cache:response:{query_hash}"

    await redis_client.setex(
        embedding_key,
        CACHE_TTL,
        embedding_to_bytes(query_embedding)
    )
    await redis_client.setex(
        response_key,
        CACHE_TTL,
        json.dumps(response)
    )

async def cached_llm_call(query: str) -> tuple[str, bool]:
    """
    Returns: (response, is_cached)
    """
    cached = await semantic_cache_get(query)
    if cached:
        return cached, True

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": query}]
    )
    result = response.choices[0].message.content

    await semantic_cache_set(query, result)

    return result, False

# Production: Dung Redis voi RediSearch module cho vector search
# Ho tro KNN search voi HNSW index -> nhanh hon brute-force scan
```

**Production tip voi Redis Vector Search:**
```python
# Tao index (chay mot lan)
import redis
from redis.commands.search.field import VectorField, TextField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType

r = redis.Redis()
schema = [
    TextField("query"),
    VectorField(
        "embedding",
        "HNSW",  # Hierarchical Navigable Small World graph
        {
            "TYPE": "FLOAT32",
            "DIM": 1536,
            "DISTANCE_METRIC": "COSINE",
            "INITIAL_CAP": 10000,
        }
    )
]
r.ft("cache_index").create_index(
    schema,
    definition=IndexDefinition(prefix=["cache:doc:"], index_type=IndexType.HASH)
)
```

---

### Q11: OpenAI Batch API — khi nao dung, trade-offs?

**Trả lời:**

**Batch API characteristics:**
- 50% cheaper than synchronous API
- 24-hour SLA (not real-time)
- Up to 50,000 requests per batch
- Ideal cho: evaluation pipelines, bulk document processing, report generation

```python
import json
import time
from openai import OpenAI
from pathlib import Path

client = OpenAI()

def create_batch_requests(queries: list[str]) -> list[dict]:
    """Tao batch request objects."""
    requests = []
    for i, query in enumerate(queries):
        requests.append({
            "custom_id": f"request-{i}",
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "Phan tich sentiment: positive/negative/neutral"},
                    {"role": "user", "content": query}
                ],
                "max_tokens": 10
            }
        })
    return requests

def run_batch_job(queries: list[str]) -> dict[str, str]:
    """
    Run batch job va doi ket qua.
    Returns: {custom_id: response_text}
    """
    # 1. Create JSONL file
    requests = create_batch_requests(queries)
    batch_file = Path("/tmp/batch_requests.jsonl")

    with open(batch_file, "w") as f:
        for req in requests:
            f.write(json.dumps(req) + "\n")

    # 2. Upload file
    with open(batch_file, "rb") as f:
        batch_input_file = client.files.create(
            file=f,
            purpose="batch"
        )

    print(f"Uploaded file: {batch_input_file.id}")

    # 3. Create batch
    batch = client.batches.create(
        input_file_id=batch_input_file.id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
        metadata={"job_type": "sentiment_analysis", "count": str(len(queries))}
    )

    print(f"Batch created: {batch.id}, status: {batch.status}")

    # 4. Poll for completion
    while True:
        batch = client.batches.retrieve(batch.id)
        print(f"Status: {batch.status}, completed: {batch.request_counts.completed}/{batch.request_counts.total}")

        if batch.status == "completed":
            break
        elif batch.status in ["failed", "expired", "cancelled"]:
            raise Exception(f"Batch failed: {batch.status}")

        time.sleep(60)  # Poll moi phut

    # 5. Download results
    result_file = client.files.content(batch.output_file_id)
    results = {}

    for line in result_file.text.strip().split("\n"):
        result = json.loads(line)
        custom_id = result["custom_id"]
        if result["error"] is None:
            response_text = result["response"]["body"]["choices"][0]["message"]["content"]
            results[custom_id] = response_text
        else:
            results[custom_id] = f"ERROR: {result['error']['message']}"

    return results

# Cost comparison:
# 1000 sentiment analyses voi gpt-4o-mini:
# Sync:  1000 x ~50 tokens x $0.15/M = $0.0075
# Batch: 1000 x ~50 tokens x $0.075/M = $0.00375  (50% cheaper)
# Savings at 1M requests/day: $37.50/day = $1,125/month
```

---

### Q12: Model routing — smart fallback strategy

**Trả lời:**

**Concept:** Dung cheap model truoc, fallback sang expensive model neu confidence thap

```python
from openai import AsyncOpenAI
import json

client = AsyncOpenAI()

async def smart_route(query: str, task_type: str = "general") -> tuple[str, str]:
    """
    Smart routing: cheap model -> expensive model neu can.
    Returns: (response, model_used)
    """

    # Step 1: Try cheap model voi confidence check
    cheap_response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": """Tra loi cau hoi va danh gia confidence cua ban.
                Format JSON: {"answer": "...", "confidence": 0.0-1.0, "reason": "..."}
                confidence < 0.7 neu cau hoi can reasoning phuc tap."""
            },
            {"role": "user", "content": query}
        ],
        response_format={"type": "json_object"},
        max_tokens=500
    )

    cheap_result = json.loads(cheap_response.choices[0].message.content)
    confidence = cheap_result.get("confidence", 0.5)

    if confidence >= 0.85:
        return cheap_result["answer"], "gpt-4o-mini"

    # Step 2: Fallback to expensive model
    print(f"Low confidence ({confidence:.2f}), routing to GPT-4o")

    expensive_response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": query}],
        max_tokens=1000
    )

    return expensive_response.choices[0].message.content, "gpt-4o"

# Advanced routing voi multiple signals
class ModelRouter:
    ROUTING_RULES = {
        "simple_qa": "gpt-4o-mini",
        "long_document": "gemini-1.5-flash",
        "code_generation": "gpt-4o",
        "classification": "gpt-4o-mini",
        "creative_writing": "claude-sonnet-4-5",
    }

    def classify_task(self, query: str, context_length: int) -> str:
        if context_length > 50_000:
            return "long_document"

        code_keywords = ["code", "function", "implement", "debug", "algorithm"]
        if any(kw in query.lower() for kw in code_keywords):
            return "code_generation"

        if len(query) < 100 and "?" in query:
            return "simple_qa"

        return "general"

    def get_model(self, query: str, context_length: int = 0) -> str:
        task = self.classify_task(query, context_length)
        return self.ROUTING_RULES.get(task, "gpt-4o-mini")
```

---

### Q13: Context window management — sliding window va summarization

**Trả lời:**

```python
from collections import deque
from dataclasses import dataclass, field
from typing import Optional
import tiktoken

@dataclass
class Message:
    role: str
    content: str
    token_count: int = 0

class ConversationManager:
    """
    Manages conversation history voi context window constraints.
    Strategy: sliding window + summarization khi gan limit.
    """

    def __init__(
        self,
        max_tokens: int = 100_000,
        model: str = "gpt-4o",
        summarize_at: float = 0.7
    ):
        self.max_tokens = max_tokens
        self.model = model
        self.summarize_at = summarize_at
        self.messages: deque[Message] = deque()
        self.summary: Optional[str] = None
        self.encoding = tiktoken.encoding_for_model(model)

    def count_tokens(self, text: str) -> int:
        return len(self.encoding.encode(text))

    def total_tokens(self) -> int:
        return sum(m.token_count for m in self.messages)

    def add_message(self, role: str, content: str):
        token_count = self.count_tokens(content)
        self.messages.append(Message(role, content, token_count))

        if self.total_tokens() > self.max_tokens * self.summarize_at:
            self._compress_history()

    def _compress_history(self):
        """Compress old messages into summary."""
        recent_count = 5

        if len(self.messages) <= recent_count:
            return

        old_messages = []
        while len(self.messages) > recent_count:
            old_messages.append(self.messages.popleft())

        # In production: call LLM to create proper summary
        summary_text = f"[Summary of {len(old_messages)} earlier messages]"

        if self.summary:
            self.summary = f"{self.summary}\n{summary_text}"
        else:
            self.summary = summary_text

    def get_messages_for_api(self) -> list[dict]:
        """Return messages formatted for API, including summary if any."""
        api_messages = []

        if self.summary:
            api_messages.append({
                "role": "system",
                "content": f"Previous conversation context: {self.summary}"
            })

        for msg in self.messages:
            api_messages.append({
                "role": msg.role,
                "content": msg.content
            })

        return api_messages

    def get_stats(self) -> dict:
        return {
            "total_tokens": self.total_tokens(),
            "message_count": len(self.messages),
            "has_summary": self.summary is not None,
            "window_usage_pct": self.total_tokens() / self.max_tokens * 100
        }
```

---

## PHẦN 4: Throughput & Scale

---

### Q14: vLLM — tai sao nhanh hon HuggingFace 20x?

**Trả lời:**

**2 innovations chinh cua vLLM:**

**1. PagedAttention:**
```
HuggingFace (old way):
  Request A (500 tokens max): Allocate 500 tokens contiguous memory
  Request B (500 tokens max): Allocate 500 tokens contiguous memory
  Actual use: A uses 100 tokens, B uses 50 tokens
  Memory waste: 750 tokens wasted (75%!)

vLLM PagedAttention:
  Memory divided into "pages" (like OS virtual memory)
  Request A: Allocated 2 pages (100 tokens actual)
  Request B: Allocated 1 page (50 tokens actual)
  Pages shared for common prefixes (e.g., system prompt)
  Memory waste: near 0%

Result: Fit 5-10x more requests in GPU memory simultaneously
```

**2. Continuous Batching:**
```
Old static batching:
  Batch = [req1(100 tok), req2(200 tok), req3(50 tok)]
  All requests must wait until LONGEST one finishes
  req3 finishes at step 50, but waits idle until step 200
  GPU utilization: ~40-60%

vLLM continuous batching:
  When req3 finishes -> immediately insert req4 into batch
  GPU never sits idle waiting for slow requests
  GPU utilization: ~90%+
```

**Practical comparison:**
```
Benchmark: Llama-2-70B, A100 GPU, 100 concurrent requests
                    | Throughput (tokens/s) | Memory efficiency
HuggingFace         | ~500 tok/s            | 30-40%
TGI (Text Gen Inf)  | ~2000 tok/s           | 60-70%
vLLM                | ~10000 tok/s          | 95%+

~20x improvement tuy workload!
```

**Khi nao tu host vLLM vs dung API:**
```
API (OpenAI/Anthropic):
  + Khong can manage infrastructure
  + Latest models
  - Cost, data privacy concerns, rate limits

vLLM self-hosted:
  + Cost-effective cho volume > 1M tokens/day
  + Data privacy (on-premise)
  + No rate limits
  - Need GPU infrastructure, model management
  - Only open-source models (Llama, Mistral, etc.)

Break-even point:
  GPT-4o-mini: $0.15/M input tokens
  p3.8xlarge on AWS: ~$12/hr
  llama3-8b throughput: ~10,000 tok/s
  Self-hosting profitable at ~300M tokens/day
```

---

### Q15: Queue architecture — SQS + ECS workers

**Trả lời:**

```
Client --> FastAPI --> SQS Queue --> ECS Workers --> LLM API
                                         |
                                    DynamoDB (job status)
                                         |
                              Client polls GET /jobs/{id}
```

**AWS architecture:**
```python
import boto3
import uuid
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime

app = FastAPI()
sqs = boto3.client("sqs", region_name="us-east-1")
dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/123456/llm-jobs.fifo"
JOB_TABLE = dynamodb.Table("llm-jobs")

class ProcessRequest(BaseModel):
    document: str
    task: str = "summarize"

@app.post("/jobs")
async def submit_job(request: ProcessRequest):
    job_id = str(uuid.uuid4())

    JOB_TABLE.put_item(Item={
        "job_id": job_id,
        "status": "queued",
        "created_at": datetime.utcnow().isoformat(),
        "task": request.task
    })

    sqs.send_message(
        QueueUrl=QUEUE_URL,
        MessageBody=json.dumps({
            "job_id": job_id,
            "document": request.document,
            "task": request.task
        }),
        MessageGroupId="llm-jobs",
        MessageDeduplicationId=job_id
    )

    return {"job_id": job_id, "status": "queued"}

@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    response = JOB_TABLE.get_item(Key={"job_id": job_id})
    item = response.get("Item")

    if not item:
        raise HTTPException(status_code=404, detail="Job not found")

    return item

# ECS Worker (separate container)
import anthropic
import time

def worker_loop():
    sqs = boto3.client("sqs", region_name="us-east-1")
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    job_table = dynamodb.Table("llm-jobs")
    llm_client = anthropic.Anthropic()

    while True:
        response = sqs.receive_message(
            QueueUrl=QUEUE_URL,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20,       # Long polling
            VisibilityTimeout=300     # 5 min: longer than max LLM processing time
        )

        messages = response.get("Messages", [])
        if not messages:
            continue

        message = messages[0]
        body = json.loads(message["Body"])
        job_id = body["job_id"]

        try:
            job_table.update_item(
                Key={"job_id": job_id},
                UpdateExpression="SET #s = :s, updated_at = :t",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={
                    ":s": "processing",
                    ":t": datetime.utcnow().isoformat()
                }
            )

            llm_response = llm_client.messages.create(
                model="claude-haiku-3-5",
                max_tokens=2048,
                messages=[{
                    "role": "user",
                    "content": f"Task: {body['task']}\n\nDocument: {body['document']}"
                }]
            )

            result = llm_response.content[0].text

            job_table.update_item(
                Key={"job_id": job_id},
                UpdateExpression="SET #s = :s, result = :r, updated_at = :t",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={
                    ":s": "completed",
                    ":r": result,
                    ":t": datetime.utcnow().isoformat()
                }
            )

            sqs.delete_message(
                QueueUrl=QUEUE_URL,
                ReceiptHandle=message["ReceiptHandle"]
            )

        except Exception as e:
            job_table.update_item(
                Key={"job_id": job_id},
                UpdateExpression="SET #s = :s, error = :e",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={":s": "failed", ":e": str(e)}
            )
            # Don't delete from SQS -> will retry (up to maxReceiveCount -> DLQ)

        time.sleep(0.1)
```

---

### Q16: Rate limiting — token bucket algorithm

**Trả lời:**

```python
import asyncio
import time
from dataclasses import dataclass, field
from collections import defaultdict

@dataclass
class TokenBucket:
    """
    Token bucket rate limiter cho LLM API calls.
    Cho phep bursting nhung enforce average rate.
    """
    capacity: int
    refill_rate: float
    tokens: float = field(init=False)
    last_refill: float = field(init=False)

    def __post_init__(self):
        self.tokens = float(self.capacity)
        self.last_refill = time.monotonic()

    async def acquire(self, tokens_needed: int = 1) -> float:
        """Acquire tokens. Returns wait time if needed."""
        now = time.monotonic()
        elapsed = now - self.last_refill

        self.tokens = min(
            self.capacity,
            self.tokens + elapsed * self.refill_rate
        )
        self.last_refill = now

        if self.tokens >= tokens_needed:
            self.tokens -= tokens_needed
            return 0.0

        wait_time = (tokens_needed - self.tokens) / self.refill_rate
        await asyncio.sleep(wait_time)
        self.tokens = 0
        return wait_time

class LLMRateLimiter:
    """
    Multi-tenant rate limiter:
    - Per-user: 100K tokens/minute
    - Global: 1M tokens/minute (OpenAI TPM limit)
    """

    def __init__(self):
        # Global: 1M tokens/min = ~16,667 tokens/sec
        self.global_bucket = TokenBucket(capacity=1_000_000, refill_rate=16_667)

        # Per-user: 100K tokens/min = ~1,667 tokens/sec
        self.user_buckets: dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(capacity=100_000, refill_rate=1_667)
        )

    async def acquire(self, user_id: str, estimated_tokens: int):
        user_wait = await self.user_buckets[user_id].acquire(estimated_tokens)
        global_wait = await self.global_bucket.acquire(estimated_tokens)

        total_wait = user_wait + global_wait
        if total_wait > 0:
            print(f"Rate limited user {user_id}: waited {total_wait:.2f}s")

# Usage in FastAPI middleware
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

rate_limiter = LLMRateLimiter()

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        user_id = request.headers.get("X-User-ID", "anonymous")

        body = await request.body()
        estimated_tokens = len(body) // 4

        try:
            await asyncio.wait_for(
                rate_limiter.acquire(user_id, estimated_tokens),
                timeout=5.0
            )
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please retry after 60 seconds.",
                headers={"Retry-After": "60"}
            )

        return await call_next(request)
```

---

## Quick Reference: Key Numbers

```
OPTIMIZATION QUICK REFERENCE
=======================================================

Latency Targets:
  TTFT P50: < 300ms    P95: < 800ms    P99: < 2000ms
  E2E  P50: < 3s       P95: < 10s      P99: < 30s

Prompt Caching:
  Claude: 90% savings, min 1024 tokens, 5min TTL, explicit cache_control
  OpenAI: 50% savings, min 1024 tokens, auto prefix matching

Model Costs ($/M tokens, input/output):
  GPT-4o:        $2.50 / $10.00    GPT-4o-mini:   $0.15 / $0.60
  Claude Sonnet: $3.00 / $15.00    Claude Haiku:  $0.80 / $4.00
  Gemini Flash:  $0.075 / $0.30

Semantic Cache: cosine_similarity > 0.95 -> cache hit
Batch API: 50% cheaper, 24h SLA, up to 50K requests/batch
vLLM: 20x throughput vs HuggingFace (PagedAttention + continuous batching)
Rate Limit: Token bucket preferred (allows bursting within capacity)

SQS Config for LLM Workers:
  VisibilityTimeout > max_processing_time (e.g. 300s for LLM)
  WaitTimeSeconds = 20 (long polling reduces empty receives)
  MaxReceiveCount = 3 -> DLQ after 3 failures
=======================================================
```
