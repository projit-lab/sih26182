import hashlib
import io
import logging
from datetime import datetime
from typing import Optional

from backend.database.repositories import CaseRepository

logger = logging.getLogger(__name__)

# Check if reportlab is available
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False
    logger.warning("ReportLab not installed. Falling back to plain text/HTML report generator.")


class ReportService:
    """
    Compiles investigator lead reports with mathematical attribution output.
    These are prototype outputs for lead generation only, not legal documents.
    """

    def __init__(self, case_repo: Optional[CaseRepository] = None):
        self.case_repo = case_repo or CaseRepository()

    def generate_pdf_report(self, case_id: str) -> io.BytesIO:
        case_data = self.case_repo.get_case(case_id)
        if not case_data:
            case_data = self.case_repo.get_latest_case_by_suspect(case_id)
        if not case_data:
            raise ValueError(f"Case ID or Suspect '{case_id}' not found in database.")

        suspect = case_data["suspect_address"]
        top_vasp = case_data["top_vasp"]
        confidence = case_data["confidence"]
        results = case_data.get("results", {})
        ranked_vasps = results.get("ranked_vasps", [])
        graph_summary = results.get("graph_summary", {})

        buffer = io.BytesIO()

        if not HAS_REPORTLAB:
            # Fallback plain text / PDF emulation
            content = f"""%PDF-1.4
% INVESTIGATOR LEAD REPORT (PROTOTYPE)
Case ID: {case_id}
Suspect Wallet: {suspect}
Top Attributed VASP: {top_vasp}
Generated At: {datetime.utcnow().isoformat()}Z
==================================================
Prototype output for investigator lead generation. Not evidence. Not certified under Section 65B / Section 63 BSA.
"""
            buffer.write(content.encode("utf-8"))
            buffer.seek(0)
            return buffer

        # Build PDF using ReportLab
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=54,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#1e293b"),
            alignment=1,
        )
        subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#475569"),
            alignment=1,
        )
        h2_style = ParagraphStyle(
            "SectionHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=10,
            spaceAfter=4,
        )
        body_style = ParagraphStyle(
            "BodyText",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#334155"),
        )
        code_style = ParagraphStyle(
            "CodeText",
            parent=styles["Normal"],
            fontName="Courier",
            fontSize=7.5,
            leading=9.5,
            textColor=colors.HexColor("#0f172a"),
            wordWrap="CJK",
        )

        story = []

        # Header
        story.append(Paragraph("INVESTIGATOR LEAD REPORT - PROTOTYPE (NOT A LEGAL OR FORENSIC DOCUMENT)", title_style))
        story.append(Paragraph("Cryptocurrency Flow &amp; VASP Attribution Analysis (Circuit Theory Engine)", subtitle_style))
        story.append(Spacer(1, 8))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=12))

        # Case Meta Box
        meta_table_data = [
            [
                Paragraph("<b>Case Reference:</b>", body_style),
                Paragraph(f"<code>{case_id}</code>", code_style),
                Paragraph("<b>Date Generated:</b>", body_style),
                Paragraph(datetime.utcnow().strftime("%d %b %Y, %H:%M:%S UTC"), body_style),
            ],
            [
                Paragraph("<b>Suspect Address:</b>", body_style),
                Paragraph(f"<code>{suspect}</code>", code_style),
                Paragraph("<b>Network:</b>", body_style),
                Paragraph("Bitcoin (BTC Mainnet)", body_style),
            ],
            [
                Paragraph("<b>Top Attributed VASP:</b>", body_style),
                Paragraph(f"<b>{top_vasp}</b>", body_style),
                Paragraph("<b>Rank:</b>", body_style),
                Paragraph("#1 by effective resistance", body_style),
            ],
        ]
        meta_table = Table(meta_table_data, colWidths=[110, 160, 110, 160])
        meta_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(meta_table)
        story.append(Spacer(1, 12))

        # Section 1: Case Summary
        story.append(Paragraph("1. CASE SUMMARY", h2_style))
        best_r_eff = ranked_vasps[0].get("effective_resistance", 0.0) if ranked_vasps else 0.0
        second_r_eff = ranked_vasps[1].get("effective_resistance", None) if len(ranked_vasps) > 1 else None
        sep_text = ""
        if second_r_eff and best_r_eff and best_r_eff > 0:
            sep_ratio = round(second_r_eff / best_r_eff, 2)
            sep_text = f" (separation ratio vs. rank #2: <b>{sep_ratio}x</b>)"
        summary_text = (
            f"An automated topological graph resistance analysis was conducted for suspect address "
            f"<b>{suspect}</b>. By calculating the grounded Laplacian matrix <b>(Lx = b)</b> across the "
            f"k-hop transaction neighborhood, multiple parallel obfuscation paths (mixers / peeling hops) "
            f"were aggregated into a unified effective resistance metric. The destination VASP demonstrating the "
            f"strongest conductance is <b>{top_vasp}</b> with an effective resistance of "
            f"<b>{best_r_eff}</b>{sep_text}."
        )
        story.append(Paragraph(summary_text, body_style))
        story.append(Spacer(1, 10))

        # Section 2: Ranked Candidates Table
        story.append(Paragraph("2. CANDIDATE VASP ATTRIBUTION MATRIX", h2_style))
        table_rows = [
            [
                Paragraph("<b>Rank</b>", body_style),
                Paragraph("<b>Entity Name</b>", body_style),
                Paragraph("<b>Candidate Address</b>", body_style),
                Paragraph("<b>Effective Resistance (Ohms)</b>", body_style),
            ]
        ]
        for idx, item in enumerate(ranked_vasps[:6], 1):
            table_rows.append(
                [
                    Paragraph(str(idx), body_style),
                    Paragraph(item.get("vasp_name", "Unknown"), body_style),
                    Paragraph(f"<code>{item.get('candidate_address', '')[:16]}...</code>", code_style),
                    Paragraph(str(item.get("effective_resistance", "N/A")), body_style),
                ]
            )

        vasp_table = Table(table_rows, colWidths=[40, 140, 180, 180])
        vasp_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e0f2fe")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(vasp_table)
        story.append(Spacer(1, 10))

        # Section 3: Graph Analytics
        story.append(Paragraph("3. GRAPH COMPUTATION METRICS", h2_style))
        metrics_text = (
            f"Neighborhood graph nodes analyzed: <b>{graph_summary.get('nodes_analyzed', 0)}</b> | "
            f"Edges analyzed: <b>{graph_summary.get('edges_analyzed', 0)}</b> | "
            f"Laplacian solver execution time: <b>{graph_summary.get('compute_time_ms', 0)} ms</b> | "
            f"Solver method: <b>{graph_summary.get('solver_method', 'effective_resistance')}</b>"
        )
        story.append(Paragraph(metrics_text, body_style))
        story.append(Spacer(1, 12))

        # Demo checksum (not a certification)
        raw_hash = hashlib.sha256(f"{case_id}:{suspect}:{top_vasp}".encode()).hexdigest()
        story.append(Paragraph(
            f"<b>Demo checksum (not a certification):</b> <code>{raw_hash}</code>",
            body_style,
        ))

        # Footer on every page
        footer_text = (
            "Prototype output for investigator lead generation. "
            "Not evidence. Not certified under Section 65B / Section 63 BSA."
        )

        def add_footer(canvas, doc):
            canvas.saveState()
            canvas.setFont("Helvetica", 7.5)
            canvas.setFillColor(colors.HexColor("#94a3b8"))
            canvas.drawCentredString(letter[0] / 2.0, 22, footer_text)
            canvas.restoreState()

        doc.build(story, onFirstPage=add_footer, onLaterPages=add_footer)
        buffer.seek(0)
        return buffer
