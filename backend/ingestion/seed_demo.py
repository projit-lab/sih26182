import hashlib
import logging
import random
from datetime import datetime, timedelta
from pathlib import Path

from backend.database.db import get_db_connection, init_db
from backend.database.repositories import EntityTagRepository, TransactionEdgeRepository
from backend.ingestion.elliptic_loader import EllipticLoader
from backend.ingestion.tagpack_loader import TagPackLoader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_fake_tx_hash(src: str, dst: str, nonce: int) -> str:
    raw = f"{src}->{dst}:{nonce}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def seed_database(num_cases: int = 25):
    """
    Seeds DuckDB/SQLite with:
    1. Pre-bundled GraphSense TagPacks (YAML + JSON)
    2. Academic Elliptic++ Benchmark Data
    3. 25 offline laundering test scenarios
    """
    db = get_db_connection()
    init_db(db)

    tag_repo = EntityTagRepository(db)
    edge_repo = TransactionEdgeRepository(db)

    # 1. Load TagPacks (GraphSense & Crypto-Tags)
    loader = TagPackLoader(tag_repo)
    loaded_tags = loader.load_all_bundled_tagpacks()
    logger.info(f"Step 1: Ingested {loaded_tags} entity tags from GraphSense TagPacks.")

    # 2. Ingest Elliptic++ Benchmark Sample
    elliptic_loader = EllipticLoader(tag_repo, edge_repo)
    el_tags, el_edges = elliptic_loader.generate_and_ingest_sample()
    logger.info(f"Step 2: Ingested Elliptic++ benchmark: {el_tags} tags, {el_edges} edges.")

    # 3. Generate 25 Laundering Test Scenarios
    edges_to_insert = []
    rng = random.Random(42)
    base_time = datetime(2026, 9, 1, 10, 0, 0)

    vasp_list = [
        ("1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s", "Binance"),
        ("34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo", "Binance"),
        ("1AnwDVbwsLB4om3PnZ54FjWc1m8qP2XbVq", "WazirX"),
        ("3M219KR5vEneNb47ewrPfWyb5jJB26FD2K", "WazirX"),
        ("1CoinDCXDepositWalletAlpha7782x9841", "CoinDCX"),
        ("3KrakenHotWalletDepositBeta992147xL", "Kraken"),
        ("1OKXHotWalletReserveDelta782914xKm", "OKX"),
        ("3HuobiGlobalCustodialVault88371xZ", "Huobi"),
    ]

    # Scenario 0: Frozen Contract demo case from ENGINE_CONTRACT.md
    edges_to_insert.extend([
        (
            generate_fake_tx_hash("suspect_042", "mixer_hop_1", 1),
            "suspect_042",
            "mixer_hop_1",
            140000000,
            base_time,
            "BTC",
            False,
        ),
        (
            generate_fake_tx_hash("mixer_hop_1", "VASP_true", 2),
            "mixer_hop_1",
            "VASP_true",
            210000000,
            base_time + timedelta(minutes=10),
            "BTC",
            False,
        ),
        (
            generate_fake_tx_hash("suspect_042", "decoy_hop_1", 3),
            "suspect_042",
            "decoy_hop_1",
            5000000,
            base_time + timedelta(minutes=2),
            "BTC",
            False,
        ),
        (
            generate_fake_tx_hash("decoy_hop_1", "VASP_decoy", 4),
            "decoy_hop_1",
            "VASP_decoy",
            5000000,
            base_time + timedelta(minutes=15),
            "BTC",
            False,
        ),
    ])

    # Scenario 1: Famous BTC Genesis / Demo Suspect Case
    genesis_suspect = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
    true_target = "1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s"
    decoy_target = "1AnwDVbwsLB4om3PnZ54FjWc1m8qP2XbVq"

    for m_idx in range(6):
        mixer_node = f"mixer_node_alpha_{m_idx}"
        w_in = int(rng.uniform(10_000_000, 50_000_000))
        w_out = int(w_in * 0.98)
        edges_to_insert.append((
            generate_fake_tx_hash(genesis_suspect, mixer_node, m_idx),
            genesis_suspect,
            mixer_node,
            w_in,
            base_time + timedelta(hours=m_idx),
            "BTC",
            False,
        ))
        edges_to_insert.append((
            generate_fake_tx_hash(mixer_node, true_target, m_idx),
            mixer_node,
            true_target,
            w_out,
            base_time + timedelta(hours=m_idx, minutes=20),
            "BTC",
            False,
        ))

    edges_to_insert.append((
        generate_fake_tx_hash(genesis_suspect, "decoy_peel_hop", 99),
        genesis_suspect,
        "decoy_peel_hop",
        1_000_000,
        base_time,
        "BTC",
        False,
    ))
    edges_to_insert.append((
        generate_fake_tx_hash("decoy_peel_hop", decoy_target, 99),
        "decoy_peel_hop",
        decoy_target,
        1_000_000,
        base_time + timedelta(minutes=5),
        "BTC",
        False,
    ))

    # Scenarios 2 to num_cases: Generate synthesized laundering graphs
    for case_id in range(2, num_cases):
        suspect_id = f"suspect_{case_id:03d}"
        dest_vasp, _ = rng.choice(vasp_list)
        decoy_vasp, _ = rng.choice([v for v in vasp_list if v[0] != dest_vasp])

        is_mixer = (case_id % 2 == 0)
        if is_mixer:
            fanout = rng.randint(4, 7)
            for f in range(fanout):
                hop = f"mixer_hop_{case_id}_{f}"
                amt = rng.randint(5_000_000, 30_000_000)
                edges_to_insert.append((
                    generate_fake_tx_hash(suspect_id, hop, f),
                    suspect_id,
                    hop,
                    amt,
                    base_time + timedelta(minutes=case_id * 10 + f),
                    "BTC",
                    False,
                ))
                edges_to_insert.append((
                    generate_fake_tx_hash(hop, dest_vasp, f),
                    hop,
                    dest_vasp,
                    int(amt * 0.99),
                    base_time + timedelta(minutes=case_id * 10 + f + 5),
                    "BTC",
                    False,
                ))

            edges_to_insert.append((
                generate_fake_tx_hash(suspect_id, decoy_vasp, 77),
                suspect_id,
                decoy_vasp,
                500_000,
                base_time + timedelta(minutes=case_id * 10),
                "BTC",
                False,
            ))
        else:
            prev_node = suspect_id
            for p in range(3):
                next_node = f"peel_hop_{case_id}_{p}"
                edges_to_insert.append((
                    generate_fake_tx_hash(prev_node, next_node, p),
                    prev_node,
                    next_node,
                    rng.randint(20_000_000, 80_000_000),
                    base_time + timedelta(minutes=case_id * 10 + p * 5),
                    "BTC",
                    False,
                ))
                prev_node = next_node

            edges_to_insert.append((
                generate_fake_tx_hash(prev_node, dest_vasp, 99),
                prev_node,
                dest_vasp,
                rng.randint(20_000_000, 80_000_000),
                base_time + timedelta(minutes=case_id * 10 + 20),
                "BTC",
                False,
            ))

    edge_repo.insert_edges(edges_to_insert)
    logger.info(f"Step 3: Seeded {len(edges_to_insert)} transaction edges across {num_cases} scenarios.")
    logger.info("Ingestion pipeline fully seeded and 100% offline pitch ready.")


if __name__ == "__main__":
    seed_database()
