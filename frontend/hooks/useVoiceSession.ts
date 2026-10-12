'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '@/lib/api';
import {
  ConversationState,
  PersistedLeadRecord,
  QualificationStatus,
  SessionStatus,
  TranscriptItem,
  ValidatedLead,
} from '@/types';

// Web Speech API interface declarations
interface IWindow extends Window {
  SpeechRecognition?: any;
  webkitSpeechRecognition?: any;
}

export type VoiceSessionStatus =
  | 'idle'
  | 'connecting'
  | 'listening'
  | 'processing'
  | 'speaking'
  | 'ended'
  | 'error';

/**
 * Detects whether an incoming recognition transcript is an acoustic echo
 * of what Ava just spoke through the laptop speakers.
 */
function isAcousticEcho(transcript: string, agentText: string): boolean {
  if (!transcript || !agentText) return false;
  const cleanTranscript = transcript
    .toLowerCase()
    .replace(/[^\w\s]/g, '')
    .trim();
  const cleanAgent = agentText
    .toLowerCase()
    .replace(/[^\w\s]/g, '')
    .trim();

  if (!cleanTranscript || !cleanAgent) return false;

  // Exact match or agent utterance contains the caller transcript
  if (cleanAgent.includes(cleanTranscript)) return true;

  // Check word matching for short phrases (e.g. "could you clarify", "marketing budget")
  const transcriptWords = cleanTranscript.split(/\s+/).filter(Boolean);
  if (transcriptWords.length <= 4 && transcriptWords.length > 0) {
    const allInAgent = transcriptWords.every((w) => cleanAgent.includes(w));
    if (allInAgent) return true;
  }

  // Token overlap ratio for longer captured echoes
  const agentWords = new Set(cleanAgent.split(/\s+/).filter(Boolean));
  const matchedWords = transcriptWords.filter((w) => agentWords.has(w));
  if (transcriptWords.length >= 2 && matchedWords.length / transcriptWords.length >= 0.7) {
    return true;
  }

  return false;
}

