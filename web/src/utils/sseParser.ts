export type SSEEventType =
  | 'thinking'
  | 'tool_result'
  | 'text_delta'
  | 'sub_agent_start'
  | 'sub_agent_done'
  | 'structured_result'
  | 'done'
  | 'error';

export interface SSEEvent {
  type: SSEEventType;
  // text
  content?: string;
  // tool lifecycle
  tool?: string;
  status?: string;
  duration_ms?: number;
  data?: Record<string, unknown>;
  // sub-agent
  agent?: string;
  // structured result
  result_type?: string;
  // session
  research_session_id?: string;
  usage?: { input_tokens: number; output_tokens: number };
  // error
  message?: string;
}

export function parseSSELine(line: string): SSEEvent | null {
  const prefix = 'data: ';
  if (!line.startsWith(prefix)) return null;
  const payload = line.slice(prefix.length).trim();
  if (payload === '[DONE]') return null;
  try {
    return JSON.parse(payload) as SSEEvent;
  } catch {
    return null;
  }
}
