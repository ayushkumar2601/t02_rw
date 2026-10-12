export type BudgetPeriod = 'monthly' | 'quarterly' | 'yearly' | 'one_time' | 'unknown';

export type QualificationStatus = 'in_progress' | 'qualified' | 'partially_qualified' | 'disqualified';

export type ConversationState =
  | 'GREETING'
  | 'ASK_COMPANY'
  | 'ASK_SIZE'
  | 'CLARIFY_SIZE'
  | 'ASK_BUDGET'
  | 'CLARIFY_BUDGET'
  | 'VALIDATE_LEAD'
  | 'SAVE_LEAD'
  | 'CLOSING'
  | 'ENDED';

export type SessionStatus = 'active' | 'completed' | 'ended';

export type Speaker = 'caller' | 'agent' | 'system';

export interface ValidatedLead {
  company_name: string | null;
  business_type: string | null;
  company_size: number | null;
  marketing_budget: number | null;
  budget_currency: string | null;
  budget_period: BudgetPeriod;
  contact_name: string | null;
  contact_email: string | null;
}

export interface SessionCreateResponse {
  session_id: string;
  state: ConversationState;
  status: SessionStatus;
  greeting: string;
}

export interface TurnResponse {
  session_id: string;
  turn_id: string;
  intent: string;
  conversation_state: ConversationState;
  state: ConversationState;
  response: string;
  lead: ValidatedLead;
  missing_fields: string[];
  qualification_status: QualificationStatus;
  should_end_call: boolean;
  session_status: SessionStatus;
}

export interface TranscriptItem {
  id: string;
  speaker: Speaker;
  text: string;
  timestamp: Date;
  isInterim?: boolean;
}

export interface PersistedLeadRecord {
  lead_id: string;
  session_id: string;
  company_name: string | null;
  business_type: string | null;
  company_size: number | null;
  marketing_budget: number | null;
  budget_currency: string | null;
  budget_period: BudgetPeriod;
  contact_name: string | null;
  contact_email: string | null;
  qualification_status: QualificationStatus;
  created_at: string;
  updated_at: string;
}

export interface SessionDetailResponse {
  session_id: string;
  state: ConversationState;
  status: SessionStatus;
  lead: ValidatedLead;
  missing_fields: string[];
  qualification_status: QualificationStatus;
  transcript: Array<{
    turn_id: string;
    session_id: string;
    speaker: Speaker;
    text: string;
    created_at: string;
  }>;
  created_at: string;
  updated_at: string;
  ended_at: string | null;
}

export interface SessionEndResponse {
  session_id: string;
  status: SessionStatus;
  qualification_status: QualificationStatus;
  lead_saved: boolean;
  lead_id: string | null;
  message: string;
}

export interface ServiceHealth {
  status: string;
  service: string;
  version: string;
  environment: string;
  llm_mode: string;
}
