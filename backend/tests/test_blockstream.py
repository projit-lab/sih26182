from backend.database.db import DatabaseConnection, init_db
from backend.database.repositories import TransactionEdgeRepository
from backend.ingestion.blockstream_client import BlockstreamClient


def test_utxo_edge_resolution(tmp_path):
    test_db_path = tmp_path / "test_blockstream.sqlite"
    db = DatabaseConnection(db_path=test_db_path, use_duckdb=False)
    init_db(db)
    repo = TransactionEdgeRepository(db)

    client = BlockstreamClient(repo=repo, use_live_api=False)

    # Simulated raw Blockstream transaction json
    sample_tx = {
        "txid": "7a3a5f973c51ef67e23a41b18126e857e4e6f47761eb103e617983637e10b144",
        "vin": [
            {
                "prevout": {
                    "scriptpubkey_address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
                    "value": 5000000000,
                }
            }
        ],
        "vout": [
            {
                "scriptpubkey_address": "1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s",
                "value": 4500000000,
            },
            {
                "scriptpubkey_address": "1ChangeAddressExample992817xKl8194",
                "value": 490000000,
            },
        ],
        "status": {"confirmed": True, "block_time": 1725300000},
    }

    edges = client.resolve_utxo_edges(sample_tx)
    assert len(edges) == 2
    assert edges[0].source_address == "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
    assert edges[0].target_address == "1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s"
    assert edges[0].amount_satoshis == 4500000000

    # Test caching
    tuples = [(e.tx_hash, e.source_address, e.target_address, e.amount_satoshis, e.timestamp, e.chain, e.is_coinbase) for e in edges]
    repo.insert_edges(tuples)

    # Verify get_or_fetch_edges returns cached edges even with use_live_api=False
    cached_edges = client.get_or_fetch_edges("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
    assert len(cached_edges) == 2
