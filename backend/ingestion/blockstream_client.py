import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
import requests
import urllib3

from backend.config import (
    BLOCKSTREAM_BASE_URL,
    MAX_RETRIES,
    REQUEST_TIMEOUT_SECONDS,
    USE_LIVE_API,
)
from backend.database.repositories import TransactionEdgeRepository
from backend.ingestion.schemas import UniformEdge

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

MEMPOOL_SPACE_BASE_URL = "https://mempool.space/api"
BLOCKCHAIN_INFO_BASE_URL = "https://blockchain.info"


class BlockstreamClient:
    """
    On-chain Bitcoin transaction fetcher supporting:
    1. Primary: Mempool.space API (Cloudflare Anycast edge network)
    2. Failover: Blockstream Info API (https://blockstream.info/api)
    3. Emergency Backup: Blockchain.info API
    4. Local DuckDB/SQLite caching to eliminate duplicate requests.
    """

    def __init__(
        self,
        base_url: str = BLOCKSTREAM_BASE_URL,
        fallback_url: str = MEMPOOL_SPACE_BASE_URL,
        repo: Optional[TransactionEdgeRepository] = None,
        use_live_api: bool = USE_LIVE_API,
    ):
        # Mempool.space first (fastest Anycast CDN routing), then Blockstream
        self.endpoints = [fallback_url.rstrip("/"), base_url.rstrip("/")]
        self.repo = repo or TransactionEdgeRepository()
        self.use_live_api = use_live_api
        self.session = requests.Session()
        self.session.verify = False
        self.session.trust_env = False
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SIH26182/1.0"})

    @property
    def live_enabled(self) -> bool:
        import backend.config as cfg
        return self.use_live_api or getattr(cfg, "USE_LIVE_API", True)

    def _get_with_failover(self, path: str) -> Optional[Any]:
        if not self.live_enabled:
            return None

        for endpoint in self.endpoints:
            url = f"{endpoint}/{path.lstrip('/')}"
            try:
                resp = self.session.get(url, timeout=REQUEST_TIMEOUT_SECONDS, verify=False)
                if resp.status_code == 200:
                    return resp.json()
                elif resp.status_code == 429:
                    logger.warning(f"Rate limit (429) on {endpoint}. Trying next provider...")
                else:
                    logger.warning(f"{endpoint} returned HTTP {resp.status_code}")
            except Exception as e:
                logger.warning(f"Provider {endpoint} unreachable for {path}: {e}")

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

        # Bound fan-out to top 15 inputs and 15 outputs to avoid combinatorial explosion
        inputs = tx_obj.get("vin", [])[:15]
        outputs = tx_obj.get("vout", [])[:15]

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

    def fetch_address_transactions(self, address: str) -> List[dict]:
        txs = self._get_with_failover(f"address/{address}/txs")
        if isinstance(txs, list):
            return txs[:20]
        return []

    def fetch_from_blockchain_info(self, address: str) -> List[UniformEdge]:
        url = f"https://blockchain.info/rawaddr/{address}?limit=25"
        try:
            resp = self.session.get(url, timeout=REQUEST_TIMEOUT_SECONDS, verify=False)
            if resp.status_code != 200:
                return []
            data = resp.json()
            txs = data.get("txs", [])
            edges: List[UniformEdge] = []
            for tx in txs:
                tx_hash = tx.get("hash", "")
                time_val = tx.get("time")
                timestamp = datetime.fromtimestamp(time_val) if time_val else datetime.utcnow()
                sources = []
                for inp in tx.get("inputs", []):
                    prev = inp.get("prev_out", {})
                    addr = prev.get("addr")
                    if addr and addr not in sources:
                        sources.append(addr)
                for out in tx.get("out", []):
                    target_addr = out.get("addr")
                    value = out.get("value", 0)
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
                        amt = max(1, value // len(sources))
                        for src in sources:
                            if src != target_addr:
                                edges.append(
                                    UniformEdge(
                                        source_address=src,
                                        target_address=target_addr,
                                        amount_satoshis=amt,
                                        tx_hash=tx_hash,
                                        timestamp=timestamp,
                                        is_coinbase=False,
                                    )
                                )
            return edges
        except Exception as e:
            logger.warning(f"Blockchain.info fallback failed for {address}: {e}")
            return []

    def get_or_fetch_edges(self, address: str) -> List[UniformEdge]:
        # 1. Check local cache first (both inbound and outbound)
        cached = self.repo.get_connected_edges(address)
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

        if not self.live_enabled:
            return []

        # 2. Fetch live via Blockstream / Mempool.space
        logger.info(f"Querying live Bitcoin API for {address}...")
        raw_txs = self.fetch_address_transactions(address)
        new_edges: List[UniformEdge] = []

        for tx in raw_txs:
            resolved = self.resolve_utxo_edges(tx)
            new_edges.extend(resolved)

        # 3. Fallback to Blockchain.info if Blockstream / Mempool failed or returned empty
        if not new_edges:
            logger.info(f"Falling back to Blockchain.info API for {address}...")
            new_edges = self.fetch_from_blockchain_info(address)

        if new_edges:
            # Prioritize largest value transfers and cap to top 100
            new_edges.sort(key=lambda e: e.amount_satoshis, reverse=True)
            new_edges = new_edges[:100]
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
