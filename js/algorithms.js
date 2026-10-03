/**
 * Scheduling Algorithms Suite for Client-Side JS Engine.
 * 1. CASE-MTH (Proposed Carbon-Aware Joint DVFS-Migration)
 * 2. Static Placement (SP)
 * 3. Latency-Aware (LAS)
 * 4. Cost-Optimization (COS)
 * 5. Green-DVFS
 * 6. Energy-Conscious Hybrid (ECHS)
 * 7. MOPSO-E
 */

class BaseScheduler {
    constructor(name, config, carbonTracker) {
        this.name = name;
        this.config = config;
        this.carbonTracker = carbonTracker;
        this.subRegionNodes = {};

        for (let nid in this.config.nodes) {
            const node = this.config.nodes[nid];
            if (!this.subRegionNodes[node.subRegion]) this.subRegionNodes[node.subRegion] = [];
            this.subRegionNodes[node.subRegion].push(node.nodeId);
        }
    }

    checkSovereignty(task, node) {
        const rule = task.sovereigntyRule;
        const tier = node.tier;
        if (rule === 'Any_Tier') return true;
        if (rule === 'Restricted_Edge_Private') return tier === 'Edge' || tier === 'Private';
        if (rule === 'Private_Only') return tier === 'Private';
        if (rule === 'Edge_Only') return tier === 'Edge';
        return true;
    }
}

class CASEMTHScheduler extends BaseScheduler {
    constructor(config, carbonTracker) {
        super("CASE-MTH", config, carbonTracker);
    }

    scheduleTask(task, currentTime, nodeAvailabilities) {
        let bestNodeId = task.originNodeId;
        let bestFreq = 1.0;
        let minUtility = Infinity;

        const originNode = this.config.nodes[task.originNodeId];
        const candidateNodes = new Set([task.originNodeId]);

        for (let subReg in this.subRegionNodes) {
            const nids = this.subRegionNodes[subReg];
            let bestInReg = nids[0];
            let minAvail = Infinity;
            for (let nid of nids) {
                const avail = nodeAvailabilities[nid] || currentTime;
                if (avail < minAvail) { minAvail = avail; bestInReg = nid; }
            }
            candidateNodes.add(bestInReg);
        }

        const freqSteps = [1.0, 0.8, 0.6, 0.5];

        candidateNodes.forEach(nodeId => {
            const node = this.config.nodes[nodeId];
            if (!this.checkSovereignty(task, node)) return;

            const linkKey = `${originNode.tier}_${node.tier}`;
            const netLink = this.config.networkLinks[linkKey] || this.config.networkLinks['Public_Public'];

            const dataMb = task.payloadInMb + task.payloadOutMb;
            const netDuration = (dataMb * 8.0) / netLink.bandwidthMbps + (netLink.latencyMs / 1000.0);

            const eNetJoules = (task.payloadInMb * netLink.betaTx) + (task.payloadOutMb * netLink.betaRx);
            const eNetKwh = eNetJoules / 3.6e6;
            const ciNet = this.carbonTracker.getCarbonIntensity(node.subRegion, currentTime);
            const cNetKg = (eNetKwh * ciNet) / 1000.0;

            const availTime = nodeAvailabilities[nodeId] || currentTime;
            const startTime = Math.max(currentTime, availTime) + netDuration;

            for (let freq of freqSteps) {
                const effectiveGflops = node.computeGflops * freq;
                const execDuration = task.gflopsRequired / effectiveGflops;
                const finishTime = startTime + execDuration;

                const powerWatts = this.config.getPowerWatts(nodeId, freq, task.cpuDemandRatio);
                const { energyKwh, carbonKg } = this.carbonTracker.calculateOperationalEmissions(
                    node.subRegion, startTime, execDuration, powerWatts
                );

                const totalCarbonKg = carbonKg + cNetKg;
                const totalEnergyKwh = energyKwh + eNetKwh;

                let slackPenalty = 0.0;
                if (finishTime > task.deadline) {
                    const overdue = finishTime - task.deadline;
                    slackPenalty = task.criticalityFlag === 1 ? 1e5 * (1.0 + overdue) : 1e2 * (1.0 + overdue);
                }

                const utility = (100.0 * totalCarbonKg) + (10.0 * totalEnergyKwh) + slackPenalty;

                if (utility < minUtility) {
                    minUtility = utility;
                    bestNodeId = nodeId;
                    bestFreq = freq;
                }
            }
        });

        return { targetNodeId: bestNodeId, freqFactor: bestFreq };
    }
}

