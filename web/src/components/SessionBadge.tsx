import React, { useContext, useState, useEffect } from 'react';
import { SessionContext } from '../context/SessionContext';
import { apiClient } from '../utils/apiClient';
import './SessionBadge.css';

export function SessionBadge() {
  const { sessionId, provider, expiresIn, clearSession } = useContext(SessionContext);
  const [timeLeft, setTimeLeft] = useState(expiresIn || 0);
  const [showConfirm, setShowConfirm] = useState(false);

  useEffect(() => {
    if (!expiresIn) return;

    setTimeLeft(expiresIn);
    const interval = setInterval(() => {
      setTimeLeft((prev) => Math.max(0, prev - 1));
    }, 1000);

    return () => clearInterval(interval);
  }, [expiresIn]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  const handleEndSession = async () => {
    if (!sessionId) return;

    try {
      await apiClient.deleteSession(sessionId);
      clearSession();
      window.location.href = '/';
    } catch (error) {
      console.error('Error ending session:', error);
    }
  };

  if (!sessionId) return null;

  return (
    <>
      <div className="session-badge">
        <span className="badge-content">
          🔐 {provider || 'Unknown'} ({formatTime(timeLeft)})
        </span>
        <button
          className="end-session-btn"
          onClick={() => setShowConfirm(true)}
          title="End session and clear credentials"
        >
          ✕
        </button>
      </div>

      {showConfirm && (
        <div className="confirmation-modal-overlay" onClick={() => setShowConfirm(false)}>
          <div className="confirmation-modal" onClick={(e) => e.stopPropagation()}>
            <h3>End Session?</h3>
            <p>
              Your API key and all session data will be <strong>permanently deleted</strong>.
              You will need to provide your credentials again to continue.
            </p>
            <div className="modal-buttons">
              <button
                className="btn-cancel"
                onClick={() => setShowConfirm(false)}
              >
                Cancel
              </button>
              <button
                className="btn-confirm"
                onClick={handleEndSession}
              >
                End Session & Clear Data
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
