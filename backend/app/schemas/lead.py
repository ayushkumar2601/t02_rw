"""Pydantic schemas for lead data representation and validation.

Maintains strict separation between untrusted candidate extractions,
trusted server-validated lead models, and persisted lead records.
"""

from datetime import datetime
from enum import Enum
import re
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class BudgetPeriod(str, Enum):
    """Supported budget periods."""

    monthly = "monthly"
    quarterly = "quarterly"
    yearly = "yearly"
    one_time = "one_time"
    unknown = "unknown"


class QualificationStatus(str, Enum):
    """Explicit qualification status of the lead."""

    in_progress = "in_progress"
    qualified = "qualified"
    partially_qualified = "partially_qualified"
    disqualified = "disqualified"


class CandidateLeadExtraction(BaseModel):
    """Untrusted candidate lead data proposed by the LLM or parser.

    Extra fields are strictly forbidden. Values undergo sanitization and
    validation before being accepted into the validated lead record.
    """

    model_config = ConfigDict(extra="forbid")

    company_name: Optional[str] = Field(
        default=None,
        description="Caller's company name if explicitly mentioned",
        max_length=200,
    )
    business_type: Optional[str] = Field(
        default=None,
        description="Type of business/industry (e.g., E-commerce, SaaS, Real Estate)",
        max_length=200,
    )
    company_size: Optional[int] = Field(
        default=None,
        ge=0,
        description="Approximate number of employees or team members. Never 0 for unknown.",
    )
    marketing_budget: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Approximate marketing budget numeric value. Never 0 for unknown.",
    )
    budget_currency: Optional[str] = Field(
        default=None,
        description="Standard 3-letter currency code (e.g. INR, USD, EUR, GBP)",
        max_length=10,
    )
    budget_period: BudgetPeriod = Field(
        default=BudgetPeriod.unknown,
        description="Budget timeframe period",
    )
    contact_name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Optional contact name",
    )
    contact_email: Optional[str] = Field(
        default=None,
        max_length=254,
        description="Optional contact email address",
    )

    @field_validator("budget_currency", mode="before")
    @classmethod
    def normalize_currency(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = str(v).strip().upper()
        # Common symbol mappings
        symbol_map = {
            "₹": "INR",
            "RS": "INR",
            "RUPEES": "INR",
            "RUPEE": "INR",
            "$": "USD",
            "DOLLAR": "USD",
            "DOLLARS": "USD",
            "€": "EUR",
            "EURO": "EUR",
            "EUROS": "EUR",
            "£": "GBP",
            "POUND": "GBP",
            "POUNDS": "GBP",
        }
        if v in symbol_map:
            return symbol_map[v]
        # Basic currency check: 3 uppercase letters
        if re.match(r"^[A-Z]{3}$", v):
            return v
        return None

    @field_validator("company_name", "business_type", "contact_name", mode="before")
    @classmethod
    def strip_strings(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        cleaned = str(v).strip()
        return cleaned if cleaned else None

    @field_validator("contact_email", mode="before")
    @classmethod
    def validate_email_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        cleaned = str(v).strip().lower()
        if not cleaned:
            return None
        email_regex = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
        if not re.match(email_regex, cleaned):
            raise ValueError(f"Invalid email format: {v}")
        return cleaned


class ValidatedLead(BaseModel):
    """Trusted server-validated lead model.

    This represents the authoritative lead state maintained across conversation turns.
    Extra fields are strictly forbidden. Zero must never represent an unknown count or budget.
    """

    model_config = ConfigDict(extra="forbid")

    company_name: Optional[str] = Field(default=None, max_length=200)
    business_type: Optional[str] = Field(default=None, max_length=200)
    company_size: Optional[int] = Field(default=None, ge=0)
    marketing_budget: Optional[float] = Field(default=None, ge=0.0)
    budget_currency: Optional[str] = Field(default=None, max_length=10)
    budget_period: BudgetPeriod = Field(default=BudgetPeriod.unknown)
    contact_name: Optional[str] = Field(default=None, max_length=100)
    contact_email: Optional[str] = Field(default=None, max_length=254)


class PersistedLeadRecord(BaseModel):
    """Final persisted lead record stored in SQLite.

    Server-generated identifiers and timestamps are immutable from client requests.
    """

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    lead_id: str
    session_id: str
    company_name: Optional[str] = None
    business_type: Optional[str] = None
    company_size: Optional[int] = None
    marketing_budget: Optional[float] = None
    budget_currency: Optional[str] = None
    budget_period: BudgetPeriod
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    qualification_status: QualificationStatus
    created_at: datetime
    updated_at: datetime
