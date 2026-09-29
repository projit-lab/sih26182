import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import requests
import urllib3

from backend.config import (
    API_REQUEST_DELAY_MS,
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
        fallback_url: str = "https://blockstream.info/api",
        repo: Optional[TransactionEdgeRepository] = None,
        use_live_api: bool = USE_LIVE_API,
    ):
        # Configurable endpoints with failover
        raw_endpoints = [
            base_url.rstrip("/"),
            fallback_url.rstrip("/"),
            "https://mempool.space/api",
            "https://blockstream.info/api",
        ]
        seen = set()
        self.endpoints = [ep for ep in raw_endpoints if ep and not (ep in seen or seen.add(ep))]
        self.repo = repo or TransactionEdgeRepository()
        self.use_live_api = use_live_api
        self.session = requests.Session()
        self.session.verify = False
        self.session.trust_env = False
        adapter = requests.adapters.HTTPAdapter(pool_connections=25, pool_maxsize=25, max_retries=1)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        # Modern Chrome User-Agent prevents Cloudflare automated scraper throttling
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
        })

    @property
    def live_enabled(self) -> bool:
        import backend.config as cfg
        return self.use_live_api

    def _get_with_failover(self, path: str) -> Optional[Any]:
        if not self.live_enabled:
            return None

        for endpoint in self.endpoints:
            url = f"{endpoint}/{path.lstrip('/')}"
            try:
                if API_REQUEST_DELAY_MS > 0:
                    time.sleep(API_REQUEST_DELAY_MS / 1000.0)
                resp = self.session.get(url, timeout=REQUEST_TIMEOUT_SECONDS, verify=False)
                if resp.status_code == 200:
                    return resp.json()
                elif resp.status_code == 404:
                    # An address returning 404 means it has 0 transactions on-chain
                    logger.debug(f"{endpoint} returned 404 for {path} (0 transactions found).")
                    if "/txs" in path:
                        return []
                    return None
                elif resp.status_code == 400:
                    logger.warning(f"{endpoint} returned HTTP 400 for {path} (Invalid Bitcoin address checksum or malformed string).")
                elif resp.status_code == 429:
                    logger.warning(f"Rate limit (429) on {endpoint}. Quick backoff and trying next provider...")
                    time.sleep(0.3)
                else:
                    logger.warning(f"{endpoint} returned HTTP {resp.status_code}")
            except Exception as e:
                logger.warning(f"Provider {endpoint} unreachable for {path}: {e}")

        logger.warning(f"All live API providers failed for path: {path}")
        return None

    def fetch_address_transactions(self, address: str) -> Tuple[Optional[List[Dict[str, Any]]], bool]:
        data = self._get_with_failover(f"address/{address}/txs")
        if data is None:
            return None, False
        is_truncated = False
        if isinstance(data, list):
            if len(data) >= 25:
                is_truncated = True
            data = data[:25]
        else:
            data = []
        return data, is_truncated

    def fetch_transaction_details(self, txid: str) -> Optional[Dict[str, Any]]:
        return self._get_with_failover(f"tx/{txid}")

    def resolve_utxo_edges(self, tx_obj: dict) -> Tuple[List[UniformEdge], bool]:
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

        raw_inputs = tx_obj.get("vin", [])
        raw_outputs = tx_obj.get("vout", [])
        
        is_truncated = False
        if len(raw_inputs) > 15 or len(raw_outputs) > 15:
            is_truncated = True

        # Bound fan-out to top 15 inputs and 15 outputs to avoid combinatorial explosion
        inputs = raw_inputs[:15]
        outputs = raw_outputs[:15]

        # Extract source addresses and their respective input values (satoshis)
        source_values: Dict[str, int] = {}
        for vin in inputs:
            prevout = vin.get("prevout")
            if prevout and "scriptpubkey_address" in prevout:
                addr = prevout["scriptpubkey_address"]
                val = prevout.get("value", 0)
                if addr:
                    source_values[addr] = source_values.get(addr, 0) + val

        sources = list(source_values.keys())
        total_input_value = sum(source_values.values())

        is_coinbase_tx = any(vin.get("is_coinbase", False) for vin in inputs) or not inputs
        edges: List[UniformEdge] = []
        for vout in outputs:
            target_addr = vout.get("scriptpubkey_address")
            value = vout.get("value", 0)
            if not target_addr or value <= 0:
                continue

            if not sources:
                src_name = "COINBASE" if is_coinbase_tx else "UNKNOWN_INPUT"
                edges.append(
                    UniformEdge(
                        source_address=src_name,
                        target_address=target_addr,
                        amount_satoshis=value,
                        tx_hash=tx_hash,
                        timestamp=timestamp,
                        is_coinbase=is_coinbase_tx,
                    )
                )
            else:
                for src in sources:
                    if src != target_addr:
                        # Mathematically rigorous Proportional UTXO attribution (haircut method):
                        # Apportion vout proportionally to each input's financial stake in the transaction.
                        # Fall back safely to equal split if prevout satoshis are unavailable.
                        if total_input_value > 0 and source_values[src] > 0:
                            allocated_amount = max(1, round(value * (source_values[src] / total_input_value)))
                        else:
                            allocated_amount = max(1, value // len(sources))

                        edges.append(
                            UniformEdge(
                                source_address=src,
                                target_address=target_addr,
                                amount_satoshis=allocated_amount,
                                tx_hash=tx_hash,
                                timestamp=timestamp,
                                is_coinbase=False,
                            )
                        )

        return edges, is_truncated

    def fetch_from_blockchain_info(self, address: str) -> Tuple[List[UniformEdge], bool]:
        url = f"https://blockchain.info/rawaddr/{address}?limit=25"
        try:
            resp = self.session.get(url, timeout=REQUEST_TIMEOUT_SECONDS, verify=False)
            if resp.status_code != 200:
                return [], False
            data = resp.json()
            txs = data.get("txs", [])
            is_truncated = False
            if data.get("n_tx", 0) > 25 or len(txs) >= 25:
                is_truncated = True
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
            return edges, is_truncated
        except Exception as e:
            logger.warning(f"Blockchain.info fallback failed for {address}: {e}")
            return [], False

    def get_or_fetch_edges(self, address: str) -> Tuple[List[UniformEdge], bool]:
        cleaned = address.strip() if isinstance(address, str) else ""
        global_truncated = False

        # 1. Check if address has already had its transactions crawled from the live API
        if self.repo.is_address_crawled(cleaned):
            cached = self.repo.get_connected_edges(cleaned)
            return [
                UniformEdge(
                    source_address=r["source_address"],
                    target_address=r["target_address"],
                    amount_satoshis=r["amount_satoshis"],
                    tx_hash=r["tx_hash"],
                    timestamp=None,
                )
                for r in cached
            ], False

        # 2. Skip live API for synthetic/demo addresses or non-BTC formats (e.g. peel_hop_*, suspect_*, mixer_*)
        is_btc_format = (
            len(cleaned) >= 26
            and len(cleaned) <= 62
            and (cleaned.startswith("1") or cleaned.startswith("3") or cleaned.lower().startswith("bc1"))
        )

        if not is_btc_format or not self.live_enabled:
            # Offline / Synthetic mode: return whatever is already stored in local DB
            cached = self.repo.get_connected_edges(cleaned)
            return [
                UniformEdge(
                    source_address=r["source_address"],
                    target_address=r["target_address"],
                    amount_satoshis=r["amount_satoshis"],
                    tx_hash=r["tx_hash"],
                    timestamp=None,
                )
                for r in cached
            ] if cached else [], False

        # 3. Fetch live via Blockstream / Mempool.space
        logger.info(f"Querying live Bitcoin API for {cleaned}...")
        raw_txs, is_txs_truncated = self.fetch_address_transactions(cleaned)
        if is_txs_truncated:
            global_truncated = True
            
        new_edges: List[UniformEdge] = []

        if raw_txs is not None:
            for tx in raw_txs:
                resolved, is_utxo_truncated = self.resolve_utxo_edges(tx)
                if is_utxo_truncated:
                    global_truncated = True
                new_edges.extend(resolved)

        # 4. Fallback to Blockchain.info ONLY if primary providers failed with error (raw_txs is None)
        if raw_txs is None:
            logger.info(f"Falling back to Blockchain.info API for {cleaned}...")
            new_edges, is_fallback_truncated = self.fetch_from_blockchain_info(cleaned)
            if is_fallback_truncated:
                global_truncated = True

        if new_edges:
            # Prioritize largest value transfers and cap to top 100
            if len(new_edges) > 100:
                global_truncated = True
            new_edges.sort(key=lambda e: e.amount_satoshis, reverse=True)
            new_edges = new_edges[:100]
            tuples = [
                (
                    e.tx_hash,
                    e.source_address,
                    e.target_address,
                    e.amount_satoshis,
                    e.timestamp.isoformat() if e.timestamp else None,
                    e.chain,
                    e.is_coinbase,
                )
                for e in new_edges
            ]
            self.repo.insert_edges(tuples)

        # Mark address as crawled only if we obtained a valid response from the live network
        if new_edges or (raw_txs is not None and len(raw_txs) == 0):
            self.repo.mark_address_crawled(cleaned, chain="BTC")

        # Return all connected edges (both newly inserted and any existing)
        cached = self.repo.get_connected_edges(cleaned)
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
            ], global_truncated

        return new_edges, global_truncated

