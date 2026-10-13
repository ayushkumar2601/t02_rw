'use client';

import React from 'react';

interface HeaderProps {
  backendHealthy: boolean;
}

export function Header({ backendHealthy }: HeaderProps) {
  return (
    <header className="border-b border-hairline bg-canvas sticky top-0 z-20">
      <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium tracking-tight text-ink">Ava</span>
          <span className="text-hairline-strong text-xs font-mono">/</span>
          <span className="text-xs text-muted">voice sdr</span>
        </div>

        <div className="flex items-center gap-2 text-xs text-muted">
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              backendHealthy ? 'bg-semantic-success' : 'bg-semantic-error'
            }`}
          />
          <span className="font-mono text-[11px]">{backendHealthy ? 'connected' : 'offline'}</span>
        </div>
      </div>
    </header>
  );
}
