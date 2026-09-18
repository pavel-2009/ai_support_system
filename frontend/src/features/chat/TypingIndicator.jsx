import { Bot, Headphones, User } from 'lucide-react';

export default function TypingIndicator({ type = 'ai', senderName }) {
  const getMeta = () => {
    switch (type) {
      case 'operator':
        return {
          icon: <Headphones size={16} />,
          avatarClass: 'operator-avatar',
          text: senderName ? `${senderName} печатает...` : 'Оператор печатает...',
        };
      case 'user':
        return {
          icon: <User size={16} />,
          avatarClass: 'user-avatar',
          text: senderName ? `${senderName} печатает...` : 'Пользователь печатает...',
        };
      case 'ai':
      default:
        return {
          icon: <Bot size={16} />,
          avatarClass: 'ai-avatar',
          text: 'ИИ генерирует ответ...',
        };
    }
  };

  const meta = getMeta();

  return (
    <div className={`message-row ${type === 'user' ? 'user' : 'assistant'} typing-row`}>
      <div className={`message-avatar ${meta.avatarClass}`}>
        {meta.icon}
      </div>
      <div className="typing-indicator">
        <span className="typing-dot" />
        <span className="typing-dot" />
        <span className="typing-dot" />
        <span className="typing-label">{meta.text}</span>
      </div>
    </div>
  );
}
