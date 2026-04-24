import { useEffect, useCallback } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export function useSessionCleanup(sessionId: string | null, onSessionEnd: () => void) {
  const handleBeforeUnload = useCallback(async () => {
    if (sessionId) {
      try {
        await axios.delete(`${API_URL}/session/${sessionId}`, {
          timeout: 2000,
        });
      } catch (error) {
        console.error('Session cleanup error:', error);
      }
    }
  }, [sessionId]);

  useEffect(() => {
    if (!sessionId) return;

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [sessionId, handleBeforeUnload]);

  // Inactivity timeout (30 min)
  useEffect(() => {
    if (!sessionId) return;

    const INACTIVITY_WARNING = 25 * 60 * 1000; // 25 min
    const INACTIVITY_LOGOUT = 30 * 60 * 1000; // 30 min

    let warningTimeout: NodeJS.Timeout;
    let logoutTimeout: NodeJS.Timeout;

    const resetTimers = () => {
      clearTimeout(warningTimeout);
      clearTimeout(logoutTimeout);

      warningTimeout = setTimeout(() => {
        const confirmed = window.confirm(
          'Your session will expire in 5 minutes due to inactivity. Click OK to continue.'
        );
        if (!confirmed) {
          handleLogout();
        }
      }, INACTIVITY_WARNING);

      logoutTimeout = setTimeout(() => {
        handleLogout();
      }, INACTIVITY_LOGOUT);
    };

    const handleLogout = async () => {
      try {
        await axios.delete(`${API_URL}/session/${sessionId}`);
      } catch (error) {
        console.error('Logout error:', error);
      }
      onSessionEnd();
    };

    const handleUserActivity = () => resetTimers();

    document.addEventListener('mousemove', handleUserActivity);
    document.addEventListener('keydown', handleUserActivity);
    document.addEventListener('click', handleUserActivity);

    resetTimers();

    return () => {
      clearTimeout(warningTimeout);
      clearTimeout(logoutTimeout);
      document.removeEventListener('mousemove', handleUserActivity);
      document.removeEventListener('keydown', handleUserActivity);
      document.removeEventListener('click', handleUserActivity);
    };
  }, [sessionId, onSessionEnd, handleBeforeUnload]);
}
