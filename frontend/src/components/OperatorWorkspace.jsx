import { useCallback, useEffect, useState } from 'react';
import { ChatPanel } from './ChatPanel';
import { statusLabels } from './ConversationList';
import { useOperatorSocket } from '../hooks/useOperatorSocket';

const actionLabels = {
  assign: 'Взять в работу',
  backToAi: 'Вернуть AI',
  close: 'Закрыть диалог',
};

export function OperatorWorkspace({ api, accessToken, user }) {
  const [queue, setQueue] = useState([]);
  const [active, setActive] = useState(null);
  const [messages, setMessages] = useState([]);
  const [notice, setNotice] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');

  const refreshQueue = useCallback(async () => {
    try { setQueue(await api.queue()); }
    catch (error) { setNotice(error.message); }
    finally { setLoading(false); }
  }, [api]);

  useEffect(() => { refreshQueue(); }, [refreshQueue]);
  useEffect(() => {
    if (!active) return undefined;
    let cancelled = false;
    const refresh = async () => {
      try { const next = await api.messages(active.id); if (!cancelled) setMessages(next); }
      catch (error) { if (!cancelled) setNotice(error.message); }
    };
    setMessages([]);
    refresh();
    const interval = window.setInterval(refresh, 3000);
    return () => { cancelled = true; window.clearInterval(interval); };
  }, [active?.id, api]);

  const connected = useOperatorSocket(accessToken, useCallback((event) => {
    if (event.type === 'typing') return;
    refreshQueue();
    if (active && String(event.conversation_id) === String(active.id)) {
      api.messages(active.id).then(setMessages).catch(() => {});
    }
  }, [active, api, refreshQueue]));

  async function action(name, method) {
    if (!active || busy) return;
    setBusy(name);
    setNotice('');
    try {
      const result = await method(active.id);
      if (result?.id) {
        setActive(result);
        if (name === 'assign') {
          setMessages(await api.messages(result.id));
        }
      } else if (result?.status) {
        setActive((current) => current ? { ...current, status: result.status } : current);
      }
      if (name === 'close') setActive((current) => current ? { ...current, status: 'closed' } : current);
      await refreshQueue();
      setNotice(name === 'assign' ? 'Диалог взят в работу' : name === 'backToAi' ? 'Диалог возвращён AI' : 'Диалог закрыт');
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy('');
    }
  }

  async function reply(content) {
    if (!active || busy || active.status === 'closed') return;
    setBusy('reply');
    setNotice('');
    try {
      const message = await api.operatorReply(active.id, content);
      setMessages((items) => items.some((item) => item.id === message.id) ? items : [...items, message]);
      setActive((current) => current ? { ...current, status: 'waiting_for_user' } : current);
      await refreshQueue();
    } catch (error) {
      setNotice(error.message);
      throw error;
    } finally {
      setBusy('');
    }
  }

  const canAssign = active && !active.operator_id && active.status === 'escalated';
  const canReply = active && active.operator_id === user.id && active.status === 'waiting_for_operator';
  const canReturn = active && active.operator_id === user.id && ['waiting_for_operator', 'waiting_for_user'].includes(active.status);
  const canClose = active && active.status !== 'closed';

  return <main className="operator">
    <section className="queue-panel">
      <header><div><p className="eyebrow">LIVE QUEUE</p><h2>Обращения</h2></div><span className={`live ${connected ? 'connected' : ''}`}>{connected ? '● онлайн' : '○ переподключение'}</span></header>
      {notice && <div className="notice" role="status"><span>{notice}</span><button onClick={() => setNotice('')}>×</button></div>}
      <div className="queue-list">
        {loading ? <p className="muted">Загружаем очередь…</p> : queue.map((item) => <button key={item.id} className={`queue-card ${active?.id === item.id ? 'selected' : ''}`} onClick={() => setActive(item)}>
          <span className={`priority ${item.priority}`}>{item.priority === 'high' ? 'Срочно' : 'Обычный'}</span>
          <b>Диалог #{item.id}</b>
          <small><i className={`status-dot ${item.status}`} />{statusLabels[item.status] || item.status}</small>
          {item.operator_id === user.id && <em>Ваш диалог</em>}
        </button>)}
        {!loading && !queue.length && <p className="muted">Очередь пуста — новых обращений нет.</p>}
      </div>
    </section>
    <section className="operator-chat">
      {active ? <>
        <div className="operator-actions">
          <div><span>Диалог #{active.id}</span><small>{statusLabels[active.status] || active.status}</small></div>
          <div className="action-group">
            {canAssign && <button className="secondary" disabled={!!busy} onClick={() => action('assign', api.assign)}>{busy === 'assign' ? 'Назначаем…' : actionLabels.assign}</button>}
            {canReturn && <button className="secondary" disabled={!!busy} onClick={() => action('backToAi', api.backToAi)}>{busy === 'backToAi' ? 'Возвращаем…' : actionLabels.backToAi}</button>}
            {canClose && <button className="danger" disabled={!!busy} onClick={() => action('close', api.close)}>{busy === 'close' ? 'Закрываем…' : actionLabels.close}</button>}
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
      </> : <div className="empty-state"><div>◉</div><h2>Рабочее место</h2><p>Выберите обращение из очереди.</p></div>}
    </section>
  </main>;
}
