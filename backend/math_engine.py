"""
Phase 3: Software Math Engine & Input Variables
Dynamic Stress (Force/Area), Strain (Disp/Length), Live Peak-Load Trackers,
Live Pacing Gauge calculations, and Zero-Force Fracture Tracking Rules.
"""

import math
from typing import List, Dict, Any, Optional, Tuple
from backend.schemas import TelemetryPayload, SampleConfig, LiveTelemetryResponse

class SoftwareMathEngine:
    """
    Automated machine data engineering calculation core engine.
    Processes live data stream frames, evaluates physical equations,
    detects fracture conditions, and tracks peak structural metrics.
    """

    def __init__(self, config: Optional[SampleConfig] = None):
        self.config = config or SampleConfig()
        self.reset()

    def reset(self, config: Optional[SampleConfig] = None):
        if config:
            self.config = config
        
        # Specimen Baseline Parameters
        self.a_0 = float(self.config.a_0)  # Baseline cross-sectional area: 50.0 mm²
        self.l_0 = float(self.config.l_0)  # Initial gauge length: 50.0 mm
        
        # Live Running State
        self.tare_offset_n = 0.0
        self.tare_offset_mm = 0.0
        self.is_running = False
        self.is_fractured = False
        self.safety_limit_reason: Optional[str] = None
        self.state = "IDLE"  # IDLE, RUNNING, FRACTURED, COMPLETED, STOPPED
        
        # Dynamic Peak Tracking Targets
        self.f_max_n = 0.0
        self.d_peak_mm = 0.0
        self.s_u_mpa = 0.0
        self.peak_index = -1
        
        # Active History Log Buffers
        self.time_series: List[float] = []
        self.force_series_n: List[float] = []
        self.force_series_kn: List[float] = []
        self.disp_series_mm: List[float] = []
        self.stress_series_mpa: List[float] = []
        self.strain_series_ratio: List[float] = []
        self.strain_series_pct: List[float] = []
        
        # Pacing window metrics
        self.load_rate_kn_min = 0.0
        self.disp_rate_mm_min = 0.0
        
        # Fracture evaluation tracking
        self.fracture_index = -1

    def tare(self):
        """Zeroes force and displacement against the latest sample."""
        if self.force_series_n:
            self.tare_offset_n += self.force_series_n[-1]
        else:
            self.tare_offset_n = 0.0
        if self.disp_series_mm:
            self.tare_offset_mm += self.disp_series_mm[-1]
        else:
            self.tare_offset_mm = 0.0

    def start_test(self, config: Optional[SampleConfig] = None):
        """Initializes a new testing run."""
        self.reset(config)
        self.is_running = True
        self.state = "RUNNING"

    def stop_test(self):
        """Manually halts testing sequence."""
        self.is_running = False
        if not self.is_fractured:
            self.state = "STOPPED"

    def ingest_frame(self, frame: TelemetryPayload) -> LiveTelemetryResponse:
        """
        Processes single incoming data frame through mathematics pipeline.
        Calculates stress, strain, peak targets, pacing velocity, and fracture rules.
        """
        raw_force = frame.force_n
        t = frame.time_sec
        disp = frame.displacement_mm - self.tare_offset_mm
        force_magnitude = abs(raw_force - self.tare_offset_n)
        force_sign = -1.0 if self.config.test_mode == "compression" else 1.0
        tared_force = force_sign * force_magnitude
        
        # Apply tare offset
        force_kn = tared_force / 1000.0
        
        # 1. Dynamic Engineering Stress (sigma) = F_n / A_0 (MPa or N/mm²)
        stress_mpa = tared_force / self.a_0 if self.a_0 > 0 else 0.0
        
        # 2. Dynamic Engineering Strain (epsilon) = D_m / L_0 (dimensionless ratio or %)
        strain_ratio = disp / self.l_0 if self.l_0 > 0 else 0.0
        strain_pct = strain_ratio * 100.0
        
        # Store in active history log buffers
        idx = len(self.time_series)
        self.time_series.append(t)
        self.force_series_n.append(tared_force)
        self.force_series_kn.append(force_kn)
        self.disp_series_mm.append(disp)
        self.stress_series_mpa.append(stress_mpa)
        self.strain_series_ratio.append(strain_ratio)
        self.strain_series_pct.append(strain_pct)

        if self.is_running and self.config.max_load_n and force_magnitude >= self.config.max_load_n:
            self.safety_limit_reason = f"Load limit exceeded ({force_magnitude:.1f} N >= {self.config.max_load_n:.1f} N)"
            self.is_running = False
            self.state = "SAFETY_LIMIT"
        elif self.is_running and self.config.max_travel_mm and abs(disp) >= self.config.max_travel_mm:
            self.safety_limit_reason = f"Travel limit exceeded ({abs(disp):.3f} mm >= {self.config.max_travel_mm:.3f} mm)"
            self.is_running = False
            self.state = "SAFETY_LIMIT"
        
        # 3. Peak Load Value Target (F_max) & Peak Displacement Vector (D_peak)
        if force_magnitude > self.f_max_n:
            self.f_max_n = force_magnitude
            self.d_peak_mm = abs(disp)
            self.peak_index = idx
            # Ultimate Strength Parameter (S_u) = F_max / A_0
            self.s_u_mpa = self.f_max_n / self.a_0 if self.a_0 > 0 else 0.0
        
        # 4. Live Pacing Gauge Component Calculation (Load Rate in kN/min, Disp Rate in mm/min)
        if idx >= 3:
            window = min(8, idx)
            dt = self.time_series[-1] - self.time_series[-window]
            if dt > 0.01:
                df_kn = abs(self.force_series_kn[-1]) - abs(self.force_series_kn[-window])
                dd_mm = abs(self.disp_series_mm[-1]) - abs(self.disp_series_mm[-window])
                
                # Convert from per second to per minute (* 60.0)
                calc_load_rate = (df_kn / dt) * 60.0
                calc_disp_rate = (dd_mm / dt) * 60.0
                
                # Smooth filter
                self.load_rate_kn_min = round(0.7 * calc_load_rate + 0.3 * self.load_rate_kn_min, 3)
                self.disp_rate_mm_min = round(0.7 * calc_disp_rate + 0.3 * self.disp_rate_mm_min, 3)

        # 5. Automated Fracture Detection Rule:
        # Halts tracking processes and flags sample fracture state when force metrics drop to
        # exactly 0.0 Newtons (or <= 0.05 kN drop after established peak)
        # after an established active history log buffer sequence length exceeding 5 index frames.
        if (self.is_running and not self.is_fractured and idx > 5 and self.f_max_n > 500.0):
            # Check for force dropping to exactly 0.0 N or sudden brittle drop below 1% of peak
            if force_magnitude <= 0.001 or force_magnitude < (0.01 * self.f_max_n):
                self.is_fractured = True
                self.is_running = False
                self.state = "FRACTURED"
                self.fracture_index = idx
                self.load_rate_kn_min = 0.0
                self.disp_rate_mm_min = 0.0

        return LiveTelemetryResponse(
            sample_id=self.config.sample_id,
            time_sec=round(t, 4),
            force_n=round(tared_force, 2),
            force_kn=round(force_kn, 4),
            displacement_mm=round(disp, 4),
            stress_mpa=round(stress_mpa, 2),
            strain_ratio=round(strain_ratio, 6),
            strain_pct=round(strain_pct, 4),
            f_max_n=round(self.f_max_n, 2),
            f_max_kn=round(self.f_max_n / 1000.0, 4),
            d_peak_mm=round(self.d_peak_mm, 4),
            s_u_mpa=round(self.s_u_mpa, 2),
            load_rate_kn_min=round(self.load_rate_kn_min, 3),
            disp_rate_mm_min=round(self.disp_rate_mm_min, 3),
            is_fractured=self.is_fractured,
            safety_limit_reason=self.safety_limit_reason,
            state=self.state,
            total_data_points=len(self.time_series)
        )

    def get_full_record(self) -> Dict[str, Any]:
        """Assembles complete test matrix for reporting, compliance, and exporting."""
        return {
            "config": self.config.model_dump(),
            "f_max_n": round(self.f_max_n, 2),
            "f_max_kn": round(self.f_max_n / 1000.0, 4),
            "d_peak_mm": round(self.d_peak_mm, 4),
            "s_u_mpa": round(self.s_u_mpa, 2),
            "is_fractured": self.is_fractured,
            "safety_limit_reason": self.safety_limit_reason,
            "state": self.state,
            "data_count": len(self.time_series),
            "time_series": self.time_series,
            "force_series_n": self.force_series_n,
            "force_series_kn": self.force_series_kn,
            "disp_series_mm": self.disp_series_mm,
            "stress_series_mpa": self.stress_series_mpa,
            "strain_series_ratio": self.strain_series_ratio,
            "strain_series_pct": self.strain_series_pct
        }
