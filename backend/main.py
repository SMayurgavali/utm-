"""
Phase 2: Asynchronous FastAPI REST Framework & High-Refresh Telemetry Hub
Serves WebSocket live stream, ingestion endpoints, compliance auditing,
export pipelines, and frontend operator workspace dashboard.
"""

import os
import sys
import json
import math
import logging
import hmac
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Response, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from backend.schemas import TelemetryPayload, SampleConfig, LiveTelemetryResponse, ComplianceResult
from backend.math_engine import SoftwareMathEngine
from backend.ai_compliance import AIComplianceReviewer
from backend.report_generator import PDFReportGenerator
from backend.exporter import MultiFormatExporter
from backend.database import DatabaseManager, ensure_seed_data
from backend.config import settings
from backend.auth import issue_session_token, verify_session_token, verify_password

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [FastAPI] %(message)s")
logger = logging.getLogger("FastAPI")

app = FastAPI(
    title="AI-Powered UTM Cloud Hub",
    description="Hardware-to-Software Retrofitting Platform for Universal Testing Machines",
    version="2.4.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core Math Engine instance
math_engine = SoftwareMathEngine()

# Simple session-based authentication for client deployment readiness
SESSION_COOKIE_NAME = "utm_session"
SESSION_TTL_SECONDS = settings.session_ttl_seconds
ACTIVE_SESSIONS: Dict[str, Dict[str, Any]] = {}
DEVICE_TOKEN = settings.device_token
DEVICE_INGEST_PATHS = {"/api/telemetry", "/api/telemetry/batch"}
DB_PATH = settings.database_path
db_manager = DatabaseManager(DB_PATH)
db_manager.init_db()
ensure_seed_data(
    db_manager,
    os.getenv("UTM_BOOTSTRAP_ADMIN_EMAIL") or settings.admin_email,
    os.getenv("UTM_BOOTSTRAP_ADMIN_PASSWORD") or settings.admin_password,
)
current_run_id: Optional[int] = None


def _persist_current_run() -> Optional[int]:
    global current_run_id
    if math_engine.time_series:
        current_run_id = db_manager.save_test_run(math_engine.get_full_record(), current_run_id)
    return current_run_id


def _record_for_run(run_id: Optional[int]) -> Dict[str, Any]:
    if run_id is None:
        return math_engine.get_full_record()
    record = db_manager.get_test_run(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Test run not found")
    record.pop("run_id", None)
    record.pop("created_at", None)
    return record


def _issue_session(username: str, role: str = "admin") -> str:
    token = issue_session_token(username, role)
    payload = verify_session_token(token)
    ACTIVE_SESSIONS[token] = {
        "username": username,
        "role": role,
        "issued_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(seconds=SESSION_TTL_SECONDS)).isoformat(),
        "token_claims": payload,
    }
    return token


def _session_is_valid(token: Optional[str]) -> bool:
    if not token or token not in ACTIVE_SESSIONS:
        verified = verify_session_token(token)
        if verified is None:
            return False
        return True
    session = ACTIVE_SESSIONS.get(token)
    if not session:
        return False
    expires_at = datetime.fromisoformat(session["expires_at"])
    return datetime.utcnow() < expires_at


@app.middleware("http")
async def auth_guard(request: Request, call_next):
    public_paths = [
        "/api/health",
        "/api/auth/login",
        "/api/auth/logout",
        "/api/auth/me",
    ]
    if request.url.path.startswith("/static/"):
        return await call_next(request)
    if request.method == "OPTIONS":
        return await call_next(request)
    if request.url.path in DEVICE_INGEST_PATHS:
        authorization = request.headers.get("Authorization", "")
        supplied_token = authorization.removeprefix("Bearer ")
        has_operator_session = _session_is_valid(request.cookies.get(SESSION_COOKIE_NAME))
        has_device_token = bool(DEVICE_TOKEN) and hmac.compare_digest(supplied_token, DEVICE_TOKEN)
        if not has_operator_session and not has_device_token:
            return JSONResponse(status_code=401, content={"detail": "Valid device bearer token required"})
        return await call_next(request)
    if request.url.path in public_paths or request.url.path == "/":
        return await call_next(request)
    if request.url.path.startswith("/api/"):
        token = request.cookies.get(SESSION_COOKIE_NAME)
        if not _session_is_valid(token):
            return JSONResponse(status_code=401, content={"detail": "Authentication required"})
        if request.url.path.startswith("/api/admin/"):
            session = ACTIVE_SESSIONS.get(token, {})
            if session.get("role") != "admin":
                return JSONResponse(status_code=403, content={"detail": "Admin access required"})
    return await call_next(request)

# Active WebSocket connections pool
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

# ----------------- Health, Auth & Session Endpoints -----------------

@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "service": "utm-cloud-hub",
        "version": app.version,
        "authenticated": False,
        "host": "127.0.0.1",
    }


@app.get("/api/auth/me")
async def get_current_user(request: Request):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not _session_is_valid(token):
        raise HTTPException(status_code=401, detail="Authentication required")
    session = ACTIVE_SESSIONS[token]
    return {"status": "ok", "user": session["username"], "role": session["role"]}


@app.post("/api/auth/login")
async def login_user(request: Request):
    payload = await request.json()
    username = str(payload.get("username", "")).strip().lower()
    password = str(payload.get("password", "")).strip()

    user = db_manager.get_user_by_email(username)
    if user and db_manager.verify_password(username, password):
        token = _issue_session(username, user.get("role", "operator"))
        db_manager.log_audit_event(
            "auth_login_success",
            entity_name="user",
            user_email=username,
            request_path="/api/auth/login",
            details={"role": user.get("role", "operator")},
        )
        response = JSONResponse({"status": "ok", "user": username, "role": user.get("role", "operator")})
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=token,
            httponly=True,
            samesite="lax",
            secure=False,
            path="/",
        )
        return response

    db_manager.log_audit_event(
        "auth_login_failed",
        entity_name="user",
        user_email=username,
        request_path="/api/auth/login",
        details={"reason": "invalid_credentials"},
    )

    raise HTTPException(status_code=401, detail="Invalid username or password")


