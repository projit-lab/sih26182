import urllib.request, json
req = urllib.request.Request('http://localhost:8001/attribute', data=b'{"case_id":"silkroad", "max_hops":1}', headers={'Content-Type': 'application/json'})
r = urllib.request.urlopen(req)
d = json.loads(r.read())
print(d.get('unreachable'))