class StaticPlacementScheduler extends BaseScheduler {
    constructor(config, carbonTracker) {
        super("Static Placement (SP)", config, carbonTracker);
        this.eligibleNodeIds = Object.keys(this.config.nodes)
            .map(Number)
            .filter(nid => ['Private', 'Public'].includes(this.config.nodes[nid].tier));
        this.rrIndex = 0;
    }

    scheduleTask(task, currentTime, nodeAvailabilities) {
        const nodeId = this.eligibleNodeIds[this.rrIndex % this.eligibleNodeIds.length];
        this.rrIndex++;
        return { targetNodeId: nodeId, freqFactor: 1.0 };
    }
}

class LatencyAwareScheduler extends BaseScheduler {
    constructor(config, carbonTracker) {
        super("Latency-Aware (LAS)", config, carbonTracker);
    }

    scheduleTask(task, currentTime, nodeAvailabilities) {
        const originNode = this.config.nodes[task.originNodeId];
        let bestNodeId = task.originNodeId;
        let minDelay = Infinity;

        const candidateNodes = new Set([task.originNodeId]);
        for (let subReg in this.subRegionNodes) {
            const nids = this.subRegionNodes[subReg];
            let bestInReg = nids[0];
            let minAvail = Infinity;
            for (let nid of nids) {
                const avail = nodeAvailabilities[nid] || currentTime;
                if (avail < minAvail) { minAvail = avail; bestInReg = nid; }
            }
            candidateNodes.add(bestInReg);
        }

        candidateNodes.forEach(nodeId => {
            const node = this.config.nodes[nodeId];
            if (!this.checkSovereignty(task, node)) return;

            const linkKey = `${originNode.tier}_${node.tier}`;
            const netLink = this.config.networkLinks[linkKey] || this.config.networkLinks['Public_Public'];

            const dataMb = task.payloadInMb + task.payloadOutMb;
            const netDelay = (dataMb * 8.0) / netLink.bandwidthMbps + (netLink.latencyMs / 1000.0);
            const execDuration = task.gflopsRequired / node.computeGflops;
            const availTime = nodeAvailabilities[nodeId] || currentTime;
            const totalDelay = netDelay + Math.max(0, availTime - currentTime) + execDuration;

            if (totalDelay < minDelay) {
                minDelay = totalDelay;
                bestNodeId = nodeId;
            }
        });

        return { targetNodeId: bestNodeId, freqFactor: 1.0 };
    }
}

class CostOptimizationScheduler extends BaseScheduler {
    constructor(config, carbonTracker) {
        super("Cost-Optimization (COS)", config, carbonTracker);
    }

    scheduleTask(task, currentTime, nodeAvailabilities) {
        let bestNodeId = task.originNodeId;
        let minCost = Infinity;

        for (let nid in this.config.nodes) {
            const node = this.config.nodes[nid];
            if (!this.checkSovereignty(task, node)) continue;

            const execDuration = task.gflopsRequired / node.computeGflops;
            const cost = node.costPerSec * execDuration;

            if (cost < minCost) {
                minCost = cost;
                bestNodeId = node.nodeId;
            }
        }

        return { targetNodeId: bestNodeId, freqFactor: 1.0 };
    }
}

class GreenDVFSScheduler extends BaseScheduler {
    constructor(config, carbonTracker) {
        super("Green-DVFS", config, carbonTracker);
    }

