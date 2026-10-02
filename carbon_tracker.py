"""
Regional Grid Carbon Trace Ingestion and Evaluation Module (Section 6.4).
Models dynamic carbon intensity curves CI_k(t) in gCO2eq/kWh for:
- Private Data Center (Industrial solar PPA offsets, 480 -> 180 gCO2eq/kWh)
- Public Cloud Region 1 (Hydro-heavy, 35 - 75 gCO2eq/kWh)
- Public Cloud Region 2 (Thermal/Coal-heavy, 580 - 820 gCO2eq/kWh)
- Edge Node Micro-Grids (Solar-battery with diesel generator triggers, 20 - 900 gCO2eq/kWh)
"""

import numpy as np
from typing import Dict, Tuple

class CarbonTracker:
    def __init__(self, simulation_duration_sec: float = 86400, seed: int = 42):
        self.duration_sec = simulation_duration_sec
        np.random.seed(seed)
        
        # Pre-generate battery state of charge (SoC) trajectory for edge microgrids
        self._init_edge_battery_state()

    def _init_edge_battery_state(self):
        """Simulates 24-hour battery State of Charge (SoC) for Edge micro-grids."""
        time_steps = int(self.duration_sec)
        self.edge_soc = np.zeros(time_steps)
        current_soc = 0.85  # Start at 85% full

        for t in range(time_steps):
            hour = (t / 3600.0) % 24.0
            # Solar charging between 07:00 and 18:00
            if 7.0 <= hour <= 18.0:
                solar_input = 0.0003 * np.sin(np.pi * (hour - 7.0) / 11.0)
            else:
                solar_input = 0.0
            
            # Base load draw
            load_draw = 0.00008 + np.random.normal(0, 0.00001)
            current_soc = np.clip(current_soc + solar_input - load_draw, 0.05, 1.0)
            self.edge_soc[t] = current_soc

    def get_carbon_intensity(self, sub_region: str, timestamp_sec: float) -> float:
        """
        Returns dynamic carbon intensity CI_k(t) in gCO2eq/kWh at a given timestamp.
        """
        t = timestamp_sec % self.duration_sec
        hour = (t / 3600.0) % 24.0

        if sub_region == 'Private_DC':
            # Baseline ~480 gCO2eq/kWh, drops to 180 between 10:00 and 16:00
            if 10.0 <= hour <= 16.0:
                solar_dip = 300.0 * np.sin(np.pi * (hour - 10.0) / 6.0)
                ci = 480.0 - solar_dip
            else:
                ci = 480.0 + 15.0 * np.sin(2 * np.pi * hour / 24.0)
            return float(np.clip(ci, 180.0, 500.0))

        elif sub_region == 'Public_Region1_Hydro':
            # Continuous low emissions averaging 35 - 75 gCO2eq/kWh
            ci = 55.0 + 18.0 * np.sin(2 * np.pi * hour / 24.0) + np.random.normal(0, 2.0)
            return float(np.clip(ci, 35.0, 75.0))

        elif sub_region == 'Public_Region2_Thermal':
            # Elevated baseline 580 - 820 gCO2eq/kWh, peak during evening (17:00 - 22:00)
            if 17.0 <= hour <= 22.0:
                peak = 200.0 * np.sin(np.pi * (hour - 17.0) / 5.0)
                ci = 620.0 + peak
            else:
                ci = 600.0 + 40.0 * np.sin(2 * np.pi * hour / 24.0)
            return float(np.clip(ci, 580.0, 820.0))

        elif sub_region == 'Edge_Grid':
            # Off-grid solar-battery with backup diesel generator trigger when SoC < 20%
            sec_idx = min(int(t), len(self.edge_soc) - 1)
            soc = self.edge_soc[sec_idx]

            if soc < 0.20:
                # Backup diesel generator triggered -> Spikes to 800 - 900 gCO2eq/kWh
                ci = 850.0 + np.random.uniform(-40.0, 50.0)
            elif 7.0 <= hour <= 17.0:
                # Direct solar generation -> 20 - 120 gCO2eq/kWh
                ci = 40.0 + 60.0 * np.random.random()
            else:
                # Battery discharge -> 150 - 350 gCO2eq/kWh
                ci = 220.0 + 50.0 * np.random.normal(0, 1.0)
            return float(np.clip(ci, 20.0, 900.0))

        else:
            return 400.0  # Default baseline fallback

    def calculate_operational_emissions(
        self, sub_region: str, start_time: float, duration_sec: float, power_watts: float
    ) -> Tuple[float, float]:
        """
        Computes energy consumed (kWh) and operational carbon emissions (kg CO2eq)
        integrated over the task execution duration.
        
        Returns:
            (energy_kwh, carbon_kg_co2eq)
        """
        if duration_sec <= 0 or power_watts <= 0:
            return 0.0, 0.0

        # Sample carbon intensity at midpoint of execution window
        mid_time = start_time + (duration_sec / 2.0)
        ci_g_per_kwh = self.get_carbon_intensity(sub_region, mid_time)

        # Energy in kWh: Power(W) * Time(s) / (1000 * 3600)
        energy_kwh = (power_watts * duration_sec) / 3.6e6

        # Carbon in kg CO2eq: Energy(kWh) * CI(gCO2eq/kWh) / 1000
        carbon_kg = (energy_kwh * ci_g_per_kwh) / 1000.0

        return energy_kwh, carbon_kg
