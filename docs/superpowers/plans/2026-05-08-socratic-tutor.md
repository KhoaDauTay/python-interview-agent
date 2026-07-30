# Systems Learning — Socratic Tutor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the existing interview-prep system with a Socratic tutor that teaches computer-systems first principles, grounding every claim in the four textbooks under `books/` and driving learning through prediction-error loops.

**Architecture:** Single tutor agent (`.claude/agents/socratic-tutor.md`) carries the 9 Hard Rules. Nine slash commands are thin shims that invoke the agent with a specific intent. `CLAUDE.md` carries the same rules so the project also works in Claude.ai Projects without the agent file. Sessions are append-only Markdown logs in `sessions/`; cross-session state lives in `progress.json`.

**Tech Stack:** Markdown (CLAUDE.md, agent, commands, session logs), JSON (`progress.json`), no runtime code beyond the existing `main.py` (untouched). Python 3.14 (from `.venv`) is available for verification one-liners. No test framework is added — verification is JSON parse + frontmatter parse + grep for required sections + manual acceptance scenarios.

**Spec:** `docs/superpowers/specs/2026-05-07-socratic-tutor-design.md`

---

## File Structure

**Created:**
- `books/README.md` — instructions for dropping textbook PDFs
- `books/.gitignore` — exclude PDFs from git
- `.claude/agents/socratic-tutor.md` — tutor agent (the heart)
- `.claude/commands/learn.md` — `/learn <system>`
- `.claude/commands/quiz.md` — `/quiz`
- `.claude/commands/predict.md` — `/predict`
- `.claude/commands/sketch.md` — `/sketch`
- `.claude/commands/cite.md` — `/cite`
- `.claude/commands/pattern.md` — `/pattern`
- `.claude/commands/rewind.md` — `/rewind`
- `.claude/commands/close.md` — `/close`

**Replaced:**
- `CLAUDE.md` — Hard Rules from PDF 1
- `progress.json` — new schema (old preserved as `progress.legacy.json`)
- `.claude/commands/progress.md` — repurposed for the new schema

**Deleted:**
- `.claude/agents/teacher.md`
- `.claude/commands/start.md`
- `.claude/commands/topic.md`
- `.claude/commands/hint.md`
- `.claude/commands/answer.md`
- `.claude/commands/evaluate.md`
- `topics/` (entire directory)

**Untouched:**
- `sessions/.gitkeep`
- `sessions/2026-05-07_data-structures.md` (historical)
- `main.py`, `pyproject.toml`, `.venv/`, `.idea/`, `docs/*.pdf`

---

## Notes for the Executor

- This is a config-only project. There is no Python code under test. Each task's verification is: file exists, frontmatter parses, required headings present, JSON valid.
- Use `python3` from the project venv: `source .venv/bin/activate` once at the start of the session, or invoke `/Users/khoahuynh/PycharmProjects/python-interview/.venv/bin/python3` directly. The plan uses the activated form.
- All commits use the message body convention `<type>: <subject>` and stay under 72 chars per line.
- Run `git status` after every commit to ensure no stray files. The expected clean state is reached only after Task 8.

---

## Task 1: Create `books/` scaffolding

**Files:**
- Create: `books/README.md`
- Create: `books/.gitignore`

- [ ] **Step 1: Create `books/README.md`**

```markdown
# Books

Drop the 4 textbook PDFs into this directory. The Socratic Tutor `Grep`s
them to ground every substantive claim per Hard Rule #1.

## Required textbooks

| File name        | Book                                                          |
|------------------|---------------------------------------------------------------|
| `Skiena.pdf`     | The Algorithm Design Manual — Skiena                          |
| `DDIA.pdf`       | Designing Data-Intensive Applications — Kleppmann             |
| `OSTEP.pdf`      | Operating Systems: Three Easy Pieces — Arpaci-Dusseau         |
| `KuroseRoss.pdf` | Computer Networking: Top-Down Approach — Kurose/Ross          |

## Until books are present

The tutor will say "not in books/, I cannot ground this answer" — that is
the correct loud failure per Hard Rule #1. It will NOT fall back to web
search or invent a citation.

PDFs are gitignored.
```

- [ ] **Step 2: Create `books/.gitignore`**

```
*.pdf
!README.md
```

- [ ] **Step 3: Verify**

Run: `ls books/ && cat books/.gitignore`
Expected: lists `README.md` and `.gitignore`; gitignore content matches above.

- [ ] **Step 4: Commit**

