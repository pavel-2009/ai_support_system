import { useEffect, useRef, useState } from 'react';
import ConversationHeader from './ConversationHeader';
import MessageComposer from './MessageComposer';
import MessageList from './MessageList';

export default function ChatWorkspace(props) {
  const { conversation, isWaitingAi, messages } = props;
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isWaitingAi]);

  return (
    <div className="chat-area">
      <ConversationHeader conversation={conversation} onCloseConversation={props.onCloseConversation} />
      <MessageList
        isWaitingAi={isWaitingAi}
        messages={messages}
        onChoosePrompt={setInputText}
        scrollTargetRef={messagesEndRef}
      />
      <MessageComposer
        conversation={conversation}
        inputText={inputText}
        isSending={props.isSending}
        onChange={setInputText}
        onSendMessage={props.onSendMessage}
      />
    </div>
  );
}
