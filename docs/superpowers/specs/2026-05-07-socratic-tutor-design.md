# Systems Learning — Socratic Tutor (Design Spec)

**Date:** 2026-05-07
**Status:** Approved (pending user spec review)
**Source documents:**
- `docs/Project Instructions from Facebook.pdf` — the Hard Rules CLAUDE.md
- `docs/Socratic Learning.pdf` — the Vietnamese meta-guide on prediction-error learning

## 1. Goal

Replace the existing interview-prep system in this repo with a Socratic tutor that teaches computer-systems first principles. The tutor grounds every substantive claim in one of four textbooks (Skiena, DDIA, OSTEP, Kurose/Ross) under `books/`, and drives learning through prediction-error loops rather than exposition.

The user (a Python engineer preparing for systems-design depth) drives sessions in the form: "I want to design Redis from scratch" — and the tutor refuses to dump information, instead asking targeted questions, demanding predictions before reveals, and closing each session with a reading assignment plus a synthesis sentence the user writes themselves.

## 2. Non-goals

- Not a generic interview-prep tool. Algorithm Q&A, behavioral STAR practice, and Python trivia are removed.
- Not a multi-language tool. The tutor speaks English only — the textbooks are English and citations need to match book wording for retrieval to work.
- Not a content generator. The tutor never writes the synthesis sentence. The user does.
- Not a book search engine. `Grep` over `books/` is sufficient; no embeddings, RAG, or external indexes.

## 3. Architecture

**Approach:** Single tutor agent + thin command shims (Approach A from brainstorming).

```
User
  │
  ├── slash command (/learn, /quiz, /predict, /sketch, /cite, /pattern, /rewind, /close, /progress)
  │
  ▼
Command shim (.claude/commands/*.md)
  │  invokes with intent
  ▼
socratic-tutor agent (.claude/agents/socratic-tutor.md)
  │  applies 9 Hard Rules
  ▼
Tools available to agent:
  - Read, Grep, Glob   → search books/ before any explanation (Rule #1)
  - Write, Edit        → append to sessions/<file>.md and progress.json
  - WebSearch          → off by default; only with user confirmation (Rule per PDF "Web Search")
```

The tutor agent owns the philosophy. Commands are entry points, not logic.

## 4. File layout

```
python-interview/
├── CLAUDE.md                                # REPLACED with Hard Rules from PDF 1
├── books/
│   ├── README.md                            # NEW — drop the 4 textbook PDFs here
│   └── (Skiena.pdf, DDIA.pdf, OSTEP.pdf, KuroseRoss.pdf — added later by user)
├── .claude/
│   ├── agents/
│   │   └── socratic-tutor.md                # NEW
│   └── commands/
│       ├── learn.md                         # NEW
│       ├── quiz.md                          # NEW
│       ├── predict.md                       # NEW
│       ├── sketch.md                        # NEW
│       ├── cite.md                          # NEW
│       ├── pattern.md                       # NEW
│       ├── rewind.md                        # NEW
│       ├── close.md                         # NEW
│       └── progress.md                      # KEPT — repurposed
├── topics/                                  # DELETED (interview-style)
├── sessions/
│   ├── .gitkeep
│   ├── 2026-05-07_data-structures.md        # KEPT (historical, old format)
│   └── (new sessions in Socratic format)
├── progress.json                            # REPURPOSED — schema in §6
└── docs/
    ├── Project Instructions from Facebook.pdf
    ├── Socratic Learning.pdf
    └── superpowers/specs/
        └── 2026-05-07-socratic-tutor-design.md  # this file
```

**Files deleted:** `.claude/agents/teacher.md`, `.claude/commands/start.md`, `topic.md`, `hint.md`, `answer.md`, `evaluate.md`, all of `topics/`.

**Files kept unchanged:** `sessions/.gitkeep`, `sessions/2026-05-07_data-structures.md` (historical).

## 5. The agent: `.claude/agents/socratic-tutor.md`

Frontmatter:

```yaml
---
name: socratic-tutor
description: Use for any systems-design learning session — designing Redis, Kafka, Postgres, etc. from first principles. Apply the 9 Hard Rules from CLAUDE.md.
tools: Read, Grep, Glob, Write, Edit, WebSearch
---
```

Body sections (verbatim or near-verbatim from PDF 1):
1. **Mission** — one paragraph stating the tutor's purpose.
2. **Hard Rules** — all 9 rules, numbered, in their original wording.
3. **Style** — short questions, friction is the point, etc.
4. **Anti-patterns** — the 4 forbidden behaviors.
5. **Web Search policy** — off by default, three approved triggers.
6. **The Loop** — Problem → predict/sketch → sharpen → grounding → pattern → next.
7. **Session logging protocol** — append to `sessions/YYYY-MM-DD_<system>.md` per the schema in §6. **The synthesis sentence is captured verbatim from the user; the tutor never paraphrases it.**

## 6. Schemas

### 6.1 Session log: `sessions/YYYY-MM-DD_<system>.md`

```markdown
# Session: <system> — <date>
**Goal:** Trace one design decision end-to-end (problem → mechanism → tradeoff → principle)

## Retrieval (open) — Rule #9
- Q: <tutor's retrieval question on prior session>
- A: <user's answer>
- Result: passed | exposed gap → today's lesson

## Loop 1 — <concept name>
- **Problem:** <what we're designing/asking>
- **Prediction (user):** <user's guess before any explanation>
- **Sharpening:** <tutor's targeted question that exposed the gap>
- **Textbook grounding:** <citation, e.g. "DDIA Ch.3 'Hash Indexes' p.74">
- **Pattern surfaced:** <e.g. "WAL — also seen in Postgres, SQLite">

## Loop 2 — ...
(repeat per concept)

## Close — Rule #8
- **Reading assignment:** <specific sections, e.g. "OSTEP §33.1–33.4">
- **Synthesis sentence (user's own words):** <user types this; tutor never writes it>
```

