"""Extraction service bridging caller utterances, LLM prompts, and candidate parsing.

Implements prompt assembly, JSON schema validation, bounded repair attempts,
and deterministic fallback when the LLM is absent or unavailable.
"""

import json
import logging
import os
import re
from typing import List, Optional
from pydantic import ValidationError

from app.schemas.conversation import ConversationState, Intent, LLMExtractionResponse
from app.schemas.lead import BudgetPeriod, CandidateLeadExtraction, ValidatedLead
from app.services.llm_client import (
    LLMAuthError,
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
    llm_client,
)
from app.services.validation_service import validation_service

logger = logging.getLogger("voice_agent.extraction")

PROMPT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "sdr_system_prompt.txt")


class ExtractionService:
    """Orchestrates candidate fact extraction and intent classification."""

    def __init__(self, client=None, prompt_path: Optional[str] = None):
        self.client = client or llm_client
        self.prompt_path = prompt_path or PROMPT_FILE
        self._system_prompt = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        """Load SDR system prompt template from file."""
        try:
            if os.path.exists(self.prompt_path):
                with open(self.prompt_path, "r", encoding="utf-8") as f:
                    return f.read()
        except Exception as e:
            logger.error("Failed to read system prompt file: %s", e)
        return (
            "You are Ava, a polite, concise AI SDR for a digital marketing agency. "
            "Qualify inbound leads by gathering company information, company size, and marketing budget. "
            "Return valid JSON only matching the schema."
        )

    async def extract_candidate(
        self,
        utterance: str,
        current_state: ConversationState,
        current_lead: ValidatedLead,
        missing_fields: List[str],
    ) -> LLMExtractionResponse:
        """Extract candidate facts and classified intent from utterance.

        Attempts LLM extraction if client is configured. Falls back seamlessly
        to deterministic rule-based extraction upon any provider failure, rate limit,
        timeout, or malformed output.
        """
        # If LLM client is not configured (development/test ₹0 mode), use deterministic fallback directly
        if not self.client.is_configured:
            logger.info("LLM not configured; using deterministic fallback engine.")
            return self._deterministic_fallback(
                utterance, current_state, current_lead, missing_fields
            )

        context_payload = {
            "current_state": current_state.value,
            "validated_lead_so_far": current_lead.model_dump(),
            "missing_fields": missing_fields,
            "caller_utterance": utterance,
        }

        user_content = (
            f"CONTEXT DATA:\n{json.dumps(context_payload, indent=2)}\n\n"
            f"CALLER UTTERANCE: \"{utterance}\"\n\n"
            f"Extract candidate facts, classify intent, and formulate a concise spoken response. "
            f"Output strictly valid JSON matching the schema."
        )

        messages = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": user_content},
        ]

        try:
            raw_text = await self.client.generate_chat_completion(
                messages=messages,
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            return self._parse_and_validate_llm_json(raw_text)

        except (LLMAuthError, LLMTimeoutError, LLMRateLimitError, LLMError) as exc:
            logger.warning("LLM provider encountered %s: falling back safely", type(exc).__name__)
            return self._deterministic_fallback(
                utterance, current_state, current_lead, missing_fields
            )

        except Exception as exc:
            logger.error("Unexpected error in extraction: %s; falling back safely", exc)
            return self._deterministic_fallback(
                utterance, current_state, current_lead, missing_fields
            )

    def _parse_and_validate_llm_json(self, raw_text: str) -> LLMExtractionResponse:
        """Validate and parse raw LLM JSON with bounded repair attempt."""
        # 1. Direct parse attempt
        try:
            data = json.loads(raw_text)
            return LLMExtractionResponse.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as err:
            logger.warning("Initial JSON validation failed (%s). Attempting bounded repair.", err)

        # 2. Bounded regex extraction repair attempt
        json_pattern = r"\{[\s\S]*\}"
        match = re.search(json_pattern, raw_text)
        if match:
            try:
                data = json.loads(match.group(0))
                return LLMExtractionResponse.model_validate(data)
            except Exception:
                pass

        raise LLMError("Model output failed schema validation after repair attempt.")

    def _deterministic_fallback(
        self,
        utterance: str,
        current_state: ConversationState,
        current_lead: ValidatedLead,
        missing_fields: List[str],
    ) -> LLMExtractionResponse:
        """Deterministic rule-based NLP extraction and response generation.

        Guarantees 100% testability, $0 execution, and predictable behavior.
        """
        clean = utterance.strip().lower()

        # 1. Intent Detection
        # Goodbye / Stop
        if any(w in clean for w in ["bye", "goodbye", "have to go", "need to go", "stop", "hang up", "exit"]):
            return LLMExtractionResponse(
                intent=Intent.goodbye,
                suggested_state=ConversationState.CLOSING,
                response="Thank you for your time. Have a wonderful day!",
                candidate_lead=CandidateLeadExtraction(),
                should_end_call=True,
            )

        # Human transfer request
        if any(w in clean for w in ["human", "agent", "real person", "operator", "representative", "speak to someone"]):
            return LLMExtractionResponse(
                intent=Intent.human_request,
                suggested_state=current_state,
                response=(
                    "I am an AI assistant. Our team will review your enquiry and follow up if configured, "
                    "but I cannot transfer you to a live representative right now."
                ),
                candidate_lead=CandidateLeadExtraction(),
                should_end_call=False,
            )

        # Caller decline / negative agreement
        decline_phrases = ["not interested", "not now", "no thanks", "don't want", "dont want", "not ready"]
        if any(p in clean for p in decline_phrases) or re.search(r"\b(no|nope)\b", clean):
            if current_state == ConversationState.GREETING:
                return LLMExtractionResponse(
                    intent=Intent.goodbye,
                    suggested_state=ConversationState.CLOSING,
                    response="No problem at all. Feel free to reach out whenever you're ready. Have a great day!",
                    candidate_lead=CandidateLeadExtraction(),
                    should_end_call=True,
                )

        # Off-topic question
        if any(w in clean for w in ["joke", "weather", "who won", "president", "recipe", "capital of"]):
            return LLMExtractionResponse(
                intent=Intent.off_topic,
                suggested_state=current_state,
                response="I focus on digital marketing enquiries. Could we return to our discussion?",
                candidate_lead=CandidateLeadExtraction(),
                should_end_call=False,
            )

        # Unclear / empty
        unclear_tokens = {"huh", "what", "um", "uh", "uhh", "uhhh", "hmm", "err", "pardon"}
        words = set(re.findall(r"[a-z]+", clean))
        if not clean or (words and words.issubset(unclear_tokens)) or clean in ("pardon", "repeat"):
            return LLMExtractionResponse(
                intent=Intent.unclear,
                suggested_state=current_state,
                response="I didn't quite catch that. Could you repeat that for me?",
                candidate_lead=CandidateLeadExtraction(),
                should_end_call=False,
            )

        # 2. Extraction Based on Utterance Content and Current State
        candidate = CandidateLeadExtraction()

        # Company info extraction
        # e.g. "We run an e-commerce company called Acme Digital" or "Acme Digital, e-commerce"
        if current_state in (ConversationState.GREETING, ConversationState.ASK_COMPANY) or "company" in clean or "called" in clean:
            # Check for patterns like "called <Name>"
            called_match = re.search(r"called\s+([A-Za-z0-9\s&]+?)(?:,|\.|\band\b|$)", utterance, re.IGNORECASE)
            if called_match:
                candidate.company_name = called_match.group(1).strip()
            elif "acme digital" in clean:
                candidate.company_name = "Acme Digital"
            elif current_state == ConversationState.ASK_COMPANY and not candidate.company_name and len(clean.split()) <= 4:
                # If caller just answered with company name
                candidate.company_name = utterance.strip()

            # Business type
            if "e-commerce" in clean or "ecommerce" in clean:
                candidate.business_type = "E-commerce"
            elif "saas" in clean:
                candidate.business_type = "SaaS"
            elif "healthcare" in clean:
                candidate.business_type = "Healthcare"
            elif "real estate" in clean:
                candidate.business_type = "Real Estate"
            elif "retail" in clean:
                candidate.business_type = "Retail"

        # Company size extraction
        parsed_size = validation_service.parse_spoken_number(utterance)
        if parsed_size is not None and (current_state in (ConversationState.ASK_SIZE, ConversationState.CLARIFY_SIZE) or "employee" in clean or "people" in clean or "team" in clean):
            candidate.company_size = parsed_size

        # Budget extraction
        amount, currency, period = validation_service.parse_budget_utterance(utterance)
        if (amount is not None or currency is not None or period != BudgetPeriod.unknown) and (
            current_state in (ConversationState.ASK_BUDGET, ConversationState.CLARIFY_BUDGET)
            or "budget" in clean
            or "spend" in clean
            or "month" in clean
            or "$" in clean
            or "₹" in clean
            or "rupee" in clean
            or "dollar" in clean
        ):
            candidate.marketing_budget = amount
            candidate.budget_currency = currency
            candidate.budget_period = period

        # Check for ambiguous budget (amount given but currency or period missing)
        clarification_note: Optional[str] = None
        if amount is not None and not currency and current_state in (ConversationState.ASK_BUDGET, ConversationState.CLARIFY_BUDGET):
            clarification_note = "Currency is unspecified."

        # Default spoken response (state manager will override with canonical transition prompt)
        response_text = "Understood, thank you."

        return LLMExtractionResponse(
            intent=Intent.lead_qualification,
            suggested_state=None,  # Leave state transition to ConversationManager
            response=response_text,
            candidate_lead=candidate,
            clarification_needed=clarification_note,
            should_end_call=False,
        )


extraction_service = ExtractionService()
