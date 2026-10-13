'use client';

import React from 'react';
import {
  PhoneCall,
  PhoneOff,
  Volume2,
  VolumeX,
  Loader2,
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
  onStartCall,
  onEndCall,
  onToggleMute,
  onInterrupt,
}: VoiceControlsProps) {
  const isCallActive = !!sessionId && voiceStatus !== 'idle' && voiceStatus !== 'ended';

  const renderStatusBadge = () => {
    switch (voiceStatus) {
      case 'connecting':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono bg-canvas border border-hairline text-muted">
            <Loader2 className="w-3 h-3 animate-spin" />
            <span>connecting</span>
          </span>
        );
      case 'listening':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono bg-timeline-grep/15 text-timeline-grep border border-timeline-grep/30">
            <span className="w-1.5 h-1.5 rounded-full bg-timeline-grep animate-pulse" />
            <span>listening</span>
          </span>
        );
      case 'processing':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono bg-timeline-thinking/15 text-timeline-thinking border border-timeline-thinking/30">
            <Loader2 className="w-3 h-3 animate-spin text-timeline-thinking" />
            <span>thinking</span>
          </span>
        );
      case 'speaking':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono bg-timeline-edit/15 text-timeline-edit border border-timeline-edit/30">
            <span className="w-1.5 h-1.5 rounded-full bg-timeline-edit animate-pulse" />
            <span>speaking</span>
          </span>
        );
      case 'ended':
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-mono bg-surface-strong text-muted border border-hairline">
            <span>ended</span>
          </span>
        );
      case 'error':
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-mono bg-semantic-error/15 text-semantic-error border border-semantic-error/30">
            <span>error</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-mono bg-canvas text-muted border border-hairline">
            <span>ready</span>
          </span>
        );
    }
  };

  return (
    <div className="bg-surface-card border border-hairline rounded-lg p-3 sm:px-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        {/* Controls */}
        <div className="flex items-center gap-2">
          {!isCallActive ? (
            <button
              onClick={onStartCall}
              className="h-9 px-4 rounded-md bg-primary hover:bg-primary-active text-on-primary text-xs font-medium transition-colors cursor-pointer flex items-center gap-2"
            >
              <PhoneCall className="w-3.5 h-3.5" />
              <span>Start call</span>
            </button>
          ) : (
            <button
              onClick={onEndCall}
              className="h-9 px-4 rounded-md bg-surface-card hover:bg-canvas text-semantic-error border border-hairline hover:border-hairline-strong text-xs font-medium transition-colors cursor-pointer flex items-center gap-2"
            >
              <PhoneOff className="w-3.5 h-3.5" />
              <span>End call</span>
            </button>
          )}

          {voiceStatus === 'speaking' && onInterrupt && (
            <button
              onClick={onInterrupt}
              className="h-9 px-3 rounded-md bg-canvas hover:bg-surface-strong text-ink border border-hairline text-xs font-medium transition-colors cursor-pointer flex items-center gap-1.5"
            >
              <Hand className="w-3.5 h-3.5 text-primary" />
              <span>Interrupt</span>
            </button>
          )}

          <button
            onClick={onToggleMute}
            disabled={!isCallActive}
            className={`h-9 w-9 rounded-md border text-xs flex items-center justify-center transition-colors cursor-pointer ${
              isMuted
                ? 'bg-canvas text-primary border-primary/40'
                : 'bg-surface-card border-hairline hover:bg-canvas text-ink'
            } ${!isCallActive ? 'opacity-30 cursor-not-allowed' : ''}`}
            title={isMuted ? 'Unmute' : 'Mute'}
          >
            {isMuted ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
          </button>
        </div>

        {/* Status & State Indicators */}
        <div className="flex items-center gap-2">
          {renderStatusBadge()}

          <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-canvas border border-hairline text-muted">
            {conversationState}
          </span>
        </div>
      </div>
    </div>
  );
}
