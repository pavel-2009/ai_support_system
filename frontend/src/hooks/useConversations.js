import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { api } from '../services/api';

const OPERATOR_ROLES = new Set(['operator', 'admin']);

export default function useConversations(currentUser) {
  const isOperator = useMemo(() => OPERATOR_ROLES.has(currentUser?.role), [currentUser?.role]);
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
      if (!silent) console.error('Failed to load messages:', error);
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
      let items;
      if (isOperator) {
        const [queue, own] = await Promise.all([api.getOperatorQueue(), api.getConversations(1, 100)]);
        const ownAssigned = (own.items || []).filter((item) => item.operator_id === currentUser.id);
        items = Array.from(new Map([...queue, ...ownAssigned].map((item) => [item.id, item])).values());
        items.sort((a, b) => new Date(b.updated_at || b.created_at) - new Date(a.updated_at || a.created_at));
      } else {
        items = (await api.getConversations(1, 50)).items || [];
      }
      setConversations(items);
      setActiveConversationId((currentId) => (
        currentId && items.some((item) => item.id === currentId) ? currentId : items[0]?.id || null
      ));
    } catch (error) {
      console.error('Failed to fetch conversations:', error);
    } finally {
      setLoading(false);
    }
  }, [currentUser, isOperator]);

  // Initial load
  useEffect(() => {
    if (!currentUser) {
      setConversations([]);
      setActiveConversationId(null);
      setMessages([]);
      return;
    }
    fetchConversations();
  }, [currentUser, fetchConversations]);

  const activeConversation = useMemo(
    () => conversations.find((conversation) => conversation.id === activeConversationId),
    [conversations, activeConversationId],
  );

  useEffect(() => {
    if (!activeConversationId) {
      setMessages([]);
      return;
    }
    if (isOperator && activeConversation?.operator_id !== currentUser.id && currentUser.role !== 'admin') {
      setMessages([]);
      return;
    }
    refreshMessages(activeConversationId);
  }, [activeConversationId, activeConversation?.operator_id, currentUser?.id, currentUser?.role, isOperator, refreshMessages]);

  // Periodic background polling for active conversation
  useEffect(() => {
    if (!currentUser) return undefined;
    const intervalId = window.setInterval(() => {
      fetchConversations();
      if (activeConversationId && (!isOperator || activeConversation?.operator_id === currentUser.id || currentUser.role === 'admin')) {
        refreshMessages(activeConversationId, { silent: true });
      }
    }, 5000);
    return () => window.clearInterval(intervalId);
  }, [currentUser, isOperator, activeConversationId, activeConversation?.operator_id, fetchConversations, refreshMessages]);

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

  const selectConversation = useCallback((id) => {
    setActiveConversationId(id);
    setMessages([]);
  }, []);

  return {
    activeConversationId, activeConversation, conversations, createConversation, isOperator,
    loading, messages, refreshMessages, selectConversation, setMessages, updateConversation,
    refreshConversations: fetchConversations,
  };
}
