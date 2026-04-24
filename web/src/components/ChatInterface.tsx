import React, { useState, useRef, useEffect } from 'react';
import { apiClient } from '../utils/apiClient';
import './ChatInterface.css';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
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
      // Parse user input and call appropriate workflow
      const workflow = parseUserInput(input);

      if (!workflow) {
        throw new Error(
          'Could not understand. Try: "Evaluate [organism] [protein]", "Generate controls for [protein] PDB [id]", etc.'
        );
      }

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

      const assistantMessage: Message = {
        role: 'assistant',
        content: result.response || 'Workflow completed.',
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: any) {
      setError(
        err.response?.data?.detail || err.message || 'An error occurred'
      );
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

// Simple NLP parser (server-side router is authoritative)
function parseUserInput(input: string): any {
  const lower = input.toLowerCase();

  // Evaluate target
  if (
    lower.includes('evaluate') ||
    lower.includes('assess') ||
    lower.includes('target')
  ) {
    const organisms = [
      'staphylococcus aureus',
      's. aureus',
      'plasmodium falciparum',
      'p. falciparum',
    ];
    let organism = '';
    for (const o of organisms) {
      if (lower.includes(o)) {
        organism = o;
        break;
      }
    }

    const proteinMatch = input.match(/(?:protein|protein name|target)[\s:]*([^,\n]+)/i);
    const proteinId = input.match(/\b([A-Z]{2,})\b/)?.[1];

    if (organism && proteinMatch) {
      return {
        type: 'evaluate',
        organism: organism === 's. aureus' ? 'Staphylococcus aureus' : organism,
        protein: proteinMatch[1].trim(),
        proteinId,
      };
    }
  }

  // Get controls
  if (
    lower.includes('control') ||
    lower.includes('validation') ||
    lower.includes('decoy')
  ) {
    const pdbMatch = input.match(/pdb[\s:]?([0-9A-Z]+)/i);
    const proteinMatch = input.match(
      /for\s+([^,\n]+?)(?:\s+pdb|\s*$)/i
    );

    if (pdbMatch && proteinMatch) {
      return {
        type: 'controls',
        protein: proteinMatch[1].trim(),
        pdbId: pdbMatch[1].toUpperCase(),
      };
    }
  }

  // Prep screening
  if (lower.includes('screening') || lower.includes('pharmacophore')) {
    const pdbMatch = input.match(/pdb[\s:]?([0-9A-Z]+)/i);
    const proteinMatch = input.match(
      /for\s+([^,\n]+?)(?:\s+pdb|\s*$)/i
    );
    const mechanismMatch = input.match(
      /mechanism[\s:]*([^,\n]+)/i
    );

    if (pdbMatch && proteinMatch && mechanismMatch) {
      return {
        type: 'screening',
        protein: proteinMatch[1].trim(),
        pdbId: pdbMatch[1].toUpperCase(),
        mechanism: mechanismMatch[1].trim(),
      };
    }
  }

  // Analyze hits
  if (
    lower.includes('analyze') ||
    lower.includes('hits') ||
    lower.includes('prioritize')
  ) {
    const numMatch = input.match(/(\d+,?\d*)\s*compounds?/i);
    const proteinMatch = input.match(/(?:for|analyzing)\s+([^\n,]+)/i);
    const scoreMatch = input.match(/mean[\s:]*([^\n,]+)/i);

    if (numMatch && proteinMatch) {
      return {
        type: 'hits',
        protein: proteinMatch[1].trim(),
        numCompounds: parseInt(numMatch[1].replace(',', '')),
        dockingScores: scoreMatch ? scoreMatch[1].trim() : 'Mean: -8.2, SD: 1.1',
      };
    }
  }

  return null;
}
