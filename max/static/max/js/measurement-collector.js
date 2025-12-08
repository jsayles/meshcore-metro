/**
 * Measurement Collector
 *
 * Handles collecting signal strength measurements via Pi WebSocket.
 * GPS is automatically streamed to Pi, measurements are requested on-demand.
 */

export class MeasurementCollector {
    constructor(piConnection, targetNodeId, sessionId) {
        this.piConnection = piConnection;
        this.targetNodeId = targetNodeId;
        this.sessionId = sessionId;
        this.mode = 'manual';
        this.interval = 5000; // milliseconds
        this.isCollecting = false;
        this.intervalId = null;
        this.measurementCount = 0;
        this.onMeasurement = null; // Callback for when measurement is collected

        // Listen for measurement confirmations from Pi
        this.piConnection.onMeasurementSaved = (data) => {
            this.measurementCount++;

            if (this.onMeasurement) {
                this.onMeasurement({
                    rssi: data.rssi,
                    snr: data.snr,
                    latitude: data.latitude,
                    longitude: data.longitude,
                    count: this.measurementCount
                });
            }
        };
    }

    /**
     * Set collection mode
     */
    setMode(mode) {
        this.mode = mode;
    }

    /**
     * Set collection interval (in seconds)
     */
    setInterval(seconds) {
        this.interval = seconds * 1000;
    }

    /**
     * Collect a single measurement
     *
     * With WebSocket architecture, GPS is already streaming to Pi.
     * We just need to request the Pi to combine current GPS + signal data.
     */
    async collectOnce() {
        try {
            // Request measurement from Pi
            // Pi will combine current GPS stream with radio signal data
            // The result will come back via the onMeasurementSaved callback
            this.piConnection.requestMeasurement(this.targetNodeId, this.sessionId);

        } catch (error) {
            console.error('Failed to collect measurement:', error);
            throw error;
        }
    }

    /**
     * Start continuous collection
     */
    startContinuous() {
        if (this.isCollecting) {
            return;
        }

        this.isCollecting = true;
        this.mode = 'continuous';

        // Collect immediately
        this.collectOnce().catch(error => {
            console.error('Continuous collection error:', error);
        });

        // Then collect at intervals
        this.intervalId = setInterval(() => {
            if (this.isCollecting) {
                this.collectOnce().catch(error => {
                    console.error('Continuous collection error:', error);
                });
            }
        }, this.interval);
    }

    /**
     * Stop continuous collection
     */
    stop() {
        this.isCollecting = false;
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
    }

    /**
     * Reset measurement count (for new session)
     */
    reset() {
        this.measurementCount = 0;
    }
}
