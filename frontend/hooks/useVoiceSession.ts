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
  const sessionIdRef = useRef<string | null>(null);
  const lastProcessedTurnTextRef = useRef<string>('');
  const isProcessingTurnRef = useRef<boolean>(false);
  const isMutedRef = useRef<boolean>(false);

  isMutedRef.current = isMuted;
  sessionIdRef.current = sessionId;

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

  // 2. Speech Synthesis Helper
  const stopSpeaking = useCallback(() => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      isSpeakingRef.current = false;
    }
  }, []);

  const speakText = useCallback(
    (text: string, onEnd?: () => void) => {
      if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
        if (onEnd) onEnd();
        return;
      }

      stopSpeaking();

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
        (v) => (v.lang.startsWith('en') && v.name.includes('Natural')) || v.name.includes('Google') || v.name.includes('Samantha')
      );
      if (preferredVoice) {
        utterance.voice = preferredVoice;
      }

      utterance.onstart = () => {
        isSpeakingRef.current = true;
        setVoiceStatus('speaking');
      };

      utterance.onend = () => {
        isSpeakingRef.current = false;
        if (onEnd) onEnd();
      };

      utterance.onerror = (e) => {
        console.warn('Speech synthesis error:', e);
        isSpeakingRef.current = false;
        if (onEnd) onEnd();
      };

      window.speechSynthesis.speak(utterance);
    },
    [stopSpeaking]
  );

  // 3. Start / Stop Speech Recognition
  const stopRecognition = useCallback(() => {
    if (recognitionRef.current && isRecognitionActiveRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {
        // ignore
      }
      isRecognitionActiveRef.current = false;
    }
  }, []);

  const startRecognition = useCallback(() => {
    if (typeof window === 'undefined') return;
    const win = window as unknown as IWindow;
    const SpeechRecognition = win.SpeechRecognition || win.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setIsVoiceSupported(false);
      return;
    }

    if (isRecognitionActiveRef.current) {
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
        if (!isSpeakingRef.current && !isProcessingTurnRef.current) {
          setVoiceStatus('listening');
        }
      };

      recognition.onresult = (event: any) => {
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

        setInterimTranscript(interim);

        // Barge-in: if user starts speaking while Ava is speaking, cancel synthesis
        if (interim.trim() && isSpeakingRef.current) {
          stopSpeaking();
        }

        const trimmedFinal = finalUtterance.trim();
        if (trimmedFinal && trimmedFinal !== lastProcessedTurnTextRef.current) {
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
        } else if (event.error !== 'no-speech') {
          console.warn('Speech recognition warning:', event.error);
        }
      };

      recognition.onend = () => {
        isRecognitionActiveRef.current = false;
        // If session is still active and not ended, safely restart recognition
        if (sessionIdRef.current && !isProcessingTurnRef.current && sessionStatus === 'active') {
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
  }, [sessionStatus, stopSpeaking]);

  // 4. Submit Turn (Caller speech or Text fallback)
  const handleCallerUtterance = useCallback(
    async (text: string) => {
      const currentSessionId = sessionIdRef.current;
      if (!currentSessionId || isProcessingTurnRef.current || !text.trim()) {
        return;
      }

      isProcessingTurnRef.current = true;
      setVoiceStatus('processing');
      stopSpeaking();

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
            setVoiceStatus('listening');
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

  // 5. Start Call Action
  const startCall = useCallback(async () => {
    setErrorMessage(null);
    setVoiceStatus('connecting');
    setTranscript([]);
    setPersistedLead(null);
    lastProcessedTurnTextRef.current = '';

    try {
      const newSession = await api.createSession();
      setSessionId(newSession.session_id);
      sessionIdRef.current = newSession.session_id;
      setConversationState(newSession.state);
      setSessionStatus(newSession.status);

      // Add initial greeting to transcript
      const greetingItem: TranscriptItem = {
        id: `greeting_${newSession.session_id}`,
        speaker: 'agent',
        text: newSession.greeting,
        timestamp: new Date(),
      };
      setTranscript([greetingItem]);

      // Speak greeting, then start speech recognition
      speakText(newSession.greeting, () => {
        startRecognition();
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Could not create voice session';
      setErrorMessage(`Connection failed: ${msg}. Make sure the FastAPI backend is running.`);
      setVoiceStatus('error');
    }
  }, [speakText, startRecognition]);

  // 6. End Call Action
  const endCall = useCallback(async () => {
    stopSpeaking();
    stopRecognition();

    const currentSessionId = sessionIdRef.current;
    if (currentSessionId) {
      setVoiceStatus('processing');
      try {
        const endRes = await api.endSession(currentSessionId);
        setSessionStatus(endRes.status);
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

  // 7. Text Fallback Turn Submission
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

  // 8. Toggle Mute
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
    submitTextTurn,
    toggleMute,
    clearError: () => setErrorMessage(null),
  };
}
