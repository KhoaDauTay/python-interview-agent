# RAG Systems — Senior AI Engineer Question Bank
> CV context: Khoa — Senior AI Engineer, đã build production RAG systems với Pinecone + OpenSearch, multi-source retrieval, metadata filtering, reranking, citation-backed responses. Giảm hallucination 60% bằng metadata pre-enrichment tại Atrix.

---

## OVERVIEW: 3 Thế hệ RAG

| Thế hệ | Tên | Đặc điểm | Dùng khi |
|--------|-----|-----------|----------|
| Gen 1 | Naive RAG | Index → Retrieve → Generate, đơn giản | Prototype, demo nhanh |
| Gen 2 | Advanced RAG | Query transform + Hybrid retrieve + Rerank + Compress | Production, cần accuracy cao |
| Gen 3 | Modular RAG | Pluggable components, có thể swap từng phần | Complex pipeline, A/B test |

---

## SECTION 1: RAG Architecture Evolution

### RAG-E01: Naive RAG là gì? Hạn chế?
**Câu hỏi:** Mô tả kiến trúc Naive RAG. Tại sao nó không đủ tốt cho production?
**Keywords:** chunk → embed → store → retrieve → prompt → LLM, low precision, context noise

**Trả lời mẫu:**

Naive RAG hoạt động theo 3 bước đơn giản:

```
[Documents] → [Chunk] → [Embed] → [Vector DB]
[Query] → [Embed] → [Top-K Retrieve] → [Concat to Prompt] → [LLM] → [Answer]
```

**Hạn chế của Naive RAG:**

1. **Low retrieval precision**: Top-K chunks dựa thuần vào cosine similarity — nếu query vague hoặc dùng từ khác nghĩa với document, retrieval miss.
2. **Context noise**: Chunks không liên quan lọt vào context window → LLM bị confuse, hallucinate.
3. **No query understanding**: "Tìm hiểu về chính sách hoàn tiền" và "refund policy" không match tốt nếu documents viết bằng tiếng Anh.
4. **Fixed chunk boundaries**: Chunk cắt giữa câu → mất context, câu trả lời bị truncate.
5. **No deduplication**: Multi-source retrieval có thể kéo về cùng 1 thông tin từ 3 nguồn khác nhau, lãng phí context window.

**Follow-up:** "Naive RAG tốt nhất khi nào?"
→ Dataset nhỏ (<10k docs), câu hỏi đơn giản, factual lookup, POC/prototype.

---

### RAG-M01: Advanced RAG — 3 phase là gì?
**Câu hỏi:** Giải thích Advanced RAG với 3 phase: pre-retrieval, retrieval, post-retrieval. Mỗi phase làm gì?
**Keywords:** query transformation, hybrid search, reranking, context compression

**Trả lời mẫu:**

```
PRE-RETRIEVAL          RETRIEVAL              POST-RETRIEVAL
─────────────         ──────────             ───────────────
Query Transform   →   Hybrid Search      →   Reranking
  - HyDE               - BM25 + Vector        - Cross-encoder
  - Decompose           - Metadata Filter      - Score threshold
  - Multi-query         - Multi-source         Context Compression
  - Step-back                                  - LLMLingua
                                               - Map-reduce
```

**Phase 1 — Pre-retrieval (Query Transformation):**
Mục tiêu: biến đổi query gốc để retrieval tốt hơn, vì user query thường ngắn, mơ hồ, thiếu context.

**Phase 2 — Retrieval:**
Hybrid search (BM25 + vector), kết hợp metadata filtering để thu hẹp search space, multi-source retrieval từ nhiều DB.

**Phase 3 — Post-retrieval:**
Rerank top candidates bằng cross-encoder (đắt hơn nhưng chính xác hơn), filter by score threshold, compress context để giảm noise.

---

### RAG-H01: Modular RAG vs Advanced RAG — khi nào chọn gì?
**Câu hỏi:** Modular RAG là gì? Khác gì Advanced RAG? Cho ví dụ kiến trúc modular bạn có thể build.
**Keywords:** plugin architecture, routing, adaptive retrieval, self-RAG, FLARE

**Trả lời mẫu:**

Modular RAG coi mỗi component là **độc lập, có thể swap**:

```python
class RAGPipeline:
    def __init__(
        self,
        retriever: BaseRetriever,       # Pinecone / OpenSearch / pgvector
        reranker: BaseReranker,         # Cohere / bge-reranker / None
        generator: BaseGenerator,       # GPT-4 / Claude / Llama
        query_transformer: BaseTransformer,  # HyDE / MultiQuery / None
        context_compressor: BaseCompressor,  # LLMLingua / Summary / None
    ):
        self.retriever = retriever
        self.reranker = reranker
        self.generator = generator
        self.query_transformer = query_transformer
        self.context_compressor = context_compressor

    async def run(self, query: str, filters: dict = None) -> RAGResponse:
        # 1. Transform query
        transformed_queries = await self.query_transformer.transform(query)

        # 2. Retrieve
        raw_docs = await self.retriever.retrieve(transformed_queries, filters)

        # 3. Rerank
        ranked_docs = await self.reranker.rerank(query, raw_docs)

        # 4. Compress
        context = await self.context_compressor.compress(ranked_docs)

        # 5. Generate
        return await self.generator.generate(query, context)
```

**Điểm mạnh của Modular RAG:**
- A/B test dễ: swap retriever từ Pinecone → OpenSearch → chạy eval → so sánh
- Routing: query về legal → dùng BM25 nặng hơn; query về semantic → dùng vector nặng hơn
- Adaptive: tự quyết định có cần retrieve không (self-RAG)

**Chọn Advanced RAG khi:** pipeline cố định, không cần swap components thường xuyên.
**Chọn Modular RAG khi:** nhiều data sources, cần tune từng bước riêng, nhiều use case khác nhau trong cùng 1 hệ thống.

---

## SECTION 2: Indexing Pipeline

### RAG-E02: Chunking strategies — trade-offs
**Câu hỏi:** Liệt kê các chunking strategies. Khi nào dùng strategy nào? Chunk size 256 vs 512 vs 1024 token — trade-offs gì?
**Keywords:** fixed-size, sentence-based, semantic chunking, hierarchical, overlap

**Trả lời mẫu:**

**1. Fixed-size chunking với overlap:**

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=64,        # 12.5% overlap — tránh mất context ở boundary
    separators=["\n\n", "\n", ".", " ", ""],  # ưu tiên split theo đoạn văn
    length_function=len,     # hoặc dùng tiktoken để đếm tokens
)

chunks = splitter.split_text(document)
```

Pros: đơn giản, predictable. Cons: cắt giữa câu, không hiểu structure của document.

**2. Sentence-based chunking:**

```python
import spacy

nlp = spacy.load("en_core_web_sm")

def sentence_chunker(text: str, sentences_per_chunk: int = 5, overlap: int = 1) -> list[str]:
    doc = nlp(text)
    sentences = [sent.text.strip() for sent in doc.sents]
    chunks = []
    for i in range(0, len(sentences), sentences_per_chunk - overlap):
        chunk = " ".join(sentences[i:i + sentences_per_chunk])
        if chunk:
            chunks.append(chunk)
    return chunks
```

Pros: không cắt giữa câu, meaningful units. Cons: chunk size variable, khó predict token count.

**3. Semantic chunking (quan trọng):**

Ý tưởng: embed từng câu → tính cosine similarity giữa câu liền kề → split khi similarity giảm mạnh (topic shift).

```python
import numpy as np
from openai import OpenAI

client = OpenAI()

