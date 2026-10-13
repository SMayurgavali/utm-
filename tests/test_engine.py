"""
Comprehensive Automated Test Suite for AI-Powered UTM Cloud Hub
Validates Phase 1 through Phase 6 core specifications.
"""

import sys
import os
import json
import zipfile
import io
from pathlib import Path
from unittest.mock import patch

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from edge.edge_agent import EdgeAgent
from edge.cache_buffer import OfflineCacheBuffer
from backend.schemas import TelemetryPayload, SampleConfig
from backend.math_engine import SoftwareMathEngine
from backend.ai_compliance import AIComplianceReviewer
from backend.report_generator import PDFReportGenerator
from backend.exporter import MultiFormatExporter
import pypdf

def test_edge_telemetry_parsing():
    print("[TEST 1] Testing Edge Telemetry Signal Parsing (Phase 1)...")
    agent = EdgeAgent(use_virtual=True)
    
    # 1. Standard comma line: Time, Force, Displacement
    raw_line = "1.250, 15420.50, 0.4520\r\n"
    packet = agent.parse_raw_line(raw_line)
    
    assert packet is not None, "Failed to parse valid comma line"
    assert packet["time_sec"] == 1.25, f"Expected time 1.25, got {packet['time_sec']}"
    assert packet["force_n"] == 15420.50, f"Expected force 15420.50, got {packet['force_n']}"
    assert packet["displacement_mm"] == 0.4520, f"Expected disp 0.4520, got {packet['displacement_mm']}"
    
    # 2. Malformed line handling
    assert agent.parse_raw_line("invalid,data\n") is None, "Malformed frame should be rejected"
    print("  -> Phase 1 Signal Parsing: PASSED")

def test_edge_serial_fails_closed_without_pyserial():
    agent = EdgeAgent(use_virtual=False, sample_id="SERIAL-TEST")
    with patch("edge.edge_agent.SERIAL_AVAILABLE", False):
        assert not agent.connect_serial()
    assert not agent.use_virtual, "Physical serial failure must not silently switch to simulated data"
    assert not agent.is_connected
    assert not agent.start_acquisition()
    print("  -> Physical Serial Fail-Closed Behavior: PASSED")

def test_offline_cache_buffer():
    print("[TEST 2] Testing Offline Ingestion Cache Buffer (Phase 1)...")
    cache = OfflineCacheBuffer("test_offline_cache.db")
    cache.clear()
    
    packet = {"sample_id": "TEST_001", "time_sec": 0.5, "force_n": 5000.0, "displacement_mm": 0.12}
    cache.push(packet)
    assert cache.count() == 1, f"Expected 1 item, got {cache.count()}"
    
    peeked = cache.peek(limit=10)
    assert len(peeked) == 1
    assert peeked[0]["sample_id"] == "TEST_001"
    
    cache.remove_ids([peeked[0]["id"]])
    assert cache.count() == 0, "Item was not removed"
    
    # Cleanup test db
    if os.path.exists("test_offline_cache.db"):
        os.remove("test_offline_cache.db")
    print("  -> Phase 1 Offline Ingestion Cache: PASSED")

def test_math_engine():
    print("[TEST 3] Testing Software Math Engine & Fracture Rule (Phase 2 & 3)...")
    cfg = SampleConfig(sample_id="SAMPLE-TEST-01", a_0=50.0, l_0=50.0)
    engine = SoftwareMathEngine(cfg)
    engine.start_test()
    
    # Ingest 10 advancing frames
    # Force rising to peak 25000 N (Stress = 25000/50 = 500 MPa, Strain = 2.5/50 = 0.05)
    for i in range(1, 10):
        t = i * 0.1
        f = i * 2777.77 # Ends near 25,000 N
        d = i * 0.25
        res = engine.ingest_frame(TelemetryPayload(sample_id=cfg.sample_id, time_sec=t, force_n=f, displacement_mm=d))
    
    assert engine.f_max_n > 24000.0, f"Peak force tracking failed: {engine.f_max_n}"
    assert abs(engine.s_u_mpa - (engine.f_max_n / 50.0)) < 0.01, "Su calculation error"
    assert not engine.is_fractured, "Should not be fractured yet"
    
    # Test Automated Fracture Detection Rule:
    # Force drops to exactly 0.0 N after active history > 5 frames
    fracture_res = engine.ingest_frame(TelemetryPayload(sample_id=cfg.sample_id, time_sec=1.1, force_n=0.0, displacement_mm=2.5))
    assert engine.is_fractured, "Fracture detection rule failed to trigger on 0.0 N"
    assert engine.state == "FRACTURED", f"Expected state FRACTURED, got {engine.state}"
    print("  -> Phase 3 Software Math & Automated Fracture Rule: PASSED")

def test_tare_and_software_limits():
    cfg = SampleConfig(sample_id="SAFETY-TEST", a_0=50.0, l_0=50.0, max_load_n=150.0, max_travel_mm=5.0)
    engine = SoftwareMathEngine(cfg)
    engine.start_test()
    engine.ingest_frame(TelemetryPayload(sample_id=cfg.sample_id, time_sec=0.1, force_n=100.0, displacement_mm=1.0))
    engine.tare()
    tared = engine.ingest_frame(TelemetryPayload(sample_id=cfg.sample_id, time_sec=0.2, force_n=120.0, displacement_mm=1.5))
    assert tared.force_n == 20.0
    assert tared.displacement_mm == 0.5
    limited = engine.ingest_frame(TelemetryPayload(sample_id=cfg.sample_id, time_sec=0.3, force_n=300.0, displacement_mm=2.0))
    assert limited.state == "SAFETY_LIMIT"
    assert limited.safety_limit_reason and "Load limit" in limited.safety_limit_reason
    assert not engine.is_running
    print("  -> Displacement Tare & Software Limits: PASSED")

