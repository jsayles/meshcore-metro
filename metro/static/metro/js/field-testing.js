/**
 * Field Testing Main Application
 *
 * Coordinates WebSocket connection, measurement collection, and heatmap rendering.
 */

import { WebSocketConnection } from './ws-connection.js';
import { MeasurementCollector } from './measurement-collector.js';
import { HeatmapRenderer } from './heatmap-renderer.js';

class FieldTester {
    constructor() {
        this.map = null;
        this.wsConnection = new WebSocketConnection();
        this.collector = null;
        this.heatmapRenderer = null;
        this.currentFieldTest = null;
        this.targetNodeId = null;
        this.repeaters = [];
        this.currentStep = 1;
        this.locationShared = false;
        this.lastTraceStartTime = null;
        this.repeaterMarker = null;
        this.userMarker = null;
        this.userLocation = null;
        this.isRadioConnected = false;
    }

    /**
     * Initialize the application
     */
    async init() {
        // Initialize Leaflet map - centered on Vancouver, BC
        this.map = L.map('map').setView([49.2827, -123.1207], 13);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19
        }).addTo(this.map);

        // Initialize heatmap renderer
        this.heatmapRenderer = new HeatmapRenderer(this.map);

        // Set up event handlers
        this.setupEventHandlers();

        // Check for pre-selected node from query parameter
        const urlParams = new URLSearchParams(window.location.search);
        const preSelectedNodeId = urlParams.get('node');
        if (preSelectedNodeId) {
            this.targetNodeId = parseInt(preSelectedNodeId);
        }

        // Load repeaters for dropdown
        await this.loadRepeaters();

        // Initialize step states
        this.initializeSteps();

        // Request location permission
        this.requestLocation();
    }

    /**
     * Automatically attempt to connect to WebSocket
     */
    async autoConnectToWS() {
        try {
            await this.connectToWS();
        } catch (error) {
            // Silent fail - user can manually retry with the button
            console.log('Auto-connect failed, user can manually connect');
        }
    }

    /**
     * Initialize step states based on current progress
     */
    initializeSteps() {
        // Hide session and collection sections initially - only show when step 3 is complete
        document.getElementById('session-section').style.display = 'none';
        document.getElementById('collection-section').style.display = 'none';

        // Step 1: Repeater selection
        if (this.targetNodeId) {
            // Show selected repeater name in the status
            const repeater = this.repeaters.find(r => Number(r.id) === Number(this.targetNodeId));
            const repeaterName = repeater ? (repeater.properties.name || repeater.properties.mesh_identity) : 'Selected';

            document.getElementById('status-repeater').textContent = repeaterName;
            document.getElementById('status-repeater').style.color = 'var(--success-color)';
            document.getElementById('repeater-select').style.display = 'none';
            this.currentStep = 2;

            // Zoom to repeater location if available
            this.zoomToRepeater(repeater);
        } else {
            this.currentStep = 1;
        }

        this.updateStepDisplay();
    }

    /**
     * Update step display (simplified - no-op for new compact layout)
     */
    updateStepDisplay() {
        // No longer needed with compact initialization box
    }

    /**
     * Zoom map to repeater location and add marker
     */
    zoomToRepeater(repeater) {
        if (repeater && repeater.geometry && repeater.geometry.coordinates) {
            const coords = repeater.geometry.coordinates;
            const latLng = [coords[1], coords[0]]; // [lat, lon]

            // Add marker for repeater
            if (this.repeaterMarker) {
                this.map.removeLayer(this.repeaterMarker);
            }

            this.repeaterMarker = L.marker(latLng, {
                icon: L.divIcon({
                    className: 'repeater-marker',
                    html: '<div style="background: #3498db; color: white; padding: 8px 12px; border-radius: 4px; font-weight: bold; white-space: nowrap; box-shadow: 0 2px 4px rgba(0,0,0,0.3);">📡 ' + (repeater.properties.name || repeater.properties.mesh_identity) + '</div>',
                    iconSize: null
                })
            }).addTo(this.map);

            // If we have user location, fit bounds to show both, otherwise just zoom to repeater
            if (this.userLocation) {
                this.fitBoundsToLocations();
            } else {
                this.map.setView(latLng, 15);
            }
        }
    }

    /**
     * Request user location
     */
    requestLocation() {
        if ('geolocation' in navigator) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    this.locationShared = true;
                    this.userLocation = [position.coords.latitude, position.coords.longitude];

                    const statusElement = document.getElementById('status-location');
                    statusElement.textContent = 'Enabled';
                    statusElement.style.color = 'var(--success-color)';

                    // Add user location marker
                    if (this.userMarker) {
                        this.map.removeLayer(this.userMarker);
                    }

                    this.userMarker = L.marker(this.userLocation, {
                        icon: L.divIcon({
                            className: 'user-marker',
                            html: '<div style="background: #27ae60; color: white; padding: 8px 12px; border-radius: 4px; font-weight: bold; white-space: nowrap; box-shadow: 0 2px 4px rgba(0,0,0,0.3);">📍 You</div>',
                            iconSize: null
                        })
                    }).addTo(this.map);

                    // Fit bounds to show both locations if repeater is selected, otherwise just user location
                    if (this.targetNodeId && this.repeaterMarker) {
                        this.fitBoundsToLocations();
                    } else {
                        this.map.setView(this.userLocation, 15);
                    }

                    if (this.currentStep === 2) {
                        this.currentStep = 3;
                        // Show the connect button
                        document.getElementById('btn-connect').style.display = 'inline-block';

                        // Auto-connect to radio now that location is granted
                        if (this.targetNodeId) {
                            this.autoConnectToWS();
                        }
                    }
                },
                (error) => {
                    console.warn('Could not get user location:', error);
                    this.showLocationPermissionLink();
                }
            );
        } else {
            document.getElementById('status-location').textContent = 'Not supported';
        }
    }

    /**
     * Fit map bounds to show both repeater and user location
     */
    fitBoundsToLocations() {
        const bounds = [];

        if (this.repeaterMarker) {
            bounds.push(this.repeaterMarker.getLatLng());
        }

        if (this.userMarker) {
            bounds.push(this.userMarker.getLatLng());
        }

        if (bounds.length > 0) {
            this.map.fitBounds(bounds, { padding: [80, 80], maxZoom: 15 });
        }
    }

    /**
     * Show clickable link to retry location permission
     */
    showLocationPermissionLink() {
        const statusElement = document.getElementById('status-location');
        const link = document.createElement('a');
        link.href = '#';
        link.className = 'permission-link';
        link.textContent = 'Permission needed';

        link.onclick = (e) => {
            e.preventDefault();
            statusElement.textContent = 'Requesting...';
            this.requestLocation();
            return false;
        };

        statusElement.textContent = '';
        statusElement.appendChild(link);
    }

    /**
     * Setup UI event handlers
     */
    setupEventHandlers() {
        // WebSocket Connection
        document.getElementById('btn-connect').addEventListener('click', () => this.connectToWS());

        // Radio status retry button
        document.getElementById('btn-retry-radio').addEventListener('click', () => this.retryRadioConnection());

        // Session management
        document.getElementById('btn-start-session').addEventListener('click', () => this.startSession());
        document.getElementById('btn-end-session').addEventListener('click', () => this.endSession());

        // Repeater selection - redirect to URL with node parameter
        document.getElementById('repeater-select').addEventListener('change', (e) => {
            const nodeId = e.target.value;
            if (nodeId && nodeId !== 'undefined' && nodeId !== '') {
                // Redirect to same page with node parameter
                window.location.href = `/field-tests/?node=${nodeId}`;
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
    }

    /**
     * Connect via WebSocket
     */
    async connectToWS() {
        const btn = document.getElementById('btn-connect');
        const wsStatus = document.getElementById('status-websocket');
        const radioStatus = document.getElementById('status-radio');

        try {
            btn.disabled = true;
            btn.textContent = 'Connecting...';
            wsStatus.textContent = 'Connecting...';
            radioStatus.textContent = 'Waiting...';

            // Set up radio status callback BEFORE connecting
            this.wsConnection.onRadioStatusChange = (status) => {
                this.handleRadioStatusChange(status);
            };

            // Connect via WebSocket
            await this.wsConnection.connect();

            // Update WebSocket status
            wsStatus.textContent = 'Connected';
            wsStatus.style.color = 'var(--success-color)';

            // Hide connect button (websocket is connected)
            btn.style.display = 'none';

            // Radio status will be updated via callback
            // Don't show session section yet - wait for radio

        } catch (error) {
            console.error('Connection failed:', error);
            wsStatus.textContent = 'Failed';
            radioStatus.textContent = 'N/A';
            btn.textContent = 'Retry Connection';
            btn.disabled = false;

            this.showMessage(`Connection failed: ${error.message}`, 'error');
        }
    }

    /**
     * Handle radio status change from WebSocket
     */
    handleRadioStatusChange(status) {
        const radioStatus = document.getElementById('status-radio');
        const retryBtn = document.getElementById('btn-retry-radio');
        const warningBox = document.getElementById('radio-warning');

        this.isRadioConnected = status.connected;

        if (status.connected) {
            // Radio is connected
            radioStatus.textContent = 'Connected';
            radioStatus.style.color = 'var(--success-color)';
            retryBtn.style.display = 'none';
            warningBox.style.display = 'none';

            this.showMessage('Radio connected! GPS streaming started.', 'success');

            // NOW show session section (both websocket AND radio are ready)
            document.getElementById('session-section').style.display = 'block';

            // Load existing heatmap data for this repeater
            this.loadAndDisplayHeatmap();

        } else {
            // Radio is NOT connected
            radioStatus.textContent = 'Disconnected';
            radioStatus.style.color = 'var(--danger-color)';
            retryBtn.style.display = 'inline-block';

            // Show warning box
            warningBox.style.display = 'block';
            const errorMsg = document.getElementById('radio-error-message');
            errorMsg.textContent = status.error || 'Could not connect to companion radio.';

            // Hide session section - can't collect without radio
            document.getElementById('session-section').style.display = 'none';

            this.showMessage('Radio connection failed. Please check hardware.', 'error');
        }
    }

    /**
     * Retry radio connection
     */
    async retryRadioConnection() {
        const retryBtn = document.getElementById('btn-retry-radio');
        const radioStatus = document.getElementById('status-radio');

        try {
            retryBtn.disabled = true;
            retryBtn.textContent = 'Checking...';
            radioStatus.textContent = 'Checking...';
            radioStatus.style.color = 'var(--text-muted)';

            // Request radio status check
            this.wsConnection.requestRadioStatus();

            // Status will be updated via callback

        } catch (error) {
            console.error('Radio status check failed:', error);
            retryBtn.disabled = false;
            retryBtn.textContent = 'Retry Radio';
            this.showMessage(`Status check failed: ${error.message}`, 'error');
        } finally {
            // Re-enable button after a short delay (callback will update status)
            setTimeout(() => {
                retryBtn.disabled = false;
                retryBtn.textContent = 'Retry Radio';
            }, 1000);
        }
    }

    /**
     * Start a new mapping session
     */
    async startSession() {
        if (!this.targetNodeId) {
            this.showMessage('Please select a target repeater first', 'warning');
            return;
        }

        const btn = document.getElementById('btn-start-session');

        try {
            btn.disabled = true;
            btn.textContent = 'Starting...';

            // Create field test via API
            const response = await fetch('/api/v1/field-tests/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    target_node: this.targetNodeId,
                    notes: ''
                })
            });

            if (!response.ok) {
                throw new Error('Failed to create field test');
            }

            this.currentFieldTest = await response.json();

            // Update UI
            document.getElementById('session-start').style.display = 'none';
            document.getElementById('session-active').style.display = 'block';
            document.getElementById('session-start-time').textContent =
                new Date(this.currentFieldTest.start_time).toLocaleString();

            // Show collection section
            document.getElementById('collection-section').style.display = 'block';

            this.showMessage('Session started successfully!', 'success');

        } catch (error) {
            console.error('Failed to start session:', error);
            this.showMessage(`Failed to start session: ${error.message}`, 'error');
            btn.disabled = false;
            btn.textContent = 'Start Session';
        }
    }

    /**
     * End the current field test
     */
    async endSession() {
        if (!this.currentFieldTest) {
            return;
        }

        const btn = document.getElementById('btn-end-session');

        try {
            btn.disabled = true;
            btn.textContent = 'Ending...';

            // Update field test via API
            const response = await fetch(`/api/v1/field-tests/${this.currentFieldTest.id}/`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    end_time: new Date().toISOString()
                })
            });

            if (!response.ok) {
                throw new Error('Failed to end field test');
            }

            // Stop any active collection
            if (this.collector && this.collector.isCollecting) {
                this.collector.stop();
            }

            // Update UI
            document.getElementById('session-start').style.display = 'block';
            document.getElementById('session-active').style.display = 'none';
            document.getElementById('collection-section').style.display = 'none';

            this.showMessage('Field test ended successfully!', 'success');

            this.currentFieldTest = null;

        } catch (error) {
            console.error('Failed to end session:', error);
            this.showMessage(`Failed to end session: ${error.message}`, 'error');
            btn.disabled = false;
            btn.textContent = 'End Session';
        }
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

    /**
     * Load available repeaters from API
     */
    async loadRepeaters() {
        try {
            const response = await fetch('/api/v1/nodes/?role=0&is_active=true');
            const data = await response.json();

            // API returns paginated results with structure: { count, results: { features: [...] } }
            const features = data.results?.features || data.features;

            if (features && features.length > 0) {
                this.repeaters = features;
                this.populateRepeaterDropdown();
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
            // ID is at feature.id, not feature.properties.id
            option.value = String(feature.id);
            option.textContent = props.name || props.mesh_identity;

            // Pre-select if this is the target node
            if (this.targetNodeId && feature.id === this.targetNodeId) {
                option.selected = true;
            }
            select.appendChild(option);
        });
    }

    /**
     * Collect single manual measurement
     */
    async collectManual() {
        // Block if radio is not connected
        if (!this.wsConnection.isReadyForMeasurements()) {
            this.showMessage('Cannot collect: Radio is not connected', 'error');
            return;
        }

        if (!this.currentFieldTest) {
            this.showMessage('Please start a field test first', 'warning');
            return;
        }

        const btn = document.getElementById('btn-collect');
        const traceStatus = document.getElementById('trace-status');

        try {
            btn.disabled = true;
            btn.textContent = 'Sending Trace...';
            traceStatus.textContent = 'Sending trace to target node...';
            traceStatus.style.color = 'var(--text-muted)';

            if (!this.collector) {
                this.collector = new MeasurementCollector(
                    this.wsConnection,
                    this.currentFieldTest.id
                );
                this.collector.onMeasurement = (data) => this.updateSessionInfo(data);
            }

            // Wait for the measurement to complete (this will take ~10 seconds if trace times out)
            this.lastTraceStartTime = Date.now();
            await this.collector.collectOnce();
            const duration = ((Date.now() - this.lastTraceStartTime) / 1000).toFixed(1);

            console.log(`Measurement completed in ${duration}s`);

            // Update trace timing display
            this.updateTraceTimingDisplay(duration);

        } catch (error) {
            console.error('Collection failed:', error);
            traceStatus.textContent = 'Trace failed';
            traceStatus.style.color = 'var(--danger-color)';
            this.showMessage(`Collection failed: ${error.message}`, 'error');
        } finally {
            btn.disabled = false;
            btn.textContent = 'Send Trace';
        }
    }

    /**
     * Start continuous collection
     */
    startContinuous() {
        // Block if radio is not connected
        if (!this.wsConnection.isReadyForMeasurements()) {
            this.showMessage('Cannot start collection: Radio is not connected', 'error');
            return;
        }

        if (!this.currentFieldTest) {
            this.showMessage('Please start a field test first', 'warning');
            return;
        }

        const interval = parseInt(document.getElementById('interval').value);
        const btnStart = document.getElementById('btn-start-continuous');
        const btnStop = document.getElementById('btn-stop-continuous');

        if (!this.collector) {
            this.collector = new MeasurementCollector(
                this.wsConnection,
                this.currentFieldTest.id
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
        const traceStatus = document.getElementById('trace-status');

        document.getElementById('measurement-count').textContent = data.count;
        document.getElementById('snr-to-target').textContent = data.snr_to_target || '0';
        document.getElementById('snr-from-target').textContent = data.snr_from_target || '0';

        // Update trace timing if duration is provided
        if (data.duration) {
            this.updateTraceTimingDisplay(data.duration);
        }

        // Show trace status
        if (data.snr_to_target === 0 && data.snr_from_target === 0) {
            traceStatus.textContent = 'Trace failed - no response from target';
            traceStatus.style.color = 'var(--danger-color)';
            this.showMessage('Trace timeout - measurement saved with default values', 'warning');
        } else {
            traceStatus.textContent = 'Trace successful!';
            traceStatus.style.color = 'var(--success-color)';
            this.showMessage('Measurement collected successfully!', 'success');
        }

        // Auto-refresh heatmap with new data (fit bounds to show new measurements)
        this.loadAndDisplayHeatmap(true);
    }

    /**
     * Update trace timing display
     */
    updateTraceTimingDisplay(durationSeconds) {
        const now = new Date();
        const timeElement = document.getElementById('trace-time');
        const durationElement = document.getElementById('trace-duration');

        if (timeElement && now) {
            timeElement.textContent = now.toLocaleTimeString();
        }
        if (durationElement && durationSeconds !== null && durationSeconds !== undefined) {
            durationElement.textContent = `${durationSeconds}s`;
        }
    }

    /**
     * Load and display heatmap automatically
     * @param {boolean} fitBounds - Whether to auto-zoom to fit all measurements (default: false on initial load)
     */
    async loadAndDisplayHeatmap(fitBounds = false) {
        if (!this.targetNodeId) {
            return;
        }

        try {
            await this.heatmapRenderer.loadData(this.targetNodeId);
            this.heatmapRenderer.render(null, fitBounds);

            const count = this.heatmapRenderer.measurements.length;
            console.log(`Heatmap updated with ${count} measurements`);

        } catch (error) {
            console.error('Failed to load heatmap:', error);
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

}

// Export FieldTester
export { FieldTester };