def semantic_chunker(sentences: list[str], threshold: float = 0.3) -> list[str]:
    # Embed tất cả sentences
    embeddings = client.embeddings.create(
        model="text-embedding-3-small",
        input=sentences,
    ).data
    vecs = np.array([e.embedding for e in embeddings])

    # Tính similarity giữa câu liền kề
    similarities = []
    for i in range(len(vecs) - 1):
        sim = np.dot(vecs[i], vecs[i+1]) / (np.linalg.norm(vecs[i]) * np.linalg.norm(vecs[i+1]))
        similarities.append(sim)

    # Split tại chỗ similarity thấp hơn ngưỡng
    split_points = [i+1 for i, s in enumerate(similarities) if s < threshold]
    split_points = [0] + split_points + [len(sentences)]

    chunks = []
    for start, end in zip(split_points[:-1], split_points[1:]):
        chunks.append(" ".join(sentences[start:end]))
    return chunks
```

**4. Hierarchical / Parent-child chunking:**

```python
from langchain.retrievers import ParentDocumentRetriever
from langchain.storage import InMemoryStore
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Parent: chunk lớn (1024 tokens) — dùng cho generation context
parent_splitter = RecursiveCharacterTextSplitter(chunk_size=1024)

# Child: chunk nhỏ (128 tokens) — dùng cho retrieval (accurate embedding)
child_splitter = RecursiveCharacterTextSplitter(chunk_size=128)

store = InMemoryStore()

retriever = ParentDocumentRetriever(
    vectorstore=vectorstore,
    docstore=store,
    child_splitter=child_splitter,
    parent_splitter=parent_splitter,
)
# Retrieval: embed child chunks → tìm child match → trả về parent context
retriever.add_documents(docs)
results = retriever.get_relevant_documents("query")
```

**Trade-offs chunk size:**

| Size | Precision | Context | Dùng khi |
|------|-----------|---------|----------|
| 256 tokens | Cao (focused) | Ít | Factual QA, specific lookup |
| 512 tokens | Trung bình | Vừa | General QA — sweet spot thường gặp |
| 1024 tokens | Thấp hơn | Nhiều | Summarization, cần broader context |

---

### RAG-M02: Metadata enrichment — kỹ thuật giảm hallucination 60%
**Câu hỏi:** Explain kỹ thuật metadata pre-enrichment mà bạn đã dùng tại Atrix. Tại sao nó giảm hallucination?
**Keywords:** metadata schema, pre-filter, document_id, source, date, section, page_number

**Trả lời mẫu (từ CV của Khoa):**

**Vấn đề:** Với hệ thống multi-source (internal docs + external APIs + user-uploaded PDFs), LLM trả lời câu hỏi bằng cách mix context từ nhiều nguồn khác nhau — một số nguồn outdated, một số không authoritative → hallucination tăng cao.

**Giải pháp: Metadata Pre-enrichment**

Thay vì chỉ index raw text, enrichment thêm structured metadata VÀO MỖI CHUNK trước khi embed:

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class ChunkMetadata:
    # Identity
    document_id: str           # unique ID của document gốc
    chunk_id: str              # unique ID của chunk
    
    # Source tracking
    source: str                # "internal_wiki" | "legal_docs" | "user_upload"
    source_url: Optional[str]  # URL gốc nếu có
    
    # Temporal
    created_at: datetime       # ngày tạo document
    updated_at: datetime       # ngày cập nhật gần nhất
    ingested_at: datetime      # ngày ingest vào vector DB
    
    # Structure
    page_number: Optional[int] # page trong PDF
    section: Optional[str]     # H1/H2 heading chứa chunk này
    document_title: str        # tiêu đề document
    
    # Quality signals
    authority_score: float     # 0-1: internal policy = 1.0, external = 0.7
    language: str              # "vi" | "en"
    
    # Business-specific
    department: Optional[str]  # "legal" | "engineering" | "finance"
    tags: list[str]            # ["refund", "policy", "v2023"]


def enrich_and_index_chunk(
    text: str,
    metadata: ChunkMetadata,
    pinecone_index,
    embedding_client,
) -> None:
    # 1. Prepend metadata summary vào text trước khi embed
    enriched_text = f"""
    [Source: {metadata.source}]
    [Section: {metadata.section}]
    [Date: {metadata.updated_at.strftime('%Y-%m-%d')}]
    [Authority: {metadata.authority_score}]
    
    {text}
    """.strip()

    # 2. Embed enriched text
    embedding = embedding_client.embeddings.create(
        model="text-embedding-3-small",
        input=enriched_text,
    ).data[0].embedding

    # 3. Store với full metadata
    pinecone_index.upsert(vectors=[{
        "id": metadata.chunk_id,
        "values": embedding,
        "metadata": {
            "text": text,                    # raw text cho display
            "source": metadata.source,
            "document_id": metadata.document_id,
            "updated_at": metadata.updated_at.timestamp(),
            "authority_score": metadata.authority_score,
            "section": metadata.section,
            "page_number": metadata.page_number,
            "department": metadata.department,
            "tags": metadata.tags,
        }
    }])
```

**Tại sao giảm hallucination?**

1. **Pre-filter theo date**: chỉ retrieve docs được cập nhật trong 12 tháng gần nhất → loại outdated info.
2. **Pre-filter theo authority**: `authority_score >= 0.8` cho câu hỏi về policy → chỉ dùng official sources.
3. **Pre-filter theo department**: câu hỏi về "refund" → chỉ retrieve từ `department=legal`.
4. **Metadata trong embedding**: model hiểu context của chunk tốt hơn (biết chunk này là từ legal docs, từ section "Refund Policy") → embedding precise hơn → retrieval accurate hơn.
5. **Citation**: LLM được cung cấp source metadata → generate citations cụ thể → user có thể verify → buộc LLM trung thực hơn.

```python
# Query với metadata pre-filter
def query_with_metadata_filter(
    query: str,
    pinecone_index,
    department: str = None,
    min_authority: float = 0.5,
    max_age_days: int = 365,
) -> list[dict]:
    import time

    # Build filter
    filter_dict = {
        "authority_score": {"$gte": min_authority},
        "updated_at": {"$gte": time.time() - max_age_days * 86400},
    }
    if department:
        filter_dict["department"] = {"$eq": department}

    # Embed query
    query_embedding = get_embedding(query)

    # Retrieve với filter
    results = pinecone_index.query(
        vector=query_embedding,
        top_k=20,
        filter=filter_dict,
        include_metadata=True,
    )
    return results.matches
```

---

### RAG-M03: Upsert strategy — full re-index vs incremental
**Câu hỏi:** Khi document được update, bạn re-index như thế nào? Trade-offs giữa full re-index, incremental update, và soft delete?
**Keywords:** document versioning, chunk_id generation, soft delete, stale index

**Trả lời mẫu:**

