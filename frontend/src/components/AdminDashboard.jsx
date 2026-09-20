import { useEffect, useMemo, useState } from 'react';
import { ChatPanel } from './ChatPanel';
import { statusLabels } from './ConversationList';

export function AdminDashboard({ api, conversations, user, onConversationsChange }) {
  const [users, setUsers] = useState([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState('');
  const [selectedId, setSelectedId] = useState(null);
  const [messages, setMessages] = useState([]);

  useEffect(() => {
    api.users().then(setUsers).catch((requestError) => setError(requestError.message));
    const interval = window.setInterval(() => {
      onConversationsChange().catch(() => {});
    }, 10000);
    return () => window.clearInterval(interval);
  }, [api, onConversationsChange]);

  const selected = useMemo(() => conversations.find((item) => item.id === selectedId), [conversations, selectedId]);

  useEffect(() => {
    if (!selected) {
      setMessages([]);
      return undefined;
    }
    let cancelled = false;
    api.messages(selected.id)
      .then((next) => { if (!cancelled) setMessages(next); })
      .catch((requestError) => { if (!cancelled && requestError.status !== 410) setError(requestError.message); });
    return () => { cancelled = true; };
  }, [api, selected?.id]);

  const open = conversations.filter((item) => item.status !== 'closed');
  const escalated = conversations.filter((item) => item.status === 'escalated');
  const waitingForOperator = conversations.filter((item) => ['escalated', 'waiting_for_operator'].includes(item.status));
  const confidenceValues = conversations
    .map((item) => item.ai_confidence)
    .filter((value) => typeof value === 'number');
  const avgConfidence = confidenceValues.length
    ? Math.round(confidenceValues.reduce((sum, value) => sum + value, 0) / confidenceValues.length * 100)
    : 0;
  const averageWait = waitingForOperator.length
    ? Math.round(waitingForOperator.reduce((sum, item) => sum + Math.max(0, Date.now() - new Date(item.updated_at).getTime()), 0) / waitingForOperator.length / 60000)
    : 0;
  const metrics = [
    ['Активные обращения', open.length, 'не закрыты'],
    ['Эскалации', escalated.length, 'без назначения оператора'],
    ['Среднее ожидание', `${averageWait} мин`, 'только очередь оператора'],
    ['Средняя уверенность AI', `${avgConfidence}%`, confidenceValues.length ? `по ${confidenceValues.length} диалогам` : 'нет данных'],
  ];

  async function runAction(name, method) {
    if (!selected || busy) return;
    setBusy(name);
    setError('');
    try {
      const result = await method(selected.id);
      if (result?.id) {
        setSelectedId(result.id);
        setMessages(await api.messages(result.id));
      }
      await onConversationsChange();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy('');
    }
  }

  async function reply(content) {
    if (!selected || busy || selected.status === 'closed') return;
    setBusy('reply');
    setError('');
    try {
      const message = await api.operatorReply(selected.id, content);
      setMessages((items) => items.some((item) => item.id === message.id) ? items : [...items, message]);
      await onConversationsChange();
    } catch (requestError) {
      setError(requestError.message);
      throw requestError;
    } finally {
      setBusy('');
    }
  }

  const canReply = selected?.operator_id === user.id && selected.status === 'waiting_for_operator';
  const canReturn = selected?.operator_id === user.id && ['waiting_for_operator', 'waiting_for_user'].includes(selected.status);

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
      <article className="panel"><h3>Контроль AI</h3><div className="quality"><strong>{avgConfidence}%</strong><span>средняя уверенность AI</span></div><p className="muted">Учитываются только диалоги, где AI действительно вернул значение confidence.</p></article>
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
          {canReturn && <button className="secondary" disabled={!!busy} onClick={() => runAction('back', api.backToAi)}>{busy === 'back' ? 'Возвращаем…' : 'Вернуть AI'}</button>}
          {selected.status !== 'closed' && <button className="danger" disabled={!!busy} onClick={() => runAction('close', api.close)}>{busy === 'close' ? 'Закрываем…' : 'Закрыть'}</button>}
        </div>
      </div>}
      {selected && <div className="admin-chat">
        <ChatPanel
          conversation={selected}
          messages={messages}
          userId={user.id}
          isLoading={false}
          isSending={busy === 'reply'}
          isAiGenerating={false}
          onSend={reply}
          readOnly={!canReply}
          autoFocusComposer={canReply && !busy}
        />
      </div>}
    </section>
  </main>;
}
