import { useEffect, useState } from 'react';
import { BarChart3, Clock, FileCheck2, Search } from 'lucide-react';
import { api } from '../api';

type Dashboard = {
  totals: { searches: number; opened_previews: number; files_found: number; seconds_saved: number };
  hours_saved: number;
  by_format: Array<{ format: string; events: number; files_found: number; seconds_saved: number }>;
  top_users: Array<{ username: string; events: number; files_found: number; seconds_saved: number }>;
  recent: Array<{ created_at: string; username: string; action: string; format: string; codes_count: number; files_found: number; seconds_saved: number }>;
};

export default function DashboardPage() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState('');
  useEffect(() => { api<Dashboard>('/api/dashboard/summary').then(setData).catch((e) => setError(String(e))); }, []);
  if (error) return <div className="error-box">{error}</div>;
  if (!data) return <div className="panel">Loading dashboard…</div>;

  return (
    <div className="stack">
      <section className="kpi-grid">
        <div className="kpi"><Search /><span>Searches</span><strong>{data.totals.searches}</strong></div>
        <div className="kpi"><FileCheck2 /><span>Files found</span><strong>{data.totals.files_found}</strong></div>
        <div className="kpi"><BarChart3 /><span>Opened previews</span><strong>{data.totals.opened_previews}</strong></div>
        <div className="kpi"><Clock /><span>Estimated hours saved</span><strong>{data.hours_saved}</strong></div>
      </section>

      <section className="panel two-col">
        <div>
          <h2>Usage by format</h2>
          <table><thead><tr><th>Format</th><th>Events</th><th>Files</th><th>Hours saved</th></tr></thead><tbody>
            {data.by_format.map((r) => <tr key={r.format}><td>{r.format?.toUpperCase()}</td><td>{r.events}</td><td>{r.files_found}</td><td>{(r.seconds_saved / 3600).toFixed(2)}</td></tr>)}
          </tbody></table>
        </div>
        <div>
          <h2>Top users</h2>
          <table><thead><tr><th>User</th><th>Events</th><th>Files</th></tr></thead><tbody>
            {data.top_users.map((r) => <tr key={r.username}><td>{r.username || 'Unknown'}</td><td>{r.events}</td><td>{r.files_found}</td></tr>)}
          </tbody></table>
        </div>
      </section>

      <section className="panel">
        <h2>Recent activity</h2>
        <table><thead><tr><th>Time</th><th>User</th><th>Action</th><th>Format</th><th>Codes</th><th>Files</th></tr></thead><tbody>
          {data.recent.map((r, i) => <tr key={i}><td>{new Date(r.created_at).toLocaleString()}</td><td>{r.username}</td><td>{r.action}</td><td>{r.format}</td><td>{r.codes_count}</td><td>{r.files_found}</td></tr>)}
        </tbody></table>
      </section>
    </div>
  );
}
