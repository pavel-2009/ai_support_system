import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { LoginForm } from './components/LoginForm';
import { ConversationList } from './components/ConversationList';
import { ChatPanel } from './components/ChatPanel';
import { OperatorWorkspace } from './components/OperatorWorkspace';
import { AdminDashboard } from './components/AdminDashboard';
import { useAuth } from './hooks/useAuth';

function Profile({ user, mode, onModeChange, onLogout }) {
  return (
    <div className="sidebar-bottom">
      {user.role === 'admin' && (
        <button
          type="button"
          className={`nav-action ${mode === 'admin' ? 'active' : ''}`}
          onClick={() => onModeChange('admin')}
        >
          ▦ Аналитика
        </button>
      )}
      {user.role !== 'user' && (
        <button
          type="button"
          className={`nav-action ${mode === 'operator' ? 'active' : ''}`}
          onClick={() => onModeChange('operator')}
        >
          ◉ Рабочее место
        </button>
      )}
      <div className="profile">
        <div className="avatar">{(user.nickname || user.email || '?')[0].toUpperCase()}</div>
        <span>
          <b>{user.nickname}</b>
          <small>{user.role === 'admin' ? 'Администратор' : user.role === 'operator' ? 'Оператор' : 'Клиент'}</small>
        </span>
        <button type="button" onClick={onLogout} title="Выйти" aria-label="Выйти">↗</button>
      </div>
    </div>
  );
}

