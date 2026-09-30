import urllib.request, json

req = urllib.request.Request('http://localhost:8001/attribute', data=b'{"case_id":"synthetic_mixer"}', headers={'Content-Type': 'application/json'})
r = urllib.request.urlopen(req)
d = json.loads(r.read())

out = {
    "ranked_candidates": d.get("ranked_candidates"),
    "scores": d.get("scores"),
    "separation_ratio": d.get("separation_ratio"),
    "dijkstra_comparison": d.get("dijkstra_comparison"),
    "truth": d.get("truth"),
    "node_count": len(d.get("graph_elements", {}).get("nodes", [])),
    "edge_count": len(d.get("graph_elements", {}).get("edges", []))
}

print(json.dumps(out, indent=2))
