'use client';

import React, { useEffect, useRef } from 'react';
import { TranscriptItem } from '@/types';
import { VoiceSessionStatus } from '@/hooks/useVoiceSession';

interface TranscriptPanelProps {
  transcript: TranscriptItem[];
  interimTranscript: string;
  voiceStatus: VoiceSessionStatus;
}

export function TranscriptPanel({
  transcript,
  interimTranscript,
  voiceStatus,
}: TranscriptPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [transcript, interimTranscript, voiceStatus]);

  return (
    <div className="bg-surface-card border border-hairline rounded-lg flex flex-col h-[460px] overflow-hidden">
      {/* Header */}
      <div className="px-4 py-2.5 border-b border-hairline bg-canvas-soft/60 flex items-center justify-between">
        <span className="text-xs font-medium text-ink">Transcript</span>
        {transcript.length > 0 && (
          <span className="text-[11px] text-muted font-mono">{transcript.length} turns</span>
        )}
      </div>

      {/* Transcript Area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3.5 scroll-smooth">
        {transcript.length === 0 && !interimTranscript ? (
          <div className="h-full flex items-center justify-center text-center p-6 text-xs text-muted">
            Press start to begin conversation
          </div>
        ) : (
          transcript.map((item) => {
            const isAgent = item.speaker === 'agent';
            return (
              <div
                key={item.id}
                className={`flex flex-col gap-1 max-w-[85%] ${
                  isAgent ? 'mr-auto items-start' : 'ml-auto items-end'
                }`}
              >
                <span className="text-[10px] font-mono text-muted px-1">
                  {isAgent ? 'Ava' : 'You'}
                </span>
                <div
                  className={`rounded-lg px-3.5 py-2 text-xs leading-relaxed ${
                    isAgent
                      ? 'bg-canvas text-ink border border-hairline'
                      : 'bg-ink text-black font-medium'
                  }`}
                >
                  <p className="whitespace-pre-wrap">{item.text}</p>
                </div>
              </div>
            );
          })
        )}

        {/* Interim Speech */}
        {interimTranscript && (
          <div className="flex flex-col gap-1 max-w-[85%] ml-auto items-end">
            <span className="text-[10px] font-mono text-primary px-1">listening...</span>
            <div className="rounded-lg px-3.5 py-2 text-xs bg-canvas text-muted border border-hairline italic">
              &ldquo;{interimTranscript}&rdquo;
            </div>
          </div>
        )}

        {/* Thinking Indicator */}
        {voiceStatus === 'processing' && (
          <div className="flex items-center gap-2 text-[11px] text-muted font-mono pl-1 pt-1">
            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
            <span>thinking...</span>
          </div>
        )}
      </div>
    </div>
  );
}
