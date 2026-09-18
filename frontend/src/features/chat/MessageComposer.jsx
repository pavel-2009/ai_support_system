import { useEffect, useRef } from 'react';
import { Send } from 'lucide-react';

export default function MessageComposer({
  conversation,
  inputText,
  isSending,
  onChange,
  onSendMessage,
  onTyping,
  placeholder = 'Напишите сообщение... (Enter для отправки)',
  channelBadge = null,
}) {
  const textareaRef = useRef(null);
  const typingTimeoutRef = useRef(null);
  const isClosed = conversation?.status === 'closed';

  useEffect(() => {
    if (!textareaRef.current) return;
    textareaRef.current.style.height = 'auto';
    textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 140)}px`;
  }, [inputText]);

  const handleInputChange = (event) => {
    const text = event.target.value;
    onChange(text);

    if (onTyping) {
      onTyping(true);
      if (typingTimeoutRef.current) clearTimeout(typingTimeoutRef.current);
      typingTimeoutRef.current = setTimeout(() => {
        onTyping(false);
      }, 2000);
    }
  };

  const send = () => {
    const content = inputText.trim();
    if (!content || isSending || isClosed) return;
    if (onTyping) {
      if (typingTimeoutRef.current) clearTimeout(typingTimeoutRef.current);
      onTyping(false);
    }
    onSendMessage(content);
    onChange('');
  };

  return (
    <div className="chat-input-bar">
      {isClosed ? (
        <p className="closed-conversation-notice">
          Этот диалог завершен. Создайте новый диалог в боковой панели, чтобы продолжить общение.
        </p>
      ) : (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            send();
          }}
        >
          <div className="input-container">
            <textarea
              className="chat-textarea"
              disabled={isSending}
              onChange={handleInputChange}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault();
                  send();
                }
              }}
              placeholder={placeholder}
              ref={textareaRef}
              rows={1}
              value={inputText}
            />
            <button
              className="send-btn"
              disabled={!inputText.trim() || isSending}
              title="Отправить сообщение"
              type="submit"
            >
              <Send size={16} />
            </button>
          </div>
          <div className="input-hints">
            <span>Enter ↵ — отправить, Shift+Enter — новая строка</span>
            <span>Канал: {channelBadge || conversation?.channel?.toUpperCase() || 'WEB'}</span>
          </div>
        </form>
      )}
    </div>
  );
}
