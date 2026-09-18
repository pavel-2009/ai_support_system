import { Activity, Flame, Headphones, Inbox, Wifi, WifiOff } from 'lucide-react';

export default function OperatorStatsBar({
  totalQueueCount = 0,
  myActiveCount = 0,
  escalatedCount = 0,
  maxLoad = 5,
  wsStatus = 'connected',
}) {
  const loadPercentage = Math.min(Math.round((myActiveCount / maxLoad) * 100), 100);

  return (
    <div className="operator-stats-bar">
      <div className="stats-group">
        <div className="stat-item" title="Всего обращений, ожидающих ответа оператора">
          <Inbox className="stat-icon" size={16} />
          <span className="stat-label">В очереди:</span>
          <span className="stat-value">{totalQueueCount}</span>
        </div>

        <div className="stat-divider" />

        <div className="stat-item" title="Обращения, назначенные на вас">
          <Headphones className="stat-icon" size={16} />
          <span className="stat-label">Мои активные:</span>
          <span className="stat-value">{myActiveCount}</span>
        </div>

        <div className="stat-divider" />

        {escalatedCount > 0 && (
          <>
            <div className="stat-item stat-item--escalated" title="Срочные эскалированные обращения">
              <Flame className="stat-icon stat-icon--flame" size={16} />
              <span className="stat-label">Эскалации:</span>
              <span className="stat-value">{escalatedCount}</span>
            </div>
            <div className="stat-divider" />
          </>
        )}

        <div className="stat-item stat-item--load" title={`Текущая нагрузка: ${myActiveCount} из ${maxLoad}`}>
          <Activity className="stat-icon" size={16} />
          <span className="stat-label">Загрузка:</span>
          <div className="load-meter-track">
            <div
              className={`load-meter-fill ${myActiveCount >= maxLoad ? 'full' : ''}`}
              style={{ width: `${loadPercentage}%` }}
            />
          </div>
          <span className="stat-value load-ratio">
            {myActiveCount}/{maxLoad}
          </span>
        </div>
      </div>

      <div className="ws-status-indicator" title={`WebSocket статус: ${wsStatus}`}>
        {wsStatus === 'connected' ? (
          <>
            <Wifi className="ws-icon ws-icon--online" size={14} />
            <span className="ws-text ws-text--online">WS Онлайн</span>
          </>
        ) : wsStatus === 'connecting' ? (
          <>
            <Wifi className="ws-icon ws-icon--connecting spin" size={14} />
            <span className="ws-text ws-text--connecting">Подключение...</span>
          </>
        ) : (
          <>
            <WifiOff className="ws-icon ws-icon--offline" size={14} />
            <span className="ws-text ws-text--offline">WS Офлайн</span>
          </>
        )}
      </div>
    </div>
  );
}
