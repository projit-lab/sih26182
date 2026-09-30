import sys

path = 'graph_visualizer.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

start_marker = '      demo_6hop: {\n'
end_marker = '      silkroad: {\n'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker, start_idx)

if start_idx != -1 and end_idx != -1:
    removed = content[start_idx + len(start_marker):end_idx]
    replacement = """        "nodes": [
          { "data": { "id": "msg", "label": "Run an investigation to load a graph", "role": "hop" } }
        ],
        "edges": []
      },
"""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content[:start_idx + len(start_marker)] + replacement + content[end_idx:])
    
    with open('removed.txt', 'w', encoding='utf-8') as f:
        f.write(removed)
    print('Replaced')
else:
    print('Not found')
