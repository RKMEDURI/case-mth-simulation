"""
CASE-MTH Interactive Web Application Backend.
Flask REST API serving real-time discrete-event simulations, carbon intensity traces,
synthetic workload stream browser, and continuum node telemetry.
"""

from flask import Flask, render_template, jsonify, request
import os
import json
import time
import numpy as np

from config import ContinuumConfig
from carbon_tracker import CarbonTracker
from workload_generator import WorkloadGenerator, TaskWorkload
from simulator_engine import DiscreteEventSimulator
from algorithms import (
    CASEMTHScheduler,
    StaticPlacementScheduler,
    LatencyAwareScheduler,
    CostOptimizationScheduler,
    GreenDVFSScheduler,
    EnergyHybridScheduler,
    MOPSOEnergyScheduler
)

app = Flask(__name__, template_folder='templates', static_folder='static')

# Global cached continuum and carbon tracker instances
DEFAULT_SEED = 42
config_instance = ContinuumConfig(seed=DEFAULT_SEED)
carbon_tracker_instance = CarbonTracker(seed=DEFAULT_SEED)
workload_generator_instance = WorkloadGenerator(num_nodes=128, seed=DEFAULT_SEED)

# Pre-generate baseline workload stream
cached_workload = workload_generator_instance.generate_workload_stream(num_tasks=3000)

@app.route('/')
def index():
    """Renders main interactive dashboard UI."""
    return render_template('index.html')

@app.route('/api/status', methods=['GET'])
def get_status():
    """Returns infrastructure continuum overview & configuration details."""
    return jsonify({
        'status': 'online',
        'num_nodes': len(config_instance.nodes),
        'edge_nodes': config_instance.NUM_EDGE_NODES,
        'private_nodes': config_instance.NUM_PRIVATE_NODES,
        'public_nodes': config_instance.NUM_PUBLIC_NODES,
        'simulation_duration_hours': 24,
        'cached_workload_size': len(cached_workload)
    })

@app.route('/api/grid-carbon', methods=['GET'])
def get_grid_carbon():
    """Returns 24-hour dynamic grid carbon intensity profiles CI_k(t)."""
    hours = np.linspace(0, 24, 144)  # Every 10 minutes
    timestamps = hours * 3600.0

    sub_regions = ['Private_DC', 'Public_Region1_Hydro', 'Public_Region2_Thermal', 'Edge_Grid']
    result = {'hours': [round(h, 2) for h in hours], 'series': {}}

    for reg in sub_regions:
        result['series'][reg] = [
            round(carbon_tracker_instance.get_carbon_intensity(reg, t), 2)
            for t in timestamps
        ]

    return jsonify(result)

@app.route('/api/nodes', methods=['GET'])
def get_nodes():
    """Returns list of 128 heterogeneous compute nodes and specs."""
    nodes_data = []
    for nid, n in config_instance.nodes.items():
        nodes_data.append({
            'node_id': n.node_id,
            'tier': n.tier,
            'sub_region': n.sub_region,
            'num_cores': n.num_cores,
            'compute_gflops': round(n.compute_gflops, 1),
            'ram_gb': n.ram_gb,
            'p_idle_watts': round(n.p_idle_watts, 1),
            'p_max_watts': round(n.p_max_watts, 1),
            'cost_per_sec': n.cost_per_sec
        })
    return jsonify(nodes_data)

@app.route('/api/generate-workload', methods=['POST'])
def generate_workload():
    """
    Regenerates global cached workload stream.
    If 'randomize': True is passed, uses a fresh time-based seed.
    Otherwise uses default fixed seed (42) for reproducible benchmarking.
    """
    global cached_workload
    data = request.json or {}
    num_tasks = int(data.get('num_tasks', 3000))
    randomize = data.get('randomize', False)
    
    if randomize:
        seed = int(time.time() * 1000) % 1000000
    else:
        seed = int(data.get('seed', DEFAULT_SEED))

    gen = WorkloadGenerator(num_nodes=128, seed=seed)
    cached_workload = gen.generate_workload_stream(num_tasks=num_tasks)
    
    return jsonify({
        'status': 'success',
        'num_tasks': len(cached_workload),
        'seed_used': seed,
        'is_randomized': randomize
    })

