import urllib.request
import json
req = urllib.request.Request('http://localhost:5173/engine/attribute', data=b'{"case_id":"synthetic_mixer","max_hops":1}', headers={'Content-Type': 'application/json'})
r = urllib.request.urlopen(req)
print(r.read().decode('utf-8'))
