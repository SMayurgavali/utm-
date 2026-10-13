"""
Phase 2: Pydantic Validation Guard & JSON Streaming Payload Syntax
{ "sample_id": "STRING", "time_sec": FLOAT, "force_n": FLOAT, "displacement_mm": FLOAT }
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field

class TelemetryPayload(BaseModel):
    """Exact required architectural JSON streaming payload syntax."""
    sample_id: str = Field(..., description="Unique coupon / sample identifier string")
    time_sec: float = Field(..., description="Continuous elapsed processing timeline parameter in seconds")
    force_n: float = Field(..., description="Active Force Metric in Newtons")
    displacement_mm: float = Field(..., description="Active Displacement Metric in millimeters")

class SampleConfig(BaseModel):
    """Specimen baseline profiling parameter configuration."""
    sample_id: str = ""
    company_name: str = ""
    system_serial_number: str = ""
    test_mode: Literal["tension", "compression"] = "tension"
    data_source: Literal["virtual", "serial"] = "virtual"
    material_grade: str = "IS_1786_FE500"
    standard: str = "IS 1786"  # IS 1608, IS 1786, ASTM E8
    geometry: Literal["round", "flat"] = "round"
    width_mm: Optional[float] = Field(default=None, gt=0)
    thickness_mm: Optional[float] = Field(default=None, gt=0)
    a_0: float = Field(50.0, gt=0, description="Measured cross-sectional area in mm²")
    l_0: float = Field(50.0, gt=0, description="Measured initial gauge length in mm")
    control_mode: Literal["crosshead_speed", "load_rate"] = "crosshead_speed"
    crosshead_speed_mm_min: Optional[float] = Field(default=None, gt=0)
    load_rate_setpoint_kn_min: Optional[float] = Field(default=None, gt=0)
    max_load_n: Optional[float] = Field(default=None, gt=0)
    max_travel_mm: Optional[float] = Field(default=None, gt=0)
    operator_name: str = ""
    inspector_name: str = ""
    witness_name: str = ""

class LiveTelemetryResponse(BaseModel):
    """Derived engineering metrics broadcasted to frontend panels."""
    sample_id: str
    time_sec: float
    force_n: float
    force_kn: float
    displacement_mm: float
    stress_mpa: float
    strain_ratio: float
    strain_pct: float
    f_max_n: float
    f_max_kn: float
    d_peak_mm: float
    s_u_mpa: float
    load_rate_kn_min: float
    disp_rate_mm_min: float
    is_fractured: bool
    safety_limit_reason: Optional[str] = None
    state: str  # IDLE, RUNNING, FRACTURED, COMPLETED, STOPPED
    total_data_points: int

class ComplianceResult(BaseModel):
    standard: str
    material_grade: str
    sample_id: str
    is_compliant: bool
    evaluation_applicable: bool = True
    youngs_modulus_gpa: float
    yield_stress_mpa: float
    yield_threshold_min: float
    uts_mpa: float
    uts_threshold_min: float
    ts_ys_ratio: float
    ratio_threshold_min: float
    elongation_pct: float
    toughness_mj_m3: float
    elongation_threshold_min: float
    evaluation_clauses: List[Dict[str, Any]]
    executive_narrative: str
    audit_hash_sha256: str