@app.post("/api/auth/logout")
async def logout_user(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    session = ACTIVE_SESSIONS.get(token, {}) if token else {}
    if session.get("username"):
        db_manager.log_audit_event(
            "auth_logout",
            entity_name="session",
            user_email=session.get("username"),
            request_path="/api/auth/logout",
            details={"role": session.get("role")},
        )
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return {"status": "ok", "message": "Logged out"}


@app.get("/api/admin/overview")
async def admin_overview():
    counts = db_manager.get_total_counts()
    return {
        "status": "ok",
        "counts": counts,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/api/admin/users")
async def list_users():
    return {"status": "ok", "users": db_manager.list_users()}


@app.post("/api/admin/users")
async def create_user(payload: Dict[str, Any]):
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", "")).strip()
    role = str(payload.get("role", "operator")).strip() or "operator"
    full_name = str(payload.get("full_name", "")).strip() or None
    company_name = str(payload.get("company_name", "")).strip() or None

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")
    if db_manager.get_user_by_email(email):
        raise HTTPException(status_code=409, detail="User already exists")

    user_id = db_manager.create_user(email, password, full_name=full_name, role=role, company_name=company_name)
    return {"status": "ok", "user_id": user_id}


@app.get("/api/admin/clients")
async def list_clients():
    return {"status": "ok", "clients": db_manager.list_clients()}


@app.post("/api/admin/clients")
async def create_client(payload: Dict[str, Any]):
    name = str(payload.get("name", "")).strip()
    email = str(payload.get("email", "") or "").strip() or None
    if not name:
        raise HTTPException(status_code=400, detail="Client name is required")
    client_id = db_manager.create_client(name, email)
    return {"status": "ok", "client_id": client_id}


@app.get("/api/reports/history")
async def reports_history():
    return {"status": "ok", "reports": db_manager.list_reports()}


@app.post("/api/reports/save")
async def save_report(payload: Dict[str, Any]):
    client_id = payload.get("client_id")
    sample_id = str(payload.get("sample_id") or "").strip()
    if not sample_id:
        raise HTTPException(status_code=400, detail="sample_id is required")
    if not client_id:
        raise HTTPException(status_code=400, detail="client_id is required")

    report_id = db_manager.save_report(
        client_id=int(client_id),
        sample_id=sample_id,
        material_grade=payload.get("material_grade"),
        standard=payload.get("standard"),
        company_name=payload.get("company_name"),
        operator_name=payload.get("operator_name"),
        status=str(payload.get("status", "PENDING")),
        report_path=payload.get("report_path"),
        details=payload.get("details", {}),
        created_by_user_id=payload.get("created_by_user_id"),
    )
    db_manager.log_audit_event(
        "report_saved",
        entity_name="report",
        user_email=payload.get("operator_name"),
        request_path="/api/reports/save",
        details={"report_id": report_id, "sample_id": sample_id, "client_id": client_id},
    )
    return {"status": "ok", "report_id": report_id}


@app.get("/api/test-runs")
async def list_test_runs(search: str = ""):
    return {"status": "ok", "runs": db_manager.list_test_runs(search.strip())}


@app.get("/api/test-runs/{run_id}")
async def get_test_run(run_id: int):
    record = db_manager.get_test_run(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Test run not found")
    return record


@app.delete("/api/test-runs/{run_id}")
async def delete_test_run(run_id: int):
    if not db_manager.delete_test_run(run_id):
        raise HTTPException(status_code=404, detail="Test run not found")
    return {"status": "deleted", "run_id": run_id}


@app.get("/api/test-runs/{run_id}/review", response_model=ComplianceResult)
async def review_saved_test_run(run_id: int):
    record = db_manager.get_test_run(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Test run not found")
    return AIComplianceReviewer.evaluate_compliance(record)

# ----------------- REST Ingestion & Control Endpoints -----------------

@app.post("/api/telemetry", response_model=LiveTelemetryResponse)
async def ingest_telemetry_frame(payload: TelemetryPayload):
    """
    Pydantic Validation Guard: Ingests incoming telemetry frame:
    { "sample_id": "STRING", "time_sec": FLOAT, "force_n": FLOAT, "displacement_mm": FLOAT }
    Calculates stress, strain, f_max, pacing, and checks fracture rule.
    """
    if not math_engine.is_running:
        raise HTTPException(status_code=409, detail="No test is running or a stop condition has been reached")
    if payload.sample_id != math_engine.config.sample_id:
        raise HTTPException(status_code=409, detail="Telemetry sample ID does not match the active test")
    previous_safety_reason = math_engine.safety_limit_reason
    response = math_engine.ingest_frame(payload)
    
    # Broadcast to live WebSocket clients
    await manager.broadcast({
        "type": "TELEMETRY_UPDATE",
        "data": response.model_dump()
    })
    
    if response.is_fractured and response.state == "FRACTURED":
        await manager.broadcast({
            "type": "FRACTURE_DETECTED",
            "message": "Automated Fracture Detection: Force dropped to 0.0 N after active load sequence.",
            "data": response.model_dump()
        })
    if response.state == "SAFETY_LIMIT" and previous_safety_reason is None:
        await manager.broadcast({
            "type": "SAFETY_LIMIT_REACHED",
            "message": response.safety_limit_reason,
            "hardware_action": "none",
            "data": response.model_dump(),
        })
    if response.state in {"FRACTURED", "SAFETY_LIMIT"}:
        _persist_current_run()
    elif response.total_data_points % 100 == 0:
        _persist_current_run()
        
    return response

@app.post("/api/telemetry/batch")
async def ingest_telemetry_batch(payloads: List[TelemetryPayload]):
    """Batch ingestion endpoint for flushing offline local cache queue routines."""
    if not payloads:
        return {"status": "ok", "ingested": 0}
        
    latest_response = None
    ingested_count = 0
    for frame in payloads:
        if not math_engine.is_running:
            if ingested_count == 0:
                raise HTTPException(status_code=409, detail="No test is running or a stop condition has been reached")
            break
        if frame.sample_id != math_engine.config.sample_id:
            raise HTTPException(status_code=409, detail="Telemetry sample ID does not match the active test")
        latest_response = math_engine.ingest_frame(frame)
        ingested_count += 1
        
    if latest_response:
        await manager.broadcast({
            "type": "TELEMETRY_BATCH_SYNC",
            "data": latest_response.model_dump(),
            "batch_count": ingested_count
        })
        if latest_response.state in {"FRACTURED", "SAFETY_LIMIT"}:
            _persist_current_run()
        elif latest_response.total_data_points % 100 == 0:
            _persist_current_run()
        
    return {"status": "ok", "ingested": ingested_count}

@app.get("/api/telemetry/live", response_model=LiveTelemetryResponse)
async def get_live_telemetry():
    """Returns the latest calculated telemetry state."""
    full = math_engine.get_full_record()
    t = full["time_series"][-1] if full["time_series"] else 0.0
    f = full["force_series_n"][-1] if full["force_series_n"] else 0.0
    d = full["disp_series_mm"][-1] if full["disp_series_mm"] else 0.0
    s = full["stress_series_mpa"][-1] if full["stress_series_mpa"] else 0.0
    sr = full["strain_series_ratio"][-1] if full["strain_series_ratio"] else 0.0
    sp = full["strain_series_pct"][-1] if full["strain_series_pct"] else 0.0
    
    return LiveTelemetryResponse(
        sample_id=math_engine.config.sample_id,
        time_sec=round(t, 4),
        force_n=round(f, 2),
        force_kn=round(f / 1000.0, 4),
        displacement_mm=round(d, 4),
        stress_mpa=round(s, 2),
        strain_ratio=round(sr, 6),
        strain_pct=round(sp, 4),
        f_max_n=round(math_engine.f_max_n, 2),
        f_max_kn=round(math_engine.f_max_n / 1000.0, 4),
        d_peak_mm=round(math_engine.d_peak_mm, 4),
        s_u_mpa=round(math_engine.s_u_mpa, 2),
        load_rate_kn_min=round(math_engine.load_rate_kn_min, 3),
        disp_rate_mm_min=round(math_engine.disp_rate_mm_min, 3),
        is_fractured=math_engine.is_fractured,
        safety_limit_reason=math_engine.safety_limit_reason,
        state=math_engine.state,
        total_data_points=len(full["time_series"])
    )

@app.get("/api/telemetry/full")
async def get_full_record():
    """Returns complete record of current active test."""
    return math_engine.get_full_record()

@app.post("/api/test/start")
async def start_test(config: SampleConfig):
    global current_run_id
    """Initializes new testing run with specified specimen profiling constants."""
    required_fields = {
        "sample_id", "material_grade", "standard", "geometry", "width_mm",
        "a_0", "l_0", "control_mode", "max_load_n", "max_travel_mm",
    }
    missing_fields = required_fields - config.model_fields_set
    if missing_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Required test setup fields: {', '.join(sorted(missing_fields))}",
        )
    if not config.sample_id.strip():
        raise HTTPException(status_code=400, detail="Sample ID is required")
    if config.max_load_n is None or config.max_travel_mm is None:
        raise HTTPException(status_code=400, detail="Maximum load and travel limits are required")
    if config.data_source == "serial" and not DEVICE_TOKEN:
        raise HTTPException(status_code=503, detail="Read-only serial ingestion is not configured on this server")
    if config.width_mm is None:
        raise HTTPException(status_code=400, detail="Specimen width or diameter is required")
    if config.geometry == "round":
        calculated_area = math.pi * (config.width_mm / 2) ** 2
    else:
        if config.thickness_mm is None:
            raise HTTPException(status_code=400, detail="Flat specimen thickness is required")
        calculated_area = config.width_mm * config.thickness_mm
    if not math.isclose(config.a_0, calculated_area, rel_tol=1e-4):
        raise HTTPException(status_code=400, detail="Cross-section area does not match specimen dimensions")
    if config.control_mode == "crosshead_speed" and config.crosshead_speed_mm_min is None:
        raise HTTPException(status_code=400, detail="Crosshead speed target is required")
    if config.control_mode == "load_rate" and config.load_rate_setpoint_kn_min is None:
        raise HTTPException(status_code=400, detail="Load-rate target is required")
    current_run_id = None
    math_engine.start_test(config)
    await manager.broadcast({
        "type": "TEST_STARTED",
        "config": config.model_dump()
    })
    return {"status": "started", "config": config.model_dump()}

@app.post("/api/test/stop")
async def stop_test():
    """Halts tracking processes."""
    math_engine.stop_test()
    run_id = _persist_current_run()
    await manager.broadcast({
        "type": "TEST_STOPPED",
        "state": math_engine.state
    })
    return {"status": "stopped", "state": math_engine.state, "run_id": run_id}

@app.post("/api/test/tare")
async def tare_load():
    """Tares active load cell."""
    math_engine.tare()
    await manager.broadcast({
        "type": "LOAD_TARED",
        "offset": math_engine.tare_offset_n
    })
    return {"status": "tared", "offset": math_engine.tare_offset_n}

# ----------------- AI Compliance & Reporting -----------------

@app.get("/api/compliance/review", response_model=ComplianceResult)
async def review_compliance(run_id: Optional[int] = None):
    """Target Compliance Code Reviewer: IS 1608, IS 1786, ASTM E8."""
    record = _record_for_run(run_id)
    return AIComplianceReviewer.evaluate_compliance(record)

@app.get("/api/report/pdf")
async def download_certified_pdf(run_id: Optional[int] = None):
    """Generates a PDF test report with vector graphics and three sign-off fields."""
    record = _record_for_run(run_id)
    pdf_bytes = PDFReportGenerator.generate_pdf_report(record)
    sample_id = record.get("config", {}).get("sample_id", "UTM-SAMPLE")
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=UTM_Report_{sample_id}.pdf"
        }
    )

# ----------------- Multi-Format Data Exports -----------------

@app.get("/api/export/csv")
async def export_csv(run_id: Optional[int] = None):
    """Export Lightweight Comma-Separated Values (.csv)."""
    record = _record_for_run(run_id)
    csv_str = MultiFormatExporter.generate_csv(record)
    sample_id = record.get("config", {}).get("sample_id", "UTM-SAMPLE")
    return Response(
        content=csv_str,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={sample_id}_telemetry.csv"}
    )

@app.get("/api/export/xyt")
async def export_xyt(run_id: Optional[int] = None):
    """Export Raw XYT Time-Series Data tables (.xyt)."""
    record = _record_for_run(run_id)
    xyt_str = MultiFormatExporter.generate_xyt(record)
    sample_id = record.get("config", {}).get("sample_id", "UTM-SAMPLE")
    return Response(
        content=xyt_str,
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename={sample_id}_raw.xyt"}
    )

@app.get("/api/export/xlsx")
async def export_xlsx(run_id: Optional[int] = None):
    """Export Excel Workbook (.xlsx) OpenXML package."""
    record = _record_for_run(run_id)
    xlsx_bytes = MultiFormatExporter.generate_xlsx(record)
    sample_id = record.get("config", {}).get("sample_id", "UTM-SAMPLE")
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={sample_id}_report.xlsx"}
    )

