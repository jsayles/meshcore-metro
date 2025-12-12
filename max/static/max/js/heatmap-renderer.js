/**
 * Heatmap Renderer
 *
 * Handles loading measurement data from API and rendering heatmap on Leaflet map.
 */

export class HeatmapRenderer {
    constructor(leafletMap) {
        this.map = leafletMap;
        this.heatLayer = null;
        this.measurements = [];
    }

    /**
     * Load traces from API for a specific target node
     */
    async loadData(targetNodeId) {
        try {
            const response = await fetch(`/api/v1/traces/?session__target_node=${targetNodeId}&ordering=-timestamp`);

            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }

            const data = await response.json();

            // Extract features from GeoJSON FeatureCollection
            if (data.features && Array.isArray(data.features)) {
                this.measurements = data.features;
            } else if (data.results && data.results.features) {
                this.measurements = data.results.features;
            } else {
                this.measurements = [];
            }

            return this.measurements;

        } catch (error) {
            console.error('Failed to load heatmap data:', error);
            throw error;
        }
    }

    /**
     * Render heatmap on map
     */
    render(measurements = null) {
        if (measurements) {
            this.measurements = measurements;
        }

        if (this.measurements.length === 0) {
            console.warn('No measurements to render');
            return;
        }

        // Convert measurements to heatmap format: [lat, lon, intensity]
        const heatData = this.measurements.map(feature => {
            const coords = feature.geometry.coordinates; // [lon, lat]
            const snr = feature.properties.snr_from_target; // Use SNR from target

            return [
                coords[1],  // latitude
                coords[0],  // longitude
                this.normalizeSNR(snr)  // intensity
            ];
        });

        // Remove existing heatmap layer
        if (this.heatLayer) {
            this.map.removeLayer(this.heatLayer);
        }

        // Create new heatmap layer
        this.heatLayer = L.heatLayer(heatData, {
            radius: 25,
            blur: 35,
            maxZoom: 17,
            max: 1.0,
            gradient: {
                0.0: 'blue',
                0.3: 'cyan',
                0.5: 'lime',
                0.7: 'yellow',
                1.0: 'red'
            }
        });

        this.heatLayer.addTo(this.map);

        // Fit map bounds to show all points
        if (this.measurements.length > 0) {
            const bounds = this.measurements.map(feature => {
                const coords = feature.geometry.coordinates;
                return [coords[1], coords[0]]; // [lat, lon]
            });
            this.map.fitBounds(bounds, { padding: [50, 50] });
        }

        console.log(`Rendered heatmap with ${heatData.length} points`);
    }

    /**
     * Normalize SNR value to 0-1 range for heatmap intensity
     * SNR typically ranges from -10 (very weak) to 10 (very strong) dB
     */
    normalizeSNR(snr) {
        const minSNR = -10;
        const maxSNR = 10;

        // Clamp value
        const clampedSNR = Math.max(minSNR, Math.min(maxSNR, snr));

        // Normalize to 0-1 range
        const normalized = (clampedSNR - minSNR) / (maxSNR - minSNR);

        return normalized;
    }

    /**
     * Clear heatmap from map
     */
    clear() {
        if (this.heatLayer) {
            this.map.removeLayer(this.heatLayer);
            this.heatLayer = null;
        }
        this.measurements = [];
    }

    /**
     * Add a single measurement to existing heatmap
     * For MVP, just reload all data
     */
    async refresh(targetNodeId) {
        await this.loadData(targetNodeId);
        this.render();
    }
}
