"""
Virtual UTM Machine Hardware Simulator:
Generates realistic tensile testing physical telemetry for various material specifications.
Simulates real test phases:
1. Linear Elastic Region (Young's Modulus Hooke's Law)
2. Yield Point / Plateau (Upper/Lower yield or 0.2% offset)
3. Plastic Strain Hardening (Hollomon's equation)
4. Ultimate Tensile Peak (F_max, S_u)
5. Localized Necking
6. Sudden Physical Fracture (Force drops to exactly 0.0 Newtons)
"""

import math
import random
import time
from typing import Generator, Tuple, Dict, Any

MATERIAL_PRESETS = {
    "IS_1786_FE415": {
        "name": "IS 1786 Grade Fe 415 Rebar",
        "E_gpa": 205.0,        # Young's modulus in GPa (205,000 MPa)
        "yield_stress": 435.0, # MPa (> 415 min)
        "yield_strain": 0.0022,
        "yield_plateau_strain": 0.015,
        "uts_stress": 530.0,   # MPa (> 485 min)
        "uts_strain": 0.12,
        "fracture_strain": 0.165, # 16.5% elongation (> 14.5% min)
        "necking_drop": 0.88,
    },
    "IS_1786_FE500": {
        "name": "IS 1786 Grade Fe 500 TMT",
        "E_gpa": 206.0,
        "yield_stress": 525.0, # MPa (> 500 min)
        "yield_strain": 0.0026,
        "yield_plateau_strain": 0.012,
        "uts_stress": 620.0,   # MPa (> 545 min)
        "uts_strain": 0.10,
        "fracture_strain": 0.145, # 14.5% elongation (> 12.0% min)
        "necking_drop": 0.85,
    },
    "ASTM_A36": {
        "name": "ASTM A36 Structural Carbon Steel",
        "E_gpa": 200.0,
        "yield_stress": 260.0, # MPa (> 250 min)
        "yield_strain": 0.0014,
        "yield_plateau_strain": 0.022,
        "uts_stress": 460.0,   # MPa (400-550 range)
        "uts_strain": 0.15,
        "fracture_strain": 0.23,  # 23% elongation (> 20% min)
        "necking_drop": 0.80,
    },
    "ALUMINUM_6061_T6": {
        "name": "ASTM B221 Aluminum 6061-T6",
        "E_gpa": 69.0,
        "yield_stress": 276.0, # MPa
        "yield_strain": 0.0042,
        "yield_plateau_strain": 0.0042, # Continuous curve
        "uts_stress": 315.0,   # MPa
        "uts_strain": 0.08,
        "fracture_strain": 0.125, # 12.5% elongation
        "necking_drop": 0.90,
    }
}

class VirtualUTMMachine:
    """Simulates physical load frame crosshead movement and load cell readings."""

    def __init__(self, material_key: str = "IS_1786_FE500", a_0: float = 50.0, l_0: float = 50.0, test_speed_mm_min: float = 5.0):
        self.material_key = material_key if material_key in MATERIAL_PRESETS else "IS_1786_FE500"
        self.mat = MATERIAL_PRESETS[self.material_key]
        self.a_0 = float(a_0)  # mm²
        self.l_0 = float(l_0)  # mm
        self.test_speed_mm_s = float(test_speed_mm_min) / 60.0  # mm/sec crosshead velocity
        
        self.time_sec = 0.0
        self.displacement_mm = 0.0
        self.force_n = 0.0
        self.is_fractured = False
        self.is_running = False
        self._tare_offset_force = 0.0

    def start(self):
        self.time_sec = 0.0
        self.displacement_mm = 0.0
        self.force_n = 0.0
        self.is_fractured = False
        self.is_running = True

    def stop(self):
        self.is_running = False

    def tare(self):
        """Zero the active load cell."""
        self._tare_offset_force = self.force_n

    def step(self, dt: float) -> Tuple[float, float, float]:
        """
        Advances test by dt seconds and computes (time_sec, force_n, displacement_mm).
        Outputs exactly formatted 3-element metric array.
        """
        if not self.is_running:
            return self.time_sec, max(0.0, self.force_n - self._tare_offset_force), self.displacement_mm

        if self.is_fractured:
            # Once fractured, force is strictly 0.0 Newtons
            self.time_sec += dt
            return round(self.time_sec, 3), 0.0, round(self.displacement_mm, 4)

        self.time_sec += dt
        # Crosshead moves with microscopic machine compliance and strain velocity
        self.displacement_mm += self.test_speed_mm_s * dt

        # Current engineering strain
        epsilon = self.displacement_mm / self.l_0

        mat = self.mat
        ey = mat["yield_strain"]
        ep = mat["yield_plateau_strain"]
        eu = mat["uts_strain"]
        ef = mat["fracture_strain"]
        sy = mat["yield_stress"]
        su = mat["uts_stress"]

        # 1. Linear Elastic Region
        if epsilon <= ey:
            # Hooke's law: sigma = E * epsilon
            sigma = (mat["E_gpa"] * 1000.0) * epsilon
            # Slight sensor noise (+- 0.3%)
            noise = (random.random() - 0.5) * 0.005 * sigma
            sigma += noise

        # 2. Yield Plateau Region
        elif epsilon <= ep:
            # Yield oscillation (upper and lower yield points)
            plateau_prog = (epsilon - ey) / max(0.0001, (ep - ey))
            osc = math.sin(plateau_prog * math.pi * 3.0) * (sy * 0.018)
            sigma = sy + osc + (random.random() - 0.5) * 1.5

        # 3. Strain Hardening Region
        elif epsilon <= eu:
            # Hollomon-like parabolic hardening
            prog = (epsilon - ep) / max(0.0001, (eu - ep))
            # Smooth ease-out power
            sigma = sy + (su - sy) * math.pow(prog, 0.45)
            sigma += (random.random() - 0.5) * 1.2

        # 4. Necking Region
        elif epsilon <= ef:
            # Localized necking softening down to necking drop
            prog = (epsilon - eu) / max(0.0001, (ef - eu))
            sigma = su - (su * (1.0 - mat["necking_drop"])) * math.pow(prog, 1.8)
            sigma += (random.random() - 0.5) * 1.0

        # 5. Coupon Fracture
        else:
            self.is_fractured = True
            self.force_n = 0.0
            return round(self.time_sec, 3), 0.0, round(self.displacement_mm, 4)

        # Force (N) = Stress (MPa = N/mm²) * Area (mm²)
        calc_force = max(0.0, sigma * self.a_0)
        self.force_n = calc_force
        active_force = max(0.0, calc_force - self._tare_offset_force)

        return round(self.time_sec, 3), round(active_force, 2), round(self.displacement_mm, 4)

    def generate_serial_line(self, dt: float) -> str:
        """
        Formats line string precisely matching serial telemetry:
        'Time,Force,Displacement\\r\\n'
        """
        t, f, d = self.step(dt)
        return f"{t:.3f},{f:.2f},{d:.4f}\r\n"