# ----------------- Historical Matrix Superimposition -----------------

@app.get("/api/historical")
async def list_historical_records():
    """Lists optional reference curves, not customer test history."""
    if os.getenv("UTM_ENABLE_REFERENCE_CURVES") != "1":
        return []
    hist_dir = Path("historical")
    if not hist_dir.exists():
        return []
    
    records = []
    for f in hist_dir.glob("*.json"):
        try:
            with open(f, "r") as fp:
                data = json.load(fp)
                cfg = data.get("config", {})
                records.append({
                    "id": f.stem,
                    "filename": f.name,
                    "sample_id": cfg.get("sample_id", f.stem),
                    "material_grade": cfg.get("material_grade", "UNKNOWN"),
                    "standard": cfg.get("standard", "IS 1786"),
                    "su_mpa": data.get("s_u_mpa", 0.0),
                    "data_points": data.get("data_count", len(data.get("time_series", [])))
                })
        except Exception:
            continue
    return records

@app.get("/api/historical/{record_id}")
async def get_historical_record(record_id: str):
    """Fetches full historical record for superimposing on active screen."""
    if os.getenv("UTM_ENABLE_REFERENCE_CURVES") != "1":
        raise HTTPException(status_code=404, detail="Reference curves are disabled")
    path = Path("historical") / f"{record_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Historical record not found")
    with open(path, "r") as fp:
        return json.load(fp)

# ----------------- WebSocket Live Stream -----------------

@app.websocket("/ws/telemetry")
async def websocket_telemetry_stream(websocket: WebSocket):
    """High-frequency real-time WebSocket connection."""
    await manager.connect(websocket)
    # Send current state immediately on connect
    full = math_engine.get_full_record()
    await websocket.send_json({
        "type": "INITIAL_STATE",
        "config": math_engine.config.model_dump(),
        "state": math_engine.state,
        "is_fractured": math_engine.is_fractured,
        "f_max_n": math_engine.f_max_n,
        "d_peak_mm": math_engine.d_peak_mm,
        "s_u_mpa": math_engine.s_u_mpa,
        "total_data_points": len(full["time_series"])
    })
    try:
        while True:
            data = await websocket.receive_text()
            # Client ping/pong or control commands
            msg = json.loads(data)
            if msg.get("action") == "PING":
                await websocket.send_json({"type": "PONG"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

# ----------------- Frontend Static Mount -----------------

frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def serve_index():
        index_file = frontend_dir / "index.html"
        if index_file.exists():
            with open(index_file, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        return HTMLResponse("<h1>Frontend loading...</h1>")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=False)
