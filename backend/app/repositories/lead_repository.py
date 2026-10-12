"""Repository for persisting and retrieving validated leads from SQLite.

Ensures uniqueness per session (preventing duplicate leads), uses transactions,
and orders records in reverse chronological order.
"""

from datetime import datetime
import uuid
from typing import List, Optional

from app.models.session import utc_now
from app.repositories.database import DatabaseManager, db_manager
from app.schemas.lead import BudgetPeriod, PersistedLeadRecord, QualificationStatus, ValidatedLead


class LeadRepository:
    """CRUD operations for validated leads in SQLite."""

    def __init__(self, manager: Optional[DatabaseManager] = None):
        self.manager = manager or db_manager

    async def save_lead(
        self,
        session_id: str,
        lead: ValidatedLead,
        qualification_status: QualificationStatus,
        lead_id: Optional[str] = None,
    ) -> PersistedLeadRecord:
        """Insert or update a lead record for a given session.

        Guarantees that a session has at most one lead record, preventing duplicates.
        """
        now = utc_now()
        existing = await self.get_lead_by_session_id(session_id)
        effective_lead_id = existing.lead_id if existing else (lead_id or f"lead_{uuid.uuid4().hex[:12]}")
        created_at = existing.created_at if existing else now

        async with self.manager.get_connection() as conn:
            await conn.execute(
                """
                INSERT INTO leads (
                    lead_id, session_id, company_name, business_type, company_size,
                    marketing_budget, budget_currency, budget_period,
                    contact_name, contact_email, qualification_status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    company_name = excluded.company_name,
                    business_type = excluded.business_type,
                    company_size = excluded.company_size,
                    marketing_budget = excluded.marketing_budget,
                    budget_currency = excluded.budget_currency,
                    budget_period = excluded.budget_period,
                    contact_name = excluded.contact_name,
                    contact_email = excluded.contact_email,
                    qualification_status = excluded.qualification_status,
                    updated_at = excluded.updated_at
                """,
                (
                    effective_lead_id,
                    session_id,
                    lead.company_name,
                    lead.business_type,
                    lead.company_size,
                    lead.marketing_budget,
                    lead.budget_currency,
                    lead.budget_period.value,
                    lead.contact_name,
                    lead.contact_email,
                    qualification_status.value,
                    created_at.isoformat(),
                    now.isoformat(),
                ),
            )
            await conn.commit()

        return PersistedLeadRecord(
            lead_id=effective_lead_id,
            session_id=session_id,
            company_name=lead.company_name,
            business_type=lead.business_type,
            company_size=lead.company_size,
            marketing_budget=lead.marketing_budget,
            budget_currency=lead.budget_currency,
            budget_period=lead.budget_period,
            contact_name=lead.contact_name,
            contact_email=lead.contact_email,
            qualification_status=qualification_status,
            created_at=created_at,
            updated_at=now,
        )

    async def get_lead_by_id(self, lead_id: str) -> Optional[PersistedLeadRecord]:
        """Fetch a single lead by its lead_id."""
        async with self.manager.get_connection() as conn:
            async with conn.execute(
                "SELECT * FROM leads WHERE lead_id = ?", (lead_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None
                return self._row_to_record(row)

    async def get_lead_by_session_id(self, session_id: str) -> Optional[PersistedLeadRecord]:
        """Fetch lead associated with a specific session_id."""
        async with self.manager.get_connection() as conn:
            async with conn.execute(
                "SELECT * FROM leads WHERE session_id = ?", (session_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None
                return self._row_to_record(row)

    async def list_leads(self, limit: int = 50, offset: int = 0) -> List[PersistedLeadRecord]:
        """Fetch persisted leads in reverse chronological order."""
        async with self.manager.get_connection() as conn:
            async with conn.execute(
                """
                SELECT * FROM leads
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_record(r) for r in rows]

    def _row_to_record(self, row) -> PersistedLeadRecord:
        """Convert a database row into a validated PersistedLeadRecord."""
        return PersistedLeadRecord(
            lead_id=row["lead_id"],
            session_id=row["session_id"],
            company_name=row["company_name"],
            business_type=row["business_type"],
            company_size=row["company_size"],
            marketing_budget=row["marketing_budget"],
            budget_currency=row["budget_currency"],
            budget_period=BudgetPeriod(row["budget_period"]),
            contact_name=row["contact_name"],
            contact_email=row["contact_email"],
            qualification_status=QualificationStatus(row["qualification_status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )


lead_repository = LeadRepository()
