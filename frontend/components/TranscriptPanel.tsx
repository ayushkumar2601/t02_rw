'use client';

import React, { useEffect, useRef } from 'react';
import { Bot, User, Mic, Sparkles } from 'lucide-react';
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

  // Auto-scroll to latest turn
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [transcript, interimTranscript, voiceStatus]);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl flex flex-col h-[480px] shadow-sm overflow-hidden">
      {/* Panel Header */}
      <div className="px-4 py-3 border-b border-slate-800 bg-slate-900/80 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-indigo-400" />
          <h2 className="text-sm font-semibold text-slate-200">Live Conversation Transcript</h2>
        </div>
        <span className="text-xs text-slate-500 font-mono">
          {transcript.length} {transcript.length === 1 ? 'turn' : 'turns'}
        </span>
      </div>

      {/* Transcript Scroll Area */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 space-y-4 scroll-smooth"
      >
        {transcript.length === 0 && !interimTranscript ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-500 text-center p-6 space-y-2">
            <Bot className="w-8 h-8 text-slate-600 mb-1" />
            <p className="text-sm font-medium text-slate-400">No active conversation</p>
            <p className="text-xs max-w-sm">
              Click &quot;Start Voice Call&quot; above to begin speaking with Ava, or enter a message in the text input below.
            </p>
          </div>
        ) : (
          transcript.map((item) => {
            const isAgent = item.speaker === 'agent';
            return (
              <div
                key={item.id}
                className={`flex gap-3 max-w-[88%] ${
                  isAgent ? 'mr-auto' : 'ml-auto flex-row-reverse'
                }`}
              >
                {/* Speaker Avatar */}
                <div
                  className={`w-7 h-7 rounded-lg flex-shrink-0 flex items-center justify-center text-xs ${
                    isAgent
                      ? 'bg-gradient-to-tr from-indigo-600 to-violet-500 text-white shadow'
                      : 'bg-slate-700 text-slate-200'
                  }`}
                >
                  {isAgent ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
                </div>

                {/* Message Bubble */}
                <div
                  className={`rounded-2xl px-4 py-2.5 text-sm ${
                    isAgent
                      ? 'bg-slate-800/90 text-slate-100 border border-slate-700/60 rounded-tl-sm'
                      : 'bg-indigo-600 text-white shadow-sm rounded-tr-sm'
                  }`}
                >
                  <div className="flex items-center justify-between gap-4 mb-1">
                    <span
                      className={`text-[11px] font-semibold tracking-wider uppercase ${
                        isAgent ? 'text-indigo-400' : 'text-indigo-200'
                      }`}
                    >
                      {isAgent ? 'Ava' : 'You (Caller)'}
                    </span>
                    <span
                      className={`text-[10px] ${
                        isAgent ? 'text-slate-400 font-mono' : 'text-indigo-200 font-mono'
                      }`}
                    >
                      {new Date(item.timestamp).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit',
                      })}
                    </span>
                  </div>
                  <p className="leading-relaxed whitespace-pre-wrap">{item.text}</p>
                </div>
              </div>
            );
          })
        )}

        {/* Live Interim Speech Bubble */}
        {interimTranscript && (
          <div className="flex gap-3 max-w-[85%] ml-auto flex-row-reverse animate-pulse">
            <div className="w-7 h-7 rounded-lg flex-shrink-0 flex items-center justify-center bg-slate-700 text-slate-300">
              <Mic className="w-4 h-4" />
            </div>
            <div className="rounded-2xl px-4 py-2.5 text-sm bg-indigo-950/60 text-indigo-300 border border-indigo-700/40 rounded-tr-sm italic">
              <span className="text-[10px] font-mono block text-indigo-400 mb-0.5">Listening...</span>
              &ldquo;{interimTranscript}&rdquo;
            </div>
          </div>
        )}

        {/* Processing Indicator */}
        {voiceStatus === 'processing' && (
          <div className="flex gap-3 max-w-[85%] mr-auto">
            <div className="w-7 h-7 rounded-lg flex-shrink-0 flex items-center justify-center bg-indigo-600/30 text-indigo-400 border border-indigo-500/30">
              <Bot className="w-4 h-4" />
            </div>
            <div className="rounded-2xl px-4 py-2 text-xs bg-slate-800/60 text-slate-400 border border-slate-700/40 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-ping" />
              <span>Ava is thinking & extracting lead details...</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
