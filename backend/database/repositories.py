import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from backend.database.db import get_db_connection

logger = logging.getLogger(__name__)


class EntityTagRepository:
    def __init__(self, db=None):
        self.db = db or get_db_connection()

    def upsert_tag(
        self,
        address: str,
        entity_name: str,
        category: str,
        chain: str = "BTC",
        source: str = "GraphSense",
        confidence: float = 1.0,
    ):
        query = """
            INSERT OR REPLACE INTO entity_tags (address, entity_name, category, chain, source, confidence, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        self.db.execute(query, (address, entity_name, category, chain, source, confidence))
        self.db.commit()

    def bulk_insert_tags(self, tags: List[tuple]):
        if not tags:
            return
        query = """
            INSERT OR REPLACE INTO entity_tags (address, entity_name, category, chain, source, confidence, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        self.db.executemany(query, tags)
        self.db.commit()

    def get_tag(self, address: str) -> Optional[Dict[str, Any]]:
        row = self.db.fetchone("SELECT * FROM entity_tags WHERE address = ?", (address,))
        if row:
            return {
                "address": row[0],
                "entity_name": row[1],
                "category": row[2],
                "chain": row[3],
                "source": row[4],
                "confidence": row[5],
            }
        return None

    def get_vasp_candidates_for_addresses(self, addresses: List[str]) -> List[Dict[str, Any]]:
        if not addresses:
            return []
        placeholders = ",".join(["?"] * len(addresses))
        query = f"""
            SELECT address, entity_name, category, confidence 
            FROM entity_tags 
            WHERE address IN ({placeholders}) AND category IN ('exchange', 'custodial', 'vasp')
        """
        rows = self.db.fetchall(query, tuple(addresses))
        return [
            {
                "address": r[0],
                "entity_name": r[1],
                "category": r[2],
                "confidence": r[3],
            }
            for r in rows
        ]

    def list_all_vasp_addresses(self) -> List[str]:
        rows = self.db.fetchall(
            "SELECT address FROM entity_tags WHERE category IN ('exchange', 'custodial', 'vasp')"
        )
        return [r[0] for r in rows]


class TransactionEdgeRepository:
    def __init__(self, db=None):
        self.db = db or get_db_connection()

    def insert_edges(self, edges: List[tuple]):
        if not edges:
            return
        query = """
            INSERT OR IGNORE INTO transaction_edges 
            (tx_hash, source_address, target_address, amount_satoshis, timestamp, chain, is_coinbase)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        self.db.executemany(query, edges)
        self.db.commit()

    def get_outgoing_edges(self, source_address: str) -> List[Dict[str, Any]]:
        query = """
            SELECT tx_hash, source_address, target_address, amount_satoshis, timestamp 
            FROM transaction_edges 
            WHERE source_address = ?
        """
        rows = self.db.fetchall(query, (source_address,))
        return [
            {
                "tx_hash": r[0],
                "source_address": r[1],
                "target_address": r[2],
                "amount_satoshis": r[3],
                "timestamp": r[4],
            }
            for r in rows
        ]

    def has_address_transactions(self, address: str) -> bool:
        row = self.db.fetchone(
            "SELECT 1 FROM transaction_edges WHERE source_address = ? OR target_address = ? LIMIT 1",
            (address, address),
        )
        return row is not None


class SahyogRepository:
    def __init__(self, db=None):
        self.db = db or get_db_connection()

    def create_dispatch(
        self,
        ack_token: str,
        case_id: str,
        suspect_address: str,
        target_vasp: str,
        action: str,
        officer_name: str,
        jurisdiction: str,
        law_section: str,
        dispatch_hash: str,
        status: str = "SUBMITTED",
    ):
        query = """
            INSERT INTO sahyog_dispatches 
            (ack_token, case_id, suspect_address, target_vasp, action, officer_name, jurisdiction, law_section, dispatch_hash, status, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        self.db.execute(
            query,
            (
                ack_token,
                case_id,
                suspect_address,
                target_vasp,
                action,
                officer_name,
                jurisdiction,
                law_section,
                dispatch_hash,
                status,
            ),
        )
        self.db.commit()

    def get_dispatch(self, ack_token: str) -> Optional[Dict[str, Any]]:
        row = self.db.fetchone("SELECT * FROM sahyog_dispatches WHERE ack_token = ?", (ack_token,))
        if row:
            return {
                "ack_token": row[0],
                "case_id": row[1],
                "suspect_address": row[2],
                "target_vasp": row[3],
                "action": row[4],
                "officer_name": row[5],
                "jurisdiction": row[6],
                "law_section": row[7],
                "dispatch_hash": row[8],
                "status": row[9],
                "timestamp": str(row[10]),
            }
        return None


class CaseRepository:
    def __init__(self, db=None):
        self.db = db or get_db_connection()

    def save_case(self, case_id: str, suspect_address: str, top_vasp: str, confidence: float, results_data: dict):
        query = """
            INSERT OR REPLACE INTO investigation_cases (case_id, suspect_address, top_vasp, confidence, results_json, created_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        self.db.execute(query, (case_id, suspect_address, top_vasp, confidence, json.dumps(results_data)))
        self.db.commit()

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        row = self.db.fetchone("SELECT * FROM investigation_cases WHERE case_id = ?", (case_id,))
        if row:
            return {
                "case_id": row[0],
                "suspect_address": row[1],
                "top_vasp": row[2],
                "confidence": row[3],
                "results": json.loads(row[4]),
                "created_at": str(row[5]),
            }
        return None
