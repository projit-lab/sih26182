"""
Data Ingestion Pipeline:
- GraphSense TagPacks & Crypto-Tags (Entity Registries)
- Blockstream Info & Mempool.space APIs (Bitcoin UTXO)
- Etherscan Developer API (Ethereum/EVM Account-based)
- Academic Elliptic++ Ingestion Loader
- Downstream Subgraph Extractor with VASP boundary pruning
"""
from backend.ingestion.schemas import UniformEdge, EntityTagItem
from backend.ingestion.tagpack_loader import TagPackLoader
from backend.ingestion.blockstream_client import BlockstreamClient
from backend.ingestion.etherscan_client import EtherscanClient
from backend.ingestion.extractor import SubgraphExtractor
from backend.ingestion.elliptic_loader import EllipticLoader

__all__ = [
    "UniformEdge",
    "EntityTagItem",
    "TagPackLoader",
    "BlockstreamClient",
    "EtherscanClient",
    "SubgraphExtractor",
    "EllipticLoader",
]
