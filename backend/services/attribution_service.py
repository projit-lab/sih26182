import logging
import math
import time
from typing import Dict, List, Optional
import networkx as nx

from backend.config import MAX_SUBGRAPH_NODES
from backend.database.repositories import CaseRepository, EntityTagRepository
from backend.ingestion.extractor import SubgraphExtractor
from backend.ingestion.obfuscation_detector import analyze_obfuscation
from backend.models.attribution import (
    GraphSummary,
    InvestigateRequest,
    InvestigateResponse,
    RankedVaspItem,
)
from src.attribution.engine import AttributionEngine
from src.attribution.weights import _log_scale_weights
from src.api.main import load_case

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
        heuristic_applied = False
        
        obfuscation_report_dict = None
        data_source = "live/cached crawl"
        
        if req.case_id == "silkroad":
            case = load_case("silkroad")
            graph = case["graph"]
            # Verified case datasets already contain log1p-scaled edges.json from E1.
            candidate_pool = list(case["candidate_vasps"].keys())
            candidates_in_graph = [c for c in candidate_pool if c in graph.nodes]
            metadata = {c: {"entity": case["candidate_vasps"].get(c, c)} for c in candidates_in_graph}
            is_truncated = case.get("truncated", False)
            req.suspect_address = case["suspect"]
            data_source = "verified silkroad dataset"
            cached_degree_correction = case.get("degree_correction", False)
            cached_null_test_runs = case.get("null_test_runs", [])
        else:
            # 1. Extract k-hop neighborhood graph
            graph, discovered_vasps, metadata, is_truncated = self.extractor.extract_subgraph(
                suspect_address=req.suspect_address,
                max_depth=req.depth_limit,
                chain=req.chain,
            )
            
            if graph.number_of_nodes() <= 1:
                raise ValueError(
                    f"Suspect wallet '{req.suspect_address}' has no transaction history in the graph"
                )

            # 1b. Run obfuscation analysis on the extracted subgraph
            known_vasps_set = set(discovered_vasps)
            obfuscation_report = analyze_obfuscation(
                graph, req.suspect_address, known_vasps_set, self.tag_repo, chain=req.chain
            )
            obfuscation_report_dict = obfuscation_report.to_dict()

            # Promote detected nested exchanges to candidate VASP pool
            for ne in obfuscation_report.nested_exchanges:
                if ne.address not in discovered_vasps:
                    discovered_vasps.append(ne.address)
                    metadata[ne.address] = {
                        "role": "nested_exchange",
                        "entity": ne.suggested_tag,
                        "category": "nested_exchange",
                        "label": ne.suggested_tag,
                        "parent_vasp": ne.parent_name,
                        "funnel_ratio": ne.funnel_ratio,
                    }
                    logger.info(f"Promoted nested exchange {ne.address} to candidate pool (via {ne.parent_name})")

            # 2. Determine candidate VASPs
            candidate_pool = req.candidate_vasps or discovered_vasps

            # If still no candidates found in k-hop, try checking all known VASPs in tag repository
            if not candidate_pool:
                all_known = self.tag_repo.list_all_vasp_addresses()
                candidate_pool = [v for v in all_known if v in graph.nodes and v != req.suspect_address]

            # P2P/OTC fallback: if no tagged exchange found, use detected P2P sinks
            if not candidate_pool and obfuscation_report.p2p_sinks:
                candidate_pool = [s.address for s in obfuscation_report.p2p_sinks]
                for s in obfuscation_report.p2p_sinks:
                    metadata[s.address] = {
                        "role": "suspected_p2p",
                        "entity": s.suggested_tag,
                        "category": "p2p_otc",
                        "label": s.suggested_tag,
                        "volume_btc": s.total_volume_btc,
                    }
                logger.info(f"Using {len(candidate_pool)} P2P sink(s) as fallback candidates")

            # Generic fallback: top-volume recipient nodes in connected component
            if not candidate_pool:
                heuristic_applied = True
                if nx.is_connected(graph):
                    reachable_nodes = set(graph.nodes)
                else:
                    reachable_nodes = nx.node_connected_component(graph, req.suspect_address)

                non_suspect_nodes = [n for n in reachable_nodes if n != req.suspect_address]
                candidate_pool = sorted(
                    non_suspect_nodes,
                    key=lambda n: graph.degree(n, weight="weight"),
                    reverse=True,
                )[:5]

            if not candidate_pool:
                raise ValueError(
                    f"No connected peer or candidate VASP addresses reachable within {req.depth_limit} hops from suspect wallet."
                )

            # Filter candidates to only those present in graph
            candidates_in_graph = [c for c in candidate_pool if c in graph.nodes]
            if not candidates_in_graph:
                raise ValueError(
                    "None of the candidate VASP addresses were found in the extracted neighborhood graph."
                )
            
            # Apply _log_scale_weights (from E1) using amount_satoshis
            logger.info("Applying log1p scaling to edge weights using field 'amount_satoshis'")
            graph = _log_scale_weights(graph)

        # 3. Null test
        degree_corrected = False
        null_test_result = None

        if req.case_id == "silkroad":
            degree_corrected = cached_degree_correction
            null_test_result = cached_null_test_runs
            engine = AttributionEngine(graph, weight_attr="weight", degree_correction=degree_corrected)
        else:
            engine = AttributionEngine(graph, weight_attr="weight", degree_correction=False)
            if graph.number_of_nodes() < 20:
                null_test_result = {"note": "Graph too small (<20 nodes) for null test"}
            else:
                exclude = {req.suspect_address, *candidates_in_graph}
                null_test_result = engine.null_test(candidates_in_graph, exclude=exclude, n=40, seed=0)
                if null_test_result.get("likely_needs_degree_correction"):
                    degree_corrected = True
                    engine = AttributionEngine(graph, weight_attr="weight", degree_correction=True)

        attr_result = engine.attribute(req.suspect_address, candidates_in_graph)
        compute_ms = round((time.perf_counter() - t0) * 1000, 2)

        ranked_items: List[RankedVaspItem] = []
        for c in attr_result.ranked_candidates:
            score_val = attr_result.scores[c]
            raw_r_eff = attr_result.raw_resistance[c]

            # Get entity name from metadata or repository
            node_meta = metadata.get(c, {})
            tag = self.tag_repo.get_tag(c)
            entity_name = node_meta.get("entity") or (tag["entity_name"] if tag else c)
            
            if heuristic_applied:
                entity_name = f"[HEURISTIC] Top Degree Hub: {entity_name}"

            ranked_items.append(
                RankedVaspItem(
                    vasp_name=entity_name,
                    candidate_address=c,
                    effective_resistance=raw_r_eff,
                    raw_effective_resistance=raw_r_eff,
                    score=score_val,
                    confidence_score=None,
                )
            )

        unreachable_vasps = []
        for c in attr_result.unreachable:
            node_meta = metadata.get(c, {})
            tag = self.tag_repo.get_tag(c)
            entity_name = node_meta.get("entity") or (tag["entity_name"] if tag else c)
            unreachable_vasps.append({"vasp_name": entity_name, "candidate_address": c})

        components = list(nx.connected_components(graph))
        n_components = len(components)
        suspect_component_size = len(nx.node_connected_component(graph, req.suspect_address)) if req.suspect_address in graph else 0

        graph_summary = GraphSummary(
            nodes_analyzed=graph.number_of_nodes(),
            edges_analyzed=graph.number_of_edges(),
            compute_time_ms=compute_ms,
            solver_method=attr_result.method,
            truncated=is_truncated,
            n_components=n_components,
            suspect_component_size=suspect_component_size,
        )

        # 5. Persist case for audit & report export
        case_id = req.case_id or f"CASE-{req.suspect_address[:8].upper()}-{int(time.time())}"
        top_vasp = ranked_items[0].vasp_name if ranked_items else "Unknown"
        sep_ratio = attr_result.separation_ratio or 0.0

        response = InvestigateResponse(
            case_id=case_id,
            suspect_address=req.suspect_address,
            ranked_vasps=ranked_items,
            graph_summary=graph_summary,
            obfuscation_report=obfuscation_report_dict,
            separation_ratio=attr_result.separation_ratio,
            degree_corrected=degree_corrected,
            null_test=null_test_result,
            unreachable_vasps=unreachable_vasps,
            data_source=data_source,
        )

        # case_repo.save_case requires confidence but it's NOT NULL in DB, so we store separation_ratio or 0.0
        self.case_repo.save_case(
            case_id=case_id,
            suspect_address=req.suspect_address,
            top_vasp=top_vasp,
            confidence=sep_ratio,
            results_data=response.model_dump(),
        )

        return response