```python
import hashlib
from enum import Enum

class IndexStrategy(Enum):
    FULL_REINDEX = "full_reindex"
    INCREMENTAL = "incremental"
    SOFT_DELETE = "soft_delete"


def generate_chunk_id(document_id: str, chunk_index: int, text: str) -> str:
    """
    Deterministic chunk ID — cùng document + cùng content → cùng ID.
    Cho phép detect thay đổi mà không cần track external state.
    """
    content_hash = hashlib.sha256(text.encode()).hexdigest()[:8]
    return f"{document_id}_chunk{chunk_index:04d}_{content_hash}"


async def incremental_upsert(
    document_id: str,
    new_chunks: list[tuple[str, dict]],  # (text, metadata)
    pinecone_index,
    embedding_client,
) -> dict:
    """
    Incremental update strategy:
    1. Fetch existing chunks cho document_id
    2. So sánh content hash
    3. Chỉ re-embed + upsert chunks đã thay đổi
    4. Delete chunks không còn tồn tại
    """
    # 1. Fetch existing chunk IDs cho document
    existing = pinecone_index.query(
        vector=[0.0] * 1536,  # dummy vector
        filter={"document_id": {"$eq": document_id}},
        top_k=10000,
        include_metadata=False,
    )
    existing_ids = {m.id for m in existing.matches}

    # 2. Generate new chunk IDs
    new_ids = set()
    to_upsert = []

    for i, (text, metadata) in enumerate(new_chunks):
        chunk_id = generate_chunk_id(document_id, i, text)
        new_ids.add(chunk_id)

        if chunk_id not in existing_ids:
            # Chunk mới hoặc đã thay đổi — re-embed
            embedding = await get_embedding_async(text, embedding_client)
            to_upsert.append({
                "id": chunk_id,
                "values": embedding,
                "metadata": {**metadata, "text": text, "document_id": document_id},
            })

    # 3. Delete stale chunks (không còn trong document mới)
    stale_ids = existing_ids - new_ids
    if stale_ids:
        pinecone_index.delete(ids=list(stale_ids))

    # 4. Upsert changed/new chunks
    if to_upsert:
        # Batch upsert — Pinecone recommend batch of 100
        for i in range(0, len(to_upsert), 100):
            pinecone_index.upsert(vectors=to_upsert[i:i+100])

    return {
        "upserted": len(to_upsert),
        "deleted": len(stale_ids),
        "unchanged": len(new_ids & existing_ids),
    }
```

**So sánh strategies:**

| Strategy | Khi dùng | Pros | Cons |
|----------|----------|------|------|
| Full re-index | Schema thay đổi, embedding model thay đổi | Đơn giản, guaranteed fresh | Tốn cost + time, downtime nếu không có shadow index |
| Incremental | Documents update thường xuyên | Nhanh, tiết kiệm | Cần deterministic chunk IDs |
| Soft delete | Cần audit trail, rollback | Có thể recover | Index phình ra, phải filter is_deleted |

---

## SECTION 3: Embedding Models & Vector DBs

### RAG-E03: Embedding model comparison
**Câu hỏi:** So sánh các embedding models phổ biến. Khi nào dùng model nào?
**Keywords:** text-embedding-3-small, bge-m3, e5-mistral, dimensions, multilingual

**Trả lời mẫu:**

| Model | Dims | Đặc điểm | Dùng khi |
|-------|------|-----------|----------|
| `text-embedding-3-small` | 1536 | Rẻ, nhanh, API-based | Production với budget, tiếng Anh chủ yếu |
| `text-embedding-3-large` | 3072 | Accuracy cao hơn, đắt hơn 5x | High-stakes retrieval, cần precision tối đa |
| `bge-m3` | 1024 | Multilingual (100+ ngôn ngữ), OSS | Vietnamese + English corpus, self-hosted |
| `e5-mistral-7b` | 4096 | State-of-art quality, 7B params | Research, offline, có GPU |

```python
# Matryoshka Embeddings — text-embedding-3 hỗ trợ truncate dimensions
import openai

client = openai.OpenAI()

# Full 3072 dims — expensive storage, best quality
large_embedding = client.embeddings.create(
    model="text-embedding-3-large",
    input="What is the refund policy?",
).data[0].embedding  # 3072 floats

# Truncate to 512 dims — 6x storage savings, ~5% quality drop
small_embedding = client.embeddings.create(
    model="text-embedding-3-large",
    input="What is the refund policy?",
    dimensions=512,  # Matryoshka: truncate to any size
).data[0].embedding  # 512 floats
```

---

### RAG-M04: HNSW vs IVF — khi nào dùng gì?
**Câu hỏi:** Giải thích HNSW và IVF indexing. Parameters quan trọng là gì? Khi nào chọn cái nào?
**Keywords:** ef_construction, M, nlist, nprobe, recall vs latency trade-off

**Trả lời mẫu:**

**HNSW (Hierarchical Navigable Small World):**

```
Graph-based. Mỗi vector là 1 node, kết nối với M nearest neighbors.
Tìm kiếm bằng cách navigate graph từ entry point.

Parameters:
- M: số neighbors mỗi node (default 16, tăng → accuracy tốt hơn, RAM nhiều hơn)
- ef_construction: beam size khi build (default 200, tăng → build chậm hơn, quality tốt hơn)
- ef_search: beam size khi query (tăng real-time để tradeoff recall vs latency)

Pros: Recall rất cao (>99%), latency thấp, không cần train
Cons: RAM nhiều (cần store graph), build time lâu với dataset lớn
```

**IVF (Inverted File Index):**

```
Clustering-based. Chia vectors thành nlist clusters (Voronoi cells).
Query: tìm nprobe clusters gần nhất → search trong đó.

Parameters:
- nlist: số clusters (thường sqrt(N) đến 4*sqrt(N))
- nprobe: số clusters search khi query (tăng → recall tốt hơn, chậm hơn)

Pros: RAM thấp hơn HNSW, tốt với dataset cực lớn (>10M vectors)
Cons: Cần training step, nprobe thấp → miss recalls
```

```python
# pgvector: chọn index type
import psycopg2

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# IVFFlat — tốt cho dataset lớn, RAM hạn chế
cur.execute("""
    CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);  -- nlist = 100, thường = sqrt(num_rows)
""")

# HNSW — tốt cho low-latency production
cur.execute("""
    CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
""")

# Tune ef_search per-query (HNSW only)
cur.execute("SET hnsw.ef_search = 100;")  # tăng recall, chấp nhận latency cao hơn
```

**Chọn HNSW khi:** latency < 10ms là ưu tiên, dataset < 10M vectors, RAM đủ.
**Chọn IVF khi:** dataset > 50M vectors, cần tiết kiệm memory, latency 50-100ms là acceptable.

---

### RAG-M05: Pinecone production patterns
**Câu hỏi:** Trong Pinecone, namespace và separate index khác gì nhau? Hybrid search hoạt động thế nào?
**Keywords:** namespace, multi-tenant, sparse-dense hybrid, metadata filtering, upsert batching

**Trả lời mẫu:**

```python
from pinecone import Pinecone, ServerlessSpec
import asyncio
from openai import AsyncOpenAI

pc = Pinecone(api_key="...")
oai = AsyncOpenAI()

# Tạo hybrid index (dense + sparse)
pc.create_index(
    name="production-rag",
    dimension=1536,
    metric="dotproduct",      # phải dùng dotproduct cho hybrid
    spec=ServerlessSpec(cloud="aws", region="us-east-1"),
)
index = pc.Index("production-rag")


# Multi-tenant với namespace
async def upsert_tenant_docs(
    tenant_id: str,
    documents: list[dict],
    batch_size: int = 100,
) -> None:
    """Mỗi tenant có namespace riêng — hoàn toàn isolated."""
    vectors = []

    for doc in documents:
        # Get dense embedding
        resp = await oai.embeddings.create(
            model="text-embedding-3-small",
            input=doc["text"],
        )
        dense = resp.data[0].embedding

        # Generate sparse embedding (BM25-style) cho hybrid
        sparse = compute_bm25_sparse(doc["text"])  # {indices: [...], values: [...]}

        vectors.append({
            "id": doc["id"],
            "values": dense,
            "sparse_values": sparse,
            "metadata": doc["metadata"],
        })

    # Batch upsert vào tenant namespace
    for i in range(0, len(vectors), batch_size):
        index.upsert(
            vectors=vectors[i:i+batch_size],
            namespace=f"tenant_{tenant_id}",   # isolation per tenant
        )


async def hybrid_search(
    query: str,
    tenant_id: str,
    top_k: int = 20,
    alpha: float = 0.75,           # 0 = pure BM25, 1 = pure vector
    metadata_filter: dict = None,
) -> list:
    """
    Hybrid search: kết hợp sparse (BM25) + dense (vector).
    alpha controls weighting.
    """
    # Dense query embedding
    resp = await oai.embeddings.create(
        model="text-embedding-3-small",
        input=query,
    )
    dense_vec = resp.data[0].embedding

    # Sparse query (BM25 tokenized)
    sparse_vec = compute_bm25_sparse(query)

    # Scale vectors by alpha
    scaled_dense = [v * alpha for v in dense_vec]
    scaled_sparse = {
        "indices": sparse_vec["indices"],
        "values": [v * (1 - alpha) for v in sparse_vec["values"]],
    }

    results = index.query(
        vector=scaled_dense,
        sparse_vector=scaled_sparse,
        top_k=top_k,
        namespace=f"tenant_{tenant_id}",
        filter=metadata_filter,
        include_metadata=True,
    )
    return results.matches
```

