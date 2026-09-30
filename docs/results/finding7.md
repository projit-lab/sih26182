# Finding 7: Disconnected-Wallet Bias

## Mechanism
Method (a) `effective_resistance_rank` in `validation/attribution_methods_baselines.py` factorizes the entire graph's Laplacian at once, grounding node 0. If a node is in a different connected component than node 0, the system for that component is singular, and the sparse LU solver (`spla.splu`) silently returns finite garbage values (typically proportional to 1/regularization) instead of failing. This causes unreachable VASPs to receive finite effective resistance scores, sometimes ranking them highly by accident (the "disconnected-wallet bias"). 
Method (b) `AttributionEngine` fixes this by correctly factorizing each connected component independently and formally marking cross-component queries as unreachable (`float('inf')`).

## Repo Pipeline (validation/finding7_study.py)
We evaluated the finding on the repository's synthetic benchmark. 

```text
--- Graph Stats per Seed ---
Seed 1: 1 components
Seed 2: 1 components
Seed 3: 1 components
Seed 4: 1 components
Seed 5: 1 components

Same-Component Queries (n=1000):
  VASP_2: 38.5% (385)
  VASP_1: 30.9% (309)
  VASP_0: 16.7% (167)
  VASP_3: 6.9% (69)
  VASP_4: 3.7% (37)
  VASP_5: 3.3% (33)
  Max share: 38.5% vs chance 16.7%

Different-Component Queries: 0 queries

Bug isolation check on different-component candidate evaluations (total=0):
  Method (a) gave finite score: 0/0 (0.0%)
  Method (b) marked unreachable: 0/0 (0.0%)
```
In the `robustness_check.py` generator, the graph consists of a single connected component for all 5 seeds. As a result, the bug (which requires disconnected components to trigger) never manifests in the repo's benchmark.

## Headline Pipeline
We searched for `data_scarcity_validation.py` to evaluate whether the 84.3% headline accuracy was affected by this bug. 
Paths checked:
- This repository: `C:\Users\praji\Desktop\blockchainheisttesting\sih26182`
- Git history: `git log --all -- '*data_scarcity*'`
- Desktop: `C:\Users\praji\Desktop`
- Documents: `C:\Users\praji\Documents`
- Downloads: `C:\Users\praji\Downloads`

**Conclusion**: could not be tested: file missing. The `data_scarcity_validation.py` file was completely absent from all specified locations, so we cannot determine if the 84.3% headline claim was artificially inflated by the disconnected-wallet bias.
