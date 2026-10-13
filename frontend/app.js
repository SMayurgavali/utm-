/**
 * AI-Powered UTM Cloud Hub — Real-Time Frontend Operator Workspace
 * High-Refresh Multi-Mode Canvas Chart, Crosshair Point Tracing,
 * 4 Graph Modes, Superimpose Historical Overlay, and Live Telemetry HUD.
 */

// Application State
const state = {
  currentMode: 1, // 1: Load vs Disp, 2: Stress vs Disp, 3: Stress vs Strain, 4: Load vs Time
  gridEnabled: true,
  autoScale: true,
  zoomLevel: 1.0,
  zoomOffsetX: 0,
  zoomOffsetY: 0,
  displayFrozen: false,
  latestTelemetry: null,
  axisBounds: null,
  panStart: null,
  hoveredPointIndex: null,
  pinnedPointIndex: null,
  
  // Active Test Data Series
  timeSeries: [],
  forceSeriesN: [],
  forceSeriesKn: [],
  dispSeriesMm: [],
  stressSeriesMpa: [],
  strainSeriesRatio: [],
  strainSeriesPct: [],
  
  fMaxKn: 0.0,
  fMaxN: 0.0,
  dPeakMm: 0.0,
  sUMpa: 0.0,
  peakIndex: -1,
  
  isFractured: false,
  testStatus: "IDLE", // IDLE, RUNNING, FRACTURED, STOPPED
  
  // Historical Superimpose Track
  overlayEnabled: true,
  historicalData: null,
  comparisonRuns: [],
  activeRunId: null,
  
  // Interactive Crosshair Point Tracer
  cursorX: null,
  cursorY: null,
  hoveredPoint: null,

  // Polling / Client Virtual Runner
  virtualTimer: null
};

// DOM References
const loginOverlay = document.getElementById("loginOverlay");
const loginForm = document.getElementById("loginForm");
const loginStatus = document.getElementById("loginStatus");
const canvas = document.getElementById("utmChartCanvas");
const overlayCanvas = document.getElementById("overlayCanvas");
const canvasWrapper = document.getElementById("canvasWrapper");
const ctx = canvas.getContext("2d");
const oCtx = overlayCanvas.getContext("2d");

const tooltip = document.getElementById("crosshairTooltip");
const tooltipHeader = document.getElementById("tooltipHeader");
const tooltipXLabel = document.getElementById("tooltipXLabel");
const tooltipXVal = document.getElementById("tooltipXVal");
const tooltipYLabel = document.getElementById("tooltipYLabel");
const tooltipYVal = document.getElementById("tooltipYVal");
const tooltipSecRow = document.getElementById("tooltipSecRow");
const tooltipSecVal = document.getElementById("tooltipSecVal");
const coordReadout = document.getElementById("coordReadout");
const fractureBanner = document.getElementById("fractureBanner");

// Digital Readouts
const valLoadKn = document.getElementById("valLoadKn");
const valLoadN = document.getElementById("valLoadN");
const valDispMm = document.getElementById("valDispMm");
const valDispRate = document.getElementById("valDispRate");
const valFmaxKn = document.getElementById("valFmaxKn");
const valFmaxN = document.getElementById("valFmaxN");
const valDpeakMm = document.getElementById("valDpeakMm");
const valSuMpa = document.getElementById("valSuMpa");
const valYoungsModulus = document.getElementById("valYoungsModulus");
const valProofStress = document.getElementById("valProofStress");
const valElongation = document.getElementById("valElongation");
const pacingText = document.getElementById("pacingText");
const pacingFill = document.getElementById("pacingFill");
const valStressMpa = document.getElementById("valStressMpa");
const valStrainPct = document.getElementById("valStrainPct");
const valTimeSec = document.getElementById("valTimeSec");
const testStateBadge = document.getElementById("testStateBadge");

// Buttons & Controls
const btnTare = document.getElementById("btnTare");
const btnStart = document.getElementById("btnStart");
const btnStop = document.getElementById("btnStop");
const btnClose = document.getElementById("btnClose");
const btnToggleGrid = document.getElementById("btnToggleGrid");
const btnToggleAutoScale = document.getElementById("btnToggleAutoScale");
const btnZoomIn = document.getElementById("btnZoomIn");
const btnZoomOut = document.getElementById("btnZoomOut");
const btnResetZoom = document.getElementById("btnResetZoom");
const btnFreezeScreen = document.getElementById("btnFreezeScreen");
const btnApplyAxisLimits = document.getElementById("btnApplyAxisLimits");
const axisMinX = document.getElementById("axisMinX");
const axisMaxX = document.getElementById("axisMaxX");
const axisMinY = document.getElementById("axisMinY");
const axisMaxY = document.getElementById("axisMaxY");

// Inputs & Selects
const hardwareSource = document.getElementById("hardwareSource");
const virtualMaterial = document.getElementById("virtualMaterial");
const virtualMaterialRow = document.getElementById("virtualMaterialRow");
const hardwareSafetyNote = document.getElementById("hardwareSafetyNote");
const controlMode = document.getElementById("controlMode");
const crossheadSpeedInput = document.getElementById("crossheadSpeed");
const loadRateTargetInput = document.getElementById("loadRateTarget");
const loadRateUnit = document.getElementById("loadRateUnit");
const maxLoadLimitInput = document.getElementById("maxLoadLimit");
const maxTravelLimitInput = document.getElementById("maxTravelLimit");
const pollingFreq = document.getElementById("pollingFreq");
const pollingFreqVal = document.getElementById("pollingFreqVal");
const sampleIdInput = document.getElementById("sampleId");
const testModeSelect = document.getElementById("testMode");
const companyNameInput = document.getElementById("companyName");
const systemSerialNumberInput = document.getElementById("systemSerialNumber");
const operatorNameInput = document.getElementById("operatorName");
const inspectorNameInput = document.getElementById("inspectorName");
const witnessNameInput = document.getElementById("witnessName");
const standardSelect = document.getElementById("standardSelect");
const areaA0Input = document.getElementById("areaA0");
const lengthL0Input = document.getElementById("lengthL0");
const geometryType = document.getElementById("geometryType");
const specimenWidthInput = document.getElementById("specimenWidth");
const specimenThicknessInput = document.getElementById("specimenThickness");
const specimenThicknessField = document.getElementById("specimenThicknessField");
const historicalSelect = document.getElementById("historicalSelect");
const toggleHistorical = document.getElementById("toggleHistorical");
const testRunSearch = document.getElementById("testRunSearch");
const testRunList = document.getElementById("testRunList");
const btnRefreshRuns = document.getElementById("btnRefreshRuns");
const btnLoadRun = document.getElementById("btnLoadRun");
const btnCompareRuns = document.getElementById("btnCompareRuns");
const btnReviewRun = document.getElementById("btnReviewRun");
const btnDeleteRun = document.getElementById("btnDeleteRun");

// Mode Tabs
const modeTabs = document.querySelectorAll(".mode-tab");

