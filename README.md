# AI-Powered UTM Cloud Hub: Hardware-to-Software Retrofitting Platform

UTM Cloud Hub is a prototype for UTM telemetry, engineering stress-strain calculations, automated compliance review, and test report generation. It has not been validated or certified for production laboratory use or continuous 24/7 operation.

---

## ⚡ Quick Start in VS Code

### 1. Open in VS Code

Open this folder in VS Code, or run in your terminal:

```powershell
code "C:\Users\mayur\OneDrive\Desktop\utm project"
```

### 2. Run Directly with F5

Press **`F5`** (or go to **Run and Debug** in the VS Code sidebar) and select:

- **`🚀 Run AI-Powered UTM Cloud Hub (run.py)`** to start the application server.
- **`🧪 Run UTM Automated Test Suite`** to execute all unit and integration tests.

### 3. Open the Workspace Dashboard

Open your web browser and navigate to:

```
http://127.0.0.1:8000/
```

The application has no default login. For a first local setup, run `python run.py --bootstrap-admin --port 8000`; it prompts for an email and reads the password without echoing it. This creates the account only if it does not already exist. For services/containers, configure `UTM_BOOTSTRAP_ADMIN_EMAIL` and `UTM_BOOTSTRAP_ADMIN_PASSWORD` through the secret manager. No client records are created automatically.

---

## 📁 Project Directory Layout

```
utm project/
├── .vscode/
│   ├── launch.json              # F5 debugging profiles for Server, Tests, & Edge Agent
│   ├── tasks.json               # One-click tasks (Start Server, Run Tests, Open Browser)
│   └── settings.json            # VS Code Python environment & formatting preferences
├── edge/
│   ├── __init__.py
│   ├── edge_agent.py            # Serial telemetry reader (9600 8-N-1 target), UTF-8 line parsing
│   ├── virtual_utm.py           # Realistic physical tensile testing engine (Fe 415, Fe 500, A36, 6061)
│   └── cache_buffer.py          # Offline local SQLite resilience queue for network dropouts
├── backend/
│   ├── __init__.py
│   ├── main.py                  # Asynchronous FastAPI hub with 50Hz WebSockets & REST endpoints
│   ├── schemas.py               # Pydantic validation guard enforcing JSON streaming schema
│   ├── math_engine.py           # Real-time Stress (F/A0), Strain (D/L0), Peak Load, and Fracture rule
│   ├── ai_compliance.py         # AI Compliance Reviewer for IS 1608, IS 1786, and ASTM E8
│   ├── report_generator.py      # PDF test report generator with vector charts & sign-off fields
│   └── exporter.py              # Multi-format exports: Excel (.xlsx), CSV, and raw XYT tables
├── frontend/
│   ├── index.html               # Three-panel desktop architecture
│   ├── styles.css               # Industrial dark-mode styling with glassmorphism & telemetry HUD
│   └── app.js                   # High-performance canvas chart, 4 modes, crosshairs, pacing
├── historical/                  # Pre-loaded benchmark curves for ghost superimposition
│   ├── demo02.json              # Fe 500 TMT benchmark test run (Su = 620 MPa)
│   ├── fe415_benchmark.json     # Fe 415 reference run (Su = 530 MPa)
│   ├── astm_a36.json            # ASTM A36 structural mild steel run (Su = 460 MPa)
│   └── generate_benchmarks.py   # Script to regenerate historical benchmark runs
├── tests/
│   └── test_engine.py           # Core integration test suite
├── run.py                       # Unified system launcher
└── README.md                    # Project documentation
```

---

## 🔬 Core System Specifications

### 1. Hardware, Ports & Serial Communication

- **Serial Input Contract**: Read-only, CR/LF-terminated UTF-8 CSV containing exactly `time_sec,force_n,displacement_mm`; defaults to 9600 8-N-1 but must match the device's approved output configuration.
- **Timeout**: 1 second per serial read.
- **Telemetry Security**: The edge agent requires `UTM_DEVICE_TOKEN`; the server accepts device ingestion only with a matching bearer token.
- **Hardware Boundary**: No valve, servo, crosshead, tare, or emergency-stop commands are implemented. No vendor protocol has been validated. A physical serial open failure stops acquisition; it never falls back to simulated data.
- **Array Index Mapping**:
  $$\text{metrics}[0] = \text{Time (s)}, \quad \text{metrics}[1] = \text{Force (N)}, \quad \text{metrics}[2] = \text{Displacement (mm)}$$
- **High-Refresh Polling**: Configurable between **10Hz and 50Hz** (default 25Hz).

### 2. Software Math Engine

- **Specimen Geometry**: Operator-entered round diameter or flat width/thickness derives $A_0$; measured gauge length $L_0$ is required at test start.
- **Dynamic Engineering Stress**: $\sigma = \frac{F_n}{A_0}\text{ (MPa or N/mm}^2\text{)}$.
- **Dynamic Engineering Strain**: $\epsilon = \frac{D_m}{L_0}\text{ (dimensionless ratio and percentage)}$.
- **Tensile / Compression Peaks**: Keeps signed force/stress for charts while calculating peak strength by force magnitude.
- **Software Load/Travel Limits**: Stop accepting test frames and persist a run when a configured limit is reached. These are software alerts, not machine actuator interlocks.
- **Automated Fracture Detection Rule**: Flags a sustained test-state force drop after an established active history.
- **Live Pacing Calculation**: Velocity derivative calculation rendering live load rate (e.g. `20.826 kN/min`).

