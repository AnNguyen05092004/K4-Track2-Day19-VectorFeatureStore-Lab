# Bonus Challenge — Build Your Own AI Memory

> Tiếng Việt: [`BONUS-CHALLENGE.md`](BONUS-CHALLENGE.md)

**Type:** Brainstorming + creative session — separate from the core lab, fully optional.
**Role:** You're an AI engineer designing a *memory system* for a personal assistant.
**Effort target:** 4–6 hours focused. Pairs (2–3 people) encouraged. Brainstorm first, code second.
**Vibe coding encouraged:** AI handles boilerplate; *you* write the architecture decisions.

This bonus is for students who want to push past the rote deliverable and
build something *creative + showcase-able*. **No formal grade** (20 bonus
points optional in `rubric.md`). The real reward is written instructor
feedback on your *judgment*, plus a portfolio piece.

---

## The Brief

You're building a **personal AI assistant for Vietnamese users** (think
ChatGPT + NotebookLM, personal-scale, Vietnamese-first). The assistant must
*remember*:

- **Episodic memory** — past conversations, documents the user has read,
  user-saved notes. The more accumulated, the smarter retrieval must be.
  → **Vector Store** (lab §1–§3).
- **Stable user profile** — preferred language (vi/en/mix), reading speed,
  topic affinity (cloud / AI / law / medicine / ...), active hours.
  → **Feature Store** (lab §4).
- **Recent activity** — queries from the last hour, topic spikes, fatigue
  patterns (longer queries late at night?). → **Streaming feature view**
  (lab §6 streaming pipeline).

Task: **design and build a minimal POC combining all three**. Document is
the primary deliverable; code is minimal-just-enough to demo your decisions.

---

## Deliverables (in `bonus/` of your repo)

### 1. `bonus/ARCHITECTURE.md` (primary, ~600–1000 words)

Must include:

- **Architecture diagram** (ascii / Mermaid / scanned hand-drawing all OK).
  Must show: data flow between episodic memory (vector) and stable profile
  (feature store), and final LLM context assembly.

- **3 architecture decisions with explicit tradeoffs:**
  1. **Chunking strategy** — how do you chunk episodic memory?
     Per-message? Per-conversation? Semantic break? Token count? Cover
     tradeoffs across *retrieval quality vs storage cost vs context window*.
  2. **Feature schema** — what user profile features? Per feature: entity,
     ttl, source. Pattern: tabular features (simple) vs embedding features
     (latent prefs from history)? Why this pattern?
  3. **Freshness strategy** — when the user finishes reading a new doc, how
     long until the recall query "what does the assistant know about me?"
     reflects it? Sub-second (streaming Push API) vs 5-min (batch refresh)
     vs daily? Pick 3 use cases with different freshness needs.

- **Reject one alternative explicitly with a reason** — "I considered X but
  chose Y because Z". E.g., "I considered storing episodic memory as an
  embedding feature view in the feature store, but split it into a vector
  store because the re-index cycles differ (new memory hourly vs profile
  weekly)".

- **Vietnamese-context considerations** — code-switching (vi/en mix),
  phonetic typos, NLP tokenizer choice (pyvi / underthesea / whitespace
  split tradeoff)?

### 2. `bonus/agent.py` (~80–150 lines)

One agent class with 2 minimum methods:

```python
class HybridMemoryAgent:
    def remember(self, text: str, user_id: str = "u_001") -> None:
        """Add a new piece of episodic memory for this user."""

    def recall(self, query: str, user_id: str = "u_001") -> str:
        """Retrieve top-K memories + user profile features → return assembled context."""
```

Vibe code freely here — mechanical, follow patterns from NB2 + NB4. Don't
optimize speed; optimize *clarity*.

### 3. `bonus/demo.py` (5-query script)

Five demo queries:

1. Simple lookup (vector only): "What have I read about Kubernetes?"
2. Profile-needed: "Recommend what to read next" (uses `topic_affinity`)
3. Fresh-activity: "What am I focused on lately?" (uses `queries_last_hour`)
4. Paraphrase (vector wins): "Documents about scaling infrastructure?"
5. Mixed (hybrid + profile): "Give me a cloud security summary"

Output: print the assembled context per query.

---

## Self-checklist for strong submissions

- [ ] Architecture diagram is clear — doesn't need to be pretty, needs to be right.
- [ ] Each of the 3 decisions has an **explicit tradeoff** (X vs Y, why X) —
      not "X is good".
- [ ] At least one decision shows *Vietnamese-context awareness* (tokenizer,
      code-switching, or privacy/Decree-13 angle).
- [ ] Code runs — `python bonus/demo.py` exits 0.
- [ ] Architecture decisions tie back **clearly to lab concepts** — PIT
      join, TTL, streaming, RRF — at least one each.
- [ ] Honest limitations — write a "What this POC doesn't handle yet"
      paragraph (privacy isolation, encryption, multi-device sync, etc.).

---

## Format

- **Pairs / triples encouraged** — credit contributors at top of `bonus/ARCHITECTURE.md`.
- Optional vibe coding workflow log (~100 words): "the prompt that worked
  best, the prompt that failed". Not graded; instructor rewards judgment,
  not hand-typed lines.

## Submission

Add `bonus/` folder to your public Lab 19 repo (same repo as the core lab).
Mention bonus in `submission/REFLECTION.md`. Grader reviews from the same
public URL on LMS.

---

## Optional extension topics

If the 3 deliverables come quickly:

- **Multi-user privacy isolation** — how does user A only see their own
  memories? Qdrant filter by user_id payload, per-user collection,
  per-user encryption? Tradeoffs?
- **Memory decay / forgetting** — TTL on episodic memory? Cohort pruning?
  "Untouched 30 days → archive"?
- **Personalization re-ranking** — after vector top-50, re-rank using
  feature-store user profile (boost docs in `topic_affinity`)? RRF with 3
  retrievers instead of 2.
- **Memory consolidation** — collapse 5 similar memories into 1 weekly
  summary (LLM-driven)? When does it trigger?

Remember: not all of these. **One good decision + one runnable POC** beats
five half-finished ideas.
