import { createContext, useCallback, useContext, useState } from 'react';
import { AlertCircle, ArrowRight, CheckCircle2, Flame, Info, X } from 'lucide-react';

const ToastContext = createContext(null);

export function useToasts() {
  const context = useContext(ToastContext);
  if (!context) {
    return {
      addToast: () => {},
      removeToast: () => {},
      playNotificationSound: () => {},
    };
  }
  return context;
}

// Gentle audio chime using Web Audio API
function playChime() {
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return;
    const ctx = new AudioContext();

    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = 'sine';
    // Two-tone chord
    osc.frequency.setValueAtTime(587.33, ctx.currentTime); // D5
    osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.12); // A5

    gain.gain.setValueAtTime(0.08, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.35);

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start();
    osc.stop(ctx.currentTime + 0.36);
  } catch {
    // Audio may be blocked by browser autoplay policy
  }
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const addToast = useCallback(({ title, message, type = 'info', actionLabel, onAction, sound = true }) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;

    if (sound) {
      playChime();
    }

    setToasts((prev) => [...prev, { id, title, message, type, actionLabel, onAction }]);

    // Auto dismiss after 6 seconds
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 6000);

    return id;
  }, []);

  return (
    <ToastContext.Provider value={{ addToast, removeToast, playNotificationSound: playChime }}>
      {children}
      <div className="toast-container">
        {toasts.map((toast) => (
          <ToastItem key={toast.id} onRemove={() => removeToast(toast.id)} toast={toast} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function ToastItem({ toast, onRemove }) {
  const getIcon = () => {
    switch (toast.type) {
      case 'escalation':
        return <Flame className="toast-icon toast-icon-escalation" size={18} />;
      case 'success':
        return <CheckCircle2 className="toast-icon toast-icon-success" size={18} />;
      case 'warning':
        return <AlertCircle className="toast-icon toast-icon-warning" size={18} />;
      case 'info':
      default:
        return <Info className="toast-icon toast-icon-info" size={18} />;
    }
  };

  return (
    <div className={`toast-card toast-${toast.type || 'info'}`}>
      <div className="toast-content">
        <div className="toast-header">
          {getIcon()}
          <span className="toast-title">{toast.title}</span>
          <button className="toast-close-btn" onClick={onRemove} title="Закрыть" type="button">
            <X size={14} />
          </button>
        </div>
        {toast.message && <p className="toast-message">{toast.message}</p>}
        {toast.actionLabel && toast.onAction && (
          <button
            className="toast-action-btn"
            onClick={() => {
              toast.onAction();
              onRemove();
            }}
            type="button"
          >
            <span>{toast.actionLabel}</span>
            <ArrowRight size={13} />
          </button>
        )}
      </div>
    </div>
  );
}
