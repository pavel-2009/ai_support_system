import { useState } from 'react';
import { Lock, Mail, User } from 'lucide-react';

export default function AuthForm({ loading, mode, onSubmit }) {
  const [fields, setFields] = useState({ email: '', password: '', nickname: '', fullname: '' });
  const setField = (name) => (event) => setFields((previous) => ({ ...previous, [name]: event.target.value }));
  return (
    <form onSubmit={(event) => { event.preventDefault(); onSubmit(fields); }}>
      <Field icon={Mail} label="Email"><input className="form-input form-input--icon" onChange={setField('email')} placeholder="name@example.com" required type="email" value={fields.email} /></Field>
      {mode === 'register' && <>
        <Field icon={User} label="Никнейм"><input className="form-input form-input--icon" onChange={setField('nickname')} placeholder="alex_dev" required type="text" value={fields.nickname} /></Field>
        <Field label="Полное имя"><input className="form-input" onChange={setField('fullname')} placeholder="Алексей Смирнов" type="text" value={fields.fullname} /></Field>
      </>}
      <Field icon={Lock} label="Пароль"><input className="form-input form-input--icon" onChange={setField('password')} placeholder="••••••••" required type="password" value={fields.password} /></Field>
      <button className="submit-btn" disabled={loading} type="submit">{loading ? 'Обработка...' : mode === 'login' ? 'Войти в систему' : 'Зарегистрироваться'}</button>
    </form>
  );
}

function Field({ children, icon: Icon, label }) {
  return <label className="form-group"><span className="form-label">{label}</span><span className="form-control">{children}{Icon && <Icon className="form-icon" size={16} />}</span></label>;
}
