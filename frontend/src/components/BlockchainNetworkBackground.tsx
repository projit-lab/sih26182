import { useEffect, useRef } from 'react';

interface Node {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  isBlock: boolean;
  pulsePhase: number;
  label?: string;
}

interface Packet {
  sourceIndex: number;
  targetIndex: number;
  progress: number;
  speed: number;
}

const HASH_LABELS = ['0x8f2c', 'blk#814', '0xbc1q', 'tx#992', '0x3a4b', 'node_v2', '0x99fe', 'p2p_mesh'];

export function BlockchainNetworkBackground() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const mouse = { x: -1000, y: -1000 };

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };

    const handleMouseMove = (e: MouseEvent) => {
      mouse.x = e.clientX;
      mouse.y = e.clientY;
    };

    const handleMouseLeave = () => {
      mouse.x = -1000;
      mouse.y = -1000;
    };

    window.addEventListener('resize', handleResize);
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseleave', handleMouseLeave);

    // Generate balanced network nodes
    const nodeCount = Math.floor(Math.min(width, 1600) / 28);
    const nodes: Node[] = [];

    for (let i = 0; i < nodeCount; i++) {
      const isBlock = i % 5 === 0;
      nodes.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.45,
        vy: (Math.random() - 0.5) * 0.45,
        radius: isBlock ? 3.5 + Math.random() * 1.5 : 2 + Math.random() * 1.2,
        isBlock,
        pulsePhase: Math.random() * Math.PI * 2,
        label: isBlock && Math.random() > 0.4 ? HASH_LABELS[i % HASH_LABELS.length] : undefined,
      });
    }

    // Dynamic transaction packets flowing between connected nodes
    const packets: Packet[] = [];
    const maxPackets = 12;

    const render = () => {
      ctx.clearRect(0, 0, width, height);

      // Update and draw nodes
      for (let i = 0; i < nodes.length; i++) {
        const n = nodes[i];

        // Move node
        n.x += n.vx;
        n.y += n.vy;

        // Bounce at boundaries with slight damping
        if (n.x < 15) { n.x = 15; n.vx *= -1; }
        if (n.x > width - 15) { n.x = width - 15; n.vx *= -1; }
        if (n.y < 15) { n.y = 15; n.vy *= -1; }
        if (n.y > height - 15) { n.y = height - 15; n.vy *= -1; }

        n.pulsePhase += 0.03;
      }

      // Draw connections
      const maxDistance = 145;
      const mouseMaxDistance = 175;

      for (let i = 0; i < nodes.length; i++) {
        const a = nodes[i];

        // Connect to neighboring nodes
        for (let j = i + 1; j < nodes.length; j++) {
          const b = nodes[j];
          const dx = b.x - a.x;
          const dy = b.y - a.y;
          const dist = Math.hypot(dx, dy);

          if (dist < maxDistance) {
            const alpha = (1 - dist / maxDistance) * (a.isBlock || b.isBlock ? 0.28 : 0.16);

            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);

            if (a.isBlock && b.isBlock) {
              ctx.strokeStyle = `rgba(5, 150, 105, ${alpha * 1.4})`;
              ctx.lineWidth = 1.2;
            } else if (a.isBlock || b.isBlock) {
              ctx.strokeStyle = `rgba(16, 185, 129, ${alpha * 1.1})`;
              ctx.lineWidth = 0.9;
            } else {
              ctx.strokeStyle = `rgba(148, 163, 184, ${alpha})`;
              ctx.lineWidth = 0.7;
            }
            ctx.stroke();

            // Chance to spawn packet along link
            if (packets.length < maxPackets && Math.random() < 0.0015) {
              packets.push({
                sourceIndex: i,
                targetIndex: j,
                progress: 0,
                speed: 0.008 + Math.random() * 0.008,
              });
            }
          }
        }

        // Interactive mouse connection
        const mouseDist = Math.hypot(a.x - mouse.x, a.y - mouse.y);
        if (mouseDist < mouseMaxDistance) {
          const mAlpha = (1 - mouseDist / mouseMaxDistance) * 0.35;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(mouse.x, mouse.y);
          ctx.strokeStyle = `rgba(5, 150, 105, ${mAlpha})`;
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      }

      // Draw and update transaction packets
      for (let pIdx = packets.length - 1; pIdx >= 0; pIdx--) {
        const p = packets[pIdx];
        p.progress += p.speed;

        if (p.progress >= 1) {
          packets.splice(pIdx, 1);
          continue;
        }

        const source = nodes[p.sourceIndex];
        const target = nodes[p.targetIndex];
        if (!source || !target) {
          packets.splice(pIdx, 1);
          continue;
        }

        const px = source.x + (target.x - source.x) * p.progress;
        const py = source.y + (target.y - source.y) * p.progress;

        ctx.beginPath();
        ctx.arc(px, py, 2.2, 0, Math.PI * 2);
        ctx.fillStyle = '#059669';
        ctx.shadowColor = 'rgba(5, 150, 105, 0.4)';
        ctx.shadowBlur = 6;
        ctx.fill();
        ctx.shadowBlur = 0; // reset
      }

      // Draw Nodes on top of lines
      for (let i = 0; i < nodes.length; i++) {
        const n = nodes[i];

        if (n.isBlock) {
          // Emerald validator/block node
          const pulse = (Math.sin(n.pulsePhase) + 1) * 0.5; // 0 to 1

          // Outer halo ring
          ctx.beginPath();
          ctx.arc(n.x, n.y, n.radius + 3.5 + pulse * 2.5, 0, Math.PI * 2);
          ctx.strokeStyle = `rgba(5, 150, 105, ${0.15 + pulse * 0.18})`;
          ctx.lineWidth = 1;
          ctx.stroke();

          // Main node circle
          ctx.beginPath();
          ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
          ctx.fillStyle = '#059669';
          ctx.fill();

          // Inner white dot
          ctx.beginPath();
          ctx.arc(n.x, n.y, 1.4, 0, Math.PI * 2);
          ctx.fillStyle = '#FFFFFF';
          ctx.fill();

          // Label
          if (n.label) {
            ctx.font = '9px "JetBrains Mono", monospace';
            ctx.fillStyle = 'rgba(100, 116, 139, 0.65)';
            ctx.fillText(n.label, n.x + n.radius + 4, n.y + 3);
          }
        } else {
          // Standard network node (clean slate gray)
          ctx.beginPath();
          ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
          ctx.fillStyle = 'rgba(100, 116, 139, 0.55)';
          ctx.fill();
        }
      }

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseleave', handleMouseLeave);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        pointerEvents: 'none',
        zIndex: 0,
        opacity: 0.85,
      }}
      aria-hidden="true"
    />
  );
}