@app.route('/api/workload', methods=['GET'])
def get_workload():
    """
    Returns paginated synthetic workload task stream with filtering.
    Query params: trace_source, search, limit, offset, criticality
    """
    trace_source = request.args.get('trace_source', 'ALL')
    search = request.args.get('search', '').strip()
    criticality = request.args.get('criticality', 'ALL')
    limit = int(request.args.get('limit', 15))
    offset = int(request.args.get('offset', 0))

    filtered = []
    for task in cached_workload:
        if trace_source != 'ALL' and task.source_trace != trace_source:
            continue
        if criticality != 'ALL' and str(task.criticality_flag) != criticality:
            continue
        if search and search not in str(task.task_id):
            continue

        filtered.append({
            'task_id': task.task_id,
            'source_trace': task.source_trace,
            'arrival_time': round(task.arrival_time, 2),
            'cpu_demand_ratio': round(task.cpu_demand_ratio, 2),
            'ram_demand_gb': round(task.ram_demand_gb, 1),
            'gflops_required': round(task.gflops_required, 1),
            'payload_in_mb': round(task.payload_in_mb, 1),
            'payload_out_mb': round(task.payload_out_mb, 1),
            'criticality_flag': task.criticality_flag,
            'slack_factor': round(task.slack_factor, 2),
            'tau_base_sec': round(task.tau_base_sec, 2),
            'deadline': round(task.deadline, 2),
            'sovereignty_rule': task.sovereignty_rule,
            'origin_node_id': task.origin_node_id
        })

    total_count = len(filtered)
    paginated = filtered[offset:offset+limit]

    return jsonify({
        'total': total_count,
        'offset': offset,
        'limit': limit,
        'tasks': paginated
    })

@app.route('/api/run-simulation', methods=['POST'])
def run_simulation():
    """
    Executes discrete-event workload placement simulation across selected algorithms.
    """
    global cached_workload
    data = request.json or {}
    num_tasks = int(data.get('num_tasks', 3000))
    randomize = data.get('randomize', False)
    
    if randomize:
        seed = int(time.time() * 1000) % 1000000
    else:
        seed = int(data.get('seed', DEFAULT_SEED))

    # Regenerate workload if cached_workload size doesn't match requested num_tasks or if randomize is True
    if len(cached_workload) != num_tasks or randomize:
        gen = WorkloadGenerator(num_nodes=128, seed=seed)
        cached_workload = gen.generate_workload_stream(num_tasks=num_tasks)

    workload = cached_workload
    cfg = ContinuumConfig(seed=seed)
    tracker = CarbonTracker(seed=seed)
    selected = data.get('selected_algorithms', ['case_mth', 'sp', 'las', 'cos', 'green_dvfs', 'echs', 'mopso'])

    all_schedulers = {
        'case_mth': CASEMTHScheduler(cfg, tracker),
        'sp': StaticPlacementScheduler(cfg, tracker),
        'las': LatencyAwareScheduler(cfg, tracker),
        'cos': CostOptimizationScheduler(cfg, tracker),
        'green_dvfs': GreenDVFSScheduler(cfg, tracker),
        'echs': EnergyHybridScheduler(cfg, tracker),
        'mopso': MOPSOEnergyScheduler(cfg, tracker, swarm_size=20, max_iter=5)
    }

    simulator = DiscreteEventSimulator(cfg, tracker)
    results_data = []

    sp_carbon = None
    if 'sp' in selected:
        sp_res = simulator.run_simulation(all_schedulers['sp'], workload)
        sp_carbon = sp_res.total_carbon_kg

    for key in selected:
        if key not in all_schedulers:
            continue
        scheduler = all_schedulers[key]
        res = simulator.run_simulation(scheduler, workload)

        abatement = 0.0
        if sp_carbon and sp_carbon > 0:
            abatement = ((sp_carbon - res.total_carbon_kg) / sp_carbon) * 100.0

        results_data.append({
            'key': key,
            'name': res.scheduler_name,
            'total_tasks': res.total_tasks,
            'completed_tasks': res.completed_tasks,
            'sla_violations': res.sla_violations,
            'sla_violation_ratio': round(res.sla_violation_ratio, 2),
            'total_energy_kwh': round(res.total_energy_kwh, 2),
            'total_carbon_kg': round(res.total_carbon_kg, 2),
            'carbon_abatement_index': round(abatement, 2),
            'avg_turnaround_time_sec': round(res.avg_turnaround_time_sec, 2),
            'tier_distribution': res.tier_task_distribution
        })

    return jsonify({
        'status': 'success',
        'num_tasks': num_tasks,
        'seed_used': seed,
        'results': results_data
    })

if __name__ == '__main__':
    print(" [*] Starting CASE-MTH Simulation Engine Web Dashboard on http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