function SupportApp({ api, accessToken, logout }) {
  const [user, setUser] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [mode, setMode] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [isAiGenerating, setIsAiGenerating] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState('');
  const pollRef = useRef(null);

  const selected = useMemo(
    () => conversations.find((item) => item.id === selectedId),
    [conversations, selectedId],
  );

  const stopMessagePolling = useCallback(() => {
    if (pollRef.current) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
    }
    setIsSending(false);
    setIsAiGenerating(false);
  }, []);

  const loadConversations = useCallback(async (keepSelection = true) => {
    const response = await api.conversations();
    const items = response.items || [];
    setConversations(items);
    setSelectedId((current) =>
      keepSelection && items.some((item) => item.id === current)
        ? current
        : items[0]?.id ?? null,
    );
    return items;
  }, [api]);

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.currentUser(), api.conversations()])
      .then(([currentUser, response]) => {
        if (cancelled) return;
        const items = response.items || [];
        setUser(currentUser);
        setMode(currentUser.role === 'user' ? 'chat' : currentUser.role === 'admin' ? 'admin' : 'operator');
        setConversations(items);
        setSelectedId(items[0]?.id ?? null);
      })
      .catch((requestError) => {
        if (!cancelled) setError(requestError.message);
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => { cancelled = true; };
  }, [api]);

  useEffect(() => {
    if (!selectedId || mode !== 'chat') {
      setMessages([]);
      return undefined;
    }

    let cancelled = false;
    setMessages([]);

    const refresh = async () => {
      try {
        const next = await api.messages(selectedId);
        if (!cancelled) setMessages(next);
      } catch (requestError) {
        if (!cancelled && requestError.status !== 410) setError(requestError.message);
      }
    };

    refresh();
    const interval = window.setInterval(refresh, 2500);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [api, selectedId, mode]);

  useEffect(() => {
    if (mode !== 'chat') return undefined;
    const interval = window.setInterval(() => {
      loadConversations(true).catch(() => {});
    }, 5000);
    return () => window.clearInterval(interval);
  }, [loadConversations, mode]);

  const selectConversation = useCallback((id) => {
    stopMessagePolling();
    setError('');
    setSelectedId(id);
    setMode('chat');
  }, [stopMessagePolling]);

  const changeMode = useCallback((nextMode) => {
    stopMessagePolling();
    setError('');
    setMode(nextMode);
  }, [stopMessagePolling]);

  async function createConversation() {
    if (isCreating) return;
    setIsCreating(true);
    setError('');
    try {
      const conversation = await api.createConversation();
      setConversations((items) => [conversation, ...items.filter((item) => item.id !== conversation.id)]);
      setSelectedId(conversation.id);
      setMode('chat');
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsCreating(false);
    }
  }

  async function sendMessage(content) {
    if (!selected || isSending || isAiGenerating || !['open', 'waiting_for_user'].includes(selected.status)) return;

    setIsSending(true);
    setIsAiGenerating(false);
    setError('');

    try {
      const message = await api.sendMessage(selected.id, content);
      setMessages((items) => items.some((item) => item.id === message.id) ? items : [...items, message]);

      let latestMessages = [message];
      const startedAt = Date.now();

      const poll = async () => {
        try {
          const [nextMessages, nextConversations] = await Promise.all([
            api.messages(selected.id),
            loadConversations(true),
          ]);

          const previousMessages = latestMessages;
          latestMessages = nextMessages;
          setMessages(nextMessages);

          const currentConversation = nextConversations.find((item) => item.id === selected.id);
          const status = currentConversation?.status;
          const escalated = status === 'escalated' || status === 'waiting_for_operator';
          const aiWorking = status === 'pending_ai';
          const hasNewAiReply = nextMessages.some(
            (item) => item.sender_type === 'ai' && !previousMessages.some((old) => old.id === item.id),
          );

          setIsAiGenerating(aiWorking);

          if (escalated || status === 'waiting_for_user' || status === 'closed' || hasNewAiReply || Date.now() - startedAt >= 30000) {
            stopMessagePolling();
          }
        } catch (requestError) {
          setError(requestError.message);
          stopMessagePolling();
        }
      };

      pollRef.current = window.setInterval(poll, 600);
      await poll();
    } catch (requestError) {
      setError(requestError.message);
      stopMessagePolling();
    }
  }

  useEffect(() => () => stopMessagePolling(), [stopMessagePolling]);

  if (isLoading) {
    return <main className="loading-screen"><div className="loading-card"><span className="loading-mark">✦</span><p>Загружаем рабочее пространство…</p></div></main>;
  }

  if (!user) {
    return <main className="loading-screen">{error || 'Не удалось загрузить профиль.'}</main>;
  }

  const isUser = user.role === 'user';

  return (
    <div className={`app-shell ${isUser ? '' : 'staff-shell'}`}>
      <div className="sidebar-wrap">
        {isUser ? (
          <ConversationList
            conversations={conversations}
            selectedId={selectedId}
            onSelect={selectConversation}
            onCreate={createConversation}
            isCreating={isCreating}
          />
        ) : (
          <ConversationList
            conversations={[]}
            showCreate={false}
            title={user.role === 'admin' ? 'РАБОЧЕЕ МЕСТО' : 'ОПЕРАТОР'}
          />
        )}
        <Profile user={user} mode={mode} onModeChange={changeMode} onLogout={logout} />
      </div>

      <section className="workspace">
        {error && (
          <div className="workspace-error" role="alert">
            <span>{error}</span>
            <button type="button" onClick={() => setError('')} aria-label="Закрыть ошибку">×</button>
          </div>
        )}

        {mode === 'admin' && user.role === 'admin'
          ? <AdminDashboard api={api} conversations={conversations} user={user} onConversationsChange={loadConversations} />
          : mode === 'operator' && user.role !== 'user'
            ? <OperatorWorkspace api={api} accessToken={accessToken} user={user} />
            : <ChatPanel
                conversation={selected}
                messages={messages}
                userId={user.id}
                isLoading={false}
                isSending={isSending}
                isAiGenerating={isAiGenerating}
                onSend={sendMessage}
              />}
      </section>
    </div>
  );
}

export default function App() {
  const { api, accessToken, login, logout } = useAuth();
  return accessToken
    ? <SupportApp api={api} accessToken={accessToken} logout={logout} />
    : <LoginForm onSubmit={login} />;
}
