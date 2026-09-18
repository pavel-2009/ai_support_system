import { useState } from 'react';
import { MessageSquarePlus, Sparkles } from 'lucide-react';

const CANNED_RESPONSES = [
  {
    label: 'Приветствие',
    text: 'Здравствуйте! Я подключился к диалогу и готов вам помочь. Опишите, пожалуйста, подробнее возникшую проблему.',
  },
  {
    label: 'Уточнение деталей',
    text: 'Уточните, пожалуйста, номер вашего заказа, аккаунта или точный текст сообщения об ошибке.',
  },
  {
    label: 'Проверка данных',
    text: 'Минуту, пожалуйста, я проверяю информацию в системе и скоро вернусь к вам с ответом.',
  },
  {
    label: 'Вопрос решен',
    text: 'Мы устранили проблему. Подскажите, пожалуйста, всё ли теперь работает корректно и остались ли еще вопросы?',
  },
  {
    label: 'Возврат в ИИ',
    text: 'Я ответил на ваш вопрос и возвращаю диалог нашему автоматическому AI-ассистенту. При необходимости оператор всегда сможет снова подключиться.',
  },
];

export default function QuickResponsesBar({ onSelectResponse }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="quick-responses-wrapper">
      <div className="quick-responses-header">
        <button
          className={`quick-responses-toggle ${isOpen ? 'active' : ''}`}
          onClick={() => setIsOpen((prev) => !prev)}
          type="button"
        >
          <MessageSquarePlus size={14} />
          <span>Быстрые шаблоны ответов</span>
          <Sparkles className="sparkle-icon" size={12} />
        </button>
      </div>

      {isOpen && (
        <div className="quick-responses-chips">
          {CANNED_RESPONSES.map((item) => (
            <button
              className="canned-chip-btn"
              key={item.label}
              onClick={() => {
                onSelectResponse(item.text);
              }}
              title={item.text}
              type="button"
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
