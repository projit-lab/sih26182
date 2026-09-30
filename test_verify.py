import urllib.request, json

cases = [
    ("silkroad", [1, 2, 3, None]),
    ("synthetic_mixer", [1, 2, 3, 4, 6, None])
]

for case_id, hops_list in cases:
    for hops in hops_list:
        payload = {"case_id": case_id}
        if hops is not None:
            payload["max_hops"] = hops
            
        req = urllib.request.Request('http://localhost:8001/attribute', data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
        r = urllib.request.urlopen(req)
        d = json.loads(r.read())
        
        print(f"--- {case_id} max_hops={hops} ---")
        print(f"depth_nodes: {d.get('depth_nodes')}, depth_edges: {d.get('depth_edges')}")
        print("ranked_candidates:", d.get('ranked_candidates'))
        print("scores:", d.get('scores'))
        print("separation_ratio:", d.get('separation_ratio'))
        print("unreachable:", d.get('unreachable'))
        print("unreachable_reasons:", d.get('unreachable_reasons'))
        print("dijkstra_comparison:", d.get('dijkstra_comparison'))
        print()
