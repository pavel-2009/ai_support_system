import { useEffect, useMemo, useState } from 'react';
import { ChatPanel } from './ChatPanel';
import { statusLabels } from './ConversationList';

const sortByUpdated = (items) => [...items].sort(
  (a, b) => new Date(b.updated_at || b.created_at).getTime() - new Date(a.updated_at || a.created_at).getTime(),
);

export function AdminDashboard({ api, conversations, user, onConversationsChange }) {
  const [users, setUsers] = useState([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState('');
  const [selectedId, setSelectedId] = useState(null);
  const [messages, setMessages] = useState([]);

  useEffect(() => {
    let cancelled = false;
    api.users()
      .then((next) => { if (!cancelled) setUsers(next || []); })
      .catch((requestError) => { if (!cancelled) setError(requestError.message); });

    const interval = window.setInterval(() => {
      onConversationsChange().catch(() => {});
    }, 5000);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [api, onConversationsChange]);

  const escalated = useMemo(
    () => sortByUpdated(conversations.filter((item) => item.status === 'escalated' && !item.operator_id)),
    [conversations],
  );

  const own = useMemo(
    () => sortByUpdated(conversations.filter((item) => item.operator_id === user.id && item.status !== 'closed')),
    [conversations, user.id],
  );

  const visible = useMemo(() => {
    const map = new Map();
    [...escalated, ...own].forEach((item) => map.set(item.id, item));
    return [...map.values()];
  }, [escalated, own]);

  const selected = useMemo(
    () => visible.find((item) => item.id === selectedId) || null,
    [visible, selectedId],
  );

  useEffect(() => {
    if (!selected) {
      setMessages([]);
      return undefined;
    }

    let cancelled = false;
    setMessages([]);

    const load = async () => {
      try {
        const next = await api.messages(selected.id);
        if (!cancelled) setMessages(next);
      } catch (requestError) {
        if (!cancelled && requestError.status !== 410) setError(requestError.message);
      }
    };

    load();
    const interval = window.setInterval(load, 2500);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [api, selected?.id]);

  const open = conversations.filter((item) => item.status !== 'closed');
  const confidenceValues = conversations
    .map((item) => item.ai_confidence)
    .filter((value) => typeof value === 'number' && Number.isFinite(value));

  const avgConfidence = confidenceValues.length
    ? Math.round((confidenceValues.reduce((sum, value) => sum + value, 0) / confidenceValues.length) * 100)
    : 0;

  const averageWait = escalated.length
    ? Math.round(
        escalated.reduce(
          (sum, item) => sum + Math.max(0, Date.now() - new Date(item.updated_at || item.created_at).getTime()),
          0,
        ) / escalated.length / 60000,
      )
    : 0;

  const metrics = [
    ['Активные обращения', open.length, 'всего в системе'],
    ['Новые эскалации', escalated.length, 'ждут оператора'],
    ['Среднее ожидание', `${averageWait} мин`, 'по новой очереди'],
    ['Уверенность AI', `${avgConfidence}%`, confidenceValues.length ? `по ${confidenceValues.length} диалогам` : 'нет данных'],
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
      if (name === 'back' || name === 'close') setSelectedId(null);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy('');
    }
  }

  async function reply(content) {
    if (!selected || busy || selected.operator_id !== user.id || selected.status !== 'waiting_for_operator') return;

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
  const canClose = selected?.operator_id === user.id && selected.status !== 'closed';

  return (
    <main className="dashboard">
      <header>
        <p className="eyebrow">ADMIN DASHBOARD</p>
        <h1>Пульс поддержки</h1>
        <p className="muted">Аналитика отдельно, рабочие диалоги — только эскалации и обращения, назначенные вам.</p>
      </header>

      {error && (
        <div className="dashboard-error" role="alert">
          <span>{error}</span>
          <button type="button" onClick={() => setError('')} aria-label="Закрыть ошибку">×</button>
        </div>
      )}

      <section className="metric-grid">
        {metrics.map(([label, value, hint]) => (
          <article className="metric" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
            <small>{hint}</small>
          </article>
        ))}
      </section>

      <section className="dashboard-grid">
        <article className="panel status-panel">
          <h3>Распределение состояний</h3>
          {Object.entries(statusLabels).map(([status, label]) => {
            const count = conversations.filter((item) => item.status === status).length;
            const width = conversations.length ? (count / conversations.length) * 100 : 0;
            return (
              <div className="bar-row" key={status}>
                <span><i className={`status-dot ${status}`} />{label}</span>
                <div><i style={{ width: `${width}%` }} /></div>
                <b>{count}</b>
              </div>
            );
          })}
        </article>

        <article className="panel">
          <h3>Контроль AI</h3>
          <div className="quality"><strong>{avgConfidence}%</strong><span>средняя уверенность</span></div>
          <p className="muted">Расчёт использует только числовые значения confidence, полученные от AI.</p>
          <p className="muted">Пользователи в системе: {users.length}</p>
        </article>
      </section>

      <section className="panel conversation-panel">
        <div className="panel-heading">
          <div>
            <h3>Рабочие диалоги</h3>
            <p className="muted">Новые эскалации и только ваши назначенные обращения.</p>
          </div>
          <span className="count-badge">{visible.length}</span>
        </div>

        <div className="staff-dialog-grid">
          <div>
            <div className="list-heading"><span>ЭСКАЛАЦИИ</span><b>{escalated.length}</b></div>
            <div className="admin-conversations">
              {escalated.map((conversation) => (
                <button
                  type="button"
                  key={conversation.id}
                  className={`admin-conversation ${selectedId === conversation.id ? 'selected' : ''}`}
                  onClick={() => setSelectedId(conversation.id)}
                >
                  <span><b>#{conversation.id}</b><small>Пользователь #{conversation.user_id}</small></span>
                  <span className={`pill ${conversation.status}`}>{statusLabels[conversation.status]}</span>
                </button>
              ))}
              {!escalated.length && <p className="muted list-empty">Новых эскалаций нет.</p>}
            </div>
          </div>

          <div>
            <div className="list-heading"><span>МОИ ДИАЛОГИ</span><b>{own.length}</b></div>
            <div className="admin-conversations">
              {own.map((conversation) => (
                <button
                  type="button"
                  key={conversation.id}
                  className={`admin-conversation ${selectedId === conversation.id ? 'selected' : ''}`}
                  onClick={() => setSelectedId(conversation.id)}
                >
                  <span><b>#{conversation.id}</b><small>{statusLabels[conversation.status]}</small></span>
                  <span className={`pill ${conversation.status}`}>{statusLabels[conversation.status]}</span>
                </button>
              ))}
              {!own.length && <p className="muted list-empty">Назначенных диалогов нет.</p>}
            </div>
          </div>
        </div>

        {selected && (
          <>
            <div className="admin-actions">
              <div>
                <b>Диалог #{selected.id}</b>
                <span className={`pill ${selected.status}`}>{statusLabels[selected.status]}</span>
              </div>
              <div className="action-group">
                {selected.status === 'escalated' && !selected.operator_id && (
                  <button type="button" className="secondary" disabled={Boolean(busy)} onClick={() => runAction('assign', api.assign)}>
                    {busy === 'assign' ? 'Назначаем…' : 'Взять в работу'}
                  </button>
                )}
                {canReturn && (
                  <button type="button" className="secondary" disabled={Boolean(busy)} onClick={() => runAction('back', api.backToAi)}>
                    {busy === 'back' ? 'Возвращаем…' : 'Вернуть AI'}
                  </button>
                )}
                {canClose && (
                  <button type="button" className="danger" disabled={Boolean(busy)} onClick={() => runAction('close', api.close)}>
                    {busy === 'close' ? 'Закрываем…' : 'Закрыть'}
                  </button>
                )}
              </div>
            </div>

            <div className="admin-chat">
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
            </div>
          </>
        )}
      </section>
    </main>
  );
}
