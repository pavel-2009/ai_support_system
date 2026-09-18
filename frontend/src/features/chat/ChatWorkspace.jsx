import { useEffect, useRef, useState } from 'react';
import ConversationHeader from './ConversationHeader';
import MessageComposer from './MessageComposer';
import MessageList from './MessageList';

export default function ChatWorkspace(props) {
  const { conversation, currentUser, isOperator, isWaitingAi, messages } = props;
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef(null);
  const previousConversationId = useRef(null);

  useEffect(() => {
    const changed = previousConversationId.current !== conversation.id;
    previousConversationId.current = conversation.id;
    if (changed) setInputText('');
    // Do not animate or smooth-scroll when switching conversations.
    messagesEndRef.current?.scrollIntoView({ behavior: 'auto', block: 'end' });
  }, [conversation.id]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'auto', block: 'end' });
  }, [messages.length, isWaitingAi]);

  return (
    <div className={`chat-area ${isOperator ? 'chat-area--operator' : ''}`}>
      <ConversationHeader
        conversation={conversation} currentUser={currentUser} isOperator={isOperator}
        onAssign={props.onAssign} onBackToAi={props.onBackToAi} onCloseConversation={props.onCloseConversation}
      />
      <MessageList isWaitingAi={isWaitingAi} messages={messages} onChoosePrompt={setInputText} scrollTargetRef={messagesEndRef} />
      <MessageComposer
        conversation={conversation} currentUser={currentUser} isOperator={isOperator}
        inputText={inputText} isSending={props.isSending} onChange={setInputText} onSendMessage={props.onSendMessage}
      />
    </div>
  );
}
