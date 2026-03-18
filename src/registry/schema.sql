-- Cinnamonint Token Registry Schema
-- Database: registry.db

CREATE TABLE IF NOT EXISTS tokens (
    id            INTEGER PRIMARY KEY,
    name          TEXT UNIQUE NOT NULL,
    category      TEXT NOT NULL,
    priority      INTEGER DEFAULT 1,
    handler_path  TEXT NOT NULL,
    test_path     TEXT,
    destructive   BOOLEAN DEFAULT 0,
    downloads     BOOLEAN DEFAULT 0,
    uploads       BOOLEAN DEFAULT 0,
    approved      BOOLEAN DEFAULT 0,
    author        TEXT DEFAULT 'local',
    source        TEXT DEFAULT 'seed',
    version       TEXT DEFAULT '1.0.0',
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS aliases (
    id        INTEGER PRIMARY KEY,
    token_id  INTEGER NOT NULL REFERENCES tokens(id) ON DELETE CASCADE,
    alias     TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS approvals (
    id              INTEGER PRIMARY KEY,
    token_id        INTEGER NOT NULL REFERENCES tokens(id) ON DELETE CASCADE,
    command_hash    TEXT NOT NULL,
    command_display TEXT NOT NULL,
    approved_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(token_id, command_hash)
);

CREATE INDEX IF NOT EXISTS idx_aliases_token ON aliases(token_id);
CREATE INDEX IF NOT EXISTS idx_aliases_alias ON aliases(alias);
CREATE INDEX IF NOT EXISTS idx_approvals_token ON approvals(token_id);
