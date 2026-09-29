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
    
    out_dir = Path("docs/results")
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "silkroad_numbers.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(out_lines))

if __name__ == "__main__":
    main()
