"""
Master Benchmark Execution Runner.
Runs synthetic workload generation, simulates placement across all 7 paradigms,
computes metrics (C_total, E_total, SVR %, ΔC_abate %), and outputs visual plots.
"""

import time
from typing import List
import pandas as pd

from config import ContinuumConfig
from carbon_tracker import CarbonTracker
from workload_generator import WorkloadGenerator, TaskWorkload
from simulator_engine import DiscreteEventSimulator, SimulationResult
from algorithms import (
    CASEMTHScheduler,
    StaticPlacementScheduler,
    LatencyAwareScheduler,
    CostOptimizationScheduler,
    GreenDVFSScheduler,
    EnergyHybridScheduler,
    MOPSOEnergyScheduler
)
from visualization import Visualizer

def run_all_benchmarks(
    num_tasks: int = 10000, seed: int = 42, output_dir: str = '.'
) -> List[SimulationResult]:
    print(f"\n==========================================================================")
    print(f"   CASE-MTH DISCRETE-EVENT SIMULATION & PLACEMENT BENCHMARK RUNNER")
    print(f"==========================================================================")
    print(f" [*] Infrastructure Continuum: 128 Heterogeneous Compute Nodes (64 Edge, 32 Private DC, 32 Public Cloud)")
    print(f" [*] Synthetic Workload Stream: {num_tasks:,} Discrete Tasks (Borg, Alibaba PAI, DataCo)")
    print(f" [*] Simulation Duration: 24-Hour Rolling Period (86,400 sec)")
    print(f"--------------------------------------------------------------------------\n")

    # 1. Initialize Continuum & Carbon Telemetry
    config = ContinuumConfig(seed=seed)
    carbon_tracker = CarbonTracker(seed=seed)
    visualizer = Visualizer(output_dir=output_dir)

    # Plot 24-hour dynamic grid carbon profiles
    carbon_plot_path = visualizer.plot_carbon_intensity_profiles(carbon_tracker)
    print(f" [+] Generated Grid Carbon Profiles Chart: {carbon_plot_path}")

    # 2. Generate Workload Stream
    print(" [*] Generating synthetic workload stream with Stage 2 telemetry augmentation...")
    generator = WorkloadGenerator(num_nodes=128, seed=seed)
    workload = generator.generate_workload_stream(num_tasks=num_tasks)
    print(f" [+] Successfully generated {len(workload):,} tasks.")

    # 3. Instantiate Schedulers
    schedulers = [
        CASEMTHScheduler(config, carbon_tracker),
        StaticPlacementScheduler(config, carbon_tracker),
        LatencyAwareScheduler(config, carbon_tracker),
        CostOptimizationScheduler(config, carbon_tracker),
        GreenDVFSScheduler(config, carbon_tracker),
        EnergyHybridScheduler(config, carbon_tracker),
        MOPSOEnergyScheduler(config, carbon_tracker, swarm_size=30, max_iter=15)
    ]

    simulator = DiscreteEventSimulator(config, carbon_tracker)
    results: List[SimulationResult] = []

    print("\n [*] Executing Discrete-Event Placement Simulations across 7 Paradigms...")
    sp_carbon = None

    for scheduler in schedulers:
        t0 = time.time()
        res = simulator.run_simulation(scheduler, workload)
        elapsed = time.time() - t0

        if scheduler.name == "Static Placement (SP)":
            sp_carbon = res.total_carbon_kg

        results.append(res)
        print(f"     -> {scheduler.name:<30}: Carbon = {res.total_carbon_kg:8.2f} kg, Energy = {res.total_energy_kwh:6.2f} kWh, SVR = {res.sla_violation_ratio:5.2f}% ({elapsed:.2f}s)")

    # 4. Calculate Carbon Abatement Index (ΔC_abate) relative to SP baseline
    if sp_carbon and sp_carbon > 0:
        for res in results:
            delta_c = ((sp_carbon - res.total_carbon_kg) / sp_carbon) * 100.0
            res.carbon_abatement_index = delta_c

    # 5. Print Summary Table
    print(f"\n==========================================================================")
    print(f"                    SUMMARY EVALUATION METRICS TABLE")
    print(f"==========================================================================")
    
    table_data = []
    for r in results:
        table_data.append({
            'Algorithm': r.scheduler_name,
            'Carbon (kg CO2eq)': f"{r.total_carbon_kg:,.2f}",
            'Energy (kWh)': f"{r.total_energy_kwh:,.2f}",
            'SLA Violation (SVR %)': f"{r.sla_violation_ratio:.2f}%",
            'Carbon Abatement (Delta C %)': f"{r.carbon_abatement_index:+.2f}%",
            'Avg Turnaround (s)': f"{r.avg_turnaround_time_sec:.2f}"
        })

    df = pd.DataFrame(table_data)
    print(df.to_string(index=False))
    print(f"==========================================================================\n")

    # 6. Generate Plot Figures
    plot_paths = visualizer.plot_benchmark_results(results)
    for p in plot_paths:
        print(f" [+] Saved Evaluation Chart: {p}")

    return results

if __name__ == "__main__":
    run_all_benchmarks(num_tasks=5000)
