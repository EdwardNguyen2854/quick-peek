import { Boxes } from 'lucide-react';
import QuickPeekPage from './pages/QuickPeekPage';

export default function App() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark"><Boxes size={17} strokeWidth={1.8} /></span>
          <div>
            <strong>Quick Peek</strong>
            <span>Engineering file preview</span>
          </div>
        </div>
        <span className="topbar-status">Local workspace</span>
      </header>

      <main className="workspace">
        <QuickPeekPage />
      </main>
    </div>
  );
}
