import { ChevronLeft } from 'lucide-react';
import type { Screen, AttributeResponse } from '../types';

interface HeaderProps {
  currentScreen: Screen;
  activeCase?: string | null;
  result: AttributeResponse | null;
  onBack: () => void;
  onBackToInput: () => void;
}

export function Header({ currentScreen, result, onBack, onBackToInput }: HeaderProps) {
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
