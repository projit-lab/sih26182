from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class UniformEdge:
    """
    Uniform schema for transaction movements across UTXO and Account-based chains.
    Edge = (source_address, target_address, amount_crypto, tx_hash, timestamp)
    """
    source_address: str
    target_address: str
    amount_satoshis: int
    tx_hash: str
    timestamp: Optional[datetime] = None
    chain: str = "BTC"
    is_coinbase: bool = False

    @property
    def amount_btc(self) -> float:
        return self.amount_satoshis / 100_000_000.0


@dataclass(frozen=True)
class EntityTagItem:
    address: str
    entity_name: str
    category: str  # 'exchange', 'mixer', 'custodial', 'illicit'
    chain: str = "BTC"
    source: str = "GraphSense"
    confidence: float = 1.0
