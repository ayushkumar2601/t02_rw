import {
  PersistedLeadRecord,
  ServiceHealth,
  SessionCreateResponse,
  SessionDetailResponse,
  SessionEndResponse,
  TurnResponse,
} from '@/types';

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, '') || 'http://localhost:8000';

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!res.ok) {
      let errorDetail = `Request failed with status ${res.status}`;
      try {
        const errorData = await res.json();
        if (errorData.detail) {
          errorDetail = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
        }
      } catch {
        // use default errorDetail
      }
      throw new ApiError(errorDetail, res.status);
    }

    return (await res.json()) as T;
  } catch (err: unknown) {
    if (err instanceof ApiError) {
      throw err;
    }
    const message = err instanceof Error ? err.message : 'Network request failed';
    throw new ApiError(message, 0);
  }
}

export const api = {
  async checkHealth(): Promise<ServiceHealth> {
    return request<ServiceHealth>('/health');
  },

  async createSession(): Promise<SessionCreateResponse> {
    return request<SessionCreateResponse>('/api/sessions', {
      method: 'POST',
    });
  },

  async sendTurn(
    sessionId: string,
    turnId: string,
    transcript: string
  ): Promise<TurnResponse> {
    return request<TurnResponse>(`/api/sessions/${sessionId}/turns`, {
      method: 'POST',
      body: JSON.stringify({
        turn_id: turnId,
        transcript,
        timestamp: new Date().toISOString(),
      }),
    });
  },

  async getSession(sessionId: string): Promise<SessionDetailResponse> {
    return request<SessionDetailResponse>(`/api/sessions/${sessionId}`);
  },

  async endSession(sessionId: string): Promise<SessionEndResponse> {
    return request<SessionEndResponse>(`/api/sessions/${sessionId}/end`, {
      method: 'POST',
    });
  },

  async listLeads(limit: number = 20, offset: number = 0): Promise<PersistedLeadRecord[]> {
    return request<PersistedLeadRecord[]>(`/api/leads?limit=${limit}&offset=${offset}`);
  },

  async getLead(leadId: string): Promise<PersistedLeadRecord> {
    return request<PersistedLeadRecord>(`/api/leads/${leadId}`);
  },
};
