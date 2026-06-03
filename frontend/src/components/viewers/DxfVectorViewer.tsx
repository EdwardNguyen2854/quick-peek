import { PointerEvent, WheelEvent, useEffect, useMemo, useRef, useState } from 'react';

type Box = { x: number; y: number; w: number; h: number };

function parseViewBox(value: string | null): Box {
  if (!value) return { x: 0, y: 0, w: 600, h: 400 };
  const nums = value.split(/[ ,]+/).map(Number).filter((x) => Number.isFinite(x));
  if (nums.length !== 4 || nums[2] === 0 || nums[3] === 0) return { x: 0, y: 0, w: 600, h: 400 };
  return { x: nums[0], y: nums[1], w: nums[2], h: nums[3] };
}

function boxToString(box: Box) {
  return `${box.x} ${box.y} ${box.w} ${box.h}`;
}

export default function DxfVectorViewer({ url, label }: { url: string; label: string }) {
  const [inner, setInner] = useState('');
  const [original, setOriginal] = useState<Box>({ x: 0, y: 0, w: 600, h: 400 });
  const [viewBox, setViewBox] = useState<Box>({ x: 0, y: 0, w: 600, h: 400 });
  const [error, setError] = useState('');
  const svgRef = useRef<SVGSVGElement | null>(null);
  const drag = useRef<{ x: number; y: number; box: Box } | null>(null);

  useEffect(() => {
    let ignore = false;
    setError('');
    fetch(url)
      .then((res) => {
        if (!res.ok) throw new Error(`Cannot load DXF preview: ${res.status}`);
        return res.text();
      })
      .then((text) => {
        if (ignore) return;
        const doc = new DOMParser().parseFromString(text, 'image/svg+xml');
        const svg = doc.querySelector('svg');
        if (!svg) throw new Error('DXF preview is not valid SVG');
        const box = parseViewBox(svg.getAttribute('viewBox'));
        setOriginal(box);
        setViewBox(box);
        setInner(svg.innerHTML);
      })
      .catch((err) => {
        if (!ignore) setError(err instanceof Error ? err.message : 'Cannot load DXF preview');
      });
    return () => { ignore = true; };
  }, [url]);

  const viewBoxText = useMemo(() => boxToString(viewBox), [viewBox]);

  function zoomAt(e: WheelEvent<SVGSVGElement>) {
    e.preventDefault();
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const px = (e.clientX - rect.left) / rect.width;
    const py = (e.clientY - rect.top) / rect.height;
    const factor = e.deltaY < 0 ? 0.86 : 1.16;
    setViewBox((box) => {
      const nextW = Math.max(original.w / 200, Math.min(original.w * 25, box.w * factor));
      const nextH = Math.max(original.h / 200, Math.min(original.h * 25, box.h * factor));
      const cx = box.x + box.w * px;
      const cy = box.y + box.h * py;
      return { x: cx - nextW * px, y: cy - nextH * py, w: nextW, h: nextH };
    });
  }

  function pointerDown(e: PointerEvent<SVGSVGElement>) {
    drag.current = { x: e.clientX, y: e.clientY, box: viewBox };
    e.currentTarget.setPointerCapture(e.pointerId);
  }

  function pointerMove(e: PointerEvent<SVGSVGElement>) {
    if (!drag.current || !svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const dx = (e.clientX - drag.current.x) / rect.width * drag.current.box.w;
    const dy = (e.clientY - drag.current.y) / rect.height * drag.current.box.h;
    setViewBox({ ...drag.current.box, x: drag.current.box.x - dx, y: drag.current.box.y - dy });
  }

  if (error) {
    return <div className="empty-preview">{error}</div>;
  }

  return (
    <div className="dxf-vector-viewer">
      <div className="panzoom-toolbar">Wheel to zoom · drag to pan · <button onClick={() => setViewBox(original)}>Fit</button></div>
      <svg
        ref={svgRef}
        viewBox={viewBoxText}
        role="img"
        aria-label={label}
        onWheel={zoomAt}
        onPointerDown={pointerDown}
        onPointerMove={pointerMove}
        onPointerUp={() => { drag.current = null; }}
        onPointerCancel={() => { drag.current = null; }}
        dangerouslySetInnerHTML={{ __html: inner }}
      />
    </div>
  );
}