---

### RAG-M06: OpenSearch kNN + BM25 hybrid
**Câu hỏi:** Setup OpenSearch cho RAG như thế nào? Viết query hybrid BM25 + kNN.
**Keywords:** knn_vector, script_score, k-NN plugin, function_score

**Trả lời mẫu:**

```python
from opensearchpy import OpenSearch, RequestsHttpConnection

client = OpenSearch(
    hosts=[{"host": "localhost", "port": 9200}],
    http_auth=("admin", "password"),
    use_ssl=True,
    connection_class=RequestsHttpConnection,
)

# Index mapping với kNN vector field
index_mapping = {
    "settings": {
        "index": {
            "knn": True,
            "knn.algo_param.ef_search": 100,   # tune recall
        }
    },
    "mappings": {
        "properties": {
            "text": {"type": "text", "analyzer": "english"},
            "embedding": {
                "type": "knn_vector",
                "dimension": 1536,
                "method": {
                    "name": "hnsw",
                    "space_type": "cosinesimil",
                    "engine": "nmslib",
                    "parameters": {
                        "ef_construction": 128,
                        "m": 24,
                    },
                },
            },
            "source": {"type": "keyword"},
            "department": {"type": "keyword"},
            "updated_at": {"type": "date"},
        }
    },
}

client.indices.create(index="rag_docs", body=index_mapping)


def hybrid_search_opensearch(
    query: str,
    query_embedding: list[float],
    top_k: int = 20,
    bm25_weight: float = 0.3,
    knn_weight: float = 0.7,
    department: str = None,
) -> list[dict]:
    """
    Hybrid: BM25 text scoring + kNN vector similarity.
    Dùng function_score để combine.
    """
    filter_clause = []
    if department:
        filter_clause.append({"term": {"department": department}})

    query_body = {
        "size": top_k,
        "query": {
            "function_score": {
                "query": {
                    "bool": {
                        "should": [
                            # BM25 text match
                            {
                                "match": {
                                    "text": {
                                        "query": query,
                                        "boost": bm25_weight,
                                    }
                                }
                            }
                        ],
                        "filter": filter_clause,
                    }
                },
                "functions": [
                    # kNN vector similarity as function score
                    {
                        "script_score": {
                            "script": {
                                "source": """
                                    double score = cosineSimilarity(params.query_vec, 'embedding') + 1.0;
                                    return score * params.knn_weight;
                                """,
                                "params": {
                                    "query_vec": query_embedding,
                                    "knn_weight": knn_weight,
                                },
                            }
                        }
                    }
                ],
                "score_mode": "sum",
                "boost_mode": "sum",
            }
        },
        "_source": ["text", "source", "document_id", "page_number", "section"],
    }

    response = client.search(index="rag_docs", body=query_body)
    return [
        {
            "score": hit["_score"],
            "text": hit["_source"]["text"],
            "metadata": {k: v for k, v in hit["_source"].items() if k != "text"},
        }
        for hit in response["hits"]["hits"]
    ]
```

---

### RAG-E04: Cosine vs Dot Product vs Euclidean
**Câu hỏi:** Khi nào dùng cosine similarity, dot product, hay Euclidean distance cho vector search?

**Trả lời mẫu:**

| Metric | Formula | Dùng khi | Lưu ý |
|--------|---------|----------|-------|
| Cosine | `dot(a,b) / (‖a‖·‖b‖)` | Text similarity, không quan tâm magnitude | Default cho RAG |
| Dot product | `dot(a,b)` | Vectors đã normalize (L2=1) | Nhanh hơn cosine; Pinecone hybrid bắt buộc |
| Euclidean | `‖a-b‖` | Image, audio, continuous space | Ít dùng trong NLP |

**Rule of thumb:** nếu normalize vectors trước khi index → Dot product = Cosine (cùng kết quả, dot nhanh hơn). Luôn normalize khi dùng OpenAI embeddings.

```python
import numpy as np

def normalize(v: list[float]) -> list[float]:
    """L2 normalize — sau đó dot product == cosine similarity."""
    arr = np.array(v)
    return (arr / np.linalg.norm(arr)).tolist()

# Normalized vectors: dot product == cosine
a = normalize(embedding_a)
b = normalize(embedding_b)
similarity = np.dot(a, b)  # range [-1, 1]
```

---

## SECTION 4: Advanced Retrieval

### RAG-H02: Hybrid Search — tại sao tốt hơn từng loại?
**Câu hỏi:** Giải thích tại sao hybrid search (BM25 + vector) tốt hơn chỉ dùng 1 loại. Khi nào BM25 thắng? Khi nào vector thắng?

**Trả lời mẫu:**

**BM25 thắng khi:**
- Query chứa từ kỹ thuật cụ thể: "RFC 7519", "ERR_SSL_HANDSHAKE", "Invoice #INV-2024-001"
- Tên riêng, product codes, IDs
- User biết chính xác từ khóa họ cần tìm

**Vector search thắng khi:**
- Paraphrase: "hoàn tiền" ≈ "refund" ≈ "chargeback" ≈ "trả lại tiền"
- Semantic similarity: "cách hủy đơn hàng" → document nói về "cancellation procedure"
- Cross-lingual: query tiếng Việt → document tiếng Anh

**Hybrid thắng cả hai:** kết hợp recall của semantic với precision của keyword.

```python
def reciprocal_rank_fusion(
    bm25_results: list[dict],
    vector_results: list[dict],
    k: int = 60,
) -> list[dict]:
    """
    RRF — Reciprocal Rank Fusion.
    Score = Σ 1 / (k + rank_i) cho mỗi result list.
    k=60 là giá trị empirically tốt nhất.
    """
    scores: dict[str, float] = {}
    doc_map: dict[str, dict] = {}

    for rank, doc in enumerate(bm25_results, start=1):
        doc_id = doc["id"]
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank)
        doc_map[doc_id] = doc

    for rank, doc in enumerate(vector_results, start=1):
        doc_id = doc["id"]
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank)
        doc_map[doc_id] = doc

    # Sort by RRF score
    sorted_ids = sorted(scores, key=lambda x: scores[x], reverse=True)
    return [
        {**doc_map[doc_id], "rrf_score": scores[doc_id]}
        for doc_id in sorted_ids
    ]
```

---

### RAG-H03: Reranking — Cross-encoder vs Bi-encoder
**Câu hỏi:** Phân biệt cross-encoder và bi-encoder. Tại sao reranker là cross-encoder? Khi nào dùng Cohere Rerank vs bge-reranker?
**Keywords:** bi-encoder (ANN), cross-encoder (BERT), latency vs accuracy, two-stage retrieval

**Trả lời mẫu:**

