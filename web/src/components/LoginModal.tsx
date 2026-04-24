import React, { useState, useContext } from 'react';
import axios from 'axios';
import { SessionContext } from '../context/SessionContext';
import './LoginModal.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const PROVIDERS = [
  'anthropic',
  'openai',
  'google',
  'cohere',
  'mistral',
  'nvidia',
  'grok',
];

const DEFAULT_MODELS: Record<string, string> = {
  anthropic: 'claude-3-5-sonnet-20241022',
  openai: 'gpt-4o',
  google: 'gemini-2.0-flash',
  cohere: 'command-r-plus',
  mistral: 'mistral-large',
  nvidia: 'nemo-12b',
  grok: 'grok-2',
};

interface LoginModalProps {
  onLoginSuccess: () => void;
}

export function LoginModal({ onLoginSuccess }: LoginModalProps) {
  const { setSession } = useContext(SessionContext);
  const [provider, setProvider] = useState('anthropic');
  const [apiKey, setApiKey] = useState('');
  const [model, setModel] = useState(DEFAULT_MODELS['anthropic']);
  const [agreed, setAgreed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleProviderChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newProvider = e.target.value;
    setProvider(newProvider);
    setModel(DEFAULT_MODELS[newProvider] || '');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!agreed) {
      setError('You must agree to the data handling policy');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await axios.post(`${API_URL}/session/create`, {
        provider,
        api_key: apiKey,
        model,
      });

      const { session_id, session_expires_in } = response.data;
      setSession(session_id, provider, model, session_expires_in);
      onLoginSuccess();
    } catch (err: any) {
      setError(
        err.response?.data?.detail || 'Failed to create session. Check your API key.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-modal-overlay">
      <div className="login-modal">
        <div className="login-header">
          <h1>🔐 Drug Discovery Agent</h1>
          <p>Secure Session Setup</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          {/* Provider Selection */}
          <div className="form-group">
            <label htmlFor="provider">LLM Provider</label>
            <select
              id="provider"
              value={provider}
              onChange={handleProviderChange}
              className="form-select"
            >
              {PROVIDERS.map((p) => (
                <option key={p} value={p}>
                  {p.charAt(0).toUpperCase() + p.slice(1)}
                </option>
              ))}
            </select>
          </div>

          {/* API Key Input */}
          <div className="form-group">
            <label htmlFor="apiKey">API Key (masked)</label>
            <input
              id="apiKey"
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="Enter your API key"
              required
              className="form-input"
            />
            <small>Your key is stored in memory only, never saved to disk.</small>
          </div>

          {/* Model Selection */}
          <div className="form-group">
            <label htmlFor="model">Model Name (optional)</label>
            <input
              id="model"
              type="text"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder="e.g., claude-3-5-sonnet-20241022"
              className="form-input"
            />
            <small>Leave blank for default. Editable to use custom or experimental models.</small>
          </div>

          {/* Confirmation Checkbox */}
          <div className="form-group checkbox-group">
            <input
              id="agreed"
              type="checkbox"
              checked={agreed}
              onChange={(e) => setAgreed(e.target.checked)}
              className="form-checkbox"
            />
            <label htmlFor="agreed" className="checkbox-label">
              ✓ I understand my API key will NOT be stored and will be deleted when I close
              this window or click "End Session"
            </label>
          </div>

          {/* Error Message */}
          {error && <div className="error-message">{error}</div>}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={!agreed || !apiKey || loading}
            className="submit-button"
          >
            {loading ? 'Creating session...' : 'Start Session'}
          </button>
        </form>

        <div className="login-footer">
          <p className="security-note">
            🔒 Your credentials are never logged, stored on disk, or sent to third parties.
            They exist only in memory during your session.
          </p>
        </div>
      </div>
    </div>
  );
}
