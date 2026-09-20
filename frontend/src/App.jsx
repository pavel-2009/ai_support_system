import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { LoginForm } from './components/LoginForm';
import { ConversationList } from './components/ConversationList';
import { ChatPanel } from './components/ChatPanel';
import { OperatorWorkspace } from './components/OperatorWorkspace';
import { AdminDashboard } from './components/AdminDashboard';
import { useAuth } from './hooks/useAuth';

function Profile({ user, mode, onModeChange, onLogout }) {
  return <div className="sidebar-bottom">
    {user.role === 'admin' && <button className={`nav-action ${mode === 'admin' ? 'active' : ''}`} onClick={() => onModeChange('admin')}>▦ Аналитика</button>}
    {user.role !== 'user' && <button className={`nav-action ${mode === 'operator' ? 'active' : ''}`} onClick={() => onModeChange('operator')}>◉ Рабочее место</button>}
    <div className="profile"><div className="avatar">{user.nickname[0].toUpperCase()}</div><span><b>{user.nickname}</b><small>{user.role === 'admin' ? 'Администратор' : user.role === 'operator' ? 'Оператор' : 'Клиент'}</small></span><button onClick={onLogout} title="Выйти">↗</button></div>
  </div>;
}

function SupportApp({ api, accessToken, logout }) {
  const [user, setUser] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [mode, setMode] = useState('chat');
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState('');
  const selected = useMemo(() => conversations.find((item) => item.id === selectedId), [conversations, selectedId]);
  const pollRef = useRef(null);

  const loadConversations = useCallback(async (keepSelection = true) => {
    const response = await api.conversations();
    setConversations(response.items);
    setSelectedId((current) => keepSelection && response.items.some((item) => item.id === current)
      ? current
      : response.items[0]?.id || null);
  }, [api]);

  useEffect(() => {
    Promise.all([api.currentUser(), loadConversations(false)])
      .then(([currentUser]) => setUser(currentUser))
      .catch((requestError) => setError(requestError.message))
      .finally(() => setIsLoading(false));
  }, [api, loadConversations]);

  useEffect(() => {
    if (!selectedId || mode !== 'chat') return undefined;
    let cancelled = false;
    const refresh = async () => {
      try {
        const next = await api.messages(selectedId);
        if (!cancelled) setMessages(next);
      } catch (requestError) {
        if (!cancelled && requestError.status !== 410) setError(requestError.message);
      }
    };
    setMessages([]);
    refresh();
    const interval = window.setInterval(refresh, 3000);
    return () => { cancelled = true; window.clearInterval(interval); };
  }, [api, selectedId, mode]);

  useEffect(() => {
    if (mode !== 'chat') return undefined;
    const interval = window.setInterval(() => loadConversations(true).catch(() => {}), 5000);
    return () => window.clearInterval(interval);
  }, [loadConversations, mode]);

  async function createConversation() {
    setIsCreating(true);
    setError('');
    try {
      const conversation = await api.createConversation();
      setConversations((items) => [conversation, ...items]);
      setSelectedId(conversation.id);
      setMode('chat');
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsCreating(false);
    }
  }

  async function sendMessage(content) {
    if (!selected || isSending || selected.status === 'closed') return;
    setIsSending(true);
    setError('');
    try {
      const message = await api.sendMessage(selected.id, content);
      setMessages((items) => items.some((item) => item.id === message.id) ? items : [...items, message]);
      await loadConversations(true);
      const startedAt = Date.now();
      pollRef.current = window.setInterval(async () => {
        try {
          const [nextMessages] = await Promise.all([api.messages(selected.id), loadConversations(true)]);
          setMessages(nextMessages);
          const hasNewAiReply = nextMessages.some((item) => item.sender_type === 'ai' && !messages.some((old) => old.id === item.id));
          if (hasNewAiReply || Date.now() - startedAt >= 30000) {
            window.clearInterval(pollRef.current);
            pollRef.current = null;
            setIsSending(false);
          }
        } catch {
          window.clearInterval(pollRef.current);
          pollRef.current = null;
          setIsSending(false);
        }
      }, 1500);
    } catch (requestError) {
      setError(requestError.message);
      setIsSending(false);
    }
  }

  useEffect(() => () => {
    if (pollRef.current) window.clearInterval(pollRef.current);
  }, []);

  if (isLoading) return <main className="loading-screen"><div className="loading-card"><span className="loading-mark">✦</span><p>Загружаем рабочее пространство…</p></div></main>;
  if (!user) return <main className="loading-screen">{error || 'Не удалось загрузить профиль.'}</main>;

  return <div className="app-shell">
    <div className="sidebar-wrap">
      <ConversationList conversations={conversations} selectedId={selectedId} onSelect={(id) => { setSelectedId(id); setMode('chat'); }} onCreate={createConversation} isCreating={isCreating} />
      <Profile user={user} mode={mode} onModeChange={setMode} onLogout={logout} />
    </div>
    <section className="workspace">
      {error && <button className="workspace-error" role="alert" onClick={() => setError('')}>{error}<span>×</span></button>}
      {mode === 'admin' && user.role === 'admin'
        ? <AdminDashboard api={api} conversations={conversations} onConversationsChange={loadConversations} />
        : mode === 'operator' && user.role !== 'user'
          ? <OperatorWorkspace api={api} accessToken={accessToken} user={user} />
          : <ChatPanel conversation={selected} messages={messages} userId={user.id} isLoading={false} isSending={isSending} onSend={sendMessage} />}
    </section>
  </div>;
}

export default function App() {
  const { api, accessToken, login, logout } = useAuth();
  return accessToken ? <SupportApp api={api} accessToken={accessToken} logout={logout} /> : <LoginForm onSubmit={login} />;
}
