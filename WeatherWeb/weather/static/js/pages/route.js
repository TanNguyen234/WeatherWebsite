/**
 * filepath: d:\Projects\WeatherWebsite\WeatherWeb\weather\static\js\pages\route.js
 * Route Page - Linear spatial analysis
 */

(function () {
    'use strict';

    // ========================================
    // State
    // ========================================
    const state = {
        map: null,
        routeLine: null,
        markerGroup: null,
        locations: [],
        routes: [],
        isAuthenticated: false,
        currentRoute: null
    };

    // ========================================
    // Initialization
    // ========================================
    function init() {
        loadInitialData();
        loadFromSession();
        initializeMap();
        bindEvents();
    }

    function loadInitialData() {
        const data = UIHelpers.parseInitialData('initial-data');
        if (data) {
            state.locations = data.locations || [];
            state.routes = data.routes || [];
            state.isAuthenticated = data.isAuthenticated || false;
        }
    }

    function loadFromSession() {
        const routePoints = JSON.parse(sessionStorage.getItem('routePoints') || '[]');
        if (routePoints.length >= 2) {
            // Try to match with saved locations
            routePoints.forEach((point, index) => {
                const matchedLoc = state.locations.find(l =>
                    Math.abs(l.latitude - point.lat) < 0.0001 &&
                    Math.abs(l.longitude - point.lng) < 0.0001
                );
                if (matchedLoc) {
                    const selectId = index === 0 ? 'start-location' : 'end-location';
                    document.getElementById(selectId).value = matchedLoc.id;
                }
            });
        }
        sessionStorage.removeItem('routePoints');
    }

    function initializeMap() {
        state.map = MapCore.initMap('map', {
            center: [16.0, 106.0],
            zoom: 6
        });

        state.markerGroup = MapCore.createMarkerGroup(state.map);
    }

    // ========================================
    // Event Binding
    // ========================================
    function bindEvents() {
        // Form submission
        document.getElementById('route-form').addEventListener('submit', handleFormSubmit);

        // Location selects
        document.getElementById('start-location').addEventListener('change', handleLocationChange);
        document.getElementById('end-location').addEventListener('change', handleLocationChange);

        // Point count slider
        document.getElementById('point-count').addEventListener('input', handlePointCountChange);

        // Route list click
        document.getElementById('route-list').addEventListener('click', handleRouteClick);

        // Save route button
        document.getElementById('save-route-btn').addEventListener('click', handleSaveRoute);
    }

    // ========================================
    // Event Handlers
    // ========================================
    function handleLocationChange(e) {
        const select = e.target;
        const option = select.options[select.selectedIndex];
        const coordsId = select.id === 'start-location' ? 'start-coords' : 'end-coords';

        if (option.value) {
            const lat = parseFloat(option.dataset.lat);
            const lng = parseFloat(option.dataset.lng);
            document.getElementById(coordsId).textContent = UIHelpers.formatCoords(lat, lng);
        } else {
            document.getElementById(coordsId).textContent = '';
        }

        // Update map preview
        updateMapPreview();
    }

    function handlePointCountChange(e) {
        document.getElementById('point-count-value').textContent = `${e.target.value} points`;
    }

    async function handleFormSubmit(e) {
        e.preventDefault();

        const startSelect = document.getElementById('start-location');
        const endSelect = document.getElementById('end-location');
        const pointCount = parseInt(document.getElementById('point-count').value);        if (!startSelect.value || !endSelect.value) {
            UIHelpers.showToast('Vui lòng chọn cả điểm xuất phát và điểm đích', 'error');
            return;
        }

        if (startSelect.value === endSelect.value) {
            UIHelpers.showToast('Điểm xuất phát và điểm đích phải khác nhau', 'error');
            return;
        }

        const startId = parseInt(startSelect.value);
        const endId = parseInt(endSelect.value);

        try {
            UIHelpers.showLoading(document.getElementById('route-tbody'));
            document.getElementById('route-results').style.display = 'block';

            const data = await WeatherApi.getRouteWeather(startId, endId, pointCount);

            state.currentRoute = {
                startId,
                endId,
                pointCount,
                data
            };

            displayRouteResults(data);
        } catch (error) {
            UIHelpers.showToast(error.message, 'error');
        }
    }

    function handleRouteClick(e) {
        const item = e.target.closest('.route-item');
        if (!item) return;

        const startId = item.dataset.start;
        const endId = item.dataset.end;

        document.getElementById('start-location').value = startId;
        document.getElementById('end-location').value = endId;

        // Trigger change events
        document.getElementById('start-location').dispatchEvent(new Event('change'));
        document.getElementById('end-location').dispatchEvent(new Event('change'));
    }    async function handleSaveRoute() {
        if (!state.isAuthenticated) {
            UIHelpers.showToast('Vui lòng đăng nhập để lưu tuyến đường', 'error');
            return;
        }

        if (!state.currentRoute) {
            UIHelpers.showToast('Không có tuyến đường để lưu', 'error');
            return;
        }

        const name = prompt('Nhập tên cho tuyến đường này:');
        if (!name) return;

        try {
            const response = await WeatherApi.post('/api/routes/', {
                name,
                start_id: state.currentRoute.startId,
                end_id: state.currentRoute.endId
            });

            UIHelpers.showToast('Đã lưu tuyến đường thành công!', 'success');
            // Reload page to update route list
            location.reload();
        } catch (error) {
            UIHelpers.showToast(error.message, 'error');
        }
    }

    // ========================================
    // Map Updates
    // ========================================
    function updateMapPreview() {
        MapCore.clearMarkerGroup(state.markerGroup);
        if (state.routeLine) {
            state.map.removeLayer(state.routeLine);
            state.routeLine = null;
        }

        const startSelect = document.getElementById('start-location');
        const endSelect = document.getElementById('end-location');

        const points = [];        if (startSelect.value) {
            const opt = startSelect.options[startSelect.selectedIndex];
            const lat = parseFloat(opt.dataset.lat);
            const lng = parseFloat(opt.dataset.lng);
            const marker = L.marker([lat, lng], {
                icon: createColoredIcon('green')
            }).bindPopup('<strong>Điểm xuất phát (A)</strong>');
            state.markerGroup.addLayer(marker);
            points.push([lat, lng]);
        }

        if (endSelect.value) {
            const opt = endSelect.options[endSelect.selectedIndex];
            const lat = parseFloat(opt.dataset.lat);
            const lng = parseFloat(opt.dataset.lng);
            const marker = L.marker([lat, lng], {
                icon: createColoredIcon('red')
            }).bindPopup('<strong>Điểm đích (B)</strong>');
            state.markerGroup.addLayer(marker);
            points.push([lat, lng]);
        }

        // Draw line if both points selected
        if (points.length === 2) {
            state.routeLine = MapCore.drawRoute(state.map, points, {
                dashArray: '10, 10',
                opacity: 0.6
            });
            MapCore.fitBounds(state.map, points);
        } else if (points.length === 1) {
            state.map.setView(points[0], 10);
        }
    }

    function displayRouteResults(data) {
        // Clear and redraw map
        MapCore.clearMarkerGroup(state.markerGroup);
        if (state.routeLine) {
            state.map.removeLayer(state.routeLine);
        }

        const points = data.route_points.map(p => [p.latitude, p.longitude]);

        // Draw route line
        state.routeLine = MapCore.drawRoute(state.map, points, {
            color: '#2563eb',
            weight: 4
        });        // Add markers for each point
        data.route_points.forEach((point, index) => {
            const isStart = index === 0;
            const isEnd = index === data.route_points.length - 1;

            let icon;
            let label;
            if (isStart) {
                icon = createColoredIcon('green');
                label = 'Xuất phát (A)';
            } else if (isEnd) {
                icon = createColoredIcon('red');
                label = 'Đích (B)';
            } else {
                icon = createSmallIcon();
                label = `Điểm ${index + 1}`;
            }

            const popupContent = `
                <div class="gis-popup">
                    <div class="popup-header">${label}</div>
                    <div class="popup-coords">${UIHelpers.formatCoords(point.latitude, point.longitude)}</div>
                    <div class="weather-info">
                        <p>Nhiệt độ: ${UIHelpers.formatTemp(point.weather.temperature)}</p>
                        <p>Gió: ${UIHelpers.formatWind(point.weather.wind_speed)}</p>
                        <p>Điều kiện: ${point.weather.description}</p>
                    </div>
                </div>
            `;

            const marker = L.marker([point.latitude, point.longitude], { icon })
                .bindPopup(popupContent);
            state.markerGroup.addLayer(marker);
        });

        // Fit map to route
        MapCore.fitBounds(state.map, points);

        // Render table
        renderRouteTable(data.route_points);
    }    function renderRouteTable(routePoints) {
        const tbody = document.getElementById('route-tbody');

        const rows = routePoints.map((point, index) => {
            const label = index === 0 ? 'A (Xuất phát)' : 
                         index === routePoints.length - 1 ? 'B (Đích)' : 
                         `${index + 1}`;
            return `
                <tr>
                    <td>${label}</td>
                    <td>${UIHelpers.formatCoords(point.latitude, point.longitude)}</td>
                    <td>${UIHelpers.formatTemp(point.weather.temperature)}</td>
                    <td>${UIHelpers.formatHumidity(point.weather.humidity)}</td>
                    <td>${UIHelpers.formatWind(point.weather.wind_speed)}</td>
                    <td>${point.weather.description}</td>
                </tr>
            `;
        }).join('');

        tbody.innerHTML = rows;
    }

    // ========================================
    // Helper Functions
    // ========================================
    function createColoredIcon(color) {
        const colors = {
            green: '#10b981',
            red: '#ef4444',
            blue: '#2563eb'
        };

        return L.divIcon({
            className: 'custom-marker',
            html: `<div style="
                background: ${colors[color] || color};
                width: 24px;
                height: 24px;
                border-radius: 50%;
                border: 3px solid white;
                box-shadow: 0 2px 6px rgba(0,0,0,0.3);
            "></div>`,
            iconSize: [24, 24],
            iconAnchor: [12, 12],
            popupAnchor: [0, -12]
        });
    }

    function createSmallIcon() {
        return L.divIcon({
            className: 'custom-marker-small',
            html: `<div style="
                background: #2563eb;
                width: 12px;
                height: 12px;
                border-radius: 50%;
                border: 2px solid white;
                box-shadow: 0 1px 4px rgba(0,0,0,0.3);
            "></div>`,
            iconSize: [12, 12],
            iconAnchor: [6, 6],
            popupAnchor: [0, -6]
        });
    }

    // ========================================
    // Initialize
    // ========================================
    document.addEventListener('DOMContentLoaded', init);
})();