```
Bi-encoder (retrieval stage):
  Query ──→ [Encoder] ──→ q_vec
  Doc   ──→ [Encoder] ──→ d_vec
  Score = cosine(q_vec, d_vec)
  
  Pros: Pre-compute doc embeddings → ANN search O(log n)
  Cons: Query và doc encoded INDEPENDENTLY → miss fine-grained interaction

Cross-encoder (reranking stage):
  [Query + Doc] ──→ [BERT] ──→ relevance_score (0-1)
  
  Pros: Full attention over query-doc pair → hiểu interaction tốt hơn nhiều
  Cons: KHÔNG pre-compute được → O(n) per query, chỉ dùng cho top-K nhỏ
```

**Two-stage retrieval pattern:**

```python
import cohere
from sentence_transformers import CrossEncoder
import asyncio

co = cohere.Client(api_key="...")
bge_reranker = CrossEncoder("BAAI/bge-reranker-large")


async def two_stage_retrieval(
    query: str,
    vector_index,
    top_k_retrieve: int = 50,    # Stage 1: retrieve nhiều
    top_k_rerank: int = 5,       # Stage 2: rerank, chỉ giữ ít nhất
    min_score: float = 0.3,
    use_cohere: bool = True,
) -> list[dict]:
    # Stage 1: Fast bi-encoder retrieval
    query_embedding = await get_embedding_async(query)
    candidates = vector_index.query(
        vector=query_embedding,
        top_k=top_k_retrieve,
        include_metadata=True,
    ).matches

    if not candidates:
        return []

    docs = [m.metadata["text"] for m in candidates]

    if use_cohere:
        # Stage 2A: Cohere Rerank (API-based, no GPU needed)
        rerank_response = co.rerank(
            model="rerank-english-v3.0",
            query=query,
            documents=docs,
            top_n=top_k_rerank,
        )
        reranked = [
            {
                "text": docs[r.index],
                "metadata": candidates[r.index].metadata,
                "rerank_score": r.relevance_score,
            }
            for r in rerank_response.results
            if r.relevance_score >= min_score
        ]
    else:
        # Stage 2B: BGE Reranker (OSS, need GPU/CPU inference)
        pairs = [[query, doc] for doc in docs]
        scores = bge_reranker.predict(pairs)

        reranked = sorted(
            [
                {
                    "text": docs[i],
                    "metadata": candidates[i].metadata,
                    "rerank_score": float(scores[i]),
                }
                for i in range(len(docs))
                if scores[i] >= min_score
            ],
            key=lambda x: x["rerank_score"],
            reverse=True,
        )[:top_k_rerank]

    return reranked
```

**Chọn Cohere khi:** không có GPU, cần managed service, production với SLA.
**Chọn bge-reranker khi:** self-hosted, cost-sensitive, multilingual (bge-reranker-v2-m3).

---

### RAG-H04: Query Transformation techniques
**Câu hỏi:** Giải thích HyDE, Query Decomposition, Multi-query, Step-back Prompting. Khi nào dùng kỹ thuật nào?
**Keywords:** hypothetical document embedding, sub-queries, abstraction, query expansion

**Trả lời mẫu:**

**1. HyDE (Hypothetical Document Embeddings):**

```python
async def hyde_retrieve(query: str, index, llm_client, top_k: int = 10) -> list:
    """
    Ý tưởng: user query ngắn, terse → embed kém.
    Thay vào đó: generate hypothetical answer → embed answer (dài, rich) → retrieve.
    """
    # Step 1: Generate hypothetical answer (fake, nhưng semantically similar)
    hyp_response = await llm_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "Write a detailed answer for the following question. "
                           "It may not be factually correct, but should be plausible.",
            },
            {"role": "user", "content": query},
        ],
        max_tokens=300,
    )
    hypothetical_answer = hyp_response.choices[0].message.content

    # Step 2: Embed hypothetical answer (giống document hơn là question)
    hyp_embedding = await get_embedding_async(hypothetical_answer)

    # Step 3: Retrieve using hypothetical embedding
    results = index.query(vector=hyp_embedding, top_k=top_k, include_metadata=True)
    return results.matches
```

**Khi nào dùng HyDE:** câu hỏi user ngắn ("refund policy"), query về technical concepts mà documents có nhiều chi tiết.

**2. Query Decomposition:**

```python
async def decompose_and_retrieve(
    complex_query: str,
    index,
    llm_client,
) -> list:
    """
    "So sánh chính sách hoàn tiền của sản phẩm A và B"
    → ["Chính sách hoàn tiền của sản phẩm A là gì?",
       "Chính sách hoàn tiền của sản phẩm B là gì?"]
    """
    decompose_prompt = f"""Break down this complex question into 2-4 simpler sub-questions.
Return ONLY a JSON array of strings. No explanation.

Question: {complex_query}

Output: ["sub-question 1", "sub-question 2", ...]"""

    resp = await llm_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": decompose_prompt}],
        response_format={"type": "json_object"},
    )
    import json
    sub_queries = json.loads(resp.choices[0].message.content)

    # Retrieve for each sub-query, then deduplicate
    all_docs = {}
    for sub_q in sub_queries:
        emb = await get_embedding_async(sub_q)
        results = index.query(vector=emb, top_k=5, include_metadata=True)
        for match in results.matches:
            if match.id not in all_docs or match.score > all_docs[match.id]["score"]:
                all_docs[match.id] = {"score": match.score, "metadata": match.metadata}

    # Sort by score
    return sorted(all_docs.values(), key=lambda x: x["score"], reverse=True)
```

**3. Multi-query (LangChain built-in):**

```python
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain_openai import ChatOpenAI
from langchain_pinecone import PineconeVectorStore

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
vectorstore = PineconeVectorStore(index=pinecone_index, embedding=embeddings)

multi_query_retriever = MultiQueryRetriever.from_llm(
    retriever=vectorstore.as_retriever(search_kwargs={"k": 10}),
    llm=llm,
    # LLM sẽ generate 3 query variants → retrieve cho mỗi → union + deduplicate
)

docs = multi_query_retriever.invoke("chính sách hoàn tiền là gì")
```

**4. Step-back Prompting:**

```python
# "Ai là CEO của Apple vào năm 2024?" → abstract → "Lịch sử lãnh đạo Apple?"
STEPBACK_PROMPT = """You are an AI that generates a more abstract, general question
from a specific question. This helps retrieve broader context first.

Specific: {query}
Abstract (step-back):"""

async def stepback_retrieve(query: str, index, llm_client, top_k: int = 10):
    resp = await llm_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": STEPBACK_PROMPT.format(query=query),
        }],
    )
    abstract_query = resp.choices[0].message.content.strip()

    # Retrieve với cả abstract và original query
    emb_abstract = await get_embedding_async(abstract_query)
    emb_original = await get_embedding_async(query)

    results_abstract = index.query(vector=emb_abstract, top_k=top_k//2, include_metadata=True)
    results_original = index.query(vector=emb_original, top_k=top_k//2, include_metadata=True)

    # Combine và deduplicate
    seen = set()
    combined = []
    for match in results_abstract.matches + results_original.matches:
        if match.id not in seen:
            seen.add(match.id)
            combined.append(match)
    return combined
```

---

### RAG-H05: Multi-hop retrieval
**Câu hỏi:** Multi-hop retrieval là gì? Khi nào cần? Implement như thế nào?
**Keywords:** chain-of-thought retrieval, iterative retrieval, IRCoT, FLARE

**Trả lời mẫu:**

Multi-hop cần khi câu trả lời yêu cầu chain nhiều documents:
"Nhân viên quản lý dự án X báo cáo cho ai?" → phải biết "ai quản lý X" trước → rồi mới biết "họ báo cáo cho ai".

