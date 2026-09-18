import { AlertCircle, AlertTriangle, Bot, Check, Clock, Sparkles } from 'lucide-react';

const STATUS_CONFIG = {
  open: {
    label: 'Открыт',
    icon: Sparkles,
  },
  pending_ai: {
    label: 'Обработка ИИ',
    icon: Bot,
  },
  waiting_for_user: {
    label: 'Ждет пользователя',
    icon: Clock,
  },
  waiting_for_operator: {
    label: 'В очереди',
    icon: AlertCircle,
  },
  escalated: {
    label: 'Эскалирован',
    icon: AlertTriangle,
  },
  closed: {
    label: 'Завершен',
    icon: Check,
  },
};

export default function StatusBadge({ status = 'open', showIcon = true }) {
  const normalizedStatus = status?.toLowerCase?.() || 'open';
  const config = STATUS_CONFIG[normalizedStatus] || {
    label: normalizedStatus.replace(/_/g, ' '),
    icon: AlertCircle,
  };

  const IconComponent = config.icon;

  return (
    <span className={`badge badge-${normalizedStatus}`}>
      {showIcon && IconComponent && <IconComponent className="badge-icon" size={11} strokeWidth={2.5} />}
      <span>{config.label}</span>
    </span>
  );
}
