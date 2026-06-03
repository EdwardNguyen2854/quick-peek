import { useEffect, useState } from 'react';
import { ChevronLeft, Folder, HardDrive, Loader2, X } from 'lucide-react';
import { browseFolder } from '../api';
import type { FolderBrowseResponse } from '../types';

export default function FolderPickerModal({
  initialPath,
  onClose,
  onSelect
}: {
  initialPath?: string;
  onClose: () => void;
  onSelect: (path: string) => void;
}) {
  const [pathInput, setPathInput] = useState(initialPath || '');
  const [data, setData] = useState<FolderBrowseResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function load(path?: string) {
    setBusy(true);
    setError('');
    try {
      const res = await browseFolder(path);
      setData(res);
      setPathInput(res.path);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Cannot browse folder');
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    load(initialPath);
  }, []);

  return (
    <div className="modal-backdrop">
      <div className="folder-modal">
        <header>
          <div>
            <h2>Browse working folder</h2>
            <p className="muted">Choose the folder where Quick Peek should search STEP, PDF, or DXF files.</p>
          </div>
          <button className="icon-button" onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </header>

        <div className="folder-path-row">
          <input value={pathInput} onChange={(e) => setPathInput(e.target.value)} placeholder="C:\\local\\aventics\\task" />
          <button className="secondary" onClick={() => load(pathInput)} disabled={busy}>
            {busy ? <Loader2 className="spin" size={16} /> : <Folder size={16} />}
            Open
          </button>
          <button className="primary" onClick={() => { onSelect(pathInput); onClose(); }} disabled={!pathInput.trim()}>
            Use this folder
          </button>
        </div>

        {error && <div className="error-box">{error}</div>}

        <div className="folder-body">
          <aside className="folder-roots">
            <span>Quick roots</span>
            {(data?.roots || []).map((root) => (
              <button key={root} onClick={() => load(root)} title={root}>
                <HardDrive size={15} />
                <em>{root}</em>
              </button>
            ))}
          </aside>

          <div className="folder-list">
            <div className="folder-current">
              <strong>{data?.path || pathInput || 'Loading...'}</strong>
              {data?.parent && (
                <button className="secondary small" onClick={() => load(data.parent || undefined)}>
                  <ChevronLeft size={15} /> Parent
                </button>
              )}
            </div>
            {busy && <div className="center-screen small-center"><Loader2 className="spin" size={22} /> Loading folders...</div>}
            {!busy && data?.items.map((item) => (
              <button key={item.path} className="folder-item" onClick={() => load(item.path)} title={item.path}>
                <Folder size={17} />
                <span>{item.name}</span>
                <em>{item.path}</em>
              </button>
            ))}
            {!busy && data && data.items.length === 0 && <p className="muted folder-empty">No subfolders found here.</p>}
          </div>
        </div>
      </div>
    </div>
  );
}
