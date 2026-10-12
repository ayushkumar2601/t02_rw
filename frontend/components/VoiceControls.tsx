'use client';

import React from 'react';
import {
  Mic,
  PhoneCall,
  PhoneOff,
  Volume2,
  VolumeX,
  Loader2,
  Radio,
  Hand,
} from 'lucide-react';
import { ConversationState } from '@/types';
import { VoiceSessionStatus } from '@/hooks/useVoiceSession';

interface VoiceControlsProps {
  sessionId: string | null;
  voiceStatus: VoiceSessionStatus;
  conversationState: ConversationState;
  isMuted: boolean;
  isVoiceSupported: boolean;
  onStartCall: () => void;
  onEndCall: () => void;
  onToggleMute: () => void;
  onInterrupt?: () => void;
}

export function VoiceControls({
  sessionId,
  voiceStatus,
  conversationState,
  isMuted,
  isVoiceSupported,
  onStartCall,
  onEndCall,
  onToggleMute,
  onInterrupt,
}: VoiceControlsProps) {
  const isCallActive = !!sessionId && voiceStatus !== 'idle' && voiceStatus !== 'ended';

  const getStatusBadge = () => {
    switch (voiceStatus) {
      case 'connecting':
        return (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 text-xs">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            <span>Connecting...</span>
          </div>
        );
      case 'listening':
        return (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs animate-pulse">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <Mic className="w-3.5 h-3.5" />
            <span>Listening to you (Speak now)</span>
          </div>
        );
      case 'processing':
        return (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 text-xs">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            <span>Ava thinking...</span>
          </div>
        );
      case 'speaking':
        return (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-violet-500/10 text-violet-400 border border-violet-500/20 text-xs">
            <Radio className="w-3.5 h-3.5 animate-pulse text-violet-400" />
            <span>Ava speaking (Mic paused)</span>
          </div>
        );
      case 'ended':
        return (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-800 text-slate-400 border border-slate-700 text-xs">
            <span>Call Completed</span>
          </div>
        );
      case 'error':
        return (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20 text-xs">
            <span>Error</span>
          </div>
        );
      default:
        return (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-800/80 text-slate-400 border border-slate-700/60 text-xs">
            <span>Ready to start</span>
          </div>
        );
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        {/* Left Side: Call Buttons & Controls */}
        <div className="flex flex-wrap items-center gap-3">
          {!isCallActive ? (
            <button
              onClick={onStartCall}
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-sm transition-all shadow-md shadow-emerald-950 cursor-pointer active:scale-95"
            >
              <PhoneCall className="w-4 h-4" />
              <span>Start Voice Call</span>
            </button>
          ) : (
            <button
              onClick={onEndCall}
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-medium text-sm transition-all shadow-md shadow-rose-950 cursor-pointer active:scale-95"
            >
              <PhoneOff className="w-4 h-4" />
              <span>End Call</span>
            </button>
          )}

          {/* Interrupt Button (Visible while Ava is speaking) */}
          {voiceStatus === 'speaking' && onInterrupt && (
            <button
              onClick={onInterrupt}
              title="Interrupt Ava and speak immediately"
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-amber-500/15 hover:bg-amber-500/25 text-amber-300 border border-amber-500/30 text-sm font-medium transition-all cursor-pointer active:scale-95 animate-pulse"
            >
              <Hand className="w-4 h-4" />
              <span>Interrupt Ava</span>
            </button>
          )}

          {/* Mute Control */}
          <button
            onClick={onToggleMute}
            disabled={!isCallActive}
            title={isMuted ? 'Unmute Ava speech' : 'Mute Ava speech'}
            className={`p-2.5 rounded-lg border text-sm transition-colors cursor-pointer ${
              !isCallActive
                ? 'opacity-40 cursor-not-allowed border-slate-800 text-slate-500'
                : isMuted
                ? 'bg-amber-500/10 border-amber-500/30 text-amber-400'
                : 'bg-slate-800/80 border-slate-700 text-slate-300 hover:bg-slate-700'
            }`}
          >
            {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
          </button>
        </div>

        {/* Right Side: Status Badges */}
        <div className="flex flex-wrap items-center gap-2.5">
          {getStatusBadge()}

          {/* State Badge */}
          <div className="px-2.5 py-1 rounded-full bg-slate-800 border border-slate-700 text-xs font-mono text-slate-300">
            State: <span className="text-indigo-400 font-semibold">{conversationState}</span>
          </div>

          {/* Session ID */}
          {sessionId && (
            <div className="hidden lg:block px-2.5 py-1 rounded-full bg-slate-800/60 border border-slate-700/40 text-[11px] font-mono text-slate-400">
              ID: {sessionId.replace('sess_', '')}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
