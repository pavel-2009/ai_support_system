import { MessageSquare } from 'lucide-react';

export default function EmptyConversation() {
  return (
    <div className="empty-conversation">
      <MessageSquare size={48} />
      <p>Выберите существующий диалог слева или создайте новый.</p>
    </div>
  );
}
