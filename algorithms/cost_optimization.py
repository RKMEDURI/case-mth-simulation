"""
Cost-Optimization Scheduling (COS) Baseline (Section 6.5).
Minimizes cloud financial expenditure by utilizing the lowest-priced instance types, ignoring carbon intensity.
"""

from typing import Dict, Tuple
from .base_scheduler import BaseScheduler
from config import ContinuumConfig
from workload_generator import TaskWorkload
from carbon_tracker import CarbonTracker

class CostOptimizationScheduler(BaseScheduler):
    def __init__(self, continuum_config: ContinuumConfig, carbon_tracker: CarbonTracker):
        super().__init__("Cost-Optimization (COS)", continuum_config, carbon_tracker)

    def schedule_task(
        self,
        task: TaskWorkload,
        current_time: float,
        node_availabilities: Dict[int, float]
    ) -> Tuple[int, float]:
        best_node_id = task.origin_node_id
        min_financial_cost = float('inf')

        for node_id, node in self.config.nodes.items():
            if not self.check_sovereignty_compliance(task, node):
                continue

            # Estimate execution duration
            exec_duration = task.gflops_required / node.compute_gflops
            # Financial cost ($/s * duration)
            cost = node.cost_per_sec * exec_duration

            if cost < min_financial_cost:
                min_financial_cost = cost
                best_node_id = node_id

        return best_node_id, 1.0
