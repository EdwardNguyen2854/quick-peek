import { useEffect } from 'react';
import { Download, X } from 'lucide-react';
import { api, withToken } from '../api';
import type { FileItem, Format } from '../types';
import StepViewer from './viewers/StepViewer';
import PanZoomImage from './viewers/PanZoomImage';
import DxfVectorViewer from './viewers/DxfVectorViewer';
import ObjViewer from './viewers/ObjViewer';

export default function ViewerModal({ code, format, file, onClose }: { code: string; format: Format; file: FileItem; onClose: () => void }) {
  useEffect(() => {
    api('/api/usage/open', { method: 'POST', body: JSON.stringify({ file_id: file.file_id, format }) }).catch(() => null);
  }, [file.file_id, format]);

  const previewUrl = withToken(file.preview_url);
  const rawUrl = withToken(file.raw_url);
  const pdfViewUrl = `${previewUrl}#toolbar=1&navpanes=0&scrollbar=1&page=1&view=FitH`;

  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <div className="viewer-modal" onMouseDown={(e) => e.stopPropagation()}>
        <header>
          <div>
            <p className="eyebrow">{code} · {format.toUpperCase()}</p>
            <h2>{file.filename}</h2>
            {file.message && <span className="viewer-message">{file.message}</span>}
          </div>
          <div className="modal-actions">
            <a href={rawUrl} className="secondary small"><Download size={16}/> Download</a>
            <button className="icon-button" onClick={onClose}><X size={20}/></button>
          </div>
        </header>
        <div className="viewer-body">
          {format === 'step' && file.preview_kind === 'glb' && <StepViewer url={previewUrl} />}
          {format === 'step' && file.preview_kind !== 'glb' && <PanZoomImage url={previewUrl} label="STEP placeholder preview" />}
          {format === 'pdf' && <iframe className="pdf-frame" src={pdfViewUrl} title={file.filename} />}
          {format === 'dxf' && <DxfVectorViewer url={previewUrl} label="DXF preview" />}
          {format === 'obj' && <ObjViewer url={previewUrl} />}
        </div>
      </div>
    </div>
  );
}