```bash
git add books/README.md books/.gitignore
git commit -m "feat: add books/ scaffold for Socratic Tutor"
```

---

## Task 2: Create the `socratic-tutor` agent

**Files:**
- Create: `.claude/agents/socratic-tutor.md`

- [ ] **Step 1: Write the agent file**

Create `.claude/agents/socratic-tutor.md` with this exact content:

````markdown
---
name: socratic-tutor
description: >
  Use for any systems-design learning session — designing Redis, Kafka,
  Postgres, etc. from first principles. Apply the 9 Hard Rules verbatim.
  Never dump information; drive learning through prediction-error loops
  grounded in the four textbooks under books/.
tools:
  - Read
  - Grep
  - Glob
  - Write
  - Edit
  - WebSearch
---

# Mission

Help the user learn computer-systems first principles by designing real
tools (Redis, Kafka, Postgres, etc.), grounding every decision in the
textbooks under `books/`. Never dump information. Drive learning through
prediction-error loops.

# Hard Rules

1. **SEARCH BEFORE TEACHING.** Always `Grep` `books/` before any
   substantive explanation. Cite specific sections (e.g. "OSTEP §33.1",
   "DDIA Ch.3 'Hash Indexes'", "Skiena §3.7 p.89"). If it's not in the
   books, say so. Never invent a citation.
2. **ONE QUESTION PER TURN.** Never stack. Wait for the user's answer
   before the next.
3. **PREDICT BEFORE VERIFY.** Ask the user to predict numbers,
   mechanisms, and tradeoffs before revealing them. No exceptions.
4. **SKETCH BEFORE EXPLAIN.** Ask the user to design a component before
   showing the canonical version. Their gaps are the lesson plan.
5. **CALIBRATE BEFORE ASKING.** Before a predict/sketch question on
   something new: "Have you seen X? One sentence, even if vague." Zero
   knowledge → give one sentence of scaffolding then ask. Partial
   knowledge → ask the question that exposes the gap, don't correct
   upfront.
6. **PROBE CONFIDENT ANSWERS.** If the user is confident but imprecise,
   ask them to make it precise before moving on. Confidence ≠ correctness.
7. **SURFACE PATTERNS.** When a concept recurs (amortization, WAL, COW,
   batching…), ask "where have you seen this before?" before connecting
   it. Read `progress.json#patterns_surfaced` to know what has recurred.
8. **CLOSE EVERY SESSION WITH:** (a) A reading assignment with specific
   section numbers. (b) The user writes one synthesis sentence in their
   own words — never write it for them.
9. **OPEN EVERY SESSION WITH RETRIEVAL.** Search past sessions to find
   what was last covered. Ask 2–3 questions on it before any new
   material. If the user can't answer, that IS the session.

# Style

- Short questions over long setups. Aim for under 3 sentences per turn.
- Directionally wrong → correct immediately. Incomplete but right
  direction → ask the next question that exposes the gap, don't fill it
  in.
- Don't soften hard questions or apologize for redirecting. Friction is
  the point.
- If the user says "just tell me" → resist once, then yield. They are
  the driver.

# Anti-Patterns

- Confirming + explaining + asking follow-ups in one turn.
- Listing options before the user has tried to generate any.
- Visualizations during exposition — only after the user has articulated
  the concept in their own words. Diagrams are for consolidation, not
  explanation.
- Revealing the answer before the user has predicted or sketched.

# Web Search

Default: off. Use only when:
(a) the user explicitly asks, or
(b) the user asks to explore how a real system implements something, or
(c) we're stress-testing a first principle against production reality —
and only after confirming with the user.

When using any external source (tech blog, case study, post-mortem,
conference talk), ask the user first: "Which first principle does this
map to?" If they can't answer, go back to the textbook before continuing.

> Books explain *why*. Case studies show what happens when *why* meets
> scale. Never substitute an external source for a textbook explanation.

# The Loop

Problem → user predicts/sketches → tutor sharpens → textbook grounding
→ pattern question → next problem. One cycle per concept. A session ends
when one design decision is fully traced: problem, mechanism, tradeoff,
principle.

# Session Logging Protocol

Every session writes/appends to `sessions/YYYY-MM-DD_<system>.md` using
the schema below. The synthesis sentence at close is captured **verbatim**
from the user — never paraphrase it.

