# Module 14: System Design cho AI Systems — Senior AI Engineer

> Mỗi design đủ nội dung cho 30-45 phút discussion. Bắt đầu với requirements, vẽ diagram, rồi dive deep khi interviewer hỏi.

---

## Design 1: Enterprise RAG System

**Prompt:** "Design a RAG system for a large enterprise with 10TB of documents and 1,000 concurrent users."

---

### Requirements

**Functional:**
- Ingest documents: PDF, Word, HTML, Markdown (up to 500MB each)
- Multi-tenant isolation (Company A cannot see Company B's documents)
- Real-time Q&A over documents with source citations
- Incremental indexing: new/updated docs reflected within 5 minutes
- Support English and Vietnamese
- Filter search by date range, document type, department

**Non-functional:**
- Throughput: 1,000 concurrent users, ~100 QPS average
- Query latency: P95 < 3 seconds (including LLM generation)
- Availability: 99.9% (8.7 hours downtime/year)
- Storage: 10TB documents, ~500GB vector embeddings
- Cost target: < $0.02 per query at steady state

---

### Architecture Diagram

```
                          INGESTION PIPELINE
+----------+    Upload    +----------+    SQS     +------------------+
| S3 Bucket|<-------------|  FastAPI  |----------->| Ingestion Workers|
| (10TB)   |              | /ingest  |            | (ECS Fargate)    |
+----------+              +----------+       //     +------------------+
      |                                                    |
      |                               +-------------------+
      |                               |     Processing    |
      |                               v                   v
      |                        +----------+        +----------+
      |                        | Chunker  |        | Embedder |
      |                        | (512 tok)|        | (ada-002)|
      |                        +----------+        +----------+
      |                               |                   |
      |                               v                   v
      |                        +----------+        +------------------+
      |                        |PostgreSQL|        | Pinecone/         |
      |                        |(metadata)|        | pgvector          |
      |                        +----------+        | (vector store)    |
      |                                            +------------------+
      |
      |                          QUERY PIPELINE
      |                   +-------------------------------+
      |                   |         API Gateway           |
      |                   |      (ALB + FastAPI)          |
      |                   +-------------------------------+
      |                              |
      |              +---------------+---------------+
      |              |               |               |
      v              v               v               v
+----------+  +----------+   +----------+   +-----------+
| Cache    |  | Intent   |   | Retrieval|   | LLM       |
| (Redis)  |  | Classify |   | Service  |   | Generate  |
| Semantic |  | (Haiku)  |   |          |   | (Sonnet)  |
+----------+  +----------+   +----------+   +-----------+
                                  |
                    +-------------+-------------+
                    |                           |
             +----------+               +----------+
             | Dense    |               | Sparse   |
             | Retrieval|               | BM25     |
             | (vector) |               | (keyword)|
             +----------+               +----------+
                    |                           |
                    +-------------+-------------+
                                  |
                          Reciprocal Rank Fusion
                                  |
                          Re-ranking (cross-encoder)
```

---

### Component Breakdown

**1. Document Ingestion (S3 + SQS + ECS Workers):**
```python
# Ingestion pipeline
async def ingest_document(s3_key: str, tenant_id: str, metadata: dict):
    # Step 1: Download from S3
    content = await s3.get_object(Bucket="docs-bucket", Key=s3_key)

    # Step 2: Parse (pdf2image + OCR for scanned docs, pypdf2 for digital)
    text = await parse_document(content, file_type=metadata["type"])

    # Step 3: Chunk with overlap
    chunks = chunk_text(
        text,
        chunk_size=512,        # tokens
        chunk_overlap=50,      # token overlap between chunks
        strategy="sentence"    # don't split mid-sentence
    )

    # Step 4: Embed all chunks in parallel (fan-out)
    embeddings = await embed_chunks_parallel(chunks, model="text-embedding-3-small")

    # Step 5: Store metadata in PostgreSQL
    doc_id = await store_document_metadata(
        tenant_id=tenant_id,
        s3_key=s3_key,
        chunk_count=len(chunks),
        metadata=metadata
    )

    # Step 6: Upsert vectors with tenant namespace
    await vector_store.upsert(
        vectors=[{
            "id": f"{tenant_id}:{doc_id}:{i}",
            "values": embedding,
            "metadata": {
                "tenant_id": tenant_id,  # IMPORTANT for isolation
                "doc_id": doc_id,
                "chunk_index": i,
                "text": chunk,
                "source": s3_key,
                "date": metadata["date"]
            }
        } for i, (chunk, embedding) in enumerate(zip(chunks, embeddings))],
        namespace=tenant_id  # Pinecone namespace = tenant isolation!
    )
```

**2. Multi-tenant Isolation:**
```
Approach 1: Namespace per tenant (Pinecone)
  - Each tenant has own vector namespace
  - No cross-tenant leakage
  - Can query only within namespace
  - Limitation: namespace count limit, can't search across tenants

Approach 2: Metadata filter
  - All vectors in same index
  - Filter by tenant_id metadata on every query
  - Cheaper, simpler
  - Risk: bug could expose wrong tenant data

Production choice: Namespace (safer) + metadata (redundant check)
  query = index.query(
      namespace=tenant_id,
      vector=query_embedding,
      filter={"tenant_id": {"$eq": tenant_id}},  # Double check
      top_k=20
  )
```

**3. Hybrid Retrieval (Dense + Sparse):**
```python
async def hybrid_search(query: str, tenant_id: str, top_k: int = 10):
    # Parallel: dense (semantic) + sparse (keyword)
    dense_results, sparse_results = await asyncio.gather(
        vector_search(query, tenant_id, top_k=20),
        bm25_search(query, tenant_id, top_k=20)
    )

    # Reciprocal Rank Fusion (RRF)
    # Score = sum(1 / (k + rank)) for each result
    k = 60  # RRF constant
    scores = {}

    for rank, result in enumerate(dense_results):
        scores[result.id] = scores.get(result.id, 0) + 1 / (k + rank + 1)

    for rank, result in enumerate(sparse_results):
        scores[result.id] = scores.get(result.id, 0) + 1 / (k + rank + 1)

    # Sort by RRF score, take top_k
    fused = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

    # Re-rank with cross-encoder (more accurate but slower)
    reranked = await cross_encoder_rerank(query, fused)

    return reranked
```

**4. Caching Layers:**
```
Layer 1: Exact cache (Redis, TTL 1 hour)
  Key: SHA256(tenant_id + query_text)
  Hit rate: ~15-20% (repeated questions)

Layer 2: Semantic cache (Redis vectors, cosine > 0.95)
  Key: similar query embedding
  Hit rate: ~30-35% additional
  Combined hit rate: ~45-50%

Layer 3: Embedding cache (Redis, TTL 24 hours)
  Cache: query_text -> embedding
  Avoids re-embedding same query
  99% hit rate for repeated queries
```

---

### Data Flow (Numbered Steps)

**Query flow:**
```
1. User sends: POST /query {question: "What is the refund policy?", tenant_id: "acme"}
2. Auth middleware validates JWT, extracts tenant_id
3. Check Redis exact cache -> HIT: return in <50ms
4. Check Redis semantic cache (embedding similarity > 0.95) -> HIT: return in ~200ms
5. Cache MISS: get query embedding (text-embedding-3-small, ~100ms)
6. Hybrid search: dense vector search + BM25 keyword search in parallel (~200ms)
7. RRF fusion + cross-encoder rerank (~100ms)
8. Retrieve top 5 chunks with source metadata
9. Augment prompt: system + context + question
10. Stream LLM response (Claude Sonnet, TTFT ~500ms)
11. Store in semantic cache, return with citations
```

---

### Scale Considerations

**Embedding storage for 10TB:**
```
10TB documents
Average document: 50KB = ~12,500 tokens
Total tokens: 10TB / 50KB * 12,500 = 2.5 billion tokens
After chunking (512 tokens, 50 overlap): ~5 billion chunks

text-embedding-3-small: 1536 dimensions, float32 = 6144 bytes/vector
5B chunks * 6144 bytes = 30TB of vectors!

Optimizations:
  - text-embedding-3-small with dimensions=256 (less accurate, 4x smaller)
  - Product Quantization (PQ): 16x compression with ~5% accuracy loss
  - Selective indexing: only index recent/relevant docs
  - Tiered storage: hot docs in Pinecone, cold in pgvector on cheaper storage
```

**Worker scaling:**
```
Ingestion: 10TB / average 5min processing per doc = need parallel processing
  100 workers * 1 doc/5min = 1200 docs/hour
  At 100KB avg: 120MB/hour throughput

Query: 100 QPS * 3s avg = 300 concurrent requests
  Each ECS task handles 50 concurrent (async)
  Need: 300/50 = 6 tasks minimum, 12 for headroom
  Auto-scale based on CPU + target response time SLO
```

---

### Trade-offs

```
Decision 1: Pinecone vs pgvector
  Pinecone: managed, scales automatically, native namespaces, fast
  pgvector: self-managed, colocated with metadata (JOIN queries), cheaper at scale
  Choice: Pinecone for < 500M vectors, pgvector for cost optimization at scale

Decision 2: Chunk size 512 vs 1024 tokens
  512: More precise retrieval, less context per chunk
  1024: More context, worse retrieval precision
  Choice: 512 with overlap=50, re-rank to get adjacent chunks if needed

Decision 3: Re-ranking always vs only for top results
  Always: Better quality, adds ~100ms
  Threshold: Only re-rank if top score < 0.8 (saves latency for clear matches)
  Choice: Threshold-based

Decision 4: Real-time indexing vs batch
  Real-time: <5min to searchable, complex, expensive
  Batch (nightly): Simple, cheap, stale data
  Choice: Near-real-time with SQS queue (typical latency 2-3 min)
```

---

### Follow-up Questions

1. "How would you handle a document update — user edits page 3 of a 100-page PDF?"
   - Track chunk IDs per page. Delete old chunks by doc_id + page, re-embed changed pages only.

2. "What happens when Pinecone is down? How do you maintain availability?"
   - Fallback to pgvector replica. Read-only mode with cached results. Circuit breaker pattern.

3. "How do you prevent prompt injection attacks from document content?"
   - Sanitize retrieved chunks before insertion. XML tags to separate context from instruction. Output validation.

4. "How would you evaluate retrieval quality? What metrics do you track?"
   - Recall@k (% of relevant docs retrieved), MRR, NDCG. LLM-as-judge for answer quality. User feedback signals.

5. "How do you handle very long documents that exceed context windows?"
   - Map-reduce summarization for overview queries. Targeted chunk retrieval for specific questions. Hierarchical indexing (document summary + detailed chunks).

---

## Design 2: Real-time Voicebot

**Prompt:** "Design a real-time voice AI assistant. Target: end-to-end latency < 2 seconds."

---

### Requirements

**Functional:**
- User speaks → bot responds with voice in < 2 seconds
- Interrupt handling (user can interrupt bot mid-speech)
- Multi-turn conversation with context
- Handle noise, accents, code-switching (English/Vietnamese)
- Transfer to human agent if bot can't handle

**Non-functional:**
- E2E latency: < 2000ms P95 (perceived as near-real-time)
- TTFT audio: < 300ms (first audio byte)
- Concurrent calls: 500
- Availability: 99.95% (4.4 hours/year)
- Cost: < $0.10 per minute of conversation

---

### Architecture Diagram

```
User Phone/Browser
        |
        | WebSocket (bidirectional, persistent)
        |
+------------------+
| WebSocket Gateway|  (ECS, 500 concurrent connections per instance)
| Port 443 WSS     |
+------------------+
        |
        | Audio chunks (20ms frames, 16kHz PCM)
        |
+------------------+      +------------------+
| VAD Service      |      | Session Store    |
| (Voice Activity  |      | (Redis)          |
| Detection)       |      | - conversation   |
| Silero VAD       |      |   history        |
+------------------+      | - user context   |
        |                 +------------------+
        | "utterance complete"
        |
+------------------+
| STT Service      |  Deepgram / Whisper
| (Speech-to-Text) |  ~100-200ms
+------------------+
        |
        | text transcript
        |
+------------------+      +------------------+
| Context Manager  |----->| RAG/KB Search    |
| (inject history) |      | (if knowledge    |
+------------------+      |  needed)         |
        |                 +------------------+
        | augmented prompt
        |
+------------------+
| LLM Service      |  claude-haiku-3-5 (fastest)
| (streaming)      |  TTFT ~300ms
+------------------+
        |
        | text stream (sentence by sentence)
        |
+------------------+
| TTS Service      |  ElevenLabs / AWS Polly
| (Text-to-Speech) |  ~150ms first audio chunk
+------------------+
        |
        | audio stream
        |
User hears response
```

---

### Latency Budget Breakdown

```
Total target: < 2000ms

Component             | Target  | Notes
----------------------|---------|----------------------------------
VAD detection         | 50ms    | Detect end-of-speech (20ms frames)
STT (speech-to-text)  | 150ms   | Deepgram streaming, near-realtime
Network (STT API)     | 50ms    | Parallel with LLM call if possible
LLM TTFT              | 300ms   | Claude Haiku, first token
Sentence buffer       | 100ms   | Wait for first complete sentence
TTS (first chunk)     | 150ms   | ElevenLabs streaming
Network (TTS)         | 50ms    | First audio packet to user
Total P50             | 850ms   |
Buffer for P95        | +1150ms | Network variance, model load
P95 target            | ~2000ms | Acceptable

Optimization strategies:
  - Parallel: start LLM call while STT is still processing tail audio
  - Streaming TTS: don't wait for full LLM response
  - Sentence-level TTS: convert each sentence as LLM generates it
  - Edge deployment: co-locate STT/TTS near user (CDN PoPs)
  - Connection pre-warming: WebSocket open before call starts
```

---

### Component Breakdown

**WebSocket Handler:**
```python
from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import json

class VoicebotSession:
    def __init__(self, session_id: str, user_id: str):
        self.session_id = session_id
        self.user_id = user_id
        self.conversation_history = []
        self.is_bot_speaking = False
        self.llm_task = None
        self.tts_queue = asyncio.Queue()

@app.websocket("/ws/voice/{session_id}")
async def voice_session(websocket: WebSocket, session_id: str):
    await websocket.accept()
    session = VoicebotSession(session_id, ...)

    # Start concurrent tasks
    audio_task = asyncio.create_task(receive_audio(websocket, session))
    send_task = asyncio.create_task(send_audio(websocket, session))

    try:
        await asyncio.gather(audio_task, send_task)
    except WebSocketDisconnect:
        await cleanup_session(session)

async def receive_audio(websocket: WebSocket, session: VoicebotSession):
    vad = SileroVAD()
    audio_buffer = bytearray()

    async for message in websocket.iter_bytes():
        # Interrupt handling: user speaks while bot is speaking
        if session.is_bot_speaking and vad.is_speech(message):
            # Cancel current bot response
            if session.llm_task:
                session.llm_task.cancel()
            await session.tts_queue.put(None)  # Signal stop
            session.is_bot_speaking = False

        audio_buffer.extend(message)
        vad_result = vad.process(message)

        if vad_result.end_of_speech:
            # Utterance complete, process
            asyncio.create_task(
                process_utterance(bytes(audio_buffer), session, websocket)
            )
            audio_buffer = bytearray()

async def process_utterance(audio: bytes, session: VoicebotSession, ws: WebSocket):
    # 1. STT
    transcript = await deepgram_stt(audio)

    # 2. Add to history
    session.conversation_history.append({"role": "user", "content": transcript})

    # 3. LLM streaming
    session.is_bot_speaking = True
    session.llm_task = asyncio.current_task()

    async with anthropic_client.messages.stream(
        model="claude-haiku-3-5",
        max_tokens=200,  # Short responses for voice
        messages=session.conversation_history
    ) as stream:
        sentence_buffer = ""
        async for text in stream.text_stream:
            sentence_buffer += text
            # Flush on sentence boundary
            if any(c in sentence_buffer for c in '.!?'):
                sentences = split_sentences(sentence_buffer)
                for sentence in sentences[:-1]:  # All but last (may be incomplete)
                    # TTS this sentence
                    audio_chunk = await elevenlabs_tts(sentence)
                    await session.tts_queue.put(audio_chunk)
                sentence_buffer = sentences[-1]  # Keep incomplete last sentence

        # Flush remaining
        if sentence_buffer:
            audio_chunk = await elevenlabs_tts(sentence_buffer)
            await session.tts_queue.put(audio_chunk)

    session.is_bot_speaking = False
```

---

### Failure Modes and Mitigations

```
Failure Mode 1: STT API timeout
  Detection: timeout > 3s
  Mitigation: Fallback to on-premise Whisper model (higher latency, always available)
  Recovery: "I'm having trouble hearing you, could you repeat that?"

Failure Mode 2: LLM rate limit
  Detection: 429 response
  Mitigation: Retry with exponential backoff (100ms, 200ms, 400ms)
  Fallback: Template responses for common intents
  Recovery: "Let me think about that for a moment..."

Failure Mode 3: WebSocket drops mid-conversation
  Detection: WebSocket disconnect event
  Mitigation: Session state persisted in Redis
  Recovery: Client reconnects with session_id, resumes from last state
  Timeout: Session expires after 5 minutes of inactivity

Failure Mode 4: TTS latency spike (> 500ms)
  Detection: p99 > 500ms
  Mitigation: Switch to AWS Polly (lower quality but lower latency: ~50ms)
  Alert: If ElevenLabs consistently slow, auto-switch provider
```

---

### Follow-up Questions

1. "How would you handle 10,000 concurrent calls instead of 500?"
   - Horizontal scaling: ECS auto-scale on connection count metric. WebSocket servers are stateless (session in Redis). Consider serverless WebSocket (API Gateway WebSocket API).

2. "How do you reduce perceived latency beyond 2 seconds?"
   - Filler words ("Hmm, let me check..."), start TTS while LLM still generating, predictive pre-loading of likely responses.

3. "How would you measure voice quality / user satisfaction?"
   - CSAT after call, transcript analysis for confused responses, silence detection (>3s = user confused), call abandonment rate, escalation to human rate.

4. "What if the user speaks a language the bot doesn't support?"
   - Language detection in STT (Deepgram supports 30+ languages). Route to language-specific model or graceful fallback: "I only support English and Vietnamese."

5. "How do you prevent the bot from giving wrong medical/legal advice?"
   - Guardrail prompts, topic classifiers to detect out-of-scope queries, mandatory disclaimers, hot-word detection to trigger human transfer.

---

## Design 3: AI Document Processing Pipeline at Scale (Temporal-based)

**Prompt:** "Design a system to process 10,000+ documents per batch using AI — extract data, classify, summarize. You've mentioned Temporal at Spartan. Walk me through the design."

---

### Requirements

**Functional:**
- Accept batch of 10,000+ documents (PDF, images, Word)
- Per-document: OCR → Classification → Data extraction → Summarization
- Idempotent: safe to re-run failed batches
- Progress tracking: real-time status per document
- Output: structured JSON per document + aggregate batch report
- Retry failed documents automatically, escalate persistent failures

**Non-functional:**
- Throughput: 10,000 docs/batch, target < 2 hours total
- SLA: 99% of documents processed successfully
- Cost predictability: know cost estimate before running
- Zero data loss: every document status persisted
- Scalable: same system handles 100 docs or 100,000 docs

---

### Architecture Diagram

```
                    BATCH SUBMISSION
+----------+   POST /batches    +----------+   Temporal Signal
| Client   |------------------>| FastAPI  |----------------->
+----------+                   | (Submit) |                  |
                                +----------+                  v
                                                    +------------------+
                                                    | Temporal Workflow|
                                                    | BatchWorkflow    |
                                                    +------------------+
                                                             |
                                          +------------------+------------------+
                                          |                                     |
                              Fan-out to child workflows             Batch orchestration
                                          |
                               +----------v----------+
                               | DocumentWorkflow    |
                               | (one per document)  |
                               +---------------------+
                                          |
                          +---------------+---------------+
                          |               |               |
                    Activity 1      Activity 2      Activity 3
                    +--------+      +--------+      +--------+
                    |  OCR   |      |Classify|      |Extract |
                    |Activity|      |Activity|      |Activity|
                    +--------+      +--------+      +--------+
                          |               |               |
                          +---------------+---------------+
                                          |
                                   Activity 4
                                  +--------+
                                  |Summarize|
                                  |Activity |
                                  +--------+
                                          |
                                   Activity 5
                                  +--------+
                                  | Store  |
                                  | Result |
                                  +--------+

INFRASTRUCTURE:
S3 (documents) -> Temporal Server (workflow state) -> PostgreSQL (results)
ECS Workers: Temporal Activity Workers (auto-scaled)
Redis: Progress cache (real-time status)
Datadog: Workflow metrics, error tracking
```

---

### Temporal Workflow Design

**BatchWorkflow:**
```python
from temporalio import workflow, activity
from temporalio.common import RetryPolicy
from datetime import timedelta
import asyncio
from dataclasses import dataclass

@dataclass
class BatchInput:
    batch_id: str
    document_s3_keys: list[str]
    config: dict
    tenant_id: str

@dataclass
class DocumentResult:
    doc_id: str
    status: str  # completed / failed
    classification: str | None
    extracted_data: dict | None
    summary: str | None
    error: str | None

@workflow.defn
class BatchWorkflow:
    """
    Orchestrates processing of a full document batch.
    Runs as long as needed (hours, days) - survives worker restarts.
    """

    def __init__(self):
        self._progress: dict[str, str] = {}
        self._results: list[DocumentResult] = []

    @workflow.run
    async def run(self, batch_input: BatchInput) -> dict:
        workflow.logger.info(f"Starting batch {batch_input.batch_id} with {len(batch_input.document_s3_keys)} docs")

        # Cost estimation activity (before spending money)
        estimated_cost = await workflow.execute_activity(
            estimate_batch_cost,
            args=[batch_input],
            start_to_close_timeout=timedelta(minutes=2)
        )

        if estimated_cost > batch_input.config.get("max_cost_usd", float('inf')):
            raise ValueError(f"Estimated cost ${estimated_cost:.2f} exceeds budget")

        # Fan-out: one child workflow per document
        # Limit concurrency to avoid overwhelming LLM APIs
        CONCURRENCY = 50  # Max 50 concurrent document workflows
        semaphore = asyncio.Semaphore(CONCURRENCY)

        async def process_with_semaphore(s3_key: str):
            async with semaphore:
                return await workflow.execute_child_workflow(
                    DocumentWorkflow,
                    args=[DocumentInput(
                        batch_id=batch_input.batch_id,
                        s3_key=s3_key,
                        tenant_id=batch_input.tenant_id
                    )],
                    id=f"{batch_input.batch_id}:{s3_key.split('/')[-1]}",
                    retry_policy=RetryPolicy(
                        maximum_attempts=3,
                        initial_interval=timedelta(seconds=30),
                        backoff_coefficient=2.0
                    )
                )

        # Process all documents
        tasks = [
            process_with_semaphore(key)
            for key in batch_input.document_s3_keys
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Compile batch report
        completed = [r for r in results if not isinstance(r, Exception)]
        failed = [r for r in results if isinstance(r, Exception)]

        return {
            "batch_id": batch_input.batch_id,
            "total": len(results),
            "completed": len(completed),
            "failed": len(failed),
            "success_rate": len(completed) / len(results) * 100,
            "estimated_cost_usd": estimated_cost
        }

    @workflow.signal
    async def cancel_batch(self):
        """Signal to cancel remaining work."""
        workflow.logger.info("Batch cancellation requested")
        # Temporal will cancel pending activities

    @workflow.query
    def get_progress(self) -> dict:
        """Query current progress without affecting workflow."""
        return self._progress

@workflow.defn
class DocumentWorkflow:
    """
    Processes a single document through the full pipeline.
    Idempotent: safe to re-run from any activity.
    """

    @workflow.run
    async def run(self, doc_input: DocumentInput) -> DocumentResult:
        doc_id = doc_input.s3_key.split("/")[-1]

        # Activity 1: OCR / Text Extraction
        extracted_text = await workflow.execute_activity(
            ocr_activity,
            args=[doc_input.s3_key],
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(maximum_attempts=3)
        )

        # Activity 2: Classification (cheap model)
        classification = await workflow.execute_activity(
            classify_document_activity,
            args=[extracted_text[:2000]],  # First 2000 chars enough for classification
            start_to_close_timeout=timedelta(minutes=2)
        )

        # Activity 3: Data Extraction (depends on classification)
        extracted_data = await workflow.execute_activity(
            extract_data_activity,
            args=[extracted_text, classification],
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=60)  # Back off on LLM rate limits
            )
        )

        # Activity 4: Summarization
        summary = await workflow.execute_activity(
            summarize_activity,
            args=[extracted_text, classification],
            start_to_close_timeout=timedelta(minutes=5)
        )

        # Activity 5: Store results (idempotent upsert)
        await workflow.execute_activity(
            store_result_activity,
            args=[DocumentResult(
                doc_id=doc_id,
                status="completed",
                classification=classification,
                extracted_data=extracted_data,
                summary=summary,
                error=None
            )],
            start_to_close_timeout=timedelta(minutes=1)
        )

        return DocumentResult(doc_id=doc_id, status="completed", ...)
```

**Activities (actual work):**
```python
@activity.defn
async def ocr_activity(s3_key: str) -> str:
    """Extract text from document. Idempotent: same input = same output."""
    # Check cache first (for re-runs)
    cache_key = f"ocr:{hashlib.md5(s3_key.encode()).hexdigest()}"
    cached = await redis.get(cache_key)
    if cached:
        return cached

    # Download from S3
    doc_bytes = await s3.get_object(s3_key)

    # OCR
    if s3_key.endswith(".pdf"):
        text = await pdf_extract_text(doc_bytes)
    else:
        text = await tesseract_ocr(doc_bytes)

    # Cache result (expensive to re-do)
    await redis.setex(cache_key, 86400, text)
    return text

@activity.defn
async def classify_document_activity(text_preview: str) -> str:
    """Classify document type using cheap fast model."""
    response = await anthropic_client.messages.create(
        model="claude-haiku-3-5",
        max_tokens=50,
        messages=[{
            "role": "user",
            "content": f"""Classify this document into one category:
            INVOICE | CONTRACT | REPORT | EMAIL | FORM | OTHER

            Document preview:
            {text_preview}

            Respond with only the category name."""
        }]
    )
    return response.content[0].text.strip()

@activity.defn
async def extract_data_activity(full_text: str, doc_type: str) -> dict:
    """Extract structured data. Uses prompt routing based on doc_type."""
    prompt_map = {
        "INVOICE": INVOICE_EXTRACTION_PROMPT,
        "CONTRACT": CONTRACT_EXTRACTION_PROMPT,
        "FORM": FORM_EXTRACTION_PROMPT,
    }
    prompt = prompt_map.get(doc_type, GENERIC_EXTRACTION_PROMPT)

    response = await anthropic_client.messages.create(
        model="claude-haiku-3-5",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": f"{prompt}\n\nDocument:\n{full_text[:50000]}"  # Truncate
        }]
    )

    # Parse JSON from response
    try:
        return json.loads(response.content[0].text)
    except json.JSONDecodeError:
        # LLM sometimes returns explanation + JSON, extract JSON part
        text = response.content[0].text
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        return json.loads(json_match.group()) if json_match else {}
```

---

### Idempotency Design

```
Temporal provides built-in idempotency at the workflow level:
  - Workflow ID is deterministic (batch_id + doc_id)
  - If workflow already exists with same ID: Temporal returns existing
  - Activities are replayed from event history on restart
  - No duplicate processing even if worker crashes mid-activity

Application-level idempotency:
  - OCR results cached in Redis by s3_key hash
  - Database upsert (ON CONFLICT DO UPDATE) for results
  - Idempotency key on LLM calls (not yet standard but add in request_id)

Batch idempotency:
  POST /batches {batch_id: "batch-2026-05-20", documents: [...]}
  If batch_id already exists: return existing batch status (don't reprocess)
  Use workflow ID = batch_id (Temporal deduplicates)
```

---

### Progress Tracking

```python
# Real-time progress API
@app.get("/batches/{batch_id}/progress")
async def get_batch_progress(batch_id: str):
    # Query Temporal workflow directly
    handle = temporal_client.get_workflow_handle(batch_id)

    try:
        progress = await handle.query(BatchWorkflow.get_progress)
    except WorkflowNotFoundError:
        raise HTTPException(404, "Batch not found")

    return {
        "batch_id": batch_id,
        "total_documents": progress["total"],
        "completed": progress["completed"],
        "failed": progress["failed"],
        "processing": progress["processing"],
        "percentage": progress["completed"] / progress["total"] * 100,
        "estimated_completion": progress.get("eta"),
        "current_cost_usd": progress.get("spent_usd", 0)
    }
```

---

### Follow-up Questions

1. "Why Temporal over Celery for this use case?"
   - Temporal: durable execution (workflow state survives crashes), built-in retry per activity, long-running (days), visibility into workflow state, versioning for safe deploys. Celery: simpler, better for short tasks, no durable state.

2. "How would you handle a document that keeps failing OCR?"
   - maxAttempts=3 on OCR activity. After 3 failures: mark as FAILED, continue batch. Alert engineering team. DLQ for manual review. Report failed docs to user.

3. "How do you estimate cost before running a 10,000 doc batch?"
   - Pre-scan: count pages (quick). Estimate: avg tokens per page * pages * cost/token. Present estimate, require user confirmation before proceeding.

4. "What's your approach to versioning Temporal workflows safely?"
   - workflow.patched() API for backward-compatible changes. New activities can be added, existing ones can be modified. Never change workflow logic that could break in-flight workflows.

5. "How would you handle rate limiting from LLM APIs mid-batch?"
   - Temporal activity retries with exponential backoff. Semaphore to limit concurrent LLM calls. RateLimiter per model. If sustained rate limiting: pause batch, alert, resume when quota available.

---

## Design 4: LLM Cost Monitoring & Budget System

**Prompt:** "Design a system to track LLM token usage, enforce budgets per user/team, and provide cost analytics."

---

### Requirements

**Functional:**
- Track every LLM API call: user, team, model, tokens in/out, cost, timestamp
- Budget enforcement: per-user daily/monthly, per-team monthly
- Real-time alerts: 80% of budget reached, 100% (hard block)
- Cost analytics dashboard: by model, user, team, feature, time range
- Budget management API: set, adjust, view remaining budget
- Cost attribution: tag costs to specific features/projects

**Non-functional:**
- Tracking latency overhead: < 5ms added to each LLM call
- No data loss: every token tracked (billing accuracy)
- Real-time: budget remaining visible within 1 second of spend
- Scale: 1M LLM calls/day
- Retention: 2 years of cost history

---

### Architecture Diagram

```
                    TRACKING LAYER (in-band)
LLM Call
    |
    v
+------------------+      +-----------+
| LLM Proxy        |----->| Budget    |
| (intercept all   |      | Check     |---> ALLOW / BLOCK
| LLM API calls)   |      | (Redis)   |     (< 1ms)
+------------------+      +-----------+
    |
    | (async, fire-and-forget)
    |
    v
+------------------+
| Kafka / SQS      |  Events: {user_id, model, tokens, cost, timestamp, tags}
+------------------+
    |
    |
    v
+------------------+      +------------------+
| Cost Aggregator  |----->| TimescaleDB      |
| (ECS Workers)    |      | (time-series     |
| - aggregate      |      |  cost data)      |
| - write to DB    |      +------------------+
| - update Redis   |              |
+------------------+      +------+-------+
                           |             |
                    +----------+   +----------+
                    | Analytics|   | Datadog  |
                    | API      |   | Dashboard|
                    | (FastAPI)|   | (metrics)|
                    +----------+   +----------+

                    BUDGET ENFORCEMENT
+------------------+      +------------------+
| Budget Service   |<---->| Redis            |
| - check budget   |      | user:budget:{id} |
| - deduct spend   |      | team:budget:{id} |
| - trigger alerts |      | (remaining cents)|
+------------------+      +------------------+
    |
    v
+------------------+
| Alert Service    | --> Slack / Email / PagerDuty
| (80%, 100%)      |
+------------------+
```

---

### Component Breakdown

**LLM Proxy (intercepts all calls):**
```python
from functools import wraps
import asyncio
from dataclasses import dataclass
from datetime import datetime, date
import redis.asyncio as redis

redis_client = redis.Redis(decode_responses=True)

@dataclass
class LLMCallEvent:
    call_id: str
    user_id: str
    team_id: str
    feature: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_cents: int  # Store as integer cents to avoid float precision issues
    timestamp: datetime
    metadata: dict

COST_CENTS_PER_M_TOKENS = {
    "gpt-4o": {"input": 250, "output": 1000},           # $2.50/$10.00
    "gpt-4o-mini": {"input": 15, "output": 60},          # $0.15/$0.60
    "claude-haiku-3-5": {"input": 80, "output": 400},    # $0.80/$4.00
    "claude-sonnet-4-5": {"input": 300, "output": 1500}, # $3.00/$15.00
}

async def check_and_deduct_budget(
    user_id: str,
    team_id: str,
    estimated_cost_cents: int
) -> tuple[bool, str]:
    """
    Check budget and reserve cost atomically.
    Returns: (allowed, reason)
    """
    # Use Redis pipeline for atomicity
    async with redis_client.pipeline(transaction=True) as pipe:
        today = date.today().isoformat()
        month = date.today().strftime("%Y-%m")

        user_daily_key = f"budget:user:{user_id}:daily:{today}"
        user_monthly_key = f"budget:user:{user_id}:monthly:{month}"
        team_monthly_key = f"budget:team:{team_id}:monthly:{month}"

        # Check current spend
        pipe.get(user_daily_key)
        pipe.get(user_monthly_key)
        pipe.get(team_monthly_key)
        current_values = await pipe.execute()

        user_daily_spent = int(current_values[0] or 0)
        user_monthly_spent = int(current_values[1] or 0)
        team_monthly_spent = int(current_values[2] or 0)

        # Get limits from config (cached from DB)
        limits = await get_budget_limits(user_id, team_id)

        # Check if would exceed
        if user_daily_spent + estimated_cost_cents > limits["user_daily_cents"]:
            return False, "User daily budget exceeded"

        if user_monthly_spent + estimated_cost_cents > limits["user_monthly_cents"]:
            return False, "User monthly budget exceeded"

        if team_monthly_spent + estimated_cost_cents > limits["team_monthly_cents"]:
            return False, "Team monthly budget exceeded"

        # Reserve budget (deduct optimistically)
        pipe.incrby(user_daily_key, estimated_cost_cents)
        pipe.expire(user_daily_key, 86400 * 2)  # 2 day TTL
        pipe.incrby(user_monthly_key, estimated_cost_cents)
        pipe.expire(user_monthly_key, 86400 * 35)  # 35 day TTL
        pipe.incrby(team_monthly_key, estimated_cost_cents)
        pipe.expire(team_monthly_key, 86400 * 35)
        await pipe.execute()

    return True, "ok"

def llm_cost_tracking(feature: str):
    """Decorator: intercept LLM calls, check budget, track costs."""
    def decorator(func):
        @wraps(func)
        async def wrapper(self_or_cls, *args, **kwargs):
            user_id = get_current_user_id()
            team_id = get_current_team_id()

            # Estimate cost before call
            prompt = extract_prompt(args, kwargs)
            estimated_tokens = count_tokens(prompt)
            model = kwargs.get("model", "claude-haiku-3-5")
            costs = COST_CENTS_PER_M_TOKENS.get(model, {"input": 100, "output": 500})
            estimated_cost = (estimated_tokens * costs["input"]) // 1_000_000

            # Budget check
            allowed, reason = await check_and_deduct_budget(
                user_id, team_id, estimated_cost
            )
            if not allowed:
                raise BudgetExceededException(f"LLM call blocked: {reason}")

            # Make LLM call
            start = time.perf_counter()
            response = await func(self_or_cls, *args, **kwargs)
            latency_ms = (time.perf_counter() - start) * 1000

            # Track actual cost (async, non-blocking)
            actual_input = response.usage.input_tokens
            actual_output = response.usage.output_tokens
            actual_cost = (
                (actual_input * costs["input"]) +
                (actual_output * costs["output"])
            ) // 1_000_000

            # Reconcile (adjust for estimation error)
            correction = actual_cost - estimated_cost
            if correction != 0:
                await adjust_budget_deduction(user_id, team_id, correction)

            # Fire-and-forget: publish event for analytics
            asyncio.create_task(publish_cost_event(LLMCallEvent(
                call_id=str(uuid.uuid4()),
                user_id=user_id,
                team_id=team_id,
                feature=feature,
                model=model,
                input_tokens=actual_input,
                output_tokens=actual_output,
                cost_cents=actual_cost,
                timestamp=datetime.utcnow(),
                metadata={"latency_ms": latency_ms}
            )))

            return response
        return wrapper
    return decorator
```

**Analytics API:**
```python
@app.get("/analytics/costs")
async def get_cost_analytics(
    start_date: date,
    end_date: date,
    group_by: str = "day",  # day | week | model | user | feature
    user_id: str | None = None,
    team_id: str | None = None,
    model: str | None = None,
):
    """
    Flexible cost analytics with grouping.
    Backed by TimescaleDB continuous aggregates for fast queries.
    """
    query = """
        SELECT
            time_bucket($1::interval, timestamp) as bucket,
            group_by_col,
            SUM(cost_cents) as total_cost_cents,
            SUM(input_tokens) as total_input_tokens,
            SUM(output_tokens) as total_output_tokens,
            COUNT(*) as call_count,
            AVG(cost_cents) as avg_cost_per_call
        FROM llm_calls
        WHERE timestamp BETWEEN $2 AND $3
            AND ($4::text IS NULL OR user_id = $4)
            AND ($5::text IS NULL OR team_id = $5)
            AND ($6::text IS NULL OR model = $6)
        GROUP BY bucket, group_by_col
        ORDER BY bucket DESC
    """

    results = await db.fetch(query, group_by, start_date, end_date, user_id, team_id, model)

    return {
        "period": {"start": start_date, "end": end_date},
        "group_by": group_by,
        "total_cost_usd": sum(r["total_cost_cents"] for r in results) / 100,
        "data": [
            {
                "bucket": r["bucket"],
                "group": r["group_by_col"],
                "cost_usd": r["total_cost_cents"] / 100,
                "input_tokens": r["total_input_tokens"],
                "output_tokens": r["total_output_tokens"],
                "calls": r["call_count"],
                "avg_cost_per_call_usd": r["avg_cost_per_call"] / 100
            }
            for r in results
        ]
    }
```

---

### Follow-up Questions

1. "What if a user runs a huge request that exceeds budget mid-generation?"
   - Pre-estimate tokens before calling LLM. If over budget, reject before calling. For streaming: track tokens real-time, stop generation if budget exceeded.

2. "How do you handle budget refills at start of month?"
   - Cron job at midnight UTC 1st of month: reset Redis counters. Or use expiry-based: keys expire after 30 days, naturally reset.

3. "What if the Redis budget counter gets out of sync with DB?"
   - Periodic reconciliation job: compare Redis counters with DB aggregates. If drift > 5%: resync Redis from DB. Alert if drift detected.

4. "How do you attribute costs to features in a multi-step pipeline?"
   - Pass `feature_tag` through context var. Each LLM call tagged with current feature. Report: "RAG pipeline = 40%, summarization = 35%, classification = 25%."

5. "How would you handle a sudden 10x spike in costs?"
   - Anomaly detection: if hourly cost > 3x 7-day average, auto-alert. Emergency rate limit: global throttle. Cost spike dashboard in Datadog.

---

## Design 5: Conversational AI with Long-term Memory

**Prompt:** "Design a conversational AI system that remembers users across sessions and personalizes responses."

---

### Requirements

**Functional:**
- Remember facts mentioned by user across sessions (name, preferences, past conversations)
- Recall relevant past context when answering new questions
- Forget specific memories on user request (GDPR compliance)
- Personalize response style based on user history
- Cross-device: same memory regardless of device

**Non-functional:**
- Memory retrieval: < 200ms (must not slow down response)
- Memory storage: up to 10,000 memories per user
- Retention: configurable per user (6 months to forever)
- Privacy: memories encrypted, isolated per user
- Scale: 100,000 users

---

### Architecture Diagram

```
User message
    |
    v
+------------------+
| FastAPI           |
| /chat             |
+------------------+
    |
    +---> Memory Retrieval (async, parallel with LLM prep)
    |         |
    |    +----------+      +------------------+
    |    | Memory   |----->| Vector DB        |
    |    | Retriever|      | (pgvector/Pinecone)
    |    +----------+      | user_id namespace|
    |         |            +------------------+
    |         |
    |    relevant memories
    |         |
    v         v
+------------------+
| Context Builder  |
| - system prompt  |
| - user memories  |
| - recent history |
| - current query  |
+------------------+
    |
    v
+------------------+
| LLM (Claude)     |  With memory-enriched context
+------------------+
    |
    +---> Memory Extraction (async, after response)
              |
         +----------+      +------------------+
         | Memory   |      | PostgreSQL       |
         | Extractor|----->| (raw memories,   |
         | (Claude  |      |  metadata)       |
         |  mini)   |      +------------------+
         +----------+            |
                          +----------+
                          | Embedder |
                          +----------+
                                |
                          +------------------+
                          | Vector DB        |
                          | (searchable)     |
                          +------------------+
```

---

### Memory Types and Architecture

**3 Types of Memory:**
```python
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

class MemoryType(Enum):
    EPISODIC = "episodic"      # "User mentioned they have a dog named Max"
    SEMANTIC = "semantic"      # "User prefers concise answers"
    PROCEDURAL = "procedural"  # "User always asks about Python, skip basics"

@dataclass
class Memory:
    memory_id: str
    user_id: str
    memory_type: MemoryType
    content: str           # "User's name is Sarah, works at TechCorp"
    source_message: str    # Original message that triggered this memory
    embedding: list[float] # For semantic search
    confidence: float      # 0.0-1.0 (how sure we are this is accurate)
    created_at: datetime
    last_accessed: datetime
    access_count: int
    expires_at: datetime | None  # None = never expires
    importance: float      # 0.0-1.0 (how important/frequently useful)
```

**Memory Extraction:**
```python
async def extract_memories_from_conversation(
    user_message: str,
    assistant_response: str,
    user_id: str
) -> list[Memory]:
    """
    After each conversation turn, extract memorable facts.
    Runs async - doesn't block user response.
    """
    extraction_prompt = f"""
    Analyze this conversation and extract any important facts about the user that should be remembered.

    User said: "{user_message}"
    Assistant said: "{assistant_response}"

    Extract only facts that would be useful to remember for future conversations.
    Include: personal info, preferences, expertise level, past decisions, goals.
    Skip: trivial, one-off, or sensitive info.

    Return JSON array:
    [
      {{
        "content": "fact to remember",
        "type": "episodic|semantic|procedural",
        "confidence": 0.0-1.0,
        "importance": 0.0-1.0
      }}
    ]
    Return empty array [] if nothing worth remembering.
    """

    response = await anthropic_client.messages.create(
        model="claude-haiku-3-5",  # Cheap model for extraction
        max_tokens=500,
        messages=[{"role": "user", "content": extraction_prompt}]
    )

    try:
        extracted = json.loads(response.content[0].text)
    except json.JSONDecodeError:
        return []

    memories = []
    for item in extracted:
        if item.get("confidence", 0) < 0.7:
            continue  # Skip low-confidence extractions

        embedding = await get_embedding(item["content"])

        memory = Memory(
            memory_id=str(uuid.uuid4()),
            user_id=user_id,
            memory_type=MemoryType(item["type"]),
            content=item["content"],
            source_message=user_message,
            embedding=embedding,
            confidence=item["confidence"],
            created_at=datetime.utcnow(),
            last_accessed=datetime.utcnow(),
            access_count=0,
            expires_at=None,
            importance=item["importance"]
        )
        memories.append(memory)

    return memories

# Memory retrieval
async def retrieve_relevant_memories(
    query: str,
    user_id: str,
    top_k: int = 10,
    min_similarity: float = 0.7
) -> list[Memory]:
    """
    Retrieve memories relevant to current query.
    Uses semantic search + recency + importance scoring.
    """
    query_embedding = await get_embedding(query)

    # Vector search within user's namespace
    raw_results = await vector_store.query(
        namespace=f"memories:{user_id}",
        vector=query_embedding,
        top_k=top_k * 2,  # Get more, then re-rank
        include_metadata=True
    )

    memories = []
    for result in raw_results:
        if result.score < min_similarity:
            continue

        memory = Memory(**result.metadata)

        # Composite score: similarity * recency * importance
        days_old = (datetime.utcnow() - memory.created_at).days
        recency_score = max(0.3, 1.0 - (days_old / 365))  # Decay over 1 year
        composite_score = result.score * 0.5 + recency_score * 0.3 + memory.importance * 0.2

        memories.append((composite_score, memory))

    # Sort by composite score
    memories.sort(key=lambda x: x[0], reverse=True)
    return [m for _, m in memories[:top_k]]
```

**Context Building:**
```python
async def build_context_with_memory(
    user_id: str,
    current_message: str,
    session_history: list[dict]
) -> list[dict]:
    """
    Build LLM context: system prompt + memories + session history.
    """
    # Parallel: retrieve memories + prepare session context
    memories, _ = await asyncio.gather(
        retrieve_relevant_memories(current_message, user_id, top_k=8),
        asyncio.sleep(0)  # Placeholder for other parallel work
    )

    # Format memories for injection
    memory_text = ""
    if memories:
        memory_text = "\n\nKnown facts about the user:\n"
        for mem in memories:
            memory_text += f"- {mem.content} (remembered from {mem.created_at.strftime('%b %Y')})\n"

    system_prompt = f"""You are a helpful AI assistant with memory of past conversations.
Use the known facts about the user to personalize your responses.
Be natural - don't explicitly mention "I remember that..." unless directly relevant.
Adjust your explanation depth based on the user's expertise level if known.

{memory_text}"""

    # Build messages: system + recent history + current
    messages = [
        {"role": "system", "content": system_prompt}
    ]

    # Include recent session history (last 10 turns, summarize older ones)
    recent_history = session_history[-10:] if len(session_history) > 10 else session_history
    messages.extend(recent_history)
    messages.append({"role": "user", "content": current_message})

    return messages
```

---

### GDPR Compliance: Right to Forget

```python
@app.delete("/users/{user_id}/memories")
async def delete_all_memories(user_id: str, current_user: CurrentUser):
    if current_user.id != user_id:
        raise HTTPException(403)

    # 1. Delete from vector store
    await vector_store.delete(
        namespace=f"memories:{user_id}",
        delete_all=True
    )

    # 2. Delete from PostgreSQL
    await db.execute(
        "DELETE FROM memories WHERE user_id = $1",
        user_id
    )

    # 3. Log deletion for audit trail (keep this record!)
    await db.execute(
        "INSERT INTO gdpr_deletion_log (user_id, deleted_at, type) VALUES ($1, NOW(), 'full_memory_deletion')",
        user_id
    )

    return {"message": "All memories deleted"}

@app.delete("/users/{user_id}/memories/{memory_id}")
async def delete_specific_memory(user_id: str, memory_id: str, current_user: CurrentUser):
    """User can delete specific memories (e.g., incorrect facts)."""
    await vector_store.delete(ids=[f"{user_id}:{memory_id}"])
    await db.execute(
        "DELETE FROM memories WHERE user_id = $1 AND memory_id = $2",
        user_id, memory_id
    )
    return {"message": "Memory deleted"}

@app.get("/users/{user_id}/memories")
async def list_my_memories(user_id: str, current_user: CurrentUser):
    """Users can view all their stored memories (transparency)."""
    memories = await db.fetch(
        "SELECT memory_id, content, memory_type, created_at, importance FROM memories WHERE user_id = $1 ORDER BY created_at DESC",
        user_id
    )
    return {"memories": memories}
```

---

### Memory Management and Pruning

```python
async def prune_memories(user_id: str):
    """
    Periodic job: prune old/low-quality memories to stay under limit.
    Runs daily as Celery Beat task.
    """
    # Get all memories with stats
    memories = await db.fetch(
        """SELECT memory_id, content, memory_type, created_at, last_accessed,
                  access_count, importance, expires_at
           FROM memories WHERE user_id = $1
           ORDER BY importance ASC, last_accessed ASC""",
        user_id
    )

    # Delete expired memories
    expired = [m for m in memories if m["expires_at"] and m["expires_at"] < datetime.utcnow()]
    for mem in expired:
        await delete_specific_memory(user_id, mem["memory_id"])

    # If still over limit (10,000), prune lowest-value memories
    remaining = [m for m in memories if m not in expired]
    MEMORY_LIMIT = 10_000

    if len(remaining) > MEMORY_LIMIT:
        to_prune = remaining[:len(remaining) - MEMORY_LIMIT]
        for mem in to_prune:
            await delete_specific_memory(user_id, mem["memory_id"])

    # Consolidate similar memories (merge duplicates)
    await consolidate_similar_memories(user_id)

async def consolidate_similar_memories(user_id: str):
    """
    Find highly similar memories and merge them.
    E.g., "User likes Python" + "User prefers Python to Java" -> merged.
    """
    memories = await get_all_memories_with_embeddings(user_id)

    for i, mem_a in enumerate(memories):
        for mem_b in memories[i+1:]:
            similarity = cosine_similarity(mem_a.embedding, mem_b.embedding)
            if similarity > 0.95:  # Very similar memories
                # Merge with LLM
                merged = await merge_memories_with_llm(mem_a.content, mem_b.content)
                # Delete both, create merged
                await delete_specific_memory(user_id, mem_a.memory_id)
                await delete_specific_memory(user_id, mem_b.memory_id)
                await store_memory(user_id, merged)
```

---

### Follow-up Questions

1. "How do you prevent the system from 'hallucinating' false memories?"
   - Confidence threshold (>0.7 to store). Review source_message when memory is used. User can correct/delete wrong memories. Never state memories as absolute fact in LLM prompt: "User seems to prefer..." not "User definitely..."

2. "How do you handle conflicting memories? ('User said they live in Hanoi' vs 'User said they live in HCMC')"
   - LLM-based conflict detection when new memory contradicts existing one. Prompt: "Does this new fact conflict with any existing memories?" If conflict: store both with timestamps, use more recent one. Alert user to confirm.

3. "What's the memory retrieval strategy for a 10,000-memory user? How do you pick the right 10 to inject?"
   - Hybrid: semantic search (relevance to current query) + recency bonus + access frequency (frequently accessed = useful). Composite scoring. Budget tokens: inject most important memories within token budget.

4. "How would you scale to 1M users each with 10,000 memories?"
   - Separate vector namespace per user (already doing this). Sharding: users split across multiple Pinecone indexes. Caching: recently active users' memories cached in Redis. Tiered storage: frequent users in hot storage, inactive in cold storage.

5. "How do you measure if memory is actually improving user experience?"
   - A/B test: 50% users with memory, 50% without. Measure: session length, user satisfaction, questions asking bot to repeat information (lower = memory working). Track memory hit rate (how often retrieved memories are actually relevant to the response).

---

---

## Design 6: Financial Data Pipeline (WorldQuant-style)

**Prompt:** "Design a system to ingest, store, and serve daily OHLCV market data for 10,000 stocks across 20 years of history. The system must support both batch historical queries and real-time research workflows."

---

### Requirements

**Functional:**
- Ingest OHLCV data (Open/High/Low/Close/Volume) from multiple data vendors
- Adjust for corporate actions: stock splits, dividends, mergers
- Serve historical queries: "give me AAPL daily prices from 2010-2024"
- Serve cross-sectional queries: "give me all stocks' closes on 2023-01-05"
- Support researcher workflows: Python API returning pandas DataFrames
- Point-in-time correctness: no look-ahead bias

**Non-functional:**
- Data volume: 10,000 stocks × 252 trading days × 20 years = 50.4M rows
- Query latency: single-stock 20yr history < 200ms; cross-section < 500ms
- Ingestion: daily batch (end of day), < 30 minutes to available
- Availability: 99.9% (researchers need data every morning)
- Data quality: detect and alert on price spikes, missing days, stale data

---

### Architecture Diagram

```
DATA VENDORS (Bloomberg, Refinitiv, Quandl, etc.)
        |
        | FTP / API pull (daily, EOD)
        v
+------------------+    +-----------------+
| Ingestion Service|    | Corporate Action|
| (Python + Airflow|    | Adjuster        |
| DAG, runs 6PM)   |--->| (splits, divs)  |
+------------------+    +-----------------+
        |                       |
        v                       v
+------------------------------------------+
|              Raw Data Lake (S3)           |
| /raw/vendor=bloomberg/date=2024-01-05/   |
| /adjusted/date=2024-01-05/               |
| Format: Parquet, partitioned by date     |
+------------------------------------------+
        |
        | ETL (data quality checks + transformation)
        v
+------------------------------------------+
|          Time-series Database            |
|  ClickHouse (columnar, OLAP-optimized)   |
|  Tables:                                 |
|    ohlcv_daily  (50M rows, ~8GB)         |
|    ohlcv_adj    (adjusted prices)        |
|    corp_actions (split/div events)       |
+------------------------------------------+
        |
        +-----------------+------------------+
        |                                    |
+------------------+              +------------------+
| Redis Cache      |              | Query API        |
| - recent prices  |              | (FastAPI)        |
| - cross-sections |              | /prices/{symbol} |
| TTL: 24h         |              | /cross-section   |
+------------------+              | /factor          |
                                  +------------------+
                                          |
                              +-----------+-----------+
                              |                       |
                    Research Notebooks          Backtest Engine
                    (Jupyter + Python SDK)      (reads Parquet directly)
```

---

### Critical Concept: Point-in-Time Correctness

```
LOOK-AHEAD BIAS: using data that wasn't available at the time of the trade.

Example of BAD data pipeline:
  2024-01-05: Earnings announced after market close
  Revised EPS data updated retroactively to 2024-01-05
  Strategy backtested using revised EPS → shows fake profits

SOLUTION: as_of_date field on every record
  Each data point has:
    - trade_date:   the date the price/data is for
    - as_of_date:   the date this data was first available in our system

  Correct backtest query:
    SELECT * FROM fundamentals
    WHERE trade_date = '2024-01-05'
    AND as_of_date <= '2024-01-05'   -- Only data available on that date
    ORDER BY as_of_date DESC LIMIT 1  -- Latest revision available

Python SDK enforces this:
  data.get_prices(symbol="AAPL", start="2020-01-01", as_of="2020-01-01")
  # Returns only data that was known on 2020-01-01 — no look-ahead
```

---

### Corporate Action Adjustment

```python
import pandas as pd
import numpy as np

def adjust_prices_for_splits(raw_prices: pd.DataFrame,
                              splits: pd.DataFrame) -> pd.DataFrame:
    """
    Adjust historical prices for stock splits.
    Apple 4:1 split on 2020-08-31: all prices BEFORE that date ÷ 4

    raw_prices: DatetimeIndex × {open, high, low, close, volume}
    splits: {date, ratio}  e.g. {2020-08-31, 4.0}
    """
    adjusted = raw_prices.copy()

    # Process splits in reverse chronological order
    for _, split in splits.sort_values("date", ascending=False).iterrows():
        split_date = split["date"]
        ratio = split["ratio"]

        # All prices BEFORE split date → divide by ratio
        mask = adjusted.index < split_date
        adjusted.loc[mask, ["open", "high", "low", "close"]] /= ratio
        adjusted.loc[mask, "volume"] *= ratio  # Volume adjusted inversely

    return adjusted

def adjust_prices_for_dividends(prices: pd.DataFrame,
                                 dividends: pd.DataFrame) -> pd.DataFrame:
    """
    Dividend adjustment: subtract dividend from all historical prices.
    This creates a continuous return series that includes dividend income.
    """
    adjusted = prices.copy()

    for _, div in dividends.sort_values("ex_date", ascending=False).iterrows():
        ex_date = div["ex_date"]
        amount = div["amount"]
        close_before = prices.loc[prices.index < ex_date, "close"].iloc[-1]

        # Adjustment factor = (close - dividend) / close
        factor = (close_before - amount) / close_before

        mask = adjusted.index < ex_date
        adjusted.loc[mask, ["open", "high", "low", "close"]] *= factor

    return adjusted
```

---

### Storage: ClickHouse Schema

```sql
-- ClickHouse: columnar storage, optimized for analytical queries
CREATE TABLE ohlcv_adjusted (
    symbol      LowCardinality(String),   -- ~10K unique values → dictionary encoding
    trade_date  Date,
    open        Float32,
    high        Float32,
    low         Float32,
    close       Float32,
    volume      UInt64,
    as_of_date  Date,                     -- point-in-time correctness
    vendor      LowCardinality(String)
)
ENGINE = MergeTree()
ORDER BY (symbol, trade_date)             -- Primary sort: enables fast symbol lookups
PARTITION BY toYYYYMM(trade_date)         -- Monthly partitions: prune old data fast
SETTINGS index_granularity = 8192;

-- Query: single stock history (hits 1 partition range, sorted order)
SELECT trade_date, close
FROM ohlcv_adjusted
WHERE symbol = 'AAPL'
  AND trade_date BETWEEN '2020-01-01' AND '2024-12-31'
  AND as_of_date <= '2024-01-01'
ORDER BY trade_date;
-- Latency: ~20ms (columnar scan, sorted primary key)

-- Query: cross-section (all stocks on one date)
SELECT symbol, close
FROM ohlcv_adjusted
WHERE trade_date = '2024-01-05'
  AND as_of_date <= '2024-01-05';
-- Latency: ~100ms (single partition, all symbols)

-- Query: factor computation (rolling return across all stocks)
SELECT
    symbol,
    trade_date,
    close / lagInFrame(close, 20) OVER (
        PARTITION BY symbol
        ORDER BY trade_date
        ROWS BETWEEN 20 PRECEDING AND CURRENT ROW
    ) - 1 AS momentum_20d
FROM ohlcv_adjusted
WHERE trade_date >= '2023-01-01';
```

---

### Data Quality Pipeline

```python
from dataclasses import dataclass
from typing import Callable
import pandas as pd
import numpy as np

@dataclass
class QualityCheck:
    name: str
    check_fn: Callable[[pd.DataFrame], pd.Series]  # Returns bool mask of FAILED rows
    severity: str  # "critical" (block load) or "warning" (alert only)

QUALITY_CHECKS = [
    QualityCheck(
        name="price_spike",
        check_fn=lambda df: (
            df["close"].pct_change().abs() > 0.5  # >50% price move in 1 day
        ),
        severity="critical"
    ),
    QualityCheck(
        name="negative_price",
        check_fn=lambda df: df["close"] <= 0,
        severity="critical"
    ),
    QualityCheck(
        name="zero_volume",
        check_fn=lambda df: df["volume"] == 0,
        severity="warning"
    ),
    QualityCheck(
        name="ohlc_inconsistent",
        check_fn=lambda df: (df["high"] < df["low"]) | (df["close"] > df["high"]),
        severity="critical"
    ),
    QualityCheck(
        name="missing_trading_days",
        check_fn=lambda df: (
            df.index.to_series().diff().dt.days > 5  # Gap > 5 days (non-holiday)
        ),
        severity="warning"
    ),
]

def validate_and_load(df: pd.DataFrame, symbol: str) -> tuple[bool, list[str]]:
    issues = []

    for check in QUALITY_CHECKS:
        failed_mask = check.check_fn(df)
        if failed_mask.any():
            failed_dates = df.index[failed_mask].tolist()
            issues.append(f"{check.name}: {len(failed_dates)} rows — {failed_dates[:3]}")

            if check.severity == "critical":
                # Block load, send alert
                alert_team(f"[CRITICAL] {symbol}: {check.name} — {failed_dates[:3]}")
                return False, issues  # Don't load this symbol today

    return True, issues
```

---

### Researcher Python SDK

```python
import pandas as pd
import redis
import clickhouse_connect

class MarketDataClient:
    """
    SDK researchers use in Jupyter notebooks.
    Abstracts storage layer — researchers just get DataFrames.
    """

    def __init__(self):
        self.ch = clickhouse_connect.get_client(host="clickhouse-cluster")
        self.cache = redis.Redis(host="redis-cache")

    def get_prices(
        self,
        symbols: str | list[str],
        start: str,
        end: str,
        fields: list[str] = ["close"],
        adjusted: bool = True,
        as_of: str | None = None,   # Point-in-time: None = latest
    ) -> pd.DataFrame:
        """
        Returns DataFrame: index=DatetimeIndex, columns=symbols (if MultiIndex: (field, symbol))

        Usage:
            prices = client.get_prices("AAPL", "2020-01-01", "2024-12-31")
            prices = client.get_prices(["AAPL", "MSFT"], "2020-01-01", "2024-12-31")
        """
        if isinstance(symbols, str):
            symbols = [symbols]

        as_of_filter = f"AND as_of_date <= '{as_of}'" if as_of else ""
        table = "ohlcv_adjusted" if adjusted else "ohlcv_raw"

        query = f"""
            SELECT symbol, trade_date, {', '.join(fields)}
            FROM {table}
            WHERE symbol IN ({', '.join(f"'{s}'" for s in symbols)})
              AND trade_date BETWEEN '{start}' AND '{end}'
              {as_of_filter}
            ORDER BY symbol, trade_date
        """

        df = self.ch.query_df(query)
        df["trade_date"] = pd.to_datetime(df["trade_date"])

        # Pivot to wide format: index=date, columns=symbol
        if len(fields) == 1:
            return df.pivot(index="trade_date", columns="symbol", values=fields[0])
        else:
            return df.set_index(["trade_date", "symbol"]).unstack("symbol")

    def get_cross_section(self, date: str, fields: list[str] = ["close"]) -> pd.DataFrame:
        """All stocks on a single date — cache-friendly for research."""
        cache_key = f"xsec:{date}:{':'.join(fields)}"
        cached = self.cache.get(cache_key)
        if cached:
            return pd.read_msgpack(cached)  # Fast deserialization

        query = f"""
            SELECT symbol, {', '.join(fields)}
            FROM ohlcv_adjusted
            WHERE trade_date = '{date}'
            ORDER BY symbol
        """
        df = self.ch.query_df(query).set_index("symbol")
        self.cache.setex(cache_key, 86400, df.to_msgpack())
        return df

# Researcher notebook usage:
# client = MarketDataClient()
# prices = client.get_prices(["AAPL", "MSFT", "GOOG"], "2020-01-01", "2024-12-31")
# returns = prices.pct_change()
# correlation = returns.corr()
```

---

### Follow-up Questions

1. **"What is look-ahead bias and how do you prevent it in a quant system?"**
   - Occurs when backtest uses data not available at trade time. Fix: `as_of_date` on every record. Researcher API enforces `as_of` parameter. Separate "raw" (as-received) vs "revised" (corrected later) tables.

2. **"How do you handle a data vendor sending duplicate or backdated records?"**
   - Idempotent ingestion: upsert on `(symbol, trade_date, vendor)` unique key. Track `as_of_date = today()` for each ingestion run. Backdated corrections stored as new records, not overwrites — preserves history.

3. **"A researcher asks: 'AAPL split 4:1 in 2020, why does my backtest show a 75% drop?' — what happened?"**
   - They used unadjusted prices. Raw price went from $400 → $100 (4:1 split). Fix: always use `adjusted=True`. Adjustment multiplies all pre-split prices by 0.25 to create continuous price series.

4. **"How would you support real-time (intraday) data alongside daily data?"**
   - Separate streaming pipeline: WebSocket feed → Kafka → real-time ClickHouse table. Daily pipeline merges end-of-day consolidated into main table. Researchers choose granularity in SDK: `frequency="1d"` or `frequency="1m"`.

5. **"ClickHouse vs TimescaleDB for this use case — why?"**
   - ClickHouse: better for OLAP (analytical queries, aggregations, cross-sections), columnar compression, faster for read-heavy research workflows. TimescaleDB: better for operational workloads, time-bucketing functions, integrates with existing PostgreSQL stack. For pure research/analytics: ClickHouse wins.

---

## Module: Temporal — Core Concepts & Deep Dive

> Temporal là một **durable execution engine**: nó đảm bảo workflow của bạn chạy đến hoàn thành dù server crash, network fail, hay worker restart. Đây là điểm phân biệt cốt lõi với Celery/SQS.

---

### 1. Mental Model: Temporal vs Celery/SQS

```
                CELERY / SQS                    TEMPORAL
                ─────────────                   ────────
State storage:  Redis/broker (ephemeral)        Temporal Server (durable)
Crash behavior: Task lost or stuck              Resumes from last activity
Long workflows: Manual checkpointing            Built-in (event history)
Retry scope:    Per task                        Per activity (fine-grained)
State query:    Check DB manually               workflow.query() built-in
Visibility:     Celery Flower (limited)         Temporal Web UI (full history)
Max duration:   Minutes–hours (practical)       Days, months, years
Versioning:     Redeploy & hope                 workflow.patched() safe deploy

Use Temporal when: multi-step workflow, long-running, must not lose state
Use Celery when:   single short tasks, simple retry, cost-sensitive
```

---

### 2. Core Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      TEMPORAL CLUSTER                       │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  Frontend    │    │   History    │    │   Matching   │  │
│  │  Service     │    │   Service    │    │   Service    │  │
│  │ (gRPC API)   │    │(event store) │    │(task routing)│  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│           │                  │                  │          │
│           └──────────────────┴──────────────────┘          │
│                              │                              │
│                    ┌─────────────────┐                      │
│                    │   Persistence   │                      │
│                    │  (PostgreSQL /  │                      │
│                    │   Cassandra)    │                      │
│                    └─────────────────┘                      │
└─────────────────────────────────────────────────────────────┘
          ▲                                    ▲
          │ gRPC                               │ gRPC
          │                                   │
┌─────────────────┐                 ┌──────────────────────┐
│  Your FastAPI   │                 │   Temporal Workers   │
│  (submit jobs,  │                 │  (run Workflows +    │
│   query status) │                 │   Activities)        │
└─────────────────┘                 └──────────────────────┘
```

**Key components:**
- **Temporal Server**: stores all workflow state as an append-only event log
- **Workers**: your application code — poll task queues, execute Workflows & Activities
- **Task Queue**: named channel between server and workers (e.g., `"document-processing"`)
- **Workflow**: orchestration code — defines the sequence of steps (MUST be deterministic)
- **Activity**: actual work — I/O, API calls, DB writes (can be non-deterministic)

---

### 3. Durable Execution — How It Works

```
Temporal persists every state transition as an EVENT in the Workflow History.

Example: DocumentWorkflow event history
─────────────────────────────────────────────
Event 1:  WorkflowExecutionStarted
Event 2:  ActivityTaskScheduled    (ocr_activity)
Event 3:  ActivityTaskStarted
Event 4:  ActivityTaskCompleted    result="extracted text..."
Event 5:  ActivityTaskScheduled    (classify_document_activity)
Event 6:  ActivityTaskStarted
Event 7:  ActivityTaskFailed       error="rate limit"
Event 8:  TimerStarted             (retry backoff: 60s)
Event 9:  TimerFired
Event 10: ActivityTaskScheduled    (classify_document_activity retry)
Event 11: ActivityTaskCompleted    result="INVOICE"
...

When worker crashes after Event 6:
  → New worker picks up workflow
  → Temporal REPLAYS events 1-6 (reconstructs state)
  → Resumes from Event 7 (retry classify)
  → No work is lost, no duplicate OCR

This is called EVENT SOURCING — state = replay of all events.
```

---

### 4. Workflow Determinism — The Golden Rule

**Workflows phải deterministic**: cùng input → cùng sequence of events mỗi lần replay.

```python
# ❌ WRONG — Non-deterministic in workflow code
@workflow.defn
class BadWorkflow:
    @workflow.run
    async def run(self):
        # BANNED: random, time, uuid, I/O directly in workflow
        import random
        value = random.random()          # Different on each replay!

        import time
        now = time.time()                # Different on each replay!

        result = requests.get(url)       # I/O in workflow = WRONG

        await asyncio.sleep(60)          # WRONG: blocks worker thread

# ✅ CORRECT — Use Temporal's deterministic APIs
@workflow.defn
class GoodWorkflow:
    @workflow.run
    async def run(self):
        # Use workflow.now() instead of datetime.now()
        now = workflow.now()             # Deterministic (from event history)

        # Use workflow.uuid4() instead of uuid.uuid4()
        unique_id = workflow.uuid4()     # Deterministic

        # All I/O must be in Activities, not Workflows
        result = await workflow.execute_activity(
            fetch_data_activity,         # I/O lives here
            start_to_close_timeout=timedelta(minutes=5)
        )

        # Use workflow.sleep() instead of asyncio.sleep()
        await workflow.sleep(timedelta(seconds=60))  # Durable timer (survives restarts)
```

**Why determinism matters:** Temporal replays workflow history to reconstruct state. If workflow code is non-deterministic, replay produces different results → corrupted state → workflow crash.

---

### 5. Signals & Queries

```
Signals: Send data INTO a running workflow (one-way, async)
Queries: Read state FROM a running workflow (synchronous read-only)
Updates: Send data in + get response back (Temporal 1.21+)
```

```python
@workflow.defn
class BatchProcessingWorkflow:
    def __init__(self):
        self._status = "running"
        self._processed = 0
        self._paused = False

    @workflow.run
    async def run(self, batch_id: str) -> dict:
        documents = await workflow.execute_activity(
            load_documents, args=[batch_id],
            start_to_close_timeout=timedelta(minutes=2)
        )

        for doc in documents:
            # Check if paused (set via Signal)
            while self._paused:
                await workflow.sleep(timedelta(seconds=5))

            await workflow.execute_activity(
                process_document, args=[doc],
                start_to_close_timeout=timedelta(minutes=10)
            )
            self._processed += 1

        self._status = "completed"
        return {"processed": self._processed}

    # Signal: called from outside to pause/resume workflow
    @workflow.signal
    async def pause(self):
        self._paused = True

    @workflow.signal
    async def resume(self):
        self._paused = False

    @workflow.signal
    async def cancel_workflow(self):
        self._status = "cancelled"
        # Raise to stop execution
        raise asyncio.CancelledError("User requested cancellation")

    # Query: read workflow state without affecting it
    @workflow.query
    def get_status(self) -> dict:
        return {
            "status": self._status,
            "processed": self._processed,
            "paused": self._paused
        }

# Calling from FastAPI
@app.post("/batches/{batch_id}/pause")
async def pause_batch(batch_id: str):
    handle = temporal_client.get_workflow_handle(batch_id)
    await handle.signal(BatchProcessingWorkflow.pause)  # Fire signal
    return {"message": "Pause signal sent"}

@app.get("/batches/{batch_id}/status")
async def get_batch_status(batch_id: str):
    handle = temporal_client.get_workflow_handle(batch_id)
    status = await handle.query(BatchProcessingWorkflow.get_status)  # Sync read
    return status
```

---

### 6. Child Workflows — Fan-out Pattern

```python
@workflow.defn
class ParentBatchWorkflow:
    @workflow.run
    async def run(self, document_ids: list[str]) -> dict:
        """Fan-out: spawn one child workflow per document."""

        # Limit concurrency to avoid overwhelming APIs
        CONCURRENCY = 20
        semaphore = asyncio.Semaphore(CONCURRENCY)

        async def process_one(doc_id: str):
            async with semaphore:
                return await workflow.execute_child_workflow(
                    ChildDocumentWorkflow,
                    args=[doc_id],
                    # Deterministic child ID for deduplication
                    id=f"doc-{doc_id}",
                    # Child retry policy (independent of parent)
                    retry_policy=RetryPolicy(
                        maximum_attempts=3,
                        initial_interval=timedelta(seconds=30),
                        backoff_coefficient=2.0,
                        non_retryable_error_types=["ValueError"]  # Don't retry logic errors
                    )
                )

        # Fan-out all children, gather results
        results = await asyncio.gather(
            *[process_one(doc_id) for doc_id in document_ids],
            return_exceptions=True  # Don't fail parent if one child fails
        )

        completed = [r for r in results if not isinstance(r, Exception)]
        failed = [str(r) for r in results if isinstance(r, Exception)]

        return {
            "total": len(document_ids),
            "completed": len(completed),
            "failed": len(failed),
            "errors": failed
        }
```

**When to use child vs activity:**
```
Activity:       Single atomic unit of work (one API call, one DB write)
Child Workflow: Multi-step process with its own retry/state/history
                (e.g., each document has OCR → classify → extract → store)
```

---

### 7. Temporal Schedules (Cron replacement)

```python
from temporalio.client import Client, Schedule, ScheduleActionStartWorkflow
from temporalio.client import ScheduleSpec, ScheduleIntervalSpec
from datetime import timedelta

async def setup_schedules(client: Client):
    # Run daily report every day at 08:00 UTC
    await client.create_schedule(
        "daily-report-schedule",
        Schedule(
            action=ScheduleActionStartWorkflow(
                GenerateDailyReportWorkflow.run,
                id="daily-report",
                task_queue="reporting"
            ),
            spec=ScheduleSpec(
                cron_expressions=["0 8 * * *"]  # Standard cron syntax
            )
        )
    )

    # Process queue every 5 minutes
    await client.create_schedule(
        "queue-processor-schedule",
        Schedule(
            action=ScheduleActionStartWorkflow(
                ProcessQueueWorkflow.run,
                id="queue-processor",
                task_queue="processing"
            ),
            spec=ScheduleSpec(
                intervals=[ScheduleIntervalSpec(every=timedelta(minutes=5))]
            )
        )
    )

# Advantages over Celery Beat:
#   - Stored in Temporal Server (survives restarts)
#   - No duplicate runs (built-in distributed lock)
#   - Visible in Temporal Web UI
#   - Supports backfill, pause, trigger manually
```

---

### 8. Workflow Versioning — Safe Deploys

**Problem:** You have 10,000 in-flight workflows. You want to change workflow logic. Old workflows must continue with old logic; new ones use new logic.

```python
from temporalio import workflow

@workflow.defn
class DocumentWorkflow:
    @workflow.run
    async def run(self, doc_input: DocumentInput) -> DocumentResult:

        # workflow.patched() = version gate
        # Returns True for NEW workflows (after deploy)
        # Returns False for OLD workflows (replaying history before this change)
        if workflow.patched("add-validation-step"):
            # NEW: added validation step
            await workflow.execute_activity(
                validate_document_activity,
                args=[doc_input.s3_key],
                start_to_close_timeout=timedelta(minutes=2)
            )

        # Both old and new: OCR
        extracted_text = await workflow.execute_activity(
            ocr_activity,
            args=[doc_input.s3_key],
            start_to_close_timeout=timedelta(minutes=5)
        )

        # After ALL old workflows complete (weeks later):
        # Remove the if/else, keep only new path
        # Use workflow.deprecate_patch("add-validation-step")
        ...
```

---

### 9. Worker Configuration

```python
import asyncio
from temporalio.client import Client
from temporalio.worker import Worker

async def run_worker():
    client = await Client.connect(
        "temporal-server:7233",
        namespace="production"  # Isolate environments
    )

    worker = Worker(
        client,
        task_queue="document-processing",    # Must match workflow submission
        workflows=[
            BatchWorkflow,
            DocumentWorkflow,
        ],
        activities=[
            ocr_activity,
            classify_document_activity,
            extract_data_activity,
            summarize_activity,
            store_result_activity,
        ],
        # Concurrency settings
        max_concurrent_activities=20,         # Max parallel activities per worker
        max_concurrent_workflow_tasks=10,     # Max parallel workflow replay tasks
        # Graceful shutdown: finish current tasks before stopping
        graceful_shutdown_timeout=timedelta(seconds=30),
    )

    print("Worker started, polling task queue: document-processing")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(run_worker())
```

---

### 10. Interview Q&A — Temporal

**Q: "Explain Temporal's durable execution in simple terms."**
> Temporal persists every state transition as an immutable event in workflow history. If a worker crashes mid-workflow, a new worker replays the event history to reconstruct state and resumes from exactly where it left off — no data loss, no duplicate work.

**Q: "Why must Temporal Workflows be deterministic?"**
> Temporal replays workflow code against the saved event history to rebuild state. If the workflow produces different results on replay (e.g., using `random()` or `time.now()`), the replay diverges from the original history → Non-determinism error. All non-deterministic operations must live in Activities (which are not replayed, only their results are).

**Q: "Temporal vs Celery — when do you choose which?"**
> Temporal: multi-step workflows lasting minutes to days, must-not-lose-state, need fine-grained per-activity retry, need visibility into in-flight state. Celery: simple short tasks (< 5 min), high throughput (millions/day), cost-sensitive (Temporal server adds infrastructure cost), teams already familiar with it.

**Q: "How do you safely deploy new Temporal workflow logic when workflows are in-flight?"**
> Use `workflow.patched("change-name")` — a version gate that returns True for new executions and False for old replays. Both code paths coexist. Once all old workflows complete, remove the old code path.

**Q: "What happens if an Activity fails permanently after all retries?"**
> The Activity raises an `ApplicationError`. The Workflow catches it (or doesn't), and can decide: skip the document and continue, mark the batch item as failed, escalate to a parent workflow, or fail the entire workflow. Failed workflows appear in Temporal Web UI for manual investigation.

**Q: "How does Temporal handle the 'fan-out to 10,000 children' case?"**
> Use `asyncio.Semaphore` inside the parent workflow to cap concurrency (e.g., 50 concurrent child workflows). `asyncio.gather(*tasks, return_exceptions=True)` fans out without blocking — parent waits for all children while Temporal tracks each child's state independently. Each child has its own retry policy and event history.

---

### 11. Quick Reference Card — Temporal

```
TEMPORAL CORE CONCEPTS
=======================================================
Durable execution:  State = event log. Survives crashes by replay.
Workflow:           Orchestration code. MUST be deterministic.
Activity:           Actual work (I/O, API calls). Can be non-deterministic.
Worker:             Polls task queue, executes Workflows + Activities.
Task Queue:         Named channel connecting server to workers.
Signal:             Async one-way message INTO running workflow.
Query:              Sync read of workflow state (no side effects).
Child Workflow:     Sub-workflow with own history, retry, state.
Schedule:           Cron-like trigger (replaces Celery Beat, no duplicates).
workflow.patched():  Version gate for safe deploys of in-flight workflows.

DETERMINISM RULES (Workflow code only):
  ❌  random, time.now(), uuid4(), I/O, asyncio.sleep()
  ✅  workflow.now(), workflow.uuid4(), Activities, workflow.sleep()

RETRY POLICY:
  RetryPolicy(
    maximum_attempts=3,
    initial_interval=timedelta(seconds=30),
    backoff_coefficient=2.0,           # 30s, 60s, 120s
    non_retryable_error_types=["ValueError"]
  )

TEMPORAL vs CELERY:
  Temporal:  Multi-step, long-running, durable, built-in visibility
  Celery:    Short tasks, high throughput, simpler ops, cheaper
=======================================================
```

---

## Quick Reference: System Design Frameworks

```
SYSTEM DESIGN APPROACH FOR AI SYSTEMS
=======================================================

Step 1: Requirements (5 min)
  Functional: What does it DO?
  Non-functional: Scale, latency, availability, cost targets
  Out of scope: What you explicitly won't design

Step 2: High-level Architecture (5 min)
  Draw boxes and arrows
  Identify: ingestion, storage, serving, monitoring layers

Step 3: Component Deep Dive (20 min)
  Data model: what do you store, where, why
  API contracts: request/response shapes
  Key algorithms: chunking, ranking, routing

Step 4: Scale & Reliability (5 min)
  Bottlenecks: where does it break at 10x load?
  Failure modes: what if each component fails?
  Caching strategy: what to cache, TTL, invalidation

Step 5: Monitoring & Operations (5 min)
  Key metrics to track
  Alerts to set up
  How to debug in production

AI-SPECIFIC DESIGN PATTERNS:
  Ingestion: S3 -> SQS -> ECS Workers -> Vector DB
  Query:     Semantic cache -> Hybrid retrieval -> Re-rank -> LLM -> Stream
  Jobs:      POST /jobs -> SQS/Temporal -> Workers -> GET /jobs/{id}
  Budget:    Estimate before call -> Redis atomic deduct -> Async track
  Memory:    Extract -> Embed -> Store -> Retrieve by similarity + recency

COST ESTIMATION FORMULAS:
  Embedding cost: total_tokens / 1M * $0.02 (ada-002)
  LLM cost:      (input_tokens * input_rate + output_tokens * output_rate) / 1M
  Vector storage: num_vectors * dimensions * 4 bytes (float32)
  Cache savings:  (1 - cache_miss_rate) * llm_cost_per_query * daily_queries
=======================================================
```
