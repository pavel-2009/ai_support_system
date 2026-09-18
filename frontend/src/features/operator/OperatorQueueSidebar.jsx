import { useMemo, useState } from 'react';
import { Inbox, RefreshCw, Search } from 'lucide-react';
import OperatorQueueCard from './OperatorQueueCard';

export default function OperatorQueueSidebar({
  queue = [],
  activeConversationId,
  currentUserId,
  loading = false,
  onSelectConversation,
  onRefresh,
  typingUsers = {},
}) {
  const [filter, setFilter] = useState('queue'); // 'queue' | 'my' | 'all'
  const [searchQuery, setSearchQuery] = useState('');

  const filteredQueue = useMemo(() => {
    return queue.filter((item) => {
      // Search filter
      if (searchQuery.trim()) {
        const query = searchQuery.trim().toLowerCase();
        const matchesId = String(item.id).includes(query);
        const matchesUser = String(item.user_id).includes(query);
        if (!matchesId && !matchesUser) return false;
      }

      // Tab filter
      if (filter === 'queue') {
        return item.operator_id === null || item.operator_id === undefined || item.status === 'escalated';
      }
      if (filter === 'my') {
        return item.operator_id === currentUserId;
      }
      return true;
    });
  }, [queue, searchQuery, filter, currentUserId]);

  const queueCounts = useMemo(() => {
    const unassigned = queue.filter(
      (c) => c.operator_id === null || c.operator_id === undefined || c.status === 'escalated',
    ).length;
    const my = queue.filter((c) => c.operator_id === currentUserId).length;
    return { unassigned, my, all: queue.length };
  }, [queue, currentUserId]);

  return (
    <aside className="operator-queue-sidebar">
      <div className="operator-queue-header">
        <div className="queue-header-row">
          <div className="queue-header-title">
            <Inbox size={18} />
            <h2>Очередь диалогов</h2>
          </div>
          <button
            className={`icon-button ${loading ? 'spin' : ''}`}
            onClick={onRefresh}
            title="Обновить очередь"
            type="button"
          >
            <RefreshCw size={15} />
          </button>
        </div>

        <div className="queue-search-container">
          <Search className="search-icon" size={14} />
          <input
            className="queue-search-input"
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Поиск по #ID диалога..."
            type="text"
            value={searchQuery}
          />
        </div>

        <div className="queue-tabs-bar">
          <button
            className={`queue-tab-btn ${filter === 'queue' ? 'active' : ''}`}
            onClick={() => setFilter('queue')}
            type="button"
          >
            В очереди ({queueCounts.unassigned})
          </button>
          <button
            className={`queue-tab-btn ${filter === 'my' ? 'active' : ''}`}
            onClick={() => setFilter('my')}
            type="button"
          >
            Мои ({queueCounts.my})
          </button>
          <button
            className={`queue-tab-btn ${filter === 'all' ? 'active' : ''}`}
            onClick={() => setFilter('all')}
            type="button"
          >
            Все ({queueCounts.all})
          </button>
        </div>
      </div>

      <div className="operator-queue-list">
        {loading && !queue.length ? (
          <div className="queue-empty-state">
            <p>Загрузка очереди...</p>
          </div>
        ) : filteredQueue.length === 0 ? (
          <div className="queue-empty-state">
            <Inbox opacity={0.3} size={36} />
            <p>
              {searchQuery.trim()
                ? 'Диалоги не найдены.'
                : filter === 'my'
                  ? 'У вас нет активных обращений в работе.'
                  : 'Очередь пуста. Все обращения обработаны!'}
            </p>
          </div>
        ) : (
          filteredQueue.map((item) => (
            <OperatorQueueCard
              conversation={item}
              isActive={item.id === activeConversationId}
              isAssignedToMe={item.operator_id === currentUserId}
              isUserTyping={Boolean(typingUsers[item.id]?.isTyping)}
              key={item.id}
              onClick={() => onSelectConversation(item.id)}
            />
          ))
        )}
      </div>
    </aside>
  );
}
