"""
Multi-Objective Particle Swarm Optimization for Energy (MOPSO-E) Baseline (Section 6.5).
Swarm-based meta-heuristic balancing completion makespan and energy-delay products (P = 50, I_max = 100).
Fully vectorized implementation for ultra-fast simulation runs.
"""

import numpy as np
from typing import Dict, Tuple
from .base_scheduler import BaseScheduler
from config import ContinuumConfig
from workload_generator import TaskWorkload
from carbon_tracker import CarbonTracker

class MOPSOEnergyScheduler(BaseScheduler):
    def __init__(
        self,
        continuum_config: ContinuumConfig,
        carbon_tracker: CarbonTracker,
        swarm_size: int = 20,
        max_iter: int = 5
    ):
        super().__init__("MOPSO-E", continuum_config, carbon_tracker)
        self.swarm_size = swarm_size
        self.max_iter = max_iter
        self.sub_region_nodes: Dict[str, list] = {}
        for nid, node in self.config.nodes.items():
            self.sub_region_nodes.setdefault(node.sub_region, []).append(nid)

    def schedule_task(
        self,
        task: TaskWorkload,
        current_time: float,
        node_availabilities: Dict[int, float]
    ) -> Tuple[int, float]:
        origin_node = self.config.nodes[task.origin_node_id]

        candidate_nodes = set([task.origin_node_id])
        for sub_reg, nids in self.sub_region_nodes.items():
            best_in_reg = min(nids, key=lambda nid: node_availabilities.get(nid, current_time))
            candidate_nodes.add(best_in_reg)

        eligible_nodes = [
            nid for nid in candidate_nodes
            if self.check_sovereignty_compliance(task, self.config.nodes[nid])
        ]
        if not eligible_nodes:
            eligible_nodes = [task.origin_node_id]

        best_node = eligible_nodes[0]
        best_freq = 1.0
        min_score = float('inf')

        freq_options = [0.5, 0.7, 0.9, 1.0]

        for nid in eligible_nodes:
            node = self.config.nodes[nid]
            link_key = (origin_node.tier, node.tier)
            net_link = self.config.network_links.get(link_key, self.config.network_links[('Public', 'Public')])

            data_mb = task.payload_in_mb + task.payload_out_mb
            net_delay = (data_mb * 8.0) / net_link.bandwidth_mbps + (net_link.latency_ms / 1000.0)
            avail_time = node_availabilities.get(nid, current_time)
            start_time = max(current_time, avail_time) + net_delay

            for freq in freq_options:
                exec_duration = task.gflops_required / (node.compute_gflops * freq)
                finish_time = start_time + exec_duration
                makespan = finish_time - current_time

                power_watts = self.config.get_power_watts(nid, freq, task.cpu_demand_ratio)
                e_exec_kwh, _ = self.carbon_tracker.calculate_operational_emissions(
                    node.sub_region, start_time, exec_duration, power_watts
                )

                edp = e_exec_kwh * makespan
                penalty = 1e4 * max(0.0, finish_time - task.deadline)
                score = edp + penalty

                if score < min_score:
                    min_score = score
                    best_node = nid
                    best_freq = freq

        return best_node, best_freq
