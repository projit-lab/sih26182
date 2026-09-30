// API and Domain Types

export interface Case {
  id: string;
  label: string;
  description: string;
  defaultSuspect: string;
  defaultCandidates?: string[];
  defaultDepth?: number;
  totalBtc?: number;
  highlight?: string;
}

export interface GraphMeta {
  nodes: number;
  edges: number;
  connected: boolean;
  n_components: number;
  largest_component?: number;
}

export interface DetailedNode {
  id: string;
  label: string;
  role: 'suspect' | 'hop' | 'mixer_hop' | 'candidate_vasp' | 'unreachable';
  entity?: string;
  category?: string;
  level?: number;
  amountBtc?: number;
}

export interface DetailedEdge {
  id: string;
  source: string;
  target: string;
  amountSatoshis: number;
  amountBtc: number;
  txHash?: string;
  branchType?: 'decoy' | 'swarm' | 'direct';
}

export interface AttributeResponse {
  suspect: string;
  ranked_candidates: string[];
  scores: Record<string, number | null>;
  raw_resistance: Record<string, number | null>;
  unreachable: string[];
  separation_ratio: number;
  method: string;
  degree_corrected: boolean;
  case_id: string;
  truncated: boolean;
  graph: GraphMeta;
  // Real API field (preferred): human-readable VASP names keyed by address
  candidate_labels?: Record<string, string>;
  // Legacy / mock field — kept for backward compatibility
  candidate_names?: Record<string, string>;
  flow_btc?: Record<string, number>;
  hop_depths?: Record<string, number>;
  dijkstra_comparison?: {
    winner: string;
    winner_name: string;
    hop_count: number;
    flaw: string;
  };
  graph_elements?: {
    nodes: DetailedNode[];
    edges: DetailedEdge[];
  };
  synthetic?: boolean;
  truth?: string;
  er_wins?: number;
  sp_wins?: number;
}

export interface AttributeRequest {
  suspect: string;
  candidates?: string[];
  case_id?: string;
  depth?: number;
}

export type Screen = 'input' | 'results' | 'graph';
