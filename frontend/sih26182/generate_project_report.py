#!/usr/bin/env python3
"""
CLI script to generate the comprehensive SIH26182 Project Implementation PDF Report.
Outputs: SIH26182_Project_Implementation_Report.pdf in the root project folder.
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.services.project_report_generator import generate_pdf_file

if __name__ == "__main__":
    out_pdf = ROOT_DIR / "SIH26182_Project_Implementation_Report.pdf"
    print(f"[*] Generating SIH26182 Project Implementation Report PDF...")
    result_path = generate_pdf_file(out_pdf)
    print(f"[✓] Successfully generated PDF report at:\n    {result_path}")
    print(f"[*] File size: {out_pdf.stat().st_size:,} bytes")
