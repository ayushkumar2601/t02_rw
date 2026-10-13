'use client';

import React, { useState } from 'react';
import { ArrowUp } from 'lucide-react';

interface TextFallbackInputProps {
  sessionId: string | null;
  disabled: boolean;
  onSubmit: (text: string) => void;
}

export function TextFallbackInput({
  sessionId,
  disabled,
  onSubmit,
}: TextFallbackInputProps) {
  const [inputText, setInputText] = useState<string>('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || disabled || !sessionId) return;
    onSubmit(inputText.trim());
    setInputText('');
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-surface-card border border-hairline rounded-lg p-1.5 pl-3 flex items-center gap-2"
    >
      <input
        type="text"
        value={inputText}
        onChange={(e) => setInputText(e.target.value)}
        disabled={disabled || !sessionId}
        placeholder={!sessionId ? 'Start call to respond...' : 'Type a response...'}
        className="flex-1 bg-transparent text-xs text-ink placeholder:text-muted focus:outline-none disabled:opacity-40"
      />

      <button
        type="submit"
        disabled={disabled || !inputText.trim() || !sessionId}
        className="h-7 w-7 rounded-md bg-ink hover:bg-ink/80 disabled:opacity-20 text-black flex items-center justify-center transition-opacity cursor-pointer disabled:cursor-not-allowed"
        title="Send response"
      >
        <ArrowUp className="w-3.5 h-3.5" />
      </button>
    </form>
  );
}