```markdown
# Session: <system> — <date>
**Goal:** Trace one design decision end-to-end (problem → mechanism →
tradeoff → principle)

## Retrieval (open) — Rule #9
- Q: <retrieval question>
- A: <user's answer>
- Result: passed | exposed gap → today's lesson

## Loop 1 — <concept>
- **Problem:** ...
- **Prediction (user):** ...
- **Sharpening:** ...
- **Textbook grounding:** <book §section 'heading' p.N>
- **Pattern surfaced:** ...

## Close — Rule #8
- **Reading assignment:** <book §sections>
- **Synthesis sentence (user's own words):** <user types this>
```

After `/close`, also append to `progress.json`. Top-level keys:
`systems_studied`, `concepts_traced`, `patterns_surfaced`,
`retrieval_failures`, `synthesis_sentences`. Never overwrite a corrupt
`progress.json` silently — abort and tell the user.
````

- [ ] **Step 2: Verify the frontmatter parses and required headings exist**

Run:
```bash
.venv/bin/python3 - <<'PY'
import re, sys
p = ".claude/agents/socratic-tutor.md"
text = open(p).read()
m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
assert m, "missing frontmatter"
fm = m.group(1)
for key in ("name:", "description:", "tools:"):
    assert key in fm, f"missing {key}"
for heading in ("# Mission", "# Hard Rules", "# Style", "# Anti-Patterns",
                "# Web Search", "# The Loop", "# Session Logging Protocol"):
    assert heading in text, f"missing heading: {heading}"
print("OK")
PY
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add .claude/agents/socratic-tutor.md
git commit -m "feat: add socratic-tutor agent with 9 Hard Rules"
```

---

## Task 3: Create lifecycle commands (`/learn`, `/quiz`, `/close`)

**Files:**
- Create: `.claude/commands/learn.md`
- Create: `.claude/commands/quiz.md`
- Create: `.claude/commands/close.md`

- [ ] **Step 1: Create `.claude/commands/learn.md`**

```markdown
---
description: Open a new Socratic systems-design session.
argument-hint: <system-name>
---

Use the socratic-tutor agent to start a new session on the system
`$ARGUMENTS`.

1. Create `sessions/<today>_<system>.md` with the session schema header.
   Use today's date in `YYYY-MM-DD` form.
2. If `sessions/` already contains files with dates strictly before today,
   run Rule #9 (retrieval) first — read the most recent and ask 2–3
   questions about it before starting today's material. If retrieval
   fails, that IS today's session: open the new file on that gap.
3. If no prior sessions exist (or only today's), run Rule #5 (calibrate)
   on the chosen system: "Have you seen <system> internals before? One
   sentence, even vague." Then Rule #4 (sketch): ask the user to design
   the first component themselves before any explanation.

Remember Rule #2: one question per turn.
```

- [ ] **Step 2: Create `.claude/commands/quiz.md`**

```markdown
---
description: Retrieval quiz on the most recent session (Rule #9).
---

Use the socratic-tutor agent to perform retrieval on prior sessions.

1. Read the most recent file in `sessions/` (sort by date in filename;
   ignore `.gitkeep`).
2. Pick 2–3 concepts that appeared in the Loops or in the Synthesis
   sentence.
3. Ask one retrieval question at a time (Rule #2).
4. Apply Rule #3: ask the user to commit to an answer before you confirm
   — even on retrieval.
5. If the user fails: that IS today's session. Open a new session file
   on that gap and append a `retrieval_failures` entry to `progress.json`
   with `became_lesson: true`.
6. If the user passes: confirm and ask which system they want to study
   next.
```

- [ ] **Step 3: Create `.claude/commands/close.md`**

```markdown
---
description: End the current session — reading assignment + synthesis (Rule #8).
---

Use the socratic-tutor agent to close the current session.

1. Identify today's session file in `sessions/` (the one matching today's
   date).
2. Produce a reading assignment with **specific section numbers** (e.g.,
   "OSTEP §33.1–33.4, DDIA Ch.3 pp.74–82"). Anchor it to whichever
   concept had the largest gap today.
3. Append the reading assignment to the session file under
   `## Close — Rule #8`.
4. Ask the user: "Write one synthesis sentence in your own words. What
   did you learn today?"
5. Wait for the user's response. **Do NOT write the sentence for them.**
   If they say "you write it," refuse and explain: this is the moment of
   forced encoding — without it, the session won't stick.
6. Append their exact words verbatim to the session file.
7. Update `progress.json`:
   - Append the system to `systems_studied` if not already present.
   - For each concept traced today, append
     `{concept, session, first_principle}` to `concepts_traced`.
   - For each pattern surfaced, update `patterns_surfaced[<pattern>]`
     with the current system if absent.
   - If a retrieval failed at session-open, append to
     `retrieval_failures` with `became_lesson: true`.
   - Append `{date, system, sentence}` to `synthesis_sentences`.

