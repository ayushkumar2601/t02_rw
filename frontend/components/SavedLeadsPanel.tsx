'use client';

import React, { useEffect, useState } from 'react';
import { RotateCw } from 'lucide-react';
import { api } from '@/lib/api';
import { PersistedLeadRecord } from '@/types';

const STORAGE_KEY = 'ava_saved_leads';

function getStoredLeads(): PersistedLeadRecord[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function storeLeads(leads: PersistedLeadRecord[]) {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(leads));
  } catch (err) {
    console.error('Failed to save leads to localStorage:', err);
  }
}

function mergeLeads(
  primary: PersistedLeadRecord[],
  secondary: PersistedLeadRecord[]
): PersistedLeadRecord[] {
  const map = new Map<string, PersistedLeadRecord>();
  // Add secondary leads first
  secondary.forEach((item) => {
    if (item && item.lead_id) map.set(item.lead_id, item);
  });
  // Overlay primary leads (newer or authoritative from server)
  primary.forEach((item) => {
    if (item && item.lead_id) map.set(item.lead_id, item);
  });
  // Sort reverse chronological
  return Array.from(map.values()).sort((a, b) => {
    const dateA = new Date(a.created_at || a.updated_at || 0).getTime();
    const dateB = new Date(b.created_at || b.updated_at || 0).getTime();
    return dateB - dateA;
  });
}

interface SavedLeadsPanelProps {
  lastUpdatedTrigger?: any;
}

export function SavedLeadsPanel({ lastUpdatedTrigger }: SavedLeadsPanelProps) {
  const [leads, setLeads] = useState<PersistedLeadRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Load from localStorage immediately on mount
  useEffect(() => {
    const cached = getStoredLeads();
    if (cached.length > 0) {
      setLeads(cached);
    }
  }, []);

  // Sync when a new lead is persisted during active session
  useEffect(() => {
    if (lastUpdatedTrigger && lastUpdatedTrigger.lead_id) {
      setLeads((prev) => {
        const merged = mergeLeads([lastUpdatedTrigger], prev);
        storeLeads(merged);
        return merged;
      });
    }
  }, [lastUpdatedTrigger]);

  const fetchLeads = async () => {
    setLoading(true);
    setError(null);
    try {
      const serverLeads = await api.listLeads(50, 0);
      setLeads((prev) => {
        const merged = mergeLeads(serverLeads, prev);
        storeLeads(merged);
        return merged;
      });
    } catch (err: unknown) {
      // Backend offline or closed: fall back safely to cached leads in localStorage
      const cached = getStoredLeads();
      if (cached.length > 0) {
        setLeads(cached);
      } else {
        const msg = err instanceof Error ? err.message : 'Failed to fetch leads';
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLeads();
  }, [lastUpdatedTrigger]);

  return (
    <div className="bg-surface-card border border-hairline rounded-lg p-4">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-hairline mb-3">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-ink">Saved leads</span>
          <span className="text-[11px] font-mono text-muted">({leads.length})</span>
        </div>

        <button
          onClick={fetchLeads}
          disabled={loading}
          className="h-7 px-2.5 rounded-md bg-canvas hover:bg-surface-strong text-ink border border-hairline text-[11px] font-mono transition-colors cursor-pointer flex items-center gap-1.5"
        >
          <RotateCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
          <span>refresh</span>
        </button>
      </div>

      {error && leads.length === 0 ? (
        <p className="text-xs text-semantic-error py-3">{error}</p>
      ) : leads.length === 0 ? (
        <p className="text-center py-6 text-xs text-muted">No saved leads yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-hairline text-muted font-mono text-[11px]">
                <th className="pb-2 font-normal">ID</th>
                <th className="pb-2 font-normal">Company</th>
                <th className="pb-2 font-normal">Industry</th>
                <th className="pb-2 font-normal">Team</th>
                <th className="pb-2 font-normal">Budget</th>
                <th className="pb-2 font-normal">Status</th>
                <th className="pb-2 font-normal text-right">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-hairline-soft">
              {leads.map((l) => (
                <tr key={l.lead_id} className="hover:bg-canvas/50 transition-colors">
                  <td className="py-2.5 pr-2 font-mono text-[11px] text-muted">
                    {l.lead_id.replace('lead_', '')}
                  </td>
                  <td className="py-2.5 pr-2 font-medium text-ink">
                    {l.company_name || '—'}
                  </td>
                  <td className="py-2.5 pr-2 text-body">
                    {l.business_type || '—'}
                  </td>
                  <td className="py-2.5 pr-2 font-mono text-body">
                    {l.company_size !== null ? l.company_size : '—'}
                  </td>
                  <td className="py-2.5 pr-2 font-mono text-body">
                    {l.marketing_budget !== null ? (
                      `${l.budget_currency || ''} ${Number(l.marketing_budget).toLocaleString()}${
                        l.budget_period !== 'unknown' ? `/${l.budget_period}` : ''
                      }`
                    ) : (
                      '—'
                    )}
                  </td>
                  <td className="py-2.5 pr-2">
                    <span
                      className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-mono ${
                        l.qualification_status === 'qualified'
                          ? 'bg-semantic-success/15 text-semantic-success border border-semantic-success/30'
                          : l.qualification_status === 'partially_qualified'
                          ? 'bg-timeline-thinking/15 text-timeline-thinking border border-timeline-thinking/30'
                          : 'bg-semantic-error/15 text-semantic-error border border-semantic-error/30'
                      }`}
                    >
                      {l.qualification_status}
                    </span>
                  </td>
                  <td className="py-2.5 font-mono text-[11px] text-muted text-right">
                    {new Date(l.created_at).toLocaleDateString([], {
                      month: 'short',
                      day: 'numeric',
                    })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
