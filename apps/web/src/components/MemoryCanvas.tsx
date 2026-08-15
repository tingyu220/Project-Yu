import { useEffect, useRef } from "react";
import { clusterColor, clusterOf } from "../lib/cluster";
import type { Memory } from "../lib/types";

interface MemoryCanvasProps {
  memories: Memory[];
  highlights: number[];
  selectedId: number | null;
  onSelect: (m: Memory | null) => void;
  reduced: boolean;
}

interface Node {
  mem: Memory;
  color: string;
  r: number;
  x: number;
  y: number;
  tx: number;
  ty: number;
  cx: number;
  cy: number;
}

function hash01(n: number): number {
  const x = Math.sin(n * 12.9898) * 43758.5453;
  return x - Math.floor(x);
}

/**
 * Memory Universe 星座：2D Canvas 力布局。
 * - 节点按记忆话题聚类（cluster），簇围绕中心排布。
 * - Node Size -> importance，Brightness -> 高亮/命中，Distance -> 话题关系。
 * - 支持拖拽平移、滚轮缩放、点击选中、查询命中聚合。
 * - 离开页面时释放 RAF / 监听器（dispose）。
 */
export default function MemoryCanvas({
  memories,
  highlights,
  selectedId,
  onSelect,
  reduced,
}: MemoryCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const nodesRef = useRef<Node[]>([]);
  const highlightsRef = useRef<Set<number>>(new Set());
  const selectedRef = useRef<number | null>(selectedId);
  const hoverRef = useRef<number | null>(null);
  const onSelectRef = useRef(onSelect);
  const viewRef = useRef({ panX: 0, panY: 0, scale: 1 });
  const dragRef = useRef({ sx: 0, sy: 0, moved: 0, active: false });

  highlightsRef.current = new Set(highlights);
  selectedRef.current = selectedId;
  onSelectRef.current = onSelect;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let raf = 0;
    let w = 0;
    let h = 0;
    let dpr = 1;

    const layout = () => {
      const byCluster = new Map<string, Memory[]>();
      for (const m of memories) {
        const c = clusterOf(m);
        const arr = byCluster.get(c) ?? [];
        arr.push(m);
        byCluster.set(c, arr);
      }
      const keys = [...byCluster.keys()];
      const n = Math.max(keys.length, 1);
      const cxm = w / 2;
      const cym = h / 2;
      const R = Math.min(w, h) * 0.34;
      const nodes: Node[] = [];
      keys.forEach((key, ci) => {
        const angle = (ci / n) * Math.PI * 2 - Math.PI / 2;
        const ax = cxm + Math.cos(angle) * R;
        const ay = cym + Math.sin(angle) * R;
        const spread = R * 0.26;
        for (const m of byCluster.get(key)!) {
          const a2 = hash01(m.id) * Math.PI * 2;
          const rr = spread * (0.12 + 0.88 * hash01(m.id + 997));
          const tx = ax + Math.cos(a2) * rr;
          const ty = ay + Math.sin(a2) * rr;
          const r = m.importance === "high" ? 5 : m.importance === "medium" ? 3.6 : 2.6;
          nodes.push({ mem: m, color: clusterColor(key), r, x: tx, y: ty, tx, ty, cx: ax, cy: ay });
        }
      });
      nodesRef.current = nodes;
    };

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      dpr = window.devicePixelRatio || 1;
      w = rect.width;
      h = rect.height;
      canvas.width = Math.max(1, Math.round(w * dpr));
      canvas.height = Math.max(1, Math.round(h * dpr));
      layout();
    };

    const toWorld = (clientX: number, clientY: number) => {
      const rect = canvas.getBoundingClientRect();
      const sx = clientX - rect.left;
      const sy = clientY - rect.top;
      const v = viewRef.current;
      return { x: (sx - v.panX) / v.scale, y: (sy - v.panY) / v.scale };
    };

    const hitTest = (wx: number, wy: number): Memory | null => {
      let bestId = -1;
      let bestD = Infinity;
      for (const nd of nodesRef.current) {
        const dx = nd.x - wx;
        const dy = nd.y - wy;
        const d = dx * dx + dy * dy;
        const rr = nd.r + 8;
        if (d < rr * rr && d < bestD) {
          bestD = d;
          bestId = nd.mem.id;
        }
      }
      if (bestId < 0) return null;
      return nodesRef.current.find((nd) => nd.mem.id === bestId)?.mem ?? null;
    };

    const onPointerDown = (e: PointerEvent) => {
      canvas.setPointerCapture(e.pointerId);
      dragRef.current = { sx: e.clientX, sy: e.clientY, moved: 0, active: true };
    };

    const onPointerMove = (e: PointerEvent) => {
      if (!dragRef.current.active) {
        if (e.pointerType === "mouse") {
          const p = toWorld(e.clientX, e.clientY);
          const m = hitTest(p.x, p.y);
          hoverRef.current = m ? m.id : null;
          canvas.style.cursor = m ? "pointer" : "grab";
        }
        return;
      }
      const dx = e.clientX - dragRef.current.sx;
      const dy = e.clientY - dragRef.current.sy;
      dragRef.current.moved += Math.abs(dx) + Math.abs(dy);
      viewRef.current.panX += dx;
      viewRef.current.panY += dy;
      dragRef.current.sx = e.clientX;
      dragRef.current.sy = e.clientY;
    };

    const onPointerUp = (e: PointerEvent) => {
      if (dragRef.current.active && dragRef.current.moved < 6) {
        const p = toWorld(e.clientX, e.clientY);
        onSelectRef.current(hitTest(p.x, p.y));
      }
      dragRef.current.active = false;
    };

    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const rect = canvas.getBoundingClientRect();
      const sx = e.clientX - rect.left;
      const sy = e.clientY - rect.top;
      const v = viewRef.current;
      const worldX = (sx - v.panX) / v.scale;
      const worldY = (sy - v.panY) / v.scale;
      const factor = e.deltaY < 0 ? 1.12 : 1 / 1.12;
      v.scale = Math.min(3, Math.max(0.5, v.scale * factor));
      v.panX = sx - worldX * v.scale;
      v.panY = sy - worldY * v.scale;
    };

    const draw = () => {
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);
      ctx.save();
      ctx.translate(viewRef.current.panX, viewRef.current.panY);
      ctx.scale(viewRef.current.scale, viewRef.current.scale);

      const cx = w / 2;
      const cy = h / 2;
      const lerp = reduced ? 1 : 0.09;
      const hs = highlightsRef.current;

      // 中央 Core 柔光
      const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, 90);
      grad.addColorStop(0, "rgba(230,207,164,0.10)");
      grad.addColorStop(1, "rgba(230,207,164,0)");
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(cx, cy, 90, 0, Math.PI * 2);
      ctx.fill();

      // 星座连线（节点 -> 簇中心）
      ctx.strokeStyle = "rgba(236,236,232,0.05)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      for (const nd of nodesRef.current) {
        ctx.moveTo(nd.cx, nd.cy);
        ctx.lineTo(nd.x, nd.y);
      }
      ctx.stroke();

      // 节点
      for (const nd of nodesRef.current) {
        let tx = nd.tx;
        let ty = nd.ty;
        let opacity = 0.8;
        let glow = false;
        if (hs.size > 0) {
          if (hs.has(nd.mem.id)) {
            tx = cx;
            ty = cy;
            opacity = 1;
            glow = true;
          } else {
            opacity = 0.13;
          }
        }
        nd.x += (tx - nd.x) * lerp;
        nd.y += (ty - nd.y) * lerp;

        const isSel = selectedRef.current === nd.mem.id;
        const isHover = hoverRef.current === nd.mem.id;
        const rad = nd.r * (isSel ? 1.55 : isHover ? 1.35 : 1);

        if (glow) {
          ctx.save();
          ctx.shadowColor = nd.color;
          ctx.shadowBlur = 14;
        }
        ctx.globalAlpha = opacity;
        ctx.fillStyle = nd.color;
        ctx.beginPath();
        ctx.arc(nd.x, nd.y, rad, 0, Math.PI * 2);
        ctx.fill();
        if (isSel) {
          ctx.globalAlpha = 1;
          ctx.strokeStyle = "rgba(236,236,232,0.9)";
          ctx.lineWidth = 1.5;
          ctx.beginPath();
          ctx.arc(nd.x, nd.y, rad + 4, 0, Math.PI * 2);
          ctx.stroke();
        }
        if (glow) ctx.restore();
      }
      ctx.globalAlpha = 1;
      ctx.restore();

      raf = requestAnimationFrame(frame);
    };

    const frame = () => {
      draw();
    };

    canvas.addEventListener("pointerdown", onPointerDown);
    canvas.addEventListener("pointermove", onPointerMove);
    canvas.addEventListener("pointerup", onPointerUp);
    canvas.addEventListener("pointercancel", onPointerUp);
    canvas.addEventListener("wheel", onWheel, { passive: false });

    resize();
    raf = requestAnimationFrame(frame);

    const ro = new ResizeObserver(resize);
    ro.observe(canvas);

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      canvas.removeEventListener("pointerdown", onPointerDown);
      canvas.removeEventListener("pointermove", onPointerMove);
      canvas.removeEventListener("pointerup", onPointerUp);
      canvas.removeEventListener("pointercancel", onPointerUp);
      canvas.removeEventListener("wheel", onWheel);
    };
  }, [memories, reduced]);

  return <canvas ref={canvasRef} className="universe__canvas" />;
}
