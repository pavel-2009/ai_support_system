import { Bot, CheckCircle2, Headset, XCircle } from 'lucide-react';
import StatusBadge from '../conversations/StatusBadge';

export default function ConversationHeader({ conversation, currentUser, isOperator, onAssign, onBackToAi, onCloseConversation }) {
  const isClosed = conversation?.status === 'closed';
  const isAssignedToMe = isOperator && conversation?.operator_id === currentUser?.id;
  const isFree = isOperator && !conversation?.operator_id;
  const canWork = !isOperator || isAssignedToMe || currentUser?.role === 'admin';

  return (
    <header className={`chat-area-header ${isOperator ? 'chat-area-header--operator' : ''}`}>
      <div className="chat-details">
        <div className="chat-title-block">
          <span className="chat-area-title">Диалог #{conversation?.id}</span>
          {isOperator && <span className="operator-context"><Headset size={13} />Операторская</span>}
        </div>
        <StatusBadge status={conversation?.status} />
        {conversation?.ai_confidence > 0 && !isOperator && <span className="ai-confidence-pill"><Bot size={13} /> AI {Math.round(conversation.ai_confidence * 100)}%</span>}
      </div>
      {isOperator ? (
        <div className="operator-actions">
          {isFree && !isClosed && <button className="operator-action operator-action--primary" onClick={onAssign}><Headset size={15} />Взять диалог</button>}
          {canWork && !isClosed && <button className="operator-action" onClick={() => onCloseConversation(conversation.id)}><CheckCircle2 size={15} />Закрыть</button>}
          {canWork && !isClosed && <button className="operator-action" onClick={() => onBackToAi(conversation.id)}><Bot size={15} />Вернуть в AI</button>}
        </div>
      ) : (
        !isClosed && <button className="btn-secondary" onClick={() => onCloseConversation(conversation.id)} type="button"><XCircle size={14} />Завершить</button>
      )}
    </header>
  );
}
