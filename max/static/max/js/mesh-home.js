/**
 * Node Overview Map
 * Displays all repeater nodes in the mesh network with coverage circles and interactive markers
 */

class NodeOverview {
    constructor() {
        this.map = null;
        this.nodes = [];
        this.markers = [];
        this.circles = [];

        this.init();
    }

    async init() {
        this.initMap();
        await this.loadNodes();
        this.updateStats();
    }

    initMap() {
        // Initialize Leaflet map
        this.map = L.map('map').setView([37.7749, -122.4194], 10);

        // Add tile layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19
        }).addTo(this.map);
    }

    async loadNodes() {
        try {
            const response = await fetch('/api/v1/nodes/?is_active=true&role=0');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            this.nodes = data.results?.features || data.features || [];

            if (this.nodes.length === 0) {
                this.showMessage('No active repeaters found', 'info');
                return;
            }

            this.renderNodes();
            this.fitMapToNodes();

        } catch (error) {
            console.error('Error loading nodes:', error);
            this.showMessage('Failed to load nodes', 'error');
        }
    }

    renderNodes() {
        // Clear existing markers and circles
        this.markers.forEach(marker => this.map.removeLayer(marker));
        this.circles.forEach(circle => this.map.removeLayer(circle));
        this.markers = [];
        this.circles = [];

        this.nodes.forEach(node => {
            const props = node.properties;
            const coords = node.geometry?.coordinates;

            if (!coords || coords.length !== 2) {
                console.warn(`Node ${props.id} has invalid coordinates`, node);
                return;
            }

            const latLng = [coords[1], coords[0]]; // GeoJSON is [lon, lat], Leaflet is [lat, lon]

            // Determine color based on last_seen
            const color = this.getNodeColor(props.last_seen);

            // Create coverage circle
            const radius = props.estimated_range || 1000;
            const circle = L.circle(latLng, {
                radius: radius,
                color: color,
                fillColor: color,
                fillOpacity: 0.1,
                weight: 2,
                opacity: 0.4,
                interactive: false
            }).addTo(this.map);
            this.circles.push(circle);

            // Create marker with colored dot
            const markerIcon = L.divIcon({
                html: `<div class="dot-marker" style="background-color: ${color};"></div>`,
                className: 'node-marker-container',
                iconSize: [16, 16],
                iconAnchor: [8, 8],
                popupAnchor: [0, -8]
            });

            const marker = L.marker(latLng, { icon: markerIcon })
                .bindPopup(this.createPopupContent(node, props, color))
                .addTo(this.map);

            this.markers.push(marker);
        });
    }

    getNodeColor(lastSeenStr) {
        if (!lastSeenStr) return '#dc3545'; // Red if never seen

        const lastSeen = new Date(lastSeenStr);
        const now = new Date();
        const hoursSince = (now - lastSeen) / (1000 * 60 * 60);

        if (hoursSince <= 24) {
            return '#28a745'; // Green - within 24 hours
        } else if (hoursSince <= 168) {
            return '#ffc107'; // Yellow - within 1 week
        } else {
            return '#dc3545'; // Red - stale
        }
    }

    createPopupContent(node, nodeProps, color) {
        const nodeName = nodeProps.name || 'Unnamed Node';
        const lastSeen = nodeProps.last_seen ? new Date(nodeProps.last_seen).toLocaleString() : 'Never';
        const range = nodeProps.estimated_range || 1000;

        const statusLabel = this.getStatusLabel(nodeProps.last_seen);

        // Build URL using node ID (from feature.id, not properties.id)
        const nodeDetailUrl = `/node/${node.id}/`;

        return `
            <div class="node-popup">
                <h3>${nodeName}</h3>
                <div class="popup-row">
                    <span class="popup-label">Status:</span>
                    <span class="popup-value" style="color: ${color};">${statusLabel}</span>
                </div>
                <div class="popup-row">
                    <span class="popup-label">Range:</span>
                    <span class="popup-value">${range}m</span>
                </div>
                <div class="popup-row">
                    <span class="popup-label">Last Seen:</span>
                    <span class="popup-value">${lastSeen}</span>
                </div>
                <button class="btn-view-node" onclick="window.location.href='${nodeDetailUrl}'">
                    View Details
                </button>
            </div>
        `;
    }

    getStatusLabel(lastSeenStr) {
        if (!lastSeenStr) return 'Never Seen';

        const lastSeen = new Date(lastSeenStr);
        const now = new Date();
        const hoursSince = (now - lastSeen) / (1000 * 60 * 60);

        if (hoursSince <= 24) {
            return 'Current';
        } else if (hoursSince <= 168) {
            return 'Recent';
        } else {
            return 'Stale';
        }
    }

    fitMapToNodes() {
        if (this.nodes.length === 0) return;

        const bounds = L.latLngBounds();

        // Extend bounds to include the coverage circles
        this.nodes.forEach(node => {
            const coords = node.geometry?.coordinates;
            if (coords && coords.length === 2) {
                const center = L.latLng(coords[1], coords[0]);
                const radius = node.properties.estimated_range || 1000;

                // Calculate the bounds of the circle
                const circleBounds = center.toBounds(radius * 2);
                bounds.extend(circleBounds);
            }
        });

        if (bounds.isValid()) {
            this.map.fitBounds(bounds, { padding: [100, 100] });
        }
    }

    updateStats() {
        const repeaterCount = this.nodes.length; // All nodes are repeaters now
        document.getElementById('repeater-count').textContent = repeaterCount;
    }

    showMessage(text, type = 'info') {
        const container = document.getElementById('status-messages');
        const message = document.createElement('div');
        message.className = `message ${type}`;
        message.textContent = text;
        container.appendChild(message);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            message.style.opacity = '0';
            message.style.transform = 'translateX(400px)';
            setTimeout(() => message.remove(), 300);
        }, 5000);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    new NodeOverview();
});
