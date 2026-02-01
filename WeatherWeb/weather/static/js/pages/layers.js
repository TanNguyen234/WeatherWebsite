/**
 * filepath: d:\Projects\WeatherWebsite\WeatherWeb\weather\static\js\pages\layers.js
 * Layers Page - GIS Layer abstraction
 */

(function () {
    'use strict';    // ========================================
    // Layer Configuration (Mock)
    // ========================================
    const LAYER_CONFIG = {
        temperature: {
            name: 'Nhiệt độ',
            icon: '',
            colors: ['#3b82f6', '#fbbf24', '#ef4444'],
            unit: '°C',
            range: [-10, 40]
        },
        rain: {
            name: 'Lượng mưa',
            icon: '',
            colors: ['#f0f9ff', '#0ea5e9', '#1e3a8a'],
            unit: 'mm',
            range: [0, 50]
        },
        wind: {
            name: 'Tốc độ gió',
            icon: '',
            colors: ['#d1fae5', '#10b981', '#064e3b'],
            unit: 'm/s',
            range: [0, 20]
        },
        clouds: {
            name: 'Độ che phủ mây',
            icon: '',
            colors: ['#fefce8', '#9ca3af', '#374151'],
            unit: '%',
            range: [0, 100]
        }
    };

    // ========================================
    // State
    // ========================================
    const state = {
        map: null,
        layers: {},
        activeLayers: new Set(['temperature'])
    };

    // ========================================
    // Initialization
    // ========================================
    function init() {
        initializeMap();
        initializeLayers();
        bindEvents();
        updateLegendPanel();
    }

    function initializeMap() {
        state.map = MapCore.initMap('map', {
            center: [16.0, 106.0],
            zoom: 6
        });
    }

    function initializeLayers() {
        // Create mock overlay layers
        Object.keys(LAYER_CONFIG).forEach(layerId => {
            state.layers[layerId] = createMockLayer(layerId);
        });

        // Add default active layer
        if (state.activeLayers.has('temperature')) {
            state.layers['temperature'].addTo(state.map);
        }
    }

    // ========================================
    // Mock Layer Creation
    // ========================================
    function createMockLayer(layerId) {
        const config = LAYER_CONFIG[layerId];

        // Create a semi-transparent overlay using Canvas
        // In production, this would be replaced with actual tile layers
        const canvasLayer = L.canvas();

        // For mock purposes, we create a simple rectangle overlay
        // representing weather data visualization
        const bounds = [[8, 102], [24, 110]]; // Vietnam approximate bounds

        const overlay = L.rectangle(bounds, {
            color: 'transparent',
            fillColor: getLayerGradientColor(layerId),
            fillOpacity: 0.3,
            weight: 0
        });

        // Add some mock data points
        const mockPoints = generateMockDataPoints(layerId);
        const group = L.layerGroup([overlay, ...mockPoints]);

        return group;
    }

    function generateMockDataPoints(layerId) {
        const config = LAYER_CONFIG[layerId];
        const points = [];

        // Generate random points across Vietnam
        const locations = [
            { lat: 21.0285, lng: 105.8542, name: 'Hanoi' },
            { lat: 10.7769, lng: 106.7009, name: 'Ho Chi Minh' },
            { lat: 16.0544, lng: 108.2022, name: 'Da Nang' },
            { lat: 12.2388, lng: 109.1967, name: 'Nha Trang' },
            { lat: 20.8449, lng: 106.6881, name: 'Hai Phong' },
            { lat: 10.0452, lng: 105.7469, name: 'Can Tho' }
        ];

        locations.forEach(loc => {
            const value = getRandomValue(config.range[0], config.range[1]);
            const color = getValueColor(value, config);

            const circleMarker = L.circleMarker([loc.lat, loc.lng], {
                radius: 20,
                fillColor: color,
                color: 'white',
                weight: 2,
                opacity: 1,
                fillOpacity: 0.7
            });            circleMarker.bindPopup(`
                <div class="gis-popup">
                    <div class="popup-header">${loc.name}</div>
                    <div class="weather-info">
                        <p>${config.name}: <strong>${value.toFixed(1)} ${config.unit}</strong></p>
                    </div>
                </div>
            `);

            points.push(circleMarker);
        });

        return points;
    }

    function getLayerGradientColor(layerId) {
        const colors = LAYER_CONFIG[layerId].colors;
        return colors[1]; // Return middle color for simple fill
    }

    function getValueColor(value, config) {
        const [min, max] = config.range;
        const ratio = (value - min) / (max - min);
        
        const colors = config.colors;
        if (ratio <= 0.5) {
            return interpolateColor(colors[0], colors[1], ratio * 2);
        } else {
            return interpolateColor(colors[1], colors[2], (ratio - 0.5) * 2);
        }
    }

    function interpolateColor(color1, color2, ratio) {
        // Simple color interpolation
        const c1 = hexToRgb(color1);
        const c2 = hexToRgb(color2);

        const r = Math.round(c1.r + (c2.r - c1.r) * ratio);
        const g = Math.round(c1.g + (c2.g - c1.g) * ratio);
        const b = Math.round(c1.b + (c2.b - c1.b) * ratio);

        return `rgb(${r}, ${g}, ${b})`;
    }

    function hexToRgb(hex) {
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return result ? {
            r: parseInt(result[1], 16),
            g: parseInt(result[2], 16),
            b: parseInt(result[3], 16)
        } : { r: 0, g: 0, b: 0 };
    }

    function getRandomValue(min, max) {
        return min + Math.random() * (max - min);
    }

    // ========================================
    // Event Binding
    // ========================================
    function bindEvents() {
        // Layer toggle checkboxes
        document.querySelectorAll('.layer-toggle input').forEach(checkbox => {
            checkbox.addEventListener('change', handleLayerToggle);
        });

        // Opacity sliders
        document.querySelectorAll('.layer-options .form-range').forEach(slider => {
            slider.addEventListener('input', handleOpacityChange);
        });
    }

    // ========================================
    // Event Handlers
    // ========================================
    function handleLayerToggle(e) {
        const checkbox = e.target;
        const layerId = checkbox.id.replace('layer-', '');
        const layerItem = checkbox.closest('.layer-item');
        const options = layerItem.querySelector('.layer-options');
        const legend = layerItem.querySelector('.layer-legend');

        if (checkbox.checked) {
            state.activeLayers.add(layerId);
            state.layers[layerId].addTo(state.map);
            if (options) options.style.display = 'flex';
            if (legend) legend.style.display = 'flex';
        } else {
            state.activeLayers.delete(layerId);
            state.map.removeLayer(state.layers[layerId]);
            if (options) options.style.display = 'none';
            if (legend) legend.style.display = 'none';
        }

        updateLegendPanel();
    }

    function handleOpacityChange(e) {
        const slider = e.target;
        const layerId = slider.id.replace('opacity-', '');
        const opacity = parseInt(slider.value) / 100;

        // Update display
        slider.nextElementSibling.textContent = `${slider.value}%`;

        // Update layer opacity
        if (state.layers[layerId]) {
            state.layers[layerId].eachLayer(layer => {
                if (layer.setStyle) {
                    layer.setStyle({ fillOpacity: opacity });
                }
            });
        }
    }    // ========================================
    // UI Updates
    // ========================================
    function updateLegendPanel() {
        const container = document.getElementById('active-legends');

        if (state.activeLayers.size === 0) {
            container.innerHTML = '<p class="text-muted" style="font-size: 0.8rem;">Không có lớp nào đang hoạt động</p>';
            return;
        }

        const html = Array.from(state.activeLayers).map(layerId => {
            const config = LAYER_CONFIG[layerId];
            return `
                <div class="legend-item">
                    <span>${config.name}</span>
                    <div class="legend-color ${layerId === 'temperature' ? 'temp' : layerId}"></div>
                    <span>${config.range[0]}-${config.range[1]} ${config.unit}</span>
                </div>
            `;
        }).join('');

        container.innerHTML = html;
    }

    // ========================================
    // Initialize
    // ========================================
    document.addEventListener('DOMContentLoaded', init);
})();
