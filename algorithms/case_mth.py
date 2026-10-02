"""
CASE-MTH: Carbon-Aware Slack-Enriched Multi-Tier Hybrid Scheduling Algorithm.
Joint DVFS-Migration co-design featuring:
- Dynamic DVFS frequency scaling calibrated against SLA slack bounds
- Cross-tier workload shifting based on regional carbon intensity profiles CI_k(t)
- Spatial locality & data sovereignty compliance enforcement (R_i)
- Comprehensive multi-tier network transmission dissipation model (β_tx, β_rx)
- Optimized candidate node sampling for high-speed simulation execution.
"""

import numpy as np
from typing import Dict, Tuple
from .base_scheduler import BaseScheduler
from config import ContinuumConfig
from workload_generator import TaskWorkload
from carbon_tracker import CarbonTracker

class CASEMTHScheduler(BaseScheduler):
    def __init__(self, continuum_config: ContinuumConfig, carbon_tracker: CarbonTracker):
        super().__init__("CASE-MTH", continuum_config, carbon_tracker)
        # Pre-group candidate node indices by sub-region for rapid lookup
        self.sub_region_nodes: Dict[str, list] = {}
        for nid, node in self.config.nodes.items():
            self.sub_region_nodes.setdefault(node.sub_region, []).append(nid)

    def schedule_task(
        self,
        task: TaskWorkload,
        current_time: float,
        node_availabilities: Dict[int, float]
    ) -> Tuple[int, float]:
        best_node_id = task.origin_node_id
        best_freq = 1.0
        min_cost_utility = float('inf')

        origin_node = self.config.nodes[task.origin_node_id]

        # Select candidate nodes: origin node + representative candidate nodes from each tier/sub-region
        candidate_node_ids = set([task.origin_node_id])
        for sub_reg, nids in self.sub_region_nodes.items():
            # Pick node with earliest available time in each sub-region
            best_in_reg = min(nids, key=lambda nid: node_availabilities.get(nid, current_time))
            candidate_node_ids.add(best_in_reg)

        freq_steps = [1.0, 0.8, 0.6, 0.5]

        for node_id in candidate_node_ids:
            node = self.config.nodes[node_id]
            if not self.check_sovereignty_compliance(task, node):
                continue

            link_key = (origin_node.tier, node.tier)
            net_link = self.config.network_links.get(link_key, self.config.network_links[('Public', 'Public')])

            data_transfer_mb = task.payload_in_mb + task.payload_out_mb
            net_transfer_duration = (data_transfer_mb * 8.0) / net_link.bandwidth_mbps + (net_link.latency_ms / 1000.0)

            e_net_joules = (task.payload_in_mb * net_link.beta_tx_j_mb) + (task.payload_out_mb * net_link.beta_rx_j_mb)
            e_net_kwh = e_net_joules / 3.6e6

            ci_net = self.carbon_tracker.get_carbon_intensity(node.sub_region, current_time)
            c_net_kg = (e_net_kwh * ci_net) / 1000.0

            avail_time = node_availabilities.get(node_id, current_time)
            start_time = max(current_time, avail_time) + net_transfer_duration

            for freq in freq_steps:
                effective_gflops = node.compute_gflops * freq
                exec_duration = task.gflops_required / effective_gflops
                finish_time = start_time + exec_duration

                power_watts = self.config.get_power_watts(node_id, freq, task.cpu_demand_ratio)
                e_exec_kwh, c_exec_kg = self.carbon_tracker.calculate_operational_emissions(
                    node.sub_region, start_time, exec_duration, power_watts
                )

                total_carbon_kg = c_exec_kg + c_net_kg
                total_energy_kwh = e_exec_kwh + e_net_kwh

                slack_penalty = 0.0
                if finish_time > task.deadline:
                    overdue = finish_time - task.deadline
                    slack_penalty = 1e5 * (1.0 + overdue) if task.criticality_flag == 1 else 1e2 * (1.0 + overdue)

                # Joint Objective Utility Function
                utility = (100.0 * total_carbon_kg) + (10.0 * total_energy_kwh) + slack_penalty

                if utility < min_cost_utility:
                    min_cost_utility = utility
                    best_node_id = node_id
                    best_freq = freq

        return best_node_id, best_freq
