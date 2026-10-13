"""
Phase 5: Document Layout Generator Engine & PDF Report Compilation
Generates high-resolution vector PDF reports with document metadata headers,
embedded vector stress-strain plots, AI compliance narratives,
and three structural verification sign-off footer blocks.
"""

import os
import io
import time
import datetime
import hashlib
from typing import Dict, Any, Optional
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # Non-GUI backend for server execution
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_pdf import PdfPages
import pypdf

from backend.ai_compliance import AIComplianceReviewer

class PDFReportGenerator:
    """
    High-fidelity PDF document layout generation module.
    Compiles structured engineering reports with vector chart embeddings
    and structural sign-off footers.
    """

    @classmethod
    def generate_pdf_report(cls, record: Dict[str, Any], output_path: Optional[str] = None) -> bytes:
        config = record.get("config", {})
        sample_id = config.get("sample_id") or "Not provided"
        company_name = config.get("company_name") or "Not provided"
        system_serial = config.get("system_serial_number") or "Not provided"
        material_grade = config.get("material_grade", "IS_1786_FE500")
        standard_name = config.get("standard", "IS 1786")
        operator_name = config.get("operator_name") or "Not provided"
        inspector_name = config.get("inspector_name") or "Not provided"
        witness_name = config.get("witness_name") or "Not provided"
        timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")

        # Evaluate AI Compliance
        compliance = AIComplianceReviewer.evaluate_compliance(record)
        metrics = AIComplianceReviewer.extract_curve_characteristics(record)

        # Extract data series
        strain_pct = record.get("strain_series_pct", [0.0, 1.0])
        stress_mpa = record.get("stress_series_mpa", [0.0, 100.0])
        disp_mm = record.get("disp_series_mm", [0.0, 0.5])
        force_kn = record.get("force_series_kn", [0.0, 5.0])

        f_max_kn = record.get("f_max_kn", max(force_kn) if force_kn else 0.0)
        d_peak_mm = record.get("d_peak_mm", 0.0)
        s_u_mpa = record.get("s_u_mpa", max(stress_mpa) if stress_mpa else 0.0)
        a_0 = config.get("a_0", 50.0)
        l_0 = config.get("l_0", 50.0)

        # Create multi-panel vector document figure
        # Standard A4 size in inches: 8.27 x 11.69
        fig = plt.figure(figsize=(8.27, 11.69), dpi=300)
        fig.patch.set_facecolor('#ffffff')

        # 1. Header Banner & Document Metadata
        # Draw top decorative banner
        ax_top = fig.add_axes([0.05, 0.90, 0.90, 0.08])
        ax_top.axis('off')
        ax_top.text(0.0, 0.70, "UNIVERSAL TESTING MACHINE (UTM) TEST REPORT", 
                    fontsize=14, fontweight='bold', color='#0f172a')
        ax_top.text(0.0, 0.35, "AI-POWERED UTM CLOUD HUB • MECHANICAL RETROFITTING PLATFORM", 
                    fontsize=9, fontweight='semibold', color='#2563eb')
        ax_top.text(0.0, 0.05, f"COMPLIANCE STANDARD: {compliance.standard.upper()}", 
                    fontsize=8.5, fontweight='bold', color='#059669' if compliance.is_compliant else '#dc2626')
        
        # QR / Verification Stamp badge on top right
        status_box = dict(boxstyle='round,pad=0.5', facecolor='#ecfdf5' if compliance.is_compliant else '#fef2f2', 
                          edgecolor='#10b981' if compliance.is_compliant else '#ef4444', linewidth=1.5)
        review_stamp = "REVIEW\nPASS" if compliance.is_compliant else "REVIEW\nFAIL" if compliance.evaluation_applicable else "NOT\nEVALUATED"
        ax_top.text(0.98, 0.45, review_stamp,
                    fontsize=10, fontweight='bold', color='#065f46' if compliance.is_compliant else '#991b1b',
                    ha='right', va='center', bbox=status_box)

        # 2. Document Metadata Headers Table
        ax_meta = fig.add_axes([0.05, 0.77, 0.90, 0.12])
        ax_meta.axis('off')
        
        # Background rect
        rect = patches.FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0.01", 
                                      facecolor="#f8fafc", edgecolor="#cbd5e1", linewidth=1.0)
        ax_meta.add_patch(rect)

        col1_text = (
            f"Company / Lab: {company_name}\n"
            f"System Serial No: {system_serial} (FTDI 9600 8-N-1)\n"
            f"Sample ID: {sample_id}\n"
            f"Material Grade: {material_grade}"
        )
        col2_text = (
            f"Execution Timestamp: {timestamp_str}\n"
            f"Measured Cross-Section (A_0): {a_0:.3f} mm²\n"
            f"Measured Gauge Length (L_0): {l_0:.3f} mm\n"
            f"Audit Hash (SHA-256): {compliance.audit_hash_sha256[:16]}..."
        )
        ax_meta.text(0.03, 0.50, col1_text, fontsize=8.2, color='#1e293b', va='center', linespacing=1.6)
        ax_meta.text(0.53, 0.50, col2_text, fontsize=8.2, color='#1e293b', va='center', linespacing=1.6)

        # 3. Vector Graphic Embeddings: Engineering Stress-Strain Chart
        ax_chart = fig.add_axes([0.08, 0.44, 0.84, 0.30])
        ax_chart.set_facecolor('#ffffff')
        
        # Plot Stress vs Strain (%)
        ax_chart.plot(strain_pct, stress_mpa, color='#2563eb', linewidth=1.8, label='Engineering Stress (MPa)')
        ax_chart.set_title(f"Engineering Stress-Strain Curve — {sample_id}", fontsize=10, fontweight='bold', color='#0f172a', pad=8)
        ax_chart.set_xlabel("Engineering Strain, ε (%) [ΔL / L₀]", fontsize=8.5, fontweight='semibold')
        ax_chart.set_ylabel("Engineering Stress, σ (MPa) [F / A₀]", fontsize=8.5, fontweight='semibold')
        ax_chart.grid(True, linestyle='--', alpha=0.5, color='#94a3b8')
        
        # Annotate Peak Load F_max / Su
        if stress_mpa:
            peak_val = max(stress_mpa)
            peak_idx = stress_mpa.index(peak_val)
            peak_strain = strain_pct[peak_idx] if peak_idx < len(strain_pct) else 0.0
            ax_chart.plot(peak_strain, peak_val, marker='o', markersize=6, color='#dc2626')
            ax_chart.annotate(f"Peak (Su = {peak_val:.1f} MPa)\nF_max = {f_max_kn:.2f} kN",
                              xy=(peak_strain, peak_val), xytext=(peak_strain * 0.7, peak_val * 0.95),
                              arrowprops=dict(facecolor='#dc2626', shrink=0.08, width=1, headwidth=4),
                              fontsize=7.5, fontweight='bold', color='#991b1b',
                              bbox=dict(boxstyle='square,pad=0.2', facecolor='#fee2e2', edgecolor='#dc2626', alpha=0.9))

        # Annotate Yield Stress if available
        if metrics["yield_stress_mpa"] > 0:
            ys_val = metrics["yield_stress_mpa"]
            ax_chart.axhline(y=ys_val, color='#059669', linestyle=':', alpha=0.8, label=f'Yield Rp0.2 ({ys_val:.1f} MPa)')

        # Annotate Fracture Point
        if strain_pct and len(strain_pct) > 5 and record.get("is_fractured", True):
            fracture_strain = strain_pct[-1]
            fracture_stress = stress_mpa[-1]
            ax_chart.plot(fracture_strain, fracture_stress, marker='x', markersize=8, color='#000000', markeredgewidth=2)
            ax_chart.annotate("Fracture (0.0 N)", xy=(fracture_strain, fracture_stress),
                              xytext=(fracture_strain * 0.85, 30.0),
                              arrowprops=dict(facecolor='#000000', shrink=0.08, width=1, headwidth=4),
                              fontsize=7.5, fontweight='bold', color='#000000',
                              bbox=dict(boxstyle='square,pad=0.2', facecolor='#f1f5f9', edgecolor='#64748b', alpha=0.9))

        ax_chart.legend(loc='lower right', fontsize=7.5, framealpha=0.8)

        # 4. Mechanical Properties Matrix Table
        ax_table = fig.add_axes([0.05, 0.28, 0.90, 0.14])
        ax_table.axis('off')
        
        table_data = [
            ["Metric Parameter", "Measured Value", "Standard Threshold", "Clause Status"],
            ["Peak Load Force (F_max)", f"{f_max_kn:.3f} kN ({record.get('f_max_n', 0):.0f} N)", "Recorded telemetry", "RECORDED"],
            ["Ultimate / Compressive Strength", f"{s_u_mpa:.2f} MPa", f">= {compliance.uts_threshold_min:.1f} MPa" if compliance.evaluation_applicable else "Manual review", "PASS" if compliance.evaluation_applicable and s_u_mpa >= compliance.uts_threshold_min else "NOT REVIEWED" if not compliance.evaluation_applicable else "FAIL"],
            ["0.2% Proof / Yield Stress (Rp0.2)", f"{compliance.yield_stress_mpa:.2f} MPa", f">= {compliance.yield_threshold_min:.1f} MPa" if compliance.evaluation_applicable else "Not applicable", "PASS" if compliance.evaluation_applicable and compliance.yield_stress_mpa >= compliance.yield_threshold_min else "NOT REVIEWED" if not compliance.evaluation_applicable else "FAIL"],
            ["Tensile / Yield Strength Ratio", f"{compliance.ts_ys_ratio:.2f}", f">= {compliance.ratio_threshold_min:.2f}" if compliance.evaluation_applicable else "Not applicable", "PASS" if compliance.evaluation_applicable and compliance.ts_ys_ratio >= compliance.ratio_threshold_min else "NOT REVIEWED" if not compliance.evaluation_applicable else "FAIL"],
            ["End Elongation", f"{compliance.elongation_pct:.2f} %", f">= {compliance.elongation_threshold_min:.1f} %" if compliance.evaluation_applicable else "Not applicable", "PASS" if compliance.evaluation_applicable and compliance.elongation_pct >= compliance.elongation_threshold_min else "NOT REVIEWED" if not compliance.evaluation_applicable else "FAIL"]
        ]
        
        table = ax_table.table(cellText=table_data, loc='center', cellLoc='center', colWidths=[0.35, 0.23, 0.24, 0.18])
        table.auto_set_font_size(False)
        table.set_fontsize(7.8)
        table.scale(1.0, 1.35)
        
        # Style table headers
        for col_idx in range(4):
            table[(0, col_idx)].set_facecolor('#0f172a')
            table[(0, col_idx)].set_text_props(color='#ffffff', fontweight='bold')
        
        # Style status column
        for row_idx in range(1, len(table_data)):
            val = table_data[row_idx][3]
            cell = table[(row_idx, 3)]
            if val in {"PASS", "RECORDED"}:
                cell.set_facecolor('#dcfce7')
                cell.set_text_props(color='#166534', fontweight='bold')
            elif val == "NOT REVIEWED":
                cell.set_facecolor('#fef3c7')
                cell.set_text_props(color='#854d0e', fontweight='bold')
            else:
                cell.set_facecolor('#fee2e2')
                cell.set_text_props(color='#991b1b', fontweight='bold')

        # 5. AI Compliance Audit Review Narrative Block
        ax_narrative = fig.add_axes([0.05, 0.14, 0.90, 0.12])
        ax_narrative.axis('off')
        
        narrative_box = patches.FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0.01", 
                                              facecolor="#f1f5f9", edgecolor="#94a3b8", linewidth=1.0)
        ax_narrative.add_patch(narrative_box)
        
        ax_narrative.text(0.02, 0.88, "AUTOMATED REVIEW NARRATIVE:", 
                          fontsize=8, fontweight='bold', color='#1e293b')
        ax_narrative.text(0.02, 0.42, compliance.executive_narrative, 
                          fontsize=7.2, color='#334155', wrap=True, va='center', linespacing=1.45)

        # 6. Verification Sign-Off Footer Blocks: Three structural sign-off footer lines
        # Reserving signature areas tracking accountability for:
        # TESTED BY, INSPECTED BY, and WITNESSED BY
        ax_footers = fig.add_axes([0.05, 0.03, 0.90, 0.09])
        ax_footers.axis('off')

        # Three distinct signature columns
        col_w = 0.30
        gap = 0.05
        
        # Box 1: TESTED BY
        b1_x = 0.0
        ax_footers.add_patch(patches.FancyBboxPatch((b1_x, 0), col_w, 1.0, boxstyle="square,pad=0", 
                                                   facecolor="#ffffff", edgecolor="#cbd5e1", linewidth=0.8))
        ax_footers.text(b1_x + 0.02, 0.82, "TESTED BY (OPERATOR):", fontsize=7.5, fontweight='bold', color='#0f172a')
        ax_footers.text(b1_x + 0.02, 0.50, f"Sign: __________________\nName: {operator_name[:25]}\nDate: {timestamp_str[:10]}", 
                        fontsize=6.8, color='#475569', linespacing=1.3)

        # Box 2: INSPECTED BY
        b2_x = col_w + gap
        ax_footers.add_patch(patches.FancyBboxPatch((b2_x, 0), col_w, 1.0, boxstyle="square,pad=0", 
                                                   facecolor="#ffffff", edgecolor="#cbd5e1", linewidth=0.8))
        ax_footers.text(b2_x + 0.02, 0.82, "INSPECTED BY (LAB HEAD):", fontsize=7.5, fontweight='bold', color='#0f172a')
        ax_footers.text(b2_x + 0.02, 0.50, f"Sign: __________________\nName: {inspector_name[:25]}\nDate: {timestamp_str[:10]}", 
                        fontsize=6.8, color='#475569', linespacing=1.3)

        # Box 3: WITNESSED BY
        b3_x = (col_w + gap) * 2
        ax_footers.add_patch(patches.FancyBboxPatch((b3_x, 0), col_w, 1.0, boxstyle="square,pad=0", 
                                                   facecolor="#ffffff", edgecolor="#cbd5e1", linewidth=0.8))
        ax_footers.text(b3_x + 0.02, 0.82, "WITNESSED BY (AUDITOR):", fontsize=7.5, fontweight='bold', color='#0f172a')
        ax_footers.text(b3_x + 0.02, 0.50, f"Sign: __________________\nName: {witness_name[:25]}\nDate: {timestamp_str[:10]}", 
                        fontsize=6.8, color='#475569', linespacing=1.3)

        # Compile PDF in memory
        raw_pdf_io = io.BytesIO()
        fig.savefig(raw_pdf_io, format='pdf', bbox_inches='tight', dpi=300)
        plt.close(fig)
        raw_pdf_io.seek(0)

        # Apply Security State Serialization:
        # Add report metadata and an audit hash for traceability.
        reader = pypdf.PdfReader(raw_pdf_io)
        writer = pypdf.PdfWriter()
        
        for page in reader.pages:
            writer.add_page(page)

        # Add report metadata and the compliance review hash.
        metadata = {
            "/Title": f"UTM Test Report - {sample_id}",
            "/Author": "AI-Powered UTM Cloud Hub Retrofitting Platform",
            "/Subject": f"Automated tensile test review - {compliance.standard}",
            "/Keywords": "UTM, Tensile, IS 1608, IS 1786, ASTM E8, Stress, Strain",
            "/Producer": "AI-Powered UTM Engine v2.4",
            "/Custom_Audit_SHA256": compliance.audit_hash_sha256
        }
        writer.add_metadata(metadata)

        # Write final report output.
        final_pdf_io = io.BytesIO()
        writer.write(final_pdf_io)
        pdf_bytes = final_pdf_io.getvalue()

        if output_path:
            with open(output_path, "wb") as f:
                f.write(pdf_bytes)

        return pdf_bytes
