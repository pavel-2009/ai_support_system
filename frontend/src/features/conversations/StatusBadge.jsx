const labels = {
  open: 'Открыт',
  waiting_for_user: 'Ждет ответа',
  waiting_for_operator: 'В очереди к оператору',
  escalated: 'Эскалирован',
  closed: 'Завершен',
};

export default function StatusBadge({ status = 'open' }) {
  return <span className={`badge badge-${status}`}>{labels[status] || status}</span>;
}
