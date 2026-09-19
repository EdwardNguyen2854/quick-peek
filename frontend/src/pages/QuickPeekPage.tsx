import { useEffect, useMemo, useState } from 'react';
import { Database, FileSearch, FolderOpen, Loader2, RefreshCw, RotateCcw, Search } from 'lucide-react';
import { getIndexStatus, normalizeCodes, refreshIndex, searchFiles } from '../api';
import type { FileItem, Format, IndexState, SearchResult } from '../types';
import PreviewCard from '../components/PreviewCard';
import ViewerModal from '../components/ViewerModal';
import FolderPickerModal from '../components/FolderPickerModal';

const formats: { id: Format; label: string; exts: string }[] = [
  { id: 'all', label: 'All', exts: 'All supported formats' },
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

const DEFAULT_CARD_WIDTH = 520;
const DEFAULT_CARD_HEIGHT = 430;

type ResultFilter = 'all' | 'found' | 'multiple' | 'suggested' | 'missing';

function savedSize(key: string, fallback: number, min: number, max: number) {
  const value = Number(localStorage.getItem(key));
  return Number.isFinite(value) && value >= min && value <= max ? value : fallback;
}

const INDEX_POLL_INTERVAL = 1500;
const ACTIVE_PHASES = new Set(['starting', 'scanning', 'pruning']);

const PHASE_LABELS: Record<string, string> = {
  starting: 'Starting',
  scanning: 'Scanning files',
  pruning: 'Pruning removed files',
  ready: 'Ready',
  error: 'Error',
  idle: 'Idle'
};

function isIndexActive(index: IndexState | null) {
  if (!index) return false;
  return index.status === 'indexing' || ACTIVE_PHASES.has(String(index.phase || ''));
}

function phaseLabel(phase?: string | null) {
  const key = String(phase || 'idle');
  return PHASE_LABELS[key] || key;
}

function rootStatusLabel(status: string) {
  switch (status) {
    case 'indexing': return 'Indexing';
    case 'ready': return 'Ready';
    case 'error': return 'Error';
    case 'idle': return 'Idle';
    default: return status;
  }
}

function shortPath(path: string) {
  const trimmed = path.replace(/[\\/]+$/, '');
  const parts = trimmed.split(/[\\/]/);
  return parts[parts.length - 1] || path;
}

function timestampLabel(value?: string | null) {
  if (!value) return 'never';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function formatDuration(seconds: number) {
  const total = Math.max(0, Math.round(seconds));
  if (total < 60) return `${total}s`;
  const minutes = Math.floor(total / 60);
  return `${minutes}m ${String(total % 60).padStart(2, '0')}s`;
}

function indexLabel(index: IndexState | null) {
  if (!index) return 'Index status unavailable';
  if (isIndexActive(index)) {
    const scanned = (index.files_indexed ?? 0).toLocaleString();
    const root = index.current_root ? ` · ${shortPath(index.current_root)}` : '';
    const elapsed = index.elapsed_seconds ? ` · ${formatDuration(index.elapsed_seconds)}` : '';
    return `${phaseLabel(index.phase)} · ${scanned} files scanned${root}${elapsed}`;
  }
  if (index.status === 'error') return `Index error · ${index.last_error || 'refresh failed'}`;
  if (!index.last_completed_at) return `${index.files_count.toLocaleString()} indexed files`;

  return `${index.files_count.toLocaleString()} indexed files · updated ${timestampLabel(index.last_completed_at)}`;
}

export default function QuickPeekPage() {
  const [format, setFormat] = useState<Format>('step');
  const [codesText, setCodesText] = useState('');
  const [workingFolder, setWorkingFolder] = useState(() => localStorage.getItem('quickpeek_working_folder') || '');
  const [showFolderPicker, setShowFolderPicker] = useState(false);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [busy, setBusy] = useState(false);
  const [refreshPending, setRefreshPending] = useState(false);
  const [rootsOpen, setRootsOpen] = useState(false);
  const [index, setIndex] = useState<IndexState | null>(null);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState<ResultFilter>('all');
  const [selected, setSelected] = useState<{ code: string; file: FileItem } | null>(null);
  const [cardWidth, setCardWidth] = useState(() => savedSize('quickpeek_card_width', DEFAULT_CARD_WIDTH, 360, 800));
  const [cardHeight, setCardHeight] = useState(() => savedSize('quickpeek_card_height', DEFAULT_CARD_HEIGHT, 320, 720));

  const codes = useMemo(() => normalizeCodes(codesText), [codesText]);
  const filesFound = results.reduce((sum, result) => sum + result.matches_count, 0);
  const foundCodes = results.filter((result) => result.status === 'found' || result.status === 'multiple_matches').length;

  const indexActive = isIndexActive(index);
  const indexBusy = refreshPending || indexActive;
  const roots = index?.roots ?? [];
  const rootsUnhealthy = roots.some((root) => root.status === 'error');
  const showRoots = roots.length > 0 && (rootsOpen || indexActive || rootsUnhealthy);

  const filterCounts = useMemo(() => ({
    all: results.length,
    found: results.filter((result) => result.status === 'found').length,
    multiple: results.filter((result) => result.status === 'multiple_matches').length,
    suggested: results.filter((result) => result.status === 'suggested').length,
    missing: results.filter((result) => result.status === 'not_found').length,
  }), [results]);

  const visibleResults = useMemo(() => {
    if (filter === 'all') return results;
    const status = filter === 'multiple'
      ? 'multiple_matches'
      : filter === 'missing'
        ? 'not_found'
        : filter;
    return results.filter((result) => result.status === status);
  }, [filter, results]);

  useEffect(() => {
    getIndexStatus()
      .then(setIndex)
      .catch(() => setIndex(null));
  }, []);

  useEffect(() => {
    if (!indexActive) return;
    let cancelled = false;
    const timer = window.setInterval(() => {
      getIndexStatus()
        .then((next) => {
          if (!cancelled) setIndex(next);
        })
        .catch(() => {});
    }, INDEX_POLL_INTERVAL);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [indexActive]);

  function selectFormat(nextFormat: Format) {
    if (nextFormat === format) return;
    setFormat(nextFormat);
    setResults([]);
    setSelected(null);
    setFilter('all');
    setError('');
  }

  function applyWorkingFolder(path: string) {
    const clean = path.trim();
    setWorkingFolder(clean);
    if (clean) localStorage.setItem('quickpeek_working_folder', clean);
    else localStorage.removeItem('quickpeek_working_folder');
  }

  async function refreshSearchIndex(path = workingFolder.trim()) {
    setRefreshPending(true);
    setError('');
    try {
      const response = await refreshIndex(path || undefined);
      setIndex(response.index);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Index refresh failed');
      try {
        setIndex(await getIndexStatus());
      } catch {}
    } finally {
      setRefreshPending(false);
    }
  }

  function chooseWorkingFolder(path: string) {
    applyWorkingFolder(path);
    void refreshSearchIndex(path);
  }

  function updateCardWidth(value: number) {
    setCardWidth(value);
    localStorage.setItem('quickpeek_card_width', String(value));
  }

  function updateCardHeight(value: number) {
    setCardHeight(value);
    localStorage.setItem('quickpeek_card_height', String(value));
  }

  function resetCardSize() {
    updateCardWidth(DEFAULT_CARD_WIDTH);
    updateCardHeight(DEFAULT_CARD_HEIGHT);
  }

  async function runSearch() {
    if (!codes.length) return;
    setBusy(true);
    setError('');
    setResults([]);
    setFilter('all');
    try {
      const response = await searchFiles(format, codes, workingFolder.trim());
      setResults(response.results);
      setIndex(response.index);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    setCodesText('');
    setResults([]);
    setFilter('all');
    setError('');
  }

  const patternLabel = format === 'all'
    ? '*code* · all supported formats'
    : format === 'step'
      ? '*code*.stp / *.step'
      : `*code*.${format}`;

  return (
    <div className="peek-page">
      <section className="intro-row">
        <div>
          <p className="eyebrow">File lookup</p>
          <h1>Find the right engineering file.</h1>
          <p className="intro-copy">Paste part numbers or codes. Quick Peek normalizes formatting, ranks revisions and folders deterministically, and keeps uncertain matches clearly separated.</p>
        </div>
        <div className="intro-meta">
          <span><strong>{codes.length}</strong> codes</span>
          <span><strong>{filesFound}</strong> matches</span>
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
              placeholder={'R502A1B10M11BF1\nR502A1B40MA00F1\nABC-123'}
            />
            <span className="field-hint">Paste rows from Excel or enter one per line. Tabs use the first pasted column; commas and semicolons are also accepted.</span>
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
              <span className="field-hint">{workingFolder.trim() ? 'Results are scoped to this indexed folder.' : 'Using configured default roots.'}</span>
            </div>

            <div className="index-block">
              <div className="index-panel">
                <div className="index-state">
                  <Database size={15} />
                  <div>
                    <strong>Search index</strong>
                    <span title={index?.current_root || undefined}>{indexLabel(index)}</span>
                  </div>
                </div>
                <div className="index-panel-actions">
                  {roots.length > 0 && (
                    <button
                      className="index-roots-toggle"
                      onClick={() => setRootsOpen((open) => !open)}
                      type="button"
                      aria-expanded={showRoots}
                    >
                      {showRoots ? 'Hide roots' : `${roots.length} root${roots.length === 1 ? '' : 's'}`}
                    </button>
                  )}
                  <button className="button subtle index-refresh" onClick={() => refreshSearchIndex()} disabled={indexBusy} type="button">
                    {indexBusy ? <Loader2 className="spin" size={15} /> : <RefreshCw size={15} />}
                    {indexActive ? 'Indexing…' : refreshPending ? 'Starting…' : 'Refresh'}
                  </button>
                </div>
              </div>

              {indexActive && (
                <div className="index-progress" role="status" aria-live="polite">
                  <span className="index-progress-phase">{phaseLabel(index?.phase)}</span>
                  <span>{index?.current_root ? shortPath(index.current_root) : 'Preparing'}</span>
                  <span>{(index?.files_indexed ?? 0).toLocaleString()} files scanned</span>
                  <span>{formatDuration(index?.elapsed_seconds ?? 0)} elapsed</span>
                </div>
              )}

              {showRoots && (
                <ul className="index-roots">
                  {roots.map((root) => (
                    <li key={root.root_path} className={`index-root ${root.status}`}>
                      <span className="index-root-dot" aria-hidden="true" />
                      <div className="index-root-main">
                        <strong title={root.root_path}>{shortPath(root.root_path)}</strong>
                        <span title={root.root_path}>{root.root_path}</span>
                      </div>
                      <div className="index-root-meta">
                        <span>{rootStatusLabel(root.status)}</span>
                        <span>{root.files_count.toLocaleString()} files</span>
                        <span>updated {timestampLabel(root.last_completed_at)}</span>
                      </div>
                      {root.last_error && <p className="index-root-error">{root.last_error}</p>}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="search-summary">
              <div>
                <span>Pattern</span>
                <strong>{patternLabel}</strong>
              </div>
              <div>
                <span>Ranking</span>
                <strong>Exact · folder · revision · date</strong>
              </div>
            </div>

            <div className="search-actions">
              <button className="button ghost" onClick={reset} disabled={!codesText && !results.length} type="button">
                <RotateCcw size={16} /> Clear
              </button>
              <button className="button primary" onClick={runSearch} disabled={busy || !codes.length || indexBusy} type="button">
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
            <h2>{results.length ? 'Search results' : 'Ready to search'}</h2>
            <p className="results-subtitle">
              {results.length
                ? `${foundCodes} of ${results.length} codes matched · ${filesFound} strong candidate${filesFound === 1 ? '' : 's'}`
                : 'Exact and normalized matches are preferred; fuzzy matches are suggestions only.'}
            </p>
          </div>

          {results.length > 0 && (
            <div className="card-size-toolbar" aria-label="Preview card size">
              <label className="size-control">
                <span>Width</span>
                <input type="range" min="360" max="800" step="20" value={cardWidth} onChange={(event) => updateCardWidth(Number(event.target.value))} />
                <output>{cardWidth}px</output>
              </label>
              <label className="size-control">
                <span>Height</span>
                <input type="range" min="320" max="720" step="20" value={cardHeight} onChange={(event) => updateCardHeight(Number(event.target.value))} />
                <output>{cardHeight}px</output>
              </label>
              <button className="size-reset" type="button" onClick={resetCardSize} title="Reset card size">Reset</button>
            </div>
          )}
        </div>

        {results.length > 0 && (
          <div className="result-filters" role="tablist" aria-label="Result filters">
            {([
              ['all', 'All'],
              ['found', 'Found'],
              ['multiple', 'Multiple'],
              ['suggested', 'Suggested'],
              ['missing', 'Missing'],
            ] as const).map(([id, label]) => (
              <button
                key={id}
                className={filter === id ? 'active' : ''}
                onClick={() => setFilter(id)}
                role="tab"
                aria-selected={filter === id}
                type="button"
              >
                {label}<span>{filterCounts[id]}</span>
              </button>
            ))}
          </div>
        )}

        {results.length > 0 ? (
          visibleResults.length > 0 ? (
            <div className="results-grid" style={{ gridTemplateColumns: `repeat(auto-fill, minmax(min(100%, ${cardWidth}px), ${cardWidth}px))` }}>
              {visibleResults.map((result) => (
                <PreviewCard
                  key={result.code}
                  result={result}
                  searchFormat={format}
                  cardHeight={cardHeight}
                  pauseStepPreview={selected !== null}
                  onOpen={(file) => setSelected({ code: result.code, file })}
                />
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <FileSearch size={24} strokeWidth={1.5} />
              <strong>No results in this filter</strong>
              <span>Choose another result category.</span>
            </div>
          )
        ) : (
          <div className="empty-state">
            <FileSearch size={24} strokeWidth={1.5} />
            <strong>No results yet</strong>
            <span>Search uses the current SQLite index and does not rescan folders.</span>
          </div>
        )}
      </section>

      {showFolderPicker && (
        <FolderPickerModal
          initialPath={workingFolder}
          onClose={() => setShowFolderPicker(false)}
          onSelect={chooseWorkingFolder}
        />
      )}

      {selected && (
        <ViewerModal
          code={selected.code}
          format={selected.file.format}
          file={selected.file}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}
