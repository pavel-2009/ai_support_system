import { useEffect, useMemo, useState } from 'react';
import { statusLabels } from './ConversationList';

export function AdminDashboard({ api, conversations, onConversationsChange }) {
  const [users, setUsers] = useState([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState('');
  const [selectedId, setSelectedId] = useState(null);

  useEffect(() => { api.users().then(setUsers).catch((requestError) => setError(requestError.message)); }, [api]);
  const selected = useMemo(() => conversations.find((item) => item.id === selectedId), [conversations, selectedId]);
  const open = conversations.filter((item) => item.status !== 'closed');
  const escalated = conversations.filter((item) => item.status === 'escalated');
  const avgConfidence = conversations.length ? Math.round(conversations.reduce((sum, item) => sum + (item.ai_confidence || 0), 0) / conversations.length * 100) : 0;
  const averageWait = open.length ? Math.round(open.reduce((sum, item) => sum + (Date.now() - new Date(item.created_at)), 0) / open.length / 60000) : 0;
  const metrics = [['Активные обращения', open.length, 'сейчас'], ['Эскалации', escalated.length, 'нуждаются в операторе'], ['Среднее ожидание', `${averageWait} мин`, 'по открытым обращениям'], ['Операторы', users.filter((item) => item.role === 'operator').length, 'в системе']];

  async function runAction(name, method) {
    if (!selected || busy) return;
    setBusy(name);
    setError('');
    try {
      await method(selected.id);
      await onConversationsChange();
      setError('');
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy('');
    }
  }

  return <main className="dashboard">
    <header><p className="eyebrow">ADMIN DASHBOARD</p><h1>Пульс поддержки</h1><p className="muted">Очередь, состояния диалогов и качество AI в одном месте.</p></header>
    {error && <p className="form-error" role="alert">{error}</p>}
    <section className="metric-grid">{metrics.map(([label, value, hint]) => <article className="metric" key={label}><span>{label}</span><strong>{value}</strong><small>{hint}</small></article>)}</section>
    <section className="dashboard-grid">
      <article className="panel status-panel"><h3>Статусы обращений</h3>
        {Object.entries(statusLabels).map(([status, label]) => { const count = conversations.filter((item) => item.status === status).length; return <div className="bar-row" key={status}>
          <span><i className={`status-dot ${status}`} />{label}</span><div><i style={{ width: `${conversations.length ? count / conversations.length * 100 : 0}%` }} /></div><b>{count}</b>
        </div>; })}
      </article>
      <article className="panel"><h3>Контроль AI</h3><div className="quality"><strong>{avgConfidence}%</strong><span>средняя уверенность AI</span></div><p className="muted">Следите за эскалациями и диалогами, которые долго остаются без ответа.</p></article>
    </section>
    <section className="panel conversation-panel">
      <div className="panel-heading"><div><h3>Диалоги</h3><p className="muted">Выберите обращение для управления состоянием.</p></div><span className="count-badge">{conversations.length}</span></div>
      <div className="admin-conversations">
        {conversations.map((conversation) => <button key={conversation.id} className={`admin-conversation ${selectedId === conversation.id ? 'selected' : ''}`} onClick={() => setSelectedId(conversation.id)}>
          <span><b>#{conversation.id}</b><small>Пользователь #{conversation.user_id}</small></span>
          <span className={`pill ${conversation.status}`}>{statusLabels[conversation.status] || conversation.status}</span>
        </button>)}
      </div>
      {selected && <div className="admin-actions">
        <div><b>Диалог #{selected.id}</b><span className={`pill ${selected.status}`}>{statusLabels[selected.status]}</span></div>
        <div className="action-group">
          {selected.status === 'escalated' && !selected.operator_id && <button className="secondary" disabled={!!busy} onClick={() => runAction('assign', api.assign)}>{busy === 'assign' ? 'Назначаем…' : 'Взять в работу'}</button>}
          {selected.operator_id && ['waiting_for_operator', 'waiting_for_user'].includes(selected.status) && <button className="secondary" disabled={!!busy} onClick={() => runAction('back', api.backToAi)}>{busy === 'back' ? 'Возвращаем…' : 'Вернуть AI'}</button>}
          {selected.status !== 'closed' && <button className="danger" disabled={!!busy} onClick={() => runAction('close', api.close)}>{busy === 'close' ? 'Закрываем…' : 'Закрыть'}</button>}
        </div>
      </div>}
    </section>
  </main>;
}
