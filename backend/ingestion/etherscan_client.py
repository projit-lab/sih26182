import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
import requests

from backend.config import MAX_RETRIES, REQUEST_TIMEOUT_SECONDS, USE_LIVE_API
from backend.database.repositories import TransactionEdgeRepository
from backend.ingestion.schemas import UniformEdge

logger = logging.getLogger(__name__)

ETHERSCAN_BASE_URL = "https://api.etherscan.io/api"
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "YourApiKeyToken")


class EtherscanClient:
    """
    On-chain Ethereum/EVM account-based transaction fetcher using Etherscan API.
    Resolves 'from' -> 'to' value transfers into UniformEdge objects
    with local DuckDB caching.
    """

    def __init__(
        self,
        api_key: str = ETHERSCAN_API_KEY,
        base_url: str = ETHERSCAN_BASE_URL,
        repo: Optional[TransactionEdgeRepository] = None,
        use_live_api: bool = USE_LIVE_API,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.repo = repo or TransactionEdgeRepository()
        self.use_live_api = use_live_api
        self.session = requests.Session()

    def fetch_account_transactions(
        self, address: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        if not self.use_live_api:
            return []

        params = {
            "module": "account",
            "action": "txlist",
            "address": address,
            "startblock": 0,
            "endblock": 99999999,
            "page": 1,
            "offset": limit,
            "sort": "desc",
            "apikey": self.api_key,
        }

        for attempt in range(MAX_RETRIES):
            try:
                resp = self.session.get(
                    self.base_url, params=params, timeout=REQUEST_TIMEOUT_SECONDS
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == "1" and isinstance(data.get("result"), list):
                        return data["result"]
                    elif "rate limit" in str(data.get("message", "")).lower():
                        time.sleep(2 ** (attempt + 1))
                    else:
                        logger.warning(f"Etherscan message: {data.get('message')}")
                        return []
            except Exception as e:
                logger.debug(f"Etherscan attempt {attempt + 1} failed: {e}")
                time.sleep(1)

        return []

    def resolve_evm_edges(self, raw_txs: List[dict]) -> List[UniformEdge]:
        edges: List[UniformEdge] = []
        for tx in raw_txs:
            # Skip failed transactions (isError == "1")
            if tx.get("isError") == "1":
                continue

            src = tx.get("from", "").strip()
            dst = tx.get("to", "").strip()
            tx_hash = tx.get("hash", "")
            raw_value = tx.get("value", "0")

            if not src or not dst or src == dst:
                continue

            try:
                wei = int(raw_value)
                # Convert Wei to Gwei/normalized satoshi-equivalent units (1 ETH = 1e18 Wei ~ 1e8 sats scale)
                amount_normalized = max(1, wei // 10_000_000_000)
            except ValueError:
                amount_normalized = 1

            ts_raw = tx.get("timeStamp")
            timestamp = (
                datetime.fromtimestamp(int(ts_raw))
                if ts_raw and ts_raw.isdigit()
                else datetime.utcnow()
            )

            edges.append(
                UniformEdge(
                    source_address=src,
                    target_address=dst,
                    amount_satoshis=amount_normalized,
                    tx_hash=tx_hash,
                    timestamp=timestamp,
                    chain="ETH",
                    is_coinbase=False,
                )
            )

        return edges

    def get_or_fetch_edges(self, address: str) -> List[UniformEdge]:
        cached = self.repo.get_outgoing_edges(address)
        if cached:
            return [
                UniformEdge(
                    source_address=r["source_address"],
                    target_address=r["target_address"],
                    amount_satoshis=r["amount_satoshis"],
                    tx_hash=r["tx_hash"],
                    timestamp=None,
                    chain="ETH",
                )
                for r in cached
            ]

        if not self.use_live_api:
            return []

        raw_txs = self.fetch_account_transactions(address)
        new_edges = self.resolve_evm_edges(raw_txs)

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
