"""
Synthetic Workload Telemetry Generation & Augmentation Pipeline (Section 6.3).
Extracts arrival patterns and resource demands modeled after:
1. Google Borg Cluster Trace (Microservices & batch jobs)
2. Alibaba PAI Cluster Trace (GPU ML training & inference graphs)
3. DataCo Supply Chain Telemetry (Transactional & sensory workloads with strict spatial locality)

Augments with synthetic telemetry:
- Network Payloads: LogNormal(μ=3.5, σ=1.2) bounded in [0.1, 1200] MB
- Latency Criticality: Bernoulli(p=0.35)
- Deadline Bounds: d_i = a_i + τ_base * (1 + ρ_slack)
- Spatial Locality / Sovereignty Rules: R_i (GDPR compliance)
"""

import json
import numpy as np
import pandas as pd
from dataclasses import dataclass, asdict
from typing import List, Dict

@dataclass
class TaskWorkload:
    task_id: int
    source_trace: str
    arrival_time: float      # a_i (sec)
    cpu_demand_ratio: float  # u_i (0.1 - 1.0)
    ram_demand_gb: float     # μ_ram (GB)
    gflops_required: float   # C_i (GFLOPS required for execution)
    payload_in_mb: float     # D_in (MB)
    payload_out_mb: float    # D_out (MB)
    criticality_flag: int    # θ_i (1 = latency-critical, 0 = delay-tolerant)
    slack_factor: float      # ρ_slack
    tau_base_sec: float      # Baseline execution duration on nominal node
    deadline: float          # d_i (sec)
    sovereignty_rule: str    # R_i ('Any_Tier', 'Restricted_Edge_Private', 'Private_Only')
    origin_node_id: int      # Node ID where task originates

class WorkloadGenerator:
    def __init__(self, num_nodes: int = 128, seed: int = 42):
        self.num_nodes = num_nodes
        self.seed = seed
        np.random.seed(seed)

    def generate_workload_stream(
        self, num_tasks: int = 10000, duration_sec: float = 86400.0
    ) -> List[TaskWorkload]:
        """
        Generates an enriched master workload stream (W) containing Google Borg,
        Alibaba PAI, and DataCo supply chain traces with synthetic telemetry augmentation.
        """
        np.random.seed(self.seed)
        tasks: List[TaskWorkload] = []

        # Generate arrival timestamps (Non-homogeneous Poisson Process with peak daytime load)
        # Peak arrival rate around hour 14 (14:00)
        raw_arrivals = np.random.uniform(0, duration_sec, num_tasks)
        # Apply sinusoidal probability thinning to model peak work hours
        probabilities = 0.4 + 0.6 * np.sin(np.pi * (raw_arrivals / duration_sec))
        keep_mask = np.random.random(num_tasks) < probabilities
        arrivals = np.sort(raw_arrivals[keep_mask])
        
        # If thinning dropped tasks, top up to exact num_tasks
        while len(arrivals) < num_tasks:
            extra = np.random.uniform(0, duration_sec, num_tasks - len(arrivals))
            arrivals = np.sort(np.concatenate([arrivals, extra]))
        arrivals = arrivals[:num_tasks]

        for i in range(num_tasks):
            arrival_time = float(arrivals[i])
            
            # Select workload stream origin (Section 6.3)
            # 45% Google Borg, 35% Alibaba PAI, 20% DataCo Supply Chain
            trace_type = np.random.choice(
                ['Google_Borg', 'Alibaba_PAI', 'DataCo_SupplyChain'],
                p=[0.45, 0.35, 0.20]
            )

            # 1. Resource Demand Extraction (Stage 1)
            if trace_type == 'Google_Borg':
                # General-purpose microservice / batch job
                cpu_demand = float(np.random.uniform(0.1, 0.5))
                ram_demand = float(np.random.uniform(1.0, 16.0))
                gflops_required = float(np.random.uniform(5.0, 50.0))
                origin_node = int(np.random.randint(0, 64))  # Edge or local client
                sovereignty = 'Any_Tier'

            elif trace_type == 'Alibaba_PAI':
                # Compute-intensive GPU ML training/inference
                cpu_demand = float(np.random.uniform(0.6, 1.0))
                ram_demand = float(np.random.uniform(8.0, 64.0))
                gflops_required = float(np.random.uniform(100.0, 800.0))
                origin_node = int(np.random.randint(0, 96))
                sovereignty = np.random.choice(['Any_Tier', 'Restricted_Edge_Private'], p=[0.7, 0.3])

            else:  # DataCo_SupplyChain
                # Enterprise transaction & sensory telemetry with strict spatial locality
                cpu_demand = float(np.random.uniform(0.2, 0.6))
                ram_demand = float(np.random.uniform(2.0, 16.0))
                gflops_required = float(np.random.uniform(10.0, 80.0))
                origin_node = int(np.random.randint(0, 64))  # Sensory edge device
                # Strict regional privacy compliance (GDPR)
                sovereignty = np.random.choice(['Restricted_Edge_Private', 'Private_Only'], p=[0.6, 0.4])

            # 2. Synthetic Telemetry Augmentation (Stage 2)
            # Network Payloads: LogNormal(μ=3.5, σ=1.2) bounded in [0.1, 1200] MB
            d_in = float(np.clip(np.random.lognormal(mean=3.5, sigma=1.2), 0.1, 1200.0))
            d_out = float(np.clip(np.random.lognormal(mean=3.5, sigma=1.2), 0.1, 1200.0))

            # Criticality Flag: Bernoulli(p=0.35)
            criticality = int(np.random.binomial(n=1, p=0.35))

            # Deadline Bounds & Slack Factor:
            # θ_i = 1 (latency-critical): ρ_slack ∈ [0.05, 0.2]
            # θ_i = 0 (delay-tolerant): ρ_slack ∈ [0.5, 4.0]
            if criticality == 1:
                slack = float(np.random.uniform(0.05, 0.20))
            else:
                slack = float(np.random.uniform(0.50, 4.00))

            # Baseline execution duration τ_base on a nominal 50 GFLOPS compute core
            tau_base = gflops_required / 50.0  # seconds
            deadline = arrival_time + tau_base * (1.0 + slack)

            tasks.append(TaskWorkload(
                task_id=i,
                source_trace=trace_type,
                arrival_time=arrival_time,
                cpu_demand_ratio=cpu_demand,
                ram_demand_gb=ram_demand,
                gflops_required=gflops_required,
                payload_in_mb=d_in,
                payload_out_mb=d_out,
                criticality_flag=criticality,
                slack_factor=slack,
                tau_base_sec=tau_base,
                deadline=deadline,
                sovereignty_rule=sovereignty,
                origin_node_id=origin_node
            ))

        return tasks

    def save_workload_to_json(self, tasks: List[TaskWorkload], filepath: str):
        """Exports generated synthetic workload to JSON format."""
        data = [asdict(t) for t in tasks]
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    def load_workload_from_json(self, filepath: str) -> List[TaskWorkload]:
        """Loads workload from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return [TaskWorkload(**item) for item in data]
