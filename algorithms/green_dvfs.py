"""
Green-DVFS Baseline Scheduler (Section 6.5).
Standalone localized frequency-scaling policy that throttles CPU/GPU frequencies to minimize local dynamic wattage without cross-tier workload shifting.
"""

from typing import Dict, Tuple
from .base_scheduler import BaseScheduler
from config import ContinuumConfig
from workload_generator import TaskWorkload
from carbon_tracker import CarbonTracker

class GreenDVFSScheduler(BaseScheduler):
    def __init__(self, continuum_config: ContinuumConfig, carbon_tracker: CarbonTracker):
        super().__init__("Green-DVFS", continuum_config, carbon_tracker)

    def schedule_task(
        self,
        task: TaskWorkload,
        current_time: float,
        node_availabilities: Dict[int, float]
    ) -> Tuple[int, float]:
        # Stays strictly on local origin node tier (no cross-tier shifting)
        node_id = task.origin_node_id
        node = self.config.nodes[node_id]

        avail_time = node_availabilities.get(node_id, current_time)
        start_time = max(current_time, avail_time)

        # Scale frequency down as low as possible while respecting deadline d_i
        freq_steps = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        selected_freq = 1.0

        for freq in freq_steps:
            effective_gflops = node.compute_gflops * freq
            exec_duration = task.gflops_required / effective_gflops
            finish_time = start_time + exec_duration

            if finish_time <= task.deadline:
                selected_freq = freq
                break  # Lowest valid frequency found

        return node_id, selected_freq
