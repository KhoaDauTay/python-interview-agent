# Database Advanced — Question Bank
> Nguồn: cs_questions.txt — DATABASE section
> Extends topics/03-python-backend.md SECTION 4 (basic DB) với deep-dive internals

---

## EASY

### DB-E01: SQL vs NoSQL
**Câu hỏi:** So sánh Relational DB (SQL) và NoSQL. Khi nào dùng cái nào?
**Keywords:** schema, ACID vs BASE, vertical vs horizontal scale, consistency, CAP theorem
**Expected answer:**
| | SQL (PostgreSQL) | NoSQL (MongoDB, Redis) |
|--|-----|-----|
| Schema | Fixed, strict | Flexible |
| Transactions | ACID | BASE (eventual consistency) |
| Scale | Vertical chủ yếu | Horizontal (sharding dễ hơn) |
| Query | Powerful JOIN | Limited (denormalized) |
| Use case | Financial, relational data | Catalog, session, cache, logs |
**Follow-up:** "CAP theorem là gì? PostgreSQL chọn CP hay AP?"

### DB-E02: Parameterized Statement & SQL Injection
**Câu hỏi:** SQL Injection là gì? Parameterized statement ngăn chặn thế nào? Hoạt động internally?
**Keywords:** prepared statement, compile once execute many, escape, bind variables
**Expected answer:**
```sql
-- VULNERABLE
query = f"SELECT * FROM users WHERE name = '{user_input}'"

-- SAFE (parameterized)
query = "SELECT * FROM users WHERE name = $1"
cursor.execute(query, (user_input,))
```
DB compile query structure trước, sau đó bind parameters → input không bao giờ được interpret như SQL code. Bonus: compiled query có thể reuse → tăng performance.
**Follow-up:** "Bao nhiêu round trips đến DB cho 1 prepared statement? (1 compile + 1 execute)"

---

## MEDIUM

### DB-M01: Indexing internals
**Câu hỏi:** Index hoạt động thế nào internally? Data structure nào được dùng?
**Keywords:** B-tree (B+tree), leaf node, range query, composite index, covering index, write overhead
**Expected answer:**
- **B+tree**: Hầu hết DB index. Leaf nodes chứa data, linked list → range query O(log n + k). Internal nodes chỉ có keys.
- **Hash index**: O(1) exact match, KHÔNG support range query.
- **Composite index (a, b, c)**: Chỉ useful khi query theo left prefix: `WHERE a=1`, `WHERE a=1 AND b=2`. KHÔNG useful: `WHERE b=2`.
```sql
-- Dùng index (a, b):
WHERE a = 5              -- ✅
WHERE a = 5 AND b = 3    -- ✅
WHERE b = 3              -- ❌ (không dùng index)
```
**Follow-up:** "Index trên boolean column có hữu ích không? Low cardinality thì sao?"

### DB-M02: Query optimization & EXPLAIN
**Câu hỏi:** Làm thế nào SQL engine optimize query? Làm sao biết query có dùng index không?
**Keywords:** query planner, `EXPLAIN ANALYZE`, seq scan vs index scan, cost estimation, statistics
**Expected code:**
```sql
EXPLAIN ANALYZE SELECT * FROM documents WHERE user_id = 123;
-- Seq Scan: đọc toàn bộ table
-- Index Scan: dùng index
-- Bitmap Heap Scan: dùng index, sau đó fetch từ heap
```
**CV link:** "Bạn optimize từ 800ms→200ms ở Sidecardata — `EXPLAIN ANALYZE` cho thấy gì? Seq scan hay Index scan?"
**Follow-up:** "Khi nào query planner KHÔNG dùng index dù có? (low cardinality, stale statistics)"

### DB-M03: Database Transaction & ACID
**Câu hỏi:** Transaction là gì? Giải thích ACID. Dirty read, phantom read, non-repeatable read?
**Keywords:** BEGIN/COMMIT/ROLLBACK, WAL (Write-Ahead Log), isolation levels, MVCC
**Expected answer:**
- **Atomicity**: All or nothing → rollback via WAL/undo log
- **Consistency**: Data valid trước và sau transaction
- **Isolation**: Concurrent transactions không affect nhau
- **Durability**: Committed data không mất → WAL flush to disk
**Isolation levels:**
| Level | Dirty Read | Non-repeatable | Phantom |
|-------|-----------|----------------|---------|
| Read Uncommitted | ✅ | ✅ | ✅ |
| Read Committed | ❌ | ✅ | ✅ |
| Repeatable Read | ❌ | ❌ | ✅ |
| Serializable | ❌ | ❌ | ❌ |
**Follow-up:** "PostgreSQL default isolation level là gì? MVCC giúp gì cho concurrent reads?"