export function useVoiceSession() {
  // Session State
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionStatus, setSessionStatus] = useState<SessionStatus>('active');
  const [conversationState, setConversationState] = useState<ConversationState>('GREETING');
  const [voiceStatus, setVoiceStatus] = useState<VoiceSessionStatus>('idle');
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [isVoiceSupported, setIsVoiceSupported] = useState<boolean>(true);

  // Transcript & Lead State
  const [transcript, setTranscript] = useState<TranscriptItem[]>([]);
  const [interimTranscript, setInterimTranscript] = useState<string>('');
  const [currentLead, setCurrentLead] = useState<ValidatedLead>({
    company_name: null,
    business_type: null,
    company_size: null,
    marketing_budget: null,
    budget_currency: null,
    budget_period: 'unknown',
    contact_name: null,
    contact_email: null,
  });
  const [missingFields, setMissingFields] = useState<string[]>([
    'company_size',
    'marketing_budget',
    'budget_currency',
    'budget_period',
  ]);
  const [qualificationStatus, setQualificationStatus] = useState<QualificationStatus>('in_progress');
  const [persistedLead, setPersistedLead] = useState<PersistedLeadRecord | null>(null);

  // Error & Backend State
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isMicAllowed, setIsMicAllowed] = useState<boolean | null>(null);
  const [backendHealthy, setBackendHealthy] = useState<boolean>(false);

  // Refs for tracking async state & speech instances
  const recognitionRef = useRef<any>(null);
  const isRecognitionActiveRef = useRef<boolean>(false);
  const isSpeakingRef = useRef<boolean>(false);
  const isAcousticCooldownRef = useRef<boolean>(false);
  const cooldownTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const sessionStatusRef = useRef<SessionStatus>('active');
  const lastProcessedTurnTextRef = useRef<string>('');
  const lastSpokenAgentTextRef = useRef<string>('');
  const isProcessingTurnRef = useRef<boolean>(false);
  const isMutedRef = useRef<boolean>(false);

  isMutedRef.current = isMuted;
  sessionIdRef.current = sessionId;
  sessionStatusRef.current = sessionStatus;

  // 1. Initial Health Check & Web Speech Detection
  useEffect(() => {
    const checkStatus = async () => {
      try {
        const health = await api.checkHealth();
        if (health.status === 'healthy') {
          setBackendHealthy(true);
        }
      } catch {
        setBackendHealthy(false);
      }
    };
    checkStatus();
    const interval = setInterval(checkStatus, 15000);

    // Detect browser SpeechRecognition support
    if (typeof window !== 'undefined') {
      const win = window as unknown as IWindow;
      const hasSpeechRec = !!(win.SpeechRecognition || win.webkitSpeechRecognition);
      setIsVoiceSupported(hasSpeechRec);
    }

    return () => clearInterval(interval);
  }, []);

  // 2. Stop Recognition Helper
  const stopRecognition = useCallback(() => {
    if (recognitionRef.current && isRecognitionActiveRef.current) {
      try {
        recognitionRef.current.abort();
      } catch {
        try {
          recognitionRef.current.stop();
        } catch {
          // ignore
        }
      }
      isRecognitionActiveRef.current = false;
    }
  }, []);

  // 3. Speech Synthesis Helper
  const stopSpeaking = useCallback(() => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      isSpeakingRef.current = false;
    }
    if (cooldownTimeoutRef.current) {
      clearTimeout(cooldownTimeoutRef.current);
      cooldownTimeoutRef.current = null;
    }
    isAcousticCooldownRef.current = false;
  }, []);

  // 4. Start Speech Recognition
  const startRecognition = useCallback(() => {
    if (typeof window === 'undefined') return;
    const win = window as unknown as IWindow;
    const SpeechRecognition = win.SpeechRecognition || win.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setIsVoiceSupported(false);
      return;
    }

    // Do NOT start if Ava is currently speaking, in acoustic cooldown, or processing
    if (
      isRecognitionActiveRef.current ||
      isSpeakingRef.current ||
      isAcousticCooldownRef.current ||
      isProcessingTurnRef.current ||
      sessionStatusRef.current !== 'active'
    ) {
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      recognition.onstart = () => {
        isRecognitionActiveRef.current = true;
        setIsMicAllowed(true);
        if (!isSpeakingRef.current && !isProcessingTurnRef.current && !isAcousticCooldownRef.current) {
          setVoiceStatus('listening');
        }
      };

      recognition.onresult = (event: any) => {
        // Multi-Layer Echo Defense 1: If Ava is speaking or in post-speech cooldown, discard completely
        if (isSpeakingRef.current || isAcousticCooldownRef.current || isProcessingTurnRef.current) {
          setInterimTranscript('');
          return;
        }

        let interim = '';
        let finalUtterance = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const item = event.results[i];
          if (item.isFinal) {
            finalUtterance += item[0].transcript;
          } else {
            interim += item[0].transcript;
          }
        }

        // Multi-Layer Echo Defense 2: Filter interim speech if it contains Ava's last spoken utterance
        if (isAcousticEcho(interim, lastSpokenAgentTextRef.current)) {
          setInterimTranscript('');
          return;
        }

        setInterimTranscript(interim);

        const trimmedFinal = finalUtterance.trim();
        if (trimmedFinal && trimmedFinal !== lastProcessedTurnTextRef.current) {
          // Multi-Layer Echo Defense 3: Filter final utterance if it matches Ava's last words
          if (isAcousticEcho(trimmedFinal, lastSpokenAgentTextRef.current)) {
            console.warn('[Voice] Echo suppression: Filtered laptop speaker bleed:', trimmedFinal);
            setInterimTranscript('');
            return;
          }

          setInterimTranscript('');
          lastProcessedTurnTextRef.current = trimmedFinal;
          // Process caller turn
          handleCallerUtterance(trimmedFinal);
        }
      };

      recognition.onerror = (event: any) => {
        if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
          setIsMicAllowed(false);
          setErrorMessage('Microphone access denied. You can use the text interface fallback below.');
          setVoiceStatus('error');
        } else if (event.error !== 'no-speech' && event.error !== 'aborted') {
          console.warn('Speech recognition warning:', event.error);
        }
      };

      recognition.onend = () => {
        isRecognitionActiveRef.current = false;
        // Strictly prevent automatic restart if Ava is speaking, cooling down, or turn is processing
        if (
          sessionIdRef.current &&
          sessionStatusRef.current === 'active' &&
          !isProcessingTurnRef.current &&
          !isSpeakingRef.current &&
          !isAcousticCooldownRef.current
        ) {
          try {
            recognition.start();
          } catch {
            // ignore
          }
        }
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (err) {
      console.error('Failed to initialize SpeechRecognition:', err);
    }
  }, []);

  // 5. Sequential Turn-Taking Speak Function
  const speakText = useCallback(
    (text: string, onEnd?: () => void) => {
      if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
        if (onEnd) onEnd();
        return;
      }

      // 1. Immediately kill recognition to prevent laptop mic from picking up speaker output
      stopRecognition();
      stopSpeaking();
      setInterimTranscript('');

      // Track the agent's utterance for echo cancellation
      lastSpokenAgentTextRef.current = text.trim();

      if (isMutedRef.current) {
        if (onEnd) onEnd();
        return;
      }

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      utterance.lang = 'en-US';

      // Pick a clean natural English voice if available
      const voices = window.speechSynthesis.getVoices();
      const preferredVoice = voices.find(
        (v) =>
          (v.lang.startsWith('en') && v.name.includes('Natural')) ||
          v.name.includes('Google') ||
          v.name.includes('Samantha')
      );
      if (preferredVoice) {
        utterance.voice = preferredVoice;
      }

      utterance.onstart = () => {
        isSpeakingRef.current = true;
        setVoiceStatus('speaking');
        // Double-check recognition is stopped
        stopRecognition();
      };

      const finishSpeaking = () => {
        isSpeakingRef.current = false;

        // Acoustic dissipation cooldown:
        // Wait 600ms for laptop speaker reverberation and audio buffers to completely clear
        // before re-enabling the microphone.
        isAcousticCooldownRef.current = true;

        if (cooldownTimeoutRef.current) {
          clearTimeout(cooldownTimeoutRef.current);
        }

        cooldownTimeoutRef.current = setTimeout(() => {
          isAcousticCooldownRef.current = false;
          if (
            sessionIdRef.current &&
            sessionStatusRef.current === 'active' &&
            !isProcessingTurnRef.current
          ) {
            setVoiceStatus('listening');
            startRecognition();
          }
          if (onEnd) onEnd();
        }, 600);
      };

      utterance.onend = () => {
        finishSpeaking();
      };

      utterance.onerror = (e) => {
        console.warn('Speech synthesis error:', e);
        finishSpeaking();
      };

      window.speechSynthesis.speak(utterance);
    },
    [startRecognition, stopRecognition, stopSpeaking]
  );

  // 6. Manual Interrupt (Safe user barge-in that stops Ava and immediately activates mic)
  const interruptSpeaking = useCallback(() => {
    if (isSpeakingRef.current || isAcousticCooldownRef.current) {
      stopSpeaking();
      setInterimTranscript('');
      setVoiceStatus('listening');
      // Delay mic start by 200ms to allow audio hardware buffer to flush
      setTimeout(() => {
        startRecognition();
      }, 200);
    }
  }, [startRecognition, stopSpeaking]);

  // 7. Submit Turn (Caller speech or Text fallback)
  const handleCallerUtterance = useCallback(
    async (text: string) => {
      const currentSessionId = sessionIdRef.current;
      if (!currentSessionId || isProcessingTurnRef.current || !text.trim()) {
        return;
      }

      // Stop recognition while backend processes and prepares agent response
      stopRecognition();
      stopSpeaking();

      isProcessingTurnRef.current = true;
      setVoiceStatus('processing');

      const turnId = `turn_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;

      // Append caller utterance to transcript
      const callerTurn: TranscriptItem = {
        id: turnId,
        speaker: 'caller',
        text: text.trim(),
        timestamp: new Date(),
      };
      setTranscript((prev) => [...prev, callerTurn]);

      try {
        const response = await api.sendTurn(currentSessionId, turnId, text.trim());

        // Update state
        setConversationState(response.conversation_state);
        setCurrentLead(response.lead);
        setMissingFields(response.missing_fields);
        setQualificationStatus(response.qualification_status);
        setSessionStatus(response.session_status);
        sessionStatusRef.current = response.session_status;

        // Append agent response to transcript
        const agentTurn: TranscriptItem = {
          id: `agent_${turnId}`,
          speaker: 'agent',
          text: response.response,
          timestamp: new Date(),
        };
        setTranscript((prev) => [...prev, agentTurn]);

        isProcessingTurnRef.current = false;

        // Speak response
        if (response.should_end_call || response.session_status !== 'active') {
          speakText(response.response, async () => {
            setVoiceStatus('ended');
            stopRecognition();
            // Fetch final persisted lead record
            try {
              const leads = await api.listLeads(10, 0);
              const found = leads.find((l) => l.session_id === currentSessionId);
              if (found) setPersistedLead(found);
            } catch {
              // ignore
            }
          });
        } else {
          speakText(response.response, () => {
            // Callback handled inside speakText cooldown
          });
        }
      } catch (err: unknown) {
        isProcessingTurnRef.current = false;
        const msg = err instanceof Error ? err.message : 'Turn processing failed';
        setErrorMessage(msg);
        setVoiceStatus('error');
      }
    },
    [speakText, stopRecognition, stopSpeaking]
  );

  // 8. Start Call Action
  const startCall = useCallback(async () => {
    setErrorMessage(null);
    setVoiceStatus('connecting');
    setTranscript([]);
    setPersistedLead(null);
    lastProcessedTurnTextRef.current = '';
    lastSpokenAgentTextRef.current = '';

    try {
      const newSession = await api.createSession();
      setSessionId(newSession.session_id);
      sessionIdRef.current = newSession.session_id;
      setConversationState(newSession.state);
      setSessionStatus(newSession.status);
      sessionStatusRef.current = newSession.status;

      // Add initial greeting to transcript
      const greetingItem: TranscriptItem = {
        id: `greeting_${newSession.session_id}`,
        speaker: 'agent',
        text: newSession.greeting,
        timestamp: new Date(),
      };
      setTranscript([greetingItem]);

      // Speak greeting with sequential turn-taking (mic will turn on AFTER greeting finishes)
      speakText(newSession.greeting);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Could not create voice session';
      setErrorMessage(`Connection failed: ${msg}. Make sure the FastAPI backend is running.`);
      setVoiceStatus('error');
    }
  }, [speakText]);

  // 9. End Call Action
  const endCall = useCallback(async () => {
    stopSpeaking();
    stopRecognition();

    const currentSessionId = sessionIdRef.current;
    if (currentSessionId) {
      setVoiceStatus('processing');
      try {
        const endRes = await api.endSession(currentSessionId);
        setSessionStatus(endRes.status);
        sessionStatusRef.current = endRes.status;
        setQualificationStatus(endRes.qualification_status);
        setConversationState('ENDED');

        // Retrieve persisted lead record
        if (endRes.lead_id) {
          const record = await api.getLead(endRes.lead_id);
          setPersistedLead(record);
        } else {
          const leads = await api.listLeads(5, 0);
          const found = leads.find((l) => l.session_id === currentSessionId);
          if (found) setPersistedLead(found);
        }

        setVoiceStatus('ended');
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Error finalizing session';
        setErrorMessage(msg);
        setVoiceStatus('ended');
      }
    } else {
      setVoiceStatus('idle');
    }
  }, [stopRecognition, stopSpeaking]);

  // 10. Text Fallback Turn Submission
  const submitTextTurn = useCallback(
    (text: string) => {
      if (!sessionIdRef.current) {
        setErrorMessage('Please start a call first before submitting a message.');
        return;
      }
      handleCallerUtterance(text);
    },
    [handleCallerUtterance]
  );

  // 11. Toggle Mute
  const toggleMute = useCallback(() => {
    setIsMuted((prev) => {
      const next = !prev;
      if (next) stopSpeaking();
      return next;
    });
  }, [stopSpeaking]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopSpeaking();
      stopRecognition();
    };
  }, [stopRecognition, stopSpeaking]);

  return {
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
    clearError: () => setErrorMessage(null),
  };
}
