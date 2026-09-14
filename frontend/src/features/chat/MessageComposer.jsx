import { useEffect, useRef } from 'react';
import { Send } from 'lucide-react';

export default function MessageComposer({ conversation, inputText, isSending, onChange, onSendMessage }) {
  const textareaRef = useRef(null);
  const isClosed = conversation?.status === 'closed';

  useEffect(() => {
    if (!textareaRef.current) return;
    textareaRef.current.style.height = 'auto';
    textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
  }, [inputText]);

  const send = () => {
    const content = inputText.trim();
    if (!content || isSending || isClosed) return;
    onSendMessage(content);
    onChange('');
  };

  return (
    <div className="chat-input-bar">
      {isClosed ? <p className="closed-conversation-notice">Этот диалог завершен. Создайте новый диалог в боковой панели, чтобы продолжить общение.</p> : (
        <form onSubmit={(event) => { event.preventDefault(); send(); }}>
          <div className="input-container">
            <textarea
              className="chat-textarea"
              disabled={isSending}
              onChange={(event) => onChange(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); send(); }
              }}
              placeholder="Напишите сообщение... (Enter для отправки)"
              ref={textareaRef}
              rows={1}
              value={inputText}
            />
            <button className="send-btn" disabled={!inputText.trim() || isSending} title="Отправить сообщение" type="submit"><Send size={16} /></button>
          </div>
          <div className="input-hints"><span>Enter ↵ — отправить, Shift+Enter — новая строка</span><span>Канал: {conversation?.channel || 'WEB'}</span></div>
        </form>
      )}
    </div>
  );
}
