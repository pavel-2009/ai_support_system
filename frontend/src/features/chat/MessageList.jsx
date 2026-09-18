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
      {messages.length === 0 ? (
        <EmptyChat onChoosePrompt={onChoosePrompt} />
      ) : (
        messages.map((message) => (
          <MessageBubble
            key={message.id || `${message.created_at}-${message.content}`}
            message={message}
          />
        ))
      )}
      {isWaitingAi && <TypingIndicator type="ai" />}
      {isTyping && <TypingIndicator senderName={typingSenderName} type={typingType} />}
      <div ref={scrollTargetRef} />
    </div>
  );
}
