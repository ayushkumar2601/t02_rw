"""Validation service for lead qualification, data consistency, and field normalization.

Enforces deterministic validation rules, recomputes missing fields,
and governs qualification status independently of LLM claims.
"""

import re
from typing import List, Optional, Tuple

from app.schemas.lead import (
    BudgetPeriod,
    CandidateLeadExtraction,
    QualificationStatus,
    ValidatedLead,
)


class ValidationService:
    """Deterministic validation and normalization service."""

    # Words to integer conversions for common spoken phrases
    NUMBER_WORD_MAP = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
        "eleven": 11,
        "twelve": 12,
        "thirteen": 13,
        "fourteen": 14,
        "fifteen": 15,
        "sixteen": 16,
        "seventeen": 17,
        "eighteen": 18,
        "nineteen": 19,
        "twenty": 20,
        "thirty": 30,
        "forty": 40,
        "fifty": 50,
        "sixty": 60,
        "seventy": 70,
        "eighty": 80,
        "ninety": 90,
        "hundred": 100,
        "thousand": 1000,
    }

    @staticmethod
    def compute_missing_fields(lead: ValidatedLead) -> List[str]:
        """Compute list of missing qualification fields according to the canonical schema.

        Mandatory qualification fields for full qualification:
        - company_size
        - marketing_budget
        - budget_currency
        - budget_period
        """
        missing: List[str] = []
        if lead.company_size is None:
            missing.append("company_size")
        if lead.marketing_budget is None:
            missing.append("marketing_budget")
        if not lead.budget_currency:
            missing.append("budget_currency")
        if lead.budget_period == BudgetPeriod.unknown:
            missing.append("budget_period")
        return missing

    @staticmethod
    def compute_qualification_status(
        lead: ValidatedLead,
        is_terminal: bool = False,
        caller_declined: bool = False,
    ) -> QualificationStatus:
        """Deterministically calculate qualification status.

        - qualified: company_size, marketing_budget, budget_currency, and budget_period are valid.
        - in_progress: call is ongoing and fields are not yet complete.
        - partially_qualified: call reached a terminal state without completing all fields.
        - disqualified: only applied when explicit disqualification rules match (e.g. zero/negative
          stated as a deliberate non-fit).
        Note: Per PRD, a caller declining must not be marked disqualified merely for declining.
        """
        missing = ValidationService.compute_missing_fields(lead)

        if not missing:
            return QualificationStatus.qualified

        if not is_terminal and not caller_declined:
            return QualificationStatus.in_progress

        # Terminal state reached but missing qualification fields
        return QualificationStatus.partially_qualified

    @staticmethod
    def merge_candidate_into_validated(
        current: ValidatedLead,
        candidate: CandidateLeadExtraction,
        utterance: str,
    ) -> ValidatedLead:
        """Merge candidate extractions into current validated lead.

        Rules:
        - Never overwrite existing valid data with null unless explicitly cleared.
        - Preserve prior fields across conversation turns.
        - Validate employee counts (cannot be negative).
        - Validate budgets (cannot be negative).
        - Allow explicit user corrections (e.g., 'actually make that 40').
        """
        updated = current.model_copy()

        # Company name
        if candidate.company_name:
            updated.company_name = candidate.company_name

        # Business type
        if candidate.business_type:
            updated.business_type = candidate.business_type

        # Company size
        if candidate.company_size is not None and candidate.company_size >= 0:
            updated.company_size = candidate.company_size

        # Marketing budget
        if candidate.marketing_budget is not None and candidate.marketing_budget >= 0.0:
            updated.marketing_budget = candidate.marketing_budget

        # Budget currency
        if candidate.budget_currency:
            updated.budget_currency = candidate.budget_currency

        # Budget period
        if candidate.budget_period and candidate.budget_period != BudgetPeriod.unknown:
            updated.budget_period = candidate.budget_period

        # Contact info
        if candidate.contact_name:
            updated.contact_name = candidate.contact_name
        if candidate.contact_email:
            updated.contact_email = candidate.contact_email

        return updated

    @classmethod
    def parse_spoken_number(cls, text: str) -> Optional[int]:
        """Helper to parse common spoken numbers and phrases into an integer."""
        clean = text.lower().strip()
        # Direct phrase matches
        if clean in ("it's just me", "its just me", "just me", "only me", "myself", "solo", "one person"):
            return 1

        # Check for digits in text
        digit_match = re.search(r"\b(\d+)\b", clean)
        if digit_match:
            try:
                val = int(digit_match.group(1))
                if val >= 0:
                    return val
            except ValueError:
                pass

        # Parse compound words like "twenty-five" or "twenty five"
        words = re.findall(r"[a-z]+", clean.replace("-", " "))
        total = 0
        current = 0
        found_any = False

        for w in words:
            if w in cls.NUMBER_WORD_MAP:
                val = cls.NUMBER_WORD_MAP[w]
                found_any = True
                if val == 100:
                    current = (current if current else 1) * 100
                elif val == 1000:
                    total += (current if current else 1) * 1000
                    current = 0
                else:
                    current += val

        total += current
        if found_any and total >= 0:
            return total

        return None

    @classmethod
    def parse_budget_utterance(
        cls, text: str
    ) -> Tuple[Optional[float], Optional[str], BudgetPeriod]:
        """Heuristic parser to extract budget amount, currency, and period from natural language.

        Supports:
        - Currency symbols: $, ₹, €, £
        - Words: rupees, dollars, euros, pounds
        - Periods: monthly, yearly, per month, a month, annual, annually, quarterly, one-time
        - Indian denominations: lakh (100,000), crore (10,000,000) when rupee context is present
        """
        clean = text.lower().strip()

        # Currency detection
        currency: Optional[str] = None
        if "₹" in clean or "rupee" in clean or "inr" in clean or re.search(r"\brs\.?\b", clean):
            currency = "INR"
        elif "$" in clean or "dollar" in clean or "usd" in clean:
            currency = "USD"
        elif "€" in clean or "euro" in clean or "eur" in clean:
            currency = "EUR"
        elif "£" in clean or "pound" in clean or "gbp" in clean:
            currency = "GBP"

        # Period detection
        period = BudgetPeriod.unknown
        if any(p in clean for p in ("month", "monthly", "per month", "each month", "a month")):
            period = BudgetPeriod.monthly
        elif any(p in clean for p in ("year", "yearly", "annual", "annually", "per year", "a year")):
            period = BudgetPeriod.yearly
        elif any(p in clean for p in ("quarter", "quarterly", "per quarter")):
            period = BudgetPeriod.quarterly
        elif any(p in clean for p in ("one time", "one-time", "single project", "fixed")):
            period = BudgetPeriod.one_time

        # Amount detection
        amount: Optional[float] = None

        # Check for Indian notation: e.g. "5 lakhs", "five lakhs", "2.5 lakh"
        lakh_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:lakh|lac)s?", clean)
        if lakh_match:
            try:
                num = float(lakh_match.group(1))
                amount = num * 100000.0
                if not currency:
                    currency = "INR"  # Lakh is uniquely an Indian denomination
            except ValueError:
                pass

        if amount is None:
            # Look for spoken numbers with "lakh" e.g. "five lakhs"
            for word, val in cls.NUMBER_WORD_MAP.items():
                if f"{word} lakh" in clean or f"{word} lac" in clean:
                    amount = float(val * 100000)
                    if not currency:
                        currency = "INR"
                    break

        if amount is None:
            # Check for thousand / k e.g. "50k", "50 thousand"
            k_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:k|thousand)", clean)
            if k_match:
                try:
                    num = float(k_match.group(1))
                    amount = num * 1000.0
                except ValueError:
                    pass

        if amount is None:
            # Direct numeric match, e.g. "$50,000", "50000"
            clean_digits = re.sub(r"[, ]", "", clean)
            match = re.search(r"(?:₹|\$|€|£)?(\d+(?:\.\d+)?)", clean_digits)
            if match:
                try:
                    val = float(match.group(1))
                    amount = val
                except ValueError:
                    pass

        if amount is None:
            # Try parsing spoken words (e.g. "fifty thousand", "two thousand", "twenty-five thousand")
            spoken = cls.parse_spoken_number(clean)
            if spoken is not None and spoken > 0:
                amount = float(spoken)

        return amount, currency, period


validation_service = ValidationService()
