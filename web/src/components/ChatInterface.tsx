import React, { useState, useRef, useEffect } from 'react';
import { apiClient } from '../utils/apiClient';
import './ChatInterface.css';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface Workflow {
  type: 'evaluate' | 'controls' | 'screening' | 'hits';
  organism?: string;
  protein?: string;
  proteinId?: string;
  pdbId?: string;
  mechanism?: string;
  dockingSoftware?: string;
  numCompounds?: number;
  dockingScores?: string;
  controls?: string;
}

interface ChatInterfaceProps {
  sessionId: string;
}

export function ChatInterface({ sessionId }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  apiClient.setSessionId(sessionId);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage: Message = {
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);
    setError('');

    try {
      // Parse user input and call appropriate workflow(s)
      const workflows = parseUserInput(input);

      if (!workflows || workflows.length === 0) {
        throw new Error(
          'Could not understand. Try: "Evaluate [organism] [protein]", "Generate controls for [protein] PDB [id]", etc.'
        );
      }

      // Execute all workflows sequentially
      const results: string[] = [];
      for (const workflow of workflows) {
        let result;
        switch (workflow.type) {
          case 'evaluate':
            result = await apiClient.evaluateTarget(
              workflow.organism!,
              workflow.protein!,
              workflow.proteinId
            );
            break;
          case 'controls':
            result = await apiClient.getControls(
              workflow.organism!,
              workflow.protein!,
              workflow.pdbId!
            );
            break;
          case 'screening':
            result = await apiClient.prepScreening(
              workflow.organism!,
              workflow.protein!,
              workflow.pdbId!,
              workflow.mechanism!,
              workflow.dockingSoftware
            );
            break;
          case 'hits':
            result = await apiClient.analyzeHits(
              workflow.protein!,
              workflow.numCompounds!,
              workflow.dockingScores!,
              workflow.controls
            );
            break;
          default:
            throw new Error('Unknown workflow');
        }
        results.push(result.response || 'Workflow completed.');
      }

      const assistantMessage: Message = {
        role: 'assistant',
        content: results.join('\n\n---\n\n') || 'Workflows completed.',
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: any) {
      const errorMessage =
        (typeof err.response?.data?.detail === 'string' ? err.response.data.detail : null) ||
        (typeof err.message === 'string' ? err.message : null) ||
        (typeof err === 'string' ? err : 'An error occurred');
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-interface">
      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="welcome-message">
            <h2>Welcome to Drug Discovery Agent</h2>
            <p>Try asking:</p>
            <ul>
              <li>"Evaluate Staphylococcus aureus GyrB"</li>
              <li>"Generate controls for S. aureus GyrB, PDB 4P8O"</li>
              <li>"Prepare screening for Plasmodium falciparum DHFR"</li>
              <li>"Analyze hits for GyrB with 180000 compounds"</li>
            </ul>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            <div className="message-content">
              {msg.role === 'assistant' ? (
                <div className="markdown-content">{msg.content}</div>
              ) : (
                msg.content
              )}
            </div>
            <small className="message-time">
              {msg.timestamp.toLocaleTimeString()}
            </small>
          </div>
        ))}

        {loading && (
          <div className="message assistant">
            <div className="loading-spinner">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <small>Processing...</small>
          </div>
        )}

        {error && (
          <div className="message error">
            <div className="message-content">⚠️ {error}</div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSendMessage} className="chat-input-form">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Describe your drug discovery task..."
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

// Extract target organism and protein from user input
function extractTarget(input: string): { organism: string; protein: string } | null {
  const organisms = [
    { match: 'staphylococcus aureus', name: 'Staphylococcus aureus' },
    { match: 's. aureus', name: 'Staphylococcus aureus' },
    { match: 'plasmodium falciparum', name: 'Plasmodium falciparum' },
    { match: 'p. falciparum', name: 'Plasmodium falciparum' },
  ];

  const lower = input.toLowerCase();

  for (const organism of organisms) {
    const index = lower.indexOf(organism.match);
    if (index === -1) continue;

    const protein = input
      .slice(index + organism.match.length)
      .replace(/^[\s,;:.-]+/, '')
      .replace(/\s+(?:with|using|pdb|mechanism)\b.*$/i, '')
      .trim();

    if (protein) return { organism: organism.name, protein };
  }

  return null;
}

// Enhanced NLP parser - detects multiple workflows in single prompt
function parseUserInput(input: string): Workflow[] | null {
  const lower = input.toLowerCase();
  const workflows: Workflow[] = [];

  // Evaluate target
  if (
    lower.includes('evaluate') ||
    lower.includes('assess') ||
    lower.includes('target')
  ) {
    const target = extractTarget(input);
    const proteinMatch = input.match(/(?:protein|protein name|target)[\s:]*([^,\n]+)/i);
    const proteinId = input.match(/\b([A-Z]{2,})\b/)?.[1];
    const protein = proteinMatch?.[1].trim() || target?.protein;

    if (target?.organism && protein) {
      workflows.push({
        type: 'evaluate',
        organism: target.organism,
        protein,
        proteinId,
      });
    }
  }

  // Get controls
  if (
    lower.includes('control') ||
    lower.includes('validation') ||
    lower.includes('decoy')
  ) {
    const target = extractTarget(input);
    const pdbMatch = input.match(/pdb[\s:]?([0-9A-Z]+)/i);
    const proteinMatch = input.match(/for\s+([^\s,]+)/i);

    if (pdbMatch && proteinMatch) {
      const organism = target?.organism || 'Plasmodium falciparum';
      workflows.push({
        type: 'controls',
        organism,
        protein: proteinMatch[1].trim(),
        pdbId: pdbMatch[1].toUpperCase(),
      });
    }
  }

  // Prep screening
  if (lower.includes('screening') || lower.includes('pharmacophore')) {
    const target = extractTarget(input);
    const pdbMatch = input.match(/pdb[\s:]?([0-9A-Z]+)/i);
    const mechanismMatch = input.match(/mechanism[\s:]*([^\s,\n]+)/i);

    if (pdbMatch && mechanismMatch) {
      const organism = target?.organism || 'Plasmodium falciparum';
      const protein = target?.protein || 'DHFR';
      workflows.push({
        type: 'screening',
        organism,
        protein,
        pdbId: pdbMatch[1].toUpperCase(),
        mechanism: mechanismMatch[1].trim(),
      });
    }
  }

  // Analyze hits
  if (
    lower.includes('analyze') ||
    lower.includes('hits') ||
    lower.includes('prioritize')
  ) {
    const numMatch = input.match(/(\d+,?\d*)\s*compounds?/i);
    const proteinMatch = input.match(/(?:for|analyzing)\s+([^\s,]+)/i);
    const scoreMatch = input.match(/mean[\s:]*([^\n,]+)/i);

    if (numMatch && proteinMatch) {
      workflows.push({
        type: 'hits',
        protein: proteinMatch[1].trim(),
        numCompounds: parseInt(numMatch[1].replace(',', '')),
        dockingScores: scoreMatch ? scoreMatch[1].trim() : 'Mean: -8.2, SD: 1.1',
      });
    }
  }

  return workflows.length > 0 ? workflows : null;
}
