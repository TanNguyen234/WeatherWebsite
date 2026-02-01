/**
 * filepath: d:\Projects\WeatherWebsite\WeatherWeb\weather\static\js\pages\compare.js
 * Compare Page - Spatial comparison across multiple points
 */

(function () {
    'use strict';

    // ========================================
    // State
    // ========================================
    const state = {
        locations: [],
        selectedLocations: [],
        miniMaps: [],
        chart: null,
        maxLocations: 4
    };

    // ========================================
    // Initialization
    // ========================================
    function init() {
        loadInitialData();
        loadFromSession();
        bindEvents();
        renderSelectedLocations();
        updateCompareButton();
    }

    function loadInitialData() {
        const data = UIHelpers.parseInitialData('initial-data');
        if (data) {
            state.locations = data.locations || [];
        }
    }

    function loadFromSession() {
        // Load any locations added from map page
        const sessionLocations = JSON.parse(sessionStorage.getItem('compareLocations') || '[]');
        sessionLocations.forEach(loc => {
            if (state.selectedLocations.length < state.maxLocations) {
                const existingLoc = state.locations.find(l => 
                    Math.abs(l.latitude - loc.lat) < 0.0001 && 
                    Math.abs(l.longitude - loc.lng) < 0.0001
                );
                if (existingLoc && !state.selectedLocations.find(s => s.id === existingLoc.id)) {
                    state.selectedLocations.push(existingLoc);
                }
            }
        });
        sessionStorage.removeItem('compareLocations');
    }

    // ========================================
    // Event Binding
    // ========================================
    function bindEvents() {
        document.getElementById('add-location-btn').addEventListener('click', handleAddLocation);
        document.getElementById('compare-btn').addEventListener('click', handleCompare);
        document.getElementById('selected-locations').addEventListener('click', handleRemoveLocation);
    }

    // ========================================
    // Event Handlers
    // ========================================
    function handleAddLocation() {
        const select = document.getElementById('location-select');
        const option = select.options[select.selectedIndex];

        if (!option.value) return;        if (state.selectedLocations.length >= state.maxLocations) {
            UIHelpers.showToast(`Tối đa ${state.maxLocations} vị trí`, 'error');
            return;
        }

        const locationId = parseInt(option.value);

        // Check if already selected
        if (state.selectedLocations.find(l => l.id === locationId)) {
            UIHelpers.showToast('Vị trí đã được chọn', 'error');
            return;
        }

        const location = {
            id: locationId,
            name: option.dataset.name,
            latitude: parseFloat(option.dataset.lat),
            longitude: parseFloat(option.dataset.lng)
        };

        state.selectedLocations.push(location);
        renderSelectedLocations();
        updateCompareButton();

        // Reset select
        select.value = '';
    }

    function handleRemoveLocation(e) {
        const removeBtn = e.target.closest('.remove-btn');
        if (!removeBtn) return;

        const locationId = parseInt(removeBtn.dataset.id);
        state.selectedLocations = state.selectedLocations.filter(l => l.id !== locationId);
        renderSelectedLocations();
        updateCompareButton();

        // Hide results if less than 2 locations
        if (state.selectedLocations.length < 2) {
            document.getElementById('comparison-results').style.display = 'none';
            document.getElementById('empty-state').style.display = 'block';
        }
    }    async function handleCompare() {
        if (state.selectedLocations.length < 2) {
            UIHelpers.showToast('Vui lòng chọn ít nhất 2 vị trí', 'error');
            return;
        }

        const compareBtn = document.getElementById('compare-btn');
        compareBtn.disabled = true;
        compareBtn.textContent = 'Đang tải...';

        try {
            const locationIds = state.selectedLocations.map(l => l.id);
            const data = await WeatherApi.compareLocations(locationIds);

            displayComparisonResults(data);
        } catch (error) {
            UIHelpers.showToast(error.message, 'error');
        } finally {
            compareBtn.disabled = false;
            compareBtn.textContent = 'So sánh thời tiết';
        }
    }    // ========================================
    // UI Updates
    // ========================================
    function renderSelectedLocations() {
        const container = document.getElementById('selected-locations');

        if (state.selectedLocations.length === 0) {
            container.innerHTML = '';
            return;
        }

        container.innerHTML = state.selectedLocations.map(loc => `
            <div class="selected-location-tag">
                <span>${loc.name}</span>
                <button class="remove-btn" data-id="${loc.id}" title="Xóa">&times;</button>
            </div>
        `).join('');
    }

    function updateCompareButton() {
        const btn = document.getElementById('compare-btn');
        btn.disabled = state.selectedLocations.length < 2;
    }

    function displayComparisonResults(data) {
        document.getElementById('empty-state').style.display = 'none';
        document.getElementById('comparison-results').style.display = 'block';

        renderMiniMaps(data.comparison);
        renderComparisonTable(data.comparison);
        renderComparisonChart(data.comparison);
    }

    function renderMiniMaps(comparison) {
        const container = document.getElementById('mini-maps-row');

        // Clear existing maps
        state.miniMaps.forEach(map => map.remove());
        state.miniMaps = [];

        container.innerHTML = comparison.map((item, index) => `
            <div class="mini-map-card">
                <div class="map-header">${item.name}</div>
                <div class="mini-map" id="mini-map-${index}"></div>
                <div class="map-weather">
                    <span class="weather-temp">${UIHelpers.formatTemp(item.weather.temperature)}</span>
                    <span>${item.weather.description}</span>
                </div>
            </div>
        `).join('');

        // Initialize mini maps
        comparison.forEach((item, index) => {
            const map = MapCore.initMap(`mini-map-${index}`, {
                center: [item.latitude, item.longitude],
                zoom: 10,
                zoomControl: false
            });
            MapCore.addMarker(map, item.latitude, item.longitude);
            state.miniMaps.push(map);
        });
    }    function renderComparisonTable(comparison) {
        // Header
        const headerRow = document.getElementById('table-header');
        headerRow.innerHTML = '<th>Chỉ số</th>' + 
            comparison.map(item => `<th>${item.name}</th>`).join('');

        // Body
        const tbody = document.getElementById('comparison-tbody');
        const metrics = [
            { key: 'temperature', label: 'Nhiệt độ', format: (v) => UIHelpers.formatTemp(v) },
            { key: 'humidity', label: 'Độ ẩm', format: (v) => UIHelpers.formatHumidity(v) },
            { key: 'wind_speed', label: 'Tốc độ gió', format: (v) => UIHelpers.formatWind(v) },
            { key: 'description', label: 'Điều kiện', format: (v) => v }
        ];

        const rows = metrics.map(metric => {
            const values = comparison.map(item => item.weather[metric.key]);
            const numericValues = values.filter(v => typeof v === 'number');
            const min = Math.min(...numericValues);
            const max = Math.max(...numericValues);

            const cells = values.map(value => {
                let className = '';
                if (typeof value === 'number') {
                    if (metric.key === 'temperature') {
                        // Lower temp is "better" in hot climate context
                        className = value === min ? 'highlight-best' : (value === max ? 'highlight-worst' : '');
                    } else if (metric.key === 'wind_speed') {
                        // Lower wind is usually preferred
                        className = value === min ? 'highlight-best' : '';
                    }
                }
                return `<td class="${className}">${metric.format(value)}</td>`;
            }).join('');

            return `<tr><td>${metric.label}</td>${cells}</tr>`;
        }).join('');

        tbody.innerHTML = rows;
    }

    function renderComparisonChart(comparison) {
        const ctx = document.getElementById('comparison-chart').getContext('2d');

        if (state.chart) {
            state.chart.destroy();
        }

        const labels = comparison.map(item => item.name);
        const temps = comparison.map(item => item.weather.temperature);
        const humidity = comparison.map(item => item.weather.humidity);
        const wind = comparison.map(item => item.weather.wind_speed);        state.chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Nhiệt độ (°C)',
                        data: temps,
                        backgroundColor: 'rgba(37, 99, 235, 0.8)',
                        borderRadius: 4
                    },
                    {
                        label: 'Độ ẩm (%)',
                        data: humidity,
                        backgroundColor: 'rgba(16, 185, 129, 0.8)',
                        borderRadius: 4
                    },
                    {
                        label: 'Gió (m/s)',
                        data: wind,
                        backgroundColor: 'rgba(245, 158, 11, 0.8)',
                        borderRadius: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    // ========================================
    // Initialize
    // ========================================
    document.addEventListener('DOMContentLoaded', init);
})();
