/**
 * filepath: d:\Projects\WeatherWebsite\WeatherWeb\weather\static\js\pages\forecast.js
 * Forecast Page - Temporal analysis at fixed point
 */

(function () {
    'use strict';

    // ========================================
    // State
    // ========================================
    const state = {
        miniMap: null,
        miniMapMarker: null,
        chart: null,
        locations: [],
        selectedLocation: null
    };

    // ========================================
    // Initialization
    // ========================================
    function init() {
        loadInitialData();
        initMiniMap();
        bindEvents();
    }

    function loadInitialData() {
        const data = UIHelpers.parseInitialData('initial-data');
        if (data) {
            state.locations = data.locations || [];
        }
    }

    function initMiniMap() {
        state.miniMap = MapCore.initMap('mini-map', {
            center: [16.0, 106.0],
            zoom: 5,
            zoomControl: false
        });

        // Click to select location on mini map
        MapCore.setupMapClick(state.miniMap, (lat, lng) => {
            updateSelectedLocation(lat, lng, null);
            document.getElementById('lat-input').value = lat.toFixed(4);
            document.getElementById('lng-input').value = lng.toFixed(4);
            document.getElementById('location-select').value = '';
        });
    }

    // ========================================
    // Event Binding
    // ========================================
    function bindEvents() {
        // Form submission
        document.getElementById('forecast-form').addEventListener('submit', handleFormSubmit);

        // Location select change
        document.getElementById('location-select').addEventListener('change', handleLocationSelect);

        // Coordinate inputs change
        document.getElementById('lat-input').addEventListener('change', handleCoordInput);
        document.getElementById('lng-input').addEventListener('change', handleCoordInput);
    }

    // ========================================
    // Event Handlers
    // ========================================
    function handleLocationSelect(e) {
        const select = e.target;
        const option = select.options[select.selectedIndex];

        if (!option.value) {
            state.selectedLocation = null;
            updateSelectedInfo(null);
            return;
        }

        const lat = parseFloat(option.dataset.lat);
        const lng = parseFloat(option.dataset.lng);
        const name = option.textContent.split('(')[0].trim();

        updateSelectedLocation(lat, lng, name);

        // Clear manual inputs
        document.getElementById('lat-input').value = '';
        document.getElementById('lng-input').value = '';
    }

    function handleCoordInput() {
        const lat = parseFloat(document.getElementById('lat-input').value);
        const lng = parseFloat(document.getElementById('lng-input').value);

        if (!isNaN(lat) && !isNaN(lng)) {
            updateSelectedLocation(lat, lng, null);
            document.getElementById('location-select').value = '';
        }
    }

    async function handleFormSubmit(e) {
        e.preventDefault();

        // Get coordinates
        let lat, lng, locationId = null;

        const selectEl = document.getElementById('location-select');
        if (selectEl.value) {
            locationId = parseInt(selectEl.value);
            const option = selectEl.options[selectEl.selectedIndex];
            lat = parseFloat(option.dataset.lat);
            lng = parseFloat(option.dataset.lng);
        } else {
            lat = parseFloat(document.getElementById('lat-input').value);
            lng = parseFloat(document.getElementById('lng-input').value);
        }        if (isNaN(lat) || isNaN(lng)) {
            UIHelpers.showToast('Vui lòng chọn vị trí hoặc nhập tọa độ', 'error');
            return;
        }

        const mode = document.getElementById('time-range').value;

        // Show loading
        showLoading();

        try {
            let data;
            if (locationId) {
                data = await WeatherApi.getForecast(locationId, mode);
            } else {
                data = await WeatherApi.getForecastByCoords(lat, lng, mode);
            }

            displayForecastResults(data, lat, lng, mode);
        } catch (error) {
            UIHelpers.showToast(error.message, 'error');
            hideResults();
        }
    }

    // ========================================
    // UI Updates
    // ========================================
    function updateSelectedLocation(lat, lng, name) {
        state.selectedLocation = { lat, lng, name };

        // Update mini map marker
        if (state.miniMapMarker) {
            state.miniMap.removeLayer(state.miniMapMarker);
        }
        state.miniMapMarker = MapCore.addMarker(state.miniMap, lat, lng);
        state.miniMap.setView([lat, lng], 10);

        // Update info
        updateSelectedInfo({ lat, lng, name });
    }    function updateSelectedInfo(location) {
        const infoEl = document.getElementById('selected-info');
        if (!location) {
            infoEl.innerHTML = '<p class="text-muted">Chọn một vị trí để xem trước</p>';
            return;
        }

        infoEl.innerHTML = `
            <p><strong>${location.name || 'Vị trí tùy chỉnh'}</strong></p>
            <p>${UIHelpers.formatCoords(location.lat, location.lng)}</p>
        `;
    }

    function showLoading() {
        document.getElementById('empty-state').style.display = 'none';
        document.getElementById('forecast-results').style.display = 'block';
        document.getElementById('forecast-tbody').innerHTML = `
            <tr><td colspan="5" class="loading"><div class="spinner"></div></td></tr>
        `;
    }

    function hideResults() {
        document.getElementById('forecast-results').style.display = 'none';
        document.getElementById('empty-state').style.display = 'block';
    }    function displayForecastResults(data, lat, lng, mode) {
        document.getElementById('empty-state').style.display = 'none';
        document.getElementById('forecast-results').style.display = 'block';

        // Update location display
        document.getElementById('result-location').textContent = 
            `${UIHelpers.formatCoords(lat, lng)}`;

        // Render table
        renderForecastTable(data.forecast, mode);

        // Render chart
        renderForecastChart(data.forecast, mode);
    }

    function renderForecastTable(forecast, mode) {
        const tbody = document.getElementById('forecast-tbody');
        
        const rows = forecast.map(item => {
            const conditionClass = getConditionClass(item.description);
            return `
                <tr>
                    <td>${item.time}</td>
                    <td>${UIHelpers.formatTemp(item.temperature)}</td>
                    <td>${UIHelpers.formatHumidity(item.humidity)}</td>
                    <td>${UIHelpers.formatWind(item.wind_speed)}</td>
                    <td><span class="condition-badge ${conditionClass}">${item.description}</span></td>
                </tr>
            `;
        }).join('');

        tbody.innerHTML = rows;
    }

    function renderForecastChart(forecast, mode) {
        const ctx = document.getElementById('forecast-chart').getContext('2d');

        // Destroy existing chart
        if (state.chart) {
            state.chart.destroy();
        }

        const labels = forecast.map(item => item.time);
        const temps = forecast.map(item => item.temperature);
        const humidity = forecast.map(item => item.humidity);        state.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Nhiệt độ (°C)',
                        data: temps,
                        borderColor: '#2563eb',
                        backgroundColor: 'rgba(37, 99, 235, 0.1)',
                        fill: true,
                        tension: 0.4,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Độ ẩm (%)',
                        data: humidity,
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        fill: false,
                        tension: 0.4,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Nhiệt độ (°C)'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Độ ẩm (%)'
                        },
                        grid: {
                            drawOnChartArea: false
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top'
                    }
                }
            }
        });
    }

    function getConditionClass(description) {
        const desc = description.toLowerCase();
        if (desc.includes('rain') || desc.includes('shower')) return 'rainy';
        if (desc.includes('cloud') || desc.includes('overcast')) return 'cloudy';
        return 'sunny';
    }

    // ========================================
    // Initialize
    // ========================================
    document.addEventListener('DOMContentLoaded', init);
})();
