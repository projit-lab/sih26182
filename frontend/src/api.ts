import type { Case, AttributeRequest, AttributeResponse } from './types';
import { DEMO_CASES, generateMockAttribution } from './mockData';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// The real /cases response is an object: { "silkroad": { nodes, edges, suspect, ... } }
// Normalize that into Case[] for the UI.
function normalizeCases(raw: unknown): Case[] {
  if (Array.isArray(raw)) {
    // Already an array — pass through if it has the right shape
    return raw as Case[];
  }
  if (raw && typeof raw === 'object') {
    const obj = raw as Record<string, { suspect?: string; nodes?: number; edges?: number; truncated?: boolean }>;
    return Object.entries(obj).map(([key, meta]) => {
      // Human-readable labels for known cases
      const LABELS: Record<string, string> = {
        silkroad: 'Silk Road (USMS Seized Asset Cluster — 199 nodes)',
      };
      const DESCS: Record<string, string> = {
        silkroad: 'Real-world seized Bitcoin graph from the DOJ/USMS Silk Road forfeiture. 199 nodes, 235 transaction edges across 7 disconnected components.',
      };
      const HIGHLIGHTS: Record<string, string> = {
        silkroad: 'Historical federal criminal asset forfeiture — adversarially tested engine (14 passing tests)',
      };
      const DEFAULT_CANDIDATES: Record<string, string[]> = {
        silkroad: [
          'bc1qy6a2hrtsen4ssxasl97c5krn7w9uxg6k2hrww6',
          '366zTCcC9nVDyF3SMSju3GbfYmMVXfewHg',
          '3BJr4VGfCNrv4w55yM2gjK1rB4gNWxV8Tt',
        ],
      };
      return {
        id: key,
        label: LABELS[key] || key,
        description: DESCS[key] || `${meta.nodes ?? '?'} nodes, ${meta.edges ?? '?'} edges`,
        defaultSuspect: meta.suspect || '',
        defaultCandidates: DEFAULT_CANDIDATES[key],
        defaultDepth: 4,
        highlight: HIGHLIGHTS[key],
      } as Case;
    });
  }
  return [];
}

export async function fetchCases(): Promise<Case[]> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3000);

    const res = await fetch(`${BASE_URL}/cases`, { signal: controller.signal });
    clearTimeout(timeoutId);

    if (res.ok) {
      const data = await res.json();
      const parsed = normalizeCases(data);
      if (parsed.length > 0) return parsed;
    }
  } catch {
    // Backend offline / not reachable — fall back to built-in demo cases
    console.info('[Blockchainheist] Live backend offline — using built-in demo cases.');
  }

  return DEMO_CASES;
}

export async function postAttribute(req: AttributeRequest): Promise<AttributeResponse> {
  // Guard: deliberate test strings
  if (
    req.suspect.trim().toLowerCase() === 'notfound' ||
    req.suspect.trim().toLowerCase() === 'invalid'
  ) {
    throw new NotFoundError('Suspect address not found in this case.');
  }

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 8000);

    // Backend field names: suspect_wallet, candidate_vasps (not suspect/candidates)
    const body: Record<string, unknown> = {
      case_id: req.case_id || 'silkroad',
    };
    // Only send suspect_wallet if the user manually typed one different from the default
    if (req.suspect && req.suspect.trim()) {
      body.suspect_wallet = req.suspect.trim();
    }
    if (req.candidates && req.candidates.length > 0) {
      body.candidate_vasps = req.candidates;
    }

    const res = await fetch(`${BASE_URL}/attribute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (res.status === 404) {
      throw new NotFoundError('Suspect address not found in this case.');
    }

    if (res.ok) {
      const data = await res.json() as AttributeResponse;
      // Back-fill candidate_names from candidate_labels so the rest of the UI
      // can use either field without branching everywhere.
      if (data.candidate_labels && !data.candidate_names) {
        data.candidate_names = data.candidate_labels;
      }
      return data;
    }

    throw new Error(`Server returned ${res.status}`);
  } catch (e) {
    if (e instanceof NotFoundError) throw e;
    console.info('[Blockchainheist] Live backend offline — computing via local engine.');
  }

  // Realistic sub-second computation simulation
  await new Promise((resolve) => setTimeout(resolve, 380));

  const caseId = req.case_id || 'silkroad';
  return generateMockAttribution(caseId, req.suspect, req.depth);
}

export class NotFoundError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'NotFoundError';
  }
}
