import { useState } from 'react';

export function LoginForm({ onSubmit }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setError('');
    setIsSubmitting(true);
    try { await onSubmit(email.trim(), password); } catch (requestError) { setError(requestError.message); } finally { setIsSubmitting(false); }
  }

  return <main className="login-page"><form className="login-card" onSubmit={submit}>
    <div className="brand-mark">✦</div><p className="eyebrow">AI SUPPORT</p><h1>Поддержка без лишнего шума.</h1>
    <p className="muted">Войдите, чтобы увидеть свои диалоги и рабочее пространство.</p>
    <label>Почта<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="name@company.ru" required /></label>
    <label>Пароль<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="••••••••" required /></label>
    {error && <p className="form-error" role="alert">{error}</p>}
    <button type="submit" className="primary wide" disabled={isSubmitting}>{isSubmitting ? 'Входим…' : 'Войти'}</button>
    <p className="login-tip">Набор функций определяется ролью учётной записи.</p>
  </form></main>;
}
