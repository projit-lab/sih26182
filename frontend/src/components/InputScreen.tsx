import { useState, useEffect } from 'react';
import { ArrowRight, X, Info, AlertCircle, SlidersHorizontal, ChevronDown } from 'lucide-react';
import { fetchCases, postAttribute, NotFoundError } from '../api';
import type { Case, AttributeRequest, AttributeResponse } from '../types';

interface InputScreenProps {
  onResult: (result: AttributeResponse, caseId: string) => void;
  initialCaseId?: string | null;
}

export function InputScreen({ onResult, initialCaseId }: InputScreenProps) {
  const [cases, setCases] = useState<Case[]>([]);
  const [casesLoading, setCasesLoading] = useState(true);
  const [casesError, setCasesError] = useState<string | null>(null);

  const [selectedCase, setSelectedCase] = useState<string>('');
  const [suspect, setSuspect] = useState('');
  const [candidates, setCandidates] = useState('');
  const [depth, setDepth] = useState<number>(6);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [showMethodologyModal, setShowMethodologyModal] = useState(false);
  const [showManualFields, setShowManualFields] = useState(false);
  const [showCaseDetails, setShowCaseDetails] = useState(false);

  // Load cases on mount
  useEffect(() => {
    fetchCases()
      .then((data) => {
        setCases(data);
        const targetId = initialCaseId || (data.length > 0 ? data[0].id : '');
        setSelectedCase(targetId);
        const match = data.find((c) => c.id === targetId);
        if (match) {
          if (match.defaultSuspect) setSuspect(match.defaultSuspect);
          if (match.defaultCandidates) setCandidates(match.defaultCandidates.join('\n'));
          if (match.defaultDepth) setDepth(match.defaultDepth);
        }
      })
      .catch((e) => {
        setCasesError('Could not load demo cases. Check backend status.');
        console.error(e);
      })
      .finally(() => setCasesLoading(false));
  }, [initialCaseId]);

  const handleCaseChange = (caseId: string) => {
    setSelectedCase(caseId);
    setError(null);
    setNotFound(false);
    const match = cases.find((c) => c.id === caseId);
    if (match) {
      if (match.defaultSuspect) setSuspect(match.defaultSuspect);
      if (match.defaultCandidates) setCandidates(match.defaultCandidates.join('\n'));
      if (match.defaultDepth) setDepth(match.defaultDepth);
    }
  };

  const currentCaseObj = cases.find((c) => c.id === selectedCase);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!suspect.trim()) {
      setShowManualFields(true);
      setError('Enter a suspect wallet address.');
      return;
    }

    setLoading(true);
    setError(null);
    setNotFound(false);

    const req: AttributeRequest = {
      suspect: suspect.trim(),
      case_id: selectedCase || undefined,
      depth: depth,
    };

    if (candidates.trim()) {
      req.candidates = candidates
        .split(/[\n,]+/)
        .map((s) => s.trim())
        .filter(Boolean);
    }

    try {
      const result = await postAttribute(req);
      onResult(result, selectedCase || result.case_id || '');
    } catch (e) {
      if (e instanceof NotFoundError) {
        setNotFound(true);
      } else {
        setError(e instanceof Error ? e.message : 'An unexpected error occurred.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="input-screen-wrapper">
      <div className="container">
        {/* Top Hero Section */}
        <section className="hero-section">
          <div className="hero-left">
            <h1 className="hero-title">VASP Attribution Engine</h1>
            <p className="hero-desc">Graph-based attribution for suspicious crypto wallets.</p>
            <p className="hero-support-text">
              Trace transaction paths, evaluate candidate VASPs, and calculate attribution using the Dirichlet Grounded Laplacian.
            </p>
          </div>
        </section>

        {/* Investigation Configuration Card (Single Cohesive White Card) */}
        <div className="config-card">
          <div className="config-header">
            <h2 className="config-title">Run Attribution</h2>
            <p className="config-subtitle">Configure an investigation using a demo case or a suspect wallet.</p>
          </div>

          <form onSubmit={handleSubmit} noValidate>
            {/* 1. DEMO CASE */}
            <div className="field-group">
              <label htmlFor="demo-case" className="field-label" style={{ fontWeight: 700 }}>
                SELECT A PRE-LOADED INVESTIGATION
              </label>

              {casesLoading ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--secondary-text)', fontSize: 13 }}>
                  <div className="spinner spinner-dark" />
                  Loading demo cases…
                </div>
              ) : casesError ? (
                <div className="error-msg" style={{ marginBottom: 0 }}>
                  <AlertCircle size={15} style={{ flexShrink: 0, marginTop: 1 }} />
                  <span>{casesError}</span>
                </div>
              ) : (
                <select
                  id="demo-case"
                  className="select"
                  value={selectedCase}
                  onChange={(e) => handleCaseChange(e.target.value)}
                >
                  <option value="">— Select an investigation case —</option>
                  {cases.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.label || c.id} {c.totalBtc ? `(${c.totalBtc} BTC)` : ''}
                    </option>
                  ))}
                </select>
              )}

              {/* View Details toggle button and case description */}
              {currentCaseObj && (
                <div style={{ marginTop: 8 }}>
                  <button
                    type="button"
                    id="toggle-case-details-btn"
                    onClick={() => setShowCaseDetails((prev) => !prev)}
                    className="btn-secondary"
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 6,
                      fontSize: 12,
                      fontWeight: 600,
                      padding: '4px 12px',
                      borderRadius: 6,
                      cursor: 'pointer',
                      background: showCaseDetails ? 'var(--light-green)' : 'rgba(15, 23, 42, 0.6)',
                      color: showCaseDetails ? 'var(--accent-green)' : 'var(--secondary-text)',
                      borderColor: showCaseDetails ? 'var(--accent-green)' : 'rgba(255, 255, 255, 0.16)',
                      transition: 'all var(--t)',
                    }}
                  >
                    <span>{showCaseDetails ? 'Hide Details' : 'View Details'}</span>
                    <ChevronDown
                      size={13}
                      style={{
                        transform: showCaseDetails ? 'rotate(180deg)' : 'none',
                        transition: 'transform var(--t)',
                      }}
                    />
                  </button>

                  {showCaseDetails && (
                    <div className="case-info-panel fade-in" style={{ marginTop: 10 }}>
                      <strong>{currentCaseObj.label}</strong>
                      <p>{currentCaseObj.description}</p>
                      {currentCaseObj.highlight && (
                        <div className="case-info-highlight">
                          {currentCaseObj.highlight}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              <p className="field-hint">
                <Info size={12} style={{ display: 'inline', marginTop: 2, flexShrink: 0 }} />
                <span>Pre-loaded demo cases work offline — no live blockchain node required.</span>
              </p>
            </div>

            {/* Enter Manually Toggle Button */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '22px 0' }}>
              <div style={{ flex: 1, height: '1px', background: 'var(--border)' }} />
              <button
                type="button"
                id="toggle-manual-entry-btn"
                onClick={() => setShowManualFields((prev) => !prev)}
                className="btn-secondary"
                style={{
                  fontSize: 13,
                  padding: '8px 20px',
                  borderRadius: 99,
                  margin: '0 14px',
                  color: showManualFields ? 'var(--accent-green)' : '#F8FAFC',
                  borderColor: showManualFields ? 'var(--accent-green)' : 'rgba(255, 255, 255, 0.22)',
                  background: showManualFields ? 'var(--light-green)' : 'var(--surface-subtle)',
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 8,
                  transition: 'all var(--t)',
                  fontWeight: 700,
                  letterSpacing: '0.02em',
                  boxShadow: '0 2px 8px rgba(0, 0, 0, 0.35)',
                }}
              >
                <SlidersHorizontal size={14} style={{ strokeWidth: 2.5 }} />
                <span style={{ fontWeight: 700 }}>{showManualFields ? 'Hide Manual Inputs' : 'Enter Manually'}</span>
                <ChevronDown
                  size={15}
                  style={{
                    strokeWidth: 2.5,
                    transform: showManualFields ? 'rotate(180deg)' : 'none',
                    transition: 'transform var(--t)',
                  }}
                />
              </button>
              <div style={{ flex: 1, height: '1px', background: 'var(--border)' }} />
            </div>

            {/* Manual Entry Fields (Displayed when Enter Manually is clicked) */}
            {showManualFields && (
              <div className="manual-fields-wrapper fade-in" style={{ paddingBottom: 6 }}>
                {/* 2. SUSPECT WALLET ADDRESS */}
                <div className="field-group">
                  <label htmlFor="suspect" className="field-label">
                    SUSPECT WALLET ADDRESS
                    <span className="field-label-sub">— required</span>
                  </label>
                  <input
                    id="suspect"
                    type="text"
                    className="input mono"
                    placeholder="e.g. bc1q9vza2e8424t6m5qgxp2r83kwln8y0e78k37df8"
                    value={suspect}
                    onChange={(e) => {
                      setSuspect(e.target.value);
                      setError(null);
                      setNotFound(false);
                    }}
                    spellCheck={false}
                    autoComplete="off"
                  />
                </div>

                {/* 3. TRAVERSAL DEPTH */}
                <div className="field-group">
                  <label htmlFor="hop-depth" className="field-label">
                    TRAVERSAL DEPTH (HOPS)
                    <span className="field-label-sub">— graph exploration radius</span>
                  </label>
                  <select
                    id="hop-depth"
                    className="select"
                    value={depth}
                    onChange={(e) => setDepth(Number(e.target.value))}
                  >
                    <option value={1}>1 Hop (Direct Peers / Immediate UTXOs)</option>
                    <option value={2}>2 Hops (Mules &amp; Relays — Decoy Horizon)</option>
                    <option value={3}>3 Hops (Mixer Layering Channels)</option>
                    <option value={4}>4 Hops (Deep Trace &amp; Mixer Demux)</option>
                    <option value={5}>5 Hops (Aggregators &amp; Consolidation)</option>
                    <option value={6}>6 Hops (Deep Layering / Full Swarm Exit)</option>
                    <option value={7}>7 Hops (Complex Peeling / Extended Trace)</option>
                    <option value={8}>8 Hops (Deep Obfuscation Trace)</option>
                  </select>
                  <p className="field-hint">
                    Controls the number of transaction hops traversed from the suspect address before solving the Grounded Laplacian.
                  </p>
                </div>

                {/* 4. CANDIDATE VASPs */}
                <div className="field-group">
                  <label htmlFor="candidates" className="field-label">
                    CANDIDATE VASPS
                    <span className="field-label-sub">— optional, one per line or comma-separated</span>
                  </label>
                  <textarea
                    id="candidates"
                    className="textarea mono"
                    rows={3}
                    placeholder="Leave blank to use all known VASPs in this case"
                    value={candidates}
                    onChange={(e) => setCandidates(e.target.value)}
                    spellCheck={false}
                    style={{ resize: 'vertical' }}
                  />
                  <p className="field-hint">
                    If left blank, the solver will evaluate all registered VASP deposit endpoints in the case.
                  </p>
                </div>
              </div>
            )}

            {/* Error & Not Found notifications */}
            {error && (
              <div className="error-msg">
                <AlertCircle size={15} style={{ flexShrink: 0, marginTop: 1 }} />
                <span>{error}</span>
              </div>
            )}

            {notFound && (
              <div className="not-found-msg">
                <Info size={15} style={{ flexShrink: 0, marginTop: 1 }} />
                <div>
                  <strong style={{ color: 'var(--primary-text)', display: 'block', marginBottom: 2 }}>
                    Suspect address not found
                  </strong>
                  The suspect wallet address was not found in the loaded case. Check the address or select a pre-loaded investigation case above.
                </div>
              </div>
            )}

            {/* 5. PRIMARY ACTION (Bottom-Right) */}
            <div className="form-actions-row">
              <button
                type="submit"
                className="btn-primary"
                disabled={loading || casesLoading}
                id="submit-attribution"
              >
                {loading ? (
                  <>
                    <div className="spinner" />
                    Solving Grounded Laplacian (Lx = b)…
                  </>
                ) : (
                  <>
                    Run Attribution
                    <ArrowRight size={14} />
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* Methodology Modal for Researchers / Judges */}
      {showMethodologyModal && (
        <div className="modal-overlay" onClick={() => setShowMethodologyModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <span className="hero-eyebrow" style={{ marginBottom: 4 }}>FORMAL METHODOLOGY</span>
                <h3 className="modal-title">Dirichlet Grounded Laplacian vs Dijkstra</h3>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setShowMethodologyModal(false)}
                aria-label="Close"
              >
                <X size={18} />
              </button>
            </div>

            <div className="modal-body">
              <p>
                Shortest-path tracing follows the single shortest route, so a short decoy transfer can outrank the exchange that most of the funds actually reach. Effective resistance weighs every parallel route.
              </p>

              <h4>1. Electrical Circuit Analogy</h4>
              <p>
                Blockchainheist maps UTXO transaction networks as a resistive network where edge conductance w_ij is proportional to transaction volume in Satoshis.
              </p>
              <div className="modal-code-block">
                L = D - W (Combinatorial Laplacian matrix)
              </div>

              <h4>2. Grounded Laplacian System (L x = b)</h4>
              <p>
                By grounding candidate VASP exit nodes as electrical sinks (Dirichlet boundary condition V_t = 0) and injecting current at suspect root s, the node potentials x satisfy the sparse linear system:
              </p>
              <div className="modal-code-block">
                L_reduced · x = b
              </div>

              <h4>3. Effective Resistance (R_eff)</h4>
              <p>
                Effective resistance aggregates <strong>all parallel paths</strong> and flow volumes. A multi-hop swarm carrying 95 BTC achieves dramatically lower effective resistance than a low-volume decoy path, provably defeating sybil and mixer obfuscation.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
