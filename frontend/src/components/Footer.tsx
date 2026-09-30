import type { AttributeResponse } from '../types';

interface FooterProps {
  result?: AttributeResponse | null;
}

export function Footer({}: FooterProps) {
  return (
    <footer className="footer">
      <div className="container footer-inner">
        <span>Ledgerhawk · Blockchain VASP Attribution System</span>
        <span style={{ fontSize: 11, color: 'var(--secondary-text)' }}>
          SIH2026 LedgerHawk
        </span>
      </div>
    </footer>
  );
}
