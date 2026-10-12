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
    submitTextTurn,
    toggleMute,
    clearError,
  } = useVoiceSession();

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* 1. Header with Live Backend Connection Status */}
      <Header backendHealthy={backendHealthy} />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 space-y-5">
        {/* 2. Error and Browser Capability Alerts */}
        <ErrorAlert
          message={errorMessage}
          isVoiceSupported={isVoiceSupported}
          isMicAllowed={isMicAllowed}
          onDismiss={clearError}
        />

        {/* 3. Voice Control Panel */}
        <VoiceControls
          sessionId={sessionId}
          voiceStatus={voiceStatus}
          conversationState={conversationState}
          isMuted={isMuted}
          isVoiceSupported={isVoiceSupported}
          onStartCall={startCall}
          onEndCall={endCall}
          onToggleMute={toggleMute}
        />

        {/* 4. Primary Grid: Transcript + Text Fallback vs Lead Summary */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          {/* Left Column: Live Transcript + Text Input */}
          <div className="lg:col-span-7 flex flex-col space-y-3">
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

          {/* Right Column: Lead Summary */}
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

        {/* 5. Saved Leads in SQLite Table */}
        <div className="pt-2">
          <SavedLeadsPanel lastUpdatedTrigger={persistedLead} />
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 px-6 py-4 mt-auto text-xs text-slate-500">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <div>
            Ava SDR Voice Agent · Phase 1 Core Backend & Phase 2 Voice Dashboard
          </div>
          <div className="flex items-center gap-4 text-slate-400">
            <span>₹0 Implementation Cost</span>
            <span>·</span>
            <span>Deterministic State Machine</span>
            <span>·</span>
            <span>SQLite Storage</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
