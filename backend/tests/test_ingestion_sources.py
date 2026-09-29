from pathlib import Path
from backend.database.db import DatabaseConnection, init_db
from backend.database.repositories import EntityTagRepository, TransactionEdgeRepository
from backend.ingestion.tagpack_loader import TagPackLoader
from backend.ingestion.etherscan_client import EtherscanClient
from backend.ingestion.elliptic_loader import EllipticLoader
from backend.ingestion.blockstream_client import BlockstreamClient


def test_yaml_tagpack_parsing(tmp_path):
    test_db = tmp_path / "test_yaml.sqlite"
    db = DatabaseConnection(db_path=test_db, use_duckdb=False)
    init_db(db)
    tag_repo = EntityTagRepository(db)
    loader = TagPackLoader(repo=tag_repo)

    yaml_sample = """
title: "Test Exchange Pack"
creator: "GraphSense"
currency: "BTC"
tags:
  - address: "1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s"
    label: "Binance Main"
    category: "exchange"
  - address: "1AnwDVbwsLB4om3PnZ54FjWc1m8qP2XbVq"
    label: "WazirX Primary"
    category: "exchange"
"""
    count = loader.load_from_text(yaml_sample, filename="sample.yaml")
    assert count == 2

    tag1 = tag_repo.get_tag("1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s")
    assert tag1 is not None
    assert "Binance" in tag1["entity_name"]
    assert tag1["category"] == "exchange"


def test_etherscan_edge_resolution(tmp_path):
    test_db = tmp_path / "test_eth.sqlite"
    db = DatabaseConnection(db_path=test_db, use_duckdb=False)
    init_db(db)
    edge_repo = TransactionEdgeRepository(db)
    client = EtherscanClient(repo=edge_repo, use_live_api=False)

    raw_txs = [
        {
            "hash": "0xabc1234567890",
            "from": "0x1111111111111111111111111111111111111111",
            "to": "0x2222222222222222222222222222222222222222",
            "value": "1000000000000000000",  # 1 ETH in Wei
            "timeStamp": "1725300000",
            "isError": "0",
        }
    ]
    edges, _ = client.resolve_evm_edges(raw_txs)
    assert len(edges) == 1
    assert edges[0].source_address == "0x1111111111111111111111111111111111111111"
    assert edges[0].target_address == "0x2222222222222222222222222222222222222222"
    assert edges[0].amount_satoshis > 0
    assert edges[0].chain == "ETH"

    # Test caching and get_outgoing_edges
    tuples = [(e.tx_hash, e.source_address, e.target_address, e.amount_satoshis, e.timestamp, e.chain, e.is_coinbase) for e in edges]
    edge_repo.insert_edges(tuples)
    cached, _ = client.get_or_fetch_edges("0x1111111111111111111111111111111111111111")
    assert len(cached) == 1
    assert cached[0].target_address == "0x2222222222222222222222222222222222222222"


def test_elliptic_loader(tmp_path):
    test_db = tmp_path / "test_elliptic.sqlite"
    db = DatabaseConnection(db_path=test_db, use_duckdb=False)
    init_db(db)
    tag_repo = EntityTagRepository(db)
    edge_repo = TransactionEdgeRepository(db)

    loader = EllipticLoader(tag_repo=tag_repo, edge_repo=edge_repo)
    tags_count, edges_count = loader.generate_and_ingest_sample()

    assert tags_count > 0
    assert edges_count > 0

    # Verify illicit suspect and licit exchange were tagged
    suspect_tag = tag_repo.get_tag("tx_101")
    assert suspect_tag is not None
    assert suspect_tag["category"] == "mixer"

    exchange_tag = tag_repo.get_tag("tx_201")
    assert exchange_tag is not None
    assert exchange_tag["category"] == "exchange"
