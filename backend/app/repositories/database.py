"""SQLite database connection and schema management using aiosqlite.

Provides connection pooling/management, automatic table creation,
and transactional safety.
"""

import aiosqlite
import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger("voice_agent.database")

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    current_state TEXT NOT NULL,
    session_status TEXT NOT NULL,
    qualification_status TEXT NOT NULL,
    validated_lead_json TEXT NOT NULL DEFAULT '{}',
    size_clarification_count INTEGER NOT NULL DEFAULT 0,
    budget_clarification_count INTEGER NOT NULL DEFAULT 0,
    last_processed_turn_id TEXT,
    last_response TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    ended_at TEXT
);

CREATE TABLE IF NOT EXISTS transcript_turns (
    turn_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    speaker TEXT NOT NULL,
    text TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (session_id, turn_id),
    FOREIGN KEY (session_id) REFERENCES sessions (session_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS leads (
    lead_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE,
    company_name TEXT,
    business_type TEXT,
    company_size INTEGER,
    marketing_budget REAL,
    budget_currency TEXT,
    budget_period TEXT NOT NULL,
    contact_name TEXT,
    contact_email TEXT,
    qualification_status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions (session_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_transcript_session ON transcript_turns (session_id, created_at ASC);
"""


from contextlib import asynccontextmanager


class DatabaseManager:
    """Manages SQLite connections and schema initialization."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.DATABASE_PATH

    @asynccontextmanager
    async def get_connection(self):
        """Yield an active aiosqlite connection with row factory and foreign keys enabled."""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA foreign_keys = ON;")
            yield conn

    async def init_db(self) -> None:
        """Initialize database schema automatically if tables do not exist."""
        async with self.get_connection() as conn:
            await conn.executescript(SCHEMA_SQL)
            await conn.commit()
            logger.info("Database initialized successfully at %s", self.db_path)


db_manager = DatabaseManager()
