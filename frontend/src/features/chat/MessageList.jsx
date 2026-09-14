import { Bot, User } from 'lucide-react';
import { formatTime } from '../../utils/date';
import EmptyChat from './EmptyChat';

export default function MessageList({ isWaitingAi, messages, onChoosePrompt, scrollTargetRef }) {
  return (
    <div className="messages-container">
      {messages.length === 0
        ? <EmptyChat onChoosePrompt={onChoosePrompt} />
        : messages.map((message) => <MessageBubble key={message.id || `${message.created_at}-${message.content}`} message={message} />)}
      {isWaitingAi && <TypingIndicator />}
      <div ref={scrollTargetRef} />
    </div>
  );
}

function MessageBubble({ message }) {
  const isUser = message.sender_type === 'user';
  return (
    <div className={`message-row ${isUser ? 'user' : 'assistant'}`}>
      <div className={`message-avatar ${isUser ? 'user-avatar' : 'ai-avatar'}`}>
        {isUser ? <User size={18} /> : <Bot size={18} />}
      </div>
      <div className="message-bubble">
        <div>{message.content}</div>
        <div className="message-meta">
          {message.confidence != null && <span className="message-tag">AI {Math.round(message.confidence * 100)}%</span>}
          {message.needs_review && <span className="message-tag message-tag--review">Проверка</span>}
          <span>{formatTime(message.created_at)}</span>
        </div>
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="message-row assistant">
      <div className="message-avatar ai-avatar"><Bot size={18} /></div>
      <div className="typing-indicator">
        <span className="typing-dot" /><span className="typing-dot" /><span className="typing-dot" />
        <span className="typing-label">ИИ генерирует ответ...</span>
      </div>
    </div>
  );
}
