/**
 * Workload Generator Module for Client-Side JS Simulator.
 * Synthesizes Borg, Alibaba PAI, DataCo supply chain traces.
 */

class WorkloadGenerator {
    constructor(numNodes = 128, seed = 42) {
        this.numNodes = numNodes;
        this.seed = seed;
    }

    _seededRandom(s) {
        let x = Math.sin(s) * 10000;
        return x - Math.floor(x);
    }

    generateWorkloadStream(numTasks = 3000, durationSec = 86400.0) {
        let s = this.seed;
        const tasks = [];

        for (let i = 0; i < numTasks; i++) {
            const arrivalTime = (i / numTasks) * durationSec;
            const randVal = this._seededRandom(s++);

            let traceType = 'Google_Borg';
            if (randVal > 0.45 && randVal <= 0.80) traceType = 'Alibaba_PAI';
            else if (randVal > 0.80) traceType = 'DataCo_SupplyChain';

            let cpuDemand, ramDemand, gflopsRequired, originNode, sovereignty;

            if (traceType === 'Google_Borg') {
                cpuDemand = 0.1 + this._seededRandom(s++) * 0.4;
                ramDemand = 1.0 + this._seededRandom(s++) * 15.0;
                gflopsRequired = 5.0 + this._seededRandom(s++) * 45.0;
                originNode = Math.floor(this._seededRandom(s++) * 64);
                sovereignty = 'Any_Tier';
            } else if (traceType === 'Alibaba_PAI') {
                cpuDemand = 0.6 + this._seededRandom(s++) * 0.4;
                ramDemand = 8.0 + this._seededRandom(s++) * 56.0;
                gflopsRequired = 100.0 + this._seededRandom(s++) * 700.0;
                originNode = Math.floor(this._seededRandom(s++) * 96);
                sovereignty = this._seededRandom(s++) > 0.3 ? 'Any_Tier' : 'Restricted_Edge_Private';
            } else {
                cpuDemand = 0.2 + this._seededRandom(s++) * 0.4;
                ramDemand = 2.0 + this._seededRandom(s++) * 14.0;
                gflopsRequired = 10.0 + this._seededRandom(s++) * 70.0;
                originNode = Math.floor(this._seededRandom(s++) * 64);
                sovereignty = this._seededRandom(s++) > 0.4 ? 'Restricted_Edge_Private' : 'Private_Only';
            }

            const dIn = 0.1 + this._seededRandom(s++) * 500.0;
            const dOut = 0.1 + this._seededRandom(s++) * 500.0;
            const criticality = this._seededRandom(s++) < 0.35 ? 1 : 0;
            const slack = criticality === 1 ? (0.05 + this._seededRandom(s++) * 0.15) : (0.50 + this._seededRandom(s++) * 3.50);

            const tauBase = gflopsRequired / 50.0;
            const deadline = arrivalTime + tauBase * (1.0 + slack);

            tasks.push({
                taskId: i,
                sourceTrace: traceType,
                arrivalTime: Math.round(arrivalTime * 100) / 100,
                cpuDemandRatio: Math.round(cpuDemand * 100) / 100,
                ramDemandGb: Math.round(ramDemand * 10) / 10,
                gflopsRequired: Math.round(gflopsRequired * 10) / 10,
                payloadInMb: Math.round(dIn * 10) / 10,
                payloadOutMb: Math.round(dOut * 10) / 10,
                criticalityFlag: criticality,
                slackFactor: Math.round(slack * 100) / 100,
                tauBaseSec: Math.round(tauBase * 100) / 100,
                deadline: Math.round(deadline * 100) / 100,
                sovereigntyRule: sovereignty,
                originNodeId: originNode
            });
        }

        return tasks;
    }
}
