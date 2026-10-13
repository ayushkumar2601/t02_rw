'use client';

import React from 'react';
import { Check } from 'lucide-react';
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
  const renderStatusBadge = () => {
    switch (qualificationStatus) {
      case 'qualified':
        return (
          <span className="px-2 py-0.5 rounded-full text-[11px] font-mono bg-semantic-success/15 text-semantic-success border border-semantic-success/30">
            qualified
          </span>
        );
      case 'partially_qualified':
        return (
          <span className="px-2 py-0.5 rounded-full text-[11px] font-mono bg-timeline-thinking/15 text-timeline-thinking border border-timeline-thinking/30">
            partially qualified
          </span>
        );
      case 'disqualified':
        return (
          <span className="px-2 py-0.5 rounded-full text-[11px] font-mono bg-semantic-error/15 text-semantic-error border border-semantic-error/30">
            disqualified
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded-full text-[11px] font-mono bg-canvas text-muted border border-hairline">
            in progress
          </span>
        );
    }
  };

  const formatBudget = () => {
    if (lead.marketing_budget === null) return '—';
    const curr = lead.budget_currency || '';
    const num = Number(lead.marketing_budget).toLocaleString();
    const period = lead.budget_period !== 'unknown' ? ` / ${lead.budget_period}` : '';
    return `${curr} ${num}${period}`.trim();
  };

  return (
    <div className="bg-surface-card border border-hairline rounded-lg p-4 flex flex-col justify-between h-full">
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-hairline">
          <span className="text-xs font-medium text-ink">Lead Details</span>
          {renderStatusBadge()}
        </div>

        {/* Data List */}
        <dl className="divide-y divide-hairline-soft text-xs">
          <div className="py-2 flex items-center justify-between">
            <dt className="text-muted">Company</dt>
            <dd className="font-medium text-ink text-right">{lead.company_name || '—'}</dd>
          </div>

          <div className="py-2 flex items-center justify-between">
            <dt className="text-muted">Industry</dt>
            <dd className="font-medium text-ink text-right">{lead.business_type || '—'}</dd>
          </div>

          <div className="py-2 flex items-center justify-between">
            <dt className="text-muted">Team size</dt>
            <dd className="font-mono text-ink text-right">
              {lead.company_size !== null ? lead.company_size : '—'}
            </dd>
          </div>

          <div className="py-2 flex items-center justify-between">
            <dt className="text-muted">Budget</dt>
            <dd className="font-mono text-ink text-right">{formatBudget()}</dd>
          </div>
        </dl>

        {/* Missing fields */}
        {missingFields.length > 0 ? (
          <div className="pt-2">
            <div className="text-[11px] font-mono text-muted mb-1.5">pending fields</div>
            <div className="flex flex-wrap gap-1">
              {missingFields.map((field) => (
                <span
                  key={field}
                  className="px-1.5 py-0.5 rounded text-[11px] font-mono bg-canvas border border-hairline text-muted"
                >
                  {field}
                </span>
              ))}
            </div>
          </div>
        ) : (
          <div className="pt-2 text-[11px] font-mono text-semantic-success flex items-center gap-1.5">
            <Check className="w-3.5 h-3.5" />
            <span>all fields captured</span>
          </div>
        )}
      </div>

      {/* Footer Meta */}
      <div className="pt-3 mt-4 border-t border-hairline flex items-center justify-between text-[11px] font-mono text-muted">
        <span>status: {sessionStatus}</span>
        {persistedLead && <span>id: {persistedLead.lead_id}</span>}
      </div>
    </div>
  );
}
