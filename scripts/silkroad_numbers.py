import json
from pathlib import Path
from src.api.main import load_case
from src.attribution.engine import AttributionEngine

def main():
    case = load_case("silkroad")
    G = case["graph"]
    candidates = list(case["candidate_vasps"].keys())
    suspect = case["suspect"]
    
    with open("data/cases/silkroad/meta.json", "r", encoding="utf-8") as f:
        meta = json.load(f)
        
    out_lines = []
    
    def log(msg):
        print(msg)
        out_lines.append(msg)
        
    log("=== Graph Health ===")
    engine = AttributionEngine(G)
    health = engine.graph_health()
    log(json.dumps(health, indent=2))
    log("")
    
    for dc in [False, True]:
        log(f"=== Degree Correction: {dc} ===")
        engine = AttributionEngine(G, degree_correction=dc)
        res = engine.attribute(suspect, candidates)
        
        log(f"Separation Ratio: {res.separation_ratio}")
        log("Ranked Candidates:")
        for c in res.ranked_candidates:
            name = case["candidate_vasps"].get(c, c)
            score = res.scores.get(c)
            raw = res.raw_resistance.get(c)
            log(f"  {name} ({c}): score={score}, raw R_eff={raw}")
            
        log("Unreachable:")
        for c in res.unreachable:
            name = case["candidate_vasps"].get(c, c)
            log(f"  {name} ({c})")
        log("")
        
    log("=== Null Test Runs ===")
    log(json.dumps(meta.get("null_test", []), indent=2))
    log("")
    
    log("=== Null Test (degree_correction=True) ===")
    engine_dc = AttributionEngine(G, degree_correction=True)
    exclude = {suspect, *candidates}
    import numpy as np
    for n, seed in [(40, 0), (40, 1), (40, 2), (200, 0)]:
        pool = [n_ for n_ in G.nodes() if n_ not in exclude]
        rng = np.random.default_rng(seed)
        sample = [pool[i] for i in rng.choice(len(pool), min(n, len(pool)), replace=False)]
        
        reachable = 0
        unreachable = 0
        wins = {}
        for s in sample:
            try:
                res = engine_dc.attribute(s, candidates)
            except ValueError:
                unreachable += 1
                continue
                
            if len(res.ranked_candidates) == 0:
                unreachable += 1
            else:
                reachable += 1
                top = res.ranked_candidates[0]
                wins[top] = wins.get(top, 0) + 1
                
        log(f"n={n} seed={seed}: reachable={reachable} unreachable={unreachable}")
        log(f"  wins: {wins}")
    
    out_dir = Path("docs/results")
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "silkroad_numbers.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(out_lines))

if __name__ == "__main__":
    main()