```python
async def multi_hop_retrieve(
    query: str,
    index,
    llm_client,
    max_hops: int = 3,
) -> tuple[list[dict], list[str]]:
    """
    IRCoT (Interleaved Retrieval + CoT) pattern:
    1. Retrieve → 2. Reason → 3. Generate follow-up → 4. Retrieve lại → repeat
    """
    all_docs = []
    reasoning_chain = []
    current_query = query

    for hop in range(max_hops):
        # Retrieve
        embedding = await get_embedding_async(current_query)
        results = index.query(vector=embedding, top_k=3, include_metadata=True)
        hop_docs = [m.metadata["text"] for m in results.matches]
        all_docs.extend(results.matches)

        # Reason: có đủ thông tin để trả lời chưa?
        context = "\n\n".join(hop_docs)
        reasoning_prompt = f"""Given the context below, determine:
1. Can you answer "{query}" with this information? (yes/no)
2. If no, what specific information are you still missing?

Context: {context}
Answer JSON: {{"can_answer": bool, "missing_info": "str or null", "follow_up_query": "str or null"}}"""

        resp = await llm_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": reasoning_prompt}],
            response_format={"type": "json_object"},
        )
        import json
        reasoning = json.loads(resp.choices[0].message.content)
        reasoning_chain.append(reasoning)

        if reasoning["can_answer"]:
            break

        # Generate follow-up query for next hop
        current_query = reasoning["follow_up_query"]

    return all_docs, reasoning_chain
```

---

## SECTION 5: Context Assembly & Generation

### RAG-M07: Context assembly và Lost-in-the-middle
**Câu hỏi:** Sau khi retrieve và rerank, bạn assemble context như thế nào? Lost-in-the-middle problem là gì?
**Keywords:** context window, positional bias, context compression, citation format

**Trả lời mẫu:**

**Lost-in-the-middle problem:** LLMs (đặc biệt GPT-3.5, older models) chú ý tốt nhất đến thông tin ở **đầu** và **cuối** context, bỏ qua thông tin ở **giữa**. Nghiên cứu Stanford 2023 cho thấy accuracy drop 20-30% khi relevant info ở giữa context.

```python
from dataclasses import dataclass
import tiktoken

@dataclass
class RAGContext:
    text: str
    score: float
    source: str
    document_id: str
    page_number: int | None
    section: str | None


def assemble_context(
    ranked_docs: list[RAGContext],
    max_tokens: int = 3000,
    model: str = "gpt-4o",
) -> tuple[str, list[str]]:
    """
    Assemble context với Lost-in-the-middle mitigation:
    - Đặt docs quan trọng nhất ở ĐẦU và CUỐI
    - Docs ít quan trọng ở giữa
    """
    enc = tiktoken.encoding_for_model(model)
    citation_map = []
    selected_docs = []
    total_tokens = 0

    # First pass: select docs that fit in token budget
    for doc in ranked_docs:
        doc_tokens = len(enc.encode(doc.text))
        if total_tokens + doc_tokens <= max_tokens:
            selected_docs.append(doc)
            total_tokens += doc_tokens

    if not selected_docs:
        return "", []

    # Mitigate lost-in-the-middle:
    # Interleave: best doc first, worst doc last, rest in middle
    n = len(selected_docs)
    if n <= 2:
        ordered = selected_docs
    else:
        best = selected_docs[0]
        second_best = selected_docs[1]
        rest = selected_docs[2:]
        # Place best at start, second_best at end, rest in middle
        ordered = [best] + rest + [second_best]

    # Format with citations
    context_parts = []
    for i, doc in enumerate(ordered, start=1):
        citation_id = f"[{i}]"
        citation_map.append(
            f"{citation_id} {doc.source} — {doc.section or 'General'}"
            + (f", p.{doc.page_number}" if doc.page_number else "")
        )
        context_parts.append(
            f"{citation_id} [Source: {doc.source} | Section: {doc.section}]\n{doc.text}"
        )

    context = "\n\n---\n\n".join(context_parts)
    return context, citation_map


RAG_SYSTEM_PROMPT = """You are a helpful assistant. Answer questions based ONLY on the provided context.
If the context does not contain enough information, say "I don't have enough information to answer this."

IMPORTANT:
- Cite your sources using [1], [2], etc. as they appear in the context
- Do NOT make up information not present in the context
- If information conflicts between sources, mention both perspectives

Context:
{context}

Citations available:
{citations}"""

def build_rag_prompt(query: str, context: str, citations: list[str]) -> list[dict]:
    return [
        {
            "role": "system",
            "content": RAG_SYSTEM_PROMPT.format(
                context=context,
                citations="\n".join(citations),
            ),
        },
        {"role": "user", "content": query},
    ]
```

---

## SECTION 6: RAG Evaluation

### RAG-H06: RAGAS metrics — giải thích từng metric
**Câu hỏi:** Giải thích 4 RAGAS metrics. Implement evaluation pipeline như thế nào? Metric nào quan trọng nhất?
**Keywords:** faithfulness, answer relevancy, context precision, context recall, LLM-as-judge

**Trả lời mẫu:**

```
RAGAS Framework:

  ┌─────────────┐    ┌──────────────────┐    ┌──────────────────┐
  │    Query    │    │  Retrieved Docs  │    │   LLM Answer     │
  └──────┬──────┘    └────────┬─────────┘    └────────┬─────────┘
         │                    │                        │
         │     Context Precision: bao nhiêu % docs     │
         │     trong retrieved là thực sự relevant?    │
         │                    │                        │
         │     Context Recall: bao nhiêu % relevant    │
         │     info được retrieve (vs golden answer)?  │
         │                                             │
         │     Faithfulness: answer có được support    │
         │     bởi context không? (0-1)                │
         │                                             │
         └──────── Answer Relevancy: answer có trả    ─┘
                   lời đúng câu hỏi không? (0-1)
```

```python
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)
from datasets import Dataset

# Chuẩn bị eval dataset
eval_data = {
    "question": ["Chính sách hoàn tiền là gì?", "Cách hủy đơn hàng?"],
    "answer": ["Hoàn tiền trong 30 ngày...", "Để hủy đơn hàng, bạn..."],    # LLM output
    "contexts": [
        ["Chính sách của chúng tôi: hoàn tiền trong 30 ngày..."],            # retrieved docs
        ["Quy trình hủy đơn: vào My Orders, chọn Cancel..."],
    ],
    "ground_truth": [                                                          # golden answers
        "Khách hàng có thể hoàn tiền trong vòng 30 ngày kể từ ngày mua.",
        "Để hủy đơn, truy cập My Orders và nhấn nút Cancel trước khi ship.",
    ],
}

dataset = Dataset.from_dict(eval_data)
results = evaluate(
    dataset=dataset,
    metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
)
print(results)
# Output: {'faithfulness': 0.87, 'answer_relevancy': 0.91, ...}
```

**LLM-as-judge với rubric (custom evaluation):**

```python
FAITHFULNESS_RUBRIC = """You are evaluating whether an AI answer is faithful to its source context.

QUERY: {query}
CONTEXT: {context}
ANSWER: {answer}

Score on this rubric:
- 1.0: Every claim in the answer is explicitly supported by the context
- 0.7: Most claims supported, minor extrapolation
- 0.4: Some unsupported claims, but core answer is in context
- 0.0: Answer contradicts or ignores context (hallucination)

Return JSON: {{"score": float, "reasoning": "str", "unsupported_claims": ["list"]}}"""

async def llm_judge_faithfulness(
    query: str,
    context: str,
    answer: str,
    llm_client,
) -> dict:
    resp = await llm_client.chat.completions.create(
        model="gpt-4o",  # Dùng model mạnh hơn làm judge
        messages=[{
            "role": "user",
            "content": FAITHFULNESS_RUBRIC.format(
                query=query, context=context, answer=answer,
            ),
        }],
        response_format={"type": "json_object"},
        temperature=0,  # deterministic judging
    )
    import json
    return json.loads(resp.choices[0].message.content)
```

