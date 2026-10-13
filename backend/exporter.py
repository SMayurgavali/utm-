"""
Phase 6: Multi-Format Data Export Pipelines
Generates:
1. Excel Reports (.xlsx) via standard OpenXML package
2. Lightweight Comma-Separated Values (.csv)
3. Raw XYT Time-Series Data tables (.xyt / .txt)
"""

import io
import csv
import zipfile
import xml.etree.ElementTree as ET
from typing import Dict, Any, List

class MultiFormatExporter:
    """Enterprise multi-format data export engine."""

    @staticmethod
    def generate_csv(record: Dict[str, Any]) -> str:
        """Generates RFC 4180 compliant CSV string."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Metadata comments
        config = record.get("config", {})
        writer.writerow(["# UTM TEST DATA RECORD"])
        writer.writerow(["# Sample ID", config.get("sample_id", "UNKNOWN")])
        writer.writerow(["# Material Grade", config.get("material_grade", "UNKNOWN")])
        writer.writerow(["# Standard", config.get("standard", "IS 1786")])
        writer.writerow(["# Area A_0 (mm2)", config.get("a_0", 50.0)])
        writer.writerow(["# Gauge Length L_0 (mm)", config.get("l_0", 50.0)])
        writer.writerow(["# Peak Force (kN)", record.get("f_max_kn", 0.0)])
        writer.writerow(["# Ultimate Tensile Strength Su (MPa)", record.get("s_u_mpa", 0.0)])
        writer.writerow([]) # Empty row

        # Table Header
        writer.writerow([
            "Time_s",
            "Force_N",
            "Force_kN",
            "Displacement_mm",
            "Stress_MPa",
            "Strain_Ratio",
            "Strain_Pct"
        ])

        t_list = record.get("time_series", [])
        fn_list = record.get("force_series_n", [])
        fkn_list = record.get("force_series_kn", [])
        d_list = record.get("disp_series_mm", [])
        s_list = record.get("stress_series_mpa", [])
        sr_list = record.get("strain_series_ratio", [])
        sp_list = record.get("strain_series_pct", [])

        for i in range(len(t_list)):
            writer.writerow([
                f"{t_list[i]:.4f}",
                f"{fn_list[i]:.2f}",
                f"{fkn_list[i]:.4f}",
                f"{d_list[i]:.4f}",
                f"{s_list[i]:.2f}",
                f"{sr_list[i]:.6f}",
                f"{sp_list[i]:.4f}"
            ])

        return output.getvalue()

    @staticmethod
    def generate_xyt(record: Dict[str, Any]) -> str:
        """
        Generates raw XYT Time-Series Data tables:
        X = Time (seconds), Y = Force (kN), T = Displacement (mm)
        Standard industrial format for finite element and structural post-processing.
        """
        output = io.StringIO()
        config = record.get("config", {})
        output.write("# ==========================================================================\n")
        output.write(f"# UTM RAW XYT TIME-SERIES TELEMETRY STREAM\n")
        output.write(f"# SAMPLE_ID        : {config.get('sample_id', 'UNKNOWN')}\n")
        output.write(f"# MATERIAL_GRADE   : {config.get('material_grade', 'UNKNOWN')}\n")
        output.write(f"# BASELINE_AREA_A0 : {config.get('a_0', 50.0):.2f} mm^2\n")
        output.write(f"# GAUGE_LENGTH_L0  : {config.get('l_0', 50.0):.2f} mm\n")
        output.write(f"# COLUMN 1 [X]     : Elapsed Time (s)\n")
        output.write(f"# COLUMN 2 [Y]     : Load Force (kN)\n")
        output.write(f"# COLUMN 3 [T]     : Crosshead Displacement (mm)\n")
        output.write("# ==========================================================================\n")
        output.write("# Time_s\t\tForce_kN\t\tDisplacement_mm\n")

        t_list = record.get("time_series", [])
        fkn_list = record.get("force_series_kn", [])
        d_list = record.get("disp_series_mm", [])

        for i in range(len(t_list)):
            output.write(f"{t_list[i]:10.4f}\t\t{fkn_list[i]:10.4f}\t\t{d_list[i]:10.4f}\n")

        return output.getvalue()

    @staticmethod
    def generate_xlsx(record: Dict[str, Any]) -> bytes:
        """
        Generates standard OpenXML Excel (.xlsx) package natively.
        Includes metadata summary banner and complete raw data table.
        """
        config = record.get("config", {})
        sample_id = str(config.get("sample_id", "TEST_SAMPLE"))
        f_max_kn = record.get("f_max_kn", 0.0)
        s_u_mpa = record.get("s_u_mpa", 0.0)

        t_list = record.get("time_series", [])
        fn_list = record.get("force_series_n", [])
        fkn_list = record.get("force_series_kn", [])
        d_list = record.get("disp_series_mm", [])
        s_list = record.get("stress_series_mpa", [])
        sr_list = record.get("strain_series_ratio", [])
        sp_list = record.get("strain_series_pct", [])

        # Build sheet1.xml rows
        sheet_rows = []
        
        # Title & Summary
        sheet_rows.append('<row r="1"><c r="A1" t="inlineStr"><is><t>AI-POWERED UTM TEST REPORT</t></is></c></row>')
        sheet_rows.append(f'<row r="2"><c r="A2" t="inlineStr"><is><t>Sample ID: {sample_id}</t></is></c><c r="C2" t="inlineStr"><is><t>Peak Force: {f_max_kn:.3f} kN</t></is></c><c r="E2" t="inlineStr"><is><t>Su: {s_u_mpa:.2f} MPa</t></is></c></row>')
        sheet_rows.append('<row r="3"/>') # Blank

        # Header row at r=4
        headers = ["Time (s)", "Force (N)", "Force (kN)", "Displacement (mm)", "Stress (MPa)", "Strain Ratio", "Strain (%)"]
        col_letters = ["A", "B", "C", "D", "E", "F", "G"]
        
        h_cells = "".join([f'<c r="{col_letters[i]}4" t="inlineStr"><is><t>{headers[i]}</t></is></c>' for i in range(len(headers))])
        sheet_rows.append(f'<row r="4">{h_cells}</row>')

        # Data rows starting at r=5
        for idx in range(len(t_list)):
            r_num = idx + 5
            c_a = f'<c r="A{r_num}"><v>{t_list[idx]:.4f}</v></c>'
            c_b = f'<c r="B{r_num}"><v>{fn_list[idx]:.2f}</v></c>'
            c_c = f'<c r="C{r_num}"><v>{fkn_list[idx]:.4f}</v></c>'
            c_d = f'<c r="D{r_num}"><v>{d_list[idx]:.4f}</v></c>'
            c_e = f'<c r="E{r_num}"><v>{s_list[idx]:.2f}</v></c>'
            c_f = f'<c r="F{r_num}"><v>{sr_list[idx]:.6f}</v></c>'
            c_g = f'<c r="G{r_num}"><v>{sp_list[idx]:.4f}</v></c>'
            sheet_rows.append(f'<row r="{r_num}">{c_a}{c_b}{c_c}{c_d}{c_e}{c_f}{c_g}</row>')

        rows_xml = "".join(sheet_rows)

        sheet1_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">\n'
            f'<sheetData>{rows_xml}</sheetData>\n'
            '</worksheet>'
        )

        content_types_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
            '<Default Extension="xml" ContentType="application/xml"/>\n'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>\n'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>\n'
            '</Types>'
        )

        rels_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>\n'
            '</Relationships>'
        )

        workbook_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">\n'
            '<sheets>\n'
            '<sheet name="UTM Telemetry Data" sheetId="1" r:id="rId1"/>\n'
            '</sheets>\n'
            '</workbook>'
        )

        workbook_rels_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>\n'
            '</Relationships>'
        )

        # Assemble in memory zip
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('[Content_Types].xml', content_types_xml)
            zf.writestr('_rels/.rels', rels_xml)
            zf.writestr('xl/workbook.xml', workbook_xml)
            zf.writestr('xl/_rels/workbook.xml.rels', workbook_rels_xml)
            zf.writestr('xl/worksheets/sheet1.xml', sheet1_xml)

        return zip_buffer.getvalue()
