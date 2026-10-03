/**
 * Config Module for CASE-MTH GitHub Pages Standalone JS Simulator.
 * 128 Heterogeneous Compute Nodes (64 Edge, 32 Private DC, 32 Public Cloud)
 */

class ContinuumConfig {
    constructor(seed = 42) {
        this.durationSec = 86400; // 24 Hours
        this.numEdgeNodes = 64;
        this.numPrivateNodes = 32;
        this.numPublicNodes = 32;
        
        this.nodes = {};
        this.networkLinks = {};
        
        this._initNodes(seed);
        this._initNetwork();
    }

    _seededRandom(seed) {
        let x = Math.sin(seed++) * 10000;
        return x - Math.floor(x);
    }

    _initNodes(seed) {
        let nodeId = 0;
        let s = seed;

        // 1. Edge Nodes (64 nodes)
        for (let i = 0; i < this.numEdgeNodes; i++) {
            const cores = [4, 6, 8][Math.floor(this._seededRandom(s++) * 3)];
            const gflops = 15.0 + this._seededRandom(s++) * 25.0;
            const ram = [8.0, 12.0, 16.0][Math.floor(this._seededRandom(s++) * 3)];
            const pIdle = 4.0 + this._seededRandom(s++) * 2.0;
            const pMax = 30.0 + this._seededRandom(s++) * 10.0;

            this.nodes[nodeId] = {
                nodeId, tier: 'Edge', subRegion: 'Edge_Grid', numCores: cores,
                computeGflops: gflops, ramGb: ram, pIdleWatts: pIdle, pMaxWatts: pMax,
                costPerSec: 0.000005, fMin: 0.5, fMax: 1.0
            };
            nodeId++;
        }

        // 2. Private DC Nodes (32 nodes)
        for (let i = 0; i < this.numPrivateNodes; i++) {
            const gflops = 180.0 + this._seededRandom(s++) * 80.0;
            const pIdle = 110.0 + this._seededRandom(s++) * 20.0;
            const pMax = 430.0 + this._seededRandom(s++) * 40.0;

            this.nodes[nodeId] = {
                nodeId, tier: 'Private', subRegion: 'Private_DC', numCores: 64,
                computeGflops: gflops, ramGb: 256.0, pIdleWatts: pIdle, pMaxWatts: pMax,
                costPerSec: 0.0, fMin: 0.5, fMax: 1.0
            };
            nodeId++;
        }

        // 3. Public Cloud Nodes (32 nodes: 16 Hydro, 16 Thermal)
        for (let i = 0; i < this.numPublicNodes; i++) {
            const subReg = i < 16 ? 'Public_Region1_Hydro' : 'Public_Region2_Thermal';
            const gflops = 450.0 + this._seededRandom(s++) * 300.0;
            const pIdle = 140.0 + this._seededRandom(s++) * 20.0;
            const pMax = 670.0 + this._seededRandom(s++) * 60.0;
            const cost = subReg === 'Public_Region1_Hydro' ? 0.00015 : 0.00011;

            this.nodes[nodeId] = {
                nodeId, tier: 'Public', subRegion: subReg, numCores: 64,
                computeGflops: gflops, ramGb: 512.0, pIdleWatts: pIdle, pMaxWatts: pMax,
                costPerSec: cost, fMin: 0.5, fMax: 1.0
            };
            nodeId++;
        }
    }

    _initNetwork() {
        this.networkLinks['Edge_Edge'] = { bandwidthMbps: 100.0, latencyMs: 5.0, betaTx: 0.01, betaRx: 0.01 };
        this.networkLinks['Edge_Private'] = { bandwidthMbps: 100.0, latencyMs: 25.0, betaTx: 0.06, betaRx: 0.02 };
        this.networkLinks['Private_Edge'] = { bandwidthMbps: 100.0, latencyMs: 25.0, betaTx: 0.02, betaRx: 0.06 };
        this.networkLinks['Edge_Public'] = { bandwidthMbps: 100.0, latencyMs: 45.0, betaTx: 0.08, betaRx: 0.03 };
        this.networkLinks['Public_Edge'] = { bandwidthMbps: 100.0, latencyMs: 45.0, betaTx: 0.03, betaRx: 0.08 };
        this.networkLinks['Private_Private'] = { bandwidthMbps: 10000.0, latencyMs: 1.0, betaTx: 0.002, betaRx: 0.001 };
        this.networkLinks['Private_Public'] = { bandwidthMbps: 5000.0, latencyMs: 15.0, betaTx: 0.02, betaRx: 0.01 };
        this.networkLinks['Public_Private'] = { bandwidthMbps: 5000.0, latencyMs: 15.0, betaTx: 0.01, betaRx: 0.02 };
        this.networkLinks['Public_Public'] = { bandwidthMbps: 2500.0, latencyMs: 20.0, betaTx: 0.015, betaRx: 0.015 };
    }

    getPowerWatts(nodeId, freqFactor, cpuUtil) {
        const node = this.nodes[nodeId];
        const fNorm = Math.max(node.fMin, Math.min(node.fMax, freqFactor / node.fMax));
        const uNorm = Math.max(0.0, Math.min(1.0, cpuUtil));
        const pDynamic = (node.pMaxWatts - node.pIdleWatts) * Math.pow(fNorm, 3) * uNorm;
        return node.pIdleWatts + pDynamic;
    }
}
