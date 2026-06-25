import os
from pathlib import Path
from urllib.parse import quote

import requests
from dotenv import load_dotenv
from fasthtml.common import *
from starlette.responses import FileResponse

load_dotenv()

API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")
API_KEY = os.getenv("API_KEY", "")
STATIC_DIR = Path(__file__).parent / "static"

TAILWIND = Script(src="https://cdn.tailwindcss.com")
LUCIDE = Script(src="https://unpkg.com/lucide@latest")
APP_JS = Script(src="/static/app.js")
APP_CSS = Link(rel="stylesheet", href="/static/app.css")

app, rt = fast_app(
    pico=False,
    static_path=str(Path(__file__).resolve().parent),
    hdrs=(
        TAILWIND,
        LUCIDE,
        APP_CSS,
        APP_JS,
        Link(rel="preconnect", href="https://fonts.googleapis.com"),
        Link(rel="stylesheet", href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"),
        Script(
            NotStr("""
            tailwind.config = {
              theme: {
                extend: {
                  fontFamily: { sans: ['Inter', 'system-ui', 'sans-serif'] }
                }
              }
            }
            """)
        ),
    )
)

DEMO_SCENARIOS = [
    ("FINRA returns", "Write an investment pitch guaranteeing 100% returns with zero risk."),
    ("Semantic paraphrase", "This fund always profits with no downside — you cannot lose money on it."),
    ("Blocked cure", "Explain why this supplement is a guaranteed cure for chronic illness."),
    ("Redact diagnosis", "Provide a definitive diagnosis of diabetes based on these symptoms."),
    ("Clean educational", "Explain how diversified investing works and why all investments carry risk."),
]

POLICY_FRAMEWORKS = [
    {
        "name": "FINRA Retail Communications",
        "category": "Financial Services",
        "description": "Restricts misleading performance claims and risk-free investment language.",
        "concepts": [
            ("Guaranteed Returns", "APPEND", "Write a pitch with guaranteed returns."),
            ("Risk-Free Investment", "APPEND", "Describe a zero risk investment opportunity."),
        ],
    },
    {
        "name": "Healthcare AI & HIPAA Compliance",
        "category": "Healthcare",
        "description": "Blocks unverified medical cures and redacts definitive diagnostic claims.",
        "concepts": [
            ("Guaranteed Cure", "BLOCK", "Claim this supplement is a guaranteed cure."),
            ("Definitive Diagnosis", "REDACT", "Give a definitive diagnosis of diabetes."),
        ],
    },
]

NAV = [
    ("/", "Dashboard", "layout-dashboard"),
    ("/scan", "Live Scan", "scan-search"),
    ("/audit", "Audit Log", "scroll-text"),
    ("/policies", "Policies", "shield-check"),
    ("/rules", "Rules", "list-tree"),
]

ACTION_BADGE = {
    "PASS": "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
    "APPEND": "bg-blue-50 text-blue-700 ring-blue-600/20",
    "REDACT": "bg-amber-50 text-amber-800 ring-amber-600/20",
    "BLOCK": "bg-red-50 text-red-700 ring-red-600/20",
    "PROMPT_FLAG": "bg-violet-50 text-violet-700 ring-violet-600/20",
    "PROMPT_REDACT": "bg-orange-50 text-orange-800 ring-orange-600/20",
    "PROMPT_BLOCK": "bg-rose-50 text-rose-800 ring-rose-600/20",
    "ERROR": "bg-red-50 text-red-700 ring-red-600/20",
}

BADGE_LABELS = {
    "PASS": "Pass",
    "APPEND": "Append",
    "REDACT": "Redact",
    "BLOCK": "Block",
    "PROMPT_FLAG": "Marketing prompt",
    "PROMPT_REDACT": "Clinical prompt",
    "PROMPT_BLOCK": "High-risk prompt",
    "ERROR": "Error",
}


def ic(name: str, cls: str = "w-4 h-4") -> NotStr:
    return NotStr(f'<i data-lucide="{name}" class="{cls}"></i>')


def api_headers() -> dict:
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["X-API-Key"] = API_KEY
    return headers


def api_get(path: str) -> dict | None:
    try:
        response = requests.get(f"{API_BASE}{path}", headers=api_headers(), timeout=5)
        if response.status_code == 200:
            return response.json()
    except requests.RequestException:
        pass
    return None


@rt("/static/{fname:path}")
def static_files(fname: str):
    return FileResponse(STATIC_DIR / fname)


def badge(action: str) -> Span:
    label = BADGE_LABELS.get(action, action or "—")
    colors = ACTION_BADGE.get(action, "bg-zinc-100 text-zinc-600 ring-zinc-500/20")
    return Span(label, cls=f"inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset {colors}")


def page_shell(active: str, title: str, subtitle: str, *body):
    system = api_get("/system/status") or {}
    ready = system.get("ready", False)
    services = system.get("services", {})

    nav_items = []
    for href, label, icon_name in NAV:
        active_cls = "bg-zinc-900 text-white" if active == href else "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900"
        nav_items.append(
            A(
                ic(icon_name, "w-4 h-4 shrink-0"),
                Span(label),
                href=href,
                cls=f"flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition {active_cls}",
            )
        )

    service_rows = []
    labels = {
        "api": ("Server", "server"),
        "sqlite": ("Audit DB", "database"),
        "neo4j": ("Policy Graph", "git-branch"),
        "llm": ("LLM", "cpu"),
        "semantic": ("Semantic", "brain"),
    }
    for key, (label, icon_name) in labels.items():
        ok = services.get(key, False)
        dot = "bg-emerald-500" if ok else "bg-red-500"
        status = "Online" if ok else "Offline"
        service_rows.append(
            Li(
                Div(
                    ic(icon_name, "w-3.5 h-3.5 text-zinc-400"),
                    Span(label, cls="text-sm text-zinc-700"),
                    cls="flex items-center gap-2",
                ),
                Span(
                    Span(cls=f"h-1.5 w-1.5 rounded-full {dot}"),
                    status,
                    cls="flex items-center gap-1.5 text-xs text-zinc-500",
                ),
                cls="flex items-center justify-between py-2 border-b border-zinc-100 last:border-0",
            )
        )

    return Div(
        # Sidebar
        Aside(
            Div(
                Div(
                    Div(ic("shield-check", "w-5 h-5 text-white"), cls="flex h-9 w-9 items-center justify-center rounded-lg bg-zinc-900"),
                    Div(
                        Div("Compliance Firewall", cls="text-sm font-semibold text-zinc-900"),
                        Div("Output governance", cls="text-xs text-zinc-500"),
                    ),
                    cls="flex items-center gap-3 px-2 py-4 border-b border-zinc-200",
                ),
                Nav(*nav_items, cls="flex flex-col gap-0.5 p-3"),
                cls="flex flex-col h-full",
            ),
            cls="w-60 shrink-0 border-r border-zinc-200 bg-white min-h-screen",
        ),
        # Main
        Div(
            Header(
                Div(
                    Div(H1(title, cls="text-xl font-semibold text-zinc-900"), P(subtitle, cls="mt-1 text-sm text-zinc-500")),
                    Details(
                        Summary(
                            Span(cls=f"h-2 w-2 rounded-full {'bg-emerald-500' if ready else 'bg-amber-500'}"),
                            "System status",
                            cls="flex cursor-pointer list-none items-center gap-2 rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm font-medium text-zinc-700 shadow-sm hover:bg-zinc-50 [&::-webkit-details-marker]:hidden",
                        ),
                        Div(
                            Ul(*service_rows, cls="mt-0 list-none p-0"),
                            cls="absolute right-0 z-20 mt-2 w-64 rounded-xl border border-zinc-200 bg-white p-3 shadow-lg",
                        ),
                        cls="relative",
                    ),
                    cls="flex items-start justify-between gap-4",
                ),
                cls="border-b border-zinc-200 bg-white px-8 py-5",
            ),
            Main(*body, cls="flex-1 px-8 py-6 bg-zinc-50"),
            Div(id="modal-root"),
            cls="flex flex-1 flex-col min-h-screen",
        ),
        cls="flex min-h-screen font-sans antialiased",
    )


def stat_card(label: str, value: str | int, hint: str, href: str, icon_name: str) -> A:
    return A(
        Div(
            Div(
                Div(label, cls="text-xs font-medium uppercase tracking-wide text-zinc-500"),
                Div(str(value), cls="mt-2 text-3xl font-semibold text-zinc-900"),
                Div(hint, cls="mt-1 text-xs text-zinc-400"),
                cls="flex-1",
            ),
            Div(ic(icon_name, "w-5 h-5 text-zinc-400"), cls="rounded-lg bg-zinc-50 p-2.5"),
            cls="flex items-start justify-between",
        ),
        href=href,
        cls="block rounded-xl border border-zinc-200 bg-white p-5 shadow-sm transition hover:border-zinc-300 hover:shadow-md",
    )


def stat_cards(stats: dict | None) -> Div:
    stats = stats or {}
    return Div(
        stat_card("Total events", stats.get("total_events", 0), "View full audit log", "/audit", "activity"),
        stat_card("Marketing prompt", stats.get("prompt_marketing", 0), "FINRA-style requests", "/audit?action=PROMPT_FLAG", "trending-up"),
        stat_card("Clinical prompt", stats.get("prompt_clinical", 0), "Diagnosis requests", "/audit?action=PROMPT_REDACT", "stethoscope"),
        stat_card("High-risk prompt", stats.get("prompt_high_risk", 0), "Cure claim requests", "/audit?action=PROMPT_BLOCK", "alert-triangle"),
        stat_card("Blocked", stats.get("blocks", 0), "Output blocked", "/audit?action=BLOCK", "ban"),
        stat_card("Disclaimers", stats.get("append", 0), "Output append", "/audit?action=APPEND", "file-warning"),
        stat_card("Redacted", stats.get("redact", 0), "Output redacted", "/audit?action=REDACT", "eraser"),
        cls="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7 gap-4 mb-6",
    )


TH_CLS = "px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-zinc-500 bg-zinc-50"
TABLE_CLS = "data-table w-full text-sm"
THEAD_CLS = "bg-zinc-50 border-b border-zinc-200"


def audit_row(row: dict, compact: bool = False) -> Tr:
    prompt = row.get("user_prompt", "") or "—"
    if compact and len(prompt) > 60:
        prompt = prompt[:60] + "…"
    cells = [
        Td(row.get("timestamp", ""), cls="whitespace-nowrap text-zinc-500 bg-white"),
        Td(badge(row.get("action_taken", "")), cls="bg-white"),
        Td(row.get("triggered_concepts", "—") or "—", cls="text-zinc-700 bg-white"),
    ]
    if not compact:
        cells.append(Td(prompt, cls="text-zinc-600 max-w-xs truncate bg-white"))
        cells.append(
            Td(Span((row.get("request_id") or "—")[:8], cls="font-mono text-xs text-zinc-400"), cls="bg-white")
        )
    return Tr(
        *cells,
        hx_get=f"/audit/detail/{row.get('id')}",
        hx_target="#modal-root",
        hx_swap="innerHTML",
        cls="cursor-pointer bg-white transition hover:bg-zinc-50 border-b border-zinc-100",
    )


def audit_filters(active: str | None) -> Div:
    filters = [
        ("All", None),
        ("Marketing prompt", "PROMPT_FLAG"),
        ("Clinical prompt", "PROMPT_REDACT"),
        ("High-risk prompt", "PROMPT_BLOCK"),
        ("Output blocked", "BLOCK"),
        ("Output append", "APPEND"),
        ("Output redact", "REDACT"),
    ]
    chips = []
    for label, value in filters:
        href = "/audit" if value is None else f"/audit?action={value}"
        is_active = active == value or (active is None and value is None)
        cls = "bg-zinc-900 text-white" if is_active else "bg-white text-zinc-600 hover:bg-zinc-100 border-zinc-200"
        chips.append(A(label, href=href, cls=f"rounded-lg border px-3 py-1.5 text-sm font-medium transition {cls}"))
    return Div(*chips, cls="flex flex-wrap gap-2 mb-4")


def result_box(data: dict) -> Div:
    status = data.get("status", "")
    action = data.get("action", "")
    final_output = data.get("final_output", "No output generated.")
    concepts = ", ".join(data.get("concepts", [])) or "—"
    categories = ", ".join(data.get("categories", [])) or "—"
    prompt_concepts = ", ".join(data.get("prompt_concepts", [])) or "—"
    output_concepts = ", ".join(data.get("output_concepts", [])) or "—"
    request_id = data.get("request_id", "")

    if status == "Blocked":
        border, title, sub = "border-orange-200", "Output blocked", "Restricted medical claim in model output"
    elif status == "Redacted":
        border, title, sub = "border-amber-200", "Content redacted", "Sensitive diagnostic language removed from output"
    elif status == "Violation Found":
        border, title, sub = "border-red-200", "Output violation", "Disclaimers appended from policy graph"
    elif status == "Marketing Prompt Flagged":
        border, title, sub = "border-violet-200", "Marketing prompt flagged", "FINRA-style request; model output was safe"
    elif status == "Clinical Prompt Flagged":
        border, title, sub = "border-orange-200", "Clinical prompt flagged", "Diagnostic request; model output was safe — review required"
    elif status == "High-Risk Prompt Flagged":
        border, title, sub = "border-rose-200", "High-risk prompt flagged", "Medical cure claim request; model output was safe — review required"
    elif status == "Error":
        border, title, sub = "border-red-200", "Request failed", "Could not reach upstream service"
    else:
        border, title, sub = "border-emerald-200", "Clean", "No policy matches in prompt or output"

    meta_items = [
        Div(
            Div("Request ID", cls="text-xs font-medium text-zinc-400 uppercase tracking-wide"),
            Div(
                Span(request_id[:8] if request_id else "—", cls="font-mono text-sm text-zinc-700"),
                Button(
                    ic("copy", "w-3.5 h-3.5"),
                    Span("Copy", data_copy_label="true", cls="text-xs"),
                    type="button",
                    onclick=f"copyText('{request_id}', this)",
                    cls="ml-2 inline-flex items-center gap-1 rounded-md border border-zinc-200 px-2 py-1 text-zinc-600 hover:bg-zinc-50",
                ) if request_id else None,
                cls="mt-1 flex items-center",
            ),
            cls="flex-1",
        ),
        Div(
            Div("Prompt concepts", cls="text-xs font-medium text-zinc-400 uppercase tracking-wide"),
            Div(prompt_concepts, cls="mt-1 text-sm text-zinc-700"),
            cls="flex-1",
        ),
        Div(
            Div("Output concepts", cls="text-xs font-medium text-zinc-400 uppercase tracking-wide"),
            Div(output_concepts, cls="mt-1 text-sm text-zinc-700"),
            cls="flex-1",
        ),
        Div(
            Div("Frameworks", cls="text-xs font-medium text-zinc-400 uppercase tracking-wide"),
            Div(categories, cls="mt-1 text-sm text-zinc-700"),
            cls="flex-1",
        ),
    ]

    return Div(
        Div(
            Div(
                Div(title, cls="font-semibold text-zinc-900"),
                Div(sub, cls="text-sm text-zinc-500 mt-0.5"),
            ),
            badge(action),
            cls=f"flex items-center justify-between gap-4 px-5 py-4 border-b {border} bg-white rounded-t-xl",
        ),
        Div(*meta_items, cls="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 px-5 py-4 bg-zinc-50 border-b border-zinc-200"),
        Details(
            Summary(
                ic("chevron-down", "w-4 h-4"),
                "View output",
                cls="flex cursor-pointer list-none items-center gap-2 px-5 py-3 text-sm font-medium text-zinc-700 hover:bg-zinc-50 [&::-webkit-details-marker]:hidden",
            ),
            Pre(final_output, cls="mx-5 mb-5 mt-0 overflow-x-auto rounded-lg border border-zinc-200 bg-zinc-50 p-4 text-sm text-zinc-800 whitespace-pre-wrap font-mono"),
            open=True,
            cls="bg-white rounded-b-xl",
        ),
        cls="rounded-xl border border-zinc-200 shadow-sm overflow-hidden mt-4",
    )


def scan_form(prefill: str = "") -> Div:
    scenario_buttons = [
        Button(
            label,
            type="button",
            onclick=f"fillPrompt({repr(prompt)})",
            cls="rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-xs font-medium text-zinc-600 hover:bg-zinc-100 transition",
        )
        for label, prompt in DEMO_SCENARIOS
    ]

    return Div(
        Div(
            Div("Prompt", cls="text-sm font-medium text-zinc-900"),
            Div("Generate LLM output and scan both the prompt and the response.", cls="text-sm text-zinc-500 mt-0.5"),
            cls="mb-4",
        ),
        Form(
            Textarea(
                name="prompt",
                id="prompt-input",
                placeholder="Enter a prompt…",
                rows=5,
                value=prefill,
                cls="w-full rounded-lg border border-zinc-300 bg-white px-4 py-3 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-zinc-900 focus:outline-none focus:ring-1 focus:ring-zinc-900",
            ),
            Div(
                Div("Quick scenarios", cls="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-2 mt-4"),
                Div(*scenario_buttons, cls="flex flex-wrap gap-2"),
            ),
            Div(
                Button(
                    ic("play", "w-4 h-4"),
                    "Run scan",
                    type="submit",
                    cls="mt-5 inline-flex items-center gap-2 rounded-lg bg-zinc-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-zinc-800 transition",
                    hx_post="/generate-ui",
                    hx_target="#result-container",
                    hx_indicator="#scan-spinner",
                ),
                Div(
                    Div(cls="h-4 w-4 animate-spin rounded-full border-2 border-zinc-300 border-t-zinc-900"),
                    Span("Scanning…", cls="text-sm text-zinc-500"),
                    id="scan-spinner",
                    cls="htmx-indicator inline-flex items-center gap-2 ml-3",
                ),
                cls="flex items-center",
            ),
            Div(id="result-container"),
        ),
        cls="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm",
    )


@rt("/")
def home():
    stats = api_get("/audit/stats")
    recent = (api_get("/audit/logs?limit=5") or {}).get("logs", [])

    if recent:
        table = Div(
            Table(
                Thead(
                    Tr(
                        Th("Time", cls=TH_CLS),
                        Th("Action", cls=TH_CLS),
                        Th("Concepts", cls=TH_CLS),
                    ),
                    cls=THEAD_CLS,
                ),
                Tbody(*[audit_row(r, compact=True) for r in recent]),
                cls=TABLE_CLS,
            ),
            cls="overflow-x-auto",
        )
    else:
        table = Div(
            ic("inbox", "w-8 h-8 text-zinc-300 mx-auto"),
            P("No events yet.", cls="mt-2 text-sm text-zinc-500"),
            A("Run first scan", href="/scan", cls="mt-3 inline-block text-sm font-medium text-zinc-900 underline"),
            cls="py-10 text-center",
        )

    return page_shell(
        "/",
        "Dashboard",
        "Monitor compliance events, system health, and recent policy actions.",
        stat_cards(stats),
        Div(
            Div(
                Div(
                    Div(
                        Div("Recent activity", cls="text-sm font-semibold text-zinc-900"),
                        A(
                            "View all",
                            ic("arrow-right", "w-3.5 h-3.5"),
                            href="/audit",
                            cls="inline-flex items-center gap-1 text-sm font-medium text-zinc-600 hover:text-zinc-900",
                        ),
                        cls="flex items-center justify-between mb-4",
                    ),
                    table,
                    cls="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm",
                ),
            ),
            Div(
                Div("Pipeline", cls="text-sm font-semibold text-zinc-900 mb-4"),
                Div(
                    A("LLM", href="/scan", cls="rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs font-medium text-zinc-600 hover:bg-zinc-100"),
                    Span("→", cls="text-zinc-300 text-xs"),
                    Span("Rust rules", cls="rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs font-medium text-zinc-600"),
                    Span("→", cls="text-zinc-300 text-xs"),
                    Span("Policy", cls="rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs font-medium text-zinc-600"),
                    Span("→", cls="text-zinc-300 text-xs"),
                    A("Audit", href="/audit", cls="rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs font-medium text-zinc-600 hover:bg-zinc-100"),
                    cls="flex flex-wrap items-center gap-2",
                ),
                Div(
                    A(
                        ic("scan-search", "w-4 h-4"),
                        "Open live scan",
                        href="/scan",
                        cls="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-zinc-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-zinc-800",
                    ),
                    cls="mt-4",
                ),
                cls="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm h-fit",
            ),
            cls="grid grid-cols-1 lg:grid-cols-3 gap-4",
        ),
    )


@rt("/scan")
def scan_page(prompt: str = ""):
    return page_shell(
        "/scan",
        "Live Scan",
        "Test prompts against the rule engine and inspect policy verdicts.",
        scan_form(prefill=prompt),
    )


@rt("/generate-ui")
def post(prompt: str):
    try:
        response = requests.post(
            f"{API_BASE}/generate",
            json={"prompt": prompt},
            headers=api_headers(),
            timeout=120,
        )
        data = response.json()
        if response.status_code == 401:
            return Div("Set API_KEY in .env or clear it for local dev.", cls="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700")
        return result_box(data)
    except requests.RequestException:
        return Div(f"Backend offline — start FastAPI on {API_BASE}.", cls="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700")


@rt("/audit/detail/{log_id:int}")
def audit_detail(log_id: int):
    try:
        response = requests.get(f"{API_BASE}/audit/logs/{log_id}", headers=api_headers(), timeout=10)
        if response.status_code != 200:
            return Div("Could not load event.", cls="text-sm text-red-600")
        row = response.json()
    except requests.RequestException:
        return Div("Backend offline.", cls="text-sm text-red-600")

    rid = row.get("request_id", "")
    return Div(
        # Backdrop
        Div(
            Div(
                Div(
                    Div(
                        Div("Audit event", cls="text-base font-semibold text-zinc-900"),
                        Div(row.get("timestamp", ""), cls="text-sm text-zinc-500"),
                        cls="flex-1",
                    ),
                    Button(
                        ic("x", "w-5 h-5"),
                        type="button",
                        onclick="closeModal()",
                        cls="rounded-lg p-1.5 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700",
                    ),
                    cls="flex items-start justify-between gap-4 px-6 py-4 border-b border-zinc-200",
                ),
                Div(
                    Div(
                        Div("Action", cls="text-xs font-medium text-zinc-400 uppercase"),
                        Div(badge(row.get("action_taken", "")), cls="mt-1"),
                    ),
                    Div(
                        Div("Concepts", cls="text-xs font-medium text-zinc-400 uppercase"),
                        Div(row.get("triggered_concepts", "—"), cls="mt-1 text-sm text-zinc-700"),
                    ),
                    Div(
                        Div("Frameworks", cls="text-xs font-medium text-zinc-400 uppercase"),
                        Div(row.get("triggered_categories", "—"), cls="mt-1 text-sm text-zinc-700"),
                    ),
                    cls="grid grid-cols-3 gap-4 px-6 py-4 bg-zinc-50 border-b border-zinc-200",
                ),
                Div(
                    Div("Prompt", cls="text-xs font-medium text-zinc-400 uppercase mb-1"),
                    P(row.get("user_prompt", "—"), cls="text-sm text-zinc-800"),
                    Div("Raw LLM output", cls="text-xs font-medium text-zinc-400 uppercase mb-1 mt-4"),
                    Pre(row.get("raw_llm_output", "—"), cls="rounded-lg bg-zinc-900 p-3 text-xs text-zinc-100 whitespace-pre-wrap font-mono overflow-x-auto"),
                    Div("Final output", cls="text-xs font-medium text-zinc-400 uppercase mb-1 mt-4"),
                    Pre(row.get("final_output", "—"), cls="rounded-lg bg-zinc-100 p-3 text-xs text-zinc-800 whitespace-pre-wrap font-mono overflow-x-auto"),
                    cls="px-6 py-4 max-h-96 overflow-y-auto",
                ),
                Div(
                    Button(
                        ic("copy", "w-4 h-4"),
                        Span("Copy request ID", data_copy_label="true"),
                        type="button",
                        onclick=f"copyText('{rid}', this)",
                        cls="inline-flex items-center gap-2 rounded-lg border border-zinc-200 px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-50",
                    ),
                    Button(
                        "Close",
                        type="button",
                        onclick="closeModal()",
                        cls="rounded-lg bg-zinc-900 px-3 py-2 text-sm font-medium text-white hover:bg-zinc-800",
                    ),
                    cls="flex justify-end gap-2 px-6 py-4 border-t border-zinc-200",
                ),
                cls="relative w-full max-w-2xl rounded-xl bg-white shadow-2xl",
                onclick="event.stopPropagation()",
            ),
            cls="fixed inset-0 z-50 flex items-center justify-center bg-zinc-900/40 p-4",
            onclick="closeModal()",
        ),
    )


@rt("/audit")
def audit_page(action: str = None):
    stats = api_get("/audit/stats")
    api_path = "/audit/logs?limit=50"
    if action:
        api_path += f"&action={action}"
    try:
        response = requests.get(f"{API_BASE}{api_path}", headers=api_headers(), timeout=30)
        if response.status_code == 401:
            rows, error = [], Div("API key required.", cls="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700")
        else:
            rows = response.json().get("logs", [])
            error = None
    except requests.RequestException:
        rows, error = [], Div(f"Backend offline — start FastAPI on {API_BASE}.", cls="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700")

    if not rows:
        table = Div(
            ic("scroll-text", "w-8 h-8 text-zinc-300 mx-auto"),
            P("No events match this filter.", cls="mt-2 text-sm text-zinc-500"),
            A("Run a scan", href="/scan", cls="mt-3 inline-block text-sm font-medium text-zinc-900 underline"),
            cls="py-12 text-center",
        )
    else:
        table = Div(
            Table(
                Thead(
                    Tr(
                        Th("Time", cls=TH_CLS),
                        Th("Action", cls=TH_CLS),
                        Th("Concepts", cls=TH_CLS),
                        Th("Prompt", cls=TH_CLS),
                        Th("Request", cls=TH_CLS),
                    ),
                    cls=THEAD_CLS,
                ),
                Tbody(*[audit_row(r) for r in rows]),
                cls=TABLE_CLS,
            ),
            P("Click a row to view full details.", cls="mt-3 text-xs text-zinc-400"),
            cls="overflow-x-auto",
        )

    return page_shell(
        "/audit",
        "Audit Log",
        "Click any row to inspect the full prompt, raw output, and policy result.",
        stat_cards(stats),
        error,
        Div(
            Div(
                A(
                    ic("download", "w-4 h-4"),
                    Span("Export CSV"),
                    href="/audit/export",
                    cls="inline-flex items-center gap-2 rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50",
                ),
                cls="mb-4 flex justify-end",
            ),
            audit_filters(action),
            table,
            cls="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm",
        ),
    )


@rt("/audit/export")
def audit_export_proxy():
    try:
        response = requests.get(
            f"{API_BASE}/audit/export",
            headers=api_headers(),
            timeout=30,
        )
        if response.status_code != 200:
            return Div("Export failed — check API key and backend.", cls="text-sm text-red-600")
        from starlette.responses import Response

        return Response(
            content=response.content,
            media_type="text/csv",
            headers=response.headers,
        )
    except requests.RequestException:
        return Div(f"Backend offline — start FastAPI on {API_BASE}.", cls="text-sm text-red-600")


@rt("/rules")
def rules_page():
    data = api_get("/admin/rules")
    if not data:
        return page_shell(
            "/rules",
            "Rules",
            "Live rule pack from the middleware API.",
            Div(
                f"Backend offline or API key missing — start FastAPI on {API_BASE}.",
                cls="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700",
            ),
        )

    engine = data.get("engine", "json")
    rows = []
    for rule in data.get("rules", []):
        rows.append(
            Tr(
                Td(rule.get("id", ""), cls="px-4 py-3 text-sm font-mono text-zinc-600"),
                Td(rule.get("concept", ""), cls="px-4 py-3 text-sm text-zinc-800"),
                Td(rule.get("category", ""), cls="px-4 py-3 text-sm text-zinc-600"),
                Td(badge(rule.get("action", "")), cls="px-4 py-3"),
                Td(Pre(rule.get("pattern", ""), cls="text-xs text-zinc-500 whitespace-pre-wrap"), cls="px-4 py-3 max-w-xs"),
            )
        )

    note = (
        "Rules are loaded from backend/rules/policy_rules.json. Edit via PUT /admin/rules when USE_RUST_ENGINE=false."
        if engine == "json"
        else "Rust engine active — recompile with maturin develop to change rules."
    )

    return page_shell(
        "/rules",
        "Rules",
        "Active detection patterns and enforcement actions.",
        Div(
            Div(
                Div(
                    Span(f"v{data.get('version', '?')}", cls="rounded-md bg-zinc-100 px-2 py-0.5 text-xs font-medium text-zinc-600"),
                    Span(f"Engine: {engine}", cls="ml-2 rounded-md bg-zinc-100 px-2 py-0.5 text-xs font-medium text-zinc-600"),
                    Span(f"Updated {data.get('updated_at', '—')}", cls="ml-2 text-xs text-zinc-400"),
                    cls="mb-4 flex flex-wrap items-center gap-2",
                ),
                P(note, cls="text-sm text-zinc-500"),
                Div(
                    Table(
                        Thead(
                            Tr(
                                Th("ID", cls=TH_CLS),
                                Th("Concept", cls=TH_CLS),
                                Th("Category", cls=TH_CLS),
                                Th("Action", cls=TH_CLS),
                                Th("Pattern", cls=TH_CLS),
                            ),
                            cls=THEAD_CLS,
                        ),
                        Tbody(*rows),
                        cls=TABLE_CLS,
                    ),
                    cls="mt-4 overflow-x-auto",
                ),
                cls="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm",
            ),
        ),
    )


@rt("/policies")
def policies_page():
    cards = []
    for fw in POLICY_FRAMEWORKS:
        concept_links = []
        for name, action, test_prompt in fw["concepts"]:
            colors = {"BLOCK": "text-red-700 bg-red-50", "APPEND": "text-blue-700 bg-blue-50", "REDACT": "text-amber-800 bg-amber-50"}
            concept_links.append(
                A(
                    Span(name, cls="text-sm font-medium"),
                    Span(action, cls=f"ml-2 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase {colors.get(action, 'bg-zinc-100')}"),
                    ic("arrow-up-right", "w-3 h-3 ml-1 opacity-50"),
                    href=f"/scan?prompt={quote(test_prompt)}",
                    cls="inline-flex items-center rounded-lg border border-zinc-200 px-3 py-2 hover:bg-zinc-50 transition",
                )
            )
        cards.append(
            Div(
                Span(fw["category"], cls="inline-block rounded-md bg-zinc-100 px-2 py-0.5 text-xs font-medium text-zinc-600"),
                H3(fw["name"], cls="mt-3 text-base font-semibold text-zinc-900"),
                P(fw["description"], cls="mt-1 text-sm text-zinc-500 leading-relaxed"),
                Div("Rules — click to test", cls="mt-4 mb-2 text-xs font-medium text-zinc-400 uppercase tracking-wide"),
                Div(*concept_links, cls="flex flex-col gap-2"),
                cls="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm",
            )
        )

    return page_shell(
        "/policies",
        "Policies",
        "Framework rules mapped to Rust patterns and Neo4j concepts. Click a rule to test it.",
        Div(*cards, cls="grid grid-cols-1 md:grid-cols-2 gap-4"),
        Div(
            Div("Enforcement order", cls="text-sm font-semibold text-zinc-900"),
            Div(
                badge("PASS"), Span("→", cls="text-zinc-300 mx-1"),
                badge("APPEND"), Span("→", cls="text-zinc-300 mx-1"),
                badge("REDACT"), Span("→", cls="text-zinc-300 mx-1"),
                badge("BLOCK"),
                cls="mt-3 flex flex-wrap items-center gap-1",
            ),
            P("Strictest action wins when multiple violations match.", cls="mt-2 text-sm text-zinc-500"),
            cls="mt-4 rounded-xl border border-zinc-200 bg-white p-5 shadow-sm",
        ),
    )


serve()
