import { useCallback, useMemo, useState } from 'react';
import useOperatorQueue from '../../hooks/useOperatorQueue';
import useOperatorWebSocket from '../../hooks/useOperatorWebSocket';
import { useToasts } from '../notifications/ToastManager';
import OperatorChatWorkspace from './OperatorChatWorkspace';
import OperatorQueueSidebar from './OperatorQueueSidebar';
import OperatorStatsBar from './OperatorStatsBar';

export default function OperatorDashboard({ currentUser }) {
  const {
    queue,
    selectedConversationId,
    selectedConversation,
    selectConversation,
    messages,
    loading,
    messagesLoading,
    actionLoading,
    assignConversation,
    replyToConversation,
    closeConversation,
    returnToAi,
    fetchQueue,
    refreshMessages,
    currentTyping,
    setConversationTyping,
  } = useOperatorQueue(currentUser);

  const { addToast } = useToasts();
  const [typingUsers, setTypingUsers] = useState({});

  // Real-time WebSocket event handlers
  const handleEscalated = useCallback((conversationId) => {
    fetchQueue({ silent: true });
    addToast({
      title: 'Новая эскалация!',
      message: `Обращение #${conversationId} эскалировано в очередь оператора.`,
      type: 'escalation',
      actionLabel: 'Открыть',
      onAction: () => {
        selectConversation(Number(conversationId));
      },
    });
  }, [fetchQueue, addToast, selectConversation]);

  const handleOperatorAssigned = useCallback((data) => {
    fetchQueue({ silent: true });
  }, [fetchQueue]);

  const handleMessageSent = useCallback((data) => {
    if (selectedConversationId && String(data.conversation_id) === String(selectedConversationId)) {
      refreshMessages(selectedConversationId, { silent: true });
    }
  }, [selectedConversationId, refreshMessages]);

  const handleTyping = useCallback((data) => {
    const convId = Number(data.conversation_id);
    const isTyping = Boolean(data.is_typing);
    const senderName = data.sender_name || (data.sender_type === 'user' ? 'Клиент' : 'Оператор');

    setTypingUsers((prev) => ({
      ...prev,
      [convId]: { isTyping, senderName, senderType: data.sender_type },
    }));

    if (convId === selectedConversationId) {
      setConversationTyping(convId, isTyping, senderName);
    }
  }, [selectedConversationId, setConversationTyping]);

  const handleConversationClosed = useCallback(() => {
    fetchQueue({ silent: true });
  }, [fetchQueue]);

  const handleConversationReturnedToAi = useCallback(() => {
    fetchQueue({ silent: true });
  }, [fetchQueue]);

  const { wsStatus, sendTyping } = useOperatorWebSocket({
    enabled: Boolean(currentUser && (currentUser.role === 'operator' || currentUser.role === 'admin')),
    onEscalated: handleEscalated,
    onOperatorAssigned: handleOperatorAssigned,
    onMessageSent: handleMessageSent,
    onTyping: handleTyping,
    onConversationClosed: handleConversationClosed,
    onConversationReturnedToAi: handleConversationReturnedToAi,
  });

  const handleOperatorTyping = useCallback((isTyping) => {
    if (selectedConversationId) {
      sendTyping(selectedConversationId, isTyping);
    }
  }, [selectedConversationId, sendTyping]);

  const stats = useMemo(() => {
    const totalQueueCount = queue.length;
    const myActiveCount = queue.filter((c) => c.operator_id === currentUser?.id).length;
    const escalatedCount = queue.filter((c) => c.status === 'escalated').length;
    return { totalQueueCount, myActiveCount, escalatedCount };
  }, [queue, currentUser]);

  return (
    <div className="operator-dashboard-container">
      <OperatorStatsBar
        escalatedCount={stats.escalatedCount}
        maxLoad={5}
        myActiveCount={stats.myActiveCount}
        totalQueueCount={stats.totalQueueCount}
        wsStatus={wsStatus}
      />
      <div className="operator-workspace-main">
        <OperatorQueueSidebar
          activeConversationId={selectedConversationId}
          currentUserId={currentUser?.id}
          loading={loading}
          onRefresh={() => fetchQueue({ silent: false })}
          onSelectConversation={selectConversation}
          queue={queue}
          typingUsers={typingUsers}
        />
        <OperatorChatWorkspace
          actionLoading={actionLoading}
          conversation={selectedConversation}
          currentUserId={currentUser?.id}
          isUserTyping={Boolean(currentTyping?.isTyping && currentTyping?.senderType !== 'operator')}
          messages={messages}
          messagesLoading={messagesLoading}
          onAssign={assignConversation}
          onBackToAi={returnToAi}
          onClose={closeConversation}
          onReply={replyToConversation}
          onTyping={handleOperatorTyping}
          userTypingName={currentTyping?.senderName || 'Клиент'}
        />
      </div>
    </div>
  );
}
