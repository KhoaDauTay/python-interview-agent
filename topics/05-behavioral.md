# Behavioral Interview — Question Bank (STAR Method)
> CV context: Khoa — Backend AI Engineer tại Spartan. Các câu STAR nên lấy từ project thực tế trong CV.

## STAR Framework
- **S**ituation: Bối cảnh, khi nào, ở đâu
- **T**ask: Nhiệm vụ của bạn là gì
- **A**ction: Bạn đã làm gì cụ thể
- **R**esult: Kết quả đạt được (số liệu càng tốt)

**Thời gian lý tưởng:** 1.5–2 phút mỗi câu. Không quá ngắn, không lan man.

---

## Self-Introduction (English — Domain 9)

### BH-INTRO: Giới thiệu bản thân bằng tiếng Anh
**Câu hỏi:** "Tell me about yourself and your background."
**Structure:** Current role → Key achievements → Tech strengths → Why this role
**Expected answer (Khoa's version):**
> "I'm Khoa, a Backend AI Engineer with over 3 years of experience building scalable Python backends and AI-powered systems. Most recently at Spartan, I led development of production RAG pipelines and LLM orchestration systems for clients in life sciences and data engineering. I'm particularly strong in FastAPI, Celery async architectures, and PostgreSQL optimization — I've cut API response times from 800ms to under 200ms and improved pipeline reliability from 87% to 99%+. I'm now looking for a role where I can continue building production-grade AI systems while deepening my expertise in [their tech stack]."

**Follow-up:** "What's your biggest technical achievement?"

---

## Problem Solving (từ CV thực tế)

### BH-P01: Bug khó nhất — Celery Beat duplicate runs
**Câu hỏi:** "Tell me about the most complex bug you've debugged."
**STAR guide (Sidecardata):**
- **S:** DataOps platform với Celery Beat scheduling data quality checks trên Snowflake
- **T:** Phát hiện pipeline runs bị duplicate dưới load, gây redundant executions
- **A:** Investigate Celery Beat scheduler, phát hiện race condition khi multiple workers pick up cùng 1 scheduled task → implement distributed lock, exponential backoff retry
- **R:** Reduced redundant executions by ~40%, pipeline reliability từ 87% → 99%+
**Follow-up:** "How did you detect it was a scheduling bug and not a business logic bug?"

### BH-P02: Performance optimization
**Câu hỏi:** "Describe a time you significantly improved system performance."
**STAR guide (Sidecardata):**
- **S:** Django REST APIs serving catalog/governance data → avg response time 800ms
- **T:** Users complaining about slow dashboard load
- **A:** EXPLAIN ANALYZE slow queries, identify missing indexes trên high-traffic metadata tables, optimize ORM queries (N+1 → select_related), add composite indexes
- **R:** Avg response time from 800ms → under 200ms (4× improvement)
**Follow-up:** "How did you decide WHICH queries to optimize first?"

### BH-P03: Reducing hallucination — Atrix AI
**Câu hỏi:** "Tell me about a technical challenge you solved in an AI system."
**STAR guide (Atrix AI):**
- **S:** Compliance-grade AI platform, LLM outputs were hallucination-heavy because siloed databases fed inconsistent context
- **T:** Improve accuracy for Medical Affairs use cases (HCP engagement)
- **A:** Built structured enrichment layer validating and consolidating metadata before prompt injection, added guardrails enforcing regulatory constraints
- **R:** Hallucination rate cut by ~60% in internal evals
**Follow-up:** "How did you measure hallucination rate? What's your eval methodology?"

---

## Leadership & Initiative

### BH-L01: Python project template
**Câu hỏi:** "Kể về lần bạn chủ động cải thiện quy trình hoặc codebase mà không ai yêu cầu."
**STAR guide (Spartan):**
- **S:** Mỗi AI project mới mất nhiều ngày để setup cùng boilerplate (FastAPI structure, RAG base classes, OpenAI integration, Pydantic schemas)
- **T:** Không có standard — mỗi engineer làm theo cách riêng
- **A:** Thiết kế và build company-wide Python project template: FastAPI structure, RAG pipeline base classes, OpenAI/Claude integration layer, Pydantic v2 schemas, Temporal workflow stubs
- **R:** Template adopted across all subsequent AI projects — bootstrap time từ days → hours
**Follow-up:** "How did you get buy-in from the team to adopt the template?"

### BH-L02: Mentor & Code review
**Câu hỏi:** "Have you ever mentored or led other engineers?"
**STAR guide (DG External):**
- **S:** Led engineering standards at DG External
- **T:** Junior engineers không consistent về Python best practices, API documentation scattered
- **A:** Conducted code reviews, produced API documentation for internal + external teams, mentored on Python best practices
- **R:** Consistent code quality, external partners able to integrate APIs independently
**Follow-up:** "What's your code review philosophy? What do you always look for?"

---

## Conflict & Teamwork

### BH-C01: Technical disagreement
**Câu hỏi:** "Kể về lần bạn có bất đồng ý kiến với teammate hoặc senior về technical decision."
**Điểm cần có:** acknowledge cả hai bên, data-driven argument, propose experiment, reach compromise
**Red flag:** "Tôi luôn đúng", đổ lỗi người khác

### BH-C02: Deadline áp lực
**Câu hỏi:** "Kể về lần phải deliver dưới áp lực deadline rất ngặt. Bạn ưu tiên thế nào?"
**Điểm cần có:** triage features, communicate scope reduction to stakeholders, ship core, iterate
**Follow-up:** "Nếu làm lại, bạn sẽ làm khác gì?"

---

## Failure & Growth

### BH-F01: Lần thất bại / sai lầm technical
**Câu hỏi:** "Tell me about a technical decision you regret."
**Điểm cần có:** ownership (không đổ lỗi), lesson learned, behavior change after
**Red flag:** "Tôi chưa bao giờ thất bại", câu chuyện quá nhỏ, đổ lỗi cho requirements

### BH-F02: Học nhanh công nghệ mới
**Câu hỏi:** "Tell me about a time you had to learn a new technology quickly."
**STAR guide candidates:**
- Temporal (workflow orchestration) khi join Spartan
- Pinecone + vector DB khi build RAG cho Atrix AI
- ClickHouse + OLAP patterns khi join Sidecardata project
**Follow-up:** "What's your learning strategy when picking up something completely new?"

---

## Motivation & Culture Fit

### BH-M01: Tại sao muốn join công ty này
**Câu hỏi:** "Why do you want to work here?"
**Tips:** Research công ty trước, nêu cụ thể (product, tech stack, mission), liên kết với career goal của Khoa (deeper into production AI systems)

### BH-M02: Career goal 3–5 năm
**Câu hỏi:** "Where do you see yourself in 3–5 years?"
**Khoa's direction:** Senior Backend/AI Engineer → Tech Lead, deeper into distributed systems + AI infrastructure (not management track initially)
**Tips:** Ambitious nhưng realistic, liên quan đến vị trí đang apply, show growth mindset

### BH-M03: Willing to learn operations
**Câu hỏi:** "You mentioned wanting to improve in operations — what have you done about it recently?"
**Expected:** Honest về gap, cụ thể về steps (reading, hands-on, asking senior devs), reference actual Sentry/Grafana experience as starting point
