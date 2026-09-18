import { useEffect, useState } from 'react';
import { statusLabels } from './ConversationList';

export function AdminDashboard({ api, conversations }) {
  const [users, setUsers] = useState([]); const [error, setError] = useState('');
  useEffect(() => { api.users().then(setUsers).catch((requestError) => setError(requestError.message)); }, [api]);
  const open = conversations.filter((item) => item.status !== 'closed'); const escalated = conversations.filter((item) => item.status === 'escalated');
  const avgConfidence = conversations.length ? Math.round(conversations.reduce((sum, item) => sum + item.ai_confidence, 0) / conversations.length * 100) : 0;
  const averageWait = open.length ? Math.round(open.reduce((sum, item) => sum + (Date.now() - new Date(item.created_at)), 0) / open.length / 60000) : 0;
  const metrics = [['Активные обращения', open.length, 'в работе сейчас'], ['Эскалации', escalated.length, `${conversations.length ? Math.round(escalated.length / conversations.length * 100) : 0}% от всех`], ['Среднее ожидание', `${averageWait} мин`, 'по открытым обращениям'], ['Операторы', users.filter((item) => item.role === 'operator').length, 'доступно в системе']];
  return <main className="dashboard"><header><p className="eyebrow">ADMIN DASHBOARD</p><h1>Пульс поддержки</h1><p className="muted">Сводка по очереди, команде и качеству AI.</p></header>{error && <p className="form-error">{error}</p>}<section className="metric-grid">{metrics.map(([label, value, hint]) => <article className="metric" key={label}><span>{label}</span><strong>{value}</strong><small>{hint}</small></article>)}</section><section className="dashboard-grid"><article className="panel"><h3>Статусы обращений</h3>{Object.entries(statusLabels).map(([status, label]) => { const count = conversations.filter((item) => item.status === status).length; return <div className="bar-row" key={status}><span>{label}</span><div><i style={{ width: `${conversations.length ? count / conversations.length * 100 : 0}%` }} /></div><b>{count}</b></div>; })}</article><article className="panel"><h3>Контроль AI</h3><div className="quality"><strong>{avgConfidence}%</strong><span>средняя уверенность AI</span></div><p className="muted">Высокая доля эскалаций и растущее ожидание — повод проверить сценарии и ответы модели.</p></article></section></main>;
}