    scheduleTask(task, currentTime, nodeAvailabilities) {
        const nodeId = task.originNodeId;
        const node = this.config.nodes[nodeId];
        const availTime = nodeAvailabilities[nodeId] || currentTime;
        const startTime = Math.max(currentTime, availTime);

        const freqSteps = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0];
        let selectedFreq = 1.0;

        for (let freq of freqSteps) {
            const execDuration = task.gflopsRequired / (node.computeGflops * freq);
            if (startTime + execDuration <= task.deadline) {
                selectedFreq = freq;
                break;
            }
        }

        return { targetNodeId: nodeId, freqFactor: selectedFreq };
    }
}

class EnergyHybridScheduler extends BaseScheduler {
    constructor(config, carbonTracker) {
        super("Energy-Conscious Hybrid (ECHS)", config, carbonTracker);
    }

    scheduleTask(task, currentTime, nodeAvailabilities) {
        let bestNodeId = task.originNodeId;
        let minGap = Infinity;

        for (let nid in this.config.nodes) {
            const node = this.config.nodes[nid];
            if (!this.checkSovereignty(task, node)) continue;

            const availTime = nodeAvailabilities[nid] || currentTime;
            if (availTime > currentTime) {
                const gap = availTime - currentTime;
                if (gap < minGap) {
                    minGap = gap;
                    bestNodeId = node.nodeId;
                }
            }
        }

        return { targetNodeId: bestNodeId, freqFactor: 1.0 };
    }
}

class MOPSOEnergyScheduler extends BaseScheduler {
    constructor(config, carbonTracker) {
        super("MOPSO-E", config, carbonTracker);
    }

    scheduleTask(task, currentTime, nodeAvailabilities) {
        const originNode = this.config.nodes[task.originNodeId];
        let bestNodeId = task.originNodeId;
        let bestFreq = 1.0;
        let minScore = Infinity;

        const candidateNodes = new Set([task.originNodeId]);
        for (let subReg in this.subRegionNodes) {
            const nids = this.subRegionNodes[subReg];
            let bestInReg = nids[0];
            let minAvail = Infinity;
            for (let nid of nids) {
                const avail = nodeAvailabilities[nid] || currentTime;
                if (avail < minAvail) { minAvail = avail; bestInReg = nid; }
            }
            candidateNodes.add(bestInReg);
        }

        const freqSteps = [0.5, 0.7, 0.9, 1.0];

        candidateNodes.forEach(nodeId => {
            const node = this.config.nodes[nodeId];
            if (!this.checkSovereignty(task, node)) return;

            const linkKey = `${originNode.tier}_${node.tier}`;
            const netLink = this.config.networkLinks[linkKey] || this.config.networkLinks['Public_Public'];

            const dataMb = task.payloadInMb + task.payloadOutMb;
            const netDelay = (dataMb * 8.0) / netLink.bandwidthMbps + (netLink.latencyMs / 1000.0);
            const availTime = nodeAvailabilities[nodeId] || currentTime;
            const startTime = Math.max(currentTime, availTime) + netDelay;

            for (let freq of freqSteps) {
                const execDuration = task.gflopsRequired / (node.computeGflops * freq);
                const finishTime = startTime + execDuration;
                const makespan = finishTime - currentTime;

                const powerWatts = this.config.getPowerWatts(nodeId, freq, task.cpuDemandRatio);
                const { energyKwh } = this.carbonTracker.calculateOperationalEmissions(
                    node.subRegion, startTime, execDuration, powerWatts
                );

                const edp = energyKwh * makespan;
                const penalty = 1e4 * Math.max(0.0, finishTime - task.deadline);
                const score = edp + penalty;

                if (score < minScore) {
                    minScore = score;
                    bestNodeId = nodeId;
                    bestFreq = freq;
                }
            }
        });

        return { targetNodeId: bestNodeId, freqFactor: bestFreq };
    }
}
