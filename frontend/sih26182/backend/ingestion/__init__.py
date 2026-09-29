"""
Data Ingestion Pipeline:
- GraphSense TagPacks & Crypto-Tags (Entity Registries)
- Blockstream Info & Mempool.space APIs (Bitcoin UTXO)
- Etherscan Developer API (Ethereum/EVM Account-based)
- Academic Elliptic++ Ingestion Loader
- Downstream Subgraph Extractor with VASP boundary pruning
"""
from backend.ingestion.schemas import UniformEdge, EntityTagItem

_lazy_imports = {
    "TagPackLoader": ".tagpack_loader",
    "BlockstreamClient": ".blockstream_client",
    "EtherscanClient": ".etherscan_client",
    "SubgraphExtractor": ".extractor",
    "EllipticLoader": ".elliptic_loader",
}

def __getattr__(name: str):
    if name in _lazy_imports:
        import importlib
        module = importlib.import_module(_lazy_imports[name], __package__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "UniformEdge",
    "EntityTagItem",
    "TagPackLoader",
    "BlockstreamClient",
    "EtherscanClient",
    "SubgraphExtractor",
    "EllipticLoader",
]