def test_compression_mode_keeps_signed_data_and_magnitude_peak():
    cfg = SampleConfig(sample_id="COMPRESSION-TEST", test_mode="compression", a_0=50.0, l_0=50.0)
    engine = SoftwareMathEngine(cfg)
    engine.start_test()
    for index in range(1, 7):
        result = engine.ingest_frame(TelemetryPayload(
            sample_id=cfg.sample_id,
            time_sec=index * 0.1,
            force_n=-index * 1000.0,
            displacement_mm=-index * 0.1,
        ))
    assert result.force_n < 0
    assert result.stress_mpa < 0
    assert engine.f_max_n == 6000.0
    assert engine.s_u_mpa == 120.0
    review = AIComplianceReviewer.evaluate_compliance(engine.get_full_record())
    assert not review.evaluation_applicable
    assert "manual standard review" in review.standard
    print("  -> Compression Metrics & Review Scope: PASSED")

def test_ai_compliance_reviewer():
    print("[TEST 4] Testing AI Automated Compliance Reviewer (Phase 5)...")
    # Load historical demo02 record (Fe 500 TMT)
    with open("historical/demo02.json", "r") as f:
        record = json.load(f)
        
    comp = AIComplianceReviewer.evaluate_compliance(record)
    assert comp.uts_mpa > 545.0, f"Fe 500 UTS check: {comp.uts_mpa}"
    assert comp.yield_stress_mpa >= 500.0, f"Fe 500 Yield check: {comp.yield_stress_mpa}"
    assert len(comp.evaluation_clauses) == 4, "Expected 4 standard clauses"
    assert len(comp.executive_narrative) > 100, "Executive narrative too short"
    assert len(comp.audit_hash_sha256) == 64, "SHA-256 hash malformed"
    print(f"  -> Phase 5 AI Compliance ({comp.standard}): PASSED [Verdict: {'PASS' if comp.is_compliant else 'FAIL'}]")

def test_pdf_report():
    print("[TEST 5] Testing PDF Report Generator (Phase 5)...")
    with open("historical/demo02.json", "r") as f:
        record = json.load(f)
        
    pdf_bytes = PDFReportGenerator.generate_pdf_report(record, output_path="test_report.pdf")
    assert len(pdf_bytes) > 5000, "PDF too small"
    
    # Inspect with pypdf
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) >= 1, "PDF has no pages"
    meta = reader.metadata
    assert "Custom_Audit_SHA256" in meta or "/Custom_Audit_SHA256" in meta, "Audit hash missing from PDF metadata"
    
    # Cleanup test artifact
    if os.path.exists("test_report.pdf"):
        os.remove("test_report.pdf")
    print("  -> Phase 5 PDF Report Generation: PASSED")

def test_multi_format_exporters():
    print("[TEST 6] Testing Multi-Format Data Exporters (Phase 6)...")
    with open("historical/demo02.json", "r") as f:
        record = json.load(f)
        
    # 1. CSV
    csv_str = MultiFormatExporter.generate_csv(record)
    assert "Time_s,Force_N,Force_kN,Displacement_mm,Stress_MPa" in csv_str
    assert len(csv_str.splitlines()) > 50
    
    # 2. Raw XYT
    xyt_str = MultiFormatExporter.generate_xyt(record)
    assert "COLUMN 1 [X]" in xyt_str
    assert "COLUMN 2 [Y]" in xyt_str
    assert "COLUMN 3 [T]" in xyt_str
    assert len(xyt_str.splitlines()) > 50
    
    # 3. Excel (.xlsx) OpenXML package
    xlsx_bytes = MultiFormatExporter.generate_xlsx(record)
    assert len(xlsx_bytes) > 1000
    # Verify valid zip package with workbook.xml and sheet1.xml
    with zipfile.ZipFile(io.BytesIO(xlsx_bytes), "r") as zf:
        namelist = zf.namelist()
        assert "[Content_Types].xml" in namelist
        assert "xl/workbook.xml" in namelist
        assert "xl/worksheets/sheet1.xml" in namelist
    print("  -> Phase 6 Multi-Format Exporters (.xlsx, .csv, .xyt): PASSED")

if __name__ == "__main__":
    print("=" * 60)
    print("RUNNING UTM PLATFORM AUTOMATED INTEGRATION TESTS")
    print("=" * 60)
    test_edge_telemetry_parsing()
    test_edge_serial_fails_closed_without_pyserial()
    test_offline_cache_buffer()
    test_math_engine()
    test_tare_and_software_limits()
    test_compression_mode_keeps_signed_data_and_magnitude_peak()
    test_ai_compliance_reviewer()
    test_pdf_report()
    test_multi_format_exporters()
    print("=" * 60)
    print("ALL CORE INTEGRATION TESTS PASSED")
    print("=" * 60)
