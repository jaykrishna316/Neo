import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import './App.css';
import Dashboard from './pages/Dashboard';

function App() {
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    // Check API connectivity
    const checkConnection = async () => {
      try {
        const response = await fetch('/health');
        setConnected(response.ok);
      } catch {
        setConnected(false);
      }
    };

    checkConnection();
    const interval = setInterval(checkConnection, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <BrowserRouter>
      <div className="app">
        <header className="app-header">
          <h1>🚀 Neo Mission Control</h1>
          <div className="status-indicator">
            <span className={`status ${connected ? 'connected' : 'disconnected'}`}>
              {connected ? '● Connected' : '● Disconnected'}
            </span>
          </div>
        </header>

        <main className="app-main">
          <Routes>
            <Route path="/" element={<Dashboard />} />
          </Routes>
        </main>

        <footer className="app-footer">
          <p>Neo Mission Control Dashboard • Real-time Conflict Detection & Coupling Analysis</p>
        </footer>
      </div>
    </BrowserRouter>
  );
}

export default App;
