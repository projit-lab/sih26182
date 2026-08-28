# SIH26182 — Wallet-to-VASP Attribution via Circuit Theory

**Status:** Hypothesis validated (6 rounds of testing, including 2 self-caught bugs and fixes).
Core engine ~30% built. Currently in active development.

## Core idea
Rank candidate VASPs for a suspect wallet by **effective resistance** (graph Laplacian
solve) instead of shortest-path. Validated: ties shortest-path on simple cases, significantly
beats it — and beats a properly-trained supervised GraphSAGE GNN — when funds are
mixer-obfuscated (the realistic case), because effective resistance aggregates evidence
across ALL parallel paths, not just the cheapest one, and requires zero labeled training data.

## Repo structure
```
docs/                      -- full team research dossier, engine contract spec, team briefing
src/attribution/engine.py  -- the core AttributionEngine (production code)
src/api/main.py            -- FastAPI service wrapping the engine
tests/                      -- smoke tests for the engine
validation/                 -- all validation/benchmark scripts and results (research code,
                               not production -- proves the core hypothesis)
```

## Quick start
```bash
pip install -r requirements.txt
python3 tests/test_engine.py        # smoke test
uvicorn src.api.main:app --reload   # run the API locally
```

## Read this first
- `docs/TEAM_BRIEFING.md` -- plain-English + technical explainer of the whole project, full glossary
- `docs/RESEARCH_DOSSIER.pdf` -- complete research dossier: problem statement, validation journey, results
- `docs/ENGINE_CONTRACT.md` -- the input/output contract everyone builds against

## Validated results (synthetic data, 6 rounds of testing)
| Comparison | Result |
|---|---|
| Effective Resistance vs. Shortest Path (mixer-obfuscated cases) | 94.6% vs 75.0% (p=3.8e-5), replicated independently at 87.5% vs 39.0% |
| Effective Resistance vs. Supervised GraphSAGE (best case, N=1000 labeled examples) | 84.3% vs 71.8%, no crossover found up to N=2500 |
| Out-of-distribution (unseen obfuscation pattern) accuracy drop | ER: -6.0pp vs GraphSAGE: -24.5pp |
| Statistical significance (final comparison) | McNemar's chi-sq=49.04, p=2.5e-12 |

See `docs/RESEARCH_DOSSIER.pdf` Section 8 for the full validation journey, including two bugs
we found and fixed in our own testing along the way.

## Known open items (not blocking, tracked honestly)
- Engine not yet tested at realistic graph scale (only a 4-node smoke test so far)
- No real chain data ingestion wired up yet (GraphSense/Elliptic++ access pending)
- SAHYOG integration, multi-chain support, entity tagging: scoped as roadmap (see dossier Section 11)
