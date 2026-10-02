"""
Configuration module for CASE-MTH Multi-Tier Hybrid Continuum Simulation.
Models heterogeneous compute nodes, network link parameters, power profiles,
and discrete-event simulation defaults based on Sections 6.1 - 6.6.
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Tuple

@dataclass
class NodeConfig:
    node_id: int
    tier: str  # 'Edge', 'Private', 'Public'
    sub_region: str  # 'Edge_Grid', 'Private_DC', 'Public_Region1_Hydro', 'Public_Region2_Thermal'
    num_cores: int
    compute_gflops: float  # Ω_{j,k} in GFLOPS
    ram_gb: float          # μ_ram in GB
    p_idle_watts: float    # P_idle
    p_max_watts: float     # P_max
    cost_per_sec: float    # Financial cost rate ($/s)
    f_min: float = 0.5     # Min normalized DVFS clock factor
    f_max: float = 1.0     # Max normalized DVFS clock factor

@dataclass
class NetworkLinkConfig:
    bandwidth_mbps: float  # Bandwidth in Mbps
    latency_ms: float      # Latency in ms
    beta_tx_j_mb: float    # Energy transmission dissipation (Joules/MB)
    beta_rx_j_mb: float    # Energy reception dissipation (Joules/MB)

class ContinuumConfig:
    SIMULATION_DURATION_SEC = 86400  # 24 Hours rolling operational period
    DEFAULT_NUM_TASKS = 10000        # Scalable workload task count (e.g. 10,000 to 100,000)

    # 128 Heterogeneous Compute Nodes breakdown
    NUM_EDGE_NODES = 64
    NUM_PRIVATE_NODES = 32
    NUM_PUBLIC_NODES = 32

    def __init__(self, seed: int = 42):
        np.random.seed(seed)
        self.nodes: Dict[int, NodeConfig] = {}
        self.network_links: Dict[Tuple[str, str], NetworkLinkConfig] = {}
        self._init_nodes()
        self._init_network()

    def _init_nodes(self):
        node_id = 0

        # 1. Edge Nodes (64 nodes)
        # 4-8 ARM Cortex / Jetson Orin (15-40 GFLOPS), 8-16 GB RAM, 5W -> 35W
        for _ in range(self.NUM_EDGE_NODES):
            cores = int(np.random.choice([4, 6, 8]))
            gflops = float(np.random.uniform(15.0, 40.0))
            ram = float(np.random.choice([8.0, 12.0, 16.0]))
            p_idle = float(np.random.uniform(4.0, 6.0))
            p_max = float(np.random.uniform(30.0, 40.0))
            
            self.nodes[node_id] = NodeConfig(
                node_id=node_id,
                tier='Edge',
                sub_region='Edge_Grid',
                num_cores=cores,
                compute_gflops=gflops,
                ram_gb=ram,
                p_idle_watts=p_idle,
                p_max_watts=p_max,
                cost_per_sec=0.000005
            )
            node_id += 1

        # 2. Private Data Center Nodes (32 nodes)
        # Dual Intel Xeon Platinum (64 Cores), 256 GB RAM, 120W -> 450W, high GFLOPS (150-250)
        for _ in range(self.NUM_PRIVATE_NODES):
            cores = 64
            gflops = float(np.random.uniform(180.0, 260.0))
            ram = 256.0
            p_idle = float(np.random.uniform(110.0, 130.0))
            p_max = float(np.random.uniform(430.0, 470.0))

            self.nodes[node_id] = NodeConfig(
                node_id=node_id,
                tier='Private',
                sub_region='Private_DC',
                num_cores=cores,
                compute_gflops=gflops,
                ram_gb=ram,
                p_idle_watts=p_idle,
                p_max_watts=p_max,
                cost_per_sec=0.0  # Fixed CapEx, zero marginal cloud price
            )
            node_id += 1

        # 3. Public Cloud AZs (32 nodes)
        # Split into 16 Region 1 (Hydro) and 16 Region 2 (Thermal)
        # 16x AMD EPYC + 16x NVIDIA A100/H100, 512 GB RAM, 150W -> 700W, very high GFLOPS (400-750)
        for i in range(self.NUM_PUBLIC_NODES):
            sub_reg = 'Public_Region1_Hydro' if i < 16 else 'Public_Region2_Thermal'
            cores = 64
            gflops = float(np.random.uniform(450.0, 750.0))
            ram = 512.0
            p_idle = float(np.random.uniform(140.0, 160.0))
            p_max = float(np.random.uniform(670.0, 730.0))
            cost = 0.00015 if sub_reg == 'Public_Region1_Hydro' else 0.00011

            self.nodes[node_id] = NodeConfig(
                node_id=node_id,
                tier='Public',
                sub_region=sub_reg,
                num_cores=cores,
                compute_gflops=gflops,
                ram_gb=ram,
                p_idle_watts=p_idle,
                p_max_watts=p_max,
                cost_per_sec=cost
            )
            node_id += 1

    def _init_network(self):
        # Network links between tiers: (src_tier, dst_tier)
        # Edge to Edge (Local)
        self.network_links[('Edge', 'Edge')] = NetworkLinkConfig(
            bandwidth_mbps=100.0, latency_ms=5.0, beta_tx_j_mb=0.01, beta_rx_j_mb=0.01
        )
        # Edge to Private (4G/5G Uplink)
        self.network_links[('Edge', 'Private')] = NetworkLinkConfig(
            bandwidth_mbps=100.0, latency_ms=25.0, beta_tx_j_mb=0.06, beta_rx_j_mb=0.02
        )
        self.network_links[('Private', 'Edge')] = NetworkLinkConfig(
            bandwidth_mbps=100.0, latency_ms=25.0, beta_tx_j_mb=0.02, beta_rx_j_mb=0.06
        )
        # Edge to Public (Internet WAN)
        self.network_links[('Edge', 'Public')] = NetworkLinkConfig(
            bandwidth_mbps=100.0, latency_ms=45.0, beta_tx_j_mb=0.08, beta_rx_j_mb=0.03
        )
        self.network_links[('Public', 'Edge')] = NetworkLinkConfig(
            bandwidth_mbps=100.0, latency_ms=45.0, beta_tx_j_mb=0.03, beta_rx_j_mb=0.08
        )
        # Private to Private (Local DC SAN)
        self.network_links[('Private', 'Private')] = NetworkLinkConfig(
            bandwidth_mbps=10000.0, latency_ms=1.0, beta_tx_j_mb=0.002, beta_rx_j_mb=0.001
        )
        # Private to Public (Direct Connect / Fast WAN)
        self.network_links[('Private', 'Public')] = NetworkLinkConfig(
            bandwidth_mbps=5000.0, latency_ms=15.0, beta_tx_j_mb=0.02, beta_rx_j_mb=0.01
        )
        self.network_links[('Public', 'Private')] = NetworkLinkConfig(
            bandwidth_mbps=5000.0, latency_ms=15.0, beta_tx_j_mb=0.01, beta_rx_j_mb=0.02
        )
        # Public to Public (Cloud Backbone)
        self.network_links[('Public', 'Public')] = NetworkLinkConfig(
            bandwidth_mbps=2500.0, latency_ms=20.0, beta_tx_j_mb=0.015, beta_rx_j_mb=0.015
        )

    def get_power_watts(self, node_id: int, freq_factor: float, cpu_utilization: float) -> float:
        """
        Cubic power scaling model (Section 6.1):
        P(f, u) = P_idle + (P_max - P_idle) * (f / f_max)^3 * u
        """
        node = self.nodes[node_id]
        f_norm = np.clip(freq_factor / node.f_max, node.f_min, node.f_max)
        u_norm = np.clip(cpu_utilization, 0.0, 1.0)
        p_dynamic = (node.p_max_watts - node.p_idle_watts) * (f_norm ** 3) * u_norm
        return node.p_idle_watts + p_dynamic
