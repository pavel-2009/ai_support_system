import { useCallback, useEffect, useState } from 'react';
import { ChatPanel } from './ChatPanel';
import { statusLabels } from './ConversationList';
import { useOperatorSocket } from '../hooks/useOperatorSocket';

export function OperatorWorkspace({ api, accessToken, user }) {
  const [queue, setQueue] = useState([]); const [active, setActive] = useState(null); const [messages, setMessages] = useState([]); const [notice, setNotice] = useState(''); const [loading, setLoading] = useState(true);
  const refreshQueue = useCallback(async () => { try { setQueue(await api.queue()); } catch (error) { setNotice(error.message); } finally { setLoading(false); } }, [api]);
  useEffect(() => { refreshQueue(); }, [refreshQueue]);
  useEffect(() => { if (!active) return; api.messages(active.id).then(setMessages).catch((error) => setNotice(error.message)); }, [active, api]);
  const connected = useOperatorSocket(accessToken, useCallback(() => { setNotice('Очередь обновилась'); refreshQueue(); }, [refreshQueue]));
  async function action(method) { if (!active) return; try { await method(active.id); await refreshQueue(); setNotice('Изменения сохранены'); } catch (error) { setNotice(error.message); } }
  async function reply(content) { const message = await api.operatorReply(active.id, content); setMessages((items) => [...items, message]); }
  return <main className="operator"><section className="queue-panel"><header><div><p className="eyebrow">LIVE QUEUE</p><h2>Открытые диалоги</h2></div><span className={`live ${connected ? 'connected' : ''}`}>{connected ? '● онлайн' : '○ подключение'}</span></header>{notice && <p className="notice">{notice}</p>}<div className="queue-list">{loading ? <p className="muted">Загружаем очередь…</p> : queue.map((item) => <button key={item.id} className={`queue-card ${active?.id === item.id ? 'selected' : ''}`} onClick={() => setActive(item)}><span className={`priority ${item.priority}`}>{item.priority === 'high' ? 'Срочно' : 'Обычный'}</span><b>Диалог #{item.id}</b><small>{statusLabels[item.status]} · #{item.user_id}</small></button>)}{!loading && !queue.length && <p className="muted">Очередь пуста — хорошая работа.</p>}</div></section><section className="operator-chat">{active ? <><div className="operator-actions"><span>Диалог #{active.id}</span>{!active.operator_id && <button className="secondary" onClick={() => action(api.assign)}>Взять в работу</button>}<button className="secondary" onClick={() => action(api.backToAi)}>Вернуть AI</button><button className="danger" onClick={() => action(api.close)}>Закрыть</button></div><ChatPanel conversation={active} messages={messages} userId={user.id} isLoading={false} isSending={false} onSend={reply} /></> : <div className="empty-state"><div>◉</div><h2>Очередь оператора</h2><p>Выберите обращение, чтобы начать работу.</p></div>}</section></main>;
}
