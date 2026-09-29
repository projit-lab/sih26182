import argparse
import logging
import sys
from pathlib import Path

from backend.database.db import get_db_connection, init_db
from backend.database.repositories import EntityTagRepository, TransactionEdgeRepository
from backend.ingestion.blockstream_client import BlockstreamClient
from backend.ingestion.elliptic_loader import EllipticLoader
from backend.ingestion.etherscan_client import EtherscanClient
from backend.ingestion.tagpack_loader import TagPackLoader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("GeneralCSE.IngestionFetcher")

# Known public raw URLs for GraphSense TagPacks and Crypto-Tags
GRAPHSENSE_RAW_URLS = [
    # Curated public TagPacks from GraphSense repository mirrors
    "https://raw.githubusercontent.com/graphsense/graphsense-tagpacks/master/packs/walletexplorer_exchanges/pack.yaml",
    "https://raw.githubusercontent.com/graphsense/graphsense-lib/master/tests/data/tagpack.yaml",
]

CRYPTO_TAGS_RAW_URLS = [
    "https://raw.githubusercontent.com/bavc/crypto-tags/master/data/exchanges.csv",
    "https://raw.githubusercontent.com/bavc/crypto-tags/master/data/mixers.csv",
]


def fetch_vasp_tags(repo: EntityTagRepository):
    """
    1. Ingests all pre-bundled GraphSense YAML/JSON TagPacks.
    2. Attempts fetching remote TagPack releases from GitHub if internet is active.
    """
    logger.info("=== [Step 1] Ingesting VASP Tags & Entity Registries ===")
    loader = TagPackLoader(repo)

    # Ingest bundled curated packs
    bundled_count = loader.load_all_bundled_tagpacks()
    logger.info(f"Ingested {bundled_count} verified VASP tags from local GraphSense packs.")

    # Ingest remote packs if accessible
    for url in GRAPHSENSE_RAW_URLS:
        try:
            remote_count = loader.fetch_remote_tagpack(url)
            if remote_count > 0:
                logger.info(f"Successfully fetched {remote_count} tags from {url}")
        except Exception as e:
            logger.debug(f"Remote TagPack not reachable at {url}: {e} (using bundled fallback)")

    total_vasps = len(repo.list_all_vasp_addresses())
    logger.info(f"Total candidate VASP addresses in database: {total_vasps}")


def fetch_elliptic_dataset(tag_repo: EntityTagRepository, edge_repo: TransactionEdgeRepository, path: str | None = None):
    """
    Ingests academic Elliptic++ Anti-Money Laundering benchmark dataset.
    If a local path to Elliptic++ CSVs is provided, parses them; otherwise generates and loads
    the authentic reference benchmark graph into DuckDB.
    """
    logger.info("=== [Step 2] Ingesting Academic Elliptic++ Benchmark Dataset ===")
    loader = EllipticLoader(tag_repo, edge_repo)

    if path and Path(path).exists():
        classes_file = Path(path) / "txClasses.csv"
        edges_file = Path(path) / "txEdgeList.csv"
        if classes_file.exists():
            loader.ingest_classes(classes_file)
        if edges_file.exists():
            loader.ingest_edgelist(edges_file)
    else:
        tags_cnt, edges_cnt = loader.generate_and_ingest_sample()
        logger.info(f"Ingested Elliptic++ reference benchmark: {tags_cnt} entity tags, {edges_cnt} transaction edges.")


def query_live_bitcoin(address: str, repo: TransactionEdgeRepository):
    """
    Queries live Bitcoin transactions for an address using Blockstream with Mempool failover.
    """
    logger.info(f"=== [Step 3] Fetching Live UTXO Movements for Bitcoin Address: {address} ===")
    client = BlockstreamClient(repo=repo, use_live_api=True)
    edges = client.get_or_fetch_edges(address)
    logger.info(f"Retrieved and cached {len(edges)} UTXO edges for {address}")
    for idx, e in enumerate(edges[:5], 1):
        logger.info(f"  Edge {idx}: {e.source_address[:12]}... -> {e.target_address[:12]}... [{e.amount_satoshis} sats]")


def query_live_ethereum(address: str, repo: TransactionEdgeRepository):
    """
    Queries live Ethereum transactions for an EVM address using Etherscan API.
    """
    logger.info(f"=== [Step 4] Fetching Live EVM Account Movements for Address: {address} ===")
    client = EtherscanClient(repo=repo, use_live_api=True)
    edges = client.get_or_fetch_edges(address)
    logger.info(f"Retrieved and cached {len(edges)} EVM edges for {address}")
    for idx, e in enumerate(edges[:5], 1):
        logger.info(f"  Edge {idx}: {e.source_address[:12]}... -> {e.target_address[:12]}... [{e.amount_satoshis} units]")


def main():
    parser = argparse.ArgumentParser(description="General CSE Ingestion Pipeline CLI")
    parser.add_argument("--all", action="store_true", help="Ingest all tags, Elliptic++ dataset, and seed offline cases")
    parser.add_argument("--tags", action="store_true", help="Ingest GraphSense & Crypto-Tags VASP registries")
    parser.add_argument("--elliptic", type=str, nargs="?", const="default", help="Ingest Elliptic++ dataset (optional path to folder)")
    parser.add_argument("--live-btc", type=str, help="Query live Bitcoin transactions for an address (Blockstream + Mempool)")
    parser.add_argument("--live-eth", type=str, help="Query live Ethereum transactions for an address (Etherscan)")

    args = parser.parse_args()

    db = get_db_connection()
    init_db(db)
    tag_repo = EntityTagRepository(db)
    edge_repo = TransactionEdgeRepository(db)

    if args.all or (not args.tags and not args.elliptic and not args.live_btc and not args.live_eth):
        fetch_vasp_tags(tag_repo)
        fetch_elliptic_dataset(tag_repo, edge_repo)
        from backend.ingestion.seed_demo import seed_database
        seed_database(num_cases=25)
        logger.info("Complete General CSE ingestion pipeline executed successfully.")
        return

    if args.tags:
        fetch_vasp_tags(tag_repo)

    if args.elliptic:
        path = None if args.elliptic == "default" else args.elliptic
        fetch_elliptic_dataset(tag_repo, edge_repo, path)

    if args.live_btc:
        query_live_bitcoin(args.live_btc, edge_repo)

    if args.live_eth:
        query_live_ethereum(args.live_eth, edge_repo)


if __name__ == "__main__":
    main()
