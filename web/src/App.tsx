import React, { useContext } from 'react';
import { SessionContext } from './context/SessionContext';
import { LoginModal } from './components/LoginModal';
import { ChatInterface } from './components/ChatInterface';
import { SessionBadge } from './components/SessionBadge';
import { useSessionCleanup } from './hooks/useSessionCleanup';
import './App.css';

function App() {
  const { sessionId, clearSession } = useContext(SessionContext);

  useSessionCleanup(sessionId, () => {
    clearSession();
    window.location.reload();
  });

  if (!sessionId) {
    return <LoginModal onLoginSuccess={() => {}} />;
  }

  return (
    <div className="app">
      <SessionBadge />

      <div className="app-header">
        <h1>🧪 Drug Discovery Agent</h1>
        <p>Natural language interface for AI-assisted drug discovery</p>
      </div>

      <div className="app-container">
        <ChatInterface sessionId={sessionId} />
      </div>
    </div>
  );
}

export default App;
