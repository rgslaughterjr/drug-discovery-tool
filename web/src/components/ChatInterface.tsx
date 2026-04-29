import React, { useCallback, useEffect, useRef, useState } from 'react';
import { apiClient } from '../utils/apiClient';
import { useAgentStream } from '../hooks/useAgentStream';
import { AgentThinking } from './AgentThinking';
import { CompoundTable } from './CompoundTable';
import { WorkflowProgress } from './WorkflowProgress';
import './ChatInterface.css';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  compoundData?: unknown[];
  isStreaming?: boolean;
}

interface ChatInterfaceProps {
  sessionId: string;
  provider: string;
  model: string;
}

export function ChatInterface({ sessionId, provider, model }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [legacyLoading, setLegacyLoading] = useState(false);
  const [legacyError, setLegacyError] = useState('');
  const [researchSessionId, setResearchSessionId] = useState<string | null>(null);
  const [pipelineStage, setPipelineStage] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  apiClient.setSessionId(sessionId);

  const isAgentMode = provider === 'anthropic';

  const {
    isStreaming,
    streamedText,
    thinkingSteps,
    structuredResults,
    currentAgent,
    error: streamError,
    startStream,
  } = useAgentStream(sessionId);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => { scrollToBottom(); }, [messages, streamedText]);

  // Commit the streaming message once done
  const prevStreamingRef = useRef(false);
  useEffect(() => {
    if (prevStreamingRef.current && !isStreaming && streamedText) {
      setMessages((prev) => {
        // Replace placeholder streaming message or append
        const last = prev[prev.length - 1];
        if (last?.isStreaming) {
          return [
            ...prev.slice(0, -1),
            {
              role: 'assistant',
              content: streamedText,
              timestamp: new Date(),
              compoundData: structuredResults.flatMap((r) => {
                const rows = (r.data as { rows?: unknown[] })?.rows;
                return Array.isArray(rows) ? rows : [];
              }),
            },
          ];
        }
        return [
          ...prev,
          { role: 'assistant', content: streamedText, timestamp: new Date() },
        ];
      });
    }
    prevStreamingRef.current = isStreaming;
  }, [isStreaming]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSend = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!input.trim()) return;

      const userMsg: Message = {
        role: 'user',
        content: input,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMsg]);
      const sentInput = input;
      setInput('');

      if (isAgentMode) {
        // Add placeholder for streaming response
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: '', timestamp: new Date(), isStreaming: true },
        ]);
        await startStream(sentInput, researchSessionId, (newId) => {
          setResearchSessionId(newId);
        });
      } else {
        // Legacy mode: keyword-based routing to /api/workflow/*
        await handleLegacy(sentInput);
      }
    },
    [input, isAgentMode, researchSessionId, startStream]
  );

  const handleLegacy = async (text: string) => {
    setLegacyLoading(true);
    setLegacyError('');
    try {
      const workflow = parseLegacyInput(text);
      if (!workflow) {
        throw new Error(
          'Could not understand. Try: "Evaluate [organism] [protein]", "Generate controls for [protein] PDB [id]", etc.'
        );
      }
      let result: { response?: string };
      switch (workflow.type) {
        case 'evaluate':
          result = await apiClient.evaluateTarget(workflow.organism!, workflow.protein!, workflow.proteinId);
          break;
        case 'controls':
          result = await apiClient.getControls(workflow.organism!, workflow.protein!, workflow.pdbId!);
          break;
        case 'screening':
          result = await apiClient.prepScreening(workflow.organism!, workflow.protein!, workflow.pdbId!, workflow.mechanism!, workflow.dockingSoftware);
          break;
        case 'hits':
          result = await apiClient.analyzeHits(workflow.protein!, workflow.numCompounds!, workflow.dockingScores!);
          break;
        default:
          throw new Error('Unknown workflow');
      }
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: result.response || 'Workflow completed.', timestamp: new Date() },
      ]);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'An error occurred';
      setLegacyError(msg);
    } finally {
      setLegacyLoading(false);
    }
  };

  const loading = isStreaming || legacyLoading;
  const error = streamError || legacyError;

  return (
    <div className="chat-interface">
      {isAgentMode && <WorkflowProgress currentStage={pipelineStage} />}

      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="welcome-message">
            <h2>Drug Discovery Agent {isAgentMode ? '🔬' : '(Classic Mode)'}</h2>
            {isAgentMode ? (
              <>
                <p>Powered by Claude + NVIDIA Nemotron with real database lookups (ChEMBL, PubChem, UniProt, RCSB PDB).</p>
                <p>Try asking:</p>
              </>
            ) : (
              <>
                <p>Classic mode ({provider}). No real database lookups. Switch to Anthropic for full agentic mode.</p>
                <p>Try:</p>
              </>
            )}
            <ul>
              <li>"Evaluate Staphylococcus aureus GyrB as a drug target"</li>
              <li>"Generate validated controls for S. aureus GyrB"</li>
              <li>"Design a screening campaign for P. falciparum DHFR"</li>
              <li>"Analyze 180,000 virtual screening hits for GyrB"</li>
            </ul>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            <div className="message-content">
              {msg.isStreaming ? (
                <>
                  {isStreaming && thinkingSteps.length > 0 && (
                    <AgentThinking steps={thinkingSteps} currentAgent={currentAgent} />
                  )}
                  <span>{streamedText}</span>
                  {isStreaming && <span className="cursor-blink">▌</span>}
                </>
              ) : (
                <>
                  <div className="message-text">{msg.content}</div>
                  {msg.compoundData && msg.compoundData.length > 0 && (
                    <CompoundTable compounds={msg.compoundData as Record<string, unknown>[]} />
                  )}
                </>
              )}
            </div>
            <small className="message-time">{msg.timestamp.toLocaleTimeString()}</small>
          </div>
        ))}

        {loading && !isStreaming && (
          <div className="message assistant">
            <div className="loading-spinner">
              <span /><span /><span />
            </div>
            <small>Processing…</small>
          </div>
        )}

        {error && (
          <div className="message error">
            <div className="message-content">⚠ {error}</div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {!isAgentMode && (
        <div className="classic-mode-banner">
          Classic mode — <strong>{provider}</strong>. No real database lookups. Switch to Anthropic for full agentic capabilities.
        </div>
      )}

      <form onSubmit={handleSend} className="chat-input-form">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={isAgentMode ? 'Ask anything about your drug target…' : 'Describe your drug discovery task…'}
          disabled={loading}
          className="chat-input"
        />
        <button type="submit" disabled={loading || !input.trim()} className="send-button">
          {loading ? '⏳' : '➤'}
        </button>
      </form>
    </div>
  );
}