### DB-M04: Read/Write Lock & Race Condition in DB
**Câu hỏi:** Làm thế nào tránh race condition trong DB? `SELECT FOR UPDATE` là gì?
**Keywords:** optimistic locking, pessimistic locking, `FOR UPDATE`, version column, deadlock
**Expected answer:**
- **Pessimistic**: `SELECT ... FOR UPDATE` → lock row cho đến end of transaction
- **Optimistic**: Thêm `version` column, check khi UPDATE:
```sql
-- Pessimistic
BEGIN;
SELECT balance FROM accounts WHERE id = 1 FOR UPDATE;
UPDATE accounts SET balance = balance - 100 WHERE id = 1;
COMMIT;

-- Optimistic
UPDATE accounts SET balance = balance - 100, version = version + 1
WHERE id = 1 AND version = 5;
-- Nếu 0 rows updated → concurrent modification → retry
```
**CV link:** "Celery Beat duplicate runs — nếu fix bằng DB lock thay vì Redis, bạn dùng cách nào?"

### DB-M05: Database Replication
**Câu hỏi:** Database Replication là gì? Master-Slave sync hoạt động thế nào?
**Keywords:** binlog/WAL, async vs sync replication, read replica, replication lag, failover
**Expected answer:**
- Master ghi WAL (Write-Ahead Log) / binlog
- Slave đọc và replay log → eventually consistent
- **Async replication**: Master không đợi slave confirm → lag, có thể mất data nếu master crash
- **Sync replication**: Master đợi ít nhất 1 slave confirm → no data loss, slower write
**Follow-up:** "Slave có thể là master của slave khác không? Cascading replication?"

### DB-M06: Database Sharding
**Câu hỏi:** Database Sharding là gì? Các sharding strategies? Làm sao ensure primary key globally unique?
**Keywords:** horizontal partitioning, shard key, consistent hashing, UUID, Snowflake ID, cross-shard join
**Expected answer:**
- **Range sharding**: user_id 1-1M → shard 1, 1M-2M → shard 2. Simple nhưng hotspot.
- **Hash sharding**: `shard = hash(user_id) % N`. Uniform nhưng khó range query.
- **Consistent hashing**: Thêm/remove node ít ảnh hưởng.
**Global unique ID**: UUID (128-bit), Snowflake ID (timestamp + machine ID + sequence).
**Follow-up:** "Cross-shard JOIN xử lý thế nào? Tại sao NoSQL scale tốt hơn SQL khi sharding?"

---

## HARD

### DB-H01: Distributed Transaction
**Câu hỏi:** Distributed transaction là gì? 2PC vs Saga pattern?
**Keywords:** 2-phase commit (prepare + commit), coordinator, Saga (choreography vs orchestration), compensating transaction
**Expected answer:**
- **2PC**: Coordinator hỏi tất cả nodes "ready?" → nếu tất cả OK → commit. Vấn đề: coordinator crash → blocking.
- **Saga**: Chuỗi local transactions. Nếu step N fail → chạy compensating transactions cho step 1..N-1.
  - Choreography: Events, không có central coordinator
  - Orchestration: Central coordinator (như Temporal workflow!)
**CV link:** "Temporal ở Spartan là orchestration-based Saga pattern. Retry/compensating activities trong Temporal hoạt động thế nào?"

### DB-H02: Indexing advanced — Complexity Analysis
**Câu hỏi:** Complexity của các query patterns này? Cách optimize?
**Keywords:** `OFFSET`, cursor pagination, covering index, `COUNT(*)`, full table scan
**Questions:**
```sql
-- Q1: Tại sao query này chậm?
SELECT * FROM posts ORDER BY created_at LIMIT 10 OFFSET 1000000;

-- Q2: COUNT(*) complexity?
SELECT COUNT(*) FROM large_table;

-- Q3: WHERE id IN (a, b, c) vs WHERE id = a OR id = b OR id = c?
```
**Expected answers:**
- Q1: Phải scan 1,000,010 rows, discard 1M → O(offset). Fix: cursor pagination (`WHERE id > last_seen_id LIMIT 10`)
- Q2: PostgreSQL có `pg_class.reltuples` estimate. Exact COUNT(*) = O(n) hoặc index scan.
- Q3: `IN` và `OR` tương đương với query planner. Cả hai dùng index nếu có.
