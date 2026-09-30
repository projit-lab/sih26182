import { useState } from 'react';
import type { AttributeResponse } from '../types';

interface ResultsScreenProps {
  result: AttributeResponse;
  onViewGraph: () => void;
  onNewQuery: () => void;
}

function fmt(n: number | null | undefined): string {
  if (n == null) return '—';
  return n.toFixed(4);
}

function shortAddr(addr: string): string {
  if (addr.length <= 22) return addr;
  return `${addr.slice(0, 10)}…${addr.slice(-8)}`;
}

export function ResultsScreen({ result, onViewGraph }: ResultsScreenProps) {
  const {
    ranked_candidates = [],
    scores = {},
    unreachable = [],
    separation_ratio,
    candidate_labels = {},
    candidate_names = {},
    label_sources = {},
    hop_depths = {},
    dijkstra_comparison = null,
    degree_corrected = false,
    graph = { nodes: 0, edges: 0 },
    suspect_component_size = 0,
    max_hops = null,
    depth_nodes = 0,
    depth_edges = 0,
    unreachable_reasons = {},
  } = result as any; // Using any for new fields since types.ts wasn't fully updated here

  const [copiedAddr, setCopiedAddr] = useState<string | null>(null);
  const [reportCopied, setReportCopied] = useState<boolean>(false);

  const labelMap: Record<string, string> = { ...candidate_names, ...candidate_labels };

  const topCandidate = ranked_candidates[0];
  const topCandidateName = labelMap[topCandidate] || (topCandidate ? shortAddr(topCandidate) : 'None');
  const topScoreStr = topCandidate && scores[topCandidate] != null ? `${fmt(scores[topCandidate])} Ω` : '—';

  const totalCandidatesCount = ranked_candidates.length + unreachable.length;

  const handleCopyAddress = (addr: string) => {
    navigator.clipboard.writeText(addr);
    setCopiedAddr(addr);
    setTimeout(() => setCopiedAddr(null), 1800);
  };

  const handleCopyReport = () => {
    const lines = [
      'LEDGERHAWK ATTRIBUTION INVESTIGATION REPORT',
      '------------------------------------------------------------',
      `Suspect wallet: ${result.suspect}`,
      `Best match: ${topCandidateName} (${topCandidate || 'N/A'})`,
      `Separation ratio: ${separation_ratio != null ? `${separation_ratio.toFixed(2)}x` : 'N/A'} over next candidate`,
      `Effective resistance (R_eff): ${topScoreStr}`,
      `Hop depth: ${hop_depths[topCandidate] != null ? `${hop_depths[topCandidate]} hops` : 'N/A'}`,
      `Graph size: ${graph.nodes} nodes, ${graph.edges} edges`,
      `Total candidates evaluated: ${totalCandidatesCount}`,
      '',
      'CANDIDATE BREAKDOWN:',
      ...ranked_candidates.map((c: string, idx: number) => {
        const name = labelMap[c] || c;
        const score = scores[c] != null ? `${fmt(scores[c])} Ω` : '—';
        const hops = hop_depths[c] != null ? `${hop_depths[c]} hops` : '—';
        let status = idx === 0 ? 'Top ranked' : `Rank ${idx + 1}`;
        if (result.synthetic && result.truth === c) status = 'Ground truth';
        else if (result.synthetic && result.dijkstra_comparison?.winner === c) status = 'Shortest-path pick';
        return `${idx + 1}. [${status}] ${name} (${c})\n   R_eff: ${score} | Depth: ${hops}`;
      }),
      ...unreachable.map((c: string, idx: number) => {
        const name = labelMap[c] || c;
        return `${ranked_candidates.length + idx + 1}. [Disconnected] ${name} (${c})\n   R_eff: ∞ (null) | Depth: ∞ hops`;
      }),
      '------------------------------------------------------------',
    ];

    navigator.clipboard.writeText(lines.join('\n'));
    setReportCopied(true);
    setTimeout(() => setReportCopied(false), 2000);
  };

  const handleExportJSON = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(result, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `ledgerhawk_attribution_${result.suspect.slice(0, 8)}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div className="analyst-results-wrap">
      {/* Title Header below Ledgerhawk */}
      <div className="analyst-screen-header">
        <div>
          <h1 className="analyst-page-title">
            Attribution Investigation
          </h1>

          <div className="analyst-suspect-bar">
            <span>Suspect wallet:</span>
            <button
              type="button"
              onClick={() => handleCopyAddress(result.suspect)}
              title={result.suspect}
              className="analyst-suspect-chip"
            >
              <span>{shortAddr(result.suspect)}</span>
              <span style={{ fontSize: 10, color: copiedAddr === result.suspect ? '#22c55e' : '#8b919b' }}>
                {copiedAddr === result.suspect ? 'copied' : 'copy'}
              </span>
            </button>
          </div>
        </div>
      </div>

      {/* Main Element: Centered Candidates Table */}
      <div className="analyst-center-content">
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, marginBottom: 16, fontSize: 13, color: '#8b919b', background: '#0F172A', padding: 12, borderRadius: 8, border: '1px solid #1E293B' }}>
          <div><strong>Separation ratio:</strong> {separation_ratio != null ? `${separation_ratio.toFixed(2)}x` : '—'}</div>
          <div><strong>Degree correction:</strong> {degree_corrected ? 'on' : 'off'}</div>
          <div>
            <strong>Search depth:</strong> {max_hops !== null 
              ? `${max_hops} hops - ${depth_nodes || suspect_component_size || (result.graph_elements?.nodes?.length ?? 0)} nodes, ${depth_edges || 0} edges analysed`
              : `Whole case graph: ${graph.nodes} nodes (${suspect_component_size || (result.graph_elements?.nodes?.length ?? 0)} connected to the suspect)`
            }
          </div>
          {dijkstra_comparison && (
             <div style={{ width: '100%' }}><strong>Shortest path check:</strong> {dijkstra_comparison.flaw}</div>
          )}
          {result.synthetic && (
            <div style={{ width: '100%' }}>
              <strong>Ground truth: {labelMap[result.truth!] || result.truth}</strong>
              <div style={{ color: '#64748b', marginTop: 4 }}>
                Synthetic benchmark case. ER is right and shortest path is wrong in {result.er_wins} {result.er_wins === 1 ? 'case' : 'cases'}; the reverse in {result.sp_wins} {result.sp_wins === 1 ? 'case' : 'cases'} (seed 42). {result.full_nodes ? `Shown: 400-node neighbourhood of a ${result.full_nodes}-node benchmark graph.` : ''}
              </div>
            </div>
          )}
        </div>

        {/* Action buttons directly above the table */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 8, marginBottom: 10 }}>
          <button type="button" onClick={handleCopyReport} className="analyst-btn">
            {reportCopied ? 'Report copied' : 'Copy report'}
          </button>
          <button type="button" onClick={handleExportJSON} className="analyst-btn">
            Export JSON
          </button>
          <button type="button" onClick={onViewGraph} className="analyst-btn-primary">
            View evidence graph
          </button>
        </div>

        <div className="analyst-table-card">
          <div style={{ overflowX: 'auto' }}>
            <table className="analyst-table" aria-label="Candidate attribution results">
              <thead>
                <tr>
                  <th className="analyst-th" style={{ width: 50 }}>Rank</th>
                  <th className="analyst-th">Candidate endpoint</th>
                  <th className="analyst-th" style={{ width: 170 }}>Wallet address</th>
                  <th className="analyst-th num" style={{ width: 120 }}>Score</th>
                  <th className="analyst-th num" style={{ width: 120 }}>Raw R_eff</th>
                  <th className="analyst-th num" style={{ width: 95 }}>Hop depth</th>
                  <th className="analyst-th" style={{ width: 120 }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {/* Ranked Candidates */}
                {ranked_candidates.map((vasp: string, idx: number) => {
                  const score = scores[vasp];
                  const entityName = labelMap[vasp] || shortAddr(vasp);
                  const isTop = idx === 0;
                  const hops = hop_depths[vasp];
                  const isCopied = copiedAddr === vasp;
                  const sourceStr = label_sources[vasp];

                  return (
                    <tr key={vasp} className={`analyst-tr ${isTop ? 'matched' : ''}`}>
                      <td className="analyst-td" style={{ color: isTop ? '#22c55e' : '#8b919b', fontWeight: isTop ? 600 : 400 }}>
                        {idx + 1}
                      </td>

                      <td className="analyst-td">
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, alignItems: 'flex-start' }}>
                          <span style={{ fontWeight: isTop ? 600 : 400, color: isTop ? '#e6e8ec' : '#d2d6dc' }}>
                            {entityName}
                          </span>
                          {sourceStr && (
                            <span style={{ fontSize: 9, background: '#1e293b', padding: '2px 6px', borderRadius: 4, color: '#94a3b8' }}>
                              label: {sourceStr}
                            </span>
                          )}
                        </div>
                      </td>

                      <td className="analyst-td">
                        <button
                          type="button"
                          onClick={() => handleCopyAddress(vasp)}
                          title={vasp}
                          className="analyst-addr-cell"
                        >
                          <span>{shortAddr(vasp)}</span>
                          <span style={{ fontSize: 10, color: isCopied ? '#22c55e' : '#6b7280' }}>
                            {isCopied ? 'copied' : 'copy'}
                          </span>
                        </button>
                      </td>

                      <td className="analyst-td num" style={{ color: isTop ? '#22c55e' : '#e6e8ec', fontWeight: isTop ? 600 : 400 }}>
                        {fmt(score)}
                      </td>

                      <td className="analyst-td num" style={{ color: '#e6e8ec' }}>
                        {result.raw_resistance[vasp] != null ? result.raw_resistance[vasp].toFixed(4) : '—'}
                      </td>

                      <td className="analyst-td num" style={{ color: '#8b919b' }}>
                        {hops != null ? `${hops}` : '—'}
                      </td>

                      <td className="analyst-td">
                        {(() => {
                           if (result.synthetic && result.truth === vasp) {
                             return <span style={{ color: '#0ea5e9', fontWeight: 500 }}>Ground truth</span>;
                           }
                           if (result.synthetic && result.dijkstra_comparison?.winner === vasp) {
                             return <span style={{ color: '#d97706', fontWeight: 500 }}>Shortest-path pick</span>;
                           }
                           if (isTop) {
                             return <span style={{ color: '#22c55e', fontWeight: 500 }}>Top ranked</span>;
                           }
                           return <span style={{ color: '#8b919b' }}>Rank {idx + 1}</span>;
                        })()}
                      </td>
                    </tr>
                  );
                })}

                {/* Disconnected Candidates Header */}
                {unreachable.length > 0 && (
                  <tr>
                    <td colSpan={7} style={{ padding: '16px 16px 8px', color: '#94a3b8', fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      No path found
                    </td>
                  </tr>
                )}

                {/* Disconnected Candidates */}
                {unreachable.map((vasp: string) => {
                  const entityName = labelMap[vasp] || shortAddr(vasp);
                  const isCopied = copiedAddr === vasp;
                  const sourceStr = label_sources[vasp];

                  return (
                    <tr key={vasp} className="analyst-tr">
                      <td className="analyst-td" style={{ color: '#8b919b' }}>
                        —
                      </td>

                      <td className="analyst-td">
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, alignItems: 'flex-start' }}>
                          <span style={{ color: '#8b919b' }}>
                            {entityName}
                          </span>
                          {sourceStr && (
                            <span style={{ fontSize: 9, background: '#1e293b', padding: '2px 6px', borderRadius: 4, color: '#64748b' }}>
                              label: {sourceStr}
                            </span>
                          )}
                        </div>
                      </td>

                      <td className="analyst-td">
                        <button
                          type="button"
                          onClick={() => handleCopyAddress(vasp)}
                          title={vasp}
                          className="analyst-addr-cell"
                        >
                          <span>{shortAddr(vasp)}</span>
                          <span style={{ fontSize: 10, color: isCopied ? '#c0564b' : '#6b7280' }}>
                            {isCopied ? 'copied' : 'copy'}
                          </span>
                        </button>
                      </td>

                      <td className="analyst-td num" style={{ color: '#8b919b' }}>
                        —
                      </td>

                      <td className="analyst-td num" style={{ color: '#8b919b' }}>
                        —
                      </td>

                      <td className="analyst-td num" style={{ color: '#8b919b' }}>
                        ∞
                      </td>

                      <td className="analyst-td">
                        <span style={{ color: '#c0564b' }}>
                          No path
                        </span>
                        {unreachable_reasons[vasp] && (
                          <div style={{ fontSize: 10, color: '#8b919b', marginTop: 2 }}>
                            {unreachable_reasons[vasp]}
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div style={{ marginTop: 12, fontSize: 11, color: '#8b919b', fontStyle: 'italic', paddingLeft: 4 }}>
            Score = raw R_eff, degree-corrected when 'Degree correction: on'. Lower = stronger connection.
          </div>
        </div>
      </div>
    </div>
  );
}
