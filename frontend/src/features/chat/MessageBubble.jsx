import { Bot, Headphones, Sparkles, User } from 'lucide-react';
import { formatTime } from '../../utils/date';

export default function MessageBubble({ message }) {
  const senderType = message.sender_type || 'user';
  const isUser = senderType === 'user';
  const isOperator = senderType === 'operator';
  const isAi = senderType === 'assistant' || senderType === 'ai';

  const getSenderMeta = () => {
    if (isUser) {
      return {
        roleLabel: null,
        avatarIcon: <User size={17} />,
        rowClass: 'user',
        avatarClass: 'user-avatar',
      };
    }
    if (isOperator) {
      return {
        roleLabel: 'Оператор поддержки',
        avatarIcon: <Headphones size={17} />,
        rowClass: 'operator',
        avatarClass: 'operator-avatar',
      };
    }
    return {
      roleLabel: 'AI Ассистент',
      avatarIcon: <Bot size={17} />,
      rowClass: 'assistant',
      avatarClass: 'ai-avatar',
    };
  };

  const meta = getSenderMeta();

  return (
    <div className={`message-row ${meta.rowClass}`}>
      <div className={`message-avatar ${meta.avatarClass}`} title={meta.roleLabel || 'Пользователь'}>
        {meta.avatarIcon}
      </div>
      <div className="message-bubble">
        {meta.roleLabel && (
          <div className="message-sender-header">
            <span className="message-sender-name">{meta.roleLabel}</span>
            {message.is_auto_reply && (
              <span className="auto-reply-pill">
                <Sparkles size={11} /> авто-ответ
              </span>
            )}
          </div>
        )}
        <div className="message-text">{message.content}</div>
        <div className="message-meta">
          {message.confidence != null && (
            <span className="message-tag" title="Уверенность модели">
              AI {Math.round(message.confidence * 100)}%
            </span>
          )}
          {message.needs_review && (
            <span className="message-tag message-tag--review" title="Требует проверки оператора">
              Проверка
            </span>
          )}
          <span className="message-time">{formatTime(message.created_at)}</span>
        </div>
      </div>
    </div>
  );
}
