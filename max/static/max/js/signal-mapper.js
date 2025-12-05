/**
 * Signal Mapper Main Application
 *
 * Coordinates BLE connection, measurement collection, and heatmap rendering.
 */

import { BLEConnection } from './ble-connection.js';
import { MeasurementCollector } from './measurement-collector.js';
import { HeatmapRenderer } from './heatmap-renderer.js';

class SignalMapper {
    constructor() {
        this.map = null;
        this.bleConnection = new BLEConnection();
        this.collector = null;
        this.heatmapRenderer = null;
        this.sessionId = this.generateUUID();
        this.targetNodeId = null;
        this.repeaters = [];
    }

    /**
     * Initialize the application
     */
    async init() {
        // Initialize Leaflet map
        this.map = L.map('map').setView([37.7749, -122.4194], 13);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19
        }).addTo(this.map);

        // Initialize heatmap renderer
        this.heatmapRenderer = new HeatmapRenderer(this.map);

        // Set up event handlers
        this.setupEventHandlers();

        // Display session ID
        document.getElementById('session-id').textContent = this.sessionId.substring(0, 8);

        // Show status message
        this.showMessage('Ready to connect. Click "Connect via BLE" to start.', 'info');

        // Try to get user's location to center map
        this.centerMapOnUser();
    }

    /**
     * Setup UI event handlers
     */
    setupEventHandlers() {
        // BLE Connection
        document.getElementById('btn-connect').addEventListener('click', () => this.connectBLE());

        // Repeater selection
        document.getElementById('repeater-select').addEventListener('change', (e) => {
            this.targetNodeId = parseInt(e.target.value);
            if (this.targetNodeId) {
                document.getElementById('collection-section').style.display = 'block';
                document.getElementById('heatmap-section').style.display = 'block';
            }
        });

        // Collection mode toggle
        document.querySelectorAll('input[name="mode"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                const mode = e.target.value;
                const continuousOptions = document.getElementById('continuous-options');
                const btnCollect = document.getElementById('btn-collect');
                const btnStart = document.getElementById('btn-start-continuous');
                const btnStop = document.getElementById('btn-stop-continuous');

                if (mode === 'continuous') {
                    continuousOptions.style.display = 'block';
                    btnCollect.style.display = 'none';
                    btnStart.style.display = 'block';
                    btnStop.style.display = 'none';
                } else {
                    continuousOptions.style.display = 'none';
                    btnCollect.style.display = 'block';
                    btnStart.style.display = 'none';
                    btnStop.style.display = 'none';
                }
            });
        });

        // Manual collection
        document.getElementById('btn-collect').addEventListener('click', () => this.collectManual());

        // Continuous collection
        document.getElementById('btn-start-continuous').addEventListener('click', () => this.startContinuous());
        document.getElementById('btn-stop-continuous').addEventListener('click', () => this.stopContinuous());

        // Heatmap controls
        document.getElementById('btn-load-heatmap').addEventListener('click', () => this.loadHeatmap());
        document.getElementById('btn-clear-heatmap').addEventListener('click', () => this.clearHeatmap());
    }

    /**
     * Connect to BLE device
     */
    async connectBLE() {
        const btn = document.getElementById('btn-connect');
        const status = document.getElementById('connection-status');

        try {
            btn.disabled = true;
            btn.textContent = 'Connecting...';

            // For MVP, skip actual BLE connection and use mock data
            this.bleConnection.useMockData = true;
            this.bleConnection.isConnected = true;

            // await this.bleConnection.connect();

            status.textContent = 'Connected (Mock Mode)';
            status.className = 'status connected';
            btn.textContent = 'Connected';

            this.showMessage('Connected successfully! Select a target repeater.', 'success');

            // Load repeaters
            await this.loadRepeaters();

        } catch (error) {
            console.error('Connection failed:', error);
            status.textContent = 'Connection Failed';
            status.className = 'status disconnected';
            btn.textContent = 'Retry Connection';
            btn.disabled = false;

            this.showMessage(`Connection failed: ${error.message}`, 'error');
        }
    }

    /**
     * Load available repeaters from API
     */
    async loadRepeaters() {
        try {
            const response = await fetch('/api/v1/nodes/?role=0&is_active=true');
            const data = await response.json();

            if (data.features && data.features.length > 0) {
                this.repeaters = data.features;
                this.populateRepeaterDropdown();
                document.getElementById('repeater-section').style.display = 'block';
            } else {
                this.showMessage('No active repeaters found in database. Add some via admin first.', 'warning');
            }

        } catch (error) {
            console.error('Failed to load repeaters:', error);
            this.showMessage('Failed to load repeaters. Check console for details.', 'error');
        }
    }

    /**
     * Populate repeater dropdown
     */
    populateRepeaterDropdown() {
        const select = document.getElementById('repeater-select');
        select.innerHTML = '<option value="">-- Select Repeater --</option>';

        this.repeaters.forEach(feature => {
            const props = feature.properties;
            const option = document.createElement('option');
            option.value = props.id;
            option.textContent = props.name || props.mesh_identity;
            select.appendChild(option);
        });
    }

    /**
     * Collect single manual measurement
     */
    async collectManual() {
        if (!this.targetNodeId) {
            this.showMessage('Please select a target repeater first', 'warning');
            return;
        }

        const btn = document.getElementById('btn-collect');

        try {
            btn.disabled = true;
            btn.textContent = 'Collecting...';

            if (!this.collector) {
                this.collector = new MeasurementCollector(
                    this.bleConnection,
                    this.targetNodeId,
                    this.sessionId
                );
                this.collector.onMeasurement = (data) => this.updateSessionInfo(data);
            }

            await this.collector.collectOnce();
            this.showMessage('Measurement collected successfully!', 'success');

        } catch (error) {
            console.error('Collection failed:', error);
            this.showMessage(`Collection failed: ${error.message}`, 'error');
        } finally {
            btn.disabled = false;
            btn.textContent = 'Collect Now';
        }
    }

    /**
     * Start continuous collection
     */
    startContinuous() {
        if (!this.targetNodeId) {
            this.showMessage('Please select a target repeater first', 'warning');
            return;
        }

        const interval = parseInt(document.getElementById('interval').value);
        const btnStart = document.getElementById('btn-start-continuous');
        const btnStop = document.getElementById('btn-stop-continuous');

        if (!this.collector) {
            this.collector = new MeasurementCollector(
                this.bleConnection,
                this.targetNodeId,
                this.sessionId
            );
            this.collector.onMeasurement = (data) => this.updateSessionInfo(data);
        }

        this.collector.setInterval(interval);
        this.collector.startContinuous();

        btnStart.style.display = 'none';
        btnStop.style.display = 'block';

        this.showMessage(`Continuous collection started (every ${interval}s)`, 'success');
    }

    /**
     * Stop continuous collection
     */
    stopContinuous() {
        if (this.collector) {
            this.collector.stop();
        }

        const btnStart = document.getElementById('btn-start-continuous');
        const btnStop = document.getElementById('btn-stop-continuous');

        btnStart.style.display = 'block';
        btnStop.style.display = 'none';

        this.showMessage('Continuous collection stopped', 'info');
    }

    /**
     * Update session info display
     */
    updateSessionInfo(data) {
        document.getElementById('measurement-count').textContent = data.count;
        document.getElementById('last-rssi').textContent = data.rssi;
        document.getElementById('last-snr').textContent = data.snr;
        document.getElementById('gps-accuracy').textContent = data.accuracy ? data.accuracy.toFixed(1) : '-';
    }

    /**
     * Load and display heatmap
     */
    async loadHeatmap() {
        if (!this.targetNodeId) {
            this.showMessage('Please select a target repeater first', 'warning');
            return;
        }

        try {
            const btn = document.getElementById('btn-load-heatmap');
            btn.disabled = true;
            btn.textContent = 'Loading...';

            await this.heatmapRenderer.loadData(this.targetNodeId);
            this.heatmapRenderer.render();

            const count = this.heatmapRenderer.measurements.length;
            this.showMessage(`Heatmap loaded with ${count} measurements`, 'success');

        } catch (error) {
            console.error('Failed to load heatmap:', error);
            this.showMessage(`Failed to load heatmap: ${error.message}`, 'error');
        } finally {
            document.getElementById('btn-load-heatmap').disabled = false;
            document.getElementById('btn-load-heatmap').textContent = 'Load Heatmap';
        }
    }

    /**
     * Clear heatmap
     */
    clearHeatmap() {
        this.heatmapRenderer.clear();
        this.showMessage('Heatmap cleared', 'info');
    }

    /**
     * Center map on user's location
     */
    centerMapOnUser() {
        if ('geolocation' in navigator) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    this.map.setView(
                        [position.coords.latitude, position.coords.longitude],
                        15
                    );
                },
                (error) => {
                    console.warn('Could not get user location:', error);
                }
            );
        }
    }

    /**
     * Show status message
     */
    showMessage(text, type = 'info') {
        const container = document.getElementById('status-messages');
        const message = document.createElement('div');
        message.className = `message ${type}`;
        message.textContent = text;

        container.appendChild(message);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            message.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => message.remove(), 300);
        }, 5000);
    }

    /**
     * Generate UUID v4
     */
    generateUUID() {
        return crypto.randomUUID();
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const app = new SignalMapper();
    app.init();
});
