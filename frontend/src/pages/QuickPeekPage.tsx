import { useMemo, useState } from 'react';
import { FileSearch, FolderOpen, Grid2X2, Grid3X3, Loader2, RotateCcw, Search } from 'lucide-react';
import { normalizeCodes, searchFiles } from '../api';
import type { FileItem, Format, SearchResult } from '../types';
import PreviewCard from '../components/PreviewCard';
import ViewerModal from '../components/ViewerModal';
import FolderPickerModal from '../components/FolderPickerModal';

const formats: { id: Format; label: string; exts: string }[] = [
  { id: 'step', label: 'STEP', exts: 'STP / STEP' },
  { id: 'pdf', label: 'PDF', exts: 'PDF' },
  { id: 'dxf', label: 'DXF', exts: 'DXF' },
  { id: 'doc', label: 'Word', exts: 'DOC / DOCX' },
  { id: 'xls', label: 'Excel', exts: 'XLS / XLSX' },
  { id: 'ppt', label: 'PowerPoint', exts: 'PPT / PPTX' },
  { id: 'md', label: 'Markdown', exts: 'MD' },
  { id: 'txt', label: 'Text', exts: 'TXT' },
  { id: 'html', label: 'HTML', exts: 'HTML' }
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
    const saved = Number(localStorage.getItem('quickpeek_columns'));
    return [2, 3, 4].includes(saved) ? saved : 3;
  });

  const codes = useMemo(() => normalizeCodes(codesText), [codesText]);
  const filesFound = results.reduce((sum, result) => sum + result.matches_count, 0);
  const foundCodes = results.filter((result) => result.status !== 'not_found').length;

  function selectFormat(nextFormat: Format) {
    if (nextFormat === format) return;
    setFormat(nextFormat);
    setResults([]);
    setSelected(null);
    setError('');
  }

  function applyWorkingFolder(path: string) {
    const clean = path.trim();
    setWorkingFolder(clean);
    if (clean) localStorage.setItem('quickpeek_working_folder', clean);
    else localStorage.removeItem('quickpeek_working_folder');
  }

  async function runSearch() {
    if (!codes.length) return;
    setBusy(true);
    setError('');
    setResults([]);
    try {
      const response = await searchFiles(format, codes, workingFolder.trim()) as { results: SearchResult[] };
      setResults(response.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    setCodesText('');
    setResults([]);
    setError('');
  }

  return (
    <div className="peek-page">
      <section className="intro-row">
        <div>
          <p className="eyebrow">File lookup</p>
          <h1>Find and inspect files quickly.</h1>
          <p className="intro-copy">Paste part numbers or codes, choose a file type, and preview matching engineering files in one place.</p>
        </div>
        <div className="intro-meta">
          <span><strong>{codes.length}</strong> codes</span>
          <span><strong>{filesFound}</strong> files</span>
        </div>
      </section>

      <section className="search-panel">
        <div className="field-group format-field">
          <span className="field-label">File type</span>
          <div className="format-tabs" role="tablist" aria-label="File type">
            {formats.map((item) => (
              <button
                key={item.id}
                className={`format-tab ${format === item.id ? 'active' : ''}`}
                onClick={() => selectFormat(item.id)}
                type="button"
                role="tab"
                aria-selected={format === item.id}
                title={item.exts}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>

        <div className="search-layout">
          <label className="field-group code-field">
            <span className="field-label">Codes or part numbers</span>
            <textarea
              value={codesText}
              onChange={(event) => setCodesText(event.target.value)}
              onKeyDown={(event) => {
                if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') runSearch();
              }}
              placeholder={'A-1024\nB-7782\nC-4100'}
            />
            <span className="field-hint">Paste from Excel or enter one per line. Ctrl/⌘ + Enter to search.</span>
          </label>

          <div className="scope-column">
            <div className="field-group">
              <span className="field-label">Search location</span>
              <div className="folder-input">
                <FolderOpen size={17} />
                <input
                  value={workingFolder}
                  onChange={(event) => applyWorkingFolder(event.target.value)}
                  placeholder="Default indexed folders"
                />
                <button className="button subtle" onClick={() => setShowFolderPicker(true)} type="button">Browse</button>
              </div>
              <span className="field-hint">{workingFolder.trim() ? 'Only this folder will be searched.' : 'Using configured default roots.'}</span>
            </div>

            <div className="search-summary">
              <div>
                <span>Pattern</span>
                <strong>*code*{format === 'step' ? '.stp/.step' : `.${format}`}</strong>
              </div>
              <div>
                <span>Preview</span>
                <strong>{format === 'step' ? 'Live 3D' : 'Automatic'}</strong>
              </div>
            </div>

            <div className="search-actions">
              <button className="button ghost" onClick={reset} disabled={!codesText && !results.length} type="button">
                <RotateCcw size={16} /> Clear
              </button>
              <button className="button primary" onClick={runSearch} disabled={busy || !codes.length} type="button">
                {busy ? <Loader2 className="spin" size={17} /> : <Search size={17} />}
                {busy ? 'Searching…' : 'Search files'}
              </button>
            </div>
          </div>
        </div>

        {error && <div className="notice error">{error}</div>}
      </section>

      <section className="results-section">
        <div className="results-header">
          <div>
            <p className="eyebrow">Results</p>
            <h2>{results.length ? 'Preview results' : 'Ready to search'}</h2>
            <p className="results-subtitle">
              {results.length
                ? `${foundCodes} of ${results.length} codes matched · ${filesFound} file${filesFound === 1 ? '' : 's'} found`
                : 'Your previews will appear here. STEP models load automatically in the grid.'}
            </p>
          </div>

          {results.length > 0 && (
            <div className="view-toggle" aria-label="Grid density">
              <button className={columns === 2 ? 'active' : ''} onClick={() => { setColumns(2); localStorage.setItem('quickpeek_columns', '2'); }} title="Comfortable grid">
                <Grid2X2 size={16} />
              </button>
              <button className={columns === 3 ? 'active' : ''} onClick={() => { setColumns(3); localStorage.setItem('quickpeek_columns', '3'); }} title="Standard grid">
                <Grid3X3 size={16} />
              </button>
              <button className={columns === 4 ? 'active compact-grid' : 'compact-grid'} onClick={() => { setColumns(4); localStorage.setItem('quickpeek_columns', '4'); }} title="Compact grid">
                <span>4</span>
              </button>
            </div>
          )}
        </div>

        {results.length > 0 ? (
          <div className="results-grid" style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}>
            {results.map((result) => (
              <PreviewCard
                key={result.code}
                result={result}
                format={format}
                onOpen={(file) => setSelected({ code: result.code, file })}
              />
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <FileSearch size={24} strokeWidth={1.5} />
            <strong>No previews yet</strong>
            <span>Choose a type, paste your codes, and search.</span>
          </div>
        )}
      </section>

      {showFolderPicker && (
        <FolderPickerModal
          initialPath={workingFolder}
          onClose={() => setShowFolderPicker(false)}
          onSelect={applyWorkingFolder}
        />
      )}

      {selected && (
        <ViewerModal
          code={selected.code}
          format={format}
          file={selected.file}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}
