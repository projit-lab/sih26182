import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests

from backend.database.repositories import EntityTagRepository
from backend.models.common import validate_crypto_address

logger = logging.getLogger(__name__)

TAGPACKS_DIR = Path(__file__).resolve().parent / "tagpacks"

# Check for PyYAML
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    logger.warning("PyYAML not installed. Using built-in lightweight YAML reader for TagPacks.")


def parse_simple_yaml(text: str) -> List[dict]:
    """
    Fallback parser for standard GraphSense YAML tagpacks when PyYAML is unavailable.
    Extracts tags containing address, label/entity, and category.
    """
    tags = []
    current_tag: Dict[str, Any] = {}
    in_tags_section = False

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("tags:"):
            in_tags_section = True
            continue

        if in_tags_section:
            if line.startswith("- address:") or line.startswith("address:"):
                if current_tag and "address" in current_tag:
                    tags.append(current_tag)
                    current_tag = {}
                parts = line.split(":", 1)
                current_tag["address"] = parts[1].strip().strip("'\"")
            elif ":" in line and current_tag:
                k, v = line.split(":", 1)
                k = k.strip().lstrip("- ").strip()
                v = v.strip().strip("'\"")
                current_tag[k] = v

    if current_tag and "address" in current_tag:
        tags.append(current_tag)

    return tags


class TagPackLoader:
    """
    Parses, validates, and ingests GraphSense TagPacks and Crypto-Tags registries
    into DuckDB/SQLite. Supports JSON, YAML, and CSV formats both locally and via remote URLs.
    """

    def __init__(self, repo: Optional[EntityTagRepository] = None):
        self.repo = repo or EntityTagRepository()

    def sanitize_and_validate(self, record: dict) -> Optional[tuple]:
        raw_addr = str(record.get("address", "")).strip()
        if not raw_addr:
            return None

        # Validate address format (BTC Base58/Bech32, EVM 0x..., or synthetic)
        try:
            addr = validate_crypto_address(raw_addr)
        except ValueError as e:
            logger.debug(f"Skipping invalid address in tagpack: {raw_addr} ({e})")
            return None

        entity_name = str(
            record.get("entity_name")
            or record.get("label")
            or record.get("entity")
            or "Unknown Entity"
        ).strip()

        raw_cat = str(record.get("category", "exchange")).strip().lower()
        if any(w in raw_cat for w in ("exchange", "custodial", "deposit", "hot_wallet", "service")):
            category = "exchange"
        elif any(w in raw_cat for w in ("mixer", "tumbler", "coinjoin", "anonymity")):
            category = "mixer"
        elif "illicit" in raw_cat or "scam" in raw_cat:
            category = "illicit"
        else:
            category = raw_cat

        chain = str(record.get("chain", record.get("currency", "BTC"))).strip().upper()
        source = str(record.get("source", "GraphSense")).strip()
        confidence = float(record.get("confidence", 1.0))

        return (addr, entity_name, category, chain, source, confidence)

    def load_from_text(self, content: str, filename: str = "data.json") -> int:
        records: List[dict] = []
        if filename.endswith((".yaml", ".yml")):
            if HAS_YAML:
                parsed = yaml.safe_load(content)
                if isinstance(parsed, dict) and "tags" in parsed:
                    records = parsed["tags"]
                elif isinstance(parsed, list):
                    records = parsed
            else:
                records = parse_simple_yaml(content)
        elif filename.endswith(".csv"):
            lines = content.strip().splitlines()
            if lines:
                headers = [h.strip().lower() for h in lines[0].split(",")]
                for line in lines[1:]:
                    vals = [v.strip().strip("'\"") for v in line.split(",")]
                    if len(vals) == len(headers):
                        records.append(dict(zip(headers, vals)))
        else:
            # Default JSON
            try:
                parsed = json.loads(content)
                records = parsed if isinstance(parsed, list) else parsed.get("tags", [])
            except Exception as e:
                logger.error(f"Error parsing JSON tagpack: {e}")

        valid_tuples = []
        for r in records:
            item = self.sanitize_and_validate(r)
            if item:
                valid_tuples.append(item)

        if valid_tuples:
            self.repo.bulk_insert_tags(valid_tuples)
            logger.info(f"Ingested {len(valid_tuples)} tags from {filename}")

        return len(valid_tuples)

    def load_from_file(self, file_path: Path) -> int:
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return 0
        with open(file_path, "r", encoding="utf-8") as f:
            return self.load_from_text(f.read(), filename=file_path.name)

    def fetch_remote_tagpack(self, url: str) -> int:
        """
        Directly fetches raw TagPack from remote URL (e.g. GitHub raw)
        and ingests into local DuckDB storage.
        """
        logger.info(f"Fetching remote tagpack from {url}...")
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                filename = url.split("/")[-1] or "tagpack.json"
                return self.load_from_text(resp.text, filename=filename)
            else:
                logger.warning(f"Remote tagpack fetch failed with HTTP {resp.status_code}")
                return 0
        except Exception as e:
            logger.error(f"Error fetching remote tagpack from {url}: {e}")
            return 0

    def load_all_bundled_tagpacks(self) -> int:
        total = 0
        if not TAGPACKS_DIR.exists():
            return 0

        for f in TAGPACKS_DIR.glob("*.*"):
            if f.suffix in (".json", ".yaml", ".yml", ".csv"):
                total += self.load_from_file(f)
        return total
