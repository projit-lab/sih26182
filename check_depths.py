import urllib.request, json
req = urllib.request.Request('http://localhost:8001/attribute', data=b'{"case_id":"silkroad"}', headers={'Content-Type': 'application/json'})
r = urllib.request.urlopen(req)
d = json.loads(r.read())
print(d.get('hop_depths'))
