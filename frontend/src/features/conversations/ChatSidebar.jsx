import { Headset, KeyRound, LogOut, MessageSquare, Plus } from 'lucide-react';
import { useMemo, useState } from 'react';
import { formatConversationTimestamp } from '../../utils/date';
import StatusBadge from './StatusBadge';

const userFilters = [{ id: 'all', label: 'Все' }, { id: 'open', label: 'Активные' }, { id: 'closed', label: 'Закрытые' }];

export default function ChatSidebar({
  activeConversationId, conversations, currentUser, isOperator, loading,
  onCreateConversation, onLogout, onManageSessions, onSelectConversation,
}) {
  const [filter, setFilter] = useState('all');
  const filteredConversations = useMemo(() => conversations.filter((conversation) => {
    if (isOperator) return filter === 'closed' ? conversation.status === 'closed' : conversation.status !== 'closed';
    if (filter === 'open') return conversation.status !== 'closed';
    if (filter === 'closed') return conversation.status === 'closed';
    return true;
  }), [conversations, filter, isOperator]);

  return (
    <aside className={`sidebar ${isOperator ? 'sidebar--operator' : ''}`}>
      <div className="sidebar-header">
        {isOperator ? (
          <div className="operator-desk-title"><Headset size={18} /><div><strong>Операторская</strong><span>Очередь обращений</span></div></div>
        ) : (
          <button className="new-chat-btn" type="button" onClick={() => onCreateConversation()}><Plus size={18} strokeWidth={2.5} />Новый диалог</button>
        )}
        <div className="filter-bar">
          {(isOperator ? [{ id: 'all', label: 'Все' }, { id: 'open', label: 'В работе' }, { id: 'closed', label: 'Закрытые' }] : userFilters)
            .map(({ id, label }) => <button className={`filter-btn ${filter === id ? 'active' : ''}`} key={id} onClick={() => setFilter(id)} type="button">{label}</button>)}
        </div>
      </div>
      <div className="chat-list">
        {loading && !conversations.length ? <p className="sidebar-empty">Загрузка...</p> : filteredConversations.length ? filteredConversations.map((conversation) => {
          const assignedToMe = isOperator && conversation.operator_id === currentUser.id;
          return (
            <button className={`chat-item ${conversation.id === activeConversationId ? 'active' : ''}`} key={conversation.id} onClick={() => onSelectConversation(conversation.id)} type="button">
              <span className="chat-item-header">
                <span className="chat-title"><span className={`priority-indicator priority-${conversation.priority || 'medium'}`} />Диалог #{conversation.id}</span>
                <span className="chat-time">{formatConversationTimestamp(conversation.updated_at || conversation.created_at)}</span>
              </span>
              <span className="chat-item-footer">
                <StatusBadge status={conversation.status} />
                {isOperator ? <span className={`assignment-label ${assignedToMe ? 'mine' : ''}`}>{assignedToMe ? 'Мой' : 'Свободен'}</span> : <span className="chat-channel">{conversation.channel || 'web'}</span>}
              </span>
            </button>
          );
        }) : <div className="sidebar-empty"><MessageSquare size={32} />Нет диалогов.</div>}
      </div>
      <footer className="sidebar-footer">
        <div className="user-profile-info">
          <div className="avatar-circle">{(currentUser?.nickname || currentUser?.email || 'U')[0].toUpperCase()}</div>
          <div className="user-meta"><span className="user-name" title={currentUser?.email}>{currentUser?.nickname || currentUser?.email}</span><span className="user-role-badge">{isOperator ? 'Оператор' : (currentUser?.role || 'Пользователь')}</span></div>
        </div>
        <div className="user-actions">
          <button className="icon-button" onClick={onManageSessions} title="Управление сессиями" type="button"><KeyRound size={16} /></button>
          <button className="icon-button" onClick={onLogout} title="Выйти из аккаунта" type="button"><LogOut size={16} /></button>
        </div>
      </footer>
    </aside>
  );
}