// Exports
const btnDownloadPdf = document.getElementById("btnDownloadPdf");
const btnDownloadXlsx = document.getElementById("btnDownloadXlsx");
const btnDownloadCsv = document.getElementById("btnDownloadCsv");
const btnDownloadXyt = document.getElementById("btnDownloadXyt");

// AI Compliance Elements
const aiAuditBadge = document.getElementById("aiAuditBadge");
const aiStdTitle = document.getElementById("aiStdTitle");
const complianceChecklist = document.getElementById("complianceChecklist");
const aiNarrativeSnippet = document.getElementById("aiNarrativeSnippet");

// Initialize Canvas Size
function resizeCanvas() {
  const rect = canvasWrapper.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  overlayCanvas.width = rect.width * dpr;
  overlayCanvas.height = rect.height * dpr;
  ctx.scale(dpr, dpr);
  oCtx.scale(dpr, dpr);
  renderChart();
}

window.addEventListener("resize", resizeCanvas);

async function checkAuth() {
  try {
    const res = await fetch("/api/auth/me", { cache: "no-store" });
    if (!res.ok) {
      throw new Error("unauthorized");
    }
    loginOverlay.classList.add("hidden");
    return true;
  } catch (error) {
    loginOverlay.classList.remove("hidden");
    return false;
  }
}

async function handleLoginSubmit(event) {
  event.preventDefault();
  const formData = new FormData(loginForm);
  const payload = {
    username: formData.get("username"),
    password: formData.get("password")
  };

  try {
    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      throw new Error("Invalid username or password");
    }

    loginStatus.textContent = "";
    loginOverlay.classList.add("hidden");
    initWebSocket();
    await populateHistoricalRecords();
    await refreshSavedTestRuns();
    loadHistoricalRecord("none");
  } catch (error) {
    loginStatus.textContent = error.message || "Authentication failed";
  }
}

loginForm.addEventListener("submit", handleLoginSubmit);

