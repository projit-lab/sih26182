from backend.database.db import DatabaseConnection, init_db
from backend.database.repositories import EntityTagRepository, TransactionEdgeRepository
from backend.ingestion.extractor import SubgraphExtractor


def test_extractor_khop_and_vasp_isolation(tmp_path):
    test_db_path = tmp_path / "test_extractor.sqlite"
    db = DatabaseConnection(db_path=test_db_path, use_duckdb=False)
    init_db(db)

    tag_repo = EntityTagRepository(db)
    edge_repo = TransactionEdgeRepository(db)

    # Setup tags
    tag_repo.upsert_tag("VASP_target", "Target Exchange", "exchange")

    # Setup edges: suspect -> hop1 -> VASP_target
    edge_repo.insert_edges([
        ("tx1", "suspect_001", "hop1", 1000000, None, "BTC", False),
        ("tx2", "hop1", "VASP_target", 950000, None, "BTC", False),
        # Past VASP_target: should be pruned
        ("tx3", "VASP_target", "beyond_node", 500000, None, "BTC", False),
    ])

    extractor = SubgraphExtractor(db=db, tag_repo=tag_repo, edge_repo=edge_repo)
    graph, candidates, metadata = extractor.extract_subgraph("suspect_001", max_depth=3)

    assert "suspect_001" in graph.nodes
    assert "hop1" in graph.nodes
    assert "VASP_target" in graph.nodes
    # beyond_node must be pruned because traversal stops at VASP boundaries
    assert "beyond_node" not in graph.nodes
    assert "VASP_target" in candidates
