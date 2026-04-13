-- 001_initial.sql
-- Baseline schema for LIOS.  Applied automatically on startup via SQLAlchemy
-- (see lios/database/connection.py::init_db).  This file is kept for
-- reference and manual migrations only.

CREATE TABLE IF NOT EXISTS regulations (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    short_name  TEXT NOT NULL,
    framework   TEXT NOT NULL,          -- e.g. CSRD | ESRS | EU_TAXONOMY | SFDR
    jurisdiction TEXT NOT NULL DEFAULT 'EU',
    article_ref TEXT,                   -- e.g. "Art. 3(1)"
    content     TEXT NOT NULL,
    source_url  TEXT,
    published_at TIMESTAMP,
    last_verified_at TIMESTAMP,
    version     TEXT DEFAULT '1.0',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_regulations_framework ON regulations(framework);
CREATE INDEX IF NOT EXISTS idx_regulations_jurisdiction ON regulations(jurisdiction);

CREATE TABLE IF NOT EXISTS queries (
    id              TEXT PRIMARY KEY,
    user_query      TEXT NOT NULL,
    resolved_answer TEXT,
    consensus_score REAL,
    decay_score     REAL,
    conflict_flags  TEXT,               -- JSON array of detected conflicts
    citations       TEXT,               -- JSON array of citation objects
    agent_responses TEXT,               -- JSON object {agent_id: response}
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_queries_created ON queries(created_at);
