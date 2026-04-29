import { useCallback, useRef, useState } from 'react';
import { parseSSELine, SSEEvent } from '../utils/sseParser';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export interface ThinkingStep {
  tool: string;
  status: 'calling' | 'done';
  duration_ms?: number;
  summary?: Record<string, unknown>;
}

export interface StructuredResult {
  result_type: string;
  data: Record<string, unknown>;
}

export interface AgentStreamState {
  isStreaming: boolean;
  streamedText: string;
  thinkingSteps: ThinkingStep[];
  structuredResults: StructuredResult[];
  currentAgent: string | null;
  error: string | null;
  currentResearchSessionId: string | null;
}

export function useAgentStream(sessionId: string | null) {
  const [state, setState] = useState<AgentStreamState>({
    isStreaming: false,
    streamedText: '',
    thinkingSteps: [],
    structuredResults: [],
    currentAgent: null,
    error: null,
    currentResearchSessionId: null,
  });

  const abortRef = useRef<AbortController | null>(null);

  const startStream = useCallback(
    async (
      message: string,
      researchSessionId: string | null,
      onDone?: (newSessionId: string) => void
    ) => {
      if (abortRef.current) abortRef.current.abort();
      abortRef.current = new AbortController();

      setState({
        isStreaming: true,
        streamedText: '',
        thinkingSteps: [],
        structuredResults: [],
        currentAgent: null,
        error: null,
        currentResearchSessionId: researchSessionId,
      });

      try {
        const response = await fetch(`${API_URL}/api/agent/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Session-ID': sessionId || '',
          },
          body: JSON.stringify({
            message,
            research_session_id: researchSessionId,
          }),
          signal: abortRef.current.signal,
        });

        if (!response.ok) {
          const err = await response.json().catch(() => ({ detail: 'Request failed' }));
          setState((s) => ({ ...s, isStreaming: false, error: err.detail || 'Request failed' }));
          return;
        }

        const reader = response.body!.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() ?? '';

          for (const line of lines) {
            const event = parseSSELine(line);
            if (!event) continue;
            _applyEvent(event, setState, onDone);
          }
        }
      } catch (err: unknown) {
        if (err instanceof Error && err.name === 'AbortError') return;
        setState((s) => ({
          ...s,
          isStreaming: false,
          error: err instanceof Error ? err.message : 'Stream error',
        }));
      }
    },
    [sessionId]
  );

  const stopStream = useCallback(() => {
    abortRef.current?.abort();
    setState((s) => ({ ...s, isStreaming: false }));
  }, []);

  return { ...state, startStream, stopStream };
}

function _applyEvent(
  event: SSEEvent,
  setState: React.Dispatch<React.SetStateAction<AgentStreamState>>,
  onDone?: (sessionId: string) => void
) {
  switch (event.type) {
    case 'thinking':
      setState((s) => ({
        ...s,
        thinkingSteps: [
          ...s.thinkingSteps,
          { tool: event.tool!, status: 'calling' },
        ],
      }));
      break;

    case 'tool_result':
      setState((s) => ({
        ...s,
        thinkingSteps: s.thinkingSteps.map((step) =>
          step.tool === event.tool && step.status === 'calling'
            ? { ...step, status: 'done', duration_ms: event.duration_ms, summary: event.data }
            : step
        ),
      }));
      break;

    case 'text_delta':
      setState((s) => ({ ...s, streamedText: s.streamedText + (event.content ?? '') }));
      break;

    case 'sub_agent_start':
      setState((s) => ({ ...s, currentAgent: event.agent ?? null }));
      break;

    case 'sub_agent_done':
      setState((s) => ({ ...s, currentAgent: null }));
      break;

    case 'structured_result':
      setState((s) => ({
        ...s,
        structuredResults: [
          ...s.structuredResults,
          { result_type: event.result_type!, data: event.data as Record<string, unknown> },
        ],
      }));
      break;

    case 'done':
      setState((s) => ({
        ...s,
        isStreaming: false,
        currentResearchSessionId: event.research_session_id ?? s.currentResearchSessionId,
      }));
      if (event.research_session_id && onDone) {
        onDone(event.research_session_id);
      }
      break;

    case 'error':
      setState((s) => ({ ...s, isStreaming: false, error: event.message ?? 'Unknown error' }));
      break;
  }
}