**Offline vs Online eval:**

| Type | Method | Dùng khi |
|------|--------|----------|
| Offline | Golden QA pairs + RAGAS | Trước khi deploy, A/B test configs |
| Online | User thumbs up/down | Sau deploy, implicit feedback |
| Online | Did user ask follow-up? | Proxy signal: follow-up = answer incomplete |

```python
# A/B testing RAG configurations
configs_to_test = [
    {"chunk_size": 256, "top_k": 10, "reranker": "cohere"},
    {"chunk_size": 512, "top_k": 20, "reranker": "bge"},
    {"chunk_size": 512, "top_k": 10, "reranker": None},
]

for config in configs_to_test:
    scores = []
    for qa_pair in golden_dataset:
        answer, context = run_rag_pipeline(qa_pair["question"], **config)
        score = evaluate_ragas(qa_pair, answer, context)
        scores.append(score)
    avg = sum(scores) / len(scores)
    print(f"Config {config}: avg RAGAS = {avg:.3f}")
```

---

## SECTION 7: Production RAG Challenges

### RAG-H07: Multi-tenant isolation — namespace vs separate index
**Câu hỏi:** Design multi-tenant RAG với 1000 tenants. Dùng namespace hay separate index? Làm sao đảm bảo tenant isolation hoàn toàn?
**Keywords:** namespace, index per tenant, metadata isolation, security, data leakage

**Trả lời mẫu:**

```
Decision framework:

  ┌─────────────────────────────────────────────────────────┐
  │ Tiêu chí          │ Namespace          │ Separate Index  │
  ├─────────────────────────────────────────────────────────┤
  │ Số tenants        │ Lên đến 10k        │ <100            │
  │ Cost              │ Chia sẻ index      │ Tốn nhất        │
  │ Isolation         │ Logical (good)     │ Physical (best) │
  │ Compliance        │ SOC2 OK            │ HIPAA/PCI cần   │
  │ Custom config     │ Không              │ Có (per index)   │
  └─────────────────────────────────────────────────────────┘
```

```python
from functools import wraps
import logging

logger = logging.getLogger(__name__)

class MultiTenantRAGClient:
    """
    Multi-tenant RAG với namespace isolation.
    CRITICAL: mọi operation PHẢI include tenant_id validation.
    """

    def __init__(self, pinecone_index, embedding_client):
        self.index = pinecone_index
        self.embedding_client = embedding_client

    def _get_namespace(self, tenant_id: str) -> str:
        """Deterministic namespace per tenant."""
        # Sanitize tenant_id — prevent namespace injection
        safe_id = "".join(c for c in tenant_id if c.isalnum() or c in "-_")
        if safe_id != tenant_id:
            raise ValueError(f"Invalid tenant_id: {tenant_id}")
        return f"tenant_{safe_id}"

    async def upsert(
        self,
        tenant_id: str,
        documents: list[dict],
        requesting_tenant_id: str,   # must match tenant_id
    ) -> None:
        """Upsert với double-check authorization."""
        if tenant_id != requesting_tenant_id:
            logger.warning(
                f"SECURITY: tenant {requesting_tenant_id} attempted to write to {tenant_id}"
            )
            raise PermissionError(f"Cannot write to namespace of another tenant")

        namespace = self._get_namespace(tenant_id)
        # ... upsert to namespace

    async def search(
        self,
        query: str,
        tenant_id: str,
        requesting_tenant_id: str,
        top_k: int = 10,
        metadata_filter: dict = None,
    ) -> list[dict]:
        """Search LUÔN LUÔN scoped to tenant namespace."""
        if tenant_id != requesting_tenant_id:
            raise PermissionError(f"Cannot search another tenant's data")

        namespace = self._get_namespace(tenant_id)
        embedding = await get_embedding_async(query, self.embedding_client)

        results = self.index.query(
            vector=embedding,
            top_k=top_k,
            namespace=namespace,        # scope to tenant
            filter=metadata_filter,
            include_metadata=True,
        )

        # Double-check: validate returned docs belong to this tenant
        validated = []
        for match in results.matches:
            if match.metadata.get("tenant_id") != tenant_id:
                logger.error(
                    f"SECURITY BREACH: doc {match.id} returned for wrong tenant!"
                )
                continue
            validated.append(match)

        return validated

    async def delete_tenant_data(self, tenant_id: str) -> None:
        """GDPR/data deletion: xóa toàn bộ namespace."""
        namespace = self._get_namespace(tenant_id)
        self.index.delete(delete_all=True, namespace=namespace)
        logger.info(f"Deleted all data for tenant {tenant_id}")
```

---

### RAG-H08: Stale index — update strategy cho dynamic documents
**Câu hỏi:** Khi documents thay đổi liên tục (daily updates), làm sao keep index fresh? Describe change detection strategy.

**Trả lời mẫu:**

```python
import asyncio
import hashlib
from datetime import datetime, timedelta
from typing import AsyncGenerator

import aiohttp
from celery import Celery

celery_app = Celery("rag_indexer", broker="redis://localhost:6379/0")


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def incremental_sync_task(self, source_id: str):
    """
    Celery task: chạy mỗi 15 phút per source.
    Detect changes bằng content hash, chỉ re-index changed docs.
    """
    try:
        asyncio.run(_sync_source(source_id))
    except Exception as exc:
        raise self.retry(exc=exc)


async def _sync_source(source_id: str):
    # 1. Fetch documents từ source (API, DB, S3...)
    new_docs = await fetch_source_documents(source_id)

    # 2. Fetch existing hashes từ metadata store
    existing_hashes = await get_stored_hashes(source_id)

    # 3. Detect changes
    to_update = []
    to_delete = set(existing_hashes.keys())

    for doc in new_docs:
        doc_hash = hashlib.sha256(doc["content"].encode()).hexdigest()
        doc_id = doc["id"]
        to_delete.discard(doc_id)  # Doc still exists

        if existing_hashes.get(doc_id) != doc_hash:
            to_update.append(doc)   # New or changed

    # 4. Re-index changed docs
    if to_update:
        await batch_reindex(to_update)

    # 5. Delete removed docs
    if to_delete:
        await batch_delete(list(to_delete))

    # 6. Update stored hashes
    await update_stored_hashes(source_id, {
        doc["id"]: hashlib.sha256(doc["content"].encode()).hexdigest()
        for doc in new_docs
    })


# Schedule: mỗi source sync mỗi 15 phút
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    "sync-source-internal-wiki": {
        "task": "incremental_sync_task",
        "schedule": crontab(minute="*/15"),
        "args": ("internal_wiki",),
    },
    "sync-source-legal-docs": {
        "task": "incremental_sync_task",
        "schedule": crontab(minute="0", hour="*/6"),  # Legal docs ít thay đổi hơn
        "args": ("legal_docs",),
    },
}
```

---

### RAG-H09: Siloed databases problem — multi-source retrieval
**Câu hỏi:** Bạn đã consolidate context từ nhiều siloed sources thế nào? Challenges và solutions?

**Trả lời mẫu (từ experience của Khoa):**

**Vấn đề tại Atrix:**
- Source 1: Internal wiki (Confluence) — structured, authoritative
- Source 2: Customer support tickets (Zendesk) — unstructured, conversational
- Source 3: Product PDFs — static, high authority
- Source 4: Real-time API data — fresh, no vector search
- Challenge: câu hỏi user cần context từ nhiều sources → không thể chỉ query 1 DB

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class RetrievedDoc:
    text: str
    source_id: str
    source_type: str   # "wiki" | "tickets" | "pdf" | "api"
    score: float
    metadata: dict


