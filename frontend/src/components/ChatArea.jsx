import React, { useState, useEffect, useRef } from 'react';
import { Send, Bot, User, Sparkles, XCircle, AlertTriangle, CheckCircle2, ShieldAlert } from 'lucide-react';

export default function ChatArea({
  conversation,
  messages = [],
  onSendMessage,
  onCloseConversation,
  isSending = false,
  isWaitingAi = false,
}) {
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  // Auto-scroll to bottom on messages change
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isWaitingAi]);

  // Adjust textarea height
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [inputText]);

  const handleSend = (e) => {
    e?.preventDefault();
    if (!inputText.trim() || isSending || conversation?.status === 'closed') return;
    onSendMessage(inputText.trim());
    setInputText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const formatTime = (dateStr) => {
    if (!dateStr) return '';
    try {
      const date = new Date(dateStr);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  const isClosed = conversation?.status === 'closed';

  const quickPrompts = [
    'Здравствуйте! Подскажите, как работает поддержка?',
    'У меня вопрос по поводу тарифов и оплаты',
    'Как связаться с живым оператором?',
  ];

  return (
    <div className="chat-area">
      {/* Header */}
      <div className="chat-area-header">
        <div className="chat-details">
          <span className="chat-area-title">Диалог #{conversation?.id}</span>

          <span className={`badge badge-${conversation?.status || 'open'}`}>
            {conversation?.status === 'open' && 'Открыт'}
            {conversation?.status === 'waiting_for_user' && 'Ждет ответа'}
            {conversation?.status === 'waiting_for_operator' && 'В очереди к оператору'}
            {conversation?.status === 'escalated' && 'Эскалирован'}
            {conversation?.status === 'closed' && 'Завершен'}
          </span>

          {conversation?.ai_confidence !== undefined && conversation?.ai_confidence > 0 && (
            <span className="ai-confidence-pill" title="Уверенность AI модели в ответе">
              <Sparkles size={13} />
              AI: {Math.round(conversation.ai_confidence * 100)}%
            </span>
          )}
        </div>

        <div>
          {!isClosed && (
            <button
              className="btn-secondary"
              onClick={() => onCloseConversation(conversation?.id)}
              title="Завершить текущий диалог"
              type="button"
            >
              <XCircle size={14} />
              Завершить диалог
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="empty-chat">
            <div className="empty-icon-halo">
              <Bot size={34} />
            </div>
            <h3 className="empty-title">Чем мы можем вам помочь?</h3>
            <p className="empty-subtitle">
              Напишите ваш вопрос в поле ниже, и наш ИИ-ассистент мгновенно проанализирует обращение и предоставит ответ.
            </p>

            <div className="prompt-suggestions">
              {quickPrompts.map((prompt, idx) => (
                <button
                  key={idx}
                  className="prompt-chip"
                  onClick={() => setInputText(prompt)}
                  type="button"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg) => {
            const isUser = msg.sender_type === 'user';
            const isAI = msg.sender_type === 'ai' || msg.sender_type === 'agent' || msg.is_auto_reply;

            return (
              <div
                key={msg.id || `${msg.created_at}-${msg.content.slice(0, 10)}`}
                className={`message-row ${isUser ? 'user' : 'assistant'}`}
              >
                <div className={`message-avatar ${isUser ? 'user-avatar' : 'ai-avatar'}`}>
                  {isUser ? <User size={18} /> : <Bot size={18} />}
                </div>

                <div className="message-bubble">
                  <div>{msg.content}</div>

                  <div className="message-meta">
                    {msg.confidence !== null && msg.confidence !== undefined && (
                      <span className="message-tag">
                        AI {Math.round(msg.confidence * 100)}%
                      </span>
                    )}
                    {msg.needs_review && (
                      <span className="message-tag" style={{ background: 'rgba(239,68,68,0.25)', color: '#fca5a5' }}>
                        Проверка
                      </span>
                    )}
                    <span>{formatTime(msg.created_at)}</span>
                  </div>
                </div>
              </div>
            );
          })
        )}

        {/* Typing indicator when waiting for LLM response */}
        {isWaitingAi && (
          <div className="message-row assistant">
            <div className="message-avatar ai-avatar">
              <Bot size={18} />
            </div>
            <div className="typing-indicator">
              <span className="typing-dot" />
              <span className="typing-dot" />
              <span className="typing-dot" />
              <span style={{ fontSize: 12, color: 'var(--text-muted)', marginLeft: 6 }}>
                ИИ генерирует ответ...
              </span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="chat-input-bar">
        {isClosed ? (
          <div style={{ textAlign: 'center', padding: '10px', color: 'var(--text-muted)', fontSize: 13 }}>
            Этот диалог завершен. Создайте новый диалог в боковой панели, чтобы продолжить общение.
          </div>
        ) : (
          <form onSubmit={handleSend}>
            <div className="input-container">
              <textarea
                ref={textareaRef}
                className="chat-textarea"
                placeholder="Напишите сообщение... (Enter для отправки)"
                rows={1}
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isSending}
              />

              <button
                type="submit"
                className="send-btn"
                disabled={!inputText.trim() || isSending}
                title="Отправить сообщение"
              >
                <Send size={16} />
              </button>
            </div>

            <div className="input-hints">
              <span>Enter ↵ — отправить, Shift+Enter — новая строка</span>
              <span>Канал: {conversation?.channel || 'WEB'}</span>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