### 6.2 `progress.json`

```json
{
  "systems_studied": ["redis", "kafka"],
  "concepts_traced": [
    {"concept": "WAL", "session": "2026-05-08_redis", "first_principle": "DDIA Ch.3"}
  ],
  "patterns_surfaced": {
    "WAL": ["redis", "postgres"],
    "COW": ["btrfs"]
  },
  "retrieval_failures": [
    {"date": "2026-05-09", "topic": "eviction policies", "became_lesson": true}
  ],
  "synthesis_sentences": [
    {"date": "2026-05-08", "system": "redis", "sentence": "<user's words>"}
  ]
}
```

**Bootstrap value** (initial state, written at install time):

```json
{
  "systems_studied": [],
  "concepts_traced": [],
  "patterns_surfaced": {},
  "retrieval_failures": [],
  "synthesis_sentences": []
}
```

## 7. Commands

Each command file is 5–20 lines of markdown — frontmatter + a short prompt that frames the tutor's response. Commands contain **no teaching logic**; they only route intent.

| Command | Trigger | Effect |
|---|---|---|
| `/learn <system>` | Start a new session | Tutor opens with Rule #5 calibration ("Have you seen X?"), then Rule #4 sketch. Creates `sessions/<date>_<system>.md`. |
| `/quiz` | Re-open prior session | Tutor finds latest `sessions/*.md`, asks 2–3 retrieval questions per Rule #9. Failed retrieval → today's lesson. |
| `/predict` | User invokes when tutor explained without asking | Tutor backs up, asks user to predict, then resumes. |
| `/sketch` | Force Rule #4 | Tutor asks user to design the next component before showing the canonical version. |
| `/cite` | Force Rule #1 | Tutor `Grep`s `books/` for the last claim, returns a section citation. If not found, says so. |
| `/pattern` | Force Rule #7 | Reads `progress.json#patterns_surfaced`, asks "where have you seen this before?" |
| `/rewind` | Reminder | Static text explaining the Claude Code rewind feature; takes no action. |
| `/close` | End session | Tutor emits reading assignment, prompts user for synthesis sentence in their own words, appends both to session file and `progress.json`. |
| `/progress` | Inspect progress | Reads `progress.json`, shows: systems studied, concepts traced (with citations), top recurring patterns, retrieval-failure rate. |

## 8. CLAUDE.md content

`CLAUDE.md` is replaced wholesale with the content of PDF 1 ("Project Instructions from Facebook"), reformatted as Markdown. This makes the project usable in three modes:
1. **Claude Code** — agent + commands operate directly on `books/`.
2. **Claude.ai Projects** — user uploads the 4 textbook PDFs as project knowledge; CLAUDE.md is pasted into Project Instructions.
3. **Other clients** — CLAUDE.md alone suffices as a system prompt.

The `Setup` and `Cách bắt đầu một session` sections from PDF 2 are NOT copied into CLAUDE.md — they are user-facing meta-guidance, not tutor instructions. They live in PDF form under `docs/`.

## 9. Behaviors and edge cases

- **Books not yet present.** `books/` exists with a README. When the tutor needs to cite, it `Grep`s, finds nothing, and per Rule #1 says "not in the books — I cannot give you a grounded answer here." It does **not** fall back to web search or guess. This is the correct loud failure.
- **User says "just tell me."** Per Style rules: tutor resists once, then yields. Yielding still requires a citation if claim is substantive.
- **Two questions in one turn.** User can interrupt with `/predict` or just say "one at a time." Tutor abandons question 2.
- **Confident-but-imprecise answer.** Tutor invokes Rule #6 — asks user to make it precise before moving on.
- **Tangent.** User uses Claude Code's rewind feature to discard the branch. `/rewind` exists only as a reminder; it doesn't manipulate history.
- **Synthesis sentence.** Tutor must NEVER write this. If user says "you write it," tutor refuses and explains why (PDF 2: "đây là lúc mình buộc phải xử lý thông tin").

## 10. Testing / verification

After implementation, manually verify by running these scenarios:

1. **Cold start:** `/learn redis` with empty `books/`. Tutor must calibrate first, ask user to sketch, and when grounding is needed, must say "not in books/."
2. **One-question rule:** Try to bait the tutor with "explain memtables AND hash indexes." Tutor must answer one and stop, OR ask which to explore first.
3. **Predict-before-verify:** Ask "how does Redis persist data?" The tutor must ask "what would you guess first?" — not explain.
4. **Citation:** With Skiena.pdf placed in `books/`, ask about amortized analysis. Tutor must produce a Skiena §X.Y citation, not a generic explanation.
5. **Close ritual:** End a session with `/close`. Tutor must produce a reading assignment, prompt for synthesis, and refuse to write it.
6. **Retrieval at next start:** Run `/quiz` after a session exists. Tutor must read `sessions/`, ask 2–3 questions, and treat failure as the lesson.

These scenarios are the acceptance test. They cover the 5 Hard Rules whose violation is observable in a single session (Rules #1, #2, #3, #4, #8) plus retrieval at session-open (#9).

## 11. Out of scope

- Migrating the existing `sessions/2026-05-07_data-structures.md` to the new schema. It stays as-is; it's a historical artifact.
- Building a books/ ingestion pipeline. User drops PDFs; `Grep` reads them directly.
- Vietnamese translation of the tutor. Explicitly rejected during brainstorming.
- A `/sketch` command that generates ASCII diagrams. The user sketches; the tutor only asks.
