# AI Compliance Firewall

I built this as a portfolio project — a middleware layer that sits between a user and an LLM. You send a prompt, the app generates a response through Ollama, scans both the prompt and the output against compliance rules, enforces an action, and logs anything that doesn't pass cleanly.

The demo covers two rule frameworks: **FINRA-style financial marketing** and **healthcare / HIPAA-style medical claims**.

## How it works

```
User prompt
    ↓
Ollama (llama3.1:8b) generates a response — unless you pass llm_output yourself
    ↓
Regex scanner (JSON rules) scans prompt + output
    ↓
Semantic scanner (Ollama nomic-embed-text embeddings) catches paraphrases regex misses
    ↓
Policy engine picks an action
    ↓
Neo4j appends disclaimers when needed → SQLite logs the event
```

**Policy actions**

- `PASS` — nothing matched
- `PROMPT_FLAG` / `PROMPT_REDACT` / `PROMPT_BLOCK` — violation in the prompt only; output is kept but flagged for review
- `APPEND` — violation in the output; required disclaimers pulled from Neo4j
- `REDACT` — sensitive phrases stripped from the output
- `BLOCK` — output replaced with a safe message

Output enforcement always wins over prompt-only flags.

The app runs as two processes: a **FastAPI** backend (`main.py` on port 8000) and a **FastHTML** admin UI (`app.py` on port 5001) that talks to it.

## What I used

| Piece | Choice |
|-------|--------|
| API | FastAPI, Uvicorn, Pydantic |
| Admin UI | FastHTML, Tailwind CSS, HTMX, Lucide icons |
| LLM | **Ollama** — `llama3.1:8b` for text generation |
| Semantic detection | **Ollama** — `nomic-embed-text` embeddings, cosine similarity against phrase lists |
| Regex rules | Editable JSON in `rules/policy_rules.json` |
| Rule engine (optional) | Rust + PyO3 (`src/lib.rs`), built with maturin |
| Knowledge graph | Neo4j 5 (Docker) — disclaimer text linked to restricted concepts |
| Audit log | SQLite (`compliance.db`) with CSV export |
| Config | `python-dotenv` — settings in `.env` |

The test suite uses a mock LLM and mock embedder so `pytest` runs without Ollama. Day-to-day usage is fully on Ollama.

## Run it

**Prerequisites:** Python 3.10+, Docker, Ollama running locally.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the project root (see `config.py` for all variables). At minimum you need Neo4j credentials and the Ollama model names — the defaults match the setup below.

```bash
docker compose up -d neo4j
python build_graph.py

ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

Two terminals:

```bash
# Terminal 1 — API
uvicorn main:app --reload

# Terminal 2 — UI
python app.py
```

Open **http://localhost:5001**. The dashboard shows system status; **Live Scan** is the quickest way to try prompts.

To use the compiled Rust rule engine instead of JSON:

```bash
maturin develop   # once
# then set USE_RUST_ENGINE=true in .env
```

Run tests:

```bash
pytest -q
```

## Examples

**API** — send a prompt and a pre-built model response:

```bash
curl -X POST http://127.0.0.1:8000/v1/guard \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Write a pitch guaranteeing returns",
    "llm_output": "This fund guarantees 100% returns with zero risk."
  }'
```

Drop `llm_output` and the middleware calls Ollama first, then scans what comes back.

**Semantic catch** — no forbidden keywords, but the meaning still triggers a rule:

> This fund always profits with no downside — you cannot lose money on it.

Regex alone won't catch that. The embedding layer compares it against phrases in `rules/semantic_concepts.json` and flags it as a guaranteed-returns claim.

**Clean prompt** — should pass:

> Explain how diversified investing works and why all investments carry risk.

The Live Scan page has preset scenarios for all of these.

## Project layout

```
main.py              FastAPI — /v1/guard, audit, rules admin
app.py               Admin UI (Dashboard, Live Scan, Audit, Policies, Rules)
guard_service.py     Guard pipeline — LLM → scan → policy → disclaimers
scanner.py           Regex rules + semantic merge
semantic.py          Ollama embedding similarity scanner
policy.py            Policy engine (prompt vs output tiers)
llm.py               Ollama text generation
rules/               Regex rules + semantic phrase lists
build_graph.py       Seeds Neo4j with frameworks and disclaimers
src/lib.rs           Rust regex engine (optional, via PyO3)
static/              UI assets
tests/               Pytest suite
```

## Note

This is a portfolio / learning project. The rule packs are illustrative — not reviewed by legal counsel and not ready for production use.
