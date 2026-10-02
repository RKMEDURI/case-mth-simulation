"""
Energy-Conscious Hybrid Scheduling (ECHS) Baseline (Section 6.5).
Macro-level heuristic prioritizing server consolidation and bin-packing to maximize node sleep states, lacking WAN energy accounting.
"""

from typing import Dict, Tuple
from .base_scheduler import BaseScheduler
from config import ContinuumConfig
from workload_generator import TaskWorkload
from carbon_tracker import CarbonTracker

class EnergyHybridScheduler(BaseScheduler):
    def __init__(self, continuum_config: ContinuumConfig, carbon_tracker: CarbonTracker):
        super().__init__("Energy-Conscious Hybrid (ECHS)", continuum_config, carbon_tracker)

    def schedule_task(
        self,
        task: TaskWorkload,
        current_time: float,
        node_availabilities: Dict[int, float]
    ) -> Tuple[int, float]:
        # Bin-packing heuristic: prefers already active/busy nodes to maximize sleep states for idle nodes
        best_node_id = task.origin_node_id
        min_idle_delta = float('inf')

        # Filter nodes by sovereignty compliance
        for node_id, node in self.config.nodes.items():
            if not self.check_sovereignty_compliance(task, node):
                continue

            avail_time = node_availabilities.get(node_id, current_time)
            # Active node metric: node is busy until avail_time
            if avail_time > current_time:
                # Prefer node with smallest queue gap
                gap = avail_time - current_time
                if gap < min_idle_delta:
                    min_idle_delta = gap
                    best_node_id = node_id

        # If no active node candidate found, fall back to first available node in Private DC
        if min_idle_delta == float('inf'):
            private_nodes = [nid for nid, n in self.config.nodes.items() if n.tier == 'Private']
            best_node_id = private_nodes[0] if private_nodes else task.origin_node_id

        return best_node_id, 1.0
