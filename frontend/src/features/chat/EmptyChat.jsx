import { Bot } from 'lucide-react';

const quickPrompts = [
  'Здравствуйте! Подскажите, как работает поддержка?',
  'У меня вопрос по поводу тарифов и оплаты',
  'Как связаться с живым оператором?',
];

export default function EmptyChat({ onChoosePrompt }) {
  return (
    <div className="empty-chat">
      <div className="empty-icon-halo"><Bot size={34} /></div>
      <h2 className="empty-title">Чем мы можем вам помочь?</h2>
      <p className="empty-subtitle">Напишите ваш вопрос в поле ниже, и наш ИИ-ассистент мгновенно проанализирует обращение и предоставит ответ.</p>
      <div className="prompt-suggestions">
        {quickPrompts.map((prompt) => (
          <button className="prompt-chip" key={prompt} onClick={() => onChoosePrompt(prompt)} type="button">{prompt}</button>
        ))}
      </div>
    </div>
  );
}
