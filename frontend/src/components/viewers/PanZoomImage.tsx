import { useRef, useState } from 'react';

export default function PanZoomImage({ url, label }: { url: string; label: string }) {
  const [scale, setScale] = useState(1);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const drag = useRef<{ x: number; y: number; px: number; py: number } | null>(null);

  return (
    <div
      className="panzoom"
      onWheel={(e) => {
        e.preventDefault();
        const next = Math.max(0.2, Math.min(8, scale + (e.deltaY < 0 ? 0.15 : -0.15)));
        setScale(next);
      }}
      onPointerDown={(e) => {
        drag.current = { x: e.clientX, y: e.clientY, px: pos.x, py: pos.y };
        (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
      }}
      onPointerMove={(e) => {
        if (!drag.current) return;
        setPos({ x: drag.current.px + e.clientX - drag.current.x, y: drag.current.py + e.clientY - drag.current.y });
      }}
      onPointerUp={() => { drag.current = null; }}
    >
      <div className="panzoom-toolbar">Wheel to zoom · drag to pan · <button onClick={() => { setScale(1); setPos({ x: 0, y: 0 }); }}>Reset</button></div>
      <img src={url} alt={label} style={{ transform: `translate(${pos.x}px, ${pos.y}px) scale(${scale})` }} draggable={false} />
    </div>
  );
}
