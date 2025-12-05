/**
 * Measurement Collector
 *
 * Handles collecting signal strength measurements with GPS coordinates
 * and submitting them to the Django API.
 */

export class MeasurementCollector {
    constructor(bleConnection, targetNodeId, sessionId) {
        this.bleConnection = bleConnection;
        this.targetNodeId = targetNodeId;
        this.sessionId = sessionId;
        this.mode = 'manual';
        this.interval = 5000; // milliseconds
        this.isCollecting = false;
        this.intervalId = null;
        this.measurementCount = 0;
        this.onMeasurement = null; // Callback for when measurement is collected
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
     */
    async collectOnce() {
        try {
            // 1. Get GPS data
            const gps = await this.bleConnection.getGPSData();

            // 2. Get signal strength data
            const signal = await this.bleConnection.getSignalData();

            // 3. Prepare measurement payload (GeoJSON format for GeoDjango)
            const measurement = {
                location: {
                    type: 'Point',
                    coordinates: [gps.longitude, gps.latitude] // lon, lat order for GeoJSON
                },
                altitude: gps.altitude,
                gps_accuracy: gps.accuracy,
                target_node: this.targetNodeId,
                rssi: signal.rssi,
                snr: signal.snr,
                session_id: this.sessionId,
                collector_user: null // Anonymous for MVP
            };

            // 4. POST to API
            const response = await fetch('/api/v1/measurements/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(measurement)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(`API error: ${JSON.stringify(error)}`);
            }

            const result = await response.json();
            this.measurementCount++;

            // Call callback if set
            if (this.onMeasurement) {
                this.onMeasurement({
                    rssi: signal.rssi,
                    snr: signal.snr,
                    accuracy: gps.accuracy,
                    count: this.measurementCount
                });
            }

            return result;

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

    /**
     * Get CSRF token from cookie
     */
    getCSRFToken() {
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
}
