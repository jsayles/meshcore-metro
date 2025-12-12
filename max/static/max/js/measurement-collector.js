/**
 * Measurement Collector
 *
 * Handles collecting signal strength measurements via Pi WebSocket.
 * GPS is automatically streamed to Pi, measurements are requested on-demand.
 */

export class MeasurementCollector {
    constructor(piConnection, sessionId) {
        this.piConnection = piConnection;
        this.sessionId = sessionId;
        this.mode = 'manual';
        this.interval = 5000; // milliseconds
        this.isCollecting = false;
        this.intervalId = null;
        this.measurementCount = 0;
        this.onMeasurement = null; // Callback for when measurement is collected
        this.pendingMeasurementResolve = null; // Promise resolve for pending measurement

        // Listen for measurement confirmations from Pi
        this.piConnection.onMeasurementSaved = (data) => {
            this.measurementCount++;

            if (this.onMeasurement) {
                this.onMeasurement({
                    snr_to_target: data.snr_to_target,
                    snr_from_target: data.snr_from_target,
                    latitude: data.latitude,
                    longitude: data.longitude,
                    count: this.measurementCount
                });
            }

            // Resolve pending measurement promise
            if (this.pendingMeasurementResolve) {
                this.pendingMeasurementResolve(data);
                this.pendingMeasurementResolve = null;
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
     * Returns a promise that resolves when the measurement is saved.
     */
    async collectOnce() {
        return new Promise((resolve, reject) => {
            try {
                // Store the resolve function to be called when measurement is saved
                this.pendingMeasurementResolve = resolve;

                // Request measurement from Pi
                // Pi will combine current GPS stream with radio signal data
                // The result will come back via the onMeasurementSaved callback
                this.piConnection.requestMeasurement(this.sessionId);

                // Set a timeout in case the measurement never completes
                setTimeout(() => {
                    if (this.pendingMeasurementResolve) {
                        this.pendingMeasurementResolve = null;
                        reject(new Error('Measurement timeout'));
                    }
                }, 15000); // 15 second timeout (longer than trace timeout)

            } catch (error) {
                console.error('Failed to collect measurement:', error);
                this.pendingMeasurementResolve = null;
                reject(error);
            }
        });
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
