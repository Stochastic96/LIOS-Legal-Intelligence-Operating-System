"""FastAPI routes for LIOS."""

from __future__ import annotations

from datetime import datetime, timezone
import uuid
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from lios.config import settings
from lios.features.applicability_checker import ApplicabilityChecker
from lios.features.carbon_accounting import (
    CarbonAccountingEngine,
    Scope1Input,
    Scope2Input,
    Scope3Input,
)
from lios.features.chat_training import ChatTurn, LocalTrainingStore
from lios.features.compliance_roadmap import ComplianceRoadmapGenerator
from lios.features.materiality import DoubleMaterialityEngine
from lios.features.supply_chain import SupplyChainDueDiligenceEngine
from lios.knowledge.regulatory_db import RegulatoryDatabase
from lios.logging_setup import RequestLogger, get_logger
from lios.models.validation import (
    ApplicabilityRequest,
    CarbonCalculationRequest,
    ErrorResponse,
    FullQueryResponse,
    HealthResponse,
    MaterialityAssessmentRequest,
    QueryRequest,
    RoadmapRequest,
    SupplierRegistrationRequest,
)
from lios.orchestration.engine import OrchestrationEngine

logger = get_logger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Legal Intelligence Operating System for EU sustainability compliance.",
)

# Shared instances (initialised once at import time)
_db = RegulatoryDatabase()
_engine = OrchestrationEngine()
_applicability_checker = ApplicabilityChecker()
_roadmap_generator = ComplianceRoadmapGenerator()
_training_store = LocalTrainingStore()
_carbon_engine = CarbonAccountingEngine()
_supply_chain_engine = SupplyChainDueDiligenceEngine()
_materiality_engine = DoubleMaterialityEngine()


