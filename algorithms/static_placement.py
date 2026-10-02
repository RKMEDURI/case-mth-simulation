"""
Static Placement (SP) Baseline Scheduler (Section 6.5).
Static round-robin task distribution to local private or public nodes without telemetry or carbon awareness.
"""

from typing import Dict, Tuple
from .base_scheduler import BaseScheduler
from config import ContinuumConfig
from workload_generator import TaskWorkload
from carbon_tracker import CarbonTracker

class StaticPlacementScheduler(BaseScheduler):
    def __init__(self, continuum_config: ContinuumConfig, carbon_tracker: CarbonTracker):
        super().__init__("Static Placement (SP)", continuum_config, carbon_tracker)
        # Select eligible target nodes (Private and Public tiers)
        self.eligible_node_ids = [
            nid for nid, node in self.config.nodes.items()
            if node.tier in ['Private', 'Public']
        ]
        self.rr_index = 0

    def schedule_task(
        self,
        task: TaskWorkload,
        current_time: float,
        node_availabilities: Dict[int, float]
    ) -> Tuple[int, float]:
        # Round-robin selection
        node_id = self.eligible_node_ids[self.rr_index % len(self.eligible_node_ids)]
        self.rr_index += 1
        
        # Static placement always runs at maximum frequency f = 1.0
        return node_id, 1.0
