import { Download, X } from 'lucide-react';
import { apiUrl } from '../api';
import type { FileItem, Format } from '../types';
import StepViewer from './viewers/StepViewer';
import PanZoomImage from './viewers/PanZoomImage';
import DxfVectorViewer from './viewers/DxfVectorViewer';
import DocViewer from './viewers/DocViewer';
import MarkdownViewer from './viewers/MarkdownViewer';
import TextViewer from './viewers/TextViewer';
import HtmlViewer from './viewers/HtmlViewer';

export default function ViewerModal({ code, format, file, onClose }: { code: string; format: Format; file: FileItem; onClose: () => void }) {
  const previewUrl = apiUrl(file.preview_url);
  const rawUrl = apiUrl(file.raw_url);
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
          {(format === 'doc' || format === 'xls' || format === 'ppt') && <DocViewer url={previewUrl} />}
          {format === 'md' && <MarkdownViewer url={previewUrl} />}
          {format === 'txt' && <TextViewer url={previewUrl} />}
          {format === 'html' && <HtmlViewer url={previewUrl} />}
        </div>
      </div>
    </div>
  );
}
