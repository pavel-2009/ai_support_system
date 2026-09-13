import { Sparkles } from 'lucide-react';

export default function AppWindow({ backendOnline, children, currentUser }) {
  return (
    <div className="app-viewport">
      <div className="ambient-bg" aria-hidden="true">
        <div className="ambient-orb orb-1" />
        <div className="ambient-orb orb-2" />
        <div className="ambient-orb orb-3" />
      </div>
      <main className="window-container">
        <header className="window-header">
          <div className="window-controls" aria-hidden="true">
            <span className="control-dot dot-close" />
            <span className="control-dot dot-minimize" />
            <span className="control-dot dot-maximize" />
          </div>
          <div className="window-title">
            <Sparkles color="#818cf8" size={16} />
            <span>AI Support Desk</span>
            <span className={`window-status-pill ${backendOnline ? '' : 'is-offline'}`}>
              <span className="status-beacon" />
              {backendOnline ? 'Online' : 'Offline'}
            </span>
          </div>
          <div className="window-actions">{currentUser?.nickname || currentUser?.email}</div>
        </header>
        <section className="window-body">{children}</section>
      </main>
    </div>
  );
}
