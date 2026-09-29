import { ChevronLeft, ExternalLink } from 'lucide-react';
import type { Screen, AttributeResponse } from '../types';

interface HeaderProps {
  currentScreen: Screen;
  activeCase?: string | null;
  result: AttributeResponse | null;
  onBack: () => void;
  onBackToInput: () => void;
}

export function Header({ currentScreen, result, onBack, onBackToInput }: HeaderProps) {
  const handleOpenVisualizer = () => {
    window.open('/graph_visualizer.html', '_blank', 'noopener,noreferrer');
  };

  return (
    <header className="header">
      <div className="container header-inner">
        <div className="header-brand">
          <div>
            <div className="header-product">Ledgerhawk</div>
            <div className="header-subtitle">VASP Attribution Engine</div>
          </div>
        </div>

        <div className="header-meta">
          <button
            type="button"
            onClick={handleOpenVisualizer}
            className="btn-secondary"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              fontSize: 12,
              fontWeight: 500,
              padding: '5px 12px',
              borderRadius: 4,
            }}
            title="Open standalone graph visualizer in a new tab"
          >
            <ExternalLink size={13} />
            Open Visualizer
          </button>

          {currentScreen === 'results' && result && (
            <div className="case-badge" style={{ fontSize: 11, color: 'var(--secondary-text)' }}>
              {result.graph.nodes}N · {result.graph.edges}E
            </div>
          )}

          {currentScreen === 'results' && (
            <button className="nav-btn" onClick={onBackToInput}>
              <ChevronLeft size={14} />
              New Investigation
            </button>
          )}

          {currentScreen === 'graph' && (
            <button className="nav-btn" onClick={onBack}>
              <ChevronLeft size={14} />
              Back to Results
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
