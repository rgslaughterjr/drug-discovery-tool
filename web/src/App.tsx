import React, { useContext } from 'react';
import { SessionContext } from './context/SessionContext';
import { LoginModal } from './components/LoginModal';
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
      <div className="app-header">
        <h1>🧪 Drug Discovery Agent</h1>
        <p>Session active. Ready for natural language queries.</p>
      </div>

      <div className="app-container">
        <p>Chat interface coming in Phase 3...</p>
      </div>
    </div>
  );
}

export default App;
