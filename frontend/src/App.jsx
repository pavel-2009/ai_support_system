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
    activeConversationId, activeConversation, conversations, createConversation, isOperator,
    loading: sidebarLoading, messages, refreshMessages, selectConversation, setMessages,
    updateConversation, refreshConversations,
  } = useConversations(currentUser);
  const [isSending, setIsSending] = useState(false);
  const [isWaitingAi, setIsWaitingAi] = useState(false);
  const [sessionsOpen, setSessionsOpen] = useState(false);

  useEffect(() => {
    if (!activeConversationId || isOperator) setIsWaitingAi(false);
  }, [activeConversationId, isOperator]);

  useEffect(() => {
    const latestMessage = messages.at(-1);
    if (latestMessage && latestMessage.sender_type !== 'user') setIsWaitingAi(false);
  }, [messages]);

  const conversation = useMemo(
    () => activeConversation || conversations.find((item) => item.id === activeConversationId),
    [activeConversation, conversations, activeConversationId],
  );

  const handleCreateConversation = useCallback(async () => {
    try { await createConversation(); }
    catch (error) { alert(`Ошибка при создании диалога: ${error.message}`); throw error; }
  }, [createConversation]);

  const handleSendMessage = useCallback(async (content) => {
    if (!activeConversationId || !content) return;
    setIsSending(true);

    if (!isOperator) {
      setIsWaitingAi(true);
      setMessages((previous) => [...previous, {
        id: `temporary-${Date.now()}`, conversation_id: activeConversationId,
        sender_type: 'user', sender_id: currentUser.id, content,
        is_auto_reply: false, created_at: new Date().toISOString(),
      }]);
    }

    try {
      if (isOperator) {
        const sent = await api.replyAsOperator(activeConversationId, content);
        setMessages((previous) => [...previous, sent]);
      } else {
        await api.sendMessage(activeConversationId, content);
        await refreshMessages(activeConversationId);
        updateConversation(activeConversationId, { updated_at: new Date().toISOString() });
      }
    } catch (error) {
      console.error('Send message error:', error);
      alert(`Не удалось отправить сообщение: ${error.message}`);
      setIsWaitingAi(false);
    } finally { setIsSending(false); }
  }, [activeConversationId, currentUser?.id, isOperator, refreshMessages, setMessages, updateConversation]);

  const handleAssign = useCallback(async () => {
    if (!activeConversationId) return;
    setIsSending(true);
    try {
      const assigned = await api.assignConversation(activeConversationId);
      updateConversation(activeConversationId, { ...assigned, operator_id: currentUser.id });
      await refreshMessages(activeConversationId);
      await refreshConversations();
    } catch (error) { alert(`Не удалось взять диалог: ${error.message}`); }
    finally { setIsSending(false); }
  }, [activeConversationId, currentUser?.id, refreshConversations, refreshMessages, updateConversation]);

  const handleCloseConversation = useCallback(async (id) => {
    try {
      if (isOperator) await api.closeAsOperator(id);
      else await api.closeConversation(id);
      updateConversation(id, { status: 'closed' });
      await refreshMessages(id);
      await refreshConversations();
    } catch (error) { alert(`Не удалось завершить диалог: ${error.message}`); }
  }, [isOperator, refreshConversations, refreshMessages, updateConversation]);

  const handleBackToAi = useCallback(async (id) => {
    try {
      await api.backToAi(id);
      await refreshConversations();
      setMessages([]);
    } catch (error) { alert(`Не удалось вернуть диалог в AI: ${error.message}`); }
  }, [refreshConversations, setMessages]);

  const handleLogout = useCallback(async () => {
    try { await logout(); }
    catch (error) {
      clearStoredTokens(); setCurrentUser(null);
      console.error('Logout error:', error);
    }
  }, [logout, setCurrentUser]);

  return (
    <AppWindow backendOnline={backendOnline} currentUser={currentUser}>
      {authLoading ? <div className="app-loading">Загрузка сессии...</div> : !currentUser ? <AuthModal onLoginSuccess={setCurrentUser} /> : (
        <>
          <ChatSidebar
            activeConversationId={activeConversationId} conversations={conversations} currentUser={currentUser}
            isOperator={isOperator} loading={sidebarLoading} onCreateConversation={handleCreateConversation}
            onLogout={handleLogout} onManageSessions={() => setSessionsOpen(true)} onSelectConversation={selectConversation}
          />
          {conversation ? (
            <ChatWorkspace
              conversation={conversation} currentUser={currentUser} isOperator={isOperator}
              isSending={isSending} isWaitingAi={isWaitingAi} messages={messages}
              onAssign={handleAssign} onBackToAi={handleBackToAi}
              onCloseConversation={handleCloseConversation} onSendMessage={handleSendMessage}
            />
          ) : <EmptyConversation />}
          {sessionsOpen && <SessionsDialog onClose={() => setSessionsOpen(false)} onLoggedOut={setCurrentUser} />}
        </>
      )}
    </AppWindow>
  );
}
