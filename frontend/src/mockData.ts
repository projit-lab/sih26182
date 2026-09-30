import type { Case, AttributeResponse } from './types';

export const DEMO_CASES: Case[] = [
  {
    id: 'silkroad',
    label: 'Silk Road (USMS Seized Asset Cluster — 199 nodes)',
    description: 'Real-world seized Bitcoin graph from DOJ/USMS Silk Road forfeiture. 199 nodes, 235 edges across 7 disconnected components.',
    defaultSuspect: '1F1tAaz5x1HUXrCNLbtMDqcw6o5GNn4xqX',
    defaultCandidates: [
      'bc1qy6a2hrtsen4ssxasl97c5krn7w9uxg6k2hrww6',
      '366zTCcC9nVDyF3SMSju3GbfYmMVXfewHg',
      '3BJr4VGfCNrv4w55yM2gjK1rB4gNWxV8Tt',
    ],
    defaultDepth: 4,
    highlight: 'Historical federal criminal asset forfeiture — adversarially tested engine',
  },
  {
    id: 'synthetic_mixer',
    label: '[SYNTHETIC] Mixer-routed benchmark case (seed 42)',
    description: 'A synthetic graph to benchmark effective resistance against shortest-path.',
    defaultSuspect: 'suspect_114',
    defaultCandidates: [
      'VASP_0',
      'VASP_1',
      'VASP_2',
      'VASP_3',
      'VASP_4',
      'VASP_5',
    ],
  },
  {
    id: 'peel_chain',
    label: 'Rapid Multi-Hop Peel Chain',
    description: 'Continuous micro-peel peeling sequence funneling to exchange deposit address',
    defaultSuspect: 'suspect_003',
    defaultCandidates: ['3KrakenHotWallet'],
    defaultDepth: 3,
    totalBtc: 55,
  },
];

export function generateMockAttribution(caseId: string, suspect: string): AttributeResponse {
  if (caseId === 'silkroad') {
    return {
      suspect: suspect || '1F1tAaz5x1HUXrCNLbtMDqcw6o5GNn4xqX',
      ranked_candidates: [
        'bc1qy6a2hrtsen4ssxasl97c5krn7w9uxg6k2hrww6',
        '366zTCcC9nVDyF3SMSju3GbfYmMVXfewHg',
        '3BJr4VGfCNrv4w55yM2gjK1rB4gNWxV8Tt',
      ],
      scores: {
        'bc1qy6a2hrtsen4ssxasl97c5krn7w9uxg6k2hrww6': 0.0504,
        '366zTCcC9nVDyF3SMSju3GbfYmMVXfewHg': 0.1219,
        '3BJr4VGfCNrv4w55yM2gjK1rB4gNWxV8Tt': 0.1231,
      },
      raw_resistance: {
        'bc1qy6a2hrtsen4ssxasl97c5krn7w9uxg6k2hrww6': 0.0504,
        '366zTCcC9nVDyF3SMSju3GbfYmMVXfewHg': 0.1219,
        '3BJr4VGfCNrv4w55yM2gjK1rB4gNWxV8Tt': 0.1231,
      },
      unreachable: [],
      separation_ratio: 2.42,
      method: 'effective_resistance',
      degree_corrected: true,
      case_id: 'silkroad',
      truncated: false,
      graph: {
        nodes: 199,
        edges: 235,
        connected: false,
        n_components: 7,
      },
      candidate_labels: {
        'bc1qy6a2hrtsen4ssxasl97c5krn7w9uxg6k2hrww6': 'Coinbase Prime Institutional Vault',
        '3BJr4VGfCNrv4w55yM2gjK1rB4gNWxV8Tt': 'Kraken Exchange Liquidation Node',
        '366zTCcC9nVDyF3SMSju3GbfYmMVXfewHg': 'Binance Multi-Sig Sweep Relay',
      },
      candidate_names: {
        'bc1qy6a2hrtsen4ssxasl97c5krn7w9uxg6k2hrww6': 'Coinbase Prime Institutional Vault',
        '3BJr4VGfCNrv4w55yM2gjK1rB4gNWxV8Tt': 'Kraken Exchange Liquidation Node',
        '366zTCcC9nVDyF3SMSju3GbfYmMVXfewHg': 'Binance Multi-Sig Sweep Relay',
      },
    };
  }

  // Fallback for everything else
  return {
    suspect: suspect,
    ranked_candidates: [],
    scores: {},
    raw_resistance: {},
    unreachable: [],
    separation_ratio: 1.0,
    method: 'effective_resistance',
    degree_corrected: false,
    case_id: caseId,
    truncated: false,
    graph: { nodes: 0, edges: 0, connected: false, n_components: 0 },
  };
}
