import React, { useState } from 'react';
import { Plus, MessageSquare, LogOut, CheckCircle2, AlertCircle, Clock, Search } from 'lucide-react';

export default function ChatSidebar({
  conversations = [],
  activeConversationId,
  onSelectConversation,
  onCreateConversation,
  currentUser,
  onLogout,
  loading = false,
}) {
  const [filter, setFilter] = useState('all'); // 'all' | 'open' | 'closed'
  const [searchTerm, setSearchTerm] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [newPriority, setNewPriority] = useState('medium');

  const filteredConversations = conversations.filter((conv) => {
    // Status filter
    if (filter === 'open' && conv.status === 'closed') return false;
    if (filter === 'closed' && conv.status !== 'closed') return false;
    // Search filter
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase();
      const matchId = String(conv.id).includes(term);
      const matchStatus = (conv.status || '').toLowerCase().includes(term);
      return matchId || matchStatus;
    }
    return true;
  });

  const handleCreateSubmit = async (e) => {
    e?.preventDefault();
    setIsCreating(true);
    try {
      await onCreateConversation(newPriority);
    } finally {
      setIsCreating(false);
    }
  };

  const formatTimestamp = (dateStr) => {
    if (!dateStr) return '';
    try {
      const date = new Date(dateStr);
      const now = new Date();
      const isToday = date.toDateString() === now.toDateString();
      if (isToday) {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      }
      return date.toLocaleDateString([], { day: 'numeric', month: 'short' });
    } catch {
      return '';
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'open':
        return <span className="badge badge-open">Открыт</span>;
      case 'waiting_for_user':
        return <span className="badge badge-waiting_for_user">Ждет вас</span>;
      case 'waiting_for_operator':
        return <span className="badge badge-waiting_for_operator">Оператор</span>;
      case 'escalated':
        return <span className="badge badge-escalated">Эскалирован</span>;
      case 'closed':
        return <span className="badge badge-closed">Закрыт</span>;
      default:
        return <span className="badge badge-open">{status}</span>;
    }
  };

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <button
          className="new-chat-btn"
          onClick={handleCreateSubmit}
          disabled={isCreating}
          type="button"
        >
          <Plus size={18} strokeWidth={2.5} />
          <span>{isCreating ? 'Создание...' : 'Новый диалог'}</span>
        </button>

        <div className="filter-bar">
          <button
            className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
            onClick={() => setFilter('all')}
            type="button"
          >
            Все ({conversations.length})
          </button>
          <button
            className={`filter-btn ${filter === 'open' ? 'active' : ''}`}
            onClick={() => setFilter('open')}
            type="button"
          >
            Активные
          </button>
          <button
            className={`filter-btn ${filter === 'closed' ? 'active' : ''}`}
            onClick={() => setFilter('closed')}
            type="button"
          >
            Закрытые
          </button>
        </div>
      </div>

      <div className="chat-list">
        {loading && conversations.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '30px 10px', color: 'var(--text-muted)', fontSize: 13 }}>
            Загрузка диалогов...
          </div>
        ) : filteredConversations.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px 16px', color: 'var(--text-muted)', fontSize: 13 }}>
            <MessageSquare size={32} style={{ opacity: 0.3, margin: '0 auto 10px' }} />
            {conversations.length === 0
              ? 'У вас пока нет диалогов. Нажмите «Новый диалог», чтобы начать.'
              : 'Нет диалогов, соответствующих фильтру.'}
          </div>
        ) : (
          filteredConversations.map((conv) => {
            const isActive = conv.id === activeConversationId;
            return (
              <div
                key={conv.id}
                className={`chat-item ${isActive ? 'active' : ''}`}
                onClick={() => onSelectConversation(conv.id)}
              >
                <div className="chat-item-header">
                  <span className="chat-title">
                    <span className={`priority-indicator priority-${conv.priority || 'medium'}`} />
                    Диалог #{conv.id}
                  </span>
                  <span className="chat-time">
                    {formatTimestamp(conv.updated_at || conv.created_at)}
                  </span>
                </div>

                <div className="chat-item-footer">
                  {getStatusBadge(conv.status)}
                  <span style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'capitalize' }}>
                    {conv.channel || 'web'}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>

      <div className="sidebar-footer">
        <div className="user-profile-info">
          <div className="avatar-circle">
            {(currentUser?.nickname || currentUser?.email || 'U')[0].toUpperCase()}
          </div>
          <div className="user-meta">
            <span className="user-name" title={currentUser?.email}>
              {currentUser?.nickname || currentUser?.email}
            </span>
            <span className="user-role-badge">
              {currentUser?.role || 'Пользователь'}
            </span>
          </div>
        </div>

        <button
          className="icon-button"
          onClick={onLogout}
          title="Выйти из аккаунта"
          type="button"
        >
          <LogOut size={16} />
        </button>
      </div>
    </div>
  );
}
