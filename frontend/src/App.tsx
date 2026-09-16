import QuickPeekPage from './pages/QuickPeekPage';

export default function App() {
  return (
    <div className="simple-shell">
      <div className="supergraphic" />
      <main className="main-panel simple-main">
        <header className="page-header">
          <div>
            <p className="eyebrow">Fast batch file preview</p>
            <h1>Quick Peek</h1>
            <p className="muted app-subtitle">
              Search by code, preview files, and open the full view.
            </p>
          </div>
        </header>
        <QuickPeekPage />
      </main>
    </div>
  );
}
