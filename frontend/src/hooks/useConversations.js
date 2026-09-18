import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../services/api';

export default function useConversations(currentUser) {
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [messagesByConvId, setMessagesByConvId] = useState({});
  const [waitingAiByConvId, setWaitingAiByConvId] = useState({});
  const [loading, setLoading] = useState(false);
  const [messagesLoading, setMessagesLoading] = useState(false);

  const activeIdRef = useRef(activeConversationId);
  activeIdRef.current = activeConversationId;

  // Refresh messages for a specific conversation with race-condition prevention
  const refreshMessages = useCallback(async (conversationId, { silent = false } = {}) => {
    if (!conversationId) return [];

    if (!silent && !messagesByConvId[conversationId]) {
      setMessagesLoading(true);
    }

    try {
      const [nextMessages, updatedConv] = await Promise.all([
        api.getMessages(conversationId),
        // Refresh conversation status in background if not silent
        api.getConversation(conversationId).catch(() => null),
      ]);

      // Always update cache for this specific conversation ID
      setMessagesByConvId((previous) => ({
        ...previous,
        [conversationId]: nextMessages,
      }));

      // If the latest message is from AI or operator, clear waiting AI flag for THIS conversation
      const latestMessage = nextMessages.at(-1);
      if (latestMessage && latestMessage.sender_type !== 'user') {
        setWaitingAiByConvId((prev) => ({ ...prev, [conversationId]: false }));
      }

      // Update conversation in sidebar list if status or updated_at changed
      if (updatedConv) {
        setConversations((previous) =>
          previous.map((conv) => (conv.id === conversationId ? { ...conv, ...updatedConv } : conv)),
        );
      }

      return nextMessages;
    } catch (error) {
      if (!silent) console.error('Failed to load messages for conversation:', conversationId, error);
      return [];
    } finally {
      if (!silent) {
        setMessagesLoading(false);
      }
    }
  }, [messagesByConvId]);

  // Load all user conversations
  const fetchConversations = useCallback(async () => {
    if (!currentUser) return;
    setLoading(true);
    try {
      const { items = [] } = await api.getConversations(1, 50);
      setConversations(items);
      setActiveConversationId((currentId) => currentId || items[0]?.id || null);
    } catch (error) {
      console.error('Failed to fetch conversations:', error);
    } finally {
      setLoading(false);
    }
  }, [currentUser]);

  // Initial load
  useEffect(() => {
    if (currentUser) {
      fetchConversations();
      return;
    }
    setConversations([]);
    setActiveConversationId(null);
    setMessagesByConvId({});
    setWaitingAiByConvId({});
  }, [currentUser, fetchConversations]);

  // When active conversation changes, load its messages
  useEffect(() => {
    if (!activeConversationId) return;
    refreshMessages(activeConversationId);
  }, [activeConversationId, refreshMessages]);

  // Periodic background polling for active conversation
  useEffect(() => {
    if (!activeConversationId || !currentUser) return undefined;
    const intervalId = window.setInterval(() => {
      refreshMessages(activeConversationId, { silent: true });
    }, 2500);
    return () => window.clearInterval(intervalId);
  }, [activeConversationId, currentUser, refreshMessages]);

  // Periodic background sync for conversations list to keep statuses up to date
  useEffect(() => {
    if (!currentUser) return undefined;
    const intervalId = window.setInterval(async () => {
      try {
        const { items = [] } = await api.getConversations(1, 50);
        setConversations(items);
      } catch {
        // Ignore background polling errors
      }
    }, 6000);
    return () => window.clearInterval(intervalId);
  }, [currentUser]);

  const createConversation = useCallback(async (priority = 'medium') => {
    const conversation = await api.createConversation(priority, 'web');
    setConversations((previous) => [conversation, ...previous]);
    setActiveConversationId(conversation.id);
    setMessagesByConvId((previous) => ({
      ...previous,
      [conversation.id]: [],
    }));
    return conversation;
  }, []);

  const updateConversation = useCallback((conversationId, changes) => {
    setConversations((previous) =>
      previous.map((conversation) =>
        conversation.id === conversationId ? { ...conversation, ...changes } : conversation,
      ),
    );
  }, []);

  const setWaitingAiForConversation = useCallback((conversationId, isWaiting) => {
    setWaitingAiByConvId((prev) => ({
      ...prev,
      [conversationId]: isWaiting,
    }));
  }, []);

  const appendOptimisticMessage = useCallback((conversationId, message) => {
    setMessagesByConvId((previous) => ({
      ...previous,
      [conversationId]: [...(previous[conversationId] || []), message],
    }));
  }, []);

  // Active conversation's messages
  const currentMessages = activeConversationId ? (messagesByConvId[activeConversationId] || []) : [];
  const isCurrentWaitingAi = activeConversationId ? Boolean(waitingAiByConvId[activeConversationId]) : false;

  return {
    activeConversationId,
    conversations,
    createConversation,
    loading,
    messagesLoading,
    messages: currentMessages,
    messagesByConvId,
    refreshMessages,
    selectConversation: setActiveConversationId,
    setMessages: (newMessagesOrFn) => {
      if (!activeConversationId) return;
      setMessagesByConvId((previous) => {
        const prevMessages = previous[activeConversationId] || [];
        const next = typeof newMessagesOrFn === 'function' ? newMessagesOrFn(prevMessages) : newMessagesOrFn;
        return { ...previous, [activeConversationId]: next };
      });
    },
    appendOptimisticMessage,
    updateConversation,
    waitingAiByConvId,
    isCurrentWaitingAi,
    setWaitingAiForConversation,
    fetchConversations,
  };
}
