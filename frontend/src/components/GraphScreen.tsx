import { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { ChevronLeft, RefreshCw, ZoomIn, ZoomOut, Info, BarChart2, Minus } from 'lucide-react';
import type { AttributeResponse } from '../types';

interface GraphScreenProps {
  result: AttributeResponse;
  onBack: () => void;
}

interface RenderNode extends d3.SimulationNodeDatum {
  id: string;
  label: string;
  role: 'suspect' | 'hop' | 'mixer_hop' | 'candidate_vasp' | 'unreachable';
  entity?: string;
  category?: string;
  level: number;
  amountBtc?: number;
  score?: number | null;
  rank?: number;
  x?: number;
  y?: number;
}

interface RenderEdge extends d3.SimulationLinkDatum<RenderNode> {
  id: string;
  source: any;
  target: any;
  amountBtc: number;
  branchType?: 'decoy' | 'swarm' | 'direct';
  txHash?: string;
}

const ROLE_COLORS: Record<string, string> = {
  suspect: '#dc2626',        // Crimson Red - Suspect root
  candidate_vasp: '#059669', // Emerald - True VASP exit
  mixer_hop: '#7c3aed',      // Purple - Mixer channel
  hop: '#2563eb',            // Blue - Relay / Mule
  unreachable: '#9ca3af',    // Muted Grey - Unreachable
};

export function GraphScreen({ result, onBack }: GraphScreenProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const zoomBehaviorRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null);
  const [layoutMode] = useState<'branching' | 'force'>('force');
  const [selectedNode, setSelectedNode] = useState<RenderNode | null>(null);
  const [hoveredEdge, setHoveredEdge] = useState<RenderEdge | null>(null);
  const [isLegendOpen, setIsLegendOpen] = useState(false);
  const [isAttributesOpen, setIsAttributesOpen] = useState(false);


  if (!result.graph_elements || result.graph_elements.nodes.length === 0) {
    return (
      <div className="graph-screen">
        <div style={{ padding: 16 }}>
          <button className="btn-secondary" onClick={onBack} id="graph-back-btn" style={{
            background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)', backdropFilter: 'blur(10px)',
          }}>
            <ChevronLeft size={14} /> Back to Results
          </button>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--muted)' }}>
          Graph data unavailable for this result
        </div>
      </div>
    );
  }

  // Extract nodes and edges with dynamic hop depth filtering
  const { nodesData, edgesData, totalNodeCount, totalEdgeCount } = (() => {
    const candidateRanks = new Map<string, number>();
    result.ranked_candidates.forEach((c, idx) => candidateRanks.set(c, idx + 1));

    let allNodes: RenderNode[] = result.graph_elements!.nodes.map((n) => ({
      ...n,
      level: n.level ?? 0,
      amountBtc: n.amountBtc,
      role: n.role as RenderNode['role'],
      rank: candidateRanks.get(n.id)
    }));

    let allEdges: RenderEdge[] = result.graph_elements!.edges.map((e) => ({
      ...e,
      source: e.source,
      target: e.target,
      amountBtc: e.amountBtc,
      txHash: e.txHash,
    }));

    const filteredNodes = allNodes; // Show all for now since level is not guaranteed
    const visibleNodeIds = new Set(filteredNodes.map((n) => n.id));
    const filteredEdges = allEdges.filter(
      (e) =>
        visibleNodeIds.has(typeof e.source === 'string' ? e.source : e.source.id) &&
        visibleNodeIds.has(typeof e.target === 'string' ? e.target : e.target.id)
    );

    return {
      nodesData: filteredNodes,
      edgesData: filteredEdges,
      totalNodeCount: allNodes.length,
      totalEdgeCount: allEdges.length,
    };
  })();

  useEffect(() => {
    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const width = svgRef.current.clientWidth || 1000;
    const height = svgRef.current.clientHeight || 700;
    const W = width;
    const H = height;

    // Marker defs for directional arrows
    const defs = svg.append('defs');

    // Arrow markers
    ['decoy', 'swarm', 'default'].forEach((type) => {
      const color = type === 'decoy' ? '#d97706' : type === 'swarm' ? '#059669' : '#A1A1AA';
      defs.append('marker')
        .attr('id', `arrow-${type}`)
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 22)
        .attr('refY', 0)
        .attr('markerWidth', 6)
        .attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-4L8,0L0,4')
        .attr('fill', color);
    });

    // Subtle glow filter
    const glow = defs.append('filter').attr('id', 'glow');
    glow.append('feGaussianBlur').attr('stdDeviation', '3').attr('result', 'coloredBlur');
    const feMerge = glow.append('feMerge');
    feMerge.append('feMergeNode').attr('in', 'coloredBlur');
    feMerge.append('feMergeNode').attr('in', 'SourceGraphic');

    const g = svg.append('g').attr('class', 'main-container');

    // Zoom setup
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.3, 3.5])
      .on('zoom', (event) => {
        g.attr('transform', event.transform.toString());
      });

    svg.call(zoom);
    zoomBehaviorRef.current = zoom;

    // Clone data for render
    const nodes: RenderNode[] = nodesData.map((d) => ({ ...d }));
    const nodeMap = new Map<string, RenderNode>(nodes.map((n) => [n.id, n]));

    const links: RenderEdge[] = edgesData
      .map((e) => ({
        ...e,
        source: nodeMap.get(typeof e.source === 'string' ? e.source : e.source.id)!,
        target: nodeMap.get(typeof e.target === 'string' ? e.target : e.target.id)!,
      }))
      .filter((e) => e.source && e.target);

    // ==========================================
    // LAYOUT 1: HIERARCHICAL BRANCHING (LEFT-TO-RIGHT)
    // ==========================================
    if (layoutMode === 'branching') {
      const levelGroups: Record<number, RenderNode[]> = {};
      nodes.forEach((n) => {
        const lvl = n.level ?? 0;
        if (!levelGroups[lvl]) levelGroups[lvl] = [];
        levelGroups[lvl].push(n);
      });

      const maxLevel = Math.max(...nodes.map((n) => n.level ?? 0), 1);
      const horizontalSpacing = Math.max(140, (W - 320) / maxLevel);
      const startX = 140;

      Object.keys(levelGroups).forEach((lvlStr) => {
        const lvl = Number(lvlStr);
        const group = levelGroups[lvl];
        const groupCount = group.length;
        const totalHeight = Math.min(H - 120, groupCount * 90);
        const startY = (H - totalHeight) / 2 + 30;
        const stepY = groupCount > 1 ? totalHeight / (groupCount - 1) : 0;

        group.forEach((node, i) => {
          node.x = startX + lvl * horizontalSpacing;
          node.y = groupCount === 1 ? H / 2 : startY + i * stepY;
        });
      });

      // Draw Branch Links (Curved Bezier Paths)
      g.append('g')
        .attr('class', 'links')
        .selectAll('path')
        .data(links)
        .join('path')
        .attr('d', (d) => {
          const s = d.source as RenderNode;
          const t = d.target as RenderNode;
          const sx = s.x ?? 0;
          const sy = s.y ?? 0;
          const tx = t.x ?? 0;
          const ty = t.y ?? 0;
          const dx = tx - sx;
          return `M ${sx} ${sy} C ${sx + dx * 0.45} ${sy}, ${tx - dx * 0.45} ${ty}, ${tx} ${ty}`;
        })
        .attr('fill', 'none')
        .attr('stroke', (d) => {
          if (d.branchType === 'decoy') return 'rgba(217, 119, 6, 0.70)';
          if (d.branchType === 'swarm') return 'rgba(5, 150, 105, 0.78)';
          return 'rgba(161, 161, 170, 0.50)';
        })
        .attr('stroke-width', (d) => {
          if (d.amountBtc >= 50) return 4;
          if (d.amountBtc >= 20) return 2.5;
          return 1.5;
        })
        .attr('marker-end', (d) => {
          if (d.branchType === 'decoy') return 'url(#arrow-decoy)';
          if (d.branchType === 'swarm') return 'url(#arrow-swarm)';
          return 'url(#arrow-default)';
        })
        .style('cursor', 'pointer')
        .on('mouseenter', (_, d) => setHoveredEdge(d))
        .on('mouseleave', () => setHoveredEdge(null));

      // Flow volume badges along the edges
      g.append('g')
        .attr('class', 'edge-labels')
        .selectAll('text')
        .data(links)
        .join('text')
        .attr('x', (d) => ((d.source.x + d.target.x) / 2))
        .attr('y', (d) => ((d.source.y + d.target.y) / 2) - 8)
        .attr('text-anchor', 'middle')
        .attr('fill', (d) => d.branchType === 'decoy' ? '#d97706' : '#059669')
        .attr('font-size', '10px')
        .attr('font-family', 'ui-monospace, monospace')
        .attr('font-weight', '700')
        .text((d) => d.amountBtc > 0 ? `${d.amountBtc.toFixed(4)} BTC` : '');

      // Initial center fit
      svg.transition().duration(400).call(
        zoom.transform,
        d3.zoomIdentity.translate(40, 15).scale(0.88)
      );
    } else {
      // ==========================================
      // LAYOUT 2: FORCE-DIRECTED SWARM
      // ==========================================
      const simulation = d3.forceSimulation<RenderNode>(nodes)
        .force('link', d3.forceLink<RenderNode, RenderEdge>(links).id((d) => d.id).distance(100).strength(0.7))
        .force('charge', d3.forceManyBody().strength(-280))
        .force('center', d3.forceCenter(W / 2, H / 2))
        .force('collision', d3.forceCollide().radius(35));

      const link = g.append('g')
        .attr('class', 'links')
        .selectAll('line')
        .data(links)
        .join('line')
        .attr('stroke', (d) => d.branchType === 'decoy' ? '#d97706' : '#059669')
        .attr('stroke-width', 2);

      simulation.on('tick', () => {
        link
          .attr('x1', (d) => (d.source as RenderNode).x ?? 0)
          .attr('y1', (d) => (d.source as RenderNode).y ?? 0)
          .attr('x2', (d) => (d.target as RenderNode).x ?? 0)
          .attr('y2', (d) => (d.target as RenderNode).y ?? 0);

        nodeGroup.attr('transform', (d) => `translate(${d.x ?? 0},${d.y ?? 0})`);
      });
    }

    // Draw Nodes
    const nodeGroup = g.append('g')
      .attr('class', 'nodes')
      .selectAll<SVGGElement, RenderNode>('g')
      .data(nodes)
      .join('g')
      .attr('transform', (d) => `translate(${d.x ?? 0},${d.y ?? 0})`)
      .style('cursor', 'pointer')
      .on('click', (_, d) => setSelectedNode(d));

    // Outer glow ring for suspect and true VASP
    nodeGroup.filter((d) => d.role === 'suspect' || (d.role === 'candidate_vasp' && d.rank === 1))
      .append('circle')
      .attr('r', (d) => d.role === 'suspect' ? 22 : 19)
      .attr('fill', 'none')
      .attr('stroke', (d) => ROLE_COLORS[d.role])
      .attr('stroke-width', 2)
      .attr('opacity', 0.4)
      .attr('filter', 'url(#glow)');

    // Main Circle with dark canvas stroke
    nodeGroup.append('circle')
      .attr('r', (d) => {
        if (d.role === 'suspect') return 18;
        if (d.role === 'candidate_vasp') return 16;
        if (d.role === 'mixer_hop') return 14;
        return 11;
      })
      .attr('fill', (d) => ROLE_COLORS[d.role] || '#71717A')
      .attr('stroke', '#070B14')
      .attr('stroke-width', 2.5);

    // Inner icon / text
    nodeGroup.filter((d) => d.role === 'suspect')
      .append('text')
      .attr('dy', 4)
      .attr('text-anchor', 'middle')
      .attr('fill', '#FFFFFF')
      .attr('font-size', '10px')
      .attr('font-weight', '700')
      .text('ROOT');

    nodeGroup.filter((d) => d.role === 'candidate_vasp')
      .append('text')
      .attr('dy', 4)
      .attr('text-anchor', 'middle')
      .attr('fill', '#FFFFFF')
      .attr('font-size', '10px')
      .attr('font-weight', '700')
      .text((d) => d.rank ? `#${d.rank}` : 'V');

    // Label beneath nodes (crisp light text on dark canvas)
    nodeGroup.append('text')
      .attr('dy', (d) => (d.role === 'suspect' ? 32 : 28))
      .attr('text-anchor', 'middle')
      .attr('fill', '#F8FAFC')
      .attr('font-size', '11px')
      .attr('font-family', 'ui-monospace, monospace')
      .attr('font-weight', (d) => d.role === 'suspect' || d.role === 'candidate_vasp' ? '700' : '600')
      .text((d) => d.label);

    // Sub-label for entity tag
    nodeGroup.filter((d) => !!d.entity && d.role !== 'hop')
      .append('text')
      .attr('dy', (d) => (d.role === 'suspect' ? 44 : 40))
      .attr('text-anchor', 'middle')
      .attr('fill', (d) => d.role === 'suspect' ? '#dc2626' : d.rank === 1 ? '#059669' : '#71717A')
      .attr('font-size', '10px')
      .attr('font-weight', '600')
      .text((d) => d.entity || '');

  }, [nodesData, edgesData, layoutMode]);

  const handleResetZoom = () => {
    if (svgRef.current && zoomBehaviorRef.current) {
      d3.select(svgRef.current).transition().duration(500).call(
        zoomBehaviorRef.current.transform,
        d3.zoomIdentity.translate(20, 0).scale(0.92)
      );
    }
  };

  const handleZoom = (factor: number) => {
    if (svgRef.current && zoomBehaviorRef.current) {
      d3.select(svgRef.current).transition().duration(300).call(
        zoomBehaviorRef.current.scaleBy,
        factor
      );
    }
  };


  return (
    <div className="graph-screen">
      {/* Top Floating Control Bar */}
      <div style={{
        position: 'absolute',
        top: 16,
        left: 16,
        right: 16,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        zIndex: 20,
        pointerEvents: 'none',
      }}>
        <div style={{ display: 'flex', gap: 10, pointerEvents: 'auto' }}>
          <button className="btn-secondary" onClick={onBack} id="graph-back-btn" style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            color: 'var(--text)',
            backdropFilter: 'blur(10px)',
          }}>
            <ChevronLeft size={14} />
            Back to Results
          </button>



          <button
            onClick={() => setIsLegendOpen((prev) => !prev)}
            className={`graph-panel-pill ${isLegendOpen ? 'active' : ''}`}
            title={isLegendOpen ? 'Hide Topology Legend' : 'Show Topology Legend'}
          >
            <Info size={13} />
            Legend {isLegendOpen ? '▾' : '▸'}
          </button>

          <button
            onClick={() => setIsAttributesOpen((prev) => !prev)}
            className={`graph-panel-pill ${isAttributesOpen ? 'active' : ''}`}
            title={isAttributesOpen ? 'Hide Graph Attributes' : 'Show Graph Attributes'}
          >
            <BarChart2 size={13} />
            Attributes {isAttributesOpen ? '▾' : '▸'}
          </button>
        </div>

        <div style={{ display: 'flex', gap: 8, pointerEvents: 'auto' }}>
          <button
            onClick={() => handleZoom(1.25)}
            title="Zoom In"
            style={{
              background: 'var(--surface)',
              border: '1px solid var(--border)',
              color: 'var(--text)',
              borderRadius: 7,
              width: 32,
              height: 32,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              boxShadow: 'var(--shadow-sm)',
            }}
          >
            <ZoomIn size={15} />
          </button>
          <button
            onClick={() => handleZoom(0.8)}
            title="Zoom Out"
            style={{
              background: 'var(--surface)',
              border: '1px solid var(--border)',
              color: 'var(--text)',
              borderRadius: 7,
              width: 32,
              height: 32,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              boxShadow: 'var(--shadow-sm)',
            }}
          >
            <ZoomOut size={15} />
          </button>
          <button
            onClick={handleResetZoom}
            title="Reset Zoom"
            style={{
              background: 'var(--surface)',
              border: '1px solid var(--border)',
              color: 'var(--text)',
              borderRadius: 7,
              width: 32,
              height: 32,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              boxShadow: 'var(--shadow-sm)',
            }}
          >
            <RefreshCw size={14} />
          </button>

        </div>
      </div>

      {/* Graph Canvas */}
      <div className="graph-canvas-wrap">
        <svg ref={svgRef} width="100%" height="100%" />
      </div>

      {/* Legend — Minimizable */}
      {isLegendOpen ? (
        <div className="graph-legend fade-in" style={{ top: 72, left: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <div className="legend-title" style={{ margin: 0 }}>Topology Legend</div>
            <button
              onClick={() => setIsLegendOpen(false)}
              title="Minimize Legend"
              style={{
                background: 'var(--surface-subtle)',
                border: '1px solid var(--border)',
                color: 'var(--muted)',
                borderRadius: 4,
                padding: '2px 6px',
                cursor: 'pointer',
                fontSize: 11,
                display: 'flex',
                alignItems: 'center',
                gap: 4,
              }}
            >
              <Minus size={11} />
              <span>Hide</span>
            </button>
          </div>
          <div className="legend-row">
            <div className="legend-dot" style={{ background: ROLE_COLORS.suspect }} />
            Suspect Root Wallet
          </div>
          <div className="legend-row">
            <div className="legend-dot" style={{ background: ROLE_COLORS.hop }} />
            Relay & Mule Forwarder
          </div>
          <div className="legend-row">
            <div className="legend-dot" style={{ background: ROLE_COLORS.mixer_hop }} />
            Mixer Swarm Channel
          </div>
          <div className="legend-row">
            <div className="legend-dot" style={{ background: ROLE_COLORS.candidate_vasp }} />
            Candidate VASP (Exit)
          </div>
          <div className="legend-row">
            <div className="legend-dot" style={{ background: ROLE_COLORS.unreachable }} />
            Unreachable (No Path)
          </div>


        </div>
      ) : (
        <button
          onClick={() => setIsLegendOpen(true)}
          className="graph-panel-pill"
          style={{ position: 'absolute', top: 72, left: 16, zIndex: 15 }}
          title="Expand Topology Legend"
        >
          <Info size={13} />
          Topology Legend
        </button>
      )}

      {/* Graph Attributes — Minimizable */}
      {isAttributesOpen ? (
        <div className="graph-info fade-in" style={{ top: 72, right: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--muted)', margin: 0 }}>
              Graph Attributes
            </div>
            <button
              onClick={() => setIsAttributesOpen(false)}
              title="Minimize Attributes"
              style={{
                background: 'var(--surface-subtle)',
                border: '1px solid var(--border)',
                color: 'var(--muted)',
                borderRadius: 4,
                padding: '2px 6px',
                cursor: 'pointer',
                fontSize: 11,
                display: 'flex',
                alignItems: 'center',
                gap: 4,
              }}
            >
              <Minus size={11} />
              <span>Hide</span>
            </button>
          </div>
          <div className="graph-info-row">
            <span>Traversal Depth</span>
            <span className="graph-info-val">
              {result.max_hops !== null ? `${result.max_hops} Hops` : 'All'}
            </span>
          </div>
          <div className="graph-info-row">
            <span>Visible Nodes</span>
            <span className="graph-info-val">{nodesData.length} / {totalNodeCount}</span>
          </div>
          <div className="graph-info-row">
            <span>Visible Flows</span>
            <span className="graph-info-val">{edgesData.length} / {totalEdgeCount}</span>
          </div>

          {result.truncated && (
            <div style={{
              marginTop: 8,
              padding: '6px 8px',
              background: 'var(--gold-dim)',
              border: '1px solid rgba(217, 119, 6, 0.25)',
              borderRadius: 5,
              fontSize: 10,
              color: '#92400e',
            }}>
              ⚠ Partial data shown
            </div>
          )}
        </div>
      ) : (
        <button
          onClick={() => setIsAttributesOpen(true)}
          className="graph-panel-pill"
          style={{ position: 'absolute', top: 72, right: 16, zIndex: 15 }}
          title="Expand Graph Attributes"
        >
          <BarChart2 size={13} />
          Graph Attributes
        </button>
      )}

      {/* Node Inspector Drawer */}
      {selectedNode && (
        <div style={{
          position: 'absolute',
          top: 72,
          right: 20,
          width: 320,
          background: 'rgba(255, 255, 255, 0.96)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-lg)',
          backdropFilter: 'blur(16px)',
          padding: '18px 20px',
          boxShadow: 'var(--shadow-lg)',
          zIndex: 30,
          color: 'var(--text)',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{
                width: 10,
                height: 10,
                borderRadius: '50%',
                background: ROLE_COLORS[selectedNode.role] || 'var(--primary)',
              }} />
              <strong style={{ fontSize: 13, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--primary)' }}>
                Node Details
              </strong>
            </div>
            <button
              onClick={() => setSelectedNode(null)}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--muted)',
                fontSize: 16,
                cursor: 'pointer',
              }}
            >
              ✕
            </button>
          </div>

          <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--primary)', marginBottom: 4 }}>
            {selectedNode.entity || selectedNode.label}
          </div>

          <div className="mono" style={{ fontSize: 11, color: 'var(--primary)', wordBreak: 'break-all', marginBottom: 14, background: 'var(--surface-subtle)', padding: '6px 8px', borderRadius: 4, border: '1px solid var(--border)' }}>
            {selectedNode.id}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border)', paddingBottom: 6 }}>
              <span style={{ color: 'var(--muted)' }}>Network Role:</span>
              <span style={{ fontWeight: 600, color: ROLE_COLORS[selectedNode.role] }}>
                {selectedNode.role.replace('_', ' ').toUpperCase()}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border)', paddingBottom: 6 }}>
              <span style={{ color: 'var(--muted)' }}>Hop Level:</span>
              <span className="mono">Level {selectedNode.level}</span>
            </div>
            {selectedNode.amountBtc !== undefined && (
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border)', paddingBottom: 6 }}>
                <span style={{ color: 'var(--muted)' }}>Transaction Volume:</span>
                <span className="mono" style={{ fontWeight: 700, color: '#059669' }}>
                  {selectedNode.amountBtc.toFixed(2)} BTC
                </span>
              </div>
            )}
            {selectedNode.score !== undefined && selectedNode.score !== null && (
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border)', paddingBottom: 6 }}>
                <span style={{ color: 'var(--muted)' }}>R_eff to Suspect:</span>
                <span className="mono" style={{ fontWeight: 700, color: '#059669' }}>
                  {selectedNode.score.toFixed(4)} Ω
                </span>
              </div>
            )}
            {selectedNode.rank && (
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border)', paddingBottom: 6 }}>
                <span style={{ color: 'var(--muted)' }}>Attribution Rank:</span>
                <span style={{ fontWeight: 700, color: selectedNode.rank === 1 ? '#059669' : '#d97706' }}>
                  #{selectedNode.rank} {selectedNode.rank === 1 ? '(Top ranked)' : ''}
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Edge Hover Tooltip */}
      {hoveredEdge && (
        <div style={{
          position: 'absolute',
          bottom: 24,
          left: '50%',
          transform: 'translateX(-50%)',
          background: 'var(--primary)',
          border: '1px solid #27272a',
          borderRadius: 8,
          padding: '10px 16px',
          color: '#FAFAF7',
          fontSize: 12,
          pointerEvents: 'none',
          boxShadow: 'var(--shadow-md)',
          zIndex: 30,
        }}>
          <strong>Flow: {hoveredEdge.amountBtc} BTC</strong> ·
          Branch: <span style={{ color: hoveredEdge.branchType === 'decoy' ? '#f59e0b' : '#34d399', fontWeight: 600 }}>
            {hoveredEdge.branchType?.toUpperCase() || 'STANDARD'}
          </span>
          {hoveredEdge.txHash && <div className="mono" style={{ fontSize: 10, color: '#A1A1AA', marginTop: 2 }}>Tx: {hoveredEdge.txHash}</div>}
        </div>
      )}
    </div>
  );
}
