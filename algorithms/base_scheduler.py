"""
Base abstract class for all workload placement & scheduling algorithms.
"""

from abc import ABC, abstractmethod
from typing import Dict, Tuple, Any
from config import ContinuumConfig, NodeConfig
from workload_generator import TaskWorkload
from carbon_tracker import CarbonTracker

class BaseScheduler(ABC):
    def __init__(self, name: str, continuum_config: ContinuumConfig, carbon_tracker: CarbonTracker):
        self.name = name
        self.config = continuum_config
        self.carbon_tracker = carbon_tracker

    def check_sovereignty_compliance(self, task: TaskWorkload, target_node: NodeConfig) -> bool:
        """Enforces spatial locality & data sovereignty compliance rules R_i."""
        rule = task.sovereignty_rule
        tier = target_node.tier
        
        if rule == 'Any_Tier':
            return True
        elif rule == 'Restricted_Edge_Private':
            return tier in ['Edge', 'Private']
        elif rule == 'Private_Only':
            return tier == 'Private'
        elif rule == 'Edge_Only':
            return tier == 'Edge'
        return True

    @abstractmethod
    def schedule_task(
        self,
        task: TaskWorkload,
        current_time: float,
        node_availabilities: Dict[int, float]  # Map of node_id -> next available time (sec)
    ) -> Tuple[int, float]:
        """
        Determines target node ID and DVFS clock frequency scaling factor f ∈ [0.5, 1.0].
        
        Returns:
            (target_node_id, dvfs_frequency_factor)
        """
        pass
