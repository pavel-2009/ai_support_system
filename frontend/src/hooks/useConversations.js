import { useCallback, useEffect, useState } from 'react';
import { api } from '../services/api';

export default function useConversations(currentUser) {
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
      if (!silent) console.error('Failed to load messages for conversation:', conversationId, error);
      return [];
    }
  }, []);

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

  useEffect(() => {
    if (currentUser) {
      fetchConversations();
      return;
    }
    setConversations([]);
    setActiveConversationId(null);
    setMessages([]);
  }, [currentUser, fetchConversations]);

  useEffect(() => {
    if (!activeConversationId) {
      setMessages([]);
      return;
    }
    refreshMessages(activeConversationId);
  }, [activeConversationId, refreshMessages]);

  useEffect(() => {
    if (!activeConversationId || !currentUser) return undefined;
    const intervalId = window.setInterval(() => refreshMessages(activeConversationId, { silent: true }), 2_500);
    return () => window.clearInterval(intervalId);
  }, [activeConversationId, currentUser, refreshMessages]);

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

  return {
    activeConversationId,
    conversations,
    createConversation,
    loading,
    messages,
    refreshMessages,
    selectConversation: setActiveConversationId,
    setMessages,
    updateConversation,
  };
}
