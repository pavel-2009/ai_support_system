import { Headphones, MessageSquare, Sparkles } from 'lucide-react';

export default function AppWindow({
  activeMode = 'customer',
  backendOnline,
  children,
  currentUser,
  onModeChange,
}) {
  const isOperatorOrAdmin =
    currentUser && (currentUser.role === 'operator' || currentUser.role === 'admin');

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
            {isOperatorOrAdmin && (
              <div className="mode-switcher" role="tablist">
                <button
                  className={`mode-switch-btn ${activeMode === 'customer' ? 'active' : ''}`}
                  onClick={() => onModeChange?.('customer')}
                  role="tab"
                  type="button"
                >
                  <MessageSquare size={13} />
                  <span>Клиентский чат</span>
                </button>
                <button
                  className={`mode-switch-btn ${activeMode === 'operator' ? 'active' : ''}`}
                  onClick={() => onModeChange?.('operator')}
                  role="tab"
                  type="button"
                >
                  <Headphones size={13} />
                  <span>Пульт оператора</span>
                </button>
              </div>
            )}
          </div>
          <div className="window-actions">
            {currentUser?.nickname || currentUser?.email}
          </div>
        </header>
        <section className="window-body">{children}</section>
      </main>
    </div>
  );
}
