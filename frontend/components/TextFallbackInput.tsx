'use client';

import React, { useState } from 'react';
import { Send, MessageSquareText } from 'lucide-react';

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
      className="bg-slate-900 border border-slate-800 rounded-xl p-3 flex items-center gap-3 shadow-sm"
    >
      <div className="text-slate-400 pl-2">
        <MessageSquareText className="w-4 h-4 text-slate-500" />
      </div>

      <input
        type="text"
        value={inputText}
        onChange={(e) => setInputText(e.target.value)}
        disabled={disabled || !sessionId}
        placeholder={
          !sessionId
            ? 'Start a call above to interact via voice or text...'
            : 'Type your answer or correction here (text fallback mode)...'
        }
        className="flex-1 bg-transparent text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none disabled:opacity-50"
      />

      <button
        type="submit"
        disabled={disabled || !inputText.trim() || !sessionId}
        className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:hover:bg-indigo-600 text-white text-xs font-medium transition-colors cursor-pointer"
      >
        <Send className="w-3.5 h-3.5" />
        <span>Send</span>
      </button>
    </form>
  );
}
