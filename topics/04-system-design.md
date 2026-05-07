# System Design — Question Bank

## Framework ôn tập
Luôn dùng framework sau khi trả lời system design:
1. **Clarify requirements** — functional & non-functional
2. **Estimate scale** — QPS, storage, bandwidth
3. **High-level design** — các component chính
4. **Deep dive** — component quan trọng nhất
5. **Bottleneck & tradeoffs** — điểm yếu, cách scale

---

## EASY

### SD-E01: URL Shortener
**Câu hỏi:** Design một URL shortener (như bit.ly).
**Keywords:** hashing, base62, redirect 301 vs 302, KV store, rate limiting
**Scale hint:** 100M URLs, 1000 reads/sec, 100 writes/sec
**Follow-up:** "Làm sao tránh hash collision? Custom alias xử lý thế nào?"

### SD-E02: Rate Limiter
**Câu hỏi:** Design một rate limiter API.
**Keywords:** token bucket, leaky bucket, sliding window, Redis, distributed rate limiting
**Follow-up:** "Khi có nhiều server, rate limit đồng bộ thế nào?"

---

## MEDIUM

### SD-M01: Notification System
**Câu hỏi:** Design một notification system (push, email, SMS) cho app 10M users.
**Keywords:** message queue, Kafka/RabbitMQ, fan-out, delivery guarantee, retry
**Follow-up:** "Làm sao đảm bảo notification gửi đúng 1 lần (exactly-once)?"

### SD-M02: News Feed (Social Network)
**Câu hỏi:** Design news feed cho social network (như Facebook).
**Keywords:** push vs pull model, fanout on write/read, celebrity problem, cache
**Follow-up:** "User có 10M followers — fanout on write có vấn đề gì?"

### SD-M03: Distributed Cache
**Câu hỏi:** Design distributed cache như Redis Cluster.
**Keywords:** consistent hashing, replication, eviction policy, CAP theorem
**Follow-up:** "Consistent hashing giúp gì khi add/remove node?"

### SD-M04: Real-time Data Pipeline
**Câu hỏi:** Design data pipeline cho crypto trading (real-time price ingestion → analytics).
**Keywords:** Kafka, stream processing, ClickHouse, WebSocket, backpressure
**Follow-up:** "Làm sao handle late data? Out-of-order events?"

---

## HARD

### SD-H01: Search Engine
**Câu hỏi:** Design một web search engine (simplified Google).
**Keywords:** crawler, inverted index, PageRank, distributed indexing, relevance scoring
**Follow-up:** "Inverted index build thế nào? Update khi web thay đổi?"

### SD-H02: Distributed Transaction
**Câu hỏi:** Khi nào cần distributed transaction? 2PC vs Saga pattern?
**Keywords:** 2-phase commit, saga (choreography vs orchestration), eventual consistency
**Follow-up:** "Saga pattern có downside gì? Compensating transaction là gì?"

### SD-H03: Multi-region Deployment
**Câu hỏi:** Design system chạy ở 3 regions (US, EU, APAC) với data residency requirements.
**Keywords:** active-active vs active-passive, CRDT, geo-routing, data sovereignty
**Follow-up:** "Conflict resolution khi 2 regions cùng update 1 record?"
