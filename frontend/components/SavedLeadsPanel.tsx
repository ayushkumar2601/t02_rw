'use client';

import React, { useEffect, useState } from 'react';
import { Database, RefreshCw, CheckCircle2, AlertTriangle } from 'lucide-react';
import { api } from '@/lib/api';
import { PersistedLeadRecord } from '@/types';

interface SavedLeadsPanelProps {
  lastUpdatedTrigger?: any;
}

export function SavedLeadsPanel({ lastUpdatedTrigger }: SavedLeadsPanelProps) {
  const [leads, setLeads] = useState<PersistedLeadRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchLeads = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listLeads(25, 0);
      setLeads(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch leads';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLeads();
  }, [lastUpdatedTrigger]);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-indigo-400" />
          <h2 className="text-sm font-semibold text-slate-200">
            Saved Leads in SQLite Database
          </h2>
          <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 font-mono">
            {leads.length} records
          </span>
        </div>
        <button
          onClick={fetchLeads}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700/80 transition-colors cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {error ? (
        <p className="text-xs text-rose-400 py-3 text-center">{error}</p>
      ) : leads.length === 0 ? (
        <div className="text-center py-6 text-slate-500 text-xs">
          No persisted leads found yet. Start and complete a qualification call to save a lead record.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-medium font-mono text-[11px]">
                <th className="pb-2.5 pr-3">Lead ID</th>
                <th className="pb-2.5 pr-3">Company</th>
                <th className="pb-2.5 pr-3">Industry</th>
                <th className="pb-2.5 pr-3">Team</th>
                <th className="pb-2.5 pr-3">Budget</th>
                <th className="pb-2.5 pr-3">Qualification</th>
                <th className="pb-2.5">Created At</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {leads.map((l) => (
                <tr key={l.lead_id} className="hover:bg-slate-800/40 transition-colors">
                  <td className="py-2.5 pr-3 font-mono text-indigo-400 font-medium">
                    {l.lead_id}
                  </td>
                  <td className="py-2.5 pr-3 font-medium text-slate-200">
                    {l.company_name || <span className="text-slate-500 italic">Not provided</span>}
                  </td>
                  <td className="py-2.5 pr-3 text-slate-400">
                    {l.business_type || <span className="text-slate-500 italic">Not provided</span>}
                  </td>
                  <td className="py-2.5 pr-3">
                    {l.company_size !== null ? (
                      `${l.company_size}`
                    ) : (
                      <span className="text-slate-500 italic">Not provided</span>
                    )}
                  </td>
                  <td className="py-2.5 pr-3">
                    {l.marketing_budget !== null ? (
                      `${l.budget_currency || ''} ${Number(l.marketing_budget).toLocaleString()}${
                        l.budget_period !== 'unknown' ? `/${l.budget_period}` : ''
                      }`
                    ) : (
                      <span className="text-slate-500 italic">Not provided</span>
                    )}
                  </td>
                  <td className="py-2.5 pr-3">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium ${
                        l.qualification_status === 'qualified'
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          : l.qualification_status === 'partially_qualified'
                          ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                          : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                      }`}
                    >
                      {l.qualification_status === 'qualified' ? (
                        <CheckCircle2 className="w-3 h-3" />
                      ) : (
                        <AlertTriangle className="w-3 h-3" />
                      )}
                      <span>{l.qualification_status}</span>
                    </span>
                  </td>
                  <td className="py-2.5 text-slate-400 font-mono text-[11px]">
                    {new Date(l.created_at).toLocaleString([], {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
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
