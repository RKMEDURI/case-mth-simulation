"""
CASE-MTH Main CLI Entry Point.
Provides command-line arguments to generate synthetic workload traces,
execute discrete-event workload placement simulation runs, and generate plots.
"""

import argparse
import sys
import os

from config import ContinuumConfig
from carbon_tracker import CarbonTracker
from workload_generator import WorkloadGenerator
from simulator_engine import DiscreteEventSimulator
from run_benchmarks import run_all_benchmarks
from algorithms import (
    CASEMTHScheduler,
    StaticPlacementScheduler,
    LatencyAwareScheduler,
    CostOptimizationScheduler,
    GreenDVFSScheduler,
    EnergyHybridScheduler,
    MOPSOEnergyScheduler
)

def main():
    parser = argparse.ArgumentParser(
        description="CASE-MTH Synthetic Workload Generator & Discrete-Event Workload Placement Simulator"
    )
    parser.add_argument(
        '--run-benchmarks', action='store_true',
        help="Run full benchmark suite comparing CASE-MTH against 6 baseline algorithms."
    )
    parser.add_argument(
        '--generate-workload', action='store_true',
        help="Generate synthetic workload stream and save to JSON."
    )
    parser.add_argument(
        '--tasks', type=int, default=5000,
        help="Number of discrete tasks to simulate (Default: 5000)."
    )
    parser.add_argument(
        '--algorithm', type=str, choices=['case_mth', 'sp', 'las', 'cos', 'green_dvfs', 'echs', 'mopso'],
        help="Run simulation for a single specific algorithm."
    )
    parser.add_argument(
        '--output-dir', type=str, default='.',
        help="Output directory for generated plots and data files."
    )
    parser.add_argument(
        '--seed', type=int, default=42,
        help="Random seed for reproducibility."
    )

    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    if args.generate_workload:
        print(f" [*] Generating synthetic workload dataset with {args.tasks:,} tasks...")
        generator = WorkloadGenerator(num_nodes=128, seed=args.seed)
        tasks = generator.generate_workload_stream(num_tasks=args.tasks)
        out_file = os.path.join(args.output_dir, "synthetic_workload.json")
        generator.save_workload_to_json(tasks, out_file)
        print(f" [+] Workload saved to {out_file}")

    if args.algorithm:
        print(f" [*] Running simulation for single algorithm: {args.algorithm}")
        config = ContinuumConfig(seed=args.seed)
        carbon_tracker = CarbonTracker(seed=args.seed)
        generator = WorkloadGenerator(num_nodes=128, seed=args.seed)
        workload = generator.generate_workload_stream(num_tasks=args.tasks)

        sched_map = {
            'case_mth': CASEMTHScheduler(config, carbon_tracker),
            'sp': StaticPlacementScheduler(config, carbon_tracker),
            'las': LatencyAwareScheduler(config, carbon_tracker),
            'cos': CostOptimizationScheduler(config, carbon_tracker),
            'green_dvfs': GreenDVFSScheduler(config, carbon_tracker),
            'echs': EnergyHybridScheduler(config, carbon_tracker),
            'mopso': MOPSOEnergyScheduler(config, carbon_tracker)
        }

        scheduler = sched_map[args.algorithm]
        simulator = DiscreteEventSimulator(config, carbon_tracker)
        res = simulator.run_simulation(scheduler, workload)

        print("\n--- Simulation Result ---")
        print(f" Algorithm         : {res.scheduler_name}")
        print(f" Total Tasks       : {res.total_tasks:,}")
        print(f" Carbon Emissions  : {res.total_carbon_kg:,.2f} kg CO2eq")
        print(f" Energy Dissipation: {res.total_energy_kwh:,.2f} kWh")
        print(f" SLA Violation Rate: {res.sla_violation_ratio:.2f}%")

    if args.run_benchmarks or (not args.generate_workload and not args.algorithm):
        # Default behavior if no specific mode flag passed: run full benchmark suite
        run_all_benchmarks(num_tasks=args.tasks, seed=args.seed, output_dir=args.output_dir)

if __name__ == '__main__':
    main()
