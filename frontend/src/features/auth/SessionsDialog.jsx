import { useEffect, useState } from 'react';
import { LogOut, Shield, X } from 'lucide-react';
import { api } from '../../services/api';

export default function SessionsDialog({ onClose, onLoggedOut }) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [revoking, setRevoking] = useState(false);

  useEffect(() => {
    api.getSessions().then(setSessions).catch((requestError) => setError(requestError.message)).finally(() => setLoading(false));
  }, []);

  const logoutEverywhere = async () => {
    setRevoking(true);
    try {
      await api.logoutAllSessions();
      onLoggedOut(null);
      onClose();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setRevoking(false);
    }
  };

  return (
    <div className="sessions-overlay" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="sessions-dialog" aria-labelledby="sessions-title" role="dialog">
        <header className="sessions-header">
          <div><span className="sessions-kicker"><Shield size={14} />Безопасность</span><h2 id="sessions-title">Активные сессии</h2></div>
          <button className="icon-button" onClick={onClose} title="Закрыть" type="button"><X size={18} /></button>
        </header>
        {error && <p className="sessions-error">{error}</p>}
        {loading ? <p className="sessions-empty">Загрузка сессий...</p> : sessions.length ? <div className="sessions-list">{sessions.map((session) => <div className="session-row" key={session.jti}><div><strong>Сессия устройства</strong><span>Истекает {new Date(session.expires_at).toLocaleString()}</span></div><span className="session-active">Активна</span></div>)}</div> : <p className="sessions-empty">Активных сессий не найдено.</p>}
        <button className="sessions-revoke" disabled={revoking || loading} onClick={logoutEverywhere} type="button"><LogOut size={16} />{revoking ? 'Завершение...' : 'Выйти на всех устройствах'}</button>
      </section>
    </div>
  );
}