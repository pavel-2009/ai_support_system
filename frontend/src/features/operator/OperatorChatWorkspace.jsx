import { useEffect, useRef, useState } from 'react';
import { Headphones, Lock } from 'lucide-react';
import MessageComposer from '../chat/MessageComposer';
import MessageList from '../chat/MessageList';
import OperatorHeaderActions from './OperatorHeaderActions';
import QuickResponsesBar from './QuickResponsesBar';

export default function OperatorChatWorkspace({
  conversation,
  currentUserId,
  messages = [],
  messagesLoading = false,
  actionLoading = false,
  isUserTyping = false,
  userTypingName = 'Клиент',
  onAssign,
  onBackToAi,
  onClose,
  onReply,
  onTyping,
}) {
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isUserTyping]);

  if (!conversation) {
    return (
      <div className="operator-chat-empty">
        <Headphones opacity={0.3} size={48} />
        <h3>Выберите диалог из очереди</h3>
        <p>Выберите обращение слева, чтобы ознакомиться с историей и подключиться к переписке.</p>
      </div>
    );
  }

  const isAssignedToMe = conversation.operator_id === currentUserId;
  const isClosed = conversation.status === 'closed';

  const handleSelectQuickResponse = (text) => {
    setInputText((prev) => (prev ? `${prev} ${text}` : text));
  };

  return (
    <div className="operator-chat-area">
      <OperatorHeaderActions
        actionLoading={actionLoading}
        conversation={conversation}
        currentUserId={currentUserId}
        onAssign={onAssign}
        onBackToAi={onBackToAi}
        onClose={onClose}
      />

      {messagesLoading && messages.length === 0 ? (
        <div className="chat-loading-overlay">
          <div className="spinner-dots">
            <span className="dot" />
            <span className="dot" />
            <span className="dot" />
          </div>
          <span>Загрузка истории диалога...</span>
        </div>
      ) : (
        <MessageList
          isTyping={isUserTyping}
          isWaitingAi={false}
          messages={messages}
          onChoosePrompt={setInputText}
          scrollTargetRef={messagesEndRef}
          typingSenderName={userTypingName}
          typingType="user"
        />
      )}

      {!isClosed && !isAssignedToMe ? (
        <div className="unassigned-chat-notice">
          <Lock size={18} />
          <div>
            <h4>Диалог не назначен вам</h4>
            <p>Чтобы ответить клиенту, нажмите кнопку «Взять в работу» в верхней панели.</p>
          </div>
        </div>
      ) : (
        <div className="operator-composer-section">
          {!isClosed && <QuickResponsesBar onSelectResponse={handleSelectQuickResponse} />}
          <MessageComposer
            channelBadge={conversation.channel}
            conversation={conversation}
            inputText={inputText}
            isSending={actionLoading}
            onChange={setInputText}
            onSendMessage={(text) => onReply(conversation.id, text)}
            onTyping={onTyping}
            placeholder="Напишите ответ клиенту от имени оператора... (Enter для отправки)"
          />
        </div>
      )}
    </div>
  );
}
