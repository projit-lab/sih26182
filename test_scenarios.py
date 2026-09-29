import httpx
import json

base='http://localhost:8000/api/v1/investigate'
data=[
    {'case_id': 'silkroad', 'suspect_address': '1F1tAaz5x1HUXrCNLbtMDqcw6o5GNn4xqX'},
    {'suspect_address': 'suspect_042'},
    {'suspect_address': '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa'},
    {'suspect_address': 'suspect_003'}
]

for d in data:
    try:
        r = httpx.post(base, json=d, timeout=30)
        v = r.json().get('ranked_vasps') if r.status_code == 200 else r.text
        print(f'{d["suspect_address"]}: {r.status_code}\n{v}\n')
    except Exception as e:
        print(f'{d["suspect_address"]}: {e}')
