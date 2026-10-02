"""
Discrete-Event Simulation Engine Core (Section 6.1).
Orchestrates global discrete-event queue across four decoupled layers:
1. Event Management Core (Priority queue for arrivals, state transitions, telemetry)
2. DVFS Processor & Thermal Emulator (Cubic power scaling formulation)
3. Network Fabric Emulator (Bandwidth queuing, latency, WAN energy dissipation)
4. Carbon Tracking & Synchronization Engine (Millisecond-granularity emissions)
"""

import heapq
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Any
import numpy as np

from config import ContinuumConfig
from workload_generator import TaskWorkload
from carbon_tracker import CarbonTracker
from algorithms import BaseScheduler

@dataclass(order=True)
class Event:
    timestamp: float
    event_type: str = field(compare=False)
    task: TaskWorkload = field(compare=False)
    node_id: int = field(compare=False)
    freq_factor: float = field(compare=False)
    extra_data: Dict[str, Any] = field(default_factory=dict, compare=False)

@dataclass
class SimulationResult:
    scheduler_name: str
    total_tasks: int
    completed_tasks: int
    sla_violations: int
    sla_violation_ratio: float  # SVR %
    total_energy_kwh: float     # E_total in kWh
    total_carbon_kg: float      # C_total in kg CO2eq
    carbon_abatement_index: float = 0.0  # ΔC_abate %
    avg_turnaround_time_sec: float = 0.0
    tier_task_distribution: Dict[str, int] = field(default_factory=dict)

class DiscreteEventSimulator:
    def __init__(self, continuum_config: ContinuumConfig, carbon_tracker: CarbonTracker):
        self.config = continuum_config
        self.carbon_tracker = carbon_tracker

    def run_simulation(
        self, scheduler: BaseScheduler, workload: List[TaskWorkload]
    ) -> SimulationResult:
        """
        Executes discrete-event simulation run for a given workload stream and scheduler.
        """
        event_queue: List[Event] = []
        node_next_available: Dict[int, float] = {nid: 0.0 for nid in self.config.nodes.keys()}
        
        # Enqueue initial task arrivals
        for task in workload:
            heapq.heappush(
                event_queue,
                Event(
                    timestamp=task.arrival_time,
                    event_type='TASK_ARRIVAL',
                    task=task,
                    node_id=-1,
                    freq_factor=1.0
                )
            )

        completed_count = 0
        sla_violations = 0
        total_energy_kwh = 0.0
        total_carbon_kg = 0.0
        turnaround_times = []
        tier_counts = {'Edge': 0, 'Private': 0, 'Public': 0}

        while event_queue:
            evt = heapq.heappop(event_queue)
            current_time = evt.timestamp
            task = evt.task

            if evt.event_type == 'TASK_ARRIVAL':
                # 1. Invoke Scheduler to select target node & DVFS clock frequency
                target_node_id, freq = scheduler.schedule_task(task, current_time, node_next_available)
                target_node = self.config.nodes[target_node_id]
                origin_node = self.config.nodes[task.origin_node_id]

                # 2. Network Transmission Dissipation & Latency
                link_key = (origin_node.tier, target_node.tier)
                net_link = self.config.network_links.get(link_key, self.config.network_links[('Public', 'Public')])

                data_mb = task.payload_in_mb + task.payload_out_mb
                net_duration = (data_mb * 8.0) / net_link.bandwidth_mbps + (net_link.latency_ms / 1000.0)

                # Network Energy and Carbon
                e_net_joules = (task.payload_in_mb * net_link.beta_tx_j_mb) + (task.payload_out_mb * net_link.beta_rx_j_mb)
                e_net_kwh = e_net_joules / 3.6e6
                ci_net = self.carbon_tracker.get_carbon_intensity(target_node.sub_region, current_time)
                c_net_kg = (e_net_kwh * ci_net) / 1000.0

                total_energy_kwh += e_net_kwh
                total_carbon_kg += c_net_kg

                # Schedule execution start time taking queue delay into account
                avail_time = node_next_available[target_node_id]
                start_exec_time = max(current_time, avail_time) + net_duration

                # 3. Compute Execution Duration and Power
                effective_gflops = target_node.compute_gflops * freq
                exec_duration = task.gflops_required / effective_gflops
                finish_exec_time = start_exec_time + exec_duration

                # Update node queue availability
                node_next_available[target_node_id] = finish_exec_time

                # Enqueue finish event
                heapq.heappush(
                    event_queue,
                    Event(
                        timestamp=finish_exec_time,
                        event_type='TASK_FINISH',
                        task=task,
                        node_id=target_node_id,
                        freq_factor=freq,
                        extra_data={
                            'start_time': start_exec_time,
                            'duration': exec_duration,
                            'net_duration': net_duration
                        }
                    )
                )

            elif evt.event_type == 'TASK_FINISH':
                completed_count += 1
                node_id = evt.node_id
                node = self.config.nodes[node_id]
                freq = evt.freq_factor

                start_time = evt.extra_data['start_time']
                duration = evt.extra_data['duration']

                # Compute power and carbon emissions for execution
                power_watts = self.config.get_power_watts(node_id, freq, task.cpu_demand_ratio)
                e_exec_kwh, c_exec_kg = self.carbon_tracker.calculate_operational_emissions(
                    node.sub_region, start_time, duration, power_watts
                )

                total_energy_kwh += e_exec_kwh
                total_carbon_kg += c_exec_kg

                # SLA Check
                if current_time > task.deadline:
                    sla_violations += 1

                turnaround = current_time - task.arrival_time
                turnaround_times.append(turnaround)
                tier_counts[node.tier] = tier_counts.get(node.tier, 0) + 1

        total_tasks = len(workload)
        svr = (sla_violations / total_tasks * 100.0) if total_tasks > 0 else 0.0
        avg_turnaround = float(np.mean(turnaround_times)) if turnaround_times else 0.0

        return SimulationResult(
            scheduler_name=scheduler.name,
            total_tasks=total_tasks,
            completed_tasks=completed_count,
            sla_violations=sla_violations,
            sla_violation_ratio=svr,
            total_energy_kwh=total_energy_kwh,
            total_carbon_kg=total_carbon_kg,
            carbon_abatement_index=0.0,  # Computed after comparing with Static Placement (SP) baseline
            avg_turnaround_time_sec=avg_turnaround,
            tier_task_distribution=tier_counts
        )
