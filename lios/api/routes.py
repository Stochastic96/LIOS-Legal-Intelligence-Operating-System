"""FastAPI routes for LIOS."""

from __future__ import annotations

from datetime import datetime, timezone
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from lios.config import settings
from lios.features.applicability_checker import ApplicabilityChecker
from lios.features.chat_training import ChatTurn, LocalTrainingStore
from lios.features.compliance_roadmap import ComplianceRoadmapGenerator
from lios.knowledge.regulatory_db import RegulatoryDatabase
from lios.logging_setup import RequestLogger, get_logger
from lios.models.validation import (
    ApplicabilityRequest,
    ErrorResponse,
    FullQueryResponse,
    HealthResponse,
    QueryRequest,
    RoadmapRequest,
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
        # Keep user questions lightweight unless a company context is explicitly provided.
        lightweight=None if company_profile else True,
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
            "lightweight": (None if company_profile else True),
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

