import { useCallback, useEffect, useMemo, useState } from 'react';
import { LoginForm } from './components/LoginForm';
import { ConversationList } from './components/ConversationList';
import { ChatPanel } from './components/ChatPanel';
import { OperatorWorkspace } from './components/OperatorWorkspace';
import { AdminDashboard } from './components/AdminDashboard';
import { useAuth } from './hooks/useAuth';

function Profile({ user, mode, onModeChange, onLogout }) {
  return <div className="sidebar-bottom">{user.role === 'admin' && <button className={`nav-action ${mode === 'admin' ? 'active' : ''}`} onClick={() => onModeChange('admin')}>▦ Аналитика</button>}{user.role !== 'user' && <button className={`nav-action ${mode === 'operator' ? 'active' : ''}`} onClick={() => onModeChange('operator')}>◉ Рабочее место</button>}<div className="profile"><div className="avatar">{user.nickname[0].toUpperCase()}</div><span><b>{user.nickname}</b><small>{user.role === 'admin' ? 'Администратор' : user.role === 'operator' ? 'Оператор' : 'Клиент'}</small></span><button onClick={onLogout} title="Выйти">↗</button></div></div>;
}

function SupportApp({ api, accessToken, logout }) {
  const [user, setUser] = useState(null); const [conversations, setConversations] = useState([]); const [selectedId, setSelectedId] = useState(null); const [messages, setMessages] = useState([]); const [mode, setMode] = useState('chat'); const [isLoading, setIsLoading] = useState(true); const [isSending, setIsSending] = useState(false); const [isCreating, setIsCreating] = useState(false); const [error, setError] = useState('');
  const selected = useMemo(() => conversations.find((item) => item.id === selectedId), [conversations, selectedId]);
  const loadConversations = useCallback(async () => { const response = await api.conversations(); setConversations(response.items); setSelectedId((current) => current || response.items[0]?.id || null); }, [api]);
  useEffect(() => { Promise.all([api.currentUser(), loadConversations()]).then(([currentUser]) => setUser(currentUser)).catch((requestError) => setError(requestError.message)).finally(() => setIsLoading(false)); }, [api, loadConversations]);
  useEffect(() => { if (!selectedId || mode !== 'chat') return; api.messages(selectedId).then(setMessages).catch((requestError) => setError(requestError.message)); }, [api, selectedId, mode]);
  async function createConversation() { setIsCreating(true); try { const conversation = await api.createConversation(); setConversations((items) => [conversation, ...items]); setSelectedId(conversation.id); setMode('chat'); } catch (requestError) { setError(requestError.message); } finally { setIsCreating(false); } }
  async function sendMessage(content) { if (!selected) return; setIsSending(true); try { const message = await api.sendMessage(selected.id, content); setMessages((items) => [...items, message]); const existingIds = new Set(messages.map((item) => item.id)); const interval = window.setInterval(async () => { try { const next = await api.messages(selected.id); const hasNewAiReply = next.some((item) => item.sender_type === 'ai' && !existingIds.has(item.id)); setMessages(next); if (hasNewAiReply) { window.clearInterval(interval); setIsSending(false); loadConversations(); } } catch { window.clearInterval(interval); setIsSending(false); } }, 1800); window.setTimeout(() => { window.clearInterval(interval); setIsSending(false); }, 30000); } catch (requestError) { setError(requestError.message); setIsSending(false); } }
  if (isLoading) return <main className="loading-screen">Загружаем рабочее пространство…</main>;
  if (!user) return <main className="loading-screen">{error || 'Не удалось загрузить профиль.'}</main>;
  return <div className="app-shell"><div className="sidebar-wrap"><ConversationList conversations={conversations} selectedId={selectedId} onSelect={(id) => { setSelectedId(id); setMode('chat'); }} onCreate={createConversation} isCreating={isCreating} /><Profile user={user} mode={mode} onModeChange={setMode} onLogout={logout} /></div><section className="workspace">{error && <p className="workspace-error" role="alert">{error}</p>}{mode === 'admin' && user.role === 'admin' ? <AdminDashboard api={api} conversations={conversations} /> : mode === 'operator' && user.role !== 'user' ? <OperatorWorkspace api={api} accessToken={accessToken} user={user} /> : <ChatPanel conversation={selected} messages={messages} userId={user.id} isLoading={false} isSending={isSending} onSend={sendMessage} />}</section></div>;
}

export default function App() { const { api, accessToken, login, logout } = useAuth(); return accessToken ? <SupportApp api={api} accessToken={accessToken} logout={logout} /> : <LoginForm onSubmit={login} />; }
