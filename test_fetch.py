import sys
from backend.ingestion.blockstream_client import BlockstreamClient
from backend.ingestion.extractor import SubgraphExtractor

client = BlockstreamClient()
print("live_enabled:", client.live_enabled)
edges, trunc = client.get_or_fetch_edges("13AM4VW2dhxYgXeQepoHkHSQuy6NgaEb94")
print(f"Edges fetched: {len(edges)}")
for e in edges[:5]:
    print(f"  {e.source_address} -> {e.target_address} ({e.amount_satoshis} sats)")

extractor = SubgraphExtractor()
G, vasps, meta, is_trunc = extractor.extract_subgraph("13AM4VW2dhxYgXeQepoHkHSQuy6NgaEb94", max_depth=1)
print(f"Graph nodes: {G.number_of_nodes()}, edges: {G.number_of_edges()}")
