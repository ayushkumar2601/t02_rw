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

    # Common business domains and industries for digital agency qualification
    KNOWN_BUSINESS_TYPES = {
        "digital marketing": "Digital Marketing",
        "marketing": "Digital Marketing",
        "marketing agency": "Marketing Agency",
        "seo": "SEO & Digital Marketing",
        "social media": "Social Media Marketing",
        "advertising": "Advertising",
        "e-commerce": "E-commerce",
        "ecommerce": "E-commerce",
        "retail": "Retail",
        "online store": "E-commerce",
        "saas": "SaaS",
        "software": "Software / Tech",
        "technology": "Technology",
        "tech": "Technology",
        "it services": "IT Services",
        "healthcare": "Healthcare",
        "health care": "Healthcare",
        "medical": "Healthcare",
        "pharma": "Pharmaceuticals",
        "real estate": "Real Estate",
        "property": "Real Estate",
        "finance": "Finance",
        "fintech": "Fintech",
        "banking": "Banking / Finance",
        "insurance": "Insurance",
        "education": "Education",
        "edtech": "Edtech",
        "consulting": "Consulting",
        "legal": "Legal Services",
        "law firm": "Legal Services",
        "manufacturing": "Manufacturing",
        "logistics": "Logistics & Supply Chain",
        "transport": "Transportation",
        "hospitality": "Hospitality",
        "hotel": "Hospitality",
        "restaurant": "Food & Beverage",
        "food": "Food & Beverage",
        "travel": "Travel & Tourism",
        "construction": "Construction",
        "design": "Design & Creative",
    }

    @classmethod
    def parse_company_info(
        cls, text: str, is_ask_company_state: bool = False
    ) -> Tuple[Optional[str], Optional[str]]:
        """Extract company name and business type from caller utterance.

        Handles natural spoken structures including:
        - 'companies name is tectrongo and the business is digital marketing'
        - 'our company is called Acme Digital and we do e-commerce'
        - 'Tectrongo, digital marketing'
        - 'company is Tectrongo'
        - 'we do digital marketing'
        """
        clean = text.strip()
        lower = clean.lower()
        company_name: Optional[str] = None
        business_type: Optional[str] = None

        # 1. Extract business type from known categories (longest match first)
        for phrase in sorted(cls.KNOWN_BUSINESS_TYPES.keys(), key=len, reverse=True):
            pattern = rf"\b{re.escape(phrase)}\b"
            if re.search(pattern, lower):
                business_type = cls.KNOWN_BUSINESS_TYPES[phrase]
                break

        # If not matched from dictionary, check dynamic pattern like "business is <...>" or "we do <...>"
        if not business_type:
            biz_pattern = (
                r"(?:the\s+)?(?:business|industry|domain|field)\s+(?:is|does|involves)\s+"
                r"([A-Za-z0-9\s&/-]+?)(?:,|\.|$|\band\b)"
            )
            biz_match = re.search(biz_pattern, clean, re.IGNORECASE)
            if biz_match:
                extracted = biz_match.group(1).strip()
                if extracted and len(extracted.split()) <= 4:
                    business_type = extracted.title()

        if not business_type:
            we_do_pattern = (
                r"(?:we\s+do|we\s+provide|we\s+are\s+in|we\s+are\s+into)\s+"
                r"([A-Za-z0-9\s&/-]+?)(?:,|\.|$|\band\b)"
            )
            we_do_match = re.search(we_do_pattern, clean, re.IGNORECASE)
            if we_do_match:
                extracted = we_do_match.group(1).strip()
                if extracted and len(extracted.split()) <= 4:
                    business_type = extracted.title()

        # 2. Extract company name using grammatical markers
        # Pattern 1: "called <NAME>", "named <NAME>"
        # e.g. "we are an e-commerce company called Acme Digital"
        comp_pattern_called = (
            r"(?:called|named)\s+([A-Za-z0-9\s&'-]+?)"
            r"(?:\s+(?:and\b|&|,|\.|\bour\b|\bthe\b|\bwe\b|\bbusiness\b|\bwhich\b)|$)"
        )
        match_called = re.search(comp_pattern_called, clean, re.IGNORECASE)
        if match_called:
            candidate = match_called.group(1).strip()
            if candidate:
                company_name = candidate

        # Pattern 2: "company('s|s)? (name)? (is)? <NAME> (and | , | . | $)"
        # Matches: "companies name is tectrongo and the business is digital marketing"
        if not company_name:
            comp_pattern_a = (
                r"(?:our\s+|my\s+|the\s+)?compan(?:ies|y(?:'s)?)\s+(?:name\s+)?(?:is\s+)?"
                r"(?:called\s+|named\s+)?"
                r"([A-Za-z0-9\s&'-]+?)"
                r"(?:\s+(?:and\b|&|,|\.|\bour\b|\bthe\b|\bwe\b|\bbusiness\b|\bindustry\b)|$)"
            )
            match_a = re.search(comp_pattern_a, clean, re.IGNORECASE)
            if match_a:
                candidate = match_a.group(1).strip()
                if candidate and candidate.lower() not in ("a", "an", "the", "our", "my", "good"):
                    company_name = candidate

        # Pattern 3: "name is <NAME>"
        if not company_name:
            comp_pattern_c = (
                r"(?:name\s+is|our\s+name\s+is)\s+([A-Za-z0-9\s&'-]+?)"
                r"(?:\s+(?:and\b|&|,|\.|\bour\b|\bthe\b|\bwe\b|\bbusiness\b)|$)"
            )
            match_c = re.search(comp_pattern_c, clean, re.IGNORECASE)
            if match_c:
                candidate = match_c.group(1).strip()
                if candidate:
                    company_name = candidate

        # Pattern D: Comma separated pair: "Acme Digital, e-commerce" or "Tectrongo, digital marketing"
        if not company_name and "," in clean:
            parts = [p.strip() for p in clean.split(",") if p.strip()]
            if len(parts) >= 2:
                first_part = parts[0]
                if len(first_part.split()) <= 4 and not any(
                    first_part.lower().startswith(x) for x in ("we ", "i ", "hello", "yes", "no")
                ):
                    company_name = first_part

        # Pattern E: "it's <NAME>" or "we are <NAME>"
        if not company_name:
            comp_pattern_e = (
                r"^(?:it'?s|its|we\s+are|we're)\s+([A-Za-z0-9\s&'-]+?)"
                r"(?:\s+(?:and\b|&|,|\.|\bour\b|\bthe\b|\bwe\b|\bbusiness\b)|$)"
            )
            match_e = re.search(comp_pattern_e, clean, re.IGNORECASE)
            if match_e:
                candidate = match_e.group(1).strip()
                if candidate.lower() not in ("an agency", "a company", "an e-commerce company", "fine", "good"):
                    if not any(candidate.lower() == k for k in cls.KNOWN_BUSINESS_TYPES):
                        company_name = candidate

        # Pattern F: In ASK_COMPANY state, if caller just speaks their company name (1-4 words)
        if not company_name and is_ask_company_state:
            filtered_words = [
                w for w in re.findall(r"[a-z0-9]+", lower)
                if w not in ("yes", "yeah", "sure", "ok", "okay")
            ]
            if filtered_words and len(filtered_words) <= 4:
                # If the entire phrase is a known business type, it's business_type not company_name
                if not any(lower == k for k in cls.KNOWN_BUSINESS_TYPES):
                    company_name = clean.strip().rstrip(".,!?")

        # Cleanup company name:
        if company_name:
            company_name = re.sub(r"^(?:a|an|the)\s+", "", company_name, flags=re.IGNORECASE).strip()
            # If all lowercase, title-case
            if company_name.islower():
                company_name = company_name.title()

        return company_name, business_type

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
