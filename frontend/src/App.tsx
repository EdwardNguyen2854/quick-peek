import { useEffect, useMemo, useState } from 'react';
import { BarChart3, LogOut, Search, Settings, Shield, UserRound } from 'lucide-react';
import { api, setToken } from './api';
import type { User } from './types';
import LoginPage from './pages/LoginPage';
import QuickPeekPage from './pages/QuickPeekPage';
import AdminPage from './pages/AdminPage';
import DashboardPage from './pages/DashboardPage';

export type Page = 'peek' | 'admin' | 'dashboard';

function has(user: User | null, perm: string): boolean {
  return !!user && (user.role === 'admin' || user.permissions.includes(perm as never));
}

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [page, setPage] = useState<Page>('peek');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api<User>('/api/auth/me')
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setLoading(false));
  }, []);

  const title = useMemo(() => {
    if (page === 'admin') return 'Admin';
    if (page === 'dashboard') return 'Dashboard';
    return 'Quick Peek';
  }, [page]);

  if (loading) return <div className="center-screen">Loading Quick Peek…</div>;
  if (!user) return <LoginPage onLogin={(u) => setUser(u)} />;

  return (
    <div className="app-shell">
      <div className="supergraphic" />
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">QP</div>
          <div>
            <strong>Quick Peek</strong>
            <span>CAD file preview</span>
          </div>
        </div>
        <nav>
          <button className={page === 'peek' ? 'active' : ''} onClick={() => setPage('peek')}>
            <Search size={18} /> Preview
          </button>
          {has(user, 'view_dashboard') && (
            <button className={page === 'dashboard' ? 'active' : ''} onClick={() => setPage('dashboard')}>
              <BarChart3 size={18} /> Dashboard
            </button>
          )}
          {has(user, 'manage_users') && (
            <button className={page === 'admin' ? 'active' : ''} onClick={() => setPage('admin')}>
              <Shield size={18} /> Admin
            </button>
          )}
        </nav>
        <div className="sidebar-footer">
          <div className="user-pill"><UserRound size={16} /> {user.username}</div>
          <button className="ghost" onClick={() => { setToken(null); setUser(null); }}>
            <LogOut size={16} /> Log out
          </button>
        </div>
      </aside>

      <main className="main-panel">
        <header className="page-header">
          <div>
            <p className="eyebrow">Professional batch preview</p>
            <h1>{title}</h1>
          </div>
          <div className="header-chip"><Settings size={16} /> White theme</div>
        </header>
        {page === 'peek' && <QuickPeekPage user={user} />}
        {page === 'admin' && <AdminPage />}
        {page === 'dashboard' && <DashboardPage />}
      </main>
    </div>
  );
}
