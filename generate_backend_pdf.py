#!/usr/bin/env python3
"""
CLI script to compile the complete Backend Implementation, Architecture, and Code Snippet Report into a PDF document.
Outputs: SIH26182_Backend_Implementation_Report.pdf
"""
import io
import sys
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import (
        HRFlowable,
        KeepTogether,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
    from reportlab.pdfgen import canvas
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False
    print("[!] ReportLab not installed. Please install with: pip install reportlab")


class NumberedCanvas(canvas.Canvas if HAS_REPORTLAB else object):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(36, 756, "SIH26182: Backend Architecture & Implementation Audit")
            self.drawRightString(576, 756, "Technical Reference Report")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(36, 750, 576, 750)

        # Footer
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(36, 42, 576, 42)

        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawString(36, 30, "CONFIDENTIAL — SIH26182 BACKEND IMPLEMENTATION AUDIT")
        self.drawRightString(576, 30, page_str)
        self.restoreState()


def build_backend_report_pdf(target_path: Path) -> str:
    if not HAS_REPORTLAB:
        raise RuntimeError("ReportLab is required to build this PDF report.")

    doc = SimpleDocTemplate(
        str(target_path),
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=48,
        bottomMargin=48,
    )

    styles = getSampleStyleSheet()
    primary = colors.HexColor("#0f172a")
    accent = colors.HexColor("#0284c7")
    border_color = colors.HexColor("#cbd5e1")

    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=primary,
    )
    subtitle_style = ParagraphStyle(
        "SubTitleStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14,
        textColor=accent,
    )
    h1_style = ParagraphStyle(
        "H1",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=primary,
        spaceBefore=14,
        spaceAfter=6,
    )
    h2_style = ParagraphStyle(
        "H2",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#0369a1"),
        spaceBefore=8,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11.5,
        textColor=colors.HexColor("#1e293b"),
    )
    code_style = ParagraphStyle(
        "CodeSnippet",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#0f172a"),
        backColor=colors.HexColor("#f1f5f9"),
        borderPadding=4,
        spaceBefore=3,
        spaceAfter=6,
    )
    th_style = ParagraphStyle(
        "TH",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=10,
        textColor=colors.white,
    )
    td_style = ParagraphStyle(
        "TD",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#1e293b"),
    )

    story = []

    # Title & Header
    story.append(Paragraph("TECHNICAL IMPLEMENTATION & FUNCTION AUDIT", subtitle_style))
    story.append(Paragraph("SIH26182: Backend Orchestration & Attribution Engine", title_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Comprehensive architectural guide, code snippets, and function input/output specifications "
        "covering multi-tier ingestion, bounded subgraph extraction, grounded Laplacian solver, and statutory notice dispatch.",
        body_style
    ))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1.5, color=accent, spaceAfter=8))

    # Meta Table
    meta_data = [
        [Paragraph("<b>System Layer:</b>", body_style), Paragraph("FastAPI Ingestion & Attribution", body_style),
         Paragraph("<b>Database:</b>", body_style), Paragraph("DuckDB + SQLite Fallback", body_style)],
        [Paragraph("<b>Core Math:</b>", body_style), Paragraph("Laplacian (Lx = b) via Sparse LU", body_style),
         Paragraph("<b>Date:</b>", body_style), Paragraph(datetime.utcnow().strftime("%B %d, %Y"), body_style)],
    ]
    meta_tab = Table(meta_data, colWidths=[90, 180, 90, 180])
    meta_tab.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 0.5, border_color),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(meta_tab)
    story.append(Spacer(1, 10))

    # 1. How the Backend Works
    story.append(Paragraph("1. How the Backend Works (Complete Architectural Flow)", h1_style))
    flow_text = (
        "<b>1. Request Validation:</b> Pydantic validates the cryptocurrency address (BTC Base58/Bech32, EVM 0x..., or synthetic IDs) at <code>POST /api/v1/investigate</code>.<br/>"
        "<b>2. Bounded Downstream Extraction:</b> <code>SubgraphExtractor</code> enforces 3 heuristic algorithms: (a) <i>Directional Temporal Filtering</i> ($t_{out} &ge; t_{in} - 2h$), "
        "(b) <i>High-Degree Super-Hub Pruning</i> (&ge; 45 edges), and (c) <i>Adaptive Volume Beam Search</i> (&ge; 85% volume threshold), halting at known VASP boundaries.<br/>"
        "<b>3. Multi-Tier Ingestion:</b> Bitcoin transactions are fetched via Mempool.space, Blockstream, and Blockchain.info with Proportional UTXO Haircut allocation. EVM transfers are fetched via Etherscan.<br/>"
        "<b>4. Grounded Laplacian Circuit Solver:</b> Constructs the grounded Laplacian matrix from transaction conductances ($w = satoshis$), grounds Node 0 ($V_0 = 0V$), and solves $Lx = b$ via Sparse LU.<br/>"
        "<b>5. Inverse Resistance Scoring:</b> Conductance weights $w_i = 1 / (R_{eff} + 10^{-6})$ normalize effective resistance into probability confidence percentages.<br/>"
        "<b>6. SAHYOG Dispatch & Section 65B PDF:</b> Issues Section 91 CrPC statutory notice with SHA-256 tamper-proof hash and outputs court-certified PDF dossiers."
    )
    story.append(Paragraph(flow_text, body_style))
    story.append(Spacer(1, 8))

    # 2. Key Code Snippets
    story.append(Paragraph("2. Key Implementation Code Snippets", h1_style))

    story.append(Paragraph("A. Proportional UTXO Apportionment (backend/ingestion/blockstream_client.py)", h2_style))
    code_1 = (
        "# Proportional Haircut allocation based on input stake:\n"
        "if total_input_value > 0 and source_values[src] > 0:\n"
        "    allocated_amount = max(1, round(value * (source_values[src] / total_input_value)))\n"
        "else:\n"
        "    allocated_amount = max(1, value // len(sources))\n"
        "edges.append(UniformEdge(src, target_addr, allocated_amount, tx_hash, timestamp))"
    )
    story.append(Paragraph(code_1.replace("\n", "<br/>&nbsp;&nbsp;"), code_style))

    story.append(Paragraph("B. Directional Temporal Filter & Adaptive Beam Search (backend/ingestion/extractor.py)", h2_style))
    code_2 = (
        "# Temporal check: ensure fund outflow occurred after arrival\n"
        "if t_arrival and edge.timestamp and edge.source_address == curr_addr:\n"
        "    if edge.timestamp < t_arrival - timedelta(hours=2):\n"
        "        continue\n"
        "# Adaptive Beam Search: retain branches until >= 85% volume mass is captured\n"
        "if hops_queued >= 3 and (accumulated_vol / total_candidate_vol) >= 0.85:\n"
        "    break"
    )
    story.append(Paragraph(code_2.replace("\n", "<br/>&nbsp;&nbsp;"), code_style))

    story.append(Paragraph("C. Inverse-Resistance Confidence Normalization (backend/services/attribution_service.py)", h2_style))
    code_3 = (
        "# Invert effective resistance to conductance:\n"
        "inverse_weights = {c: 1.0 / (attr_result.scores[c] + 1e-6) for c in candidates}\n"
        "total_weight = sum(inverse_weights.values()) or 1.0\n"
        "confidence = inverse_weights[c] / total_weight  # Normalized [0.0 - 1.0]"
    )
    story.append(Paragraph(code_3.replace("\n", "<br/>&nbsp;&nbsp;"), code_style))

    story.append(Paragraph("D. Tamper-Proof SAHYOG Dispatch Hashing (backend/services/sahyog_service.py)", h2_style))
    code_4 = (
        "ack_token = f'SAHYOG-ACK-2026-{uuid.uuid4().hex[:6].upper()}'\n"
        "payload = f'{req.case_id}:{req.suspect_address}:{req.target_vasp}:{req.action}:{now_str}'\n"
        "dispatch_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()\n"
        "self.repo.create_dispatch(ack_token=ack_token, dispatch_hash=dispatch_hash, ...)"
    )
    story.append(Paragraph(code_4.replace("\n", "<br/>&nbsp;&nbsp;"), code_style))

    story.append(Spacer(1, 6))

    # 3. Master Function & Endpoint Reference Table
    story.append(Paragraph("3. Master Function & Endpoint Reference Table", h1_style))
    table_data = [
        [
            Paragraph("<b>Function / Route</b>", th_style),
            Paragraph("<b>Type</b>", th_style),
            Paragraph("<b>Input Parameters</b>", th_style),
            Paragraph("<b>Output Return Value</b>", th_style),
        ],
        [
            Paragraph("<code>POST /api/v1/investigate</code>", td_style),
            Paragraph("Endpoint", td_style),
            Paragraph("<code>InvestigateRequest</code> (address, chain, depth)", td_style),
            Paragraph("<code>InvestigateResponse</code> (Ranked VASPs, R_eff, confidence)", td_style),
        ],
        [
            Paragraph("<code>POST /attribute</code>", td_style),
            Paragraph("Endpoint", td_style),
            Paragraph("<code>AttributionRequest</code> (suspect, candidate_vasps)", td_style),
            Paragraph("<code>AttributionResponse</code> (scores, ranked)", td_style),
        ],
        [
            Paragraph("<code>GET /api/v1/graph/subgraph/{addr}</code>", td_style),
            Paragraph("Endpoint", td_style),
            Paragraph("<code>address: str</code>, <code>depth: int</code>, <code>chain: str</code>", td_style),
            Paragraph("<code>SubgraphResponse</code> (Cytoscape.js nodes/edges)", td_style),
        ],
        [
            Paragraph("<code>POST /api/v1/sahyog/dispatch</code>", td_style),
            Paragraph("Endpoint", td_style),
            Paragraph("<code>SahyogDispatchRequest</code> (case_id, suspect, vasp, action)", td_style),
            Paragraph("<code>SahyogDispatchResponse</code> (ack_token, SHA-256 hash)", td_style),
        ],
        [
            Paragraph("<code>GET /api/v1/reports/{id}/export</code>", td_style),
            Paragraph("Endpoint", td_style),
            Paragraph("<code>case_id: str</code>", td_style),
            Paragraph("<code>StreamingResponse</code> (Section 65B PDF)", td_style),
        ],
        [
            Paragraph("<code>SubgraphExtractor.extract_subgraph</code>", td_style),
            Paragraph("Method", td_style),
            Paragraph("<code>suspect_addr: str</code>, <code>max_depth: int</code>", td_style),
            Paragraph("<code>(G: nx.Graph, candidates: List[str], meta: dict)</code>", td_style),
        ],
        [
            Paragraph("<code>BlockstreamClient.get_or_fetch_edges</code>", td_style),
            Paragraph("Method", td_style),
            Paragraph("<code>address: str</code>", td_style),
            Paragraph("<code>List[UniformEdge]</code> (Proportional haircut edges)", td_style),
        ],
        [
            Paragraph("<code>ReportService.generate_pdf_report</code>", td_style),
            Paragraph("Method", td_style),
            Paragraph("<code>case_id: str</code>", td_style),
            Paragraph("<code>io.BytesIO</code> (Court-admissible PDF buffer)", td_style),
        ],
    ]

    ref_table = Table(table_data, colWidths=[130, 45, 180, 185])
    ref_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), primary),
        ("BOX", (0, 0), (-1, -1), 0.5, border_color),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(ref_table)

    doc.build(story, canvasmaker=NumberedCanvas)
    return str(target_path)


if __name__ == "__main__":
    out_file = ROOT_DIR / "SIH26182_Backend_Implementation_Report.pdf"
    print(f"[*] Compiling SIH26182 Backend Implementation Report PDF to: {out_file}...")
    try:
        result = build_backend_report_pdf(out_file)
        print(f"[✓] Successfully generated Backend Implementation Report PDF at:\n    {result}")
        print(f"[*] File size: {out_file.stat().st_size:,} bytes")
    except Exception as e:
        print(f"[X] Failed to compile PDF: {e}")
