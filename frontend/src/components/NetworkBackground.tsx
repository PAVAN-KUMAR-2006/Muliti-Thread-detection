import { useEffect, useRef } from "react";

export default function NetworkBackground() {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const cv = ref.current!;
    const cx = cv.getContext("2d")!;
    const dpr = window.devicePixelRatio || 1;
    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let W = 0, H = 0, raf = 0;
    type P = { x: number; y: number; vx: number; vy: number; t: boolean };
    let pts: P[] = [];
    const size = () => {
      W = cv.width = innerWidth * dpr; H = cv.height = innerHeight * dpr;
      pts = Array.from({ length: Math.min(70, Math.floor(innerWidth / 18)) }, () => ({
        x: Math.random() * W, y: Math.random() * H,
        vx: (Math.random() - 0.5) * 0.35 * dpr, vy: (Math.random() - 0.5) * 0.35 * dpr, t: Math.random() < 0.08,
      }));
    };
    const frame = () => {
      cx.clearRect(0, 0, W, H);
      const dark = document.documentElement.dataset.theme !== "light";
      const base = dark ? "76,201,240" : "10,132,198", bad = "248,113,113";
      for (const p of pts) {
        p.x += p.vx; p.y += p.vy;
        if (p.x < 0 || p.x > W) p.vx *= -1;
        if (p.y < 0 || p.y > H) p.vy *= -1;
        cx.beginPath(); cx.arc(p.x, p.y, (p.t ? 3.2 : 1.8) * dpr, 0, 7);
        cx.fillStyle = `rgba(${p.t ? bad : base},${p.t ? 0.9 : 0.6})`; cx.fill();
      }
      const D = 150 * dpr;
      for (let i = 0; i < pts.length; i++) for (let j = i + 1; j < pts.length; j++) {
        const a = pts[i], b = pts[j], d = Math.hypot(a.x - b.x, a.y - b.y);
        if (d < D) {
          cx.strokeStyle = `rgba(${a.t || b.t ? bad : base},${(1 - d / D) * 0.28})`;
          cx.lineWidth = dpr; cx.beginPath(); cx.moveTo(a.x, a.y); cx.lineTo(b.x, b.y); cx.stroke();
        }
      }
      if (!still) raf = requestAnimationFrame(frame);
    };
    size(); frame();
    addEventListener("resize", size);
    return () => { cancelAnimationFrame(raf); removeEventListener("resize", size); };
  }, []);
  return <canvas id="net" ref={ref} aria-hidden="true" />;
}
