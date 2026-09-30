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
    flow_btc = {},
    hop_depths = {},
  } = result;

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
      `Flow captured: ${flow_btc[topCandidate] != null ? `${flow_btc[topCandidate].toFixed(2)} BTC` : 'N/A'}`,
      `Hop depth: ${hop_depths[topCandidate] != null ? `${hop_depths[topCandidate]} hops` : 'N/A'}`,
      `Graph size: ${result.graph.nodes} nodes, ${result.graph.edges} edges`,
      `Total candidates evaluated: ${totalCandidatesCount}`,
      '',
      'CANDIDATE BREAKDOWN:',
      ...ranked_candidates.map((c, idx) => {
        const name = labelMap[c] || c;
        const score = scores[c] != null ? `${fmt(scores[c])} Ω` : '—';
        const flow = flow_btc[c] != null ? `${flow_btc[c].toFixed(2)} BTC` : '—';
        const hops = hop_depths[c] != null ? `${hop_depths[c]} hops` : '—';
        const status = idx === 0 ? 'Matched' : 'Decoy';
        return `${idx + 1}. [${status}] ${name} (${c})\n   R_eff: ${score} | Flow: ${flow} | Depth: ${hops}`;
      }),
      ...unreachable.map((c, idx) => {
        const name = labelMap[c] || c;
        return `${ranked_candidates.length + idx + 1}. [Disconnected] ${name} (${c})\n   R_eff: ∞ (null) | Flow: 0.00 BTC | Depth: ∞ hops`;
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
            <th className="analyst-th num" style={{ width: 120 }}>R_eff</th>
            <th className="analyst-th num" style={{ width: 130 }}>Flow captured</th>
            <th className="analyst-th num" style={{ width: 95 }}>Hop depth</th>
            <th className="analyst-th num" style={{ width: 100 }}>Separation</th>
            <th className="analyst-th" style={{ width: 120 }}>Status</th>
          </tr>
        </thead>
        <tbody>
          {/* Ranked Candidates */}
          {ranked_candidates.map((vasp, idx) => {
            const score = scores[vasp];
            const entityName = labelMap[vasp] || shortAddr(vasp);
            const isTop = idx === 0;
            const btc = flow_btc[vasp];
            const hops = hop_depths[vasp];
            const isCopied = copiedAddr === vasp;

            return (
              <tr key={vasp} className={`analyst-tr ${isTop ? 'matched' : ''}`}>
                <td className="analyst-td" style={{ color: isTop ? '#22c55e' : '#8b919b', fontWeight: isTop ? 600 : 400 }}>
                  {idx + 1}
                </td>

                <td className="analyst-td">
                  <span style={{ fontWeight: isTop ? 600 : 400, color: isTop ? '#e6e8ec' : '#d2d6dc' }}>
                    {entityName}
                  </span>
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
                  {fmt(score)} Ω
                </td>

                <td className="analyst-td num" style={{ color: isTop ? '#22c55e' : '#e6e8ec' }}>
                  {btc != null ? `${btc.toFixed(2)} BTC` : '—'}
                </td>

                <td className="analyst-td num" style={{ color: '#8b919b' }}>
                  {hops != null ? `${hops} hops` : '—'}
                </td>

                <td className="analyst-td num" style={{ color: isTop ? '#22c55e' : '#8b919b', fontWeight: isTop ? 600 : 400 }}>
                  {isTop && separation_ratio != null ? `${separation_ratio.toFixed(2)}x` : '—'}
                </td>

                <td className="analyst-td">
                  {isTop ? (
                    <span style={{ color: '#22c55e', fontWeight: 500 }}>
                      Matched
                    </span>
                  ) : (
                    <span style={{ color: '#8b919b' }}>
                      Decoy
                    </span>
                  )}
                </td>
              </tr>
            );
          })}

          {/* Disconnected Candidates */}
          {unreachable.map((vasp) => {
            const entityName = labelMap[vasp] || shortAddr(vasp);
            const isCopied = copiedAddr === vasp;

            return (
              <tr key={vasp} className="analyst-tr">
                <td className="analyst-td" style={{ color: '#8b919b' }}>
                  —
                </td>

                <td className="analyst-td">
                  <span style={{ color: '#8b919b' }}>
                    {entityName}
                  </span>
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
                  ∞ (null)
                </td>

                <td className="analyst-td num" style={{ color: '#8b919b' }}>
                  0.00 BTC
                </td>

                <td className="analyst-td num" style={{ color: '#8b919b' }}>
                  ∞ hops
                </td>

                <td className="analyst-td num" style={{ color: '#8b919b' }}>
                  —
                </td>

                <td className="analyst-td">
                  <span style={{ color: '#c0564b' }}>
                    Disconnected
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
          </div>
        </div>
      </div>
    </div>
  );
}