// Legacy parser (only used for non-Anthropic providers)
function parseLegacyInput(input: string): Record<string, unknown> | null {
  const lower = input.toLowerCase();
  if (lower.includes('evaluate') || lower.includes('assess') || lower.includes('target')) {
    const organisms = ['staphylococcus aureus', 's. aureus', 'plasmodium falciparum', 'p. falciparum'];
    let organism = '';
    for (const o of organisms) { if (lower.includes(o)) { organism = o; break; } }
    const proteinMatch = input.match(/(?:protein|target)[\s:]*([^,\n]+)/i);
    if (organism && proteinMatch) {
      return { type: 'evaluate', organism: organism === 's. aureus' ? 'Staphylococcus aureus' : organism, protein: proteinMatch[1].trim() };
    }
  }
  if (lower.includes('control') || lower.includes('decoy')) {
    const pdbMatch = input.match(/pdb[\s:]?([0-9A-Z]+)/i);
    const proteinMatch = input.match(/for\s+([^,\n]+?)(?:\s+pdb|\s*$)/i);
    if (pdbMatch && proteinMatch) return { type: 'controls', protein: proteinMatch[1].trim(), pdbId: pdbMatch[1].toUpperCase(), organism: 'Unknown' };
  }
  if (lower.includes('screening') || lower.includes('pharmacophore')) {
    const pdbMatch = input.match(/pdb[\s:]?([0-9A-Z]+)/i);
    const proteinMatch = input.match(/for\s+([^,\n]+?)(?:\s+pdb|\s*$)/i);
    const mechanismMatch = input.match(/mechanism[\s:]*([^,\n]+)/i);
    if (pdbMatch && proteinMatch && mechanismMatch) return { type: 'screening', protein: proteinMatch[1].trim(), pdbId: pdbMatch[1].toUpperCase(), mechanism: mechanismMatch[1].trim(), organism: 'Unknown' };
  }
  if (lower.includes('analyze') || lower.includes('hits') || lower.includes('prioritize')) {
    const numMatch = input.match(/(\d+,?\d*)\s*compounds?/i);
    const proteinMatch = input.match(/(?:for|analyzing)\s+([^\n,]+)/i);
    if (numMatch && proteinMatch) return { type: 'hits', protein: proteinMatch[1].trim(), numCompounds: parseInt(numMatch[1].replace(',', '')), dockingScores: 'Mean: -8.2, SD: 1.1' };
  }
  return null;
}
