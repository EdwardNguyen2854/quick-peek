type ReleaseItem = {
  version: string;
  date: string;
  status: 'done' | 'in-progress' | 'planned';
  items: string[];
};

const releases: ReleaseItem[] = [
  {
    version: 'v0.1 — MVP',
    date: '2025',
    status: 'done',
    items: [
      'JWT auth with admin/user roles',
      'STEP / PDF / DXF / OBJ file search by code',
      'Preview rendering (iframe, img, 3D placeholder)',
      'Working folder selection + presets',
      'Column & height controls for preview grid',
    ],
  },
  {
    version: 'v0.2 — Polish & Expand',
    date: '2025',
    status: 'done',
    items: [
      'Real STEP → GLB conversion via FreeCAD',
      'Full-screen viewer with pan/zoom for images',
      'DXF SVG rendering improvements',
      'User management (admin CRUD)',
      'Download files with permission check',
    ],
  },
  {
    version: 'v0.3 — Document Formats',
    date: '2026',
    status: 'done',
    items: [
      'Office formats: DOC, DOCX, XLS, XLSX, PPT, PPTX → HTML preview via pure Python (python-docx, openpyxl, python-pptx)',
      'Markdown (.md) → styled HTML preview',
      'Plain text (.txt) direct serve',
      'HTML (.html, .htm) direct serve',
      'File size checks and graceful degradation when Python libraries unavailable',
    ],
  },
  {
    version: 'v0.4 — Enterprise',
    date: 'TBD',
    status: 'planned',
    items: [
      'STL, 3MF, IGES support',
      'Image formats: PNG, JPG, WebP, TIFF',
      'Batch export selected files as ZIP',
      'Dark mode toggle',
      'LDAP / SSO integration',
      'Per-folder permission scoping',
      'Search history & recent files',
      'File tagging & custom metadata',
      'API key auth for external tools',
    ],
  },
];

function statusBadge(status: ReleaseItem['status']) {
  const map = {
    done: { label: 'Done', cls: 'badge-done' },
    'in-progress': { label: 'In progress', cls: 'badge-progress' },
    planned: { label: 'Planned', cls: 'badge-planned' },
  };
  const b = map[status];
  return <span className={`roadmap-badge ${b.cls}`}>{b.label}</span>;
}

export default function ReleasesPage() {
  return (
    <div className="stack">
      <section className="panel">
        <h2 style={{ marginBottom: 4 }}>Release History</h2>
        <p className="muted" style={{ margin: '0 0 24px' }}>
          Changelog and version history for Quick Peek.
        </p>
        <div className="roadmap-list">
          {releases.map((release) => (
            <div key={release.version} className="roadmap-phase">
              <div className="roadmap-header">
                <h3>{release.version}</h3>
                {statusBadge(release.status)}
              </div>
              <p className="muted" style={{ fontSize: 12, margin: '0 0 12px' }}>{release.date}</p>
              <ul>
                {release.items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}