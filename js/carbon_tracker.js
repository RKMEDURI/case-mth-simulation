/**
 * Carbon Tracker Module for Client-Side JS Simulation Engine.
 * Dynamic 24-Hour Regional Grid Carbon Intensity Curves CI_k(t)
 */

class CarbonTracker {
    constructor(durationSec = 86400, seed = 42) {
        this.durationSec = durationSec;
        this.edgeSoc = new Float32Array(durationSec);
        this._initEdgeBattery(seed);
    }

    _initEdgeBattery(seed) {
        let currentSoc = 0.85;
        for (let t = 0; t < this.durationSec; t++) {
            const hour = (t / 3600.0) % 24.0;
            const solarInput = (hour >= 7.0 && hour <= 18.0) ? 0.0003 * Math.sin(Math.PI * (hour - 7.0) / 11.0) : 0.0;
            const loadDraw = 0.00008;
            currentSoc = Math.max(0.05, Math.min(1.0, currentSoc + solarInput - loadDraw));
            this.edgeSoc[t] = currentSoc;
        }
    }

    getCarbonIntensity(subRegion, timestampSec) {
        const t = timestampSec % this.durationSec;
        const hour = (t / 3600.0) % 24.0;

        if (subRegion === 'Private_DC') {
            if (hour >= 10.0 && hour <= 16.0) {
                const solarDip = 300.0 * Math.sin(Math.PI * (hour - 10.0) / 6.0);
                return Math.max(180.0, Math.min(500.0, 480.0 - solarDip));
            }
            return Math.max(180.0, Math.min(500.0, 480.0 + 15.0 * Math.sin(2 * Math.PI * hour / 24.0)));
        } else if (subRegion === 'Public_Region1_Hydro') {
            return Math.max(35.0, Math.min(75.0, 55.0 + 18.0 * Math.sin(2 * Math.PI * hour / 24.0)));
        } else if (subRegion === 'Public_Region2_Thermal') {
            if (hour >= 17.0 && hour <= 22.0) {
                const peak = 200.0 * Math.sin(Math.PI * (hour - 17.0) / 5.0);
                return Math.max(580.0, Math.min(820.0, 620.0 + peak));
            }
            return Math.max(580.0, Math.min(820.0, 600.0 + 40.0 * Math.sin(2 * Math.PI * hour / 24.0)));
        } else if (subRegion === 'Edge_Grid') {
            const secIdx = Math.min(Math.floor(t), this.edgeSoc.length - 1);
            const soc = this.edgeSoc[secIdx];
            if (soc < 0.20) return 850.0;
            if (hour >= 7.0 && hour <= 17.0) return 70.0;
            return 220.0;
        }
        return 400.0;
    }

    calculateOperationalEmissions(subRegion, startTime, durationSec, powerWatts) {
        if (durationSec <= 0 || powerWatts <= 0) return { energyKwh: 0.0, carbonKg: 0.0 };
        const midTime = startTime + (durationSec / 2.0);
        const ciGPerKwh = this.getCarbonIntensity(subRegion, midTime);
        const energyKwh = (powerWatts * durationSec) / 3.6e6;
        const carbonKg = (energyKwh * ciGPerKwh) / 1000.0;
        return { energyKwh, carbonKg };
    }
}
