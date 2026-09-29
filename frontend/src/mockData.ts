import type { Case, AttributeResponse, DetailedNode, DetailedEdge } from './types';

export const DEMO_CASES: Case[] = [
  {
    id: 'demo_6hop',
    label: '6-Hop Asymmetric Swarm (Decoy Diversion & Swarm Mixers)',
    description: '100 BTC laundering syndicate using 4 parallel mixer channels and 2-hop decoy trap',
    defaultSuspect: 'bc1q9vza2e8424t6m5qgxp2r83kwln8y0e78k37df8',
    defaultCandidates: [
      'bc1qm34lsc65zpw79lxes69zkqmk6ee3ewf0j77s3h',
      '1AnwDVbwsLB4om3PnZ54FjWc1m8qP2XbVq',
      '1DecoyUnreachableColdStorage9999',
    ],
    defaultDepth: 6,
    totalBtc: 100,
    highlight: 'Proves Dirichlet Laplacian (Lx = b) beats Dijkstra shortest path',
  },
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
    totalBtc: 29658,
    highlight: 'Historical federal criminal asset forfeiture — adversarially tested engine',
  },
  {
    id: 'genesis',
    label: 'Genesis Cluster & Mixer Swarm Investigation',
    description: 'Triple parallel mixer obfuscation terminating in institutional exchange hot wallet',
    defaultSuspect: '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa',
    defaultCandidates: [
      '1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s',
      '1AnwDVbwsLB4om3PnZ54FjWc1m8qP2XbVq',
    ],
    defaultDepth: 3,
    totalBtc: 50,
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

// Build the complete branching graph elements for the 6-Hop Swarm
function getDemo6HopElements(): { nodes: DetailedNode[]; edges: DetailedEdge[] } {
  const nodes: DetailedNode[] = [
    {
      id: 'bc1q9vza2e8424t6m5qgxp2r83kwln8y0e78k37df8',
      label: 'Suspect Root (100 BTC)',
      role: 'suspect',
      entity: 'Syndicate Main Vault',
      category: 'suspect',
      level: 0,
      amountBtc: 100.0,
    },
    // Branch 1: Decoy trap (Short 2-hop)
    {
      id: 'bc1q_decoy_relay_1',
      label: 'Decoy Relay (Short Path)',
      role: 'hop',
      entity: 'Intermediate Peel Hop',
      category: 'intermediate',
      level: 1,
      amountBtc: 5.0,
    },
    {
      id: '1AnwDVbwsLB4om3PnZ54FjWc1m8qP2XbVq',
      label: 'WazirX Decoy Exchange (TRAP)',
      role: 'candidate_vasp',
      entity: 'WazirX',
      category: 'exchange',
      level: 2,
      amountBtc: 4.98,
    },
    // Branch 2: True Swarm Exit (Deep 6-hop)
    {
      id: 'bc1q_layer1_peel_relay',
      label: 'Layer-1 Peel Relay',
      role: 'hop',
      entity: 'Laundering Relay 1',
      category: 'intermediate',
      level: 1,
      amountBtc: 95.0,
    },
    {
      id: 'bc1q_swarm_splitter_alpha',
      label: 'Swarm Splitter Alpha',
      role: 'hop',
      entity: 'High-Throughput Demux',
      category: 'intermediate',
      level: 2,
      amountBtc: 94.8,
    },
    // 4 Parallel Mixers
    {
      id: '1Mixer_Channel_Alpha',
      label: 'Mixer Swarm Alpha',
      role: 'mixer_hop',
      entity: 'Wasabi Pool A',
      category: 'mixer',
      level: 3,
      amountBtc: 23.7,
    },
    {
      id: '1Mixer_Channel_Beta',
      label: 'Mixer Swarm Beta',
      role: 'mixer_hop',
      entity: 'Wasabi Pool B',
      category: 'mixer',
      level: 3,
      amountBtc: 23.7,
    },
    {
      id: '1Mixer_Channel_Gamma',
      label: 'Mixer Swarm Gamma',
      role: 'mixer_hop',
      entity: 'Wasabi Pool C',
      category: 'mixer',
      level: 3,
      amountBtc: 23.7,
    },
    {
      id: '1Mixer_Channel_Delta',
      label: 'Mixer Swarm Delta',
      role: 'mixer_hop',
      entity: 'Wasabi Pool D',
      category: 'mixer',
      level: 3,
      amountBtc: 23.7,
    },
    // 4 Mule Forwarders
    {
      id: 'bc1q_mule_hop_a',
      label: 'Forwarding Mule A',
      role: 'hop',
      entity: 'Mule Wallet 1',
      category: 'intermediate',
      level: 4,
      amountBtc: 23.5,
    },
    {
      id: 'bc1q_mule_hop_b',
      label: 'Forwarding Mule B',
      role: 'hop',
      entity: 'Mule Wallet 2',
      category: 'intermediate',
      level: 4,
      amountBtc: 23.5,
    },
    {
      id: 'bc1q_mule_hop_c',
      label: 'Forwarding Mule C',
      role: 'hop',
      entity: 'Mule Wallet 3',
      category: 'intermediate',
      level: 4,
      amountBtc: 23.5,
    },
    {
      id: 'bc1q_mule_hop_d',
      label: 'Forwarding Mule D',
      role: 'hop',
      entity: 'Mule Wallet 4',
      category: 'intermediate',
      level: 4,
      amountBtc: 23.5,
    },
    // Consolidation Aggregator
    {
      id: 'bc1q_consolidation_aggregator',
      label: 'Consolidation Aggregator',
      role: 'hop',
      entity: 'Fan-In Accumulator',
      category: 'intermediate',
      level: 5,
      amountBtc: 93.8,
    },
    // True VASP Exit
    {
      id: 'bc1qm34lsc65zpw79lxes69zkqmk6ee3ewf0j77s3h',
      label: 'Binance Cold Storage Vault II (TRUE EXIT)',
      role: 'candidate_vasp',
      entity: 'Binance',
      category: 'exchange',
      level: 6,
      amountBtc: 93.75,
    },
    // Unreachable candidate
    {
      id: '1DecoyUnreachableColdStorage9999',
      label: 'Cold Storage Vault (Unreachable)',
      role: 'unreachable',
      entity: 'Offline Cold Vault',
      category: 'exchange',
      level: 6,
      amountBtc: 0,
    },
  ];

  const edges: DetailedEdge[] = [
    // Decoy branch
    {
      id: 'e_decoy_1',
      source: 'bc1q9vza2e8424t6m5qgxp2r83kwln8y0e78k37df8',
      target: 'bc1q_decoy_relay_1',
      amountSatoshis: 500000000,
      amountBtc: 5.0,
      txHash: 'a1f87c92b450...e94e',
      branchType: 'decoy',
    },
    {
      id: 'e_decoy_2',
      source: 'bc1q_decoy_relay_1',
      target: '1AnwDVbwsLB4om3PnZ54FjWc1m8qP2XbVq',
      amountSatoshis: 498000000,
      amountBtc: 4.98,
      txHash: 'b2c98d03a561...fa5f',
      branchType: 'decoy',
    },
    // Swarm branch
    {
      id: 'e_swarm_1',
      source: 'bc1q9vza2e8424t6m5qgxp2r83kwln8y0e78k37df8',
      target: 'bc1q_layer1_peel_relay',
      amountSatoshis: 9500000000,
      amountBtc: 95.0,
      txHash: 'c3d09e14b672...0b60',
      branchType: 'swarm',
    },
    {
      id: 'e_swarm_2',
      source: 'bc1q_layer1_peel_relay',
      target: 'bc1q_swarm_splitter_alpha',
      amountSatoshis: 9480000000,
      amountBtc: 94.8,
      txHash: 'd4e1af25c783...1c71',
      branchType: 'swarm',
    },
    // 4 Split branches
    {
      id: 'e_split_a',
      source: 'bc1q_swarm_splitter_alpha',
      target: '1Mixer_Channel_Alpha',
      amountSatoshis: 2370000000,
      amountBtc: 23.7,
      txHash: 'e5f2b036d894...2d82',
      branchType: 'swarm',
    },
    {
      id: 'e_split_b',
      source: 'bc1q_swarm_splitter_alpha',
      target: '1Mixer_Channel_Beta',
      amountSatoshis: 2370000000,
      amountBtc: 23.7,
      txHash: 'f603c147e905...3e93',
      branchType: 'swarm',
    },
    {
      id: 'e_split_c',
      source: 'bc1q_swarm_splitter_alpha',
      target: '1Mixer_Channel_Gamma',
      amountSatoshis: 2370000000,
      amountBtc: 23.7,
      txHash: '0714d258fa16...4fa4',
      branchType: 'swarm',
    },
    {
      id: 'e_split_d',
      source: 'bc1q_swarm_splitter_alpha',
      target: '1Mixer_Channel_Delta',
      amountSatoshis: 2370000000,
      amountBtc: 23.7,
      txHash: '1825e3690b27...50b5',
      branchType: 'swarm',
    },
    // 4 Mule branches
    {
      id: 'e_mule_a',
      source: '1Mixer_Channel_Alpha',
      target: 'bc1q_mule_hop_a',
      amountSatoshis: 2350000000,
      amountBtc: 23.5,
      txHash: '2936f47a1c38...61c6',
      branchType: 'swarm',
    },
    {
      id: 'e_mule_b',
      source: '1Mixer_Channel_Beta',
      target: 'bc1q_mule_hop_b',
      amountSatoshis: 2350000000,
      amountBtc: 23.5,
      txHash: '3047058b2d49...72d7',
      branchType: 'swarm',
    },
    {
      id: 'e_mule_c',
      source: '1Mixer_Channel_Gamma',
      target: 'bc1q_mule_hop_c',
      amountSatoshis: 2350000000,
      amountBtc: 23.5,
      txHash: '4158169c3e5a...83e8',
      branchType: 'swarm',
    },
    {
      id: 'e_mule_d',
      source: '1Mixer_Channel_Delta',
      target: 'bc1q_mule_hop_d',
      amountSatoshis: 2350000000,
      amountBtc: 23.5,
      txHash: '526927ad4f6b...94f9',
      branchType: 'swarm',
    },
    // 4 Consolidation branches
    {
      id: 'e_agg_a',
      source: 'bc1q_mule_hop_a',
      target: 'bc1q_consolidation_aggregator',
      amountSatoshis: 2345000000,
      amountBtc: 23.45,
      txHash: '637a38be507c...050a',
      branchType: 'swarm',
    },
    {
      id: 'e_agg_b',
      source: 'bc1q_mule_hop_b',
      target: 'bc1q_consolidation_aggregator',
      amountSatoshis: 2345000000,
      amountBtc: 23.45,
      txHash: '748b49cf618d...161b',
      branchType: 'swarm',
    },
    {
      id: 'e_agg_c',
      source: 'bc1q_mule_hop_c',
      target: 'bc1q_consolidation_aggregator',
      amountSatoshis: 2345000000,
      amountBtc: 23.45,
      txHash: '859c5ad0729e...272c',
      branchType: 'swarm',
    },
    {
      id: 'e_agg_d',
      source: 'bc1q_mule_hop_d',
      target: 'bc1q_consolidation_aggregator',
      amountSatoshis: 2345000000,
      amountBtc: 23.45,
      txHash: '96ad6be183af...383d',
      branchType: 'swarm',
    },
    // Final exit to Binance
    {
      id: 'e_exit_binance',
      source: 'bc1q_consolidation_aggregator',
      target: 'bc1qm34lsc65zpw79lxes69zkqmk6ee3ewf0j77s3h',
      amountSatoshis: 9375000000,
      amountBtc: 93.75,
      txHash: 'a7be7cf294b0...0494',
      branchType: 'swarm',
    },
  ];

  return { nodes, edges };
}

export function generateMockAttribution(caseId: string, suspect: string, depth = 6): AttributeResponse {
  if (caseId === 'silkroad') {
    // Fallback values mirror the real verified API response exactly.
    // These are only used when the backend is offline.
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

  // Default: 6-Hop Asymmetric Swarm
  const allElements = getDemo6HopElements();
  const maxHop = Math.max(1, depth);

  // Filter elements up to depth
  const visibleNodes = allElements.nodes.filter((n) => (n.level ?? 0) <= maxHop);
  const visibleNodeIds = new Set(visibleNodes.map((n) => n.id));
  const visibleEdges = allElements.edges.filter(
    (e) => visibleNodeIds.has(e.source) && visibleNodeIds.has(e.target)
  );

  // If depth is less than 6, Binance Vault II (at level 6) hasn't been reached yet!
  const hasReachedBinance = maxHop >= 6;
  const hasReachedWazirX = maxHop >= 2;

  let ranked_candidates: string[] = [];
  let unreachable: string[] = ['1DecoyUnreachableColdStorage9999'];
  let separation_ratio = 1.0;

  if (hasReachedBinance && hasReachedWazirX) {
    ranked_candidates = [
      'bc1qm34lsc65zpw79lxes69zkqmk6ee3ewf0j77s3h',
      '1AnwDVbwsLB4om3PnZ54FjWc1m8qP2XbVq',
    ];
    separation_ratio = 6.3;
  } else if (hasReachedWazirX) {
    // Only WazirX decoy was reached
    ranked_candidates = ['1AnwDVbwsLB4om3PnZ54FjWc1m8qP2XbVq'];
    unreachable = [
      'bc1qm34lsc65zpw79lxes69zkqmk6ee3ewf0j77s3h',
      '1DecoyUnreachableColdStorage9999',
    ];
    separation_ratio = 1.0;
  } else {
    // 1 hop: no exchange reached
    unreachable = [
      'bc1qm34lsc65zpw79lxes69zkqmk6ee3ewf0j77s3h',
      '1AnwDVbwsLB4om3PnZ54FjWc1m8qP2XbVq',
      '1DecoyUnreachableColdStorage9999',
    ];
  }

  return {
    suspect: suspect || 'bc1q9vza2e8424t6m5qgxp2r83kwln8y0e78k37df8',
    ranked_candidates,
    scores: {
      'bc1qm34lsc65zpw79lxes69zkqmk6ee3ewf0j77s3h': hasReachedBinance ? 0.0636 : null,
      '1AnwDVbwsLB4om3PnZ54FjWc1m8qP2XbVq': hasReachedWazirX ? 0.4008 : null,
      '1DecoyUnreachableColdStorage9999': null,
    },
    raw_resistance: {
      'bc1qm34lsc65zpw79lxes69zkqmk6ee3ewf0j77s3h': hasReachedBinance ? 0.0636 : null,
      '1AnwDVbwsLB4om3PnZ54FjWc1m8qP2XbVq': hasReachedWazirX ? 0.4008 : null,
      '1DecoyUnreachableColdStorage9999': null,
    },
    unreachable,
    separation_ratio,
    method: 'effective_resistance',
    degree_corrected: false,
    case_id: caseId || 'demo_6hop',
    truncated: maxHop < 6,
    graph: {
      nodes: visibleNodes.length,
      edges: visibleEdges.length,
      connected: true,
      n_components: 1,
    },
    candidate_names: {
      'bc1qm34lsc65zpw79lxes69zkqmk6ee3ewf0j77s3h': 'Binance Institutional Cold Storage Vault II',
      '1AnwDVbwsLB4om3PnZ54FjWc1m8qP2XbVq': 'WazirX Decoy Exchange',
      '1DecoyUnreachableColdStorage9999': 'Unreachable Cold Storage Vault',
    },
    flow_btc: {
      'bc1qm34lsc65zpw79lxes69zkqmk6ee3ewf0j77s3h': 93.75,
      '1AnwDVbwsLB4om3PnZ54FjWc1m8qP2XbVq': 4.98,
    },
    hop_depths: {
      'bc1qm34lsc65zpw79lxes69zkqmk6ee3ewf0j77s3h': 6,
      '1AnwDVbwsLB4om3PnZ54FjWc1m8qP2XbVq': 2,
    },
    dijkstra_comparison: {
      winner: hasReachedWazirX ? '1AnwDVbwsLB4om3PnZ54FjWc1m8qP2XbVq' : 'None',
      winner_name: hasReachedWazirX ? 'WazirX Decoy Exchange' : 'None',
      hop_count: 2,
      flaw: hasReachedBinance
        ? 'Shortest path stopped at 2-hop WazirX decoy (5 BTC). Missed 95 BTC true swarm exit to Binance.'
        : `At search depth ${maxHop}, search horizon has not reached the 6-hop true exit (Binance). Only the 2-hop decoy (WazirX) was reached. Increase depth to 6 to unveil the full swarm.`,
    },
    graph_elements: { nodes: visibleNodes, edges: visibleEdges },
  };
}
