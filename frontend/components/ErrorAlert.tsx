'use client';

import React from 'react';
import { AlertCircle, X, MicOff, Info } from 'lucide-react';

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
      {/* Unsupported Web Speech Warning */}
      {!isVoiceSupported && (
        <div className="bg-amber-950/40 border border-amber-800/60 rounded-xl p-3.5 flex items-start gap-3 text-xs text-amber-200">
          <Info className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
          <div className="flex-1">
            <span className="font-semibold block text-amber-300 mb-0.5">
              Browser Web Speech Recognition Unsupported
            </span>
            <span>
              Your browser does not expose the Web Speech API (supported in Google Chrome & Edge desktop). You can still complete full lead qualification using the text fallback input below.
            </span>
          </div>
        </div>
      )}

      {/* Mic Permission Denied */}
      {isMicAllowed === false && (
        <div className="bg-rose-950/40 border border-rose-800/60 rounded-xl p-3.5 flex items-start gap-3 text-xs text-rose-200">
          <MicOff className="w-4 h-4 text-rose-400 mt-0.5 flex-shrink-0" />
          <div className="flex-1">
            <span className="font-semibold block text-rose-300 mb-0.5">
              Microphone Permission Denied
            </span>
            <span>
              Microphone access was blocked. To enable voice speech, allow microphone access in your browser site settings or use the text fallback input below.
            </span>
          </div>
        </div>
      )}

      {/* General Error Message */}
      {message && (
        <div className="bg-rose-950/40 border border-rose-800/60 rounded-xl p-3.5 flex items-start justify-between gap-3 text-xs text-rose-200">
          <div className="flex items-start gap-2.5">
            <AlertCircle className="w-4 h-4 text-rose-400 mt-0.5 flex-shrink-0" />
            <div>
              <span className="font-semibold block text-rose-300 mb-0.5">Notice</span>
              <span>{message}</span>
            </div>
          </div>
          <button
            onClick={onDismiss}
            className="text-rose-400 hover:text-rose-200 p-1 cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}
