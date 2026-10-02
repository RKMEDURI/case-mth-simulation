"""
Latency-Aware Scheduling (LAS) Baseline (Section 6.5).
Prioritizes minimum communication hop and execution delay, routing tasks strictly to the highest-frequency available core.
"""

from typing import Dict, Tuple
from .base_scheduler import BaseScheduler
from config import ContinuumConfig
from workload_generator import TaskWorkload
from carbon_tracker import CarbonTracker

class LatencyAwareScheduler(BaseScheduler):
    def __init__(self, continuum_config: ContinuumConfig, carbon_tracker: CarbonTracker):
        super().__init__("Latency-Aware (LAS)", continuum_config, carbon_tracker)
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
        best_node_id = task.origin_node_id
        min_total_delay = float('inf')

        candidate_nodes = set([task.origin_node_id])
        for sub_reg, nids in self.sub_region_nodes.items():
            best_in_reg = min(nids, key=lambda nid: node_availabilities.get(nid, current_time))
            candidate_nodes.add(best_in_reg)

        for node_id in candidate_nodes:
            node = self.config.nodes[node_id]
            if not self.check_sovereignty_compliance(task, node):
                continue

            link_key = (origin_node.tier, node.tier)
            net_link = self.config.network_links.get(link_key, self.config.network_links[('Public', 'Public')])

            data_transfer_mb = task.payload_in_mb + task.payload_out_mb
            net_delay = (data_transfer_mb * 8.0) / net_link.bandwidth_mbps + (net_link.latency_ms / 1000.0)

            exec_duration = task.gflops_required / node.compute_gflops
            avail_time = node_availabilities.get(node_id, current_time)
            queue_delay = max(0.0, avail_time - current_time)

            total_delay = net_delay + queue_delay + exec_duration
            if total_delay < min_total_delay:
                min_total_delay = total_delay
                best_node_id = node_id

        return best_node_id, 1.0
