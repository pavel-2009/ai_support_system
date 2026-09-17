import { useCallback, useEffect, useMemo, useState } from 'react';
import { api, clearStoredTokens } from './services/api';
import AppWindow from './components/layout/AppWindow';
import AuthModal from './features/auth/AuthModal';
import ChatSidebar from './features/conversations/ChatSidebar';
import ChatWorkspace from './features/chat/ChatWorkspace';
import EmptyConversation from './features/chat/EmptyConversation';
import useAuthSession from './hooks/useAuthSession';
import useBackendHealth from './hooks/useBackendHealth';
import useConversations from './hooks/useConversations';
import SessionsDialog from './features/auth/SessionsDialog';

export default function App() {
  const { currentUser, authLoading, setCurrentUser, logout } = useAuthSession();
  const backendOnline = useBackendHealth();
  const {
    activeConversationId,
    conversations,
    createConversation,
    loading: sidebarLoading,
    messages,
    refreshMessages,
    selectConversation,
    setMessages,
    updateConversation,
  } = useConversations(currentUser);
  const [isSending, setIsSending] = useState(false);
  const [isWaitingAi, setIsWaitingAi] = useState(false);
  const [sessionsOpen, setSessionsOpen] = useState(false);

  useEffect(() => {
    if (!activeConversationId) setIsWaitingAi(false);
  }, [activeConversationId]);

  useEffect(() => {
    const latestMessage = messages.at(-1);
    if (latestMessage && latestMessage.sender_type !== 'user') setIsWaitingAi(false);
  }, [messages]);

  const activeConversation = useMemo(
    () => conversations.find((conversation) => conversation.id === activeConversationId),
    [activeConversationId, conversations],
  );

  const handleCreateConversation = useCallback(async (priority = 'medium') => {
    try {
      await createConversation(priority);
    } catch (error) {
      alert(`Ошибка при создании диалога: ${error.message}`);
      throw error;
    }
  }, [createConversation]);

  const handleSendMessage = useCallback(async (content) => {
    if (!activeConversationId || !content) return;

    setIsSending(true);
    setIsWaitingAi(true);
    const optimisticMessage = {
      id: `temporary-${Date.now()}`,
      conversation_id: activeConversationId,
      sender_type: 'user',
      content,
      is_auto_reply: false,
      created_at: new Date().toISOString(),
    };
    setMessages((previousMessages) => [...previousMessages, optimisticMessage]);

    try {
      await api.sendMessage(activeConversationId, content);
      await refreshMessages(activeConversationId);
      updateConversation(activeConversationId, { updated_at: new Date().toISOString() });
    } catch (error) {
      console.error('Send message error:', error);
      alert(`Не удалось отправить сообщение: ${error.message}`);
      setIsWaitingAi(false);
    } finally {
      setIsSending(false);
    }
  }, [activeConversationId, refreshMessages, setMessages, updateConversation]);

  const handleCloseConversation = useCallback(async (conversationId) => {
    try {
      await api.closeConversation(conversationId);
      updateConversation(conversationId, { status: 'closed' });
      await refreshMessages(conversationId);
    } catch (error) {
      alert(`Не удалось завершить диалог: ${error.message}`);
    }
  }, [refreshMessages, updateConversation]);

  const handleLogout = useCallback(async () => {
    try {
      await logout();
    } catch (error) {
      clearStoredTokens();
      setCurrentUser(null);
      console.error('Logout error:', error);
    }
  }, [logout, setCurrentUser]);

  return (
    <AppWindow backendOnline={backendOnline} currentUser={currentUser}>
      {authLoading ? (
        <div className="app-loading">Загрузка сессии...</div>
      ) : !currentUser ? (
        <AuthModal onLoginSuccess={setCurrentUser} />
      ) : (
        <>
          <ChatSidebar
            activeConversationId={activeConversationId}
            conversations={conversations}
            currentUser={currentUser}
            loading={sidebarLoading}
            onCreateConversation={handleCreateConversation}
            onLogout={handleLogout}
            onManageSessions={() => setSessionsOpen(true)}
            onSelectConversation={selectConversation}
          />
          {activeConversation ? (
            <ChatWorkspace
              conversation={activeConversation}
              isSending={isSending}
              isWaitingAi={isWaitingAi}
              messages={messages}
              onCloseConversation={handleCloseConversation}
              onSendMessage={handleSendMessage}
            />
          ) : <EmptyConversation />}
          {sessionsOpen && <SessionsDialog onClose={() => setSessionsOpen(false)} onLoggedOut={setCurrentUser} />}
        </>
      )}
    </AppWindow>
  );
}