For physical telemetry monitoring, the device must already output CR/LF-terminated UTF-8 lines exactly as `elapsed_seconds,force_newtons,displacement_mm`; the default serial settings are 9600 8-N-1. Confirm the OEM protocol and units before connecting. Configure the same high-entropy `UTM_DEVICE_TOKEN` in the server's environment and the edge process environment, start a test in the dashboard, then launch `python edge/edge_agent.py --serial --port COMx --sample-id YOUR_ACTIVE_SAMPLE_ID`. The sample ID must match the active dashboard run. Rejected/expired frames are not cached for later replay. This provides telemetry only, not motion control, tare commands, or hardware stopping.

### 3. Graphical Interface & Interactive Controls

- **Three-Panel Desktop Architecture**:
  - **Panel 1 (Left)**: Tare/start/stop/reset, simulator speed/load-rate targets, software limits, measured specimen setup, saved run search/load/compare/review/delete, and exports.
  - **Panel 2 (Center)**: Dynamic canvas supporting **4 Instant Chart Modes**:
    1. Mode 1: Load (kN) vs Displacement (mm)
    2. Mode 2: Engineering Stress (MPa) vs Displacement (mm)
    3. Mode 3: Engineering Stress (MPa) vs Engineering Strain ($\Delta L/L_0$)
    4. Mode 4: Load (kN) vs Time (s)
    - Interactive Crosshair Point Tracing Tool with live tooltip coordinates.
    - Grid toggle, zoom, custom axis bounds, Shift/middle-drag pan, freeze-display mode, and click-to-pin point tracing.
  - **Panel 3 (Right)**: Oversized Digital Telemetry Readouts (active Load in kN, Displacement in mm), Visual Peak Load Retention Field, Live Pacing Gauge, and AI Compliance Review card.

### 4. Automated Compliance Review & Report Generation

- **Standards Reviewer**: Validates test metrics against **IS 1608**, **IS 1786** (Fe 415, Fe 500, Fe 550), and **ASTM E8 / E8M**.
- **Automated Narrative Construction**: Generates executive metallurgical audit summary.
- **PDF Test Report**: ReportLab/Matplotlib report with stress-strain curves, metadata, and three sign-off fields. It is not a digital signature or accredited certificate:
  - `TESTED BY:` (Operator)
  - `INSPECTED BY:` (Lab Head)
  - `WITNESSED BY:` (Auditor)
- A SHA-256 audit hash is included as metadata; it does not prove identity, calibration, or certification.
- Compression reports explicitly mark tensile-standard review as not applicable and require a controlled compression standard review.
- Saved test runs are stored in SQLite, checkpointed every 100 frames, and can be searched, loaded, compared (up to three), re-analyzed, exported, or deleted.

### 5. Multi-Format Data Exports

- Excel Reports (`.xlsx`) via OpenXML spreadsheet package.
- Lightweight Comma-Separated Values (`.csv`).
- Raw XYT Time-Series Data tables (`.xyt` / `.txt`).

---

## 🧪 Running Automated Tests

Run the test suite directly from VS Code terminal:

```powershell
python tests/test_engine.py
```

Expected output:

```
============================================================
RUNNING UTM PLATFORM AUTOMATED INTEGRATION TESTS
============================================================
[TEST 1] Testing Edge Telemetry Signal Parsing (Phase 1)...
  -> Phase 1 Signal Parsing: PASSED
[TEST 2] Testing Offline Ingestion Cache Buffer (Phase 1)...
  -> Phase 1 Offline Ingestion Cache: PASSED
[TEST 3] Testing Software Math Engine & Fracture Rule (Phase 2 & 3)...
  -> Phase 3 Software Math & Automated Fracture Rule: PASSED
[TEST 4] Testing AI Automated Compliance Reviewer (Phase 5)...
  -> Phase 5 AI Compliance (IS 1786 Grade Fe 500 TMT Steel Reinforcement Bar): PASSED [Verdict: PASS]
[TEST 5] Testing PDF Report Generator (Phase 5)...
  -> Phase 5 PDF Report Generation: PASSED
[TEST 6] Testing Multi-Format Data Exporters (Phase 6)...
  -> Phase 6 Multi-Format Exporters (.xlsx, .csv, .xyt): PASSED
============================================================
ALL CORE INTEGRATION TESTS PASSED
============================================================
```

## Deployment Readiness

This repository is a prototype, not a qualified 24/7 laboratory system. Before client use, complete and verify at least these items:

- Validate serial framing, sensor scaling, load-cell calibration, emergency-stop behavior, and machine-specific specimen dimensions on each real UTM.
- Obtain the exact OEM command/telemetry specification and validate a supported adapter before any motion-control work; the current edge interface is telemetry-only.
- Have a qualified materials/testing engineer verify each implemented standard clause and acceptance threshold against the current controlled standard text and accredited lab procedures.
- Replace in-memory sessions with a shared, durable session/authentication design; use salted password hashing, login throttling, HTTPS, restricted CORS, and authenticated WebSockets.
- Add durable test-run storage, database migrations, scheduled backups, restore drills, retention rules, and export/report integrity verification.
- Deploy under a process supervisor with monitoring, alerting, log rotation, disk-capacity checks, recovery drills, and multi-day soak/load testing.
- Package and pin runtime dependencies, then run the full automated suite in CI. The database/history tests require `pytest`.
- Treat generated PDFs as reports, not accredited certificates. The current hash is metadata and is not a digital signature.
