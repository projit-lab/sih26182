# SIH26182 — Core Engine Contract Specification
### Freeze this before building. Everyone codes against this, not against each other's internals.

---

## 1. What the engine takes as input

### Graph object (built by General CSE's data pipeline, consumed by your engine)

A weighted, undirected graph. In Python, this is a `networkx.Graph` object where:

- **Nodes** are wallet address strings (e.g., `"1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"`, or for synthetic demo data, simple IDs like `"suspect_042"`, `"VASP_3"`).
- **Edges** have a required `weight` attribute (float) representing transaction volume/frequency between two wallets.

```python
# Example construction (what General CSE's pipeline must produce):
import networkx as nx

G = nx.Graph()
G.add_edge("suspect_042", "mixer_hop_1", weight=1.4)
G.add_edge("mixer_hop_1", "VASP_true", weight=2.1)
G.add_edge("suspect_042", "decoy_hop_1", weight=0.05)
G.add_edge("decoy_hop_1", "VASP_decoy", weight=0.05)
```

### Function call signature (already built, in `src/attribution/engine.py`)

```python
from src.attribution.engine import AttributionEngine

engine = AttributionEngine(graph)  # graph = the networkx.Graph above

result = engine.attribute(
    suspect="suspect_042",              # str — the wallet address being investigated
    candidates=["VASP_true", "VASP_decoy", "VASP_other"]  # list[str] — candidate VASP node IDs
)
```

**Rules everyone building against this must know:**
- `suspect` and every entry in `candidates` MUST already exist as nodes in `graph` — the engine does not create nodes, it only ranks existing ones.
- `candidates` can be any length ≥ 1.
- The graph can be arbitrarily large — the engine factorizes once and reuses that factorization, so for multiple suspects against the same graph, use `attribute_batch()` (see below) rather than calling `attribute()` in a loop from outside, to avoid re-factorizing unnecessarily.

### Batch call (for demo scenarios with many suspects at once)

```python
results = engine.attribute_batch(
    suspects=["suspect_042", "suspect_099"],
    candidates=["VASP_true", "VASP_decoy", "VASP_other"]
)
# returns: list[AttributionResult], one per suspect, same candidate pool for all
```

---

## 2. What the engine returns as output

```python
@dataclass
class AttributionResult:
    suspect: str                 # echoes back the input suspect wallet
    ranked_candidates: list      # list[str] — candidate VASP IDs, BEST GUESS FIRST
    scores: dict                 # {candidate_id: float} — raw effective resistance value
                                  #   LOWER score = stronger/more likely connection
    method: str = "effective_resistance"  # constant, always this value
```

### Example return value

```python
AttributionResult(
    suspect="suspect_042",
    ranked_candidates=["VASP_true", "VASP_other", "VASP_decoy"],
    scores={
        "VASP_true": 0.42,
        "VASP_other": 1.85,
        "VASP_decoy": 3.10,
    },
    method="effective_resistance"
)
```

**Rules for anyone consuming this (API layer, Frontend, ML-A's benchmark module):**
- `ranked_candidates[0]` is always the engine's top prediction.
- `scores` are raw effective-resistance values, **not** normalized probabilities and **not** percentages. If the Frontend wants a "confidence score" out of 100 for display, that conversion (e.g., inverse-normalize across the candidate scores) happens in the API layer or Frontend — not inside the engine. This keeps the engine's output mathematically pure and lets the display layer decide how to present it.
- If a candidate doesn't exist in the graph, its score will be `float('inf')` and it will always rank last — handle this gracefully in the UI (e.g., show "no path found" rather than a raw `inf`).

---

## 3. Error cases everyone must handle

| Condition | What the engine does | What the caller (API layer) must do |
|---|---|---|
| `suspect` not in graph | Raises `ValueError` | Catch it, return HTTP 404 with a clear message ("suspect wallet not found in current graph") |
| A candidate not in graph | Does NOT raise — returns `inf` score for that candidate, ranks it last | Frontend should visually flag candidates with `inf` score as "no connection found," not just silently show a huge number |
| Empty `candidates` list | Returns empty `ranked_candidates` and `scores` | API/Frontend should validate `candidates` is non-empty before calling, and show a user-facing error if it isn't |

---

## 4. The API contract (what General CSE builds around the engine)

### Request

```
POST /attribute
Content-Type: application/json

{
  "suspect_wallet": "suspect_042",
  "candidate_vasps": ["VASP_true", "VASP_decoy", "VASP_other"]
}
```

### Response (success)

```json
{
  "suspect": "suspect_042",
  "ranked_candidates": ["VASP_true", "VASP_other", "VASP_decoy"],
  "scores": {
    "VASP_true": 0.42,
    "VASP_other": 1.85,
    "VASP_decoy": 3.10
  },
  "method": "effective_resistance"
}
```

### Response (suspect not found)

```
HTTP 404
{
  "detail": "Suspect wallet 'suspect_042' not found in current graph"
}
```

This already matches what's scaffolded in `src/api/main.py` — General CSE's job is filling in `load_demo_graph()` with a real data source instead of the current empty placeholder, nothing about this contract needs to change.

---

## 5. What ML-B / Frontend can build RIGHT NOW, before the engine is scale-tested

Since the contract above is frozen, ML-B and Frontend do not need to wait for you to finish scale/performance work. They can:

- Build the entire UI flow against **mocked responses** shaped exactly like the JSON example in Section 4.
- Build the "live comparison" visual (effective resistance vs. shortest-path) using pre-computed results from ML-A's validation runs as placeholder data, then swap in real live API calls once your engine is confirmed working end-to-end.

---

## 6. What changes if real chain data (GraphSense/Elliptic++) becomes available

**Nothing in this contract changes.** Real data just becomes a different `graph` object built by General CSE's ingestion pipeline (real wallet addresses instead of `suspect_042`-style synthetic IDs) — everything downstream (engine, API, Frontend) works identically because they only ever interact through this same contract.

---

## Summary — what to do with this document

1. **You**: build/finish the engine against Sections 1–3 exactly as specified — don't change the function signatures or return shape without telling everyone.
2. **General CSE**: build `load_demo_graph()` and the API layer against Sections 1, 3, and 4.
3. **ML-A**: point the validation/benchmark module at `AttributionEngine` directly (Section 1–2), confirm numbers match your standalone validation scripts.
4. **ML-B + Frontend**: build against Section 4's JSON shape today, using mocked data — don't wait.
