import { useMemo, useState } from 'react';
import { FileSearch, FolderOpen, Loader2, RotateCcw } from 'lucide-react';
import { normalizeCodes, searchFiles } from '../api';
import type { FileItem, Format, SearchResult } from '../types';
import PreviewCard from '../components/PreviewCard';
import ViewerModal from '../components/ViewerModal';
import FolderPickerModal from '../components/FolderPickerModal';

const formats: { id: Format; label: string; exts: string }[] = [
  { id: 'step', label: 'STEP', exts: '.stp .step' },
  { id: 'pdf', label: 'PDF', exts: '.pdf' },
  { id: 'dxf', label: 'DXF', exts: '.dxf' },
  { id: 'doc', label: 'Word', exts: '.doc .docx' },
  { id: 'xls', label: 'Excel', exts: '.xls .xlsx' },
  { id: 'ppt', label: 'PowerPoint', exts: '.ppt .pptx' },
  { id: 'md', label: 'Markdown', exts: '.md' },
  { id: 'txt', label: 'Text', exts: '.txt' },
  { id: 'html', label: 'HTML', exts: '.html .htm' }
];

export default function QuickPeekPage() {
  const [format, setFormat] = useState<Format>('step');
  const [codesText, setCodesText] = useState('');
  const [workingFolder, setWorkingFolder] = useState(() => localStorage.getItem('quickpeek_working_folder') || '');
  const [showFolderPicker, setShowFolderPicker] = useState(false);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState<{ code: string; file: FileItem } | null>(null);
  const [columns, setColumns] = useState(() => {
    const saved = localStorage.getItem('quickpeek_columns');
    return saved ? parseInt(saved, 10) : 3;
  });
  const [cardHeight, setCardHeight] = useState(() => {
    const saved = localStorage.getItem('quickpeek_card_height');
    return saved ? parseInt(saved, 10) : 350;
  });

  const codes = useMemo(() => normalizeCodes(codesText), [codesText]);
  const found = results.reduce((sum, r) => sum + r.matches_count, 0);

  function applyWorkingFolder(path: string) {
    const clean = path.trim();
    setWorkingFolder(clean);
    if (clean) localStorage.setItem('quickpeek_working_folder', clean);
    else localStorage.removeItem('quickpeek_working_folder');
  }

  async function runSearch() {
    setBusy(true);
    setError('');
    setResults([]);
    try {
      const res = await searchFiles(format, codes, workingFolder.trim()) as { results: SearchResult[] };
      setResults(res.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack">
      <section className="panel hero-panel">
        <div className="format-row">
          {formats.map((f) => (
            <button
              key={f.id}
              className={`format-card ${format === f.id ? 'selected' : ''}`}
              onClick={() => setFormat(f.id)}
            >
              <strong>{f.label}</strong>
              <span>{f.exts}</span>
            </button>
          ))}
        </div>

        <div className="folder-panel">
          <div className="folder-title-row">
            <div>
              <strong>Working folder</strong>
              <p className="muted">Search only this folder, or leave empty to use the configured roots.</p>
            </div>
            <button className="secondary" onClick={() => setShowFolderPicker(true)}>
              <FolderOpen size={16} /> Browse
            </button>
          </div>
          <div className="folder-control-row">
            <input
              value={workingFolder}
              onChange={(e) => applyWorkingFolder(e.target.value)}
              placeholder="Example: C:\\engineering\\cad or \\\\server\\shared\\cad"
            />
            <button className="secondary" onClick={() => applyWorkingFolder('')}>Use default roots</button>
          </div>
        </div>

        <div className="input-grid">
          <label className="code-input-label">
            Code list
            <textarea value={codesText} onChange={(e) => setCodesText(e.target.value)} placeholder="Paste one or many codes here" />
          </label>
          <div className="search-help">
            <div className="stat-card"><span>Codes</span><strong>{codes.length}</strong></div>
            <div className="stat-card"><span>Found files</span><strong>{found}</strong></div>
            <p>Search pattern: <code>*code-number*{format === 'step' ? '.stp/.step' : '.' + format}</code></p>
            <p className="muted">Folder: <code>{workingFolder.trim() || 'Default roots'}</code></p>
            <button className="primary" onClick={runSearch} disabled={busy || !codes.length}>
              {busy ? <Loader2 className="spin" size={18} /> : <FileSearch size={18} />}
              Search previews
            </button>
            <button className="secondary" onClick={() => { setCodesText(''); setResults([]); }}>
              <RotateCcw size={16} /> Reset
            </button>
          </div>
        </div>
        {error && <div className="error-box">{error}</div>}
      </section>

      {results.length > 0 && (
        <div className="results-controls">
          <span className="results-count">{results.length} result{results.length !== 1 ? 's' : ''}</span>
          <div className="columns-control">
            <span>Cols:</span>
            {[1, 2, 3, 4, 5].map((n) => (
              <button
                key={n}
                className={`col-btn ${columns === n ? 'active' : ''}`}
                onClick={() => { setColumns(n); localStorage.setItem('quickpeek_columns', String(n)); }}
              >
                {n}
              </button>
            ))}
          </div>
          <div className="height-control">
            <span>Height:</span>
            <input
              type="range"
              min="200"
              max="600"
              step="10"
              value={cardHeight}
              onChange={(e) => {
                const v = parseInt(e.target.value, 10);
                setCardHeight(v);
                localStorage.setItem('quickpeek_card_height', String(v));
              }}
            />
            <span className="height-val">{cardHeight}px</span>
          </div>
        </div>
      )}

      <section className="results-grid" style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}>
        {results.map((r) => (
          <PreviewCard key={r.code} result={r} format={format} onOpen={(file) => setSelected({ code: r.code, file })} previewHeight={cardHeight} />
        ))}
      </section>

      {showFolderPicker && <FolderPickerModal initialPath={workingFolder} onClose={() => setShowFolderPicker(false)} onSelect={applyWorkingFolder} />}
      {selected && <ViewerModal code={selected.code} format={format} file={selected.file} onClose={() => setSelected(null)} />}
    </div>
  );
}
