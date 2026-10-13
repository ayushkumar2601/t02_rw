'use client';

import React from 'react';
import { X } from 'lucide-react';

interface ErrorAlertProps {
  message: string | null;
  isVoiceSupported: boolean;
  isMicAllowed: boolean | null;
  onDismiss: () => void;
}

export function ErrorAlert({
  message,
  isVoiceSupported,
  isMicAllowed,
  onDismiss,
}: ErrorAlertProps) {
  if (!message && isVoiceSupported && isMicAllowed !== false) {
    return null;
  }

  return (
    <div className="space-y-2">
      {!isVoiceSupported && (
        <div className="bg-surface-card border border-hairline rounded-lg px-3.5 py-2.5 text-xs text-muted flex items-center justify-between">
          <span>Web Speech API is unavailable in this browser. Use text input below.</span>
        </div>
      )}

      {isMicAllowed === false && (
        <div className="bg-surface-card border border-semantic-error/40 text-semantic-error rounded-lg px-3.5 py-2.5 text-xs flex items-center justify-between">
          <span>Microphone access blocked. Enable microphone in browser settings or use text input.</span>
        </div>
      )}

      {message && (
        <div className="bg-surface-card border border-semantic-error/40 text-semantic-error rounded-lg px-3.5 py-2.5 text-xs flex items-center justify-between">
          <span>{message}</span>
          <button
            onClick={onDismiss}
            className="text-muted hover:text-ink p-1 cursor-pointer"
            title="Dismiss"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}
