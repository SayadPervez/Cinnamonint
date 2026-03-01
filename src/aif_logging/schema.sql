-- AIF Logging Schema
-- Database: logs.db

CREATE TABLE IF NOT EXISTS prompts (
    id              INTEGER PRIMARY KEY,
    timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    input_text      TEXT NOT NULL,
    final_output    TEXT,
    iteration_count INTEGER,
    status          TEXT DEFAULT 'ok'
);

CREATE TABLE IF NOT EXISTS iterations (
    id              INTEGER PRIMARY KEY,
    prompt_id       INTEGER NOT NULL REFERENCES prompts(id) ON DELETE CASCADE,
    iteration_num   INTEGER NOT NULL,
    sentence_before TEXT NOT NULL,
    token_processed TEXT,
    handler_path    TEXT,
    sentence_after  TEXT NOT NULL,
    duration_ms     INTEGER,
    timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS learning_events (
    id          INTEGER PRIMARY KEY,
    timestamp   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    token_name  TEXT NOT NULL,
    action      TEXT NOT NULL,
    details     TEXT,
    source      TEXT DEFAULT 'local'
);

CREATE TABLE IF NOT EXISTS execution_log (
    id              INTEGER PRIMARY KEY,
    prompt_id       INTEGER REFERENCES prompts(id) ON DELETE SET NULL,
    timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    token_name      TEXT,
    action_type     TEXT NOT NULL,
    command         TEXT,
    path            TEXT,
    url             TEXT,
    exit_code       INTEGER,
    details         TEXT
);

CREATE INDEX IF NOT EXISTS idx_prompts_timestamp ON prompts(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_iterations_prompt ON iterations(prompt_id);
CREATE INDEX IF NOT EXISTS idx_exec_log_timestamp ON execution_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_exec_log_prompt ON execution_log(prompt_id);
