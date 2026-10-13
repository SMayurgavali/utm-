import json
import os
import sqlite3
from pathlib import Path

from backend.database import DatabaseManager, ensure_seed_data


def test_database_has_no_demo_records_and_supports_explicit_admin_bootstrap(tmp_path):
    db_path = tmp_path / "utm_clean.db"
    db = DatabaseManager(str(db_path))
    db.init_db()
    ensure_seed_data(db)

    conn = sqlite3.connect(str(db_path))
    assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0] == 0
    conn.close()

    ensure_seed_data(db, "admin@example.com", "configured-password")
    user = db.get_user_by_email("admin@example.com")
    assert user["role"] == "admin"
    assert db.verify_password("admin@example.com", "configured-password")


def test_report_history_can_be_saved(tmp_path):
    db_path = tmp_path / "utm_reports.db"
    db = DatabaseManager(str(db_path))
    db.init_db()
    ensure_seed_data(db, "admin@example.com", "configured-password")

    admin_id = db.get_user_by_email("admin@example.com")["id"]
    client_id = db.create_client("Acme Labs", "client@acme.com")
    report_id = db.save_report(
        client_id=client_id,
        sample_id="CLIENT-REPORT-001",
        material_grade="IS_1786_FE500",
        standard="IS 1786",
        operator_name="Operator One",
        company_name="Acme Labs",
        status="PASS",
        report_path="/tmp/report.pdf",
        details={"score": 99.2},
        created_by_user_id=admin_id,
    )

    history = db.list_reports()
    assert any(item["id"] == report_id for item in history)
    assert any(item["sample_id"] == "CLIENT-REPORT-001" for item in history)


def test_test_run_history_can_be_loaded_and_deleted(tmp_path):
    db = DatabaseManager(str(tmp_path / "test_runs.db"))
    db.init_db()
    run_id = db.save_test_run({
        "config": {"sample_id": "UTM-2026-001", "material_grade": "FE500", "standard": "IS 1786"},
        "state": "FRACTURED",
        "data_count": 2,
        "time_series": [0.1, 0.2],
        "force_series_n": [100.0, 200.0],
        "force_series_kn": [0.1, 0.2],
        "disp_series_mm": [0.01, 0.02],
        "stress_series_mpa": [2.0, 4.0],
        "strain_series_ratio": [0.0002, 0.0004],
        "strain_series_pct": [0.02, 0.04],
    })

    assert db.list_test_runs("2026-001")[0]["id"] == run_id
    assert db.get_test_run(run_id)["force_series_n"] == [100.0, 200.0]
    assert db.delete_test_run(run_id)
    assert db.get_test_run(run_id) is None
