'use client';

import React from 'react';
import {
  Building2,
  Users,
  DollarSign,
  Briefcase,
  CheckCircle2,
  Clock,
  AlertTriangle,
  XCircle,
  Database,
} from 'lucide-react';
import {
  PersistedLeadRecord,
  QualificationStatus,
  SessionStatus,
  ValidatedLead,
} from '@/types';

interface LeadSummaryProps {
  lead: ValidatedLead;
  missingFields: string[];
  qualificationStatus: QualificationStatus;
  sessionStatus: SessionStatus;
  persistedLead: PersistedLeadRecord | null;
}

export function LeadSummary({
  lead,
  missingFields,
  qualificationStatus,
  sessionStatus,
  persistedLead,
}: LeadSummaryProps) {
  const getQualificationBadge = () => {
    switch (qualificationStatus) {
      case 'qualified':
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-medium">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Qualified</span>
          </span>
        );
      case 'partially_qualified':
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 text-xs font-medium">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>Partially Qualified</span>
          </span>
        );
      case 'disqualified':
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20 text-xs font-medium">
            <XCircle className="w-3.5 h-3.5" />
            <span>Disqualified</span>
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 text-xs font-medium">
            <Clock className="w-3.5 h-3.5" />
            <span>In Progress</span>
          </span>
        );
    }
  };

  const formatBudget = () => {
    if (lead.marketing_budget === null) {
      return <span className="text-slate-500 italic">Not provided</span>;
    }
    const curr = lead.budget_currency || '';
    const formattedNum = Number(lead.marketing_budget).toLocaleString();
    const period = lead.budget_period !== 'unknown' ? ` / ${lead.budget_period}` : '';
    return `${curr} ${formattedNum}${period}`.trim();
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm flex flex-col justify-between h-full">
      <div className="space-y-4">
        {/* Panel Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <h2 className="text-sm font-semibold text-slate-200">Extracted Lead Record</h2>
          {getQualificationBadge()}
        </div>

        {/* Lead Attribute Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 text-xs">
          {/* Company Name */}
          <div className="bg-slate-800/60 border border-slate-700/50 rounded-lg p-3">
            <div className="flex items-center gap-1.5 text-slate-400 mb-1">
              <Building2 className="w-3.5 h-3.5 text-indigo-400" />
              <span>Company Name</span>
            </div>
            <div className="font-medium text-slate-100 text-sm">
              {lead.company_name || <span className="text-slate-500 italic">Not provided</span>}
            </div>
          </div>

          {/* Business Type */}
          <div className="bg-slate-800/60 border border-slate-700/50 rounded-lg p-3">
            <div className="flex items-center gap-1.5 text-slate-400 mb-1">
              <Briefcase className="w-3.5 h-3.5 text-indigo-400" />
              <span>Business Type / Industry</span>
            </div>
            <div className="font-medium text-slate-100 text-sm">
              {lead.business_type || <span className="text-slate-500 italic">Not provided</span>}
            </div>
          </div>

          {/* Company Size */}
          <div className="bg-slate-800/60 border border-slate-700/50 rounded-lg p-3">
            <div className="flex items-center gap-1.5 text-slate-400 mb-1">
              <Users className="w-3.5 h-3.5 text-indigo-400" />
              <span>Team Size (Employees)</span>
            </div>
            <div className="font-medium text-slate-100 text-sm">
              {lead.company_size !== null ? (
                `${lead.company_size} members`
              ) : (
                <span className="text-slate-500 italic">Not provided</span>
              )}
            </div>
          </div>

          {/* Marketing Budget */}
          <div className="bg-slate-800/60 border border-slate-700/50 rounded-lg p-3">
            <div className="flex items-center gap-1.5 text-slate-400 mb-1">
              <DollarSign className="w-3.5 h-3.5 text-indigo-400" />
              <span>Marketing Budget</span>
            </div>
            <div className="font-medium text-slate-100 text-sm">{formatBudget()}</div>
          </div>
        </div>

        {/* Missing Fields Tracker */}
        <div className="bg-slate-950/60 border border-slate-800 rounded-lg p-3 text-xs">
          <div className="text-slate-400 mb-1.5 font-medium flex items-center justify-between">
            <span>Missing Mandatory Qualification Fields:</span>
            <span className="font-mono text-slate-500">({missingFields.length})</span>
          </div>
          {missingFields.length === 0 ? (
            <p className="text-emerald-400 flex items-center gap-1 font-medium">
              <CheckCircle2 className="w-3.5 h-3.5" /> All qualification criteria satisfied
            </p>
          ) : (
            <div className="flex flex-wrap gap-1.5">
              {missingFields.map((field) => (
                <span
                  key={field}
                  className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-[11px] border border-slate-700"
                >
                  {field}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Footer Persistence Status */}
      <div className="mt-4 pt-3 border-t border-slate-800 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-slate-400">
        <div className="flex items-center gap-1.5">
          <Database className="w-3.5 h-3.5 text-indigo-400" />
          <span>Persistence:</span>
          {persistedLead ? (
            <span className="text-emerald-400 font-medium">
              Saved in SQLite ({persistedLead.lead_id})
            </span>
          ) : sessionStatus === 'active' ? (
            <span className="text-slate-500">In-progress turn (saves on call completion)</span>
          ) : (
            <span className="text-amber-400">Not persisted</span>
          )}
        </div>
        <div className="font-mono text-[11px] text-slate-500">
          Status: <span className="text-slate-300 uppercase">{sessionStatus}</span>
        </div>
      </div>
    </div>
  );
}
