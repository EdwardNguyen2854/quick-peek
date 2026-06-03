import { FileSearch, FolderOpen, Shield, Zap } from 'lucide-react';

const features = [
  {
    icon: <FileSearch size={22} />,
    title: 'Batch code-based search',
    desc: 'Enter multiple part numbers or codes at once. Quick Peek finds matching CAD files across your configured roots.',
  },
  {
    icon: <FolderOpen size={22} />,
    title: 'Flexible folder scopes',
    desc: 'Search in a specific working folder, or fall back to all configured backend roots. Save folder presets for quick access.',
  },
  {
    icon: <Zap size={22} />,
    title: 'Multi-format preview',
    desc: 'Preview STEP, PDF, DXF, and OBJ files directly in the browser. 3D STEP files get a GLB thumbnail via FreeCAD conversion.',
  },
  {
    icon: <Shield size={22} />,
    title: 'Role-based access',
    desc: 'Admin controls which users can view which formats. Permissions are per-format: view_step, view_pdf, view_dxf, view_obj.',
  },
];

const specs = [
  { label: 'Backend', value: 'FastAPI + SQLite' },
  { label: 'Frontend', value: 'React + Vite + TypeScript' },
  { label: 'Auth', value: 'JWT Bearer tokens' },
  { label: '3D Preview', value: 'STEP → GLB via FreeCAD CLI' },
  { label: 'PDF Preview', value: 'Embedded iframe (PDF.js)' },
  { label: 'DXF Preview', value: 'SVG vector render (custom parser)' },
  { label: 'Image formats', value: 'PNG, JPG, SVG, WebP via <img>' },
  { label: 'CORS', value: 'Open (internal tool)' },
];

export default function InfoPage() {
  return (
    <div className="stack">
      <section className="panel">
        <h2 style={{ marginBottom: 4 }}>About Quick Peek</h2>
        <p className="muted" style={{ margin: '0 0 20px' }}>
          A fast local-file batch preview tool for engineering and CAD teams.
        </p>
        <div className="two-col">
          <div>
            <h3 style={{ marginBottom: 14 }}>Features</h3>
            <div className="stack" style={{ gap: 14 }}>
              {features.map((f) => (
                <div key={f.title} className="info-feature">
                  <div className="info-icon">{f.icon}</div>
                  <div>
                    <strong style={{ fontSize: 14 }}>{f.title}</strong>
                    <p className="muted" style={{ margin: 3, fontSize: 13 }}>{f.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div>
            <h3 style={{ marginBottom: 14 }}>Technical specs</h3>
            <div className="spec-grid">
              {specs.map((s) => (
                <div key={s.label} className="spec-row">
                  <span>{s.label}</span>
                  <code>{s.value}</code>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="panel">
        <h3 style={{ marginBottom: 14 }}>Supported file types</h3>
        <div className="format-table">
          {[
            { fmt: 'STEP', exts: ['.stp', '.step'], note: '3D CAD model — preview via GLB conversion' },
            { fmt: 'PDF', exts: ['.pdf'], note: 'Document — embedded PDF viewer' },
            { fmt: 'DXF', exts: ['.dxf'], note: '2D/3D vector — SVG vector render' },
            { fmt: 'OBJ', exts: ['.obj'], note: '3D mesh — rendered in browser via Three.js' },
          ].map((f) => (
            <div key={f.fmt} className="format-row-item">
              <strong>{f.fmt}</strong>
              <div className="ext-tags">
                {f.exts.map((e) => <span key={e} className="ext-tag">{e}</span>)}
              </div>
              <span className="muted" style={{ fontSize: 12 }}>{f.note}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}