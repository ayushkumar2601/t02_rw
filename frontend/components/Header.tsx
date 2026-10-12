'use client';

import React from 'react';
import { Activity, Bot, ShieldCheck, Wifi, WifiOff } from 'lucide-react';

interface HeaderProps {
  backendHealthy: boolean;
}

export function Header({ backendHealthy }: HeaderProps) {
  return (
    <header className="border-b border-slate-800 bg-slate-900/95 backdrop-blur px-6 py-4 sticky top-0 z-20">
      <div className="max-w-7xl mx-auto flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center text-white shadow-lg shadow-indigo-500/20">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold text-white tracking-tight">Ava Voice Agent</h1>
              <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-medium">
                SDR AI
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Autonomous Inbound Lead Qualification Assistant · Digital Marketing Agency
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 text-xs">
          {/* Disclosure */}
          <div className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700/60 text-slate-300">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>AI Assistant Disclosure Active</span>
          </div>

          {/* Backend Status */}
          <div
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border font-medium transition-colors ${
              backendHealthy
                ? 'bg-emerald-950/40 text-emerald-400 border-emerald-800/60'
                : 'bg-rose-950/40 text-rose-400 border-rose-800/60'
            }`}
          >
            {backendHealthy ? (
              <>
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <Wifi className="w-3.5 h-3.5" />
                <span>Backend Connected</span>
              </>
            ) : (
              <>
                <span className="w-2 h-2 rounded-full bg-rose-400" />
                <WifiOff className="w-3.5 h-3.5" />
                <span>Backend Offline</span>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
