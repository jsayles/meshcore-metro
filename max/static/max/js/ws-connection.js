/**
 * WebSocket Connection Handler
 *
 * Connects browser to Django/Channels WebSocket server.
 * - Streams GPS from browser to server
 * - Receives signal data from server (which reads from USB radio)
 * - Handles real-time measurement collection
 */

export class WebSocketConnection {
    constructor() {
        this.ws = null;
        this.isConnected = false;
        this.lastSignalData = null;
        this.reconnectInterval = null;
        this.reconnectDelay = 5000; // 5 seconds
        this.gpsWatchId = null;

        // Callbacks
        this.onSignalUpdate = null;
        this.onConnectionChange = null;
        this.onMeasurementSaved = null;
    }

    /**
     * Connect to Pi WebSocket server
     */
    async connect() {
        return new Promise((resolve, reject) => {
            try {
                // Use ws:// for local connection, wss:// for production
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/ws/signal/`;

                console.log('Connecting to Pi WebSocket:', wsUrl);
                this.ws = new WebSocket(wsUrl);

                this.ws.onopen = () => {
                    console.log('Connected to Pi');
                    this.isConnected = true;
                    this.stopReconnect();
                    this.startGPSStreaming();

                    if (this.onConnectionChange) {
                        this.onConnectionChange(true);
                    }

                    resolve(true);
                };

                this.ws.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        this.handleMessage(data);
                    } catch (error) {
                        console.error('Failed to parse WebSocket message:', error);
                    }
                };

                this.ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    reject(new Error('Failed to connect to Pi'));
                };

                this.ws.onclose = () => {
                    console.log('Disconnected from Pi');
                    this.isConnected = false;
                    this.stopGPSStreaming();

                    if (this.onConnectionChange) {
                        this.onConnectionChange(false);
                    }

                    // Attempt to reconnect
                    this.startReconnect();
                };

            } catch (error) {
                reject(error);
            }
        });
    }

    /**
     * Handle incoming WebSocket messages from Pi
     */
    handleMessage(data) {
        console.log('Received from Pi:', data.type);

        switch (data.type) {
            case 'connected':
                console.log('Pi welcome:', data.message);
                break;

            case 'signal_data':
                // Pi sent us current signal data
                this.lastSignalData = {
                    snr_to_target: data.snr_to_target,
                    snr_from_target: data.snr_from_target,
                    timestamp: data.timestamp
                };

                if (this.onSignalUpdate) {
                    this.onSignalUpdate(this.lastSignalData);
                }
                break;

            case 'measurement_saved':
                // Pi confirmed measurement was saved
                console.log('Trace saved:', data.trace_id);

                if (this.onMeasurementSaved) {
                    this.onMeasurementSaved({
                        id: data.trace_id,
                        snr_to_target: data.snr_to_target,
                        snr_from_target: data.snr_from_target,
                        latitude: data.latitude,
                        longitude: data.longitude
                    });
                }
                break;

            case 'error':
                console.error('Pi error:', data.message);
                break;

            default:
                console.warn('Unknown message type:', data.type);
        }
    }

    /**
     * Start streaming GPS data to Pi
     */
    startGPSStreaming() {
        if (!('geolocation' in navigator)) {
            console.error('Geolocation not supported');
            return;
        }

        console.log('Starting GPS stream to Pi');

        // Use watchPosition for continuous GPS updates
        this.gpsWatchId = navigator.geolocation.watchPosition(
            (position) => {
                if (this.isConnected) {
                    this.sendGPS({
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude,
                        altitude: position.coords.altitude,
                        accuracy: position.coords.accuracy,
                        timestamp: position.timestamp
                    });
                }
            },
            (error) => {
                console.error('GPS error:', error);
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 0
            }
        );
    }

    /**
     * Stop GPS streaming
     */
    stopGPSStreaming() {
        if (this.gpsWatchId !== null) {
            navigator.geolocation.clearWatch(this.gpsWatchId);
            this.gpsWatchId = null;
            console.log('Stopped GPS stream');
        }
    }

    /**
     * Send GPS coordinates to Pi
     */
    sendGPS(gpsData) {
        if (!this.isConnected || !this.ws) {
            return;
        }

        try {
            this.ws.send(JSON.stringify({
                type: 'gps_data',
                data: gpsData
            }));
        } catch (error) {
            console.error('Failed to send GPS data:', error);
        }
    }

    /**
     * Get current GPS data (one-time reading)
     */
    async getGPSData() {
        return new Promise((resolve, reject) => {
            if (!('geolocation' in navigator)) {
                reject(new Error('Geolocation not supported'));
                return;
            }

            navigator.geolocation.getCurrentPosition(
                (position) => {
                    resolve({
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude,
                        altitude: position.coords.altitude,
                        accuracy: position.coords.accuracy
                    });
                },
                (error) => {
                    reject(new Error(`GPS error: ${error.message}`));
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 0
                }
            );
        });
    }

    /**
     * Get latest signal strength data from Pi
     */
    async getSignalData() {
        if (!this.lastSignalData) {
            throw new Error('No signal data available yet');
        }
        return this.lastSignalData;
    }

    /**
     * Request signal measurement from Pi
     * Pi will combine current GPS stream with radio signal data
     */
    requestMeasurement(sessionId) {
        if (!this.isConnected || !this.ws) {
            throw new Error('Not connected to Pi');
        }

        try {
            this.ws.send(JSON.stringify({
                type: 'request_measurement',
                session_id: sessionId
            }));
        } catch (error) {
            console.error('Failed to request measurement:', error);
            throw error;
        }
    }

    /**
     * Disconnect from Pi
     */
    disconnect() {
        this.stopGPSStreaming();
        this.stopReconnect();

        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }

        this.isConnected = false;
    }

    /**
     * Start automatic reconnection
     */
    startReconnect() {
        if (this.reconnectInterval) {
            return;
        }

        console.log('Will attempt to reconnect in', this.reconnectDelay / 1000, 'seconds');

        this.reconnectInterval = setInterval(() => {
            console.log('Attempting to reconnect to Pi...');
            this.connect().catch(error => {
                console.error('Reconnection failed:', error);
            });
        }, this.reconnectDelay);
    }

    /**
     * Stop automatic reconnection
     */
    stopReconnect() {
        if (this.reconnectInterval) {
            clearInterval(this.reconnectInterval);
            this.reconnectInterval = null;
        }
    }

    /**
     * Check connection status
     */
    getStatus() {
        return this.isConnected ? 'Connected' : 'Disconnected';
    }
}
