import logging
import math
import time
from typing import Dict, List, Optional
import networkx as nx

from backend.database.repositories import CaseRepository, EntityTagRepository
from backend.ingestion.extractor import SubgraphExtractor
from backend.models.attribution import (
    GraphSummary,
    InvestigateRequest,
    InvestigateResponse,
    RankedVaspItem,
)
from src.attribution.engine import AttributionEngine

logger = logging.getLogger(__name__)


class AttributionService:
    """
    Orchestrates:
    1. Subgraph extraction around suspect wallet
    2. Candidate VASP identification
    3. Core Laplacian Solver execution (AttributionEngine: Lx = b)
    4. Inverse-resistance confidence score normalization
    5. Case persistence for audit & PDF reporting
    """

    def __init__(
        self,
        extractor: Optional[SubgraphExtractor] = None,
        tag_repo: Optional[EntityTagRepository] = None,
        case_repo: Optional[CaseRepository] = None,
    ):
        self.extractor = extractor or SubgraphExtractor()
        self.tag_repo = tag_repo or EntityTagRepository()
        self.case_repo = case_repo or CaseRepository()

    def investigate(self, req: InvestigateRequest) -> InvestigateResponse:
        t0 = time.perf_counter()

        # 1. Extract k-hop neighborhood graph
        graph, discovered_vasps, metadata = self.extractor.extract_subgraph(
            suspect_address=req.suspect_address,
            max_depth=req.depth_limit,
            chain=req.chain,
        )

        if graph.number_of_nodes() <= 1:
            raise ValueError(
                f"Suspect wallet '{req.suspect_address}' has no transaction history in the graph"
            )

        # 2. Determine candidate VASPs
        candidate_pool = req.candidate_vasps or discovered_vasps

        # If still no candidates found in k-hop, try checking all known VASPs in tag repository
        if not candidate_pool:
            all_known = self.tag_repo.list_all_vasp_addresses()
            candidate_pool = [v for v in all_known if v in graph.nodes and v != req.suspect_address]

        if not candidate_pool:
            raise ValueError(
                f"No candidate VASP addresses reachable within {req.depth_limit} hops from suspect wallet."
            )

        # Filter candidates to only those present in graph
        candidates_in_graph = [c for c in candidate_pool if c in graph.nodes]
        if not candidates_in_graph:
            raise ValueError(
                "None of the candidate VASP addresses were found in the extracted neighborhood graph."
            )

        # 3. Execute Laplacian Solver (AttributionEngine)
        engine = AttributionEngine(graph, weight_attr="weight")
        attr_result = engine.attribute(req.suspect_address, candidates_in_graph)

        compute_ms = round((time.perf_counter() - t0) * 1000, 2)

        # 4. Normalize effective resistance scores into confidence probabilities
        # Lower resistance = higher confidence
        finite_candidates = [
            c for c in attr_result.ranked_candidates if not math.isinf(attr_result.scores[c])
        ]

        inverse_weights: Dict[str, float] = {}
        for c in finite_candidates:
            r_eff = attr_result.scores[c]
            # Avoid division by zero
            inverse_weights[c] = 1.0 / (r_eff + 1e-6)

        total_weight = sum(inverse_weights.values()) or 1.0

        ranked_items: List[RankedVaspItem] = []
        for c in attr_result.ranked_candidates:
            r_eff = attr_result.scores[c]
            if math.isinf(r_eff):
                conf = 0.0
            else:
                conf = round(inverse_weights[c] / total_weight, 3)

            # Get entity name from metadata or repository
            node_meta = metadata.get(c, {})
            tag = self.tag_repo.get_tag(c)
            entity_name = node_meta.get("entity") or (tag["entity_name"] if tag else c)

            eff_res_val = round(r_eff, 4) if r_eff >= 0.0001 else round(r_eff, 8)
            ranked_items.append(
                RankedVaspItem(
                    vasp_name=entity_name,
                    candidate_address=c,
                    effective_resistance=eff_res_val,
                    confidence_score=conf,
                )
            )

        graph_summary = GraphSummary(
            nodes_analyzed=graph.number_of_nodes(),
            edges_analyzed=graph.number_of_edges(),
            compute_time_ms=compute_ms,
            solver_method=attr_result.method,
        )

        response = InvestigateResponse(
            suspect_address=req.suspect_address,
            ranked_vasps=ranked_items,
            graph_summary=graph_summary,
        )

        # 5. Persist case for audit & report export
        case_id = f"CASE-{req.suspect_address[:8].upper()}-{int(time.time())}"
        top_vasp = ranked_items[0].vasp_name if ranked_items else "Unknown"
        top_conf = ranked_items[0].confidence_score if ranked_items else 0.0
        self.case_repo.save_case(
            case_id=case_id,
            suspect_address=req.suspect_address,
            top_vasp=top_vasp,
            confidence=top_conf,
            results_data=response.model_dump(),
        )

        return response
