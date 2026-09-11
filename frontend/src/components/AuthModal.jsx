import React, { useState } from 'react';
import { LogIn, UserPlus, Sparkles, AlertCircle, Mail, Lock, User } from 'lucide-react';
import { api } from '../services/api';

export default function AuthModal({ onLoginSuccess }) {
  const [mode, setMode] = useState('login'); // 'login' | 'register'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [nickname, setNickname] = useState('');
  const [fullname, setFullname] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e?.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (mode === 'register') {
        await api.register({ email, password, nickname, fullname });
        // After registration, log in immediately
        await api.login(email, password);
      } else {
        await api.login(email, password);
      }
      const user = await api.getMe();
      onLoginSuccess(user);
    } catch (err) {
      setError(err.message || 'Ошибка авторизации. Проверьте введенные данные.');
    } finally {
      setLoading(false);
    }
  };

  const handleDemoLogin = async (demoEmail, demoPassword) => {
    setError('');
    setLoading(true);
    try {
      await api.login(demoEmail, demoPassword);
      const user = await api.getMe();
      onLoginSuccess(user);
    } catch (err) {
      // If demo user doesn't exist yet, try to register it first!
      try {
        await api.register({
          email: demoEmail,
          password: demoPassword,
          nickname: demoEmail.split('@')[0],
          fullname: 'Demo User',
        });
        await api.login(demoEmail, demoPassword);
        const user = await api.getMe();
        onLoginSuccess(user);
      } catch (regErr) {
        setError(`Не удалось войти: ${err.message}`);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-overlay">
      <div className="auth-card">
        <div className="auth-header">
          <div style={{ display: 'inline-flex', padding: 10, borderRadius: '50%', background: 'rgba(99, 102, 241, 0.15)', color: '#818cf8', marginBottom: 12 }}>
            <Sparkles size={28} />
          </div>
          <h2 className="auth-title">AI Support Hub</h2>
          <p className="auth-subtitle">
            {mode === 'login' ? 'Войдите в аккаунт для начала общения' : 'Создайте аккаунт для доступа к поддержке'}
          </p>
        </div>

        <div className="auth-tabs">
          <button
            className={`auth-tab-btn ${mode === 'login' ? 'active' : ''}`}
            onClick={() => { setMode('login'); setError(''); }}
            type="button"
          >
            Вход
          </button>
          <button
            className={`auth-tab-btn ${mode === 'register' ? 'active' : ''}`}
            onClick={() => { setMode('register'); setError(''); }}
            type="button"
          >
            Регистрация
          </button>
        </div>

        {error && (
          <div className="error-banner">
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Email</label>
            <div style={{ position: 'relative' }}>
              <input
                className="form-input"
                style={{ width: '100%', paddingLeft: 36 }}
                type="email"
                required
                placeholder="name@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
              <Mail size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            </div>
          </div>

          {mode === 'register' && (
            <>
              <div className="form-group">
                <label className="form-label">Никнейм</label>
                <div style={{ position: 'relative' }}>
                  <input
                    className="form-input"
                    style={{ width: '100%', paddingLeft: 36 }}
                    type="text"
                    required
                    placeholder="alex_dev"
                    value={nickname}
                    onChange={(e) => setNickname(e.target.value)}
                  />
                  <User size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                </div>
              </div>
              <div className="form-group">
                <label className="form-label">Полное имя</label>
                <input
                  className="form-input"
                  type="text"
                  placeholder="Алексей Смирнов"
                  value={fullname}
                  onChange={(e) => setFullname(e.target.value)}
                />
              </div>
            </>
          )}

          <div className="form-group">
            <label className="form-label">Пароль</label>
            <div style={{ position: 'relative' }}>
              <input
                className="form-input"
                style={{ width: '100%', paddingLeft: 36 }}
                type="password"
                required
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <Lock size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            </div>
          </div>

          <button className="submit-btn" type="submit" disabled={loading}>
            {loading ? 'Обработка...' : mode === 'login' ? 'Войти в систему' : 'Зарегистрироваться'}
          </button>
        </form>

        <div className="demo-login-box">
          <button
            type="button"
            className="demo-btn"
            onClick={() => handleDemoLogin('user@example.com', 'TestPass123!')}
            disabled={loading}
          >
            <Sparkles size={15} color="#818cf8" />
            Быстрый демо-вход (user@example.com)
          </button>
        </div>
      </div>
    </div>
  );
}
