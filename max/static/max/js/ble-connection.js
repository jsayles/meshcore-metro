/**
 * BLE Connection Handler for MeshCore Radio
 *
 * For MVP, this uses the browser's Geolocation API for GPS
 * and Web Bluetooth API for BLE connection.
 *
 * TODO: Integrate @liamcottle/meshcore.js for actual radio communication
 * For now, we'll use getStats() polling approach to get RSSI/SNR
 */

export class BLEConnection {
    constructor() {
        this.device = null;
        this.server = null;
        this.isConnected = false;
        this.lastRssi = null;
        this.lastSnr = null;

        // Mock data for testing without actual radio
        this.useMockData = true;
    }

    /**
     * Check if Web Bluetooth is supported
     */
    isSupported() {
        return 'bluetooth' in navigator;
    }

    /**
     * Connect to MeshCore radio via BLE
     */
    async connect() {
        if (!this.isSupported()) {
            throw new Error('Web Bluetooth is not supported in this browser. Use Chrome or Edge.');
        }

        try {
            // Request Bluetooth device
            // TODO: Replace with actual MeshCore service UUID
            this.device = await navigator.bluetooth.requestDevice({
                filters: [{ namePrefix: 'MeshCore' }],
                optionalServices: ['generic_access'] // TODO: Add MeshCore service UUIDs
            });

            console.log('Selected device:', this.device.name);

            // Connect to GATT server
            this.server = await this.device.gatt.connect();
            this.isConnected = true;

            // Set up disconnect handler
            this.device.addEventListener('gattserverdisconnected', () => {
                this.isConnected = false;
                console.log('Disconnected from device');
            });

            return true;
        } catch (error) {
            console.error('Failed to connect:', error);
            throw error;
        }
    }

    /**
     * Disconnect from device
     */
    disconnect() {
        if (this.device && this.device.gatt.connected) {
            this.device.gatt.disconnect();
        }
        this.isConnected = false;
    }

    /**
     * Get signal strength data (RSSI and SNR)
     *
     * TODO: Implement actual meshcore.js getStats() call
     * For now, returns mock data
     */
    async getSignalData() {
        if (this.useMockData) {
            // Return mock data for testing
            return {
                rssi: Math.floor(Math.random() * 60) - 100, // -100 to -40 dBm
                snr: Math.floor(Math.random() * 20) - 5      // -5 to 15 dB
            };
        }

        // TODO: Replace with actual meshcore.js integration
        // const stats = await this.meshcore.getStats();
        // return { rssi: stats.last_rssi, snr: stats.last_snr };

        throw new Error('Real radio communication not yet implemented');
    }

    /**
     * Get GPS coordinates using browser Geolocation API
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
     * Check connection status
     */
    getStatus() {
        return this.isConnected ? 'Connected' : 'Disconnected';
    }
}
