/**
 * Discrete-Event Simulator Engine for Client-Side JS Execution.
 * Runs 100% inside user's web browser without server backend.
 */

class DiscreteEventSimulator {
    constructor(config, carbonTracker) {
        this.config = config;
        this.carbonTracker = carbonTracker;
    }

    runSimulation(scheduler, workload) {
        const nodeNextAvailable = {};
        for (let nid in this.config.nodes) {
            nodeNextAvailable[nid] = 0.0;
        }

        let completedCount = 0;
        let slaViolations = 0;
        let totalEnergyKwh = 0.0;
        let totalCarbonKg = 0.0;
        let turnaroundTimes = [];
        let tierCounts = { 'Edge': 0, 'Private': 0, 'Public': 0 };

        const totalTasks = workload.length;

        for (let i = 0; i < totalTasks; i++) {
            const task = workload[i];
            const currentTime = task.arrivalTime;

            const { targetNodeId, freqFactor } = scheduler.scheduleTask(task, currentTime, nodeNextAvailable);
            const targetNode = this.config.nodes[targetNodeId];
            const originNode = this.config.nodes[task.originNodeId];

            const linkKey = `${originNode.tier}_${targetNode.tier}`;
            const netLink = this.config.networkLinks[linkKey] || this.config.networkLinks['Public_Public'];

            const dataMb = task.payloadInMb + task.payloadOutMb;
            const netDuration = (dataMb * 8.0) / netLink.bandwidthMbps + (netLink.latencyMs / 1000.0);

            const eNetJoules = (task.payloadInMb * netLink.betaTx) + (task.payloadOutMb * netLink.betaRx);
            const eNetKwh = eNetJoules / 3.6e6;
            const ciNet = this.carbonTracker.getCarbonIntensity(targetNode.subRegion, currentTime);
            const cNetKg = (eNetKwh * ciNet) / 1000.0;

            totalEnergyKwh += eNetKwh;
            totalCarbonKg += cNetKg;

            const availTime = nodeNextAvailable[targetNodeId] || currentTime;
            const startExecTime = Math.max(currentTime, availTime) + netDuration;

            const effectiveGflops = targetNode.computeGflops * freqFactor;
            const execDuration = task.gflopsRequired / effectiveGflops;
            const finishExecTime = startExecTime + execDuration;

            nodeNextAvailable[targetNodeId] = finishExecTime;

            const powerWatts = this.config.getPowerWatts(targetNodeId, freqFactor, task.cpuDemandRatio);
            const { energyKwh, carbonKg } = this.carbonTracker.calculateOperationalEmissions(
                targetNode.subRegion, startExecTime, execDuration, powerWatts
            );

            totalEnergyKwh += energyKwh;
            totalCarbonKg += carbonKg;

            completedCount++;
            if (finishExecTime > task.deadline) {
                slaViolations++;
            }

            turnaroundTimes.push(finishExecTime - task.arrivalTime);
            tierCounts[targetNode.tier] = (tierCounts[targetNode.tier] || 0) + 1;
        }

        const svr = (slaViolations / totalTasks) * 100.0;
        const avgTurnaround = turnaroundTimes.reduce((a, b) => a + b, 0) / totalTasks;

        return {
            name: scheduler.name,
            totalTasks,
            completedTasks: completedCount,
            slaViolations,
            slaViolationRatio: Math.round(svr * 100) / 100,
            totalEnergyKwh: Math.round(totalEnergyKwh * 100) / 100,
            totalCarbonKg: Math.round(totalCarbonKg * 100) / 100,
            carbonAbatementIndex: 0.0,
            avgTurnaroundTimeSec: Math.round(avgTurnaround * 100) / 100,
            tierDistribution: tierCounts
        };
    }
}
