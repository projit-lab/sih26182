import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
import requests

from backend.config import (
    BLOCKSTREAM_BASE_URL,
    MAX_RETRIES,
    REQUEST_TIMEOUT_SECONDS,
    USE_LIVE_API,
)
from backend.database.repositories import TransactionEdgeRepository
from backend.ingestion.schemas import UniformEdge

logger = logging.getLogger(__name__)

MEMPOOL_SPACE_BASE_URL = "https://mempool.space/api"


class BlockstreamClient:
    """
    On-chain Bitcoin transaction fetcher supporting:
    1. Primary: Blockstream Info API (https://blockstream.info/api)
    2. Fallback: Mempool.space API (https://mempool.space/api)
    3. UTXO Edge Resolution (vin -> vout with satoshi volume)
    4. Local DuckDB caching to eliminate duplicate API requests.
    """

    def __init__(
        self,
        base_url: str = BLOCKSTREAM_BASE_URL,
        fallback_url: str = MEMPOOL_SPACE_BASE_URL,
        repo: Optional[TransactionEdgeRepository] = None,
        use_live_api: bool = USE_LIVE_API,
    ):
        self.endpoints = [base_url.rstrip("/"), fallback_url.rstrip("/")]
        self.repo = repo or TransactionEdgeRepository()
        self.use_live_api = use_live_api
        self.session = requests.Session()

    def _get_with_failover(self, path: str) -> Optional[Any]:
        if not self.use_live_api:
            return None

        for endpoint in self.endpoints:
            url = f"{endpoint}/{path.lstrip('/')}"
            for attempt in range(MAX_RETRIES):
                try:
                    resp = self.session.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
                    if resp.status_code == 200:
                        return resp.json()
                    elif resp.status_code == 429:
                        sleep_time = 2 ** (attempt + 1)
                        logger.warning(f"Rate limit (429) on {endpoint}. Backing off {sleep_time}s...")
                        time.sleep(sleep_time)
                    else:
                        logger.warning(f"{endpoint} returned HTTP {resp.status_code}")
                        break
                except Exception as e:
                    logger.debug(f"Attempt {attempt + 1} failed for {url}: {e}")
                    time.sleep(1)

        logger.warning(f"All live API providers failed for path: {path}")
        return None

    def fetch_address_transactions(self, address: str) -> List[Dict[str, Any]]:
        data = self._get_with_failover(f"address/{address}/txs")
        return data if isinstance(data, list) else []

    def fetch_transaction_details(self, txid: str) -> Optional[Dict[str, Any]]:
        return self._get_with_failover(f"tx/{txid}")

    def resolve_utxo_edges(self, tx_obj: dict) -> List[UniformEdge]:
        """
        Parses raw Blockstream / Mempool.space transaction JSON into UniformEdge list:
        - vin[].prevout.scriptpubkey_address -> source
        - vout[].scriptpubkey_address -> target
        - vout[].value -> amount_satoshis
        """
        tx_hash = tx_obj.get("txid", "")
        status = tx_obj.get("status", {})
        block_time = status.get("block_time")
        timestamp = datetime.fromtimestamp(block_time) if block_time else datetime.utcnow()

        inputs = tx_obj.get("vin", [])
        outputs = tx_obj.get("vout", [])

        # Extract unique source addresses from inputs
        sources = []
        for vin in inputs:
            prevout = vin.get("prevout")
            if prevout and "scriptpubkey_address" in prevout:
                addr = prevout["scriptpubkey_address"]
                if addr and addr not in sources:
                    sources.append(addr)

        edges: List[UniformEdge] = []
        for vout in outputs:
            target_addr = vout.get("scriptpubkey_address")
            value = vout.get("value", 0)
            if not target_addr or value <= 0:
                continue

            if not sources:
                edges.append(
                    UniformEdge(
                        source_address="COINBASE",
                        target_address=target_addr,
                        amount_satoshis=value,
                        tx_hash=tx_hash,
                        timestamp=timestamp,
                        is_coinbase=True,
                    )
                )
            else:
                amount_per_source = max(1, value // len(sources))
                for src in sources:
                    if src != target_addr:
                        edges.append(
                            UniformEdge(
                                source_address=src,
                                target_address=target_addr,
                                amount_satoshis=amount_per_source,
                                tx_hash=tx_hash,
                                timestamp=timestamp,
                                is_coinbase=False,
                            )
                        )

        return edges

    def get_or_fetch_edges(self, address: str) -> List[UniformEdge]:
        # 1. Check local cache first
        cached = self.repo.get_outgoing_edges(address)
        if cached:
            return [
                UniformEdge(
                    source_address=r["source_address"],
                    target_address=r["target_address"],
                    amount_satoshis=r["amount_satoshis"],
                    tx_hash=r["tx_hash"],
                    timestamp=None,
                )
                for r in cached
            ]

        if not self.use_live_api:
            return []

        # 2. Fetch live via Blockstream / Mempool.space
        logger.info(f"Querying live Bitcoin API for {address}...")
        raw_txs = self.fetch_address_transactions(address)
        new_edges: List[UniformEdge] = []

        for tx in raw_txs:
            resolved = self.resolve_utxo_edges(tx)
            new_edges.extend(resolved)

        if new_edges:
            tuples = [
                (
                    e.tx_hash,
                    e.source_address,
                    e.target_address,
                    e.amount_satoshis,
                    e.timestamp,
                    e.chain,
                    e.is_coinbase,
                )
                for e in new_edges
            ]
            self.repo.insert_edges(tuples)

        return new_edges
