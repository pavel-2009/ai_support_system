import { useEffect, useRef, useState } from 'react';
import ConversationHeader from './ConversationHeader';
import MessageComposer from './MessageComposer';
import MessageList from './MessageList';

export default function ChatWorkspace({
  conversation,
  isWaitingAi = false,
  isTyping = false,
  typingType = 'operator',
  typingSenderName,
  messages = [],
  messagesLoading = false,
  isSending = false,
  onCloseConversation,
  onSendMessage,
  onTyping,
}) {
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isWaitingAi, isTyping]);

  return (
    <div className="chat-area">
      <ConversationHeader
        conversation={conversation}
        onCloseConversation={onCloseConversation}
      />
      {messagesLoading && messages.length === 0 ? (
        <div className="chat-loading-overlay">
          <div className="spinner-dots">
            <span className="dot" />
            <span className="dot" />
            <span className="dot" />
          </div>
          <span>Загрузка сообщений...</span>
        </div>
      ) : (
        <MessageList
          isTyping={isTyping}
          isWaitingAi={isWaitingAi}
          messages={messages}
          onChoosePrompt={setInputText}
          scrollTargetRef={messagesEndRef}
          typingSenderName={typingSenderName}
          typingType={typingType}
        />
      )}
      <MessageComposer
        conversation={conversation}
        inputText={inputText}
        isSending={isSending}
        onChange={setInputText}
        onSendMessage={onSendMessage}
        onTyping={onTyping}
      />
    </div>
  );
}
