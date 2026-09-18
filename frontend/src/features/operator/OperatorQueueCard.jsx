import { Headphones, Sparkles } from 'lucide-react';
import { formatConversationTimestamp } from '../../utils/date';
import StatusBadge from '../conversations/StatusBadge';

export default function OperatorQueueCard({
  conversation,
  isActive,
  isAssignedToMe,
  isUserTyping,
  onClick,
}) {
  const priority = conversation.priority || 'medium';

  return (
    <button
      className={`queue-card ${isActive ? 'active' : ''} priority-border-${priority}`}
      onClick={onClick}
      type="button"
    >
      <div className="queue-card-top">
        <div className="queue-card-id-block">
          <span className={`priority-indicator priority-${priority}`} />
          <span className="queue-card-id">Обращение #{conversation.id}</span>
        </div>
        <span className="queue-card-time">
          {formatConversationTimestamp(conversation.updated_at || conversation.created_at)}
        </span>
      </div>

      <div className="queue-card-mid">
        <StatusBadge status={conversation.status} />
        <span className="queue-card-channel">{conversation.channel || 'WEB'}</span>
      </div>

      <div className="queue-card-bottom">
        <div className="queue-card-assignee">
          {isAssignedToMe ? (
            <span className="assignee-tag assignee-me">
              <Headphones size={11} /> В работе у вас
            </span>
          ) : conversation.operator_id ? (
            <span className="assignee-tag assignee-other">
              <Headphones size={11} /> Оператор #{conversation.operator_id}
            </span>
          ) : (
            <span className="assignee-tag assignee-unassigned">
              Свободен
            </span>
          )}
        </div>

        {conversation.ai_confidence > 0 && (
          <span className="queue-ai-conf" title="Уверенность ИИ">
            <Sparkles size={11} /> {Math.round(conversation.ai_confidence * 100)}%
          </span>
        )}
      </div>

      {isUserTyping && (
        <div className="queue-card-typing-banner">
          <span className="typing-dot" />
          <span className="typing-dot" />
          <span className="typing-dot" />
          <span>Клиент печатает...</span>
        </div>
      )}
    </button>
  );
}
