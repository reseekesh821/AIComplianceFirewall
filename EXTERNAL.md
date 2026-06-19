# What requires help outside this codebase

This project is an enterprise-shaped **proof-of-concept**. The following need people or services beyond code:

## Legal and compliance (required for real sales)

- **Legal counsel** to approve rule definitions, disclaimers, and enforcement actions
- **Regulatory mapping** (FINRA, SEC, HIPAA, state insurance rules) tied to official text
- **Customer contracts** and liability language ("risk reduction" not "zero hallucination")

## Enterprise operations

- **SSO / identity provider** (Okta, Azure AD) for production login — not built in POC
- **Production hosting** (AWS, GCP, Azure) with HA, backups, and security review
- **SOC 2 / pen test** if selling to banks or large health systems
- **Postgres or cloud audit store** with retention policies (SQLite is for local POC)

## Detection depth

- **Semantic layer (Phase 2):** local Ollama embeddings compare text to concept phrase lists in `rules/semantic_concepts.json`. Free, no API keys. Tune threshold via `SEMANTIC_THRESHOLD`.
- **Human review team** and workflow SLAs for flagged prompts in production

## Integrations

- **Customer LLM endpoints** (OpenAI, Azure OpenAI, Bedrock) — `LLM_PROVIDER=ollama|mock` today; OpenAI-compatible adapter is a small code add when credentials exist
- **SIEM / ticketing** (Splunk, Jira) for alert routing

## What Phase 1 already covers in code

- Middleware API (`POST /v1/guard`)
- JSON rule pack with admin GET/PUT
- Pluggable LLM (Ollama + mock)
- Policy engine (prompt + output tiers)
- Neo4j disclaimers, SQLite audit, CSV export
- Admin dashboard UI

When arranging outside help, prioritize **legal review of one rule pack** and **one pilot user** before scaling infra.
