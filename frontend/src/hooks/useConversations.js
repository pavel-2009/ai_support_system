import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '../services/api';

const OPERATOR_ROLES = new Set(['operator', 'admin']);

export default function useConversations(currentUser) {
  const isOperator = useMemo(() => OPERATOR_ROLES.has(currentUser?.role), [currentUser?.role]);
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  const refreshMessages = useCallback(async (conversationId, { silent = false } = {}) => {
    if (!conversationId) return [];
    try {
      const nextMessages = await api.getMessages(conversationId);
      setMessages(nextMessages);
      return nextMessages;
    } catch (error) {
      if (!silent) console.error('Failed to load messages:', error);
      return [];
    }
  }, []);

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
    setMessages([]);
    return conversation;
  }, []);

  const updateConversation = useCallback((conversationId, changes) => {
    setConversations((previous) => previous.map((conversation) => (
      conversation.id === conversationId ? { ...conversation, ...changes } : conversation
    )));
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
