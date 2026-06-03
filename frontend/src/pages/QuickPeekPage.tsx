import { useEffect, useMemo, useState } from 'react';
import { FileSearch, FolderOpen, Loader2, RotateCcw, Save, Trash2 } from 'lucide-react';
import { deleteFolderPreset, listFolderPresets, normalizeCodes, saveFolderPreset, searchFiles } from '../api';
import type { FileItem, FolderPreset, Format, SearchResult, User } from '../types';
import PreviewCard from '../components/PreviewCard';
import ViewerModal from '../components/ViewerModal';
import FolderPickerModal from '../components/FolderPickerModal';

const formats: { id: Format; label: string; sub: string; permission: string }[] = [
  { id: 'step', label: 'STEP', sub: '.stp / .step', permission: 'view_step' },
  { id: 'pdf', label: 'PDF', sub: '.pdf', permission: 'view_pdf' },
  { id: 'dxf', label: 'DXF', sub: '.dxf', permission: 'view_dxf' },
  { id: 'obj', label: 'OBJ', sub: '.obj', permission: 'view_obj' }
];

function canView(user: User, permission: string) {
  return user.role === 'admin' || user.permissions.includes(permission as never);
}

export default function QuickPeekPage({ user }: { user: User }) {
  const initialFormat = formats.find((f) => canView(user, f.permission))?.id ?? 'step';
  const [format, setFormat] = useState<Format>(initialFormat);
  const [codesText, setCodesText] = useState('1827009605\n573419\nSAMPLE');
  const [workingFolder, setWorkingFolder] = useState(() => localStorage.getItem('quickpeek_working_folder') || '');
  const [presetName, setPresetName] = useState('');
  const [presets, setPresets] = useState<FolderPreset[]>([]);
  const [showFolderPicker, setShowFolderPicker] = useState(false);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [busy, setBusy] = useState(false);
  const [folderBusy, setFolderBusy] = useState(false);
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

  async function loadPresets() {
    try {
      const res = await listFolderPresets();
      setPresets(res.presets);
    } catch {
      // Presets are helpful, but the page should still work if this fails.
    }
  }

  useEffect(() => {
    loadPresets();
  }, []);

  function applyWorkingFolder(path: string) {
    const clean = path.trim();
    setWorkingFolder(clean);
    if (clean) localStorage.setItem('quickpeek_working_folder', clean);
    else localStorage.removeItem('quickpeek_working_folder');
  }

  async function saveCurrentFolder() {
    if (!workingFolder.trim()) {
      setError('Choose a working folder before saving a preset.');
      return;
    }
    const name = (presetName.trim() || workingFolder.split(/[\\/]/).filter(Boolean).slice(-1)[0] || 'Working folder').trim();
    setFolderBusy(true);
    setError('');
    try {
      await saveFolderPreset(name, workingFolder);
      setPresetName('');
      await loadPresets();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Cannot save folder preset');
    } finally {
      setFolderBusy(false);
    }
  }

  async function removePreset(id: number) {
    setFolderBusy(true);
    setError('');
    try {
      await deleteFolderPreset(id);
      await loadPresets();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Cannot delete folder preset');
    } finally {
      setFolderBusy(false);
    }
  }

  async function runSearch() {
    setBusy(true); setError(''); setResults([]);
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
          {formats.map((f) => {
            const disabled = !canView(user, f.permission);
            return (
              <button
                key={f.id}
                disabled={disabled}
                className={`format-card ${format === f.id ? 'selected' : ''}`}
                onClick={() => setFormat(f.id)}
              >
                <strong>{f.label}</strong>
                <span>{disabled ? 'No permission' : f.sub}</span>
              </button>
            );
          })}
        </div>

        <div className="folder-panel">
          <div className="folder-title-row">
            <div>
              <strong>Working folder</strong>
              <p className="muted">Search only inside this folder. Leave empty to use the backend default roots.</p>
            </div>
            <button className="secondary" onClick={() => setShowFolderPicker(true)}>
              <FolderOpen size={16} /> Browse
            </button>
          </div>
          <div className="folder-control-row">
            <input
              value={workingFolder}
              onChange={(e) => applyWorkingFolder(e.target.value)}
              placeholder="Example: C:\\local\\aventics\\task or \\\\server\\shared\\cad"
            />
            <button className="secondary" onClick={() => applyWorkingFolder('')}>Use default roots</button>
          </div>
          <div className="folder-save-row">
            <input value={presetName} onChange={(e) => setPresetName(e.target.value)} placeholder="Preset name, e.g. Aventics task folder" />
            <button className="primary" onClick={saveCurrentFolder} disabled={folderBusy || !workingFolder.trim()}>
              {folderBusy ? <Loader2 className="spin" size={16} /> : <Save size={16} />}
              Save folder
            </button>
          </div>
          {presets.length > 0 && (
            <div className="folder-presets">
              {presets.map((preset) => (
                <div className="folder-preset" key={preset.id}>
                  <button onClick={() => applyWorkingFolder(preset.path)} title={preset.path}>
                    <strong>{preset.name}</strong>
                    <span>{preset.path}</span>
                  </button>
                  <button className="icon-button" onClick={() => removePreset(preset.id)} title="Delete preset">
                    <Trash2 size={15} />
                  </button>
                </div>
              ))}
            </div>
          )}
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
            <p className="muted">Folder: <code>{workingFolder.trim() || 'Default backend roots'}</code></p>
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