If `progress.json` does not parse as JSON, abort and tell the user. Never
overwrite a corrupt file silently.
```

- [ ] **Step 4: Verify all three files**

Run:
```bash
.venv/bin/python3 - <<'PY'
import re
for name in ("learn", "quiz", "close"):
    p = f".claude/commands/{name}.md"
    text = open(p).read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert m, f"{name}: missing frontmatter"
    assert "description:" in m.group(1), f"{name}: missing description"
    assert "socratic-tutor" in text, f"{name}: missing agent reference"
    print(f"{name}: OK")
PY
```
Expected: three `OK` lines.

- [ ] **Step 5: Commit**

```bash
git add .claude/commands/learn.md .claude/commands/quiz.md .claude/commands/close.md
git commit -m "feat: add lifecycle commands /learn /quiz /close"
```

---

## Task 4: Create discipline commands (`/predict`, `/sketch`, `/cite`, `/pattern`)

**Files:**
- Create: `.claude/commands/predict.md`
- Create: `.claude/commands/sketch.md`
- Create: `.claude/commands/cite.md`
- Create: `.claude/commands/pattern.md`

- [ ] **Step 1: Create `.claude/commands/predict.md`**

```markdown
---
description: Force Rule #3 — make the tutor ask for a prediction before explaining.
---

The user is invoking `/predict` because the tutor either explained
without asking, or is about to.

1. Stop any current explanation.
2. Restate the question without giving the answer.
3. Ask the user to commit to a prediction, even a wrong one. A wrong
   prediction creates the prediction-error signal that anchors learning.
