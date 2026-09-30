import { useState } from 'react';
import { Header } from './components/Header';
import { Footer } from './components/Footer';
import { InputScreen } from './components/InputScreen';
import { ResultsScreen } from './components/ResultsScreen';
import { GraphScreen } from './components/GraphScreen';
import { BlockchainNetworkBackground } from './components/BlockchainNetworkBackground';
import type { Screen, AttributeResponse } from './types';
import './index.css';

export default function App() {
  const [screen, setScreen] = useState<Screen>('input');
  const [result, setResult] = useState<AttributeResponse | null>(null);
  const [activeCaseId, setActiveCaseId] = useState<string | null>(null);

  const handleResult = (res: AttributeResponse, caseId: string) => {
    setResult(res);
    setActiveCaseId(caseId || res.case_id || null);
    setScreen('results');
  };

  const handleViewGraph = () => setScreen('graph');

  const handleBackToResults = () => setScreen('results');

  const handleNewQuery = () => {
    setScreen('input');
  };

  return (
    <div className="shell">
      {/* Dynamic Blockchain Network Background (Input & Results screens) */}
      {screen !== 'graph' && <BlockchainNetworkBackground />}

      <Header
        currentScreen={screen}
        activeCase={activeCaseId}
        result={result}
        onBack={handleBackToResults}
        onBackToInput={handleNewQuery}
      />

      <main className="main" style={{ position: 'relative', zIndex: 1 }}>
        {screen === 'input' && (
          <InputScreen
            onResult={handleResult}
            initialCaseId={activeCaseId}
          />
        )}

        {screen === 'results' && result && (
          <ResultsScreen
            result={result}
            onViewGraph={handleViewGraph}
            onNewQuery={handleNewQuery}
          />
        )}

        {screen === 'graph' && result && (
          <GraphScreen
            result={result}
            onBack={handleBackToResults}
          />
        )}
      </main>

      <Footer result={screen !== 'input' ? result : null} />
    </div>
  );
}
