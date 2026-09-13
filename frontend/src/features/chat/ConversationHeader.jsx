import { Sparkles, XCircle } from 'lucide-react';
import StatusBadge from '../conversations/StatusBadge';

export default function ConversationHeader({ conversation, onCloseConversation }) {
  const isClosed = conversation?.status === 'closed';

  return (
    <header className="chat-area-header">
      <div className="chat-details">
        <span className="chat-area-title">Диалог #{conversation?.id}</span>
        <StatusBadge status={conversation?.status} />
        {conversation?.ai_confidence > 0 && (
          <span className="ai-confidence-pill" title="Уверенность AI модели в ответе">
            <Sparkles size={13} /> AI: {Math.round(conversation.ai_confidence * 100)}%
          </span>
        )}
      </div>
      {!isClosed && (
        <button className="btn-secondary" onClick={() => onCloseConversation(conversation.id)} type="button">
          <XCircle size={14} /> Завершить диалог
        </button>
      )}
    </header>
  );
}
