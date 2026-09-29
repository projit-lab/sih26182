import os
from pathlib import Path
from backend.database.db import DatabaseConnection, init_db
from backend.database.repositories import EntityTagRepository, TransactionEdgeRepository, SahyogRepository, CaseRepository


def test_database_initialization(tmp_path):
    test_db_path = tmp_path / "test.sqlite"
    db = DatabaseConnection(db_path=test_db_path, use_duckdb=False)
    init_db(db)

    tag_repo = EntityTagRepository(db)
    tag_repo.upsert_tag("1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s", "Binance", "exchange")

    tag = tag_repo.get_tag("1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s")
    assert tag is not None
    assert tag["entity_name"] == "Binance"
    assert tag["category"] == "exchange"

    edge_repo = TransactionEdgeRepository(db)
    edge_repo.insert_edges([
        ("tx123", "src1", "dst1", 1000000, None, "BTC", False)
    ])
    assert edge_repo.has_address_transactions("src1")
    assert edge_repo.has_address_transactions("dst1")

    sahyog_repo = SahyogRepository(db)
    sahyog_repo.create_dispatch(
        ack_token="SAHYOG-TEST-001",
        case_id="CASE-001",
        suspect_address="src1",
        target_vasp="Binance",
        action="FREEZE_REQUEST",
        officer_name="Officer Test",
        jurisdiction="Cyber Cell",
        law_section="Section 91 CrPC",
        dispatch_hash="hash123",
    )
    dispatch = sahyog_repo.get_dispatch("SAHYOG-TEST-001")
    assert dispatch is not None
    assert dispatch["case_id"] == "CASE-001"
    assert dispatch["status"] == "SUBMITTED"

    case_repo = CaseRepository(db)
    case_repo.save_case("CASE-001", "src1", "Binance", 0.95, {"key": "val"})
    case = case_repo.get_case("CASE-001")
    assert case is not None
    assert case["top_vasp"] == "Binance"
    assert case["confidence"] == 0.95