// ----------------- WebSocket Connection -----------------
let ws = null;
function initWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws/telemetry`;
  
  ws = new WebSocket(wsUrl);
  
  ws.onopen = () => {
    document.getElementById("cloudPill").className = "status-pill ws-connected";
    document.getElementById("wsStatusText").innerText = `SYNCED (${pollingFreq.value}Hz)`;
  };
  
  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      if (msg.type === "TELEMETRY_UPDATE" || msg.type === "TELEMETRY_BATCH_SYNC") {
        handleIncomingTelemetry(msg.data);
      } else if (msg.type === "SAFETY_LIMIT_REACHED") {
        handleIncomingTelemetry(msg.data);
        fractureBanner.classList.remove("hidden");
        fractureBanner.querySelector(".fracture-title").innerText = "SOFTWARE LIMIT EXCEEDED";
        fractureBanner.querySelector(".fracture-desc").innerText = `${msg.message}. This application cannot stop the physical machine; use its verified hardware stop.`;
        refreshSavedTestRuns();
      } else if (msg.type === "FRACTURE_DETECTED") {
        handleIncomingTelemetry(msg.data);
        triggerFractureAlert();
        refreshSavedTestRuns();
      } else if (msg.type === "INITIAL_STATE") {
        if (msg.config && msg.state !== "IDLE") {
          sampleIdInput.value = msg.config.sample_id;
          areaA0Input.value = msg.config.a_0;
          lengthL0Input.value = msg.config.l_0;
          geometryType.value = msg.config.geometry || "";
          specimenWidthInput.value = msg.config.width_mm || "";
          specimenThicknessInput.value = msg.config.thickness_mm || "";
          updateGeometryArea();
        }
      }
    } catch (e) {
      console.error("WS Parse error:", e);
    }
  };
  
  ws.onclose = () => {
    document.getElementById("cloudPill").className = "status-pill";
    document.getElementById("wsStatusText").innerText = "OFFLINE (RECONNECTING)";
    setTimeout(initWebSocket, 2000);
  };
}

// ----------------- Incoming Telemetry Processing -----------------
function handleIncomingTelemetry(data) {
  // Append to active arrays
  state.timeSeries.push(data.time_sec);
  state.forceSeriesN.push(data.force_n);
  state.forceSeriesKn.push(data.force_kn);
  state.dispSeriesMm.push(data.displacement_mm);
  state.stressSeriesMpa.push(data.stress_mpa);
  state.strainSeriesRatio.push(data.strain_ratio);
  state.strainSeriesPct.push(data.strain_pct);

  state.fMaxKn = data.f_max_kn;
  state.fMaxN = data.f_max_n;
  state.dPeakMm = data.d_peak_mm;
  state.sUMpa = data.s_u_mpa;
  state.isFractured = data.is_fractured;
  state.testStatus = data.state;

  if (state.fMaxKn > 0) {
    state.peakIndex = state.forceSeriesKn.indexOf(state.fMaxKn);
  }

  state.latestTelemetry = data;
  if (state.displayFrozen) return;
  renderTelemetryDisplay(data);
}

function renderTelemetryDisplay(data) {
  // Update Oversized Digital Readouts
  valLoadKn.innerText = data.force_kn.toFixed(3);
  valLoadN.innerText = `${data.force_n.toFixed(1)} N`;
  valDispMm.innerText = data.displacement_mm.toFixed(4);
  valDispRate.innerText = `${data.disp_rate_mm_min.toFixed(3)} mm/min`;

  // Visual Peak Load Retention Field
  valFmaxKn.innerText = data.f_max_kn.toFixed(3);
  valFmaxN.innerText = `${data.f_max_n.toFixed(0)} N`;
  valDpeakMm.innerText = data.d_peak_mm.toFixed(4);
  valSuMpa.innerText = data.s_u_mpa.toFixed(2);

  // Live Pacing Gauge Component
  pacingText.innerText = `Load Rate: ${data.load_rate_kn_min.toFixed(3)} kN/min`;
  // Standard target range is ~20 kN/min, scale 0 to 40
  const pacingPct = Math.min(100, Math.max(0, (data.load_rate_kn_min / 40.0) * 100));
  pacingFill.style.width = `${pacingPct}%`;

  // Dynamic Stress & Strain HUD
  valStressMpa.innerText = `${data.stress_mpa.toFixed(2)} MPa`;
  valStrainPct.innerText = `${data.strain_pct.toFixed(3)} %`;
  valTimeSec.innerText = `${data.time_sec.toFixed(2)} s`;

  // Test state badge
  updateStateBadge(data.state);

  if (data.is_fractured) {
    triggerFractureAlert();
  }

  // Trigger high-refresh canvas render
  requestAnimationFrame(renderChart);
}

function updateStateBadge(st) {
  testStateBadge.className = `test-state-badge ${st.toLowerCase()}`;
  testStateBadge.innerText = `STATE: ${st}`;
}

function triggerFractureAlert() {
  fractureBanner.classList.remove("hidden");
  updateStateBadge("FRACTURED");
  fetchAIComplianceReview();
}

// ----------------- AI Compliance Fetcher -----------------
async function fetchAIComplianceReview(runId = null) {
  try {
    const endpoint = runId ? `/api/compliance/review?run_id=${encodeURIComponent(runId)}` : "/api/compliance/review";
    const res = await fetch(endpoint);
    if (!res.ok) return;
    const comp = await res.json();

    aiStdTitle.innerText = `Standard: ${comp.standard}`;
    valYoungsModulus.innerText = `${comp.youngs_modulus_gpa.toFixed(1)} GPa`;
    valProofStress.innerText = `${comp.yield_stress_mpa.toFixed(2)} MPa`;
    valElongation.innerText = `${comp.elongation_pct.toFixed(2)} %`;
    aiAuditBadge.className = `ai-audit-badge ${!comp.evaluation_applicable ? "na" : comp.is_compliant ? "pass" : "fail"}`;
    aiAuditBadge.innerText = !comp.evaluation_applicable ? "NOT EVALUATED" : comp.is_compliant ? "REVIEW PASS" : "NON-COMPLIANT";

    // Build checklist
    complianceChecklist.innerHTML = comp.evaluation_clauses.map(c => `
      <li class="chk-item ${c.pass ? 'pass' : 'fail'}">
        <span class="chk-dot">●</span>
        <span class="chk-text">${c.clause}: <strong>${c.measured}</strong> (${c.required_threshold})</span>
      </li>
    `).join("");

    aiNarrativeSnippet.innerText = comp.executive_narrative;
  } catch (err) {
    console.error("AI Compliance fetch error:", err);
  }
}

// ----------------- Historical Data Overlay -----------------
async function loadHistoricalRecord(recordId) {
  if (!recordId || recordId === "none") {
    state.historicalData = null;
    state.overlayEnabled = false;
    document.getElementById("toggleHistorical").checked = false;
    document.getElementById("ghostLegendItem").style.display = "none";
    document.getElementById("ghostCurveLegend").innerText = "Historical Overlay: Disabled";
    renderChart();
    return;
  }
  
  try {
    const res = await fetch(`/api/historical/${recordId}`);
    if (res.ok) {
      state.historicalData = await res.json();
      document.getElementById("ghostCurveLegend").innerText = `Historical Superimpose: ${recordId}`;
      document.getElementById("ghostLegendItem").style.display = "flex";
      renderChart();
    }
  } catch (e) {
    console.error("Error loading historical track:", e);
  }
}

async function populateHistoricalRecords() {
  try {
    const response = await fetch("/api/historical");
    if (!response.ok) return;
    const records = await response.json();
    for (const record of records) {
      const option = document.createElement("option");
      option.value = record.id;
      option.textContent = `REFERENCE ONLY - ${record.material_grade} (${record.sample_id})`;
      historicalSelect.appendChild(option);
    }
  } catch (error) {
    console.error("Reference curves unavailable:", error);
  }
}

async function refreshSavedTestRuns() {
  const query = encodeURIComponent(testRunSearch.value.trim());
  const response = await fetch(`/api/test-runs?search=${query}`);
  if (!response.ok) return;
  const { runs } = await response.json();
  testRunList.replaceChildren();
  for (const run of runs) {
    const option = document.createElement("option");
    option.value = run.id;
    option.textContent = `${run.created_at} | ${run.sample_id} | ${run.status}`;
    testRunList.appendChild(option);
  }
}

function selectedRunIds() {
  return Array.from(testRunList.selectedOptions, option => option.value);
}

function recordToChartData(record) {
  return {
    timeSeries: record.time_series || [],
    forceSeriesKn: record.force_series_kn || [],
    dispSeriesMm: record.disp_series_mm || [],
    stressSeriesMpa: record.stress_series_mpa || [],
    strainSeriesPct: record.strain_series_pct || []
  };
}

async function fetchSavedRun(runId) {
  const response = await fetch(`/api/test-runs/${encodeURIComponent(runId)}`);
  if (!response.ok) throw new Error("Could not load saved test run");
  return response.json();
}

async function loadSelectedTestRun() {
  if (state.testStatus === "RUNNING") {
    alert("Stop the active test before loading a saved run.");
    return;
  }
  const runId = selectedRunIds()[0];
  if (!runId) return;
  try {
    const record = await fetchSavedRun(runId);
    const config = record.config || {};
    state.activeRunId = record.run_id;
    state.timeSeries = record.time_series || [];
    state.forceSeriesN = record.force_series_n || [];
    state.forceSeriesKn = record.force_series_kn || [];
    state.dispSeriesMm = record.disp_series_mm || [];
    state.stressSeriesMpa = record.stress_series_mpa || [];
    state.strainSeriesRatio = record.strain_series_ratio || [];
    state.strainSeriesPct = record.strain_series_pct || [];
    state.fMaxN = record.f_max_n || 0;
    state.fMaxKn = record.f_max_kn || 0;
    state.dPeakMm = record.d_peak_mm || 0;
    state.sUMpa = record.s_u_mpa || 0;
    state.peakIndex = state.forceSeriesKn.indexOf(Math.max(...state.forceSeriesKn));
    state.isFractured = Boolean(record.is_fractured);
    state.testStatus = record.state || "STOPPED";
    state.latestTelemetry = null;
    sampleIdInput.value = config.sample_id || "";
    testModeSelect.value = config.test_mode || "tension";
    geometryType.value = config.geometry || "";
    specimenWidthInput.value = config.width_mm || "";
    specimenThicknessInput.value = config.thickness_mm || "";
    updateGeometryArea();
    areaA0Input.value = config.a_0 || "";
    lengthL0Input.value = config.l_0 || "";
    standardSelect.value = config.standard || "";
    virtualMaterial.value = config.material_grade || "";
    companyNameInput.value = config.company_name || "";
    systemSerialNumberInput.value = config.system_serial_number || "";
    operatorNameInput.value = config.operator_name || "";
    inspectorNameInput.value = config.inspector_name || "";
    witnessNameInput.value = config.witness_name || "";
    valLoadKn.innerText = (state.forceSeriesKn.at(-1) || 0).toFixed(3);
    valLoadN.innerText = `${(state.forceSeriesN.at(-1) || 0).toFixed(1)} N`;
    valDispMm.innerText = (state.dispSeriesMm.at(-1) || 0).toFixed(4);
    valFmaxKn.innerText = state.fMaxKn.toFixed(3);
    valFmaxN.innerText = `${state.fMaxN.toFixed(0)} N`;
    valDpeakMm.innerText = state.dPeakMm.toFixed(4);
    valSuMpa.innerText = state.sUMpa.toFixed(2);
    valTimeSec.innerText = `${(state.timeSeries.at(-1) || 0).toFixed(2)} s`;
    updateStateBadge(state.testStatus);
    renderChart();
    await fetchAIComplianceReview(record.run_id);
  } catch (error) {
    alert(error.message);
  }
}

async function compareSelectedTestRuns() {
  const ids = selectedRunIds();
  if (!ids.length || ids.length > 3) {
    alert("Select between one and three saved runs to compare.");
    return;
  }
  try {
    state.comparisonRuns = await Promise.all(ids.map(fetchSavedRun));
    state.overlayEnabled = true;
    toggleHistorical.checked = true;
    document.getElementById("ghostLegendItem").style.display = "flex";
    document.getElementById("ghostCurveLegend").innerText = `Comparison: ${state.comparisonRuns.map(run => run.config.sample_id).join(", ")}`;
    renderChart();
  } catch (error) {
    alert(error.message);
  }
}

// ----------------- Canvas Rendering Engine -----------------
function getModeMetadata(mode) {
  switch (mode) {
    case 1:
      return {
        xLabel: "Displacement, D (mm)",
        yLabel: "System Load, F (kN)",
        getX: (i, d) => d.dispSeriesMm[i],
        getY: (i, d) => d.forceSeriesKn[i],
        xUnit: "mm",
        yUnit: "kN"
      };
    case 2:
      return {
        xLabel: "Displacement, D (mm)",
        yLabel: "Engineering Stress, σ (MPa)",
        getX: (i, d) => d.dispSeriesMm[i],
        getY: (i, d) => d.stressSeriesMpa[i],
        xUnit: "mm",
        yUnit: "MPa"
      };
    case 3:
      return {
        xLabel: "Engineering Strain, ε (%) [ΔL / L₀]",
        yLabel: "Engineering Stress, σ (MPa)",
        getX: (i, d) => d.strainSeriesPct[i],
        getY: (i, d) => d.stressSeriesMpa[i],
        xUnit: "%",
        yUnit: "MPa"
      };
    case 4:
      return {
        xLabel: "Time Duration, T (seconds)",
        yLabel: "System Load, F (kN)",
        getX: (i, d) => d.timeSeries[i],
        getY: (i, d) => d.forceSeriesKn[i],
        xUnit: "s",
        yUnit: "kN"
      };
    default:
      return getModeMetadata(1);
  }
}

function renderChart() {
  const rect = canvasWrapper.getBoundingClientRect();
  const w = rect.width;
  const h = rect.height;

  ctx.clearRect(0, 0, w, h);
  if (w <= 0 || h <= 0) return;

  const padding = { top: 30, right: 35, bottom: 45, left: 60 };
  const plotW = w - padding.left - padding.right;
  const plotH = h - padding.top - padding.bottom;

  const meta = getModeMetadata(state.currentMode);

  // Compute Active Bounds
  let minX = 0, maxX = 1.0;
  let minY = 0, maxY = 1.0;

  const n = state.timeSeries.length;
  if (n > 0) {
    for (let i = 0; i < n; i++) {
      const x = meta.getX(i, state);
      const y = meta.getY(i, state);
      if (x > maxX) maxX = x;
      if (y > maxY) maxY = y;
    }
  }

  // Include Historical Data in Bounds if superimposed
  if (state.overlayEnabled && state.historicalData) {
    const hist = state.historicalData;
    const histDataWrap = {
      timeSeries: hist.time_series || [],
      forceSeriesKn: hist.force_series_kn || [],
      dispSeriesMm: hist.disp_series_mm || [],
      stressSeriesMpa: hist.stress_series_mpa || [],
      strainSeriesPct: hist.strain_series_pct || []
    };
    const hn = histDataWrap.timeSeries.length;
    for (let i = 0; i < hn; i++) {
      const hx = meta.getX(i, histDataWrap);
      const hy = meta.getY(i, histDataWrap);
      if (hx > maxX) maxX = hx;
      if (hy > maxY) maxY = hy;
    }
  }

  if (state.overlayEnabled) {
    for (const run of state.comparisonRuns) {
      const series = recordToChartData(run);
      for (let i = 0; i < series.timeSeries.length; i++) {
        maxX = Math.max(maxX, meta.getX(i, series));
        maxY = Math.max(maxY, meta.getY(i, series));
      }
    }
  }

  // Apply headroom margin (12%)
  maxX = maxX * 1.12;
  maxY = maxY * 1.15;
  if (maxX <= 0) maxX = 1.0;
  if (maxY <= 0) maxY = 1.0;

  // Zoom and operator bounds
  if (state.axisBounds) {
    minX = state.axisBounds.minX;
    maxX = state.axisBounds.maxX;
    minY = state.axisBounds.minY;
    maxY = state.axisBounds.maxY;
  } else if (!state.autoScale || state.zoomLevel !== 1.0) {
    maxX = maxX / state.zoomLevel;
    maxY = maxY / state.zoomLevel;
  }

  // Coordinate transform functions
  const toScreenX = (val) => padding.left + ((val - minX) / (maxX - minX)) * plotW;
  const toScreenY = (val) => padding.top + plotH - ((val - minY) / (maxY - minY)) * plotH;
  const toValX = (screenX) => minX + ((screenX - padding.left) / plotW) * (maxX - minX);
  const toValY = (screenY) => minY + ((padding.top + plotH - screenY) / plotH) * (maxY - minY);

  state._coordMap = { toScreenX, toScreenY, toValX, toValY, padding, plotW, plotH, minX, maxX, minY, maxY };

  // 1. Draw Grid Lines
  if (state.gridEnabled) {
    ctx.strokeStyle = "rgba(148, 163, 184, 0.12)";
    ctx.lineWidth = 1;

    // Vertical grid lines
    const xSteps = 8;
    for (let i = 0; i <= xSteps; i++) {
      const gx = minX + (i / xSteps) * (maxX - minX);
      const sx = toScreenX(gx);
      ctx.beginPath();
      ctx.moveTo(sx, padding.top);
      ctx.lineTo(sx, padding.top + plotH);
      ctx.stroke();

      // Axis label
      ctx.fillStyle = "#64748b";
      ctx.font = "9px 'JetBrains Mono', monospace";
      ctx.textAlign = "center";
      ctx.fillText(gx.toFixed(gx > 10 ? 1 : 2), sx, padding.top + plotH + 15);
    }

    // Horizontal grid lines
    const ySteps = 6;
    for (let i = 0; i <= ySteps; i++) {
      const gy = minY + (i / ySteps) * (maxY - minY);
      const sy = toScreenY(gy);
      ctx.beginPath();
      ctx.moveTo(padding.left, sy);
      ctx.lineTo(padding.left + plotW, sy);
      ctx.stroke();

      // Axis label
      ctx.fillStyle = "#64748b";
      ctx.font = "9px 'JetBrains Mono', monospace";
      ctx.textAlign = "right";
      ctx.fillText(gy.toFixed(gy > 10 ? 1 : 2), padding.left - 8, sy + 3);
    }
  }

  // 2. Draw Plot Axes
  ctx.strokeStyle = "rgba(255, 255, 255, 0.25)";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(padding.left, padding.top);
  ctx.lineTo(padding.left, padding.top + plotH);
  ctx.lineTo(padding.left + plotW, padding.top + plotH);
  ctx.stroke();

  // Axis Titles
  ctx.fillStyle = "#94a3b8";
  ctx.font = "600 10.5px 'Inter', sans-serif";
  ctx.textAlign = "center";
  ctx.fillText(meta.xLabel, padding.left + plotW / 2, padding.top + plotH + 35);

  ctx.save();
  ctx.translate(16, padding.top + plotH / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText(meta.yLabel, 0, 0);
  ctx.restore();

  // 3. Superimpose Historical Ghost Curve
  if (state.overlayEnabled && state.historicalData) {
    const hist = state.historicalData;
    const histDataWrap = {
      timeSeries: hist.time_series || [],
      forceSeriesKn: hist.force_series_kn || [],
      dispSeriesMm: hist.disp_series_mm || [],
      stressSeriesMpa: hist.stress_series_mpa || [],
      strainSeriesPct: hist.strain_series_pct || []
    };
    const hn = histDataWrap.timeSeries.length;

    if (hn > 1) {
      ctx.save();
      ctx.strokeStyle = "#f59e0b";
      ctx.lineWidth = 1.8;
      ctx.setLineDash([5, 4]); // Dashed amber track
      ctx.beginPath();

      for (let i = 0; i < hn; i++) {
        const hx = meta.getX(i, histDataWrap);
        const hy = meta.getY(i, histDataWrap);
        const sx = toScreenX(hx);
        const sy = toScreenY(hy);
        if (i === 0) ctx.moveTo(sx, sy);
        else ctx.lineTo(sx, sy);
      }
      ctx.stroke();
      ctx.restore();
    }
  }

  if (state.overlayEnabled) {
    const comparisonColors = ["#f97316", "#16a34a", "#a855f7"];
    state.comparisonRuns.forEach((run, runIndex) => {
      const series = recordToChartData(run);
      if (series.timeSeries.length < 2) return;
      ctx.save();
      ctx.strokeStyle = comparisonColors[runIndex % comparisonColors.length];
      ctx.lineWidth = 1.8;
      ctx.setLineDash([6, 4]);
      ctx.beginPath();
      for (let i = 0; i < series.timeSeries.length; i++) {
        const sx = toScreenX(meta.getX(i, series));
        const sy = toScreenY(meta.getY(i, series));
        if (i === 0) ctx.moveTo(sx, sy);
        else ctx.lineTo(sx, sy);
      }
      ctx.stroke();
      ctx.restore();
    });
  }

  // 4. Render Active Live Curve
  if (n > 1) {
    // Fill under curve
    const gradient = ctx.createLinearGradient(0, padding.top, 0, padding.top + plotH);
    gradient.addColorStop(0, "rgba(59, 130, 246, 0.25)");
    gradient.addColorStop(1, "rgba(59, 130, 246, 0.0)");

    ctx.beginPath();
    const firstX = toScreenX(meta.getX(0, state));
    const firstY = toScreenY(meta.getY(0, state));
    ctx.moveTo(firstX, padding.top + plotH);
    ctx.lineTo(firstX, firstY);

    for (let i = 1; i < n; i++) {
      const sx = toScreenX(meta.getX(i, state));
      const sy = toScreenY(meta.getY(i, state));
      ctx.lineTo(sx, sy);
    }
    const lastX = toScreenX(meta.getX(n - 1, state));
    ctx.lineTo(lastX, padding.top + plotH);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();

    // Solid glowing stroke
    ctx.strokeStyle = "#3b82f6";
    ctx.lineWidth = 2.2;
    ctx.shadowColor = "rgba(59, 130, 246, 0.5)";
    ctx.shadowBlur = 8;
    ctx.beginPath();

    for (let i = 0; i < n; i++) {
      const sx = toScreenX(meta.getX(i, state));
      const sy = toScreenY(meta.getY(i, state));
      if (i === 0) ctx.moveTo(sx, sy);
      else ctx.lineTo(sx, sy);
    }
    ctx.stroke();
    ctx.shadowBlur = 0; // Reset shadow
  }

  // 5. Annotate Peak Load Point
  if (state.peakIndex >= 0 && state.peakIndex < n) {
    const px = toScreenX(meta.getX(state.peakIndex, state));
    const py = toScreenY(meta.getY(state.peakIndex, state));

    ctx.fillStyle = "#ef4444";
    ctx.beginPath();
    ctx.arc(px, py, 5, 0, Math.PI * 2);
    ctx.fill();

    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 1.5;
    ctx.stroke();

    ctx.fillStyle = "#f87171";
    ctx.font = "bold 9.5px 'JetBrains Mono', monospace";
    ctx.textAlign = "left";
    ctx.fillText(`PEAK (Su: ${state.sUMpa.toFixed(1)} MPa)`, px + 8, py - 6);
  }

  // 6. Annotate Fracture Point
  if (state.isFractured && n > 5) {
    const lastIdx = n - 1;
    const fx = toScreenX(meta.getX(lastIdx, state));
    const fy = toScreenY(meta.getY(lastIdx, state));

    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 2.5;
    const sz = 6;
    ctx.beginPath();
    ctx.moveTo(fx - sz, fy - sz);
    ctx.lineTo(fx + sz, fy + sz);
    ctx.moveTo(fx + sz, fy - sz);
    ctx.lineTo(fx - sz, fy + sz);
    ctx.stroke();

    ctx.fillStyle = "#cbd5e1";
    ctx.font = "bold 9px 'JetBrains Mono', monospace";
    ctx.textAlign = "center";
    ctx.fillText("FRACTURE (0.0 N)", fx, fy + 16);
  }

  // Render crosshairs on overlay canvas
  renderOverlay();
}

// ----------------- Interactive Point Tracing Tool -----------------
function renderOverlay() {
  const rect = canvasWrapper.getBoundingClientRect();
  const w = rect.width;
  const h = rect.height;

  oCtx.clearRect(0, 0, w, h);
  if (!state.cursorX || !state.cursorY || !state._coordMap) return;

  const { toScreenX, toScreenY, padding, plotW, plotH } = state._coordMap;

  // Check if cursor is inside plot region
  if (
    state.cursorX < padding.left ||
    state.cursorX > padding.left + plotW ||
    state.cursorY < padding.top ||
    state.cursorY > padding.top + plotH
  ) {
    tooltip.classList.add("hidden");
    return;
  }

  // Draw Crosshair intersection lines
  oCtx.strokeStyle = "rgba(6, 182, 212, 0.6)";
  oCtx.lineWidth = 1;
  oCtx.setLineDash([4, 4]);

  // Vertical intersection line
  oCtx.beginPath();
  oCtx.moveTo(state.cursorX, padding.top);
  oCtx.lineTo(state.cursorX, padding.top + plotH);
  oCtx.stroke();

  // Horizontal intersection line
  oCtx.beginPath();
  oCtx.moveTo(padding.left, state.cursorY);
  oCtx.lineTo(padding.left + plotW, state.cursorY);
  oCtx.stroke();
  oCtx.setLineDash([]);

  // Find nearest curve point
  const meta = getModeMetadata(state.currentMode);
  const n = state.timeSeries.length;
  let nearestIdx = state.pinnedPointIndex ?? -1;
  let minDist = state.pinnedPointIndex === null ? 999999 : 0;

  if (state.pinnedPointIndex === null) {
    for (let i = 0; i < n; i++) {
      const sx = toScreenX(meta.getX(i, state));
      const sy = toScreenY(meta.getY(i, state));
      const dist = Math.hypot(sx - state.cursorX, sy - state.cursorY);
      if (dist < minDist) {
        minDist = dist;
        nearestIdx = i;
      }
    }
  }

  if (nearestIdx >= 0 && (state.pinnedPointIndex === nearestIdx || minDist < 80)) {
    state.hoveredPointIndex = nearestIdx;
    const ptX = toScreenX(meta.getX(nearestIdx, state));
    const ptY = toScreenY(meta.getY(nearestIdx, state));

    // Highlight dot on curve
    oCtx.fillStyle = "#06b6d4";
    oCtx.beginPath();
    oCtx.arc(ptX, ptY, 4.5, 0, Math.PI * 2);
    oCtx.fill();
    oCtx.strokeStyle = "#ffffff";
    oCtx.lineWidth = 1.5;
    oCtx.stroke();

    // Show floating tooltip
    const valX = meta.getX(nearestIdx, state);
    const valY = meta.getY(nearestIdx, state);
    const stress = state.stressSeriesMpa[nearestIdx];

    tooltipXLabel.innerText = `${meta.xLabel.split(",")[0]}:`;
    tooltipXVal.innerText = `${valX.toFixed(3)} ${meta.xUnit}`;
    tooltipYLabel.innerText = `${meta.yLabel.split(",")[0]}:`;
    tooltipYVal.innerText = `${valY.toFixed(3)} ${meta.yUnit}`;
    tooltipSecVal.innerText = `${stress.toFixed(2)} MPa`;

    coordReadout.innerText = `X: ${valX.toFixed(3)} ${meta.xUnit} | Y: ${valY.toFixed(3)} ${meta.yUnit}`;

    // Position tooltip
    tooltip.classList.remove("hidden");
    const tW = 160;
    const tH = 80;
    let leftPos = ptX + 15;
    let topPos = ptY - 40;
    if (leftPos + tW > w) leftPos = ptX - tW - 15;
    if (topPos < 10) topPos = ptY + 15;

    tooltip.style.left = `${leftPos}px`;
    tooltip.style.top = `${topPos}px`;
  } else {
    state.hoveredPointIndex = null;
    // Show coordinates under crosshair
    const { toValX, toValY } = state._coordMap;
    const vX = toValX(state.cursorX);
    const vY = toValY(state.cursorY);
    coordReadout.innerText = `X: ${vX.toFixed(3)} ${meta.xUnit} | Y: ${vY.toFixed(3)} ${meta.yUnit}`;
    tooltip.classList.add("hidden");
  }
}

// Canvas Mouse Move Event
canvasWrapper.addEventListener("mousemove", (e) => {
  const rect = canvasWrapper.getBoundingClientRect();
  if (state.panStart) {
    const dx = e.clientX - state.panStart.x;
    const dy = e.clientY - state.panStart.y;
    const { bounds, plotW, plotH } = state.panStart;
    const xShift = dx * (bounds.maxX - bounds.minX) / plotW;
    const yShift = dy * (bounds.maxY - bounds.minY) / plotH;
    state.axisBounds = {
      minX: bounds.minX - xShift,
      maxX: bounds.maxX - xShift,
      minY: bounds.minY + yShift,
      maxY: bounds.maxY + yShift
    };
    renderChart();
    return;
  }
  state.cursorX = e.clientX - rect.left;
  state.cursorY = e.clientY - rect.top;
  renderOverlay();
});

canvasWrapper.addEventListener("pointerdown", (event) => {
  if (!(event.shiftKey || event.button === 1) || !state._coordMap) return;
  const map = state._coordMap;
  state.panStart = {
    x: event.clientX,
    y: event.clientY,
    bounds: { minX: map.minX, maxX: map.maxX, minY: map.minY, maxY: map.maxY },
    plotW: map.plotW,
    plotH: map.plotH
  };
  canvasWrapper.setPointerCapture(event.pointerId);
});

canvasWrapper.addEventListener("pointerup", () => { state.panStart = null; });

canvasWrapper.addEventListener("mouseleave", () => {
  if (state.pinnedPointIndex !== null) return;
  state.cursorX = null;
  state.cursorY = null;
  coordReadout.innerText = "X: -- | Y: --";
  tooltip.classList.add("hidden");
  oCtx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
});

canvasWrapper.addEventListener("click", () => {
  state.pinnedPointIndex = state.pinnedPointIndex === null ? state.hoveredPointIndex : null;
  renderOverlay();
});

// ----------------- Mode Switch Handler -----------------
modeTabs.forEach(tab => {
  tab.addEventListener("click", () => {
    modeTabs.forEach(t => t.classList.remove("active"));
    tab.classList.add("active");
    state.currentMode = parseInt(tab.getAttribute("data-mode"));
    renderChart();
  });
});

// ----------------- Chart Controls (Grid, Auto-Scale, Zoom) -----------------
btnToggleGrid.addEventListener("click", () => {
  state.gridEnabled = !state.gridEnabled;
  btnToggleGrid.classList.toggle("active", state.gridEnabled);
  btnToggleGrid.innerHTML = `<span>⊞</span> Grid Lines: ${state.gridEnabled ? "ON" : "OFF"}`;
  renderChart();
});

btnToggleAutoScale.addEventListener("click", () => {
  state.autoScale = !state.autoScale;
  if (state.autoScale) state.axisBounds = null;
  btnToggleAutoScale.classList.toggle("active", state.autoScale);
  btnToggleAutoScale.innerHTML = `<span>⤢</span> Auto-Scale: ${state.autoScale ? "ON" : "OFF"}`;
  renderChart();
});

btnZoomIn.addEventListener("click", () => {
  state.axisBounds = null;
  state.autoScale = false;
  btnToggleAutoScale.classList.remove("active");
  btnToggleAutoScale.innerHTML = "<span>⤢</span> Auto-Scale: OFF";
  state.zoomLevel *= 1.3;
  renderChart();
});

btnZoomOut.addEventListener("click", () => {
  state.axisBounds = null;
  state.zoomLevel = Math.max(0.5, state.zoomLevel / 1.3);
  renderChart();
});

btnResetZoom.addEventListener("click", () => {
  state.zoomLevel = 1.0;
  state.axisBounds = null;
  state.pinnedPointIndex = null;
  state.autoScale = true;
  btnToggleAutoScale.classList.add("active");
  btnToggleAutoScale.innerHTML = "<span>⤢</span> Auto-Scale: ON";
  renderChart();
});

btnFreezeScreen.addEventListener("click", () => {
  state.displayFrozen = !state.displayFrozen;
  btnFreezeScreen.classList.toggle("active", state.displayFrozen);
  btnFreezeScreen.setAttribute("aria-pressed", String(state.displayFrozen));
  btnFreezeScreen.innerHTML = state.displayFrozen ? "<span>▶</span> Resume Screen" : "<span>Ⅱ</span> Freeze Screen";
  if (!state.displayFrozen && state.latestTelemetry) renderTelemetryDisplay(state.latestTelemetry);
});

btnApplyAxisLimits.addEventListener("click", () => {
  const bounds = {
    minX: Number(axisMinX.value),
    maxX: Number(axisMaxX.value),
    minY: Number(axisMinY.value),
    maxY: Number(axisMaxY.value)
  };
  if (Object.values(bounds).some(value => !Number.isFinite(value)) || bounds.maxX <= bounds.minX || bounds.maxY <= bounds.minY) {
    alert("Enter finite axis bounds with each maximum greater than its minimum.");
    return;
  }
  state.axisBounds = bounds;
  state.autoScale = false;
  btnToggleAutoScale.classList.remove("active");
  btnToggleAutoScale.innerHTML = "<span>⤢</span> Auto-Scale: OFF";
  state.zoomLevel = 1.0;
  renderChart();
});

// ----------------- Operational Action Triggers -----------------
btnTare.addEventListener("click", async () => {
  try {
    const res = await fetch("/api/test/tare", { method: "POST" });
    if (res.ok) {
      console.log("Load Cell Tared.");
    }
  } catch (err) {
    console.error("Tare failed:", err);
  }
});

btnStart.addEventListener("click", async () => {
  if (!sampleIdInput.value.trim() || !standardSelect.value || !virtualMaterial.value || !geometryType.value || !specimenWidthInput.value || (geometryType.value === "flat" && !specimenThicknessInput.value) || !areaA0Input.value || !lengthL0Input.value || !maxLoadLimitInput.value || !maxTravelLimitInput.value) {
    alert("Enter the sample, material, standard, specimen dimensions, gauge length, and both software limits before starting.");
    return;
  }
  fractureBanner.classList.add("hidden");
  
  // Clear local buffers
  state.timeSeries = [];
  state.forceSeriesN = [];
  state.forceSeriesKn = [];
  state.dispSeriesMm = [];
  state.stressSeriesMpa = [];
  state.strainSeriesRatio = [];
  state.strainSeriesPct = [];
  state.fMaxKn = 0.0;
  state.fMaxN = 0.0;
  state.sUMpa = 0.0;
  state.peakIndex = -1;
  state.isFractured = false;
  state.testStatus = "RUNNING";

  renderChart();

  const payloadConfig = {
    sample_id: sampleIdInput.value.trim(),
    material_grade: virtualMaterial.value,
    standard: standardSelect.value,
    test_mode: testModeSelect.value,
    data_source: hardwareSource.value,
    company_name: companyNameInput.value.trim(),
    system_serial_number: systemSerialNumberInput.value.trim(),
    operator_name: operatorNameInput.value.trim(),
    inspector_name: inspectorNameInput.value.trim(),
    witness_name: witnessNameInput.value.trim(),
    a_0: Number(areaA0Input.value),
    l_0: Number(lengthL0Input.value),
    geometry: geometryType.value,
    width_mm: Number(specimenWidthInput.value),
    thickness_mm: geometryType.value === "flat" ? Number(specimenThicknessInput.value) : null,
    control_mode: controlMode.value,
    crosshead_speed_mm_min: Number(crossheadSpeedInput.value),
    load_rate_setpoint_kn_min: Number(loadRateTargetInput.value) * (loadRateUnit.value === "n_sec" ? 0.06 : 1),
    max_load_n: Number(maxLoadLimitInput.value),
    max_travel_mm: Number(maxTravelLimitInput.value)
  };

  try {
    const response = await fetch("/api/test/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payloadConfig)
    });
    if (!response.ok) throw new Error((await response.json()).detail || "Test could not start");
    state.activeRunId = null;
    state.comparisonRuns = [];
    updateStateBadge("RUNNING");
  } catch (err) {
    console.error("Test start failed:", err);
    state.testStatus = "IDLE";
    updateStateBadge("IDLE");
    alert(err.message || "Test could not start");
    return;
  }

  // If Data Source is Virtual UTM Simulator, start client-side telemetry ingestion loop
  if (hardwareSource.value === "virtual") {
    startVirtualSimulationLoop();
  }
});

btnStop.addEventListener("click", async () => {
  try {
    const response = await fetch("/api/test/stop", { method: "POST" });
    if (!response.ok) throw new Error("Test could not stop cleanly");
    updateStateBadge("STOPPED");
    if (state.virtualTimer) {
      clearInterval(state.virtualTimer);
      state.virtualTimer = null;
    }
    fetchAIComplianceReview();
    await refreshSavedTestRuns();
  } catch (err) {
    console.error("Test stop failed:", err);
  }
});

btnClose.addEventListener("click", async () => {
  if (state.testStatus === "RUNNING") {
    const response = await fetch("/api/test/stop", { method: "POST" });
    if (!response.ok) {
      alert("The active test could not be stopped. Use the machine's verified hardware stop.");
      return;
    }
    await refreshSavedTestRuns();
  }
  if (state.virtualTimer) {
    clearInterval(state.virtualTimer);
    state.virtualTimer = null;
  }
  fractureBanner.classList.add("hidden");
  state.testStatus = "IDLE";
  updateStateBadge("IDLE");
  state.timeSeries = [];
  state.forceSeriesN = [];
  state.forceSeriesKn = [];
  state.dispSeriesMm = [];
  state.stressSeriesMpa = [];
  state.strainSeriesRatio = [];
  state.strainSeriesPct = [];
  state.fMaxKn = 0.0;
  state.fMaxN = 0.0;
  state.sUMpa = 0.0;
  renderChart();
});

// ----------------- Virtual Machine Client Driver -----------------
function startVirtualSimulationLoop() {
  if (state.virtualTimer) {
    clearInterval(state.virtualTimer);
  }

  const hz = parseInt(pollingFreq.value) || 25;
  const dt = 1.0 / hz;
  const matKey = virtualMaterial.value;
  const a0 = Number(areaA0Input.value);
  const l0 = Number(lengthL0Input.value);
  const sampleId = sampleIdInput.value.trim();

  // Physics simulation state
  let simTime = 0.0;
  let simDisp = 0.0;
  let simForce = 0.0;
  let fractured = false;

  // Material properties
  const isSteel = matKey.includes("FE") || matKey.includes("A36");
  const isFe500 = matKey.includes("500");
  const isFe415 = matKey.includes("415");
  const isA36 = matKey.includes("A36");

  let E = 205000; // MPa
  let Sy = isFe500 ? 525 : (isFe415 ? 435 : (isA36 ? 260 : 276));
  let Su = isFe500 ? 620 : (isFe415 ? 530 : (isA36 ? 460 : 315));
  let ey = Sy / E;
  let ep = isA36 ? 0.022 : (isFe500 ? 0.012 : 0.015);
  let eu = isA36 ? 0.15 : (isFe500 ? 0.10 : 0.12);
  let ef = isA36 ? 0.23 : (isFe500 ? 0.145 : 0.165);
  const speedMmMin = controlMode.value === "load_rate"
    ? Math.min(100, Math.max(0.1, Number(loadRateTargetInput.value) * (loadRateUnit.value === "n_sec" ? 60 : 1000) * l0 / (E * a0)))
    : Number(crossheadSpeedInput.value);
  const testSpeed = speedMmMin / 60.0;
  const testDirection = testModeSelect.value === "compression" ? -1 : 1;

  state.virtualTimer = setInterval(async () => {
    simTime += dt;
    simDisp += testSpeed * dt;
    const eps = simDisp / l0;

    let sigma = 0.0;
    if (eps <= ey) {
      sigma = E * eps + (Math.random() - 0.5) * 1.5;
    } else if (eps <= ep) {
      const prog = (eps - ey) / Math.max(0.0001, (ep - ey));
      sigma = Sy + Math.sin(prog * Math.PI * 3.0) * (Sy * 0.018) + (Math.random() - 0.5) * 1.5;
    } else if (eps <= eu) {
      const prog = (eps - ep) / Math.max(0.0001, (eu - ep));
      sigma = Sy + (Su - Sy) * Math.pow(prog, 0.45) + (Math.random() - 0.5) * 1.2;
    } else if (eps <= ef) {
      const prog = (eps - eu) / Math.max(0.0001, (ef - eu));
      sigma = Su - (Su * 0.15) * Math.pow(prog, 1.8) + (Math.random() - 0.5) * 1.0;
    } else {
      fractured = true;
      sigma = 0.0;
      simForce = 0.0;
    }

    if (!fractured) {
      simForce = Math.max(0.0, sigma * a0);
    }

    // Ingest frame to cloud backend
    const frame = {
      sample_id: sampleId,
      time_sec: parseFloat(simTime.toFixed(4)),
      force_n: parseFloat((testDirection * simForce).toFixed(2)),
      displacement_mm: parseFloat((testDirection * simDisp).toFixed(4))
    };

    try {
      const response = await fetch("/api/telemetry", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(frame)
      });
      if (response.status === 409) {
        clearInterval(state.virtualTimer);
        state.virtualTimer = null;
      }
    } catch (e) {
      console.warn("Direct post error (offline queue handling)");
    }

    if (fractured) {
      clearInterval(state.virtualTimer);
      state.virtualTimer = null;
    }
  }, Math.round(1000 / hz));
}

// ----------------- Hardware & Controls UI Listeners -----------------
pollingFreq.addEventListener("input", (e) => {
  pollingFreqVal.innerText = `${e.target.value} Hz`;
});

hardwareSource.addEventListener("change", (e) => {
  virtualMaterialRow.style.display = e.target.value === "virtual" ? "flex" : "none";
  hardwareSafetyNote.hidden = e.target.value !== "serial";
});

controlMode.addEventListener("change", () => {
  const loadRateMode = controlMode.value === "load_rate";
  document.getElementById("loadRateField").hidden = !loadRateMode;
  document.getElementById("crossheadSpeedField").hidden = loadRateMode;
});

function updateGeometryArea() {
  const width = Number(specimenWidthInput.value);
  const thickness = Number(specimenThicknessInput.value);
  const isFlat = geometryType.value === "flat";
  specimenThicknessField.hidden = !isFlat;
  specimenThicknessInput.required = isFlat;
  const area = isFlat ? width * thickness : Math.PI * width * width / 4;
  areaA0Input.value = Number.isFinite(area) && area > 0 ? area.toFixed(6) : "";
}

geometryType.addEventListener("change", updateGeometryArea);
specimenWidthInput.addEventListener("input", updateGeometryArea);
specimenThicknessInput.addEventListener("input", updateGeometryArea);

historicalSelect.addEventListener("change", (e) => {
  loadHistoricalRecord(e.target.value);
});

btnRefreshRuns.addEventListener("click", refreshSavedTestRuns);
testRunSearch.addEventListener("input", () => {
  clearTimeout(state.historySearchTimer);
  state.historySearchTimer = setTimeout(refreshSavedTestRuns, 200);
});
btnLoadRun.addEventListener("click", loadSelectedTestRun);
btnCompareRuns.addEventListener("click", compareSelectedTestRuns);
btnReviewRun.addEventListener("click", async () => {
  const runId = selectedRunIds()[0];
  if (runId) await fetchAIComplianceReview(runId);
});
btnDeleteRun.addEventListener("click", async () => {
  const runId = selectedRunIds()[0];
  if (!runId || !confirm("Permanently delete this saved test run?")) return;
  const response = await fetch(`/api/test-runs/${encodeURIComponent(runId)}`, { method: "DELETE" });
  if (!response.ok) {
    alert("The saved test run could not be deleted.");
    return;
  }
  if (String(state.activeRunId) === runId) state.activeRunId = null;
  state.comparisonRuns = state.comparisonRuns.filter(run => String(run.run_id) !== runId);
  await refreshSavedTestRuns();
  renderChart();
});

toggleHistorical.addEventListener("change", () => {
  state.overlayEnabled = toggleHistorical.checked;
  document.getElementById("ghostLegendItem").style.display = state.overlayEnabled && (state.historicalData || state.comparisonRuns.length) ? "flex" : "none";
  renderChart();
});

// ----------------- Export Downloads -----------------
btnDownloadPdf.addEventListener("click", () => {
  const runId = selectedRunIds()[0] || state.activeRunId;
  window.open(runId ? `/api/report/pdf?run_id=${encodeURIComponent(runId)}` : "/api/report/pdf", "_blank");
});

btnDownloadXlsx.addEventListener("click", () => {
  const runId = selectedRunIds()[0] || state.activeRunId;
  window.location.href = runId ? `/api/export/xlsx?run_id=${encodeURIComponent(runId)}` : "/api/export/xlsx";
});

btnDownloadCsv.addEventListener("click", () => {
  const runId = selectedRunIds()[0] || state.activeRunId;
  window.location.href = runId ? `/api/export/csv?run_id=${encodeURIComponent(runId)}` : "/api/export/csv";
});

btnDownloadXyt.addEventListener("click", () => {
  const runId = selectedRunIds()[0] || state.activeRunId;
  window.location.href = runId ? `/api/export/xyt?run_id=${encodeURIComponent(runId)}` : "/api/export/xyt";
});

// Initial boot sequence
window.addEventListener("DOMContentLoaded", async () => {
  resizeCanvas();
  const authenticated = await checkAuth();
  if (!authenticated) {
    return;
  }
  initWebSocket();
  await populateHistoricalRecords();
  await refreshSavedTestRuns();
  loadHistoricalRecord("none");
});
