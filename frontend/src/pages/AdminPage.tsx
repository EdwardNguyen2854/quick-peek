import { FormEvent, useEffect, useState } from 'react';
import { RefreshCcw, Save, UserPlus } from 'lucide-react';
import { api } from '../api';
import type { Permission, User } from '../types';

export default function AdminPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [message, setMessage] = useState('');
  const [form, setForm] = useState({ username: '', password: '', role: 'user' as 'user' | 'admin' });

  async function load() {
    const [u, p] = await Promise.all([
      api<{ users: User[] }>('/api/admin/users'),
      api<{ available_permissions: Permission[] }>('/api/admin/permissions')
    ]);
    setUsers(u.users); setPermissions(p.available_permissions);
  }
  useEffect(() => { load().catch((e) => setMessage(String(e))); }, []);

  async function create(e: FormEvent) {
    e.preventDefault();
    await api('/api/admin/users', {
      method: 'POST',
      body: JSON.stringify({ ...form, permissions: form.role === 'admin' ? permissions : ['use_quick_peek', 'view_step', 'view_pdf', 'view_dxf', 'view_obj'], is_active: true })
    });
    setForm({ username: '', password: '', role: 'user' });
    setMessage('User created');
    await load();
  }

  async function updateUser(user: User, changes: Partial<User>) {
    await api(`/api/admin/users/${user.id}`, { method: 'PUT', body: JSON.stringify(changes) });
    setMessage('User updated');
    await load();
  }

  async function reindex() {
    const res = await api<{ indexed: number; roots: number }>('/api/admin/reindex', { method: 'POST' });
    setMessage(`Indexed ${res.indexed} files from ${res.roots} root(s)`);
  }

  return (
    <div className="stack">
      <section className="panel admin-toolbar">
        <form onSubmit={create} className="create-user-form">
          <input placeholder="Username" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} required />
          <input placeholder="Password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required />
          <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as 'user' | 'admin' })}>
            <option value="user">User</option>
            <option value="admin">Admin</option>
          </select>
          <button className="primary"><UserPlus size={16} /> Create user</button>
        </form>
        <button className="secondary" onClick={reindex}><RefreshCcw size={16} /> Reindex files</button>
        {message && <div className="success-box">{message}</div>}
      </section>

      <section className="panel">
        <h2>User management</h2>
        <div className="table-wrap">
          <table>
            <thead><tr><th>User</th><th>Role</th><th>Active</th><th>Permissions</th><th>Save</th></tr></thead>
            <tbody>
              {users.map((u) => <UserRow key={u.id} user={u} permissions={permissions} onSave={updateUser} />)}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function UserRow({ user, permissions, onSave }: { user: User; permissions: Permission[]; onSave: (u: User, c: Partial<User>) => Promise<void> }) {
  const [role, setRole] = useState(user.role);
  const [active, setActive] = useState(user.is_active);
  const [perms, setPerms] = useState<Permission[]>(user.permissions);

  function toggle(p: Permission) {
    setPerms((old) => old.includes(p) ? old.filter((x) => x !== p) : [...old, p]);
  }

  return (
    <tr>
      <td><strong>{user.username}</strong><span className="muted-block">Last login: {user.last_login_at || 'never'}</span></td>
      <td><select value={role} onChange={(e) => setRole(e.target.value as 'user' | 'admin')}><option value="user">User</option><option value="admin">Admin</option></select></td>
      <td><input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} /></td>
      <td>
        <div className="permission-list">
          {permissions.map((p) => <label key={p}><input type="checkbox" checked={perms.includes(p)} onChange={() => toggle(p)} /> {p}</label>)}
        </div>
      </td>
      <td><button className="secondary small" onClick={() => onSave(user, { role, is_active: active, permissions: perms })}><Save size={15} /> Save</button></td>
    </tr>
  );
}
