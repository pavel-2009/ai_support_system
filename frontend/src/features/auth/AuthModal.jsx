import { useState } from 'react';
import { AlertCircle, Sparkles } from 'lucide-react';
import { api } from '../../services/api';
import AuthForm from './AuthForm';

export default function AuthModal({ onLoginSuccess }) {
  const [mode, setMode] = useState('login');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const authenticate = async ({ email, password, nickname, fullname }) => {
    setError('');
    setLoading(true);
    try {
      if (mode === 'register') await api.register({ email, password, nickname, fullname });
      await api.login(email, password);
      onLoginSuccess(await api.getMe());
    } catch (requestError) {
      setError(requestError.message || 'Ошибка авторизации. Проверьте введенные данные.');
    } finally {
      setLoading(false);
    }
  };

  const demoLogin = async () => {
    const credentials = { email: 'user@example.com', password: 'TestPass123!', nickname: 'user', fullname: 'Demo User' };
    setError('');
    setLoading(true);
    try {
      try { await api.login(credentials.email, credentials.password); }
      catch { await api.register(credentials); await api.login(credentials.email, credentials.password); }
      onLoginSuccess(await api.getMe());
    } catch (requestError) {
      setError(`Не удалось войти: ${requestError.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-overlay">
      <section className="auth-card">
        <header className="auth-header"><div className="auth-logo"><Sparkles size={28} /></div><h1 className="auth-title">AI Support Hub</h1><p className="auth-subtitle">{mode === 'login' ? 'Войдите в аккаунт для начала общения' : 'Создайте аккаунт для доступа к поддержке'}</p></header>
        <div className="auth-tabs">
          <button className={`auth-tab-btn ${mode === 'login' ? 'active' : ''}`} onClick={() => { setMode('login'); setError(''); }} type="button">Вход</button>
          <button className={`auth-tab-btn ${mode === 'register' ? 'active' : ''}`} onClick={() => { setMode('register'); setError(''); }} type="button">Регистрация</button>
        </div>
        {error && <div className="error-banner"><AlertCircle size={18} />{error}</div>}
        <AuthForm loading={loading} mode={mode} onSubmit={authenticate} />
        <div className="demo-login-box"><button className="demo-btn" disabled={loading} onClick={demoLogin} type="button"><Sparkles size={15} />Быстрый демо-вход (user@example.com)</button></div>
      </section>
    </div>
  );
}