class BaseRetriever(ABC):
    @abstractmethod
    async def retrieve(self, query: str, top_k: int, filters: dict) -> list[RetrievedDoc]:
        pass


class PineconeRetriever(BaseRetriever):
    """Retriever cho wiki + PDFs (static content)."""
    def __init__(self, index, namespace: str):
        self.index = index
        self.namespace = namespace

    async def retrieve(self, query, top_k=10, filters=None):
        embedding = await get_embedding_async(query)
        results = self.index.query(
            vector=embedding, top_k=top_k,
            namespace=self.namespace, filter=filters,
            include_metadata=True,
        )
        return [
            RetrievedDoc(
                text=m.metadata["text"],
                source_id=m.id,
                source_type="pinecone",
                score=m.score,
                metadata=m.metadata,
            )
            for m in results.matches
        ]


class OpenSearchRetriever(BaseRetriever):
    """Retriever cho support tickets (BM25 heavy)."""
    def __init__(self, client, index_name: str):
        self.client = client
        self.index_name = index_name

    async def retrieve(self, query, top_k=10, filters=None):
        # ... OpenSearch BM25 + kNN query
        pass


class APIRetriever(BaseRetriever):
    """Real-time data retriever (không có vector index)."""
    def __init__(self, api_base_url: str):
        self.api_base_url = api_base_url

    async def retrieve(self, query, top_k=5, filters=None):
        # Route to appropriate API endpoint based on query intent
        intent = await detect_intent(query)
        if intent == "order_status":
            data = await fetch_order_api(filters.get("order_id"))
            return [RetrievedDoc(
                text=format_order_data(data),
                source_id=f"api_order_{filters.get('order_id')}",
                source_type="api",
                score=1.0,   # Direct lookup, always relevant
                metadata={"fresh": True},
            )]
        return []


class MultiSourceRetriever:
    """
    Orchestrate retrieval từ multiple sources.
    Retrieve in parallel, merge, deduplicate, rerank.
    """
    def __init__(
        self,
        retrievers: dict[str, BaseRetriever],
        reranker=None,
    ):
        self.retrievers = retrievers
        self.reranker = reranker

    async def retrieve(
        self,
        query: str,
        source_weights: dict[str, float] = None,   # override source importance
        filters: dict[str, dict] = None,            # per-source filters
        top_k_per_source: int = 10,
        top_k_final: int = 5,
    ) -> list[RetrievedDoc]:
        # Retrieve from all sources in parallel
        tasks = {
            name: retriever.retrieve(
                query,
                top_k=top_k_per_source,
                filters=(filters or {}).get(name, {}),
            )
            for name, retriever in self.retrievers.items()
        }
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        all_docs = []
        for name, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                logger.warning(f"Retriever {name} failed: {result}")
                continue
            # Apply source weight
            weight = (source_weights or {}).get(name, 1.0)
            for doc in result:
                doc.score *= weight
                all_docs.append(doc)

        # Rerank combined results
        if self.reranker and all_docs:
            all_docs = await self.reranker.rerank(query, all_docs)

        # Return top-k after fusion
        all_docs.sort(key=lambda d: d.score, reverse=True)
        return all_docs[:top_k_final]


# Usage
retriever = MultiSourceRetriever(
    retrievers={
        "wiki": PineconeRetriever(wiki_index, namespace="wiki"),
        "pdfs": PineconeRetriever(pdf_index, namespace="pdfs"),
        "tickets": OpenSearchRetriever(os_client, "support_tickets"),
        "api": APIRetriever("https://api.internal/v1"),
    },
    reranker=CohereReranker(),
)

docs = await retriever.retrieve(
    query="Trạng thái đơn hàng #12345 và chính sách hoàn tiền là gì?",
    source_weights={"api": 2.0, "wiki": 1.0, "pdfs": 1.5, "tickets": 0.7},
    filters={"api": {"order_id": "12345"}},
)
```

---

## SECTION 8: Câu hỏi hay gặp trong phỏng vấn Senior AI Engineer

### INTERVIEW-01: "Describe your production RAG architecture"
**Framework trả lời (STAR + Technical):**

1. **Situation:** "Tại Atrix, chúng tôi cần build RAG system cho enterprise customers, mỗi tenant có siloed data sources khác nhau."
2. **Task:** "Multi-tenant system hỗ trợ query cross-source, với citation và accuracy cao."
3. **Architecture:** Mô tả diagram → indexing pipeline → retrieval pipeline → evaluation.
4. **Result:** "Giảm hallucination 60% bằng metadata pre-enrichment, RAGAS faithfulness 0.87."

---

### INTERVIEW-02: "How did you reduce hallucination 60%?"
**Framework trả lời:**

1. **Identify root cause:** chunks không có context → LLM không biết chunk này authoritative hay không.
2. **Solution:** metadata enrichment (source, date, authority_score, section).
3. **Pre-filtering:** chỉ retrieve docs có `authority_score >= 0.8` cho policy queries.
4. **Citation enforcement:** prompt explicitly yêu cầu cite source [1], [2] → LLM "phải trung thực hơn".
5. **Measurement:** RAGAS faithfulness trước: 0.54 → sau: 0.87.

---

### INTERVIEW-03: "RRF formula — giải thích"
**Công thức:**
```
RRF_score(d) = Σ_{r in rankings} 1 / (k + rank_r(d))

k = 60 (constant, giảm impact của top-ranked docs, empirically optimal)
rank_r(d) = vị trí của document d trong ranking r
```

Ví dụ: doc A ranked #1 trong BM25, ranked #3 trong vector:
```
RRF(A) = 1/(60+1) + 1/(60+3) = 0.01639 + 0.01587 = 0.03226
```

---

### INTERVIEW-04: "Chunk size tuning — how do you decide?"
**Framework trả lời:**

1. Chạy eval với golden QA dataset
2. Test chunk_size ∈ {128, 256, 512, 1024}
3. Đo Context Precision và Context Recall với RAGAS
4. Thường: 512 là sweet spot; nếu queries cần specific facts → 256; nếu queries cần broad context → 1024
5. Parent-child chunking: best of both worlds (small for retrieval, large for generation)

---

### INTERVIEW-05: "Pinecone vs OpenSearch — khi nào dùng cái nào?"

| Tiêu chí | Pinecone | OpenSearch |
|----------|----------|------------|
| Hybrid search | Built-in sparse-dense | Manual (BM25 + script_score) |
| Managed | Fully managed, serverless | Self-managed hoặc AWS OpenSearch Service |
| Keyword search | Limited | Excellent (Elasticsearch core) |
| Multi-tenant | Namespace | Index-per-tenant hoặc routing |
| Cost | Per query/vector | Compute-based |
| Dùng khi | Pure vector, managed, startup | Existing ES, keyword-heavy, hybrid critical |

---

## Quick Reference: Metrics cần nhớ

| Metric | Formula ngắn | Target production |
|--------|-------------|------------------|
| RAGAS Faithfulness | Claims supported by context | > 0.80 |
| RAGAS Answer Relevancy | Answer addresses question | > 0.85 |
| RAGAS Context Precision | Retrieved docs relevant | > 0.70 |
| RAGAS Context Recall | All relevant info retrieved | > 0.75 |
| Latency (P99) | End-to-end RAG | < 3s |
| Retrieval Recall@5 | Relevant doc in top 5 | > 0.85 |

---

*File này cover toàn bộ RAG stack từ indexing đến evaluation. Focus vào Section 4 (Advanced Retrieval) và Section 7 (Production Challenges) — đây là những phần interviewer hay đào sâu nhất cho Senior AI Engineer level.*
