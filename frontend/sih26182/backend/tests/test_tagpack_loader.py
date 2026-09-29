from backend.database.db import DatabaseConnection, init_db
from backend.database.repositories import EntityTagRepository
from backend.ingestion.tagpack_loader import TagPackLoader


def test_tagpack_loader_bundled(tmp_path):
    test_db_path = tmp_path / "test_tagpack.sqlite"
    db = DatabaseConnection(db_path=test_db_path, use_duckdb=False)
    init_db(db)
    repo = EntityTagRepository(db)

    loader = TagPackLoader(repo=repo)
    total_loaded = loader.load_all_bundled_tagpacks()
    assert total_loaded > 0

    # Verify Binance address is present
    binance_tag = repo.get_tag("1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s")
    assert binance_tag is not None
    assert binance_tag["entity_name"] == "Binance"
    assert binance_tag["category"] == "exchange"

    # Verify invalid address sanitization
    invalid_record = {"address": "not_an_address!!", "entity_name": "Bad", "category": "exchange"}
    sanitized = loader.sanitize_and_validate(invalid_record)
    assert sanitized is None