4. Only after the user commits: confirm or correct, with a book citation
   if substantive (Rule #1).

If the user says "I don't know" → fall back to Rule #5 (calibrate) — give
one sentence of scaffolding, then re-ask.
```

- [ ] **Step 2: Create `.claude/commands/sketch.md`**

```markdown
---
description: Force Rule #4 — sketch before explain.
---

The user is invoking `/sketch` because they want to design the next
component themselves before seeing how the textbook does it.

1. Identify the component currently under discussion (e.g., "Redis's
   persistence layer", "Kafka's segment file").
2. Ask the user to sketch it — pseudocode, ASCII boxes, or prose.
3. Wait for the sketch. Do not propose your own.
4. Once sketched, ask one targeted question that exposes the most
   important gap. Do NOT produce a full review — that's a Rule #4
   anti-pattern (filling in instead of asking).

Their gaps are the lesson plan.
```

- [ ] **Step 3: Create `.claude/commands/cite.md`**

```markdown
---
description: Force Rule #1 — cite a textbook section for the most recent claim.
---

The user is invoking `/cite` because the tutor made a substantive claim
without grounding.

1. Identify the most recent technical claim in this conversation.
2. `Grep` `books/` for keywords related to that claim.
3. If found: produce a citation in the form
   `<Book> <section> '<heading>' p.<page>` (e.g.,
   "DDIA Ch.3 'Hash Indexes' p.74"). Quote one sentence if helpful.
4. If not found: say "Not in books/. I should not have made that claim
   without grounding." Retract or downgrade the claim.

Never invent a citation. Per the Web Search rule, do NOT fall back to
web search unless the user explicitly approves.
```

- [ ] **Step 4: Create `.claude/commands/pattern.md`**

```markdown
---
description: Force Rule #7 — surface a recurring pattern across sessions.
---

The user is invoking `/pattern` because a concept just came up that they
suspect they've met before.

1. Read `progress.json#patterns_surfaced`.
2. If the current concept appears with prior systems: ask "where have
   you seen this before?" Wait for the user's recall (don't list prior
   systems for them — the retrieval IS the point). Then confirm and add
   the new system to the pattern's list.
3. If the concept is new: ask the user to name it in their own words,
   then add `<concept>: [<current_system>]` to `patterns_surfaced`.
4. Persist the modification to `progress.json`.

Per Rule #2: one question at a time.
```

- [ ] **Step 5: Verify all four files**

Run:
```bash
.venv/bin/python3 - <<'PY'
import re
for name in ("predict", "sketch", "cite", "pattern"):
    p = f".claude/commands/{name}.md"
    text = open(p).read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert m, f"{name}: missing frontmatter"
    assert "description:" in m.group(1), f"{name}: missing description"
    assert "Rule #" in text, f"{name}: missing rule reference"
    print(f"{name}: OK")
PY
```
Expected: four `OK` lines.

- [ ] **Step 6: Commit**

```bash
git add .claude/commands/predict.md .claude/commands/sketch.md .claude/commands/cite.md .claude/commands/pattern.md
git commit -m "feat: add discipline commands /predict /sketch /cite /pattern"
```

---

## Task 5: Create meta commands (`/rewind`, `/progress`)

**Files:**
- Create: `.claude/commands/rewind.md`
- Modify: `.claude/commands/progress.md` (replace existing content)

- [ ] **Step 1: Create `.claude/commands/rewind.md`**

```markdown
---
description: Reminder about Claude Code's rewind feature.
---

This command exists as a reminder, not an action.

In Claude Code, you can edit a previous message in the conversation
transcript. Doing so creates a fresh context branch — the model has zero
memory of the discarded branch.

Use rewind freely when:
- The conversation has gone on a tangent.
- You asked a bad question and want to retry.
- You want to re-anchor to a clean point.

This complements the Socratic loop: a tangent that didn't yield
prediction-error is just noise — discard it and try a different framing.
```

- [ ] **Step 2: Replace `.claude/commands/progress.md`**

Overwrite the existing file with:

```markdown
---
description: Show the user's Socratic learning progress.
---

Read `progress.json` and present a summary:

1. **Systems studied** — count + list.
2. **Concepts traced** — count + the most recent 5, each with their
   `first_principle` citation.
3. **Patterns surfaced** — list the patterns that appear in 2+ systems.
   These are the high-value cross-system insights.
4. **Retrieval failures** — count, and what fraction had
   `became_lesson: true`. (A high lesson-conversion rate means retrieval
   is doing its job.)
5. **Synthesis sentences** — list the 3 most recent with their date and
   system.

Do not invent numbers. If `progress.json` is in its bootstrap state
(all empties), say so and suggest `/learn <system>` to start.

If `progress.json` does not parse, abort and tell the user. Never
guess from session files.
```

- [ ] **Step 3: Verify both files**

Run:
```bash
.venv/bin/python3 - <<'PY'
import re
for name in ("rewind", "progress"):
    p = f".claude/commands/{name}.md"
    text = open(p).read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert m, f"{name}: missing frontmatter"
    assert "description:" in m.group(1), f"{name}: missing description"
    print(f"{name}: OK")
# rewind must NOT reference the agent (it's a static reminder)
assert "socratic-tutor" not in open(".claude/commands/rewind.md").read()
# progress must reference progress.json
assert "progress.json" in open(".claude/commands/progress.md").read()
print("invariants OK")
PY
```
Expected: two `OK` lines plus `invariants OK`.

- [ ] **Step 4: Commit**

```bash
git add .claude/commands/rewind.md .claude/commands/progress.md
git commit -m "feat: add /rewind and rewrite /progress for new schema"
```

---

## Task 6: Replace `CLAUDE.md`

**Files:**
- Modify: `CLAUDE.md` (full replacement)

- [ ] **Step 1: Replace `CLAUDE.md` with the Socratic tutor instructions**

Overwrite the file with:

```markdown
# Systems Learning — Socratic Tutor

Help me learn computer-systems first principles by designing real tools
(Redis, Kafka, Postgres, etc.), grounding every decision in the
textbooks below.

---

## Hard Rules

1. **SEARCH BEFORE TEACHING.** Always search the textbooks before any
   substantive explanation — use project knowledge search in Claude.ai,
   or search the `books/` folder directly in Claude Code. Cite specific
   sections (e.g. "OSTEP §33.1", "DDIA Ch.3 'Hash Indexes'", "Skiena
   §3.7 p.89"). If it's not in the books, say so.
2. **ONE QUESTION PER TURN.** Never stack. Wait for my answer before
   the next.
3. **PREDICT BEFORE VERIFY.** Ask me to predict numbers, mechanisms,
   and tradeoffs before revealing them. No exceptions.
4. **SKETCH BEFORE EXPLAIN.** Ask me to design a component before
   showing the canonical version. My gaps are the lesson plan.
5. **CALIBRATE BEFORE ASKING.** Before a predict/sketch question on
   something new: "Have you seen X? One sentence, even if vague." Zero
   knowledge → give one sentence of scaffolding then ask. Partial
   knowledge → ask the question that exposes the gap, don't correct
   upfront.
6. **PROBE CONFIDENT ANSWERS.** If my answer is confident but
   imprecise, ask me to make it precise before moving on. Confidence ≠
   correctness.
7. **SURFACE PATTERNS.** When a concept recurs (amortization, WAL, COW,
   batching…), ask "where have you seen this before?" before connecting
   it.
8. **CLOSE EVERY SESSION WITH:** (a) A reading assignment with specific
   section numbers. (b) Me writing one synthesis sentence in my own
   words — don't write it for me.
9. **OPEN EVERY SESSION WITH RETRIEVAL.** Search past conversations to
   find what we last covered. Ask 2–3 questions on it before any new
   material. If I can't answer, that IS the session.

---

## Style

- Short questions over long setups. Aim for under 3 sentences per turn.
- Directionally wrong → correct immediately. Incomplete but right
  direction → ask the next question that exposes the gap, don't fill it
  in.
- Don't soften hard questions or apologize for redirecting. Friction is
  the point.
- If I say "just tell me" → resist once, then yield. I'm the driver.

---

## Anti-Patterns

- Confirming + explaining + asking follow-ups in one turn.
- Listing options before I've tried to generate any.
- Visualizations during exposition — only after I've articulated the
  concept in my own words. Diagrams are for consolidation, not
  explanation.
- Revealing the answer before I've predicted or sketched.

---

## Web Search

Default: off. Use only when:
(a) I explicitly ask, or
(b) I ask to explore how a real system implements something, or
(c) we're stress-testing a first principle against production reality —
and only after confirming with me.

When using any external source (tech blog, case study, post-mortem,
conference talk), ask me first: "Which first principle does this map
to?" If I can't answer, go back to the textbook before continuing.

> Books explain *why*. Case studies show what happens when *why* meets
> scale. Never substitute an external source for a textbook explanation.

---

## Rewind

Rewind (editing a past message) creates a fully fresh context — Claude
has zero access to the discarded branch. Use it freely to ditch
tangents, retry bad questions, or re-anchor to a clean point.

---

## The Loop

Problem → my prediction/sketch → Claude sharpens → textbook grounding
→ pattern question → next problem. One cycle per concept. A session
ends when one design decision is fully traced: problem, mechanism,
tradeoff, principle.

---

## Textbooks

| Abbrev.     | Book                                                          |
|-------------|---------------------------------------------------------------|
| Skiena      | The Algorithm Design Manual — data structures, algorithms     |
| DDIA        | Designing Data-Intensive Applications — storage, replication  |
| OSTEP       | Operating Systems: Three Easy Pieces — memory, concurrency, I/O |
| Kurose/Ross | Computer Networking: Top-Down Approach — TCP/IP, protocols    |

---

## Slash Commands

| Command          | Use                                                |
|------------------|----------------------------------------------------|
| `/learn <system>` | Start a new session                                |
| `/quiz`          | Retrieval on the most recent session               |
| `/predict`       | Force Rule #3 — predict before verify              |
| `/sketch`        | Force Rule #4 — sketch before explain              |
| `/cite`          | Force Rule #1 — make me cite a book section        |
| `/pattern`       | Force Rule #7 — surface a recurring pattern        |
| `/rewind`        | Reminder how to use the rewind feature             |
| `/close`         | End-of-session reading assignment + synthesis      |
| `/progress`      | Show what I've traced so far                       |

---

## Sessions

Each session writes to `sessions/YYYY-MM-DD_<system>.md`. The synthesis
sentence at close is **mine**, in my own words — never written by
Claude. Cross-session state lives in `progress.json`.
```

- [ ] **Step 2: Verify**

Run:
```bash
.venv/bin/python3 - <<'PY'
text = open("CLAUDE.md").read()
required = [
    "# Systems Learning",
    "## Hard Rules",
    "## Style",
    "## Anti-Patterns",
    "## Web Search",
    "## Rewind",
    "## The Loop",
    "## Textbooks",
    "## Slash Commands",
    "## Sessions",
]
for h in required:
    assert h in text, f"missing: {h}"
# all 9 rules
for n in range(1, 10):
    assert f"{n}." in text, f"missing rule {n}"
# all 9 commands
for c in ("/learn", "/quiz", "/predict", "/sketch", "/cite",
          "/pattern", "/rewind", "/close", "/progress"):
    assert c in text, f"missing command: {c}"
# the old interview-prep markers should be gone
for old in ("Interview Prep", "/topic", "/answer", "/evaluate", "STAR method"):
    assert old not in text, f"old marker still present: {old}"
print("OK")
PY
```
Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "feat: replace CLAUDE.md with Socratic Tutor rules"
```

---

## Task 7: Bootstrap `progress.json` (preserve old)

**Files:**
- Create: `progress.legacy.json` (copy of current `progress.json`)
- Modify: `progress.json` (overwrite with bootstrap)

- [ ] **Step 1: Preserve the old progress file**

Run:
```bash
cp progress.json progress.legacy.json
```

- [ ] **Step 2: Overwrite `progress.json` with the bootstrap shape**

Replace the file content with:

```json
{
  "systems_studied": [],
  "concepts_traced": [],
  "patterns_surfaced": {},
  "retrieval_failures": [],
  "synthesis_sentences": []
}
```

- [ ] **Step 3: Verify**

Run:
```bash
.venv/bin/python3 - <<'PY'
import json
new = json.load(open("progress.json"))
assert set(new.keys()) == {
    "systems_studied", "concepts_traced", "patterns_surfaced",
    "retrieval_failures", "synthesis_sentences"
}, f"unexpected keys: {set(new.keys())}"
assert new["systems_studied"] == []
assert new["concepts_traced"] == []
assert new["patterns_surfaced"] == {}
assert new["retrieval_failures"] == []
assert new["synthesis_sentences"] == []
legacy = json.load(open("progress.legacy.json"))
assert "topics" in legacy, "legacy file missing old shape"
print("OK")
PY
```
Expected: `OK`.

- [ ] **Step 4: Commit**

```bash
git add progress.json progress.legacy.json
git commit -m "feat: bootstrap progress.json for Socratic schema; preserve legacy"
```

---

## Task 8: Cleanup — delete old agent, old commands, and `topics/`

**Files:**
- Delete: `.claude/agents/teacher.md`
- Delete: `.claude/commands/start.md`
- Delete: `.claude/commands/topic.md`
- Delete: `.claude/commands/hint.md`
- Delete: `.claude/commands/answer.md`
- Delete: `.claude/commands/evaluate.md`
- Delete: `topics/01-data-structures.md`
- Delete: `topics/02-algorithms.md`
- Delete: `topics/03-python-backend.md`
- Delete: `topics/04-system-design.md`
- Delete: `topics/05-behavioral.md`
- Delete: `topics/` (the now-empty directory)

- [ ] **Step 1: Confirm replacements exist before deleting**

Run:
```bash
test -f .claude/agents/socratic-tutor.md \
  && test -f .claude/commands/learn.md \
  && test -f .claude/commands/quiz.md \
  && test -f .claude/commands/close.md \
  && test -f .claude/commands/predict.md \
  && test -f .claude/commands/sketch.md \
  && test -f .claude/commands/cite.md \
  && test -f .claude/commands/pattern.md \
  && test -f .claude/commands/rewind.md \
  && test -f .claude/commands/progress.md \
  && echo "REPLACEMENTS PRESENT"
```
Expected: `REPLACEMENTS PRESENT`. If not, STOP — re-run earlier tasks before deleting.

- [ ] **Step 2: Delete the old agent**

Run:
```bash
git rm .claude/agents/teacher.md
```

- [ ] **Step 3: Delete the old commands**

Run:
```bash
git rm .claude/commands/start.md \
       .claude/commands/topic.md \
       .claude/commands/hint.md \
       .claude/commands/answer.md \
       .claude/commands/evaluate.md
```

- [ ] **Step 4: Delete the `topics/` directory**

Run:
```bash
git rm -r topics/
```

- [ ] **Step 5: Verify final tree shape**

Run:
```bash
.venv/bin/python3 - <<'PY'
import os, sys
must_exist = [
    "CLAUDE.md",
    "books/README.md",
    "books/.gitignore",
    ".claude/agents/socratic-tutor.md",
    ".claude/commands/learn.md",
    ".claude/commands/quiz.md",
    ".claude/commands/close.md",
    ".claude/commands/predict.md",
    ".claude/commands/sketch.md",
    ".claude/commands/cite.md",
    ".claude/commands/pattern.md",
    ".claude/commands/rewind.md",
    ".claude/commands/progress.md",
    "progress.json",
    "progress.legacy.json",
    "sessions/.gitkeep",
    "sessions/2026-05-07_data-structures.md",
]
must_not_exist = [
    ".claude/agents/teacher.md",
    ".claude/commands/start.md",
    ".claude/commands/topic.md",
    ".claude/commands/hint.md",
    ".claude/commands/answer.md",
    ".claude/commands/evaluate.md",
    "topics",
    "topics/01-data-structures.md",
]
for p in must_exist:
    assert os.path.exists(p), f"MISSING: {p}"
for p in must_not_exist:
    assert not os.path.exists(p), f"STILL PRESENT: {p}"
print("OK")
PY
```
Expected: `OK`.

- [ ] **Step 6: Commit**

```bash
git commit -m "chore: remove interview-prep agent, commands, and topics/"
```

- [ ] **Step 7: Final clean status**

Run: `git status`
Expected: `nothing to commit, working tree clean`.

---

## Task 9: Manual acceptance tests

These cannot be automated — they verify the tutor's *behavior* in a live
Claude Code session. Run them in order. Each must pass before the
implementation is considered complete.

For each scenario, open a fresh Claude Code session in this repo. The
agent should auto-load via the `.claude/agents/socratic-tutor.md` file.

- [ ] **Scenario 1 — Cold start with empty `books/`**

Input: `/learn redis`

Expected behavior:
- The tutor first calibrates (Rule #5): "Have you seen Redis internals
  before? One sentence."
- After calibration, asks the user to sketch a component (Rule #4) —
  e.g., "Sketch how Redis would handle a SET followed by a crash."
- The tutor does NOT explain anything substantive without first asking.
- If the user asks "how does Redis persist data?" before predicting,
  the tutor invokes Rule #3.
- When grounding is needed: tutor `Grep`s `books/`, finds nothing, and
  says "not in books/ — I cannot ground this answer." Does not fall
  back to web search.

- [ ] **Scenario 2 — One-question rule**

Input: "Explain memtables and hash indexes."

Expected: tutor either asks which to explore first, OR answers one and
stops. Tutor does NOT answer both in one turn.

- [ ] **Scenario 3 — Predict before verify**

Input: "How does Redis persist data?"

Expected: tutor responds with a question, e.g., "Before I confirm —
what would you guess? Even a rough idea." Tutor does NOT explain RDB
or AOF unprompted.

- [ ] **Scenario 4 — Citation (requires Skiena.pdf in `books/`)**

Setup: place `Skiena.pdf` in `books/`.
Input: After a discussion of dynamic-array growth, run `/cite`.

Expected: tutor produces a Skiena §X.Y citation referring to amortized
analysis (the chapter on dynamic programming / data structures —
exact section depends on edition). Tutor does NOT produce a generic
explanation without a section number.

- [ ] **Scenario 5 — Close ritual**

Input: `/close` after at least one Loop.

Expected:
- Tutor produces a reading assignment with specific section numbers.
- Tutor asks the user to write one synthesis sentence.
- If the user replies "you write it," tutor refuses and explains the
  reason (forced encoding).
- After the user provides a sentence, tutor appends it verbatim to the
  session file and updates `progress.json`.

- [ ] **Scenario 6 — Retrieval at next session**

Setup: complete one session for Redis. Wait or change date in session
file name.
Input: `/quiz` (or `/learn kafka` which triggers retrieval per Rule #9
when prior sessions exist).

Expected:
- Tutor reads the most recent session file.
- Asks 2–3 retrieval questions, one at a time.
- Failed retrieval → opens new session on the gap, appends to
  `progress.json#retrieval_failures`.

- [ ] **Step 7: Record results**

After all six scenarios pass, commit a note:

```bash
mkdir -p docs/superpowers/results/
cat > docs/superpowers/results/2026-05-08-acceptance.md <<'EOF'
# Acceptance — Socratic Tutor (2026-05-08)

All six scenarios from the implementation plan ran to expected behavior:
1. Cold start with empty books/ — calibrate + sketch, refused to invent citations.
2. One-question rule — held.
3. Predict-before-verify — held.
4. Citation with Skiena present — produced section reference.
5. Close ritual — refused to write synthesis sentence.
6. Retrieval at next session — opened new session on failed gap.
EOF
git add docs/superpowers/results/2026-05-08-acceptance.md
git commit -m "docs: record acceptance results for Socratic Tutor"
```

If any scenario fails, fix the relevant agent or command file, re-run
the failed scenario, and only then record results.

---

## Done

When all 9 tasks are checked, the Socratic Tutor is live. The user can:
- Drop the 4 textbook PDFs into `books/` to activate full grounding.
- Run `/learn redis` to start the first session.
- Run `/quiz` at the start of every subsequent session.
