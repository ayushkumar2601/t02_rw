"""Repository for session persistence and transcript logging in SQLite."""

from datetime import datetime, timezone
from typing import List, Optional
import aiosqlite

from app.models.session import Session, utc_now
from app.repositories.database import DatabaseManager, db_manager
from app.schemas.conversation import ConversationState, SessionStatus, Speaker, TranscriptTurnItem
from app.schemas.lead import QualificationStatus, ValidatedLead


class SessionRepository:
    """Handles CRUD operations for sessions and transcript turns."""

    def __init__(self, manager: Optional[DatabaseManager] = None):
        self.manager = manager or db_manager

    async def save_session(self, session: Session) -> None:
        """Insert or update a session record."""
        session.updated_at = utc_now()
        async with self.manager.get_connection() as conn:
            await conn.execute(
                """
                INSERT INTO sessions (
                    session_id, current_state, session_status, qualification_status,
                    validated_lead_json, size_clarification_count, budget_clarification_count,
                    last_processed_turn_id, last_response, created_at, updated_at, ended_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    current_state = excluded.current_state,
                    session_status = excluded.session_status,
                    qualification_status = excluded.qualification_status,
                    validated_lead_json = excluded.validated_lead_json,
                    size_clarification_count = excluded.size_clarification_count,
                    budget_clarification_count = excluded.budget_clarification_count,
                    last_processed_turn_id = excluded.last_processed_turn_id,
                    last_response = excluded.last_response,
                    updated_at = excluded.updated_at,
                    ended_at = excluded.ended_at
                """,
                (
                    session.session_id,
                    session.current_state.value,
                    session.session_status.value,
                    session.qualification_status.value,
                    session.validated_lead.model_dump_json(),
                    session.size_clarification_count,
                    session.budget_clarification_count,
                    session.last_processed_turn_id,
                    session.last_response,
                    session.created_at.isoformat(),
                    session.updated_at.isoformat(),
                    session.ended_at.isoformat() if session.ended_at else None,
                ),
            )
            await conn.commit()

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Retrieve a session by its unique session_id."""
        async with self.manager.get_connection() as conn:
            async with conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None

                created_at = datetime.fromisoformat(row["created_at"])
                updated_at = datetime.fromisoformat(row["updated_at"])
                ended_at = datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None

                validated_lead = ValidatedLead()
                if "validated_lead_json" in row.keys() and row["validated_lead_json"]:
                    try:
                        validated_lead = ValidatedLead.model_validate_json(row["validated_lead_json"])
                    except Exception:
                        pass

                return Session(
                    session_id=row["session_id"],
                    current_state=ConversationState(row["current_state"]),
                    session_status=SessionStatus(row["session_status"]),
                    qualification_status=QualificationStatus(row["qualification_status"]),
                    validated_lead=validated_lead,
                    size_clarification_count=row["size_clarification_count"],
                    budget_clarification_count=row["budget_clarification_count"],
                    last_processed_turn_id=row["last_processed_turn_id"],
                    last_response=row["last_response"],
                    created_at=created_at,
                    updated_at=updated_at,
                    ended_at=ended_at,
                )

    async def add_transcript_turn(
        self,
        session_id: str,
        turn_id: str,
        speaker: Speaker,
        text: str,
        created_at: Optional[datetime] = None,
    ) -> bool:
        """Add a turn to the transcript.

        Returns True if inserted, False if turn_id already existed for this session.
        """
        ts = created_at or utc_now()
        async with self.manager.get_connection() as conn:
            try:
                await conn.execute(
                    """
                    INSERT INTO transcript_turns (turn_id, session_id, speaker, text, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (turn_id, session_id, speaker.value, text, ts.isoformat()),
                )
                await conn.commit()
                return True
            except aiosqlite.IntegrityError:
                # Turn already recorded for this session (idempotency check)
                return False

    async def has_turn(self, session_id: str, turn_id: str) -> bool:
        """Check if a turn_id has already been processed for this session."""
        async with self.manager.get_connection() as conn:
            async with conn.execute(
                "SELECT 1 FROM transcript_turns WHERE session_id = ? AND turn_id = ?",
                (session_id, turn_id),
            ) as cursor:
                row = await cursor.fetchone()
                return row is not None

    async def get_transcript(self, session_id: str) -> List[TranscriptTurnItem]:
        """Fetch all transcript turns for a session in chronological order."""
        async with self.manager.get_connection() as conn:
            async with conn.execute(
                """
                SELECT turn_id, session_id, speaker, text, created_at
                FROM transcript_turns
                WHERE session_id = ?
                ORDER BY created_at ASC, rowid ASC
                """,
                (session_id,),
            ) as cursor:
                rows = await cursor.fetchall()
                return [
                    TranscriptTurnItem(
                        turn_id=row["turn_id"],
                        session_id=row["session_id"],
                        speaker=Speaker(row["speaker"]),
                        text=row["text"],
                        created_at=datetime.fromisoformat(row["created_at"]),
                    )
                    for row in rows
                ]


session_repository = SessionRepository()
