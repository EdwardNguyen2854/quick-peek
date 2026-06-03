type RoadmapItem = {
  phase: string;
  status: 'done' | 'in-progress' | 'planned';
  items: string[];
};

const phases: RoadmapItem[] = [
  {
    phase: 'v0.1 — MVP (Done)',
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
    phase: 'v0.2 — Polish & Expand',
    status: 'in-progress',
    items: [
      'Real STEP → GLB conversion via FreeCAD',
      'Full-screen viewer with pan/zoom for images',
      'DXF SVG rendering improvements',
      'User management (admin CRUD)',
      'Download files with permission check',
    ],
  },
  {
    phase: 'v0.3 — Formats & Scale',
    status: 'planned',
    items: [
      'STL, 3MF, IGES support',
      'Image formats: PNG, JPG, WebP, TIFF',
      'Office formats: DOCX, XLSX (thumbnail)',
      'Batch export selected files as ZIP',
      'Dark mode toggle',
    ],
  },
  {
    phase: 'v0.4 — Enterprise',
    status: 'planned',
    items: [
      'LDAP / SSO integration',
      'Per-folder permission scoping',
      'Search history & recent files',
      'File tagging & custom metadata',
      'API key auth for external tools',
    ],
  },
];

function statusBadge(status: RoadmapItem['status']) {
  const map = {
    done: { label: 'Done', cls: 'badge-done' },
    'in-progress': { label: 'In progress', cls: 'badge-progress' },
    planned: { label: 'Planned', cls: 'badge-planned' },
  };
  const b = map[status];
  return <span className={`roadmap-badge ${b.cls}`}>{b.label}</span>;
}

export default function RoadmapPage() {
  return (
    <div className="stack">
      <section className="panel">
        <h2 style={{ marginBottom: 4 }}>Roadmap</h2>
        <p className="muted" style={{ margin: '0 0 24px' }}>
          Planned features and improvements for Quick Peek.
        </p>
        <div className="roadmap-list">
          {phases.map((phase) => (
            <div key={phase.phase} className="roadmap-phase">
              <div className="roadmap-header">
                <h3>{phase.phase}</h3>
                {statusBadge(phase.status)}
              </div>
              <ul>
                {phase.items.map((item) => (
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