import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '../services/api';

export default function useOperatorQueue(currentUser) {
  const [queue, setQueue] = useState([]);
  const [selectedConversationId, setSelectedConversationId] = useState(null);
  const [messagesByConvId, setMessagesByConvId] = useState({});
  const [loading, setLoading] = useState(false);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [typingUsers, setTypingUsers] = useState({}); // { [conversationId]: { isTyping, senderName } }

  const fetchQueue = useCallback(async ({ silent = false } = {}) => {
    if (!currentUser || (currentUser.role !== 'operator' && currentUser.role !== 'admin')) {
      return;
    }

    if (!silent) setLoading(true);
    try {
      const items = await api.getOperatorQueue();
      setQueue(Array.isArray(items) ? items : []);
      setSelectedConversationId((current) => current || (items && items[0]?.id) || null);
    } catch (error) {
      if (!silent) console.error('Failed to fetch operator queue:', error);
    } finally {
      if (!silent) setLoading(false);
    }
  }, [currentUser]);

  const refreshMessages = useCallback(async (conversationId, { silent = false } = {}) => {
    if (!conversationId) return [];
    if (!silent && !messagesByConvId[conversationId]) {
      setMessagesLoading(true);
    }

    try {
      const messages = await api.getMessages(conversationId);
      setMessagesByConvId((prev) => ({
        ...prev,
        [conversationId]: messages,
      }));
      return messages;
    } catch (error) {
      if (!silent) console.error('Failed to load conversation messages:', conversationId, error);
      return [];
    } finally {
      if (!silent) setMessagesLoading(false);
    }
  }, [messagesByConvId]);

  // Initial load
  useEffect(() => {
    fetchQueue();
  }, [fetchQueue]);

  // When selected conversation changes
  useEffect(() => {
    if (selectedConversationId) {
      refreshMessages(selectedConversationId);
    }
  }, [selectedConversationId, refreshMessages]);

  // Background polling fallback for queue and active messages
  useEffect(() => {
    if (!currentUser || (currentUser.role !== 'operator' && currentUser.role !== 'admin')) {
      return undefined;
    }

    const intervalId = window.setInterval(() => {
      fetchQueue({ silent: true });
      if (selectedConversationId) {
        refreshMessages(selectedConversationId, { silent: true });
      }
    }, 4000);

    return () => window.clearInterval(intervalId);
  }, [currentUser, fetchQueue, refreshMessages, selectedConversationId]);

  const selectedConversation = useMemo(
    () => queue.find((c) => c.id === selectedConversationId) || null,
    [queue, selectedConversationId],
  );

  const assignConversation = useCallback(async (conversationId) => {
    setActionLoading(true);
    try {
      const updated = await api.assignOperator(conversationId);
      setQueue((prev) =>
        prev.map((item) => (item.id === conversationId ? { ...item, ...updated, operator_id: currentUser?.id } : item)),
      );
      await refreshMessages(conversationId);
      return updated;
    } catch (error) {
      console.error('Failed to assign conversation:', error);
      throw error;
    } finally {
      setActionLoading(false);
    }
  }, [currentUser, refreshMessages]);

  const replyToConversation = useCallback(async (conversationId, text) => {
    setActionLoading(true);
    // Optimistic message
    const optimisticMessage = {
      id: `temp-${Date.now()}`,
      conversation_id: conversationId,
      sender_type: 'operator',
      sender_id: currentUser?.id,
      content: text,
      is_auto_reply: false,
      created_at: new Date().toISOString(),
    };

    setMessagesByConvId((prev) => ({
      ...prev,
      [conversationId]: [...(prev[conversationId] || []), optimisticMessage],
    }));

    try {
      const res = await api.replyAsOperator(conversationId, text);
      await refreshMessages(conversationId, { silent: true });
      return res;
    } catch (error) {
      console.error('Failed to reply to conversation:', error);
      throw error;
    } finally {
      setActionLoading(false);
    }
  }, [currentUser, refreshMessages]);

  const closeConversation = useCallback(async (conversationId) => {
    setActionLoading(true);
    try {
      await api.closeOperatorConversation(conversationId);
      setQueue((prev) => prev.filter((item) => item.id !== conversationId));
      if (selectedConversationId === conversationId) {
        setSelectedConversationId(null);
      }
    } catch (error) {
      console.error('Failed to close conversation:', error);
      throw error;
    } finally {
      setActionLoading(false);
    }
  }, [selectedConversationId]);

  const returnToAi = useCallback(async (conversationId) => {
    setActionLoading(true);
    try {
      await api.backToAi(conversationId);
      setQueue((prev) => prev.filter((item) => item.id !== conversationId));
      if (selectedConversationId === conversationId) {
        setSelectedConversationId(null);
      }
    } catch (error) {
      console.error('Failed to return conversation to AI:', error);
      throw error;
    } finally {
      setActionLoading(false);
    }
  }, [selectedConversationId]);

  const setConversationTyping = useCallback((conversationId, isTyping, senderName) => {
    setTypingUsers((prev) => ({
      ...prev,
      [conversationId]: { isTyping, senderName },
    }));
  }, []);

  const currentMessages = selectedConversationId ? messagesByConvId[selectedConversationId] || [] : [];
  const currentTyping = selectedConversationId ? typingUsers[selectedConversationId] : null;

  return {
    queue,
    selectedConversationId,
    selectedConversation,
    selectConversation: setSelectedConversationId,
    messages: currentMessages,
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
  };
}
