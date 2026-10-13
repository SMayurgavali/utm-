"""
Generate historical benchmark records (e.g. demo02).
"""

import sys
import json
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from edge.virtual_utm import VirtualUTMMachine
from backend.math_engine import SoftwareMathEngine
from backend.schemas import TelemetryPayload, SampleConfig

def generate_record(filename: str, material_key: str, sample_id: str):
    vm = VirtualUTMMachine(material_key=material_key, a_0=50.0, l_0=50.0, test_speed_mm_min=18.0)
    cfg = SampleConfig(sample_id=sample_id, material_grade=material_key)
    engine = SoftwareMathEngine(cfg)
    engine.start_test()
    vm.start()
    
    dt = 0.04
    while engine.is_running and len(engine.time_series) < 1200:
        t, f, d = vm.step(dt)
        p = TelemetryPayload(sample_id=sample_id, time_sec=t, force_n=f, displacement_mm=d)
        engine.ingest_frame(p)
        if vm.is_fractured:
            break
            
    record = engine.get_full_record()
    out_path = Path("historical") / filename
    with open(out_path, "w") as fp:
        json.dump(record, fp, indent=2)
    print(f"Generated {out_path} with {record['data_count']} frames, Su={record['s_u_mpa']} MPa")

if __name__ == "__main__":
    generate_record("demo02.json", "IS_1786_FE500", "DEMO02-HISTORICAL-FE500")
    generate_record("fe415_benchmark.json", "IS_1786_FE415", "BENCHMARK-FE415-REF")
    generate_record("astm_a36.json", "ASTM_A36", "ASTM-A36-STRUCTURAL")
