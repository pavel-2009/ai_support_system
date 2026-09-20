import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ChatPanel } from './ChatPanel';
import { statusLabels } from './ConversationList';
import { useOperatorSocket } from '../hooks/useOperatorSocket';

const notificationLabels = {
  conversation_escalated: 'Новый диалог ожидает оператора',
  message_sent: 'В диалоге появилось новое сообщение',
  operator_assigned: 'Диалог назначен оператору',
  conversation_closed: 'Диалог закрыт',
  conversation_returned_to_ai: 'Диалог возвращён AI',
};

const sortConversations = (items) => [...items].sort((a, b) => {
  const priority = { high: 2, medium: 1, low: 0 };
  const priorityDiff = (priority[b.priority] ?? 0) - (priority[a.priority] ?? 0);
  if (priorityDiff) return priorityDiff;
  return new Date(b.updated_at || b.created_at).getTime() - new Date(a.updated_at || a.created_at).getTime();
});

export function OperatorWorkspace({ api, accessToken, user }) {
  const [queue, setQueue] = useState([]);
  const [mine, setMine] = useState([]);
  const [active, setActive] = useState(null);
  const [messages, setMessages] = useState([]);
  const [notice, setNotice] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const activeRef = useRef(null);

  useEffect(() => { activeRef.current = active; }, [active]);

  const refresh = useCallback(async () => {
    try {
      const [nextQueue, ownResponse] = await Promise.all([
        api.queue(),
        api.conversations({ operatorId: user.id }),
      ]);
      setQueue(sortConversations(nextQueue || []));
      setMine(sortConversations(ownResponse.items || []));
    } catch (error) {
      setNotice(error.message);
    } finally {
      setLoading(false);
    }
  }, [api, user.id]);

  useEffect(() => { refresh(); }, [refresh]);

  useEffect(() => {
    if (!active) {
      setMessages([]);
      return undefined;
    }

    let cancelled = false;
    setMessages([]);

    const load = async () => {
      try {
        const next = await api.messages(active.id);
        if (!cancelled) setMessages(next);
      } catch (error) {
        if (!cancelled && error.status !== 410) setNotice(error.message);
      }
    };

    load();
    const interval = window.setInterval(load, 2500);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [active?.id, api]);

  const onSocketEvent = useCallback((event) => {
    if (event.type === 'typing') return;
    if (notificationLabels[event.type]) setNotice(notificationLabels[event.type]);
    refresh();

    const current = activeRef.current;
    if (current && String(event.conversation_id) === String(current.id)) {
      api.messages(current.id).then(setMessages).catch(() => {});
    }
  }, [api, refresh]);

  const connected = useOperatorSocket(accessToken, onSocketEvent);

  const selectActive = useCallback((conversation) => {
    setNotice('');
    setActive(conversation);
  }, []);

  async function action(name, method) {
    if (!active || busy) return;
    setBusy(name);
    setNotice('');

    try {
      const result = await method(active.id);
      if (result?.id) {
        setActive(result);
        setMessages(await api.messages(result.id));
      } else if (result?.status) {
        setActive((current) => current ? { ...current, status: result.status } : current);
      }
      await refresh();

      if (name === 'backToAi' || name === 'close') setActive(null);
      else setNotice(name === 'assign' ? 'Диалог взят в работу.' : '');
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy('');
    }
  }

  async function reply(content) {
    if (!active || busy || active.operator_id !== user.id || active.status !== 'waiting_for_operator') return;

    setBusy('reply');
    setNotice('');
    try {
      const message = await api.operatorReply(active.id, content);
      setMessages((items) => items.some((item) => item.id === message.id) ? items : [...items, message]);
      setActive((current) => current ? { ...current, status: 'waiting_for_user' } : current);
      await refresh();
    } catch (error) {
      setNotice(error.message);
      throw error;
    } finally {
      setBusy('');
    }
  }

  const unassignedQueue = useMemo(
    () => queue.filter((item) => item.status === 'escalated' && !item.operator_id),
    [queue],
  );

  const own = useMemo(
    () => mine.filter((item) => item.operator_id === user.id && item.status !== 'closed'),
    [mine, user.id],
  );

  const canAssign = active?.status === 'escalated' && !active.operator_id;
  const canReply = active?.operator_id === user.id && active?.status === 'waiting_for_operator';
  const canReturn = active?.operator_id === user.id && ['waiting_for_operator', 'waiting_for_user'].includes(active.status);
  const canClose = active?.operator_id === user.id && active.status !== 'closed';

  const ConversationCard = ({ item }) => (
    <button
      type="button"
      key={item.id}
      className={`queue-card ${active?.id === item.id ? 'selected' : ''}`}
      onClick={() => selectActive(item)}
    >
      <span className={`priority ${item.priority}`}>{item.priority === 'high' ? 'Срочно' : 'Обычный'}</span>
      <b>Диалог #{item.id}</b>
      <small><i className={`status-dot ${item.status}`} />{statusLabels[item.status] || item.status}</small>
      {item.operator_id === user.id && <em>Ваш диалог</em>}
    </button>
  );

  return (
    <main className="operator">
      <section className="queue-panel">
        <header>
          <div><p className="eyebrow">LIVE QUEUE</p><h2>Операторская</h2></div>
          <span className={`live ${connected ? 'connected' : ''}`}>
            {connected ? '● онлайн' : '○ переподключение'}
          </span>
        </header>

        {notice && (
          <div className="notice" role="status">
            <span>{notice}</span>
            <button type="button" onClick={() => setNotice('')} aria-label="Закрыть уведомление">×</button>
          </div>
        )}

        <section className="queue-section">
          <div className="queue-section-heading">
            <span>ЭСКАЛИРОВАННЫЕ</span><b>{unassignedQueue.length}</b>
          </div>
          {loading ? <p className="muted">Загружаем очередь…</p> : (
            unassignedQueue.map((item) => <ConversationCard item={item} key={item.id} />)
          )}
          {!loading && !unassignedQueue.length && <p className="muted queue-empty">Нет новых эскалаций.</p>}
        </section>

        <section className="queue-section">
          <div className="queue-section-heading">
            <span>МОИ ДИАЛОГИ</span><b>{own.length}</b>
          </div>
          {own.map((item) => <ConversationCard item={item} key={item.id} />)}
          {!own.length && <p className="muted queue-empty">Назначенных диалогов нет.</p>}
        </section>
      </section>

      <section className="operator-chat">
        {active ? (
          <>
            <div className="operator-actions">
              <div>
                <span>Диалог #{active.id}</span>
                <small>{statusLabels[active.status] || active.status}</small>
              </div>
              <div className="action-group">
                {canAssign && (
                  <button type="button" className="secondary" disabled={Boolean(busy)} onClick={() => action('assign', api.assign)}>
                    {busy === 'assign' ? 'Назначаем…' : 'Взять в работу'}
                  </button>
                )}
                {canReturn && (
                  <button type="button" className="secondary" disabled={Boolean(busy)} onClick={() => action('backToAi', api.backToAi)}>
                    {busy === 'backToAi' ? 'Возвращаем…' : 'Вернуть AI'}
                  </button>
                )}
                {canClose && (
                  <button type="button" className="danger" disabled={Boolean(busy)} onClick={() => action('close', api.close)}>
                    {busy === 'close' ? 'Закрываем…' : 'Закрыть'}
                  </button>
                )}
              </div>
            </div>

            <ChatPanel
              conversation={active}
              messages={messages}
              userId={user.id}
              isLoading={false}
              isSending={busy === 'reply'}
              isAiGenerating={false}
              onSend={reply}
              readOnly={!canReply}
              autoFocusComposer={canReply && !busy}
            />
          </>
        ) : (
          <div className="empty-state">
            <div>◉</div>
            <h2>Рабочее место</h2>
            <p>Слева — только новые эскалации и ваши диалоги.</p>
          </div>
        )}
      </section>
    </main>
  );
}
