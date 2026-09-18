import { Bot, CheckCircle, Headphones, UserCheck, XCircle } from 'lucide-react';
import StatusBadge from '../conversations/StatusBadge';

export default function OperatorHeaderActions({
  conversation,
  currentUserId,
  actionLoading,
  onAssign,
  onBackToAi,
  onClose,
}) {
  if (!conversation) return null;

  const isAssignedToMe = conversation.operator_id === currentUserId;
  const isClosed = conversation.status === 'closed';

  return (
    <header className="operator-chat-header">
      <div className="operator-header-main">
        <div className="operator-header-titles">
          <span className="operator-dialog-id">Обращение #{conversation.id}</span>
          <span className="operator-user-info">Клиент #{conversation.user_id}</span>
          <StatusBadge status={conversation.status} />
          <span className={`priority-pill priority-${conversation.priority || 'medium'}`}>
            Приоритет: {(conversation.priority || 'medium').toUpperCase()}
          </span>
        </div>

        <div className="operator-header-buttons">
          {!isClosed && !isAssignedToMe && (
            <button
              className="btn-primary-action"
              disabled={actionLoading}
              onClick={() => onAssign(conversation.id)}
              title="Назначить диалог себе"
              type="button"
            >
              <UserCheck size={14} />
              <span>Взять в работу</span>
            </button>
          )}

          {!isClosed && isAssignedToMe && (
            <>
              <button
                className="btn-secondary-action btn-back-ai"
                disabled={actionLoading}
                onClick={() => onBackToAi(conversation.id)}
                title="Передать диалог обратно ИИ"
                type="button"
              >
                <Bot size={14} />
                <span>Вернуть ИИ</span>
              </button>

              <button
                className="btn-secondary-action btn-close-conv"
                disabled={actionLoading}
                onClick={() => onClose(conversation.id)}
                title="Закрыть обращение"
                type="button"
              >
                <CheckCircle size={14} />
                <span>Завершить</span>
              </button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
