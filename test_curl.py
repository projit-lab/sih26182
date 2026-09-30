import urllib.request, json
req = urllib.request.Request('http://localhost:8001/attribute', data=b'{"case_id":"silkroad"}', headers={'Content-Type': 'application/json'})
r = urllib.request.urlopen(req)
d = json.loads(r.read())
n = d['graph_elements']['nodes']
e = d['graph_elements']['edges']
d['graph_elements']['nodes'] = f"<list of {len(n)} nodes, first 3: {n[:3]}>"
d['graph_elements']['edges'] = f"<list of {len(e)} edges, first 3: {e[:3]}>"
print(json.dumps(d, indent=2))
