import { Bot, Headset, User } from 'lucide-react';
import { formatTime } from '../../utils/date';
import EmptyChat from './EmptyChat';
import MessageBubble from './MessageBubble';
import TypingIndicator from './TypingIndicator';

export default function MessageList({
  isWaitingAi = false,
  isTyping = false,
  typingType = 'operator',
  typingSenderName,
  messages = [],
  onChoosePrompt,
  scrollTargetRef,
}) {
  return (
    <div className="messages-container">
      {messages.length === 0 ? <EmptyChat onChoosePrompt={onChoosePrompt} /> : messages.map((message) => <MessageBubble key={message.id || `${message.created_at}-${message.content}`} message={message} />)}
      {isWaitingAi && <TypingIndicator />}
      <div ref={scrollTargetRef} />
    </div>
  );
}

function MessageBubble({ message }) {
  const type = message.sender_type;
  const isUser = type === 'user';
  const isOperator = type === 'operator';
  const label = isUser ? 'Пользователь' : isOperator ? 'Оператор' : 'ИИ';
  const Icon = isUser ? User : isOperator ? Headset : Bot;
  const roleClass = isUser ? 'user' : isOperator ? 'operator' : 'assistant';
  return (
    <div className={`message-row ${roleClass}`}>
      <div className={`message-avatar ${roleClass}-avatar`}><Icon size={18} /></div>
      <div className="message-bubble">
        <div className="message-author">{label}</div>
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
  return <div className="message-row assistant"><div className="message-avatar assistant-avatar"><Bot size={18} /></div><div className="typing-indicator"><span className="typing-dot" /><span className="typing-dot" /><span className="typing-dot" /><span className="typing-label">ИИ генерирует ответ...</span></div></div>;
}