# ---- Exception handlers ----

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed response."""
    request_id = str(uuid.uuid4())
    logger.error(f"Validation error (request_id={request_id}): {exc}")
    
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error="Request validation failed",
            error_type="validation",
            details={
                "errors": [
                    {
                        "field": ".".join(str(loc) for loc in error["loc"]),
                        "type": error["type"],
                        "message": error["msg"],
                    }
                    for error in exc.errors()
                ]
            },
            request_id=request_id,
        ).model_dump(),
    )


# ---- Endpoints ----

@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """Redirect the base URL to the chat workspace."""
    return RedirectResponse(url="/chat", status_code=307)


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    """Return an empty favicon response to avoid noisy 404 logs in local runs."""
    return Response(status_code=204)

@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        app_name=settings.APP_NAME,
        version=settings.VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
        components={
            "database": "ok",
            "engine": "ok",
        },
    )


@app.get("/regulations")
def list_regulations() -> list[dict[str, Any]]:
    """List all available regulations."""
    logger.debug("Listing all regulations")
    return _db.get_all_regulations()


@app.get("/regulations/{name}")
def get_regulation(name: str) -> dict[str, Any]:
    """Get a specific regulation by name."""
    logger.debug(f"Fetching regulation: {name}")
    reg = _db.get_regulation(name)
    if reg is None:
        request_id = str(uuid.uuid4())
        logger.warning(f"Regulation not found: {name} (request_id={request_id})")
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error=f"Regulation '{name}' not found",
                error_type="not_found",
                request_id=request_id,
            ).model_dump(),
        )
    # Exclude module object from response
    return {k: v for k, v in reg.items() if k != "module"}


@app.get("/chat", response_class=HTMLResponse)
def chat_workspace() -> str:
        """Serve a local-first visual chat workspace for iterative training runs."""
        return """<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>LIOS Chat Studio</title>
    <style>
        :root {
            --bg: #f4f1e8;
            --paper: #fffdf8;
            --ink: #1c2322;
            --muted: #61706c;
            --brand: #126d67;
            --accent: #cf642e;
            --line: #d9d2c6;
            --shadow: 0 18px 40px rgba(16, 24, 22, 0.12);
        }
        * { box-sizing: border-box; }
        body {
            margin: 0;
            min-height: 100vh;
            font-family: Arial, sans-serif;
            color: var(--ink);
            background:
                radial-gradient(circle at top left, #f8dcc2 0, transparent 34%),
                radial-gradient(circle at top right, #d8efe7 0, transparent 28%),
                linear-gradient(160deg, #faf7f0 0%, #f1eee7 100%);
        }
        .shell {
            max-width: 1180px;
            margin: 24px auto;
            padding: 0 16px;
            display: grid;
            grid-template-columns: 300px 1fr;
            gap: 16px;
        }
        .card {
            background: var(--paper);
            border: 1px solid var(--line);
            border-radius: 18px;
            box-shadow: var(--shadow);
            overflow: hidden;
        }
        .sidebar { padding: 16px; }
        .title h1 { margin: 0; font-size: 1.25rem; }
        .title p { margin: 6px 0 0; color: var(--muted); font-size: 0.92rem; }
        .field { margin-top: 14px; }
        label {
            display: block;
            margin-bottom: 6px;
            font-size: 0.78rem;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: var(--muted);
        }
        input, textarea, button {
            font: inherit;
        }
        input, textarea {
            width: 100%;
            border: 1px solid var(--line);
            border-radius: 12px;
            padding: 12px 12px;
            background: #fff;
            color: var(--ink);
        }
        textarea { resize: vertical; min-height: 80px; }
        .help { margin-top: 10px; color: var(--muted); font-size: 0.8rem; line-height: 1.4; }
        .actions { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 14px; }
        button {
            border: 0;
            border-radius: 12px;
            padding: 11px 14px;
            cursor: pointer;
            font-weight: 700;
            transition: transform 120ms ease, opacity 120ms ease;
        }
        button:hover { transform: translateY(-1px); }
        button:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
        .ghost { background: #ece7dc; color: #24302d; }
        .primary { background: var(--brand); color: #fff; }
        .workspace {
            display: grid;
            grid-template-rows: auto 1fr auto;
            min-height: 78vh;
        }
        .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            padding: 14px 16px;
            border-bottom: 1px solid var(--line);
            background: linear-gradient(110deg, #fff 0%, #f8f5ef 100%);
        }
        .header strong { font-size: 1rem; }
        .status {
            padding: 4px 10px;
            border-radius: 999px;
            border: 1px solid #bcd9d2;
            background: #dff2ed;
            color: #255e57;
            font-size: 0.76rem;
            font-family: monospace;
        }
        .log {
            padding: 16px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .bubble {
            max-width: 88%;
            padding: 12px 14px;
            border-radius: 16px;
            border: 1px solid var(--line);
            line-height: 1.45;
            white-space: pre-wrap;
            animation: rise 180ms ease;
        }
        .bubble.user { align-self: flex-end; background: #e9f3f0; border-color: #beddd7; }
        .bubble.assistant { align-self: flex-start; background: #fff; }
        .meta { margin-top: 8px; color: var(--muted); font-size: 0.74rem; font-family: monospace; }
        .composer {
            padding: 14px;
            border-top: 1px solid var(--line);
            background: #fbfaf6;
            display: grid;
            grid-template-columns: 1fr 128px;
            gap: 12px;
        }
        .composer textarea { min-height: 56px; max-height: 160px; }
        .send { background: var(--accent); color: #fff; }
        @keyframes rise {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
        }
        @media (max-width: 900px) {
            .shell { grid-template-columns: 1fr; }
            .workspace { min-height: 70vh; }
            .bubble { max-width: 100%; }
            .composer { grid-template-columns: 1fr; }
            .actions { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="shell">
        <aside class="card sidebar">
            <div class="title">
                <h1>LIOS Chat Studio</h1>
                <p>Local-first training workspace</p>
            </div>

            <div class="field">
                <label for="sessionId">Session ID</label>
                <input id="sessionId" />
            </div>

            <div class="field">
                <label for="jurisdictions">Jurisdictions</label>
                <input id="jurisdictions" placeholder="EU, Germany" />
            </div>

            <div class="field">
                <label for="profile">Company profile JSON</label>
                <textarea id="profile" placeholder='{"employees":750,"turnover_eur":350000000,"listed":true}'></textarea>
            </div>

            <div class="actions">
                <button class="ghost" id="loadBtn">Load Session</button>
                <button class="ghost" id="exportBtn">Export JSONL</button>
            </div>

            <div class="help">Every exchange is stored locally in logs/chat_training.jsonl for iterative training and prompt tuning.</div>
        </aside>

        <section class="card workspace">
            <header class="header">
                <strong>Interactive Legal Chat</strong>
                <span class="status" id="status">ready</span>
            </header>
            <main class="log" id="chatLog"></main>
            <footer class="composer">
                <textarea id="prompt" placeholder="Ask LIOS a compliance question..."></textarea>
                <button class="send" id="sendBtn">Send</button>
            </footer>
        </section>
    </div>

    <script>
        const chatLog = document.getElementById("chatLog");
        const statusEl = document.getElementById("status");
        const promptEl = document.getElementById("prompt");
        const sendBtn = document.getElementById("sendBtn");
        const loadBtn = document.getElementById("loadBtn");
        const exportBtn = document.getElementById("exportBtn");
        const sessionEl = document.getElementById("sessionId");
        const jursEl = document.getElementById("jurisdictions");
        const profileEl = document.getElementById("profile");

        sessionEl.value = `session-${Date.now().toString(36)}`;

        function addBubble(text, role, meta = "") {
            const bubble = document.createElement("div");
            bubble.className = `bubble ${role}`;
            bubble.textContent = text;
            if (meta) {
                const metaEl = document.createElement("div");
                metaEl.className = "meta";
                metaEl.textContent = meta;
                bubble.appendChild(metaEl);
            }
            chatLog.appendChild(bubble);
            chatLog.scrollTop = chatLog.scrollHeight;
        }

        function parseProfile() {
            const raw = profileEl.value.trim();
            if (!raw) return null;
            return JSON.parse(raw);
        }

        async function sendMessage() {
            const query = promptEl.value.trim();
            if (!query) return;

            let companyProfile = null;
            try {
                companyProfile = parseProfile();
            } catch {
                addBubble("Invalid company profile JSON. Please fix it and try again.", "assistant");
                return;
            }

            const jurisdictions = jursEl.value.split(",").map((value) => value.trim()).filter(Boolean);

            addBubble(query, "user");
            promptEl.value = "";
            statusEl.textContent = "thinking";
            sendBtn.disabled = true;

            try {
                const response = await fetch("/chat/api/message", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        query,
                        session_id: sessionEl.value,
                        jurisdictions,
                        company_profile: companyProfile,
                    }),
                });

                const data = await response.json();
                if (!response.ok) {
                    addBubble(`Error: ${data.error || "request failed"}`, "assistant");
                    return;
                }

                const citations = (data.citations || [])
                    .slice(0, 3)
                    .map((citation) => `${citation.regulation} ${citation.article_id}`)
                    .join(" | ");
                addBubble(data.answer, "assistant", `intent=${data.intent}${citations ? " | " + citations : ""}`);
            } catch (error) {
                addBubble(`Request failed: ${error}`, "assistant");
            } finally {
                statusEl.textContent = "ready";
                sendBtn.disabled = false;
            }
        }

        async function loadSession() {
            statusEl.textContent = "loading";
            chatLog.innerHTML = "";
            try {
                const response = await fetch(`/chat/api/history?session_id=${encodeURIComponent(sessionEl.value)}`);
                const data = await response.json();
                if (!response.ok) {
                    addBubble(`Error: ${data.error || "unable to load session"}`, "assistant");
                    return;
                }
                for (const turn of data.turns || []) {
                    addBubble(turn.user_query || "", "user");
                    addBubble(turn.answer || "", "assistant", `intent=${turn.intent || "unknown"}`);
                }
            } finally {
                statusEl.textContent = "ready";
            }
        }

        async function exportSession() {
            const response = await fetch(`/chat/api/export?session_id=${encodeURIComponent(sessionEl.value)}`);
            if (!response.ok) {
                addBubble("Could not export session.", "assistant");
                return;
            }
            const text = await response.text();
            const blob = new Blob([text], { type: "application/x-ndjson" });
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = `${sessionEl.value}.jsonl`;
            link.click();
            URL.revokeObjectURL(url);
        }

        sendBtn.addEventListener("click", sendMessage);
        loadBtn.addEventListener("click", loadSession);
        exportBtn.addEventListener("click", exportSession);
        promptEl.addEventListener("keydown", (event) => {
            if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                sendMessage();
            }
        });

        addBubble("Workspace ready. Send your first query to begin local training capture.", "assistant");
    </script>
</body>
</html>"""


@app.get("/chat-ui", include_in_schema=False)
def chat_workspace_alias() -> RedirectResponse:
    """Alias route for chat workspace to simplify local troubleshooting."""
    return RedirectResponse(url="/chat", status_code=307)


@app.get("/chat-react", response_class=HTMLResponse)
def chat_workspace_react() -> str:
        """Serve a React-based chat workspace without a separate frontend build."""
        return """<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>LIOS React Chat Studio</title>
    <script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    <style>
        :root { --bg: #f5f6f8; --panel: #ffffff; --ink: #1f2937; --muted: #6b7280; --line: #d9dee8; --brand: #0f766e; --accent: #0b7285; }
        * { box-sizing: border-box; }
        body { margin: 0; background: linear-gradient(180deg, #eef2f6 0, #f7f8fb 100%); color: var(--ink); font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Helvetica, Arial, sans-serif; }
        .shell { max-width: 1120px; margin: 24px auto; padding: 0 16px; display: grid; grid-template-columns: 300px 1fr; gap: 16px; }
        .card { background: var(--panel); border: 1px solid var(--line); border-radius: 14px; }
        .side { padding: 14px; }
        .side h1 { margin: 0 0 4px; font-size: 1.1rem; }
        .muted { color: var(--muted); font-size: 0.88rem; }
        label { display: block; margin-top: 10px; margin-bottom: 4px; font-size: 0.78rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.04em; }
        input, textarea, button { width: 100%; font: inherit; }
        input, textarea { border: 1px solid var(--line); border-radius: 10px; padding: 10px; }
        textarea { min-height: 80px; resize: vertical; }
        .row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 10px; }
        button { border: 0; border-radius: 10px; padding: 10px 12px; cursor: pointer; font-weight: 700; }
        .ghost { background: #e9edf3; color: #1f2937; }
        .primary { background: var(--brand); color: #fff; }
        .chat { display: grid; grid-template-rows: auto 1fr auto; min-height: 74vh; }
        .head { padding: 12px 14px; border-bottom: 1px solid var(--line); display: flex; justify-content: space-between; align-items: center; }
        .status { font-size: 0.78rem; color: var(--accent); background: #eaf5f8; border: 1px solid #c9e4eb; border-radius: 999px; padding: 4px 10px; }
        .log { padding: 14px; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; }
        .msg { max-width: 88%; border: 1px solid var(--line); border-radius: 14px; padding: 10px 12px; white-space: pre-wrap; line-height: 1.45; }
        .u { align-self: flex-end; background: #e8f5f4; }
        .a { align-self: flex-start; background: #fff; }
        .meta { margin-top: 6px; color: var(--muted); font-size: 0.74rem; }
        .compose { border-top: 1px solid var(--line); padding: 12px; display: grid; grid-template-columns: 1fr 120px; gap: 10px; }
        .compose textarea { min-height: 56px; max-height: 150px; }
        @media (max-width: 900px) { .shell { grid-template-columns: 1fr; } .compose { grid-template-columns: 1fr; } .row { grid-template-columns: 1fr; } .msg { max-width: 100%; } }
    </style>
</head>
<body>
    <div id="root"></div>
    <script type="text/babel">
        const { useMemo, useState } = React;

        function App() {
            const [sessionId, setSessionId] = useState(`session-${Date.now().toString(36)}`);
            const [jurisdictions, setJurisdictions] = useState("");
            const [profile, setProfile] = useState('{"employees":750,"turnover_eur":350000000,"listed":true}');
            const [prompt, setPrompt] = useState("");
            const [status, setStatus] = useState("ready");
            const [messages, setMessages] = useState([{ role: "assistant", text: "React workspace ready. Ask your first compliance question.", meta: "local" }]);

            const parsedJurisdictions = useMemo(
                () => jurisdictions.split(",").map((v) => v.trim()).filter(Boolean),
                [jurisdictions]
            );

            function addMessage(role, text, meta = "") {
                setMessages((prev) => [...prev, { role, text, meta }]);
            }

            function parseProfile() {
                const raw = profile.trim();
                if (!raw) return null;
                return JSON.parse(raw);
            }

            async function sendMessage() {
                const query = prompt.trim();
                if (!query) return;

                let companyProfile = null;
                try {
                    companyProfile = parseProfile();
                } catch {
                    addMessage("assistant", "Invalid company profile JSON. Fix JSON and retry.");
                    return;
                }

                addMessage("user", query);
                setPrompt("");
                setStatus("thinking");

                try {
                    const response = await fetch("/chat/api/message", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            query,
                            session_id: sessionId,
                            jurisdictions: parsedJurisdictions,
                            company_profile: companyProfile,
                        }),
                    });
                    const data = await response.json();
                    if (!response.ok) {
                        addMessage("assistant", `Error: ${data.error || "request failed"}`);
                        return;
                    }

                    const citations = (data.citations || [])
                        .slice(0, 3)
                        .map((c) => `${c.regulation} ${c.article_id}`)
                        .join(" | ");
                    const meta = `intent=${data.intent}${citations ? " | " + citations : ""}`;
                    addMessage("assistant", data.answer, meta);
                } catch (error) {
                    addMessage("assistant", `Request failed: ${error}`);
                } finally {
                    setStatus("ready");
                }
            }

            async function loadSession() {
                setStatus("loading");
                try {
                    const response = await fetch(`/chat/api/history?session_id=${encodeURIComponent(sessionId)}`);
                    const data = await response.json();
                    if (!response.ok) {
                        addMessage("assistant", `Error: ${data.error || "unable to load session"}`);
                        return;
                    }
                    const loaded = [];
                    for (const turn of data.turns || []) {
                        loaded.push({ role: "user", text: turn.user_query || "", meta: "" });
                        loaded.push({ role: "assistant", text: turn.answer || "", meta: `intent=${turn.intent || "unknown"}` });
                    }
                    setMessages(loaded.length ? loaded : [{ role: "assistant", text: "No turns yet for this session.", meta: "" }]);
                } finally {
                    setStatus("ready");
                }
            }

            async function exportSession() {
                const response = await fetch(`/chat/api/export?session_id=${encodeURIComponent(sessionId)}`);
                if (!response.ok) {
                    addMessage("assistant", "Could not export session.");
                    return;
                }
                const text = await response.text();
                const blob = new Blob([text], { type: "application/x-ndjson" });
                const url = URL.createObjectURL(blob);
                const link = document.createElement("a");
                link.href = url;
                link.download = `${sessionId}.jsonl`;
                link.click();
                URL.revokeObjectURL(url);
            }

            return (
                <div className="shell">
                    <aside className="card side">
                        <h1>LIOS React Chat</h1>
                        <div className="muted">No-build React UI on top of LIOS APIs</div>

                        <label>Session ID</label>
                        <input value={sessionId} onChange={(e) => setSessionId(e.target.value)} />

                        <label>Jurisdictions</label>
                        <input value={jurisdictions} onChange={(e) => setJurisdictions(e.target.value)} placeholder="EU, Germany" />

                        <label>Company Profile JSON</label>
                        <textarea value={profile} onChange={(e) => setProfile(e.target.value)} />

                        <div className="row">
                            <button className="ghost" onClick={loadSession}>Load</button>
                            <button className="ghost" onClick={exportSession}>Export</button>
                        </div>
                    </aside>

                    <section className="card chat">
                        <header className="head">
                            <strong>React Chat Workspace</strong>
                            <span className="status">{status}</span>
                        </header>
                        <main className="log">
                            {messages.map((m, i) => (
                                <div key={i} className={`msg ${m.role === "user" ? "u" : "a"}`}>
                                    {m.text}
                                    {m.meta ? <div className="meta">{m.meta}</div> : null}
                                </div>
                            ))}
                        </main>
                        <footer className="compose">
                            <textarea
                                value={prompt}
                                onChange={(e) => setPrompt(e.target.value)}
                                onKeyDown={(e) => {
                                    if (e.key === "Enter" && !e.shiftKey) {
                                        e.preventDefault();
                                        sendMessage();
                                    }
                                }}
                                placeholder="Ask LIOS a compliance question..."
                            />
                            <button className="primary" onClick={sendMessage}>Send</button>
                        </footer>
                    </section>
                </div>
            );
        }

        ReactDOM.createRoot(document.getElementById("root")).render(<App />);
    </script>
</body>
</html>"""


@app.get("/debug/routes")
def list_routes() -> dict[str, list[str]]:
    """List registered routes to help diagnose local path mismatch issues."""
    paths = sorted({route.path for route in app.routes})
    return {"routes": paths}


@app.post("/chat/api/message")
def chat_message(payload: dict[str, Any]) -> dict[str, Any]:
    """Process one chat message and persist turn locally for training workflows."""
    query = (payload.get("query") or "").strip()
    if len(query) < 3:
        raise HTTPException(status_code=400, detail={"error": "query must be at least 3 characters"})

    session_id = (payload.get("session_id") or str(uuid.uuid4())).strip()
    company_profile = payload.get("company_profile") or None
    jurisdictions = payload.get("jurisdictions") or None
    direction_hint = _training_store.infer_session_direction(session_id=session_id, window=3)

    result = _engine.route_query(
        query=query,
        company_profile=company_profile,
        jurisdictions=jurisdictions,
        preferred_intent=(direction_hint or {}).get("intent"),
        preferred_regulation=(direction_hint or {}).get("regulation"),
        lightweight=None,
        concise=True,
    )

    citation_rows = [
        {
            "regulation": c.regulation,
            "article_id": c.article_id,
            "title": c.title,
            "relevance_score": c.relevance_score,
            "url": c.url,
        }
        for c in result.citations
    ]

    _training_store.append_turn(
        ChatTurn(
            timestamp=LocalTrainingStore.now_iso(),
            session_id=session_id,
            user_query=query,
            answer=result.answer,
            intent=result.intent,
            citations=citation_rows,
            metadata={
                "consensus_reached": result.consensus_result.consensus_reached,
                "confidence": result.consensus_result.confidence,
                "direction_hint": direction_hint,
                "agent_count": len(result.consensus_result.agent_responses),
            },
        )
    )

    return {
        "session_id": session_id,
        "answer": result.answer,
        "intent": result.intent,
        "citations": citation_rows,
        "consensus": {
            "reached": result.consensus_result.consensus_reached,
            "confidence": result.consensus_result.confidence,
        },
        "mode": {
            "lightweight": False,
            "agent_count": len(result.consensus_result.agent_responses),
            "direction_hint": direction_hint,
        },
    }


@app.get("/chat/api/history")
def chat_history(session_id: str) -> dict[str, Any]:
        """Load chat history for a local training session."""
        if not session_id.strip():
                raise HTTPException(status_code=400, detail={"error": "session_id is required"})
        return {"session_id": session_id, "turns": _training_store.list_session(session_id)}


@app.get("/chat/api/export")
def chat_export(session_id: str) -> HTMLResponse:
        """Export one session as JSONL suitable for prompt-tuning datasets."""
        if not session_id.strip():
                raise HTTPException(status_code=400, detail={"error": "session_id is required"})
        body = _training_store.export_session_jsonl(session_id)
        return HTMLResponse(
                content=body,
                media_type="application/x-ndjson",
                headers={"Content-Disposition": f"attachment; filename={session_id}.jsonl"},
        )


@app.post("/query", response_model=FullQueryResponse)
def query_endpoint(request: QueryRequest) -> FullQueryResponse:
    """Process a legal compliance query."""
    request_id = str(uuid.uuid4())
    
    with RequestLogger(logger, "Query processing", request_id=request_id, query=request.query[:100]):
        try:
            result = _engine.route_query(
                query=request.query,
                company_profile=request.company_profile.model_dump() if request.company_profile else None,
                jurisdictions=request.jurisdictions,
            )

            return FullQueryResponse(
                query=result.query,
                intent=result.intent,
                answer=result.answer,
                citations=[
                    {
                        "regulation": c.regulation,
                        "article_id": c.article_id,
                        "title": c.title,
                        "relevance_score": c.relevance_score,
                        "url": c.url,
                    }
                    for c in result.citations
                ],
                decay_scores=[
                    {
                        "regulation": d.regulation,
                        "score": d.score,
                        "freshness_label": d.freshness_label,
                        "days_since_update": d.days_since_update,
                        "last_updated": d.last_updated,
                    }
                    for d in result.decay_scores
                ],
                conflicts=[
                    {
                        "regulation": c.eu_regulation,
                        "jurisdiction_1": c.eu_regulation,
                        "jurisdiction_2": c.jurisdiction,
                        "conflict_type": c.conflict_type,
                        "description": c.description,
                        "severity": c.severity,
                    }
                    for c in result.conflicts
                ],
                consensus={
                    "reached": result.consensus_result.consensus_reached,
                    "confidence": result.consensus_result.confidence,
                    "agreeing_agents": result.consensus_result.agreeing_agents,
                    "diverging_agents": [
                        a.agent_name for a in result.consensus_result.agent_responses
                        if a.agent_name not in result.consensus_result.agreeing_agents
                    ],
                    "total_agents": len(result.consensus_result.agent_responses),
                },
                roadmap=_serialise_roadmap(result.roadmap),
                breakdown=_serialise_breakdown(result.breakdown),
                applicability=_serialise_applicability(result.applicability),
                metadata={"request_id": request_id},
            )
        except Exception as e:
            logger.error(f"Error processing query (request_id={request_id}): {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error="Internal server error while processing query",
                    error_type="internal",
                    request_id=request_id,
                ).model_dump(),
            )


@app.post("/applicability")
def applicability_endpoint(request: ApplicabilityRequest) -> dict[str, Any]:
    """Check if a regulation applies to a company."""
    request_id = str(uuid.uuid4())
    
    with RequestLogger(
        logger,
        "Applicability check",
        request_id=request_id,
        regulation=request.regulation,
    ):
        try:
            result = _applicability_checker.check_applicability(
                request.regulation,
                request.company_profile.model_dump(),
            )
            return {
                "regulation": result.regulation,
                "applicable": result.applicable,
                "reason": result.reason,
                "threshold_details": result.threshold_details,
                "articles_cited": result.articles_cited,
                "metadata": {"request_id": request_id},
            }
        except Exception as e:
            logger.error(
                f"Error checking applicability (request_id={request_id}): {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error="Error checking regulation applicability",
                    error_type="internal",
                    request_id=request_id,
                ).model_dump(),
            )


@app.post("/roadmap")
def roadmap_endpoint(request: RoadmapRequest) -> dict[str, Any]:
    """Generate a compliance roadmap."""
    request_id = str(uuid.uuid4())
    
    with RequestLogger(logger, "Roadmap generation", request_id=request_id):
        try:
            roadmap = _roadmap_generator.generate_roadmap(request.company_profile.model_dump())
            return {
                **(_serialise_roadmap(roadmap) or {}),
                "metadata": {"request_id": request_id},
            }
        except Exception as e:
            logger.error(
                f"Error generating roadmap (request_id={request_id}): {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error="Error generating compliance roadmap",
                    error_type="internal",
                    request_id=request_id,
                ).model_dump(),
            )


# ---- Serialisation helpers ----

def _serialise_roadmap(roadmap: Any) -> dict[str, Any] | None:
    """Serialize compliance roadmap to JSON-compatible dict."""
    if roadmap is None:
        return None
    return {
        "summary": roadmap.summary,
        "applicable_regulations": roadmap.applicable_regulations,
        "steps": [
            {
                "step_number": s.step_number,
                "title": s.title,
                "description": s.description,
                "deadline": s.deadline,
                "regulation": s.regulation,
                "priority": s.priority,
                "articles_cited": s.articles_cited,
            }
            for s in roadmap.steps
        ],
    }


def _serialise_breakdown(breakdown: Any) -> dict[str, Any] | None:
    """Serialize legal breakdown to JSON-compatible dict."""
    if breakdown is None:
        return None
    return {
        "topic": breakdown.topic,
        "regulation": breakdown.regulation,
        "summary": breakdown.summary,
        "key_articles": breakdown.key_articles,
        "obligations": breakdown.obligations,
        "penalties": breakdown.penalties,
        "timeline": breakdown.timeline,
    }


def _serialise_applicability(applicability: Any) -> dict[str, Any] | None:
    """Serialize applicability result to JSON-compatible dict."""
    if applicability is None:
        return None
    return {
        "regulation": applicability.regulation,
        "applicable": applicability.applicable,
        "reason": applicability.reason,
        "threshold_details": applicability.threshold_details,
        "articles_cited": applicability.articles_cited,
    }


# ---------------------------------------------------------------------------
# Carbon Accounting Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/carbon/calculate")
def carbon_calculate(request: CarbonCalculationRequest) -> dict[str, Any]:
    """Calculate GHG emissions (Scope 1, 2, 3) – GHG Protocol / CSRD ESRS E1 aligned."""
    request_id = str(uuid.uuid4())
    with RequestLogger(logger, "Carbon calculation", request_id=request_id):
        try:
            s1 = Scope1Input(
                natural_gas_mwh=request.scope1.natural_gas_mwh,
                diesel_litres=request.scope1.diesel_litres,
                petrol_litres=request.scope1.petrol_litres,
                coal_tonnes=request.scope1.coal_tonnes,
                fuel_oil_litres=request.scope1.fuel_oil_litres,
                lpg_litres=request.scope1.lpg_litres,
                process_emissions_tco2e=request.scope1.process_emissions_tco2e,
                notes=request.scope1.notes,
            )
            s2 = Scope2Input(
                electricity_mwh=request.scope2.electricity_mwh,
                district_heat_mwh=request.scope2.district_heat_mwh,
                steam_mwh=request.scope2.steam_mwh,
                country=request.scope2.country,
                use_market_based=request.scope2.use_market_based,
                market_based_factor=request.scope2.market_based_factor,
                notes=request.scope2.notes,
            )
            s3 = Scope3Input(
                steel_tonnes=request.scope3.steel_tonnes,
                aluminium_tonnes=request.scope3.aluminium_tonnes,
                concrete_tonnes=request.scope3.concrete_tonnes,
                plastics_tonnes=request.scope3.plastics_tonnes,
                paper_tonnes=request.scope3.paper_tonnes,
                chemicals_tonnes=request.scope3.chemicals_tonnes,
                other_purchased_goods_tco2e=request.scope3.other_purchased_goods_tco2e,
                road_freight_tonne_km=request.scope3.road_freight_tonne_km,
                sea_freight_tonne_km=request.scope3.sea_freight_tonne_km,
                air_freight_tonne_km=request.scope3.air_freight_tonne_km,
                rail_freight_tonne_km=request.scope3.rail_freight_tonne_km,
                air_travel_km=request.scope3.air_travel_km,
                car_travel_km=request.scope3.car_travel_km,
                rail_travel_km=request.scope3.rail_travel_km,
                employees=request.scope3.employees,
                waste_landfill_tonnes=request.scope3.waste_landfill_tonnes,
                waste_incineration_tonnes=request.scope3.waste_incineration_tonnes,
                waste_recycling_tonnes=request.scope3.waste_recycling_tonnes,
                cat2_capital_goods_tco2e=request.scope3.cat2_capital_goods_tco2e,
                cat3_fuel_energy_tco2e=request.scope3.cat3_fuel_energy_tco2e,
                cat5_waste_operations_tco2e=request.scope3.cat5_waste_operations_tco2e,
                cat8_upstream_leased_tco2e=request.scope3.cat8_upstream_leased_tco2e,
                cat9_downstream_transport_tco2e=request.scope3.cat9_downstream_transport_tco2e,
                cat10_processing_sold_products_tco2e=request.scope3.cat10_processing_sold_products_tco2e,
                cat11_use_sold_products_tco2e=request.scope3.cat11_use_sold_products_tco2e,
                cat13_downstream_leased_tco2e=request.scope3.cat13_downstream_leased_tco2e,
                cat14_franchises_tco2e=request.scope3.cat14_franchises_tco2e,
                cat15_investments_tco2e=request.scope3.cat15_investments_tco2e,
                notes=request.scope3.notes,
            )
            report = _carbon_engine.calculate(
                scope1=s1,
                scope2=s2,
                scope3=s3,
                company_name=request.company_name,
                reporting_year=request.reporting_year,
                employees=request.employees,
                revenue_meur=request.revenue_meur,
            )
            return {
                "company_name": report.company_name,
                "reporting_year": report.reporting_year,
                "scope1_total_tco2e": report.scope1_total_tco2e,
                "scope2_location_total_tco2e": report.scope2_location_total_tco2e,
                "scope2_market_total_tco2e": report.scope2_market_total_tco2e,
                "scope3_total_tco2e": report.scope3_total_tco2e,
                "total_tco2e": report.total_tco2e,
                "intensity_per_employee": report.intensity_per_employee,
                "intensity_per_revenue_meur": report.intensity_per_revenue_meur,
                "uncertainty_percent": report.uncertainty_percent,
                "methodology_notes": report.methodology_notes,
                "csrd_article": report.csrd_article,
                "esrs_datapoints": report.esrs_datapoints,
                "breakdown": [
                    {
                        "source": b.source,
                        "category": b.category,
                        "sub_category": b.sub_category,
                        "amount_tco2e": b.amount_tco2e,
                        "unit": b.unit,
                        "factor_used": b.factor_used,
                        "factor_source": b.factor_source,
                    }
                    for b in report.breakdown
                ],
                "metadata": {"request_id": request_id},
            }
        except Exception as e:
            logger.error(f"Error in carbon calculation (request_id={request_id}): {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error="Error calculating carbon emissions",
                    error_type="internal",
                    request_id=request_id,
                ).model_dump(),
            )


@app.get("/api/carbon/emission-factors")
def carbon_emission_factors() -> dict[str, Any]:
    """Return the built-in emission factors database (Scope 1, 2, 3)."""
    return {
        "emission_factors": _carbon_engine.get_emission_factors(),
        "sources": [
            "IPCC AR6 (2021)",
            "IEA World Energy Statistics 2023",
            "European Environment Agency (EEA) 2022",
            "GHG Protocol Corporate Standard",
        ],
        "metadata": {"unit": "tCO2e per stated input unit"},
    }


# ---------------------------------------------------------------------------
# Supply Chain Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/supply-chain/add-supplier")
def supply_chain_add_supplier(request: SupplierRegistrationRequest) -> dict[str, Any]:
    """Register a new supplier with ESG scores."""
    request_id = str(uuid.uuid4())
    with RequestLogger(logger, "Add supplier", request_id=request_id, supplier=request.name):
        try:
            supplier = _supply_chain_engine.add_supplier(
                name=request.name,
                country=request.country,
                sector=request.sector,
                tier=request.tier,
                environmental_score=request.environmental_score,
                social_score=request.social_score,
                governance_score=request.governance_score,
                data_quality=request.data_quality,
                annual_spend_eur=request.annual_spend_eur,
                employees=request.employees,
                contact_email=request.contact_email,
                website=request.website,
                certifications=request.certifications,
                notes=request.notes,
            )
            return {
                "supplier_id": supplier.supplier_id,
                "name": supplier.name,
                "country": supplier.country,
                "sector": supplier.sector,
                "tier": supplier.tier,
                "esg_scores": {
                    "environmental": supplier.esg_scores.environmental,
                    "social": supplier.esg_scores.social,
                    "governance": supplier.esg_scores.governance,
                    "composite": supplier.esg_scores.composite,
                    "data_quality": supplier.esg_scores.data_quality,
                },
                "created_at": supplier.created_at,
                "metadata": {"request_id": request_id},
            }
        except Exception as e:
            logger.error(f"Error adding supplier (request_id={request_id}): {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error="Error registering supplier",
                    error_type="internal",
                    request_id=request_id,
                ).model_dump(),
            )


@app.get("/api/supply-chain/suppliers")
def supply_chain_list_suppliers() -> dict[str, Any]:
    """List all registered suppliers."""
    suppliers = _supply_chain_engine.list_suppliers()
    return {
        "total": len(suppliers),
        "suppliers": [
            {
                "supplier_id": s.supplier_id,
                "name": s.name,
                "country": s.country,
                "sector": s.sector,
                "tier": s.tier,
                "composite_esg_score": s.esg_scores.composite,
                "annual_spend_eur": s.annual_spend_eur,
                "audit_status": s.audit_status,
                "certifications": s.certifications,
            }
            for s in suppliers
        ],
    }


@app.get("/api/supply-chain/risk-assessment")
def supply_chain_risk_assessment() -> dict[str, Any]:
    """Get risk assessment for all registered suppliers."""
    request_id = str(uuid.uuid4())
    with RequestLogger(logger, "Supply chain risk assessment", request_id=request_id):
        try:
            assessments = _supply_chain_engine.assess_all_risks()
            portfolio = _supply_chain_engine.get_portfolio_summary()
            return {
                "portfolio_summary": {
                    "total_suppliers": portfolio.total_suppliers,
                    "critical_count": portfolio.critical_count,
                    "high_count": portfolio.high_count,
                    "medium_count": portfolio.medium_count,
                    "low_count": portfolio.low_count,
                    "average_esg_score": portfolio.average_esg_score,
                    "total_annual_spend_eur": portfolio.total_annual_spend_eur,
                    "high_risk_spend_eur": portfolio.high_risk_spend_eur,
                    "coverage_percent": portfolio.coverage_percent,
                    "top_risks": portfolio.top_risks,
                    "csrd_compliance_status": portfolio.csrd_compliance_status,
                },
                "supplier_assessments": [
                    {
                        "supplier_id": a.supplier_id,
                        "supplier_name": a.supplier_name,
                        "overall_risk": a.overall_risk,
                        "overall_score": a.overall_score,
                        "csrd_compliance_gaps": a.csrd_compliance_gaps,
                        "recommended_actions": a.recommended_actions,
                        "assessment_date": a.assessment_date,
                        "due_diligence_complete": a.due_diligence_complete,
                        "risk_factors": [
                            {
                                "name": rf.name,
                                "score": rf.score,
                                "weighted_score": rf.weighted_score,
                                "description": rf.description,
                            }
                            for rf in a.risk_factors
                        ],
                    }
                    for a in assessments
                ],
                "metadata": {"request_id": request_id},
            }
        except Exception as e:
            logger.error(f"Error in risk assessment (request_id={request_id}): {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error="Error generating supply chain risk assessment",
                    error_type="internal",
                    request_id=request_id,
                ).model_dump(),
            )


@app.get("/api/supply-chain/due-diligence-checklist")
def supply_chain_checklist() -> dict[str, Any]:
    """Return the CSRD Art.8 / CSDDD due diligence checklist."""
    return {
        "checklist": _supply_chain_engine.get_checklist(),
        "csrd_reference": "CSRD Art.8 – Value chain due diligence",
        "csddd_reference": "CSDDD Art.5, 7, 9, 11",
    }


# ---------------------------------------------------------------------------
# Double Materiality (Business Impact) Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/impact/materiality")
def impact_materiality(request: MaterialityAssessmentRequest) -> dict[str, Any]:
    """Run a double materiality assessment (CSRD Art.4 / ESRS 1)."""
    request_id = str(uuid.uuid4())
    with RequestLogger(logger, "Materiality assessment", request_id=request_id):
        try:
            topic_inputs = [t.model_dump() for t in request.topics]
            matrix = _materiality_engine.assess(
                company_profile=request.company_profile,
                topic_inputs=topic_inputs,
            )
            return {
                "material_topics": matrix.material_topics,
                "mandatory_topics": matrix.mandatory_topics,
                "recommended_disclosures": matrix.recommended_disclosures,
                "assessment_summary": matrix.assessment_summary,
                "next_steps": matrix.next_steps,
                "csrd_article_references": matrix.csrd_article_references,
                "assessed_topics": [
                    {
                        "esrs_code": t.esrs_code,
                        "topic_name": t.topic_name,
                        "sub_topic": t.sub_topic,
                        "impact_score": t.impact_score,
                        "financial_score": t.financial_score,
                        "double_material": t.double_material,
                        "materiality_level": t.materiality_level,
                        "impact_material": t.impact_material,
                        "financial_material": t.financial_material,
                        "financial_time_horizon": t.financial_time_horizon,
                        "rationale": t.rationale,
                        "priority_actions": t.priority_actions,
                    }
                    for t in matrix.assessed_topics
                ],
                "metadata": {"request_id": request_id},
            }
        except Exception as e:
            logger.error(f"Error in materiality assessment (request_id={request_id}): {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error="Error running materiality assessment",
                    error_type="internal",
                    request_id=request_id,
                ).model_dump(),
            )


@app.get("/api/impact/esrs-topics")
def impact_esrs_topics() -> dict[str, Any]:
    """Return the full ESRS topic taxonomy for materiality assessment."""
    return {
        "topics": _materiality_engine.get_topic_catalog(),
        "reference": "ESRS 1, Appendix A – Full list of sustainability matters",
    }


@app.get("/api/impact/materiality-template")
def impact_materiality_template(sector: str = "manufacturing") -> dict[str, Any]:
    """Return a pre-populated materiality assessment template for a given sector."""
    inputs = _materiality_engine.create_default_assessment_inputs(sector=sector)
    return {
        "sector": sector,
        "topic_inputs": inputs,
        "instructions": (
            "Adjust scores (1–5) based on your company's situation before submitting "
            "to POST /api/impact/materiality. 1=low/unlikely, 5=severe/certain."
        ),
    }


# ---------------------------------------------------------------------------
# Dashboard endpoint
# ---------------------------------------------------------------------------

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> str:
    """Serve the LIOS sustainability dashboard."""
    return _build_dashboard_html()


def _build_dashboard_html() -> str:
    """Build the HTML for the LIOS sustainability dashboard."""
    return """<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>LIOS Dashboard – Sustainability Intelligence</title>
    <style>
        :root {
            --bg: #f4f1e8;
            --paper: #fffdf8;
            --ink: #1c2322;
            --muted: #61706c;
            --brand: #126d67;
            --accent: #cf642e;
            --line: #d9d2c6;
            --green: #2d8a6e;
            --amber: #d4872a;
            --red: #c0392b;
            --shadow: 0 8px 24px rgba(16,24,22,0.10);
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(160deg, #faf7f0 0%, #f1eee7 100%);
            color: var(--ink);
            min-height: 100vh;
        }
        nav {
            background: var(--brand);
            color: #fff;
            padding: 12px 32px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        nav h1 { font-size: 1.2rem; }
        nav a { color: #fff; text-decoration: none; margin-left: 20px; font-size: 0.9rem; opacity: 0.85; }
        nav a:hover { opacity: 1; }
        .container { max-width: 1280px; margin: 0 auto; padding: 24px 16px; }
        h2 { font-size: 1.4rem; color: var(--brand); margin-bottom: 16px; }
        h3 { font-size: 1rem; color: var(--ink); margin-bottom: 10px; }
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }
        .kpi-card {
            background: var(--paper);
            border: 1px solid var(--line);
            border-radius: 16px;
            padding: 20px;
            box-shadow: var(--shadow);
        }
        .kpi-card .value { font-size: 2rem; font-weight: 700; color: var(--brand); }
        .kpi-card .label { color: var(--muted); font-size: 0.82rem; margin-top: 4px; }
        .kpi-card .change { font-size: 0.78rem; margin-top: 6px; }
        .kpi-card .change.up { color: var(--red); }
        .kpi-card .change.down { color: var(--green); }
        .panels {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 32px;
        }
        .panel {
            background: var(--paper);
            border: 1px solid var(--line);
            border-radius: 16px;
            padding: 20px;
            box-shadow: var(--shadow);
        }
        .panel.full { grid-column: 1 / -1; }
        .bar-chart { margin-top: 12px; }
        .bar-row { display: flex; align-items: center; margin-bottom: 8px; gap: 10px; }
        .bar-label { width: 120px; font-size: 0.82rem; color: var(--muted); flex-shrink: 0; }
        .bar-track { flex: 1; background: #ece7dc; border-radius: 6px; height: 16px; overflow: hidden; }
        .bar-fill { height: 100%; border-radius: 6px; transition: width 0.6s ease; }
        .bar-val { width: 80px; text-align: right; font-size: 0.82rem; font-weight: 600; }
        .risk-table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.85rem; }
        .risk-table th { background: #ece7dc; padding: 8px 10px; text-align: left; }
        .risk-table td { padding: 8px 10px; border-bottom: 1px solid var(--line); }
        .badge {
            display: inline-block;
            padding: 2px 10px;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .badge.critical { background: #fde8e6; color: var(--red); }
        .badge.high { background: #fef3e0; color: var(--amber); }
        .badge.medium { background: #e8f4f1; color: #2d8a6e; }
        .badge.low { background: #e9f5f3; color: #1a7060; }
        .roadmap { margin-top: 12px; }
        .milestone {
            display: flex;
            gap: 14px;
            margin-bottom: 14px;
            align-items: flex-start;
        }
        .ms-dot {
            width: 16px; height: 16px; border-radius: 50%; flex-shrink: 0;
            margin-top: 3px;
        }
        .ms-dot.done { background: var(--green); }
        .ms-dot.active { background: var(--amber); }
        .ms-dot.pending { background: #c8c0b4; }
        .ms-content .ms-title { font-weight: 600; font-size: 0.9rem; }
        .ms-content .ms-date { color: var(--muted); font-size: 0.78rem; }
        .form-section {
            background: var(--paper);
            border: 1px solid var(--line);
            border-radius: 16px;
            padding: 24px;
            box-shadow: var(--shadow);
            margin-bottom: 24px;
        }
        label { display: block; font-size: 0.8rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; margin-top: 12px; }
        input, select, textarea {
            width: 100%; border: 1px solid var(--line); border-radius: 10px;
            padding: 10px 12px; font: inherit; background: #fff; color: var(--ink);
        }
        .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        button.primary {
            background: var(--brand); color: #fff; border: 0; border-radius: 10px;
            padding: 11px 24px; font: inherit; font-weight: 700; cursor: pointer;
            margin-top: 16px; transition: opacity 0.15s;
        }
        button.primary:hover { opacity: 0.88; }
        .result-box {
            background: #f0f8f5; border: 1px solid #b8ddd4; border-radius: 10px;
            padding: 16px; margin-top: 16px; font-family: monospace; font-size: 0.83rem;
            white-space: pre-wrap; display: none; max-height: 400px; overflow-y: auto;
        }
        .tabs { display: flex; gap: 4px; margin-bottom: 24px; flex-wrap: wrap; }
        .tab {
            padding: 8px 18px; border-radius: 999px; border: 1px solid var(--line);
            background: var(--paper); cursor: pointer; font-size: 0.85rem;
            font-weight: 600; color: var(--muted);
        }
        .tab.active { background: var(--brand); color: #fff; border-color: var(--brand); }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        @media (max-width: 768px) {
            .panels { grid-template-columns: 1fr; }
            .form-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <nav>
        <h1>🌿 LIOS – Sustainability Intelligence</h1>
        <div>
            <a href="/chat">Chat</a>
            <a href="/dashboard">Dashboard</a>
            <a href="/docs">API Docs</a>
        </div>
    </nav>
    <div class="container">

        <!-- KPI Cards -->
        <div style="margin: 24px 0 8px; display:flex; align-items:center; justify-content:space-between;">
            <h2>📊 Sustainability Overview</h2>
            <span style="font-size:0.8rem;color:var(--muted)">Demo data – connect your company data via the forms below</span>
        </div>
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="value" id="kpi-total-emissions">—</div>
                <div class="label">Total GHG Emissions (tCO₂e)</div>
                <div class="change" id="kpi-emissions-change">Calculate below ↓</div>
            </div>
            <div class="kpi-card">
                <div class="value" id="kpi-scope3-pct">—</div>
                <div class="label">Scope 3 Share (%)</div>
                <div class="change">Value chain emissions</div>
            </div>
            <div class="kpi-card">
                <div class="value" id="kpi-supplier-risk">—</div>
                <div class="label">High-Risk Suppliers</div>
                <div class="change">Add suppliers below ↓</div>
            </div>
            <div class="kpi-card">
                <div class="value" id="kpi-material-topics">—</div>
                <div class="label">Material ESRS Topics</div>
                <div class="change">Run DMA below ↓</div>
            </div>
            <div class="kpi-card">
                <div class="value" id="kpi-roadmap-pct">—</div>
                <div class="label">Roadmap Completion</div>
                <div class="change">Generate roadmap via Chat</div>
            </div>
        </div>

        <!-- Tabs -->
        <div class="tabs">
            <div class="tab active" onclick="switchTab('carbon')">🔥 Carbon Calculator</div>
            <div class="tab" onclick="switchTab('supply')">🔗 Supply Chain</div>
            <div class="tab" onclick="switchTab('materiality')">📋 Materiality</div>
            <div class="tab" onclick="switchTab('overview')">📈 Analysis</div>
        </div>

        <!-- Carbon Tab -->
        <div class="tab-content active" id="tab-carbon">
            <div class="form-section">
                <h3>🔥 GHG Emission Calculator (ESRS E1 – Scope 1, 2, 3)</h3>
                <div class="form-grid">
                    <div>
                        <label>Company Name</label>
                        <input id="c-company" value="My Company" />
                    </div>
                    <div>
                        <label>Reporting Year</label>
                        <input id="c-year" type="number" value="2024" />
                    </div>
                    <div>
                        <label>Employees</label>
                        <input id="c-employees" type="number" value="500" />
                    </div>
                    <div>
                        <label>Revenue (M EUR)</label>
                        <input id="c-revenue" type="number" value="120" />
                    </div>
                </div>
                <h3 style="margin-top:16px">Scope 1 – Direct Emissions</h3>
                <div class="form-grid">
                    <div><label>Natural Gas (MWh)</label><input id="s1-gas" type="number" value="1500" /></div>
                    <div><label>Diesel (litres)</label><input id="s1-diesel" type="number" value="20000" /></div>
                    <div><label>Petrol (litres)</label><input id="s1-petrol" type="number" value="5000" /></div>
                    <div><label>Process Emissions (tCO₂e)</label><input id="s1-process" type="number" value="0" /></div>
                </div>
                <h3 style="margin-top:16px">Scope 2 – Purchased Energy</h3>
                <div class="form-grid">
                    <div><label>Electricity (MWh)</label><input id="s2-elec" type="number" value="3000" /></div>
                    <div>
                        <label>Country (for grid factor)</label>
                        <select id="s2-country">
                            <option value="EU">EU Average</option>
                            <option value="Germany" selected>Germany</option>
                            <option value="France">France</option>
                            <option value="Poland">Poland</option>
                            <option value="Sweden">Sweden</option>
                            <option value="UK">UK</option>
                            <option value="US">US</option>
                        </select>
                    </div>
                    <div><label>District Heat (MWh)</label><input id="s2-heat" type="number" value="200" /></div>
                </div>
                <h3 style="margin-top:16px">Scope 3 – Value Chain (key categories)</h3>
                <div class="form-grid">
                    <div><label>Air Travel (km)</label><input id="s3-air" type="number" value="200000" /></div>
                    <div><label>Road Freight (tonne-km)</label><input id="s3-road" type="number" value="500000" /></div>
                    <div><label>Steel Purchased (tonnes)</label><input id="s3-steel" type="number" value="50" /></div>
                    <div><label>Paper Purchased (tonnes)</label><input id="s3-paper" type="number" value="10" /></div>
                </div>
                <button class="primary" onclick="calcCarbon()">⚡ Calculate Emissions</button>
                <div class="result-box" id="carbon-result"></div>
            </div>
        </div>

        <!-- Supply Chain Tab -->
        <div class="tab-content" id="tab-supply">
            <div class="form-section">
                <h3>🔗 Register Supplier (CSRD Art.8 Due Diligence)</h3>
                <div class="form-grid">
                    <div><label>Supplier Name</label><input id="sup-name" value="Supplier A" /></div>
                    <div><label>Country</label><input id="sup-country" value="Bangladesh" /></div>
                    <div><label>Sector</label><input id="sup-sector" value="textile" /></div>
                    <div>
                        <label>Supply Chain Tier</label>
                        <select id="sup-tier">
                            <option value="1" selected>Tier 1 (Direct)</option>
                            <option value="2">Tier 2</option>
                            <option value="3">Tier 3</option>
                        </select>
                    </div>
                    <div><label>Environmental Score (0–100)</label><input id="sup-env" type="number" value="40" /></div>
                    <div><label>Social Score (0–100)</label><input id="sup-soc" type="number" value="35" /></div>
                    <div><label>Governance Score (0–100)</label><input id="sup-gov" type="number" value="55" /></div>
                    <div><label>Annual Spend (EUR)</label><input id="sup-spend" type="number" value="500000" /></div>
                    <div><label>Employees</label><input id="sup-emp" type="number" value="2000" /></div>
                </div>
                <button class="primary" onclick="addSupplier()">➕ Register Supplier</button>
                <div class="result-box" id="supplier-result"></div>
                <button class="primary" onclick="getRiskAssessment()" style="margin-left:10px;background:#8a4020">📊 Run Risk Assessment</button>
                <div class="result-box" id="risk-result"></div>
            </div>
        </div>

        <!-- Materiality Tab -->
        <div class="tab-content" id="tab-materiality">
            <div class="form-section">
                <h3>📋 Double Materiality Assessment (CSRD Art.4 / ESRS 1)</h3>
                <p style="color:var(--muted);font-size:0.85rem;margin-bottom:12px">
                    Rate each dimension 1 (low) to 5 (high). The system applies the double materiality principle:
                    a topic is material if it exceeds the threshold on <em>either</em> impact or financial dimension.
                </p>
                <div class="form-grid">
                    <div>
                        <label>Company Name</label>
                        <input id="m-company" value="My Company" />
                    </div>
                    <div>
                        <label>Sector</label>
                        <select id="m-sector" onchange="loadTemplate()">
                            <option value="manufacturing">Manufacturing</option>
                            <option value="finance">Finance</option>
                            <option value="retail">Retail</option>
                        </select>
                    </div>
                </div>
                <div id="topic-table" style="margin-top:16px;overflow-x:auto">
                    <table style="width:100%;border-collapse:collapse;font-size:0.83rem">
                        <thead>
                            <tr style="background:#ece7dc">
                                <th style="padding:8px;text-align:left">ESRS</th>
                                <th style="padding:8px;text-align:left">Topic</th>
                                <th style="padding:8px">Impact Severity</th>
                                <th style="padding:8px">Impact Scale</th>
                                <th style="padding:8px">Impact Likelihood</th>
                                <th style="padding:8px">Financial Likelihood</th>
                                <th style="padding:8px">Financial Magnitude</th>
                                <th style="padding:8px">Time Horizon</th>
                            </tr>
                        </thead>
                        <tbody id="topic-rows">
                            <tr><td colspan="8" style="padding:12px;color:var(--muted)">Loading template…</td></tr>
                        </tbody>
                    </table>
                </div>
                <button class="primary" onclick="runMateriality()">🎯 Run Materiality Assessment</button>
                <div class="result-box" id="materiality-result"></div>
            </div>
        </div>

        <!-- Overview Tab -->
        <div class="tab-content" id="tab-overview">
            <div class="panels">
                <div class="panel">
                    <h3>Emissions by Scope</h3>
                    <div class="bar-chart" id="scope-bars">
                        <div style="color:var(--muted);font-size:0.85rem">Run a carbon calculation first →</div>
                    </div>
                </div>
                <div class="panel">
                    <h3>Supplier Risk Distribution</h3>
                    <div class="bar-chart" id="risk-bars">
                        <div style="color:var(--muted);font-size:0.85rem">Register suppliers and run risk assessment →</div>
                    </div>
                </div>
                <div class="panel full">
                    <h3>CSRD Compliance Roadmap Milestones</h3>
                    <div class="roadmap">
                        <div class="milestone">
                            <div class="ms-dot done"></div>
                            <div class="ms-content">
                                <div class="ms-title">Double Materiality Assessment (DMA)</div>
                                <div class="ms-date">Complete via Materiality tab above</div>
                            </div>
                        </div>
                        <div class="milestone">
                            <div class="ms-dot active"></div>
                            <div class="ms-content">
                                <div class="ms-title">GHG Baseline (Scope 1, 2, 3)</div>
                                <div class="ms-date">Complete via Carbon Calculator tab above – ESRS E1-6</div>
                            </div>
                        </div>
                        <div class="milestone">
                            <div class="ms-dot active"></div>
                            <div class="ms-content">
                                <div class="ms-title">Supply Chain Due Diligence</div>
                                <div class="ms-date">Register suppliers and run risk assessment – CSRD Art.8</div>
                            </div>
                        </div>
                        <div class="milestone">
                            <div class="ms-dot pending"></div>
                            <div class="ms-content">
                                <div class="ms-title">ESRS Data Collection Systems</div>
                                <div class="ms-date">Integrate all mandatory KPI data streams</div>
                            </div>
                        </div>
                        <div class="milestone">
                            <div class="ms-dot pending"></div>
                            <div class="ms-content">
                                <div class="ms-title">Sustainability Statement & Limited Assurance</div>
                                <div class="ms-date">Annual reporting per CSRD Art.3 – deadline per company category</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Tab switching
        function switchTab(name) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            document.querySelector(`#tab-${name}`).classList.add('active');
            event.target.classList.add('active');
        }

        // Carbon calculation
        async function calcCarbon() {
            const body = {
                company_name: document.getElementById('c-company').value,
                reporting_year: parseInt(document.getElementById('c-year').value),
                employees: parseInt(document.getElementById('c-employees').value),
                revenue_meur: parseFloat(document.getElementById('c-revenue').value),
                scope1: {
                    natural_gas_mwh: parseFloat(document.getElementById('s1-gas').value) || 0,
                    diesel_litres: parseFloat(document.getElementById('s1-diesel').value) || 0,
                    petrol_litres: parseFloat(document.getElementById('s1-petrol').value) || 0,
                    process_emissions_tco2e: parseFloat(document.getElementById('s1-process').value) || 0,
                },
                scope2: {
                    electricity_mwh: parseFloat(document.getElementById('s2-elec').value) || 0,
                    district_heat_mwh: parseFloat(document.getElementById('s2-heat').value) || 0,
                    country: document.getElementById('s2-country').value,
                },
                scope3: {
                    air_travel_km: parseFloat(document.getElementById('s3-air').value) || 0,
                    road_freight_tonne_km: parseFloat(document.getElementById('s3-road').value) || 0,
                    steel_tonnes: parseFloat(document.getElementById('s3-steel').value) || 0,
                    paper_tonnes: parseFloat(document.getElementById('s3-paper').value) || 0,
                    employees: parseInt(document.getElementById('c-employees').value) || 0,
                },
            };
            try {
                const res = await fetch('/api/carbon/calculate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(body),
                });
                const data = await res.json();
                const box = document.getElementById('carbon-result');
                box.style.display = 'block';
                box.textContent = JSON.stringify(data, null, 2);

                // Update KPIs
                document.getElementById('kpi-total-emissions').textContent =
                    (data.total_tco2e || 0).toLocaleString('en', {maximumFractionDigits: 0}) + ' tCO₂e';
                const s3pct = data.total_tco2e > 0
                    ? Math.round(data.scope3_total_tco2e / data.total_tco2e * 100) : 0;
                document.getElementById('kpi-scope3-pct').textContent = s3pct + '%';

                // Update scope bars
                const bars = document.getElementById('scope-bars');
                const max = data.total_tco2e || 1;
                bars.innerHTML = [
                    ['Scope 1', data.scope1_total_tco2e, '#c0392b'],
                    ['Scope 2', data.scope2_location_total_tco2e, '#d4872a'],
                    ['Scope 3', data.scope3_total_tco2e, '#2d8a6e'],
                ].map(([label, val, color]) => `
                    <div class="bar-row">
                        <span class="bar-label">${label}</span>
                        <div class="bar-track">
                            <div class="bar-fill" style="width:${Math.round(val/max*100)}%;background:${color}"></div>
                        </div>
                        <span class="bar-val">${(val||0).toLocaleString('en',{maximumFractionDigits:0})} t</span>
                    </div>`).join('');
            } catch(e) {
                alert('Error: ' + e.message);
            }
        }

        // Add supplier
        async function addSupplier() {
            const body = {
                name: document.getElementById('sup-name').value,
                country: document.getElementById('sup-country').value,
                sector: document.getElementById('sup-sector').value,
                tier: parseInt(document.getElementById('sup-tier').value),
                environmental_score: parseFloat(document.getElementById('sup-env').value),
                social_score: parseFloat(document.getElementById('sup-soc').value),
                governance_score: parseFloat(document.getElementById('sup-gov').value),
                annual_spend_eur: parseFloat(document.getElementById('sup-spend').value) || 0,
                employees: parseInt(document.getElementById('sup-emp').value) || 0,
            };
            try {
                const res = await fetch('/api/supply-chain/add-supplier', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(body),
                });
                const data = await res.json();
                const box = document.getElementById('supplier-result');
                box.style.display = 'block';
                box.textContent = JSON.stringify(data, null, 2);
            } catch(e) { alert('Error: ' + e.message); }
        }

        // Risk assessment
        async function getRiskAssessment() {
            try {
                const res = await fetch('/api/supply-chain/risk-assessment');
                const data = await res.json();
                const box = document.getElementById('risk-result');
                box.style.display = 'block';
                box.textContent = JSON.stringify(data, null, 2);

                // Update KPI
                const p = data.portfolio_summary || {};
                document.getElementById('kpi-supplier-risk').textContent =
                    ((p.critical_count || 0) + (p.high_count || 0)) + ' suppliers';

                // Update risk bars
                const bars = document.getElementById('risk-bars');
                const total = p.total_suppliers || 1;
                bars.innerHTML = [
                    ['Critical', p.critical_count || 0, '#c0392b'],
                    ['High', p.high_count || 0, '#d4872a'],
                    ['Medium', p.medium_count || 0, '#2d8a6e'],
                    ['Low', p.low_count || 0, '#5dade2'],
                ].map(([label, val, color]) => `
                    <div class="bar-row">
                        <span class="bar-label">${label}</span>
                        <div class="bar-track">
                            <div class="bar-fill" style="width:${Math.round(val/total*100)}%;background:${color}"></div>
                        </div>
                        <span class="bar-val">${val} suppliers</span>
                    </div>`).join('');
            } catch(e) { alert('Error: ' + e.message); }
        }

        // Load materiality template
        async function loadTemplate() {
            const sector = document.getElementById('m-sector').value;
            try {
                const res = await fetch(`/api/impact/materiality-template?sector=${sector}`);
                const data = await res.json();
                const tbody = document.getElementById('topic-rows');
                tbody.innerHTML = (data.topic_inputs || []).map(t => `
                    <tr>
                        <td style="padding:6px 8px;font-weight:600">${t.esrs_code}</td>
                        <td style="padding:6px 8px">${t.sub_topic}</td>
                        <td><input type="number" min="1" max="5" step="0.5"
                            value="${t.impact_severity}" style="width:60px;padding:4px;text-align:center"
                            data-code="${t.esrs_code}" data-field="impact_severity"></td>
                        <td><input type="number" min="1" max="5" step="0.5"
                            value="${t.impact_scale}" style="width:60px;padding:4px;text-align:center"
                            data-code="${t.esrs_code}" data-field="impact_scale"></td>
                        <td><input type="number" min="1" max="5" step="0.5"
                            value="${t.impact_likelihood}" style="width:60px;padding:4px;text-align:center"
                            data-code="${t.esrs_code}" data-field="impact_likelihood"></td>
                        <td><input type="number" min="1" max="5" step="0.5"
                            value="${t.financial_likelihood}" style="width:60px;padding:4px;text-align:center"
                            data-code="${t.esrs_code}" data-field="financial_likelihood"></td>
                        <td><input type="number" min="1" max="5" step="0.5"
                            value="${t.financial_magnitude}" style="width:60px;padding:4px;text-align:center"
                            data-code="${t.esrs_code}" data-field="financial_magnitude"></td>
                        <td>
                            <select data-code="${t.esrs_code}" data-field="financial_time_horizon" style="padding:4px">
                                <option value="short" ${t.financial_time_horizon==='short'?'selected':''}>Short</option>
                                <option value="medium" ${t.financial_time_horizon==='medium'?'selected':''}>Medium</option>
                                <option value="long" ${t.financial_time_horizon==='long'?'selected':''}>Long</option>
                            </select>
                        </td>
                    </tr>
                `).join('');
            } catch(e) { console.error(e); }
        }

        // Run materiality assessment
        async function runMateriality() {
            const rows = document.getElementById('topic-rows').querySelectorAll('tr');
            const topics = [];
            rows.forEach(row => {
                const inputs = row.querySelectorAll('[data-code]');
                if (!inputs.length) return;
                const code = inputs[0].dataset.code;
                const t = { esrs_code: code, sub_topic: code };
                inputs.forEach(inp => { t[inp.dataset.field] = isNaN(inp.value) ? inp.value : parseFloat(inp.value); });
                topics.push(t);
            });
            const body = {
                company_profile: { name: document.getElementById('m-company').value,
                    sector: document.getElementById('m-sector').value },
                topics,
            };
            try {
                const res = await fetch('/api/impact/materiality', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(body),
                });
                const data = await res.json();
                const box = document.getElementById('materiality-result');
                box.style.display = 'block';
                box.textContent = JSON.stringify(data, null, 2);

                // Update KPI
                document.getElementById('kpi-material-topics').textContent =
                    (data.material_topics || []).length + ' topics';
            } catch(e) { alert('Error: ' + e.message); }
        }

        // Initial load
        loadTemplate();
    </script>
</body>
</html>"""


# ── Mobile app endpoints ───────────────────────────────────────────────────────
# In-memory stores for brain state, rules, corrections and learn progress.
# These reset on server restart; good enough for local dev use.

import httpx
from pydantic import BaseModel as _BM

_brain_on: bool = False
_brain_toggled_at: Optional[str] = None

_rules: dict[str, dict] = {}
_corrections: list[dict] = []

_LEARN_TOPICS: list[dict] = [
    {"id": "csrd-basics", "name": "CSRD Basics", "category": "CSRD", "description": "Corporate Sustainability Reporting Directive scope and thresholds"},
    {"id": "esrs-e1", "name": "ESRS E1 Climate", "category": "ESRS", "description": "Climate change mitigation and adaptation disclosures"},
    {"id": "esrs-s1", "name": "ESRS S1 Workforce", "category": "ESRS", "description": "Own workforce social standards and disclosures"},
    {"id": "eu-taxonomy", "name": "EU Taxonomy", "category": "EU Taxonomy", "description": "Sustainable activity classification criteria"},
    {"id": "sfdr-basics", "name": "SFDR PAI", "category": "SFDR", "description": "Principal Adverse Impact indicators for financial products"},
    {"id": "gdpr-data", "name": "GDPR Data Subject Rights", "category": "GDPR", "description": "Individual rights and controller obligations"},
    {"id": "supply-chain-lksg", "name": "LkSG Due Diligence", "category": "Supply Chain", "description": "German Supply Chain Act obligations"},
]
_learn_progress: dict[str, dict] = {
    t["id"]: {"status": "unknown", "pct": 0, "last_updated": None} for t in _LEARN_TOPICS
}


async def _ollama_reachable() -> bool:
    try:
        base = settings.LLM_BASE_URL.rstrip("/").removesuffix("/v1")
        async with httpx.AsyncClient(timeout=2.0) as c:
            r = await c.get(f"{base}/api/tags")
            return r.status_code == 200
    except Exception:
        return False


class _BrainToggleReq(_BM):
    enabled: bool

class _AddRuleReq(_BM):
    rule_text: str
    topic: str = "general"

class _FeedbackReq(_BM):
    session_id: str
    message_id: str
    query: str
    original_answer: str
    feedback_type: str  # good | wrong | partial
    correction_text: Optional[str] = None
    make_rule: bool = False

class _LearnAnswerReq(_BM):
    topic_id: str
    answer_text: str
    reference: str = ""


@app.get("/brain/status")
async def brain_status():
    reachable = await _ollama_reachable()
    chunk_count = 0
    try:
        from lios.retrieval.hybrid_retriever import HybridRetriever
        hr = HybridRetriever.get_instance()
        chunk_count = len(hr._chunks) if hasattr(hr, "_chunks") else 0
    except Exception:
        pass
    active_rules = sum(1 for r in _rules.values() if r.get("active", True))
    return {
        "brain_on": _brain_on,
        "model": settings.LLM_MODEL,
        "base_url": settings.LLM_BASE_URL,
        "llm_reachable": reachable,
        "knowledge_chunks": chunk_count,
        "active_rules": active_rules,
        "total_corrections": len(_corrections),
        "toggled_at": _brain_toggled_at,
    }


@app.post("/brain/toggle")
async def brain_toggle(body: _BrainToggleReq):
    global _brain_on, _brain_toggled_at
    _brain_on = body.enabled
    _brain_toggled_at = datetime.now(timezone.utc).isoformat()
    reachable = await _ollama_reachable()
    active_rules = sum(1 for r in _rules.values() if r.get("active", True))
    return {
        "brain_on": _brain_on,
        "model": settings.LLM_MODEL,
        "base_url": settings.LLM_BASE_URL,
        "llm_reachable": reachable,
        "knowledge_chunks": 0,
        "active_rules": active_rules,
        "total_corrections": len(_corrections),
        "toggled_at": _brain_toggled_at,
    }


@app.get("/memory/rules")
async def memory_rules():
    active = [r for r in _rules.values() if r.get("active", True)]
    return {"rules": active, "total": len(active)}


@app.post("/memory/rules")
async def memory_add_rule(body: _AddRuleReq):
    rule_id = str(uuid.uuid4())[:8]
    rule = {
        "id": rule_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": "user",
        "topic": body.topic,
        "rule_text": body.rule_text,
        "active": True,
    }
    _rules[rule_id] = rule
    return {"created": True, "rule": rule}


@app.delete("/memory/rules/{rule_id}")
async def memory_delete_rule(rule_id: str):
    if rule_id not in _rules:
        raise HTTPException(status_code=404, detail="Rule not found")
    _rules[rule_id]["active"] = False
    return {"deactivated": True}


@app.get("/memory/corrections")
async def memory_corrections(limit: int = 50):
    recent = _corrections[-limit:][::-1]
    return {"corrections": recent, "total": len(_corrections)}


@app.post("/feedback")
async def submit_feedback(body: _FeedbackReq):
    record = {
        "id": str(uuid.uuid4())[:8],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "session_id": body.session_id,
        "user_query": body.query,
        "feedback_type": body.feedback_type,
        "correction_text": body.correction_text or "",
        "made_rule": False,
    }
    _corrections.append(record)
    rule_created = False
    if body.make_rule and body.correction_text:
        rule_id = str(uuid.uuid4())[:8]
        _rules[rule_id] = {
            "id": rule_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source": "feedback",
            "topic": "general",
            "rule_text": body.correction_text,
            "active": True,
        }
        record["made_rule"] = True
        rule_created = True
    return {"stored": True, "rule_created": rule_created, "message": "Feedback recorded"}


@app.get("/learn/next")
async def learn_next():
    for t in _LEARN_TOPICS:
        prog = _learn_progress[t["id"]]
        if prog["status"] != "mastered":
            return {
                "all_mastered": False,
                "topic": {**t, "status": prog["status"], "pct": prog["pct"]},
                "question": f"Explain the key obligations under {t['name']} in one sentence.",
            }
    return {"all_mastered": True, "topic": None, "question": None}


@app.post("/learn/answer")
async def learn_answer(body: _LearnAnswerReq):
    if body.topic_id not in _learn_progress:
        raise HTTPException(status_code=404, detail="Topic not found")
    prog = _learn_progress[body.topic_id]
    new_pct = min(prog["pct"] + 25, 100)
    status = "mastered" if new_pct >= 100 else ("functional" if new_pct >= 50 else "learning")
    prog.update({"pct": new_pct, "status": status, "last_updated": datetime.now(timezone.utc).isoformat()})
    topic_meta = next(t for t in _LEARN_TOPICS if t["id"] == body.topic_id)
    overall = int(sum(p["pct"] for p in _learn_progress.values()) / len(_learn_progress))
    next_topic = next(
        (t["id"] for t in _LEARN_TOPICS if _learn_progress[t["id"]]["status"] != "mastered" and t["id"] != body.topic_id),
        None,
    )
    return {
        "topic_updated": {**topic_meta, **prog},
        "overall_pct": overall,
        "next_topic": next_topic,
    }


@app.get("/learn/map")
async def learn_map():
    from collections import defaultdict
    cats: dict[str, list] = defaultdict(list)
    for t in _LEARN_TOPICS:
        prog = _learn_progress[t["id"]]
        cats[t["category"]].append({
            "id": t["id"], "name": t["name"],
            "status": prog["status"], "pct": prog["pct"],
            "last_updated": prog["last_updated"],
        })
    mastered = sum(1 for p in _learn_progress.values() if p["status"] == "mastered")
    functional = sum(1 for p in _learn_progress.values() if p["status"] == "functional")
    learning = sum(1 for p in _learn_progress.values() if p["status"] == "learning")
    unknown = sum(1 for p in _learn_progress.values() if p["status"] == "unknown")
    overall = int(sum(p["pct"] for p in _learn_progress.values()) / len(_learn_progress))
    return {
        "overall_pct": overall,
        "total_topics": len(_LEARN_TOPICS),
        "mastered": mastered,
        "functional": functional,
        "learning": learning,
        "unknown": unknown,
        "categories": dict(cats),
    }

