"""
Visualization Module for CASE-MTH Multi-Tier Simulation Results.
Generates charts for:
1. 24-Hour Grid Carbon Intensity Profiles CI_k(t)
2. Cumulative Carbon Emissions & Abatement Index
3. Energy Consumption vs SLA Deadline Violation Ratio Tradeoffs
4. Task Distribution Across Architectural Tiers (Edge, Private, Public)
"""

import matplotlib.pyplot as plt
import numpy as np
from typing import List, Dict
from carbon_tracker import CarbonTracker
from simulator_engine import SimulationResult

class Visualizer:
    def __init__(self, output_dir: str = '.'):
        self.output_dir = output_dir

    def plot_carbon_intensity_profiles(self, carbon_tracker: CarbonTracker):
        """Plots 24-hour dynamic carbon profiles CI_k(t) for all 4 sub-regions."""
        fig, ax = plt.subplots(figsize=(10, 5))
        hours = np.linspace(0, 24, 288)
        timestamps = hours * 3600.0

        sub_regions = [
            ('Private_DC', 'Private DC (Solar PPA Offset)', '#2ca02c', '-'),
            ('Public_Region1_Hydro', 'Public Region 1 (Hydro Clean)', '#1f77b4', '--'),
            ('Public_Region2_Thermal', 'Public Region 2 (Thermal Peak)', '#d62728', '-.'),
            ('Edge_Grid', 'Edge Micro-Grid (Solar-Battery & Diesel)', '#ff7f0e', ':')
        ]

        for reg_key, label, color, linestyle in sub_regions:
            ci_vals = [carbon_tracker.get_carbon_intensity(reg_key, t) for t in timestamps]
            ax.plot(hours, ci_vals, label=label, color=color, linestyle=linestyle, linewidth=2)

        ax.set_title('Regional Grid Carbon Intensity Profiles $CI_k(t)$ (24-Hour Operational Period)', fontsize=12, fontweight='bold')
        ax.set_xlabel('Time of Day (Hours)', fontsize=11)
        ax.set_ylabel(r'Carbon Intensity ($\mathrm{gCO}_2\mathrm{eq/kWh}$)', fontsize=11)
        ax.set_xlim(0, 24)
        ax.set_ylim(0, 950)
        ax.grid(True, linestyle=':', alpha=0.6)
        ax.legend(loc='upper right', framealpha=0.9)

        plt.tight_layout()
        filepath = f"{self.output_dir}/grid_carbon_profiles.png"
        plt.savefig(filepath, dpi=300)
        plt.close()
        return filepath

    def plot_benchmark_results(self, results: List[SimulationResult]):
        """Generates comprehensive comparison plots across all evaluated algorithms."""
        names = [r.scheduler_name for r in results]
        carbon_kg = [r.total_carbon_kg for r in results]
        energy_kwh = [r.total_energy_kwh for r in results]
        svr_pct = [r.sla_violation_ratio for r in results]
        abatement_pct = [r.carbon_abatement_index for r in results]

        # Colors highlighting CASE-MTH
        colors = ['#2ca02c' if 'CASE-MTH' in name else '#1f77b4' for name in names]

        # 1. Carbon Emissions & Abatement Plot
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

        bars1 = ax1.bar(names, carbon_kg, color=colors, edgecolor='black', alpha=0.85)
        ax1.set_title(r'Cumulative Carbon Emissions ($C_{\mathrm{total}}$)', fontsize=12, fontweight='bold')
        ax1.set_ylabel(r'Operational Carbon Emissions ($\mathrm{kg CO}_2\mathrm{eq}$)', fontsize=11)
        ax1.tick_params(axis='x', rotation=30)
        ax1.grid(axis='y', linestyle=':', alpha=0.6)

        for bar in bars1:
            yval = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2.0, yval + (max(carbon_kg)*0.01), f'{yval:.1f}', ha='center', va='bottom', fontsize=9)

        bars2 = ax2.bar(names, abatement_pct, color=colors, edgecolor='black', alpha=0.85)
        ax2.set_title(r'Carbon Abatement Index ($\Delta C_{\mathrm{abate}}$ % vs SP)', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Reduction in Emissions (%)', fontsize=11)
        ax2.tick_params(axis='x', rotation=30)
        ax2.grid(axis='y', linestyle=':', alpha=0.6)

        for bar in bars2:
            yval = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2.0, yval + 0.5, f'{yval:+.1f}%', ha='center', va='bottom', fontsize=9, fontweight='bold' if yval > 0 else 'normal')

        plt.tight_layout()
        filepath1 = f"{self.output_dir}/carbon_comparison.png"
        plt.savefig(filepath1, dpi=300)
        plt.close()

        # 2. Energy Consumption & SLA Violation Ratio Tradeoff Plot
        fig, (ax3, ax4) = plt.subplots(1, 2, figsize=(14, 5))

        bars3 = ax3.bar(names, energy_kwh, color='#ff7f0e', edgecolor='black', alpha=0.85)
        ax3.set_title(r'Total Energy Dissipation ($E_{\mathrm{total}}$)', fontsize=12, fontweight='bold')
        ax3.set_ylabel(r'Total Electrical Energy ($\mathrm{kWh}$)', fontsize=11)
        ax3.tick_params(axis='x', rotation=30)
        ax3.grid(axis='y', linestyle=':', alpha=0.6)

        for bar in bars3:
            yval = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2.0, yval + (max(energy_kwh)*0.01), f'{yval:.1f}', ha='center', va='bottom', fontsize=9)

        bars4 = ax4.bar(names, svr_pct, color='#d62728', edgecolor='black', alpha=0.85)
        ax4.set_title('SLA Deadline Violation Ratio (SVR %)', fontsize=12, fontweight='bold')
        ax4.set_ylabel('Violation Ratio (%)', fontsize=11)
        ax4.tick_params(axis='x', rotation=30)
        ax4.grid(axis='y', linestyle=':', alpha=0.6)

        for bar in bars4:
            yval = bar.get_height()
            ax4.text(bar.get_x() + bar.get_width()/2.0, yval + 0.2, f'{yval:.2f}%', ha='center', va='bottom', fontsize=9)

        plt.tight_layout()
        filepath2 = f"{self.output_dir}/energy_sla_tradeoff.png"
        plt.savefig(filepath2, dpi=300)
        plt.close()

        return [filepath1, filepath2]
