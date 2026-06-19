import csv
import io
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import requests
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from neo4j import GraphDatabase
from pydantic import BaseModel, Field

from config import Settings, get_settings
from guard_service import GuardResponse, run_guard
from policy import PolicyResult
from scanner import get_scanner
from semantic import get_semantic_scanner

neo4j_driver = None


def init_audit_db(sqlite_file: str) -> None:
    conn = sqlite3.connect(sqlite_file)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS compliance_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT,
            timestamp TEXT,
            user_prompt TEXT,
            raw_llm_output TEXT,
            triggered_concepts TEXT,
            triggered_categories TEXT,
            action_taken TEXT,
            final_output TEXT,
            policy_version TEXT
        )
        """
    )
    cursor.execute("PRAGMA table_info(compliance_logs)")
    existing = {row[1] for row in cursor.fetchall()}
    migrations = {
        "request_id": "TEXT",
        "triggered_concepts": "TEXT",
        "action_taken": "TEXT",
        "final_output": "TEXT",
        "policy_version": "TEXT",
    }
    for column, col_type in migrations.items():
        if column not in existing:
            cursor.execute(f"ALTER TABLE compliance_logs ADD COLUMN {column} {col_type}")
    conn.commit()
    conn.close()


def log_compliance_event(
    sqlite_file: str,
    request_id: str,
    prompt: str,
    llm_output: str,
    result: PolicyResult,
    policy_version: str,
) -> None:
    conn = sqlite3.connect(sqlite_file)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO compliance_logs (
            request_id, timestamp, user_prompt, raw_llm_output,
            triggered_concepts, triggered_categories, action_taken, final_output,
            policy_version
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            request_id,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            prompt,
            llm_output,
            ", ".join(result.concepts),
            ", ".join(result.categories),
            result.action,
            result.final_output,
            policy_version,
        ),
    )
    conn.commit()
    conn.close()


def fetch_audit_stats(sqlite_file: str) -> dict:
    conn = sqlite3.connect(sqlite_file)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM compliance_logs")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT action_taken, COUNT(*) FROM compliance_logs GROUP BY action_taken")
    by_action = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return {
        "total_events": total,
        "by_action": by_action,
        "blocks": by_action.get("BLOCK", 0),
        "append": by_action.get("APPEND", 0),
        "redact": by_action.get("REDACT", 0),
        "prompt_marketing": by_action.get("PROMPT_FLAG", 0),
        "prompt_clinical": by_action.get("PROMPT_REDACT", 0),
        "prompt_high_risk": by_action.get("PROMPT_BLOCK", 0),
        "prompt_flags": (
            by_action.get("PROMPT_FLAG", 0)
            + by_action.get("PROMPT_REDACT", 0)
            + by_action.get("PROMPT_BLOCK", 0)
        ),
    }


def fetch_audit_logs(sqlite_file: str, limit: int = 50, action: str | None = None) -> list[dict]:
    conn = sqlite3.connect(sqlite_file)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if action:
        cursor.execute(
            """
            SELECT id, request_id, timestamp, user_prompt, triggered_concepts,
                   triggered_categories, action_taken, final_output, policy_version
            FROM compliance_logs WHERE action_taken = ? ORDER BY id DESC LIMIT ?
            """,
            (action, limit),
        )
    else:
        cursor.execute(
            """
            SELECT id, request_id, timestamp, user_prompt, triggered_concepts,
                   triggered_categories, action_taken, final_output, policy_version
            FROM compliance_logs ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def fetch_audit_log_by_id(sqlite_file: str, log_id: int) -> dict | None:
    conn = sqlite3.connect(sqlite_file)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, request_id, timestamp, user_prompt, raw_llm_output,
               triggered_concepts, triggered_categories, action_taken, final_output,
               policy_version
        FROM compliance_logs WHERE id = ?
        """,
        (log_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def settings_dep() -> Settings:
    return get_settings()


def require_api_key(
    settings: Settings = Depends(settings_dep),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global neo4j_driver
    settings = get_settings()
    init_audit_db(settings.sqlite_file)
    get_scanner(Path(settings.rules_file))
    if settings.semantic_enabled:
        try:
            get_semantic_scanner(settings).warm_up()
        except Exception:
            pass
    neo4j_driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    yield
    if neo4j_driver is not None:
        neo4j_driver.close()


app = FastAPI(
    title="Neuro-Symbolic Compliance Middleware",
    description="Enterprise LLM output guardrail — scan, enforce, audit.",
    lifespan=lifespan,
)


class GuardRequest(BaseModel):
    prompt: str
    llm_output: str | None = Field(
        default=None,
        description="Optional. If omitted, middleware calls the configured LLM.",
    )


class RulesUpdate(BaseModel):
    version: str
    updated_at: str
    rules: list[dict]


def _guard_to_response(guard: GuardResponse) -> dict:
    return {
        "request_id": guard.request_id,
        "status": guard.status,
        "action": guard.action,
        "concepts": guard.concepts,
        "categories": guard.categories,
        "prompt_concepts": guard.prompt_concepts,
        "output_concepts": guard.output_concepts,
        "prompt_flagged": guard.prompt_flagged,
        "final_output": guard.final_output,
        "policy_version": guard.policy_version,
    }


def _execute_guard(request: GuardRequest, settings: Settings) -> GuardResponse:
    guard = run_guard(settings, request.prompt, request.llm_output, neo4j_driver)
    if guard.action != "PASS" and guard.action != "ERROR":
        log_compliance_event(
            settings.sqlite_file,
            guard.request_id,
            request.prompt,
            guard.raw_llm_output,
            PolicyResult(
                status=guard.status,
                action=guard.action,
                final_output=guard.final_output,
                concepts=guard.concepts,
                categories=guard.categories,
                prompt_concepts=guard.prompt_concepts,
                output_concepts=guard.output_concepts,
                prompt_flagged=guard.prompt_flagged,
            ),
            guard.policy_version,
        )
    return guard


@app.post("/v1/guard", response_model=GuardResponse)
def guard_v1(request: GuardRequest, _: None = Depends(require_api_key)):
    """Enterprise middleware: pass prompt only, or prompt + pre-generated LLM output."""
    settings = get_settings()
    return _execute_guard(request, settings)


@app.post("/generate")
def generate(request: GuardRequest, _: None = Depends(require_api_key)):
    """Legacy demo endpoint — same pipeline as /v1/guard."""
    settings = get_settings()
    guard = _execute_guard(request, settings)
    return _guard_to_response(guard)


@app.get("/admin/rules")
def get_rules(_: None = Depends(require_api_key)):
    settings = get_settings()
    scanner = get_scanner(Path(settings.rules_file))
    return {
        "version": scanner.pack.version,
        "updated_at": scanner.pack.updated_at,
        "rules": scanner.pack.rules,
        "engine": "rust" if settings.use_rust_engine else "json",
    }


@app.put("/admin/rules")
def update_rules(body: RulesUpdate, _: None = Depends(require_api_key)):
    settings = get_settings()
    if settings.use_rust_engine:
        raise HTTPException(
            status_code=400,
            detail="Rule edits require USE_RUST_ENGINE=false (JSON scanner).",
        )
    scanner = get_scanner(Path(settings.rules_file))
    scanner.save(body.model_dump())
    return {"status": "ok", "version": body.version, "rule_count": len(body.rules)}


@app.get("/audit/export")
def audit_export(_: None = Depends(require_api_key)):
    settings = get_settings()
    rows = fetch_audit_logs(settings.sqlite_file, limit=10_000)
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=[
            "id", "request_id", "timestamp", "action_taken", "triggered_concepts",
            "triggered_categories", "policy_version", "user_prompt", "final_output",
        ],
    )
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, "") for k in writer.fieldnames})
    buffer.seek(0)
    filename = f"compliance_audit_{datetime.now().strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/system/status")
def system_status(settings: Settings = Depends(settings_dep)):
    status = {
        "api": True,
        "sqlite": True,
        "neo4j": False,
        "llm": False,
        "semantic": False,
        "rules_engine": "rust" if settings.use_rust_engine else "json",
    }
    try:
        conn = sqlite3.connect(settings.sqlite_file)
        conn.execute("SELECT 1")
        conn.close()
    except sqlite3.Error:
        status["sqlite"] = False
    try:
        if neo4j_driver is not None:
            neo4j_driver.verify_connectivity()
            status["neo4j"] = True
    except Exception:
        status["neo4j"] = False
    if settings.llm_provider == "mock":
        status["llm"] = True
    else:
        try:
            base = settings.ollama_url.replace("/api/generate", "")
            requests.get(base, timeout=3)
            status["llm"] = True
        except requests.RequestException:
            status["llm"] = False
    if settings.semantic_enabled:
        if settings.semantic_provider == "mock":
            status["semantic"] = True
        else:
            try:
                status["semantic"] = get_semantic_scanner(settings).ping()
            except Exception:
                status["semantic"] = False
    else:
        status["semantic"] = True
    return {"services": status, "ready": all(status.values())}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready(settings: Settings = Depends(settings_dep)):
    checks = {"sqlite": True, "neo4j": False}
    try:
        conn = sqlite3.connect(settings.sqlite_file)
        conn.execute("SELECT 1")
        conn.close()
    except sqlite3.Error:
        checks["sqlite"] = False
    try:
        if neo4j_driver is not None:
            neo4j_driver.verify_connectivity()
            checks["neo4j"] = True
    except Exception:
        checks["neo4j"] = False
    if all(checks.values()):
        return {"status": "ready", "checks": checks}
    raise HTTPException(status_code=503, detail={"status": "not ready", "checks": checks})


@app.get("/audit/stats")
def audit_stats(_: None = Depends(require_api_key)):
    return fetch_audit_stats(get_settings().sqlite_file)


@app.get("/audit/logs/{log_id}")
def audit_log_detail(log_id: int, _: None = Depends(require_api_key)):
    row = fetch_audit_log_by_id(get_settings().sqlite_file, log_id)
    if not row:
        raise HTTPException(status_code=404, detail="Audit event not found")
    return row


@app.get("/audit/logs")
def audit_logs(limit: int = 50, action: str | None = None, _: None = Depends(require_api_key)):
    settings = get_settings()
    return {"logs": fetch_audit_logs(settings.sqlite_file, limit=limit, action=action)}
