import { useCallback, useEffect, useMemo, useState } from 'react';
import AppWindow from './components/layout/AppWindow';
import AuthModal from './features/auth/AuthModal';
import SessionsDialog from './features/auth/SessionsDialog';
import ChatWorkspace from './features/chat/ChatWorkspace';
import EmptyConversation from './features/chat/EmptyConversation';
import ChatSidebar from './features/conversations/ChatSidebar';
import { ToastProvider, useToasts } from './features/notifications/ToastManager';
import OperatorDashboard from './features/operator/OperatorDashboard';
import useAuthSession from './hooks/useAuthSession';
import useBackendHealth from './hooks/useBackendHealth';
import useConversations from './hooks/useConversations';
import useOperatorWebSocket from './hooks/useOperatorWebSocket';
import { api, clearStoredTokens } from './services/api';

export default function App() {
  return (
    <ToastProvider>
      <AppContent />
    </ToastProvider>
  );
}

function AppContent() {
  const { currentUser, authLoading, setCurrentUser, logout } = useAuthSession();
  const backendOnline = useBackendHealth();
  const { addToast } = useToasts();

  const isOperatorOrAdmin = useMemo(() => {
    return Boolean(currentUser && (currentUser.role === 'operator' || currentUser.role === 'admin'));
  }, [currentUser]);

  // Mode switcher: 'customer' or 'operator'
  const [appMode, setAppMode] = useState('customer');

  // Default operators to operator workspace on initial login
  useEffect(() => {
    if (currentUser?.role === 'operator') {
      setAppMode('operator');
    } else if (currentUser && currentUser.role !== 'admin') {
      setAppMode('customer');
    }
  }, [currentUser]);

  const {
    activeConversationId,
    conversations,
    createConversation,
    loading: sidebarLoading,
    messagesLoading,
    messages,
    refreshMessages,
    selectConversation,
    setMessages,
    appendOptimisticMessage,
    updateConversation,
    isCurrentWaitingAi,
    setWaitingAiForConversation,
  } = useConversations(currentUser);

  const [isSending, setIsSending] = useState(false);
  const [sessionsOpen, setSessionsOpen] = useState(false);
  const [operatorTyping, setOperatorTyping] = useState({ isTyping: false, name: 'Оператор' });

  // Handle WebSocket events in Customer mode (for operator typing and new messages)
  const handleWsTyping = useCallback((data) => {
    if (String(data.conversation_id) === String(activeConversationId)) {
      if (data.sender_type === 'operator') {
        setOperatorTyping({
          isTyping: Boolean(data.is_typing),
          name: data.sender_name || 'Оператор',
        });
      }
    }
  }, [activeConversationId]);

  const handleWsMessageSent = useCallback((data) => {
    if (String(data.conversation_id) === String(activeConversationId)) {
      refreshMessages(activeConversationId, { silent: true });
    }
  }, [activeConversationId, refreshMessages]);

  const handleWsEscalated = useCallback((conversationId) => {
    // Only alert if we're an operator or admin
    if (isOperatorOrAdmin) {
      addToast({
        title: 'Новая эскалация',
        message: `Обращение #${conversationId} переведено в очередь операторов.`,
        type: 'escalation',
        actionLabel: 'Перейти к оператору',
        onAction: () => setAppMode('operator'),
      });
    }
  }, [isOperatorOrAdmin, addToast]);

  useOperatorWebSocket({
    enabled: Boolean(isOperatorOrAdmin),
    onTyping: handleWsTyping,
    onMessageSent: handleWsMessageSent,
    onEscalated: handleWsEscalated,
  });

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
    // Mark ONLY this active conversation as waiting for AI
    setWaitingAiForConversation(activeConversationId, true);

    const optimisticMessage = {
      id: `temporary-${Date.now()}`,
      conversation_id: activeConversationId,
      sender_type: 'user',
      content,
      is_auto_reply: false,
      created_at: new Date().toISOString(),
    };
    appendOptimisticMessage(activeConversationId, optimisticMessage);

    try {
      await api.sendMessage(activeConversationId, content);
      await refreshMessages(activeConversationId, { silent: true });
      updateConversation(activeConversationId, {
        status: 'pending_ai',
        updated_at: new Date().toISOString(),
      });
    } catch (error) {
      console.error('Send message error:', error);
      alert(`Не удалось отправить сообщение: ${error.message}`);
      setWaitingAiForConversation(activeConversationId, false);
    } finally {
      setIsSending(false);
    }
  }, [
    activeConversationId,
    appendOptimisticMessage,
    refreshMessages,
    setWaitingAiForConversation,
    updateConversation,
  ]);

  const handleUserTyping = useCallback((isTyping) => {
    if (activeConversationId) {
      api.sendTypingStatus(activeConversationId, isTyping);
    }
  }, [activeConversationId]);

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
    <AppWindow
      activeMode={appMode}
      backendOnline={backendOnline}
      currentUser={currentUser}
      onModeChange={setAppMode}
    >
      {authLoading ? (
        <div className="app-loading">Загрузка сессии...</div>
      ) : !currentUser ? (
        <AuthModal onLoginSuccess={setCurrentUser} />
      ) : appMode === 'operator' && isOperatorOrAdmin ? (
        <OperatorDashboard currentUser={currentUser} />
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
              isTyping={operatorTyping.isTyping}
              isWaitingAi={isCurrentWaitingAi}
              messages={messages}
              messagesLoading={messagesLoading}
              onCloseConversation={handleCloseConversation}
              onSendMessage={handleSendMessage}
              onTyping={handleUserTyping}
              typingSenderName={operatorTyping.name}
              typingType="operator"
            />
          ) : (
            <EmptyConversation />
          )}
          {sessionsOpen && (
            <SessionsDialog
              onClose={() => setSessionsOpen(false)}
              onLoggedOut={setCurrentUser}
            />
          )}
        </>
      )}
    </AppWindow>
  );
}
