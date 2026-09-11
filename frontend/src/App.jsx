import React, { useState, useEffect, useRef, useCallback } from 'react';
import { api, getStoredToken, clearStoredTokens } from './services/api';
import AuthModal from './components/AuthModal';
import ChatSidebar from './components/ChatSidebar';
import ChatArea from './components/ChatArea';
import { Sparkles, MessageSquare, AlertCircle } from 'lucide-react';

export default function App() {
  const [currentUser, setCurrentUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isSending, setIsSending] = useState(false);
  const [isWaitingAi, setIsWaitingAi] = useState(false);
  const [backendOnline, setBackendOnline] = useState(true);
  const [sidebarLoading, setSidebarLoading] = useState(false);

  // Check initial user authentication
  useEffect(() => {
    const token = getStoredToken();
    if (token) {
      api.getMe()
        .then((user) => setCurrentUser(user))
        .catch(() => {
          clearStoredTokens();
          setCurrentUser(null);
        })
        .finally(() => setAuthLoading(false));
    } else {
      setAuthLoading(false);
    }

    const handleAuthExpired = () => setCurrentUser(null);
    window.addEventListener('auth-expired', handleAuthExpired);
    return () => window.removeEventListener('auth-expired', handleAuthExpired);
  }, []);

  // Periodic health check
  useEffect(() => {
    const checkHealth = async () => {
      try {
        await api.checkHealth();
        setBackendOnline(true);
      } catch {
        setBackendOnline(false);
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  // Fetch conversations when user logs in
  const fetchConversations = useCallback(async () => {
    if (!currentUser) return;
    setSidebarLoading(true);
    try {
      const data = await api.getConversations(1, 50);
      const items = data.items || [];
      setConversations(items);
      // If no active conversation, pick the first one if available
      if (items.length > 0 && !activeConversationId) {
        setActiveConversationId(items[0].id);
      }
    } catch (err) {
      console.error('Failed to fetch conversations:', err);
    } finally {
      setSidebarLoading(false);
    }
  }, [currentUser, activeConversationId]);

  useEffect(() => {
    if (currentUser) {
      fetchConversations();
    } else {
      setConversations([]);
      setActiveConversationId(null);
      setMessages([]);
    }
  }, [currentUser]);

  // Fetch messages for active conversation
  const fetchMessages = useCallback(async (convId, silent = false) => {
    if (!convId) return;
    try {
      const msgs = await api.getMessages(convId);
      setMessages(msgs);
      // Check if last message is an AI reply to turn off typing indicator
      if (msgs.length > 0) {
        const lastMsg = msgs[msgs.length - 1];
        if (lastMsg.sender_type !== 'user') {
          setIsWaitingAi(false);
        }
      }
    } catch (err) {
      if (!silent) {
        console.error('Failed to load messages for conversation:', convId, err);
      }
    }
  }, []);

  // On active conversation change, load its messages
  useEffect(() => {
    if (activeConversationId) {
      setIsWaitingAi(false);
      fetchMessages(activeConversationId);
    } else {
      setMessages([]);
    }
  }, [activeConversationId, fetchMessages]);

  // Polling for new messages (e.g. AI answer from Celery) while active
  useEffect(() => {
    if (!activeConversationId || !currentUser) return;

    const interval = setInterval(() => {
      fetchMessages(activeConversationId, true);
    }, 2500);

    return () => clearInterval(interval);
  }, [activeConversationId, currentUser, fetchMessages]);

  // Handler: Create new conversation
  const handleCreateConversation = async (priority = 'medium') => {
    try {
      const newConv = await api.createConversation(priority, 'web');
      setConversations((prev) => [newConv, ...prev]);
      setActiveConversationId(newConv.id);
      setMessages([]);
    } catch (err) {
      alert(`Ошибка при создании диалога: ${err.message}`);
    }
  };

  // Handler: Send message
  const handleSendMessage = async (content) => {
    if (!activeConversationId || !content) return;
    setIsSending(true);
    setIsWaitingAi(true);

    // Optimistic user message addition
    const tempUserMsg = {
      id: Date.now(),
      conversation_id: activeConversationId,
      sender_type: 'user',
      content,
      is_auto_reply: false,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      await api.sendMessage(activeConversationId, content);
      // Refresh messages list
      await fetchMessages(activeConversationId);
      // Update conversation in sidebar list (last updated timestamp)
      setConversations((prev) =>
        prev.map((c) => (c.id === activeConversationId ? { ...c, updated_at: new Date().toISOString() } : c))
      );
    } catch (err) {
      console.error('Send message error:', err);
      alert(`Не удалось отправить сообщение: ${err.message}`);
      setIsWaitingAi(false);
    } finally {
      setIsSending(false);
    }
  };

  // Handler: Close conversation
  const handleCloseConversation = async (id) => {
    try {
      const closed = await api.closeConversation(id);
      setConversations((prev) =>
        prev.map((c) => (c.id === id ? { ...c, status: 'closed' } : c))
      );
      if (activeConversationId === id) {
        // Refresh conversation details
        fetchMessages(id);
      }
    } catch (err) {
      alert(`Не удалось завершить диалог: ${err.message}`);
    }
  };

  // Handler: Logout
  const handleLogout = () => {
    clearStoredTokens();
    setCurrentUser(null);
    setConversations([]);
    setActiveConversationId(null);
    setMessages([]);
  };

  const activeConversation = conversations.find((c) => c.id === activeConversationId);

  return (
    <div className="app-viewport">
      {/* Background Animated Gradient Orbs */}
      <div className="ambient-bg">
        <div className="ambient-orb orb-1" />
        <div className="ambient-orb orb-2" />
        <div className="ambient-orb orb-3" />
      </div>

      {/* Centered Main Window */}
      <div className="window-container">
        {/* Top Window Chrome */}
        <div className="window-header">
          <div className="window-controls">
            <span className="control-dot dot-close" title="Закрыть" />
            <span className="control-dot dot-minimize" title="Свернуть" />
            <span className="control-dot dot-maximize" title="Развернуть" />
          </div>

          <div className="window-title">
            <Sparkles size={16} color="#818cf8" />
            <span>AI Support Desk</span>
            <div className="window-status-pill">
              <span className={`status-beacon ${backendOnline ? '' : 'offline'}`} style={backendOnline ? {} : { backgroundColor: '#ef4444', boxShadow: '0 0 8px #ef4444' }} />
              <span>{backendOnline ? 'Online' : 'Offline'}</span>
            </div>
          </div>

          <div className="window-actions">
            {currentUser && (
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                {currentUser.nickname || currentUser.email}
              </span>
            )}
          </div>
        </div>

        {/* Window Content Body */}
        <div className="window-body">
          {authLoading ? (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
              Загрузка сессии...
            </div>
          ) : !currentUser ? (
            <AuthModal onLoginSuccess={(user) => setCurrentUser(user)} />
          ) : (
            <>
              <ChatSidebar
                conversations={conversations}
                activeConversationId={activeConversationId}
                onSelectConversation={(id) => setActiveConversationId(id)}
                onCreateConversation={handleCreateConversation}
                currentUser={currentUser}
                onLogout={handleLogout}
                loading={sidebarLoading}
              />

              {activeConversation ? (
                <ChatArea
                  conversation={activeConversation}
                  messages={messages}
                  onSendMessage={handleSendMessage}
                  onCloseConversation={handleCloseConversation}
                  isSending={isSending}
                  isWaitingAi={isWaitingAi}
                />
              ) : (
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', gap: 12 }}>
                  <MessageSquare size={48} style={{ opacity: 0.3 }} />
                  <p style={{ fontSize: 14 }}>Выберите существующий диалог слева или создайте новый.</p>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
