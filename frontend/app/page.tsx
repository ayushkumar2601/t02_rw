'use client';

import React from 'react';
import { Header } from '@/components/Header';
import { VoiceControls } from '@/components/VoiceControls';
import { TranscriptPanel } from '@/components/TranscriptPanel';
import { LeadSummary } from '@/components/LeadSummary';
import { TextFallbackInput } from '@/components/TextFallbackInput';
import { SavedLeadsPanel } from '@/components/SavedLeadsPanel';
import { ErrorAlert } from '@/components/ErrorAlert';
import { useVoiceSession } from '@/hooks/useVoiceSession';

export default function Home() {
  const {
    sessionId,
    sessionStatus,
    conversationState,
    voiceStatus,
    isMuted,
    isVoiceSupported,
    isMicAllowed,
    backendHealthy,
    transcript,
    interimTranscript,
    currentLead,
    missingFields,
    qualificationStatus,
    persistedLead,
    errorMessage,
    startCall,
    endCall,
    interruptSpeaking,
    submitTextTurn,
    toggleMute,
    clearError,
  } = useVoiceSession();

  return (
    <div className="min-h-screen flex flex-col font-sans bg-canvas text-ink">
      {/* Navigation */}

      <Header backendHealthy={backendHealthy} />

      {/* Main Container */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-6 space-y-4">
        {/* Alerts */}
        <ErrorAlert
          message={errorMessage}
          isVoiceSupported={isVoiceSupported}
          isMicAllowed={isMicAllowed}
          onDismiss={clearError}
        />

        {/* Controls */}
        <VoiceControls
          sessionId={sessionId}
          voiceStatus={voiceStatus}
          conversationState={conversationState}
          isMuted={isMuted}
          isVoiceSupported={isVoiceSupported}
          onStartCall={startCall}
          onEndCall={endCall}
          onToggleMute={toggleMute}
          onInterrupt={interruptSpeaking}
        />

        {/* Grid: Transcript & Lead Summary */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          <div className="lg:col-span-7 flex flex-col space-y-2.5">
            <TranscriptPanel
              transcript={transcript}
              interimTranscript={interimTranscript}
              voiceStatus={voiceStatus}
            />
            <TextFallbackInput
              sessionId={sessionId}
              disabled={voiceStatus === 'processing'}
              onSubmit={submitTextTurn}
            />
          </div>

          <div className="lg:col-span-5 flex flex-col">
            <LeadSummary
              lead={currentLead}
              missingFields={missingFields}
              qualificationStatus={qualificationStatus}
              sessionStatus={sessionStatus}
              persistedLead={persistedLead}
            />
          </div>
        </div>

        {/* Saved Leads */}
        <div className="pt-2">
          <SavedLeadsPanel lastUpdatedTrigger={persistedLead} />
        </div>
      </main>

      {/* Minimal Footer */}
      <footer className="border-t border-hairline py-4 px-6 text-xs text-muted">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <span>Ava</span>
          <span className="font-mono text-[11px]">sqlite · local</span>
        </div>
      </footer>
    </div>
  );
}
