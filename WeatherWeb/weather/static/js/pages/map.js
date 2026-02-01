/**
 * filepath: d:\Projects\WeatherWebsite\WeatherWeb\weather\static\js\pages\map.js
 * Map Page - Main JavaScript
 * Single-point spatial interaction
 */

(function () {
    'use strict';

    // ========================================
    // State Management
    // ========================================
    const state = {
        map: null,
        markerGroup: null,
        currentPopupMarker: null,
        locations: [],
        groups: [],
        isAuthenticated: false,
        selectedGroupId: null
    };

    // ========================================
    // Initialization
    // ========================================
    function init() {
        loadInitialData();
        initializeMap();
        bindEvents();
        renderLocationList();
        updateLocationCount();
    }

    function loadInitialData() {
        const data = UIHelpers.parseInitialData('initial-data');
        if (data) {
            state.locations = data.locations || [];
            state.groups = data.groups || [];
            state.isAuthenticated = data.isAuthenticated || false;
        }
    }

    function initializeMap() {
        state.map = MapCore.initMap('map', {
            center: [16.0, 106.0],
            zoom: 6
        });

        state.markerGroup = MapCore.createMarkerGroup(state.map);

        // Setup click handler
        MapCore.setupMapClick(state.map, handleMapClick);

        // Add existing location markers
        renderMapMarkers();
    }

    // ========================================
    // Event Binding
    // ========================================
    function bindEvents() {
        // Group filter change
        const groupFilter = document.getElementById('group-filter');
        if (groupFilter) {
            groupFilter.addEventListener('change', handleGroupFilterChange);
        }

        // Quick add form
        const quickAddForm = document.getElementById('quick-add-form');
        if (quickAddForm) {
            quickAddForm.addEventListener('submit', handleQuickAdd);
        }

        // Location list click delegation
        const locationList = document.getElementById('location-list');
        if (locationList) {
            locationList.addEventListener('click', handleLocationListClick);
        }

        // Popup action delegation (using document for dynamic popups)
        document.addEventListener('click', handlePopupAction);
    }

    // ========================================
    // Map Interaction
    // ========================================
    async function handleMapClick(lat, lng) {
        // Remove previous popup marker
        if (state.currentPopupMarker) {
            state.map.removeLayer(state.currentPopupMarker);
        }

        // Show loading popup
        const loadingContent = createLoadingPopup(lat, lng);
        state.currentPopupMarker = MapCore.addMarkerWithPopup(
            state.map, lat, lng, loadingContent
        );
        state.currentPopupMarker.openPopup();

        try {
            // Fetch weather data
            const weather = await WeatherApi.getCurrentWeather(lat, lng);

            // Update popup with weather data
            const popupContent = UIHelpers.createWeatherPopupContent({
                lat, lng, weather, name: null
            }, { isAuthenticated: state.isAuthenticated });

            state.currentPopupMarker.setPopupContent(popupContent);
        } catch (error) {
            const errorContent = createErrorPopup(lat, lng, error.message);
            state.currentPopupMarker.setPopupContent(errorContent);
        }
    }    function createLoadingPopup(lat, lng) {
        return `
            <div class="gis-popup">
                <div class="popup-header">Đang tải...</div>
                <div class="popup-coords">${UIHelpers.formatCoords(lat, lng)}</div>
                <div class="loading"><div class="spinner"></div></div>
            </div>
        `;
    }

    function createErrorPopup(lat, lng, message) {
        return `
            <div class="gis-popup">
                <div class="popup-header">Lỗi</div>
                <div class="popup-coords">${UIHelpers.formatCoords(lat, lng)}</div>
                <p style="color: var(--danger);">${message}</p>
                ${state.isAuthenticated ? `
                <div class="popup-actions">
                    <button class="btn-popup" data-action="save" data-lat="${lat}" data-lng="${lng}">
                        Vẫn lưu vị trí
                    </button>
                </div>
                ` : ''}
            </div>
        `;
    }

    // ========================================
    // Location List
    // ========================================
    function renderLocationList() {
        const container = document.getElementById('location-list');
        if (!container) return;

        const filteredLocations = filterLocationsByGroup(state.locations);
        UIHelpers.renderLocationList(container, filteredLocations, {
            showDelete: state.isAuthenticated
        });
    }

    function filterLocationsByGroup(locations) {
        if (!state.selectedGroupId) return locations;

        // Filter by group - would need group items data
        // For now, return all locations
        return locations;
    }

    function updateLocationCount() {
        const countEl = document.getElementById('location-count');
        if (countEl) {
            countEl.textContent = state.locations.length;
        }
    }    function renderMapMarkers() {
        MapCore.clearMarkerGroup(state.markerGroup);

        state.locations.forEach(location => {
            const marker = L.marker([location.latitude, location.longitude]);
            
            const popupContent = `
                <div class="gis-popup">
                    <div class="popup-header">${location.name || 'Vị trí đã lưu'}</div>
                    <div class="popup-coords">${UIHelpers.formatCoords(location.latitude, location.longitude)}</div>
                    <div class="popup-actions">
                        <button class="btn-popup btn-outline" data-action="weather" 
                            data-id="${location.id}" data-lat="${location.latitude}" data-lng="${location.longitude}">
                            Xem thời tiết
                        </button>
                        <button class="btn-popup btn-outline" data-action="delete" data-id="${location.id}">
                            Xóa
                        </button>
                    </div>
                </div>
            `;
            
            marker.bindPopup(popupContent);
            state.markerGroup.addLayer(marker);
        });

        // Fit bounds if locations exist
        if (state.locations.length > 0) {
            const bounds = state.locations.map(l => [l.latitude, l.longitude]);
            MapCore.fitBounds(state.map, bounds);
        }
    }

    // ========================================
    // Event Handlers
    // ========================================
    function handleGroupFilterChange(e) {
        state.selectedGroupId = e.target.value || null;
        renderLocationList();
    }

    async function handleQuickAdd(e) {
        e.preventDefault();        if (!state.isAuthenticated) {
            UIHelpers.showToast('Vui lòng đăng nhập để lưu vị trí', 'error');
            return;
        }

        const lat = parseFloat(document.getElementById('input-lat').value);
        const lng = parseFloat(document.getElementById('input-lng').value);
        const name = document.getElementById('input-name').value || null;

        if (isNaN(lat) || isNaN(lng)) {
            UIHelpers.showToast('Vui lòng nhập tọa độ hợp lệ', 'error');
            return;
        }

        if (lat < -90 || lat > 90 || lng < -180 || lng > 180) {
            UIHelpers.showToast('Tọa độ nằm ngoài phạm vi hợp lệ', 'error');
            return;
        }

        try {
            const result = await WeatherApi.saveLocation(lat, lng, name);
            
            // Add to state
            state.locations.push(result.location);
            
            // Update UI
            renderLocationList();
            renderMapMarkers();
            updateLocationCount();
            
            // Clear form
            document.getElementById('quick-add-form').reset();
            
            // Pan to new location
            MapCore.panTo(state.map, lat, lng, 10);
              UIHelpers.showToast('Đã lưu vị trí thành công!', 'success');
        } catch (error) {
            UIHelpers.showToast(error.message, 'error');
        }
    }

    function handleLocationListClick(e) {
        const item = e.target.closest('.location-item');
        if (!item) return;

        // Check if delete button clicked
        const deleteBtn = e.target.closest('[data-action="delete"]');
        if (deleteBtn) {
            const id = parseInt(deleteBtn.dataset.id);
            deleteLocation(id);
            return;
        }

        // Pan to location
        const lat = parseFloat(item.dataset.lat);
        const lng = parseFloat(item.dataset.lng);
        MapCore.panTo(state.map, lat, lng, 12);

        // Highlight item
        document.querySelectorAll('.location-item').forEach(el => el.classList.remove('active'));
        item.classList.add('active');
    }

    async function handlePopupAction(e) {
        const btn = e.target.closest('[data-action]');
        if (!btn || !btn.closest('.gis-popup')) return;

        const action = btn.dataset.action;
        const lat = parseFloat(btn.dataset.lat);
        const lng = parseFloat(btn.dataset.lng);
        const id = btn.dataset.id ? parseInt(btn.dataset.id) : null;

        switch (action) {
            case 'save':
                await saveLocationFromPopup(lat, lng);
                break;
            case 'delete':
                await deleteLocation(id);
                break;
            case 'weather':
                await showWeatherForLocation(id, lat, lng);
                break;
            case 'compare':
                addToCompare(lat, lng);
                break;
            case 'route':
                useForRoute(lat, lng);
                break;
        }
    }

    // ========================================
    // Actions
    // ========================================
    async function saveLocationFromPopup(lat, lng) {
        if (!state.isAuthenticated) {
            UIHelpers.showToast('Vui lòng đăng nhập để lưu vị trí', 'error');
            return;
        }

        const name = prompt('Nhập tên cho vị trí này (tùy chọn):');

        try {
            const result = await WeatherApi.saveLocation(lat, lng, name);
            state.locations.push(result.location);
            renderLocationList();
            renderMapMarkers();
            updateLocationCount();
            UIHelpers.showToast('Đã lưu vị trí!', 'success');

            // Close popup
            if (state.currentPopupMarker) {
                state.currentPopupMarker.closePopup();
            }
        } catch (error) {
            UIHelpers.showToast(error.message, 'error');
        }
    }

    async function deleteLocation(id) {
        if (!confirm('Bạn có chắc chắn muốn xóa vị trí này?')) return;

        try {
            await WeatherApi.deleteLocation(id);
            state.locations = state.locations.filter(l => l.id !== id);
            renderLocationList();
            renderMapMarkers();
            updateLocationCount();
            UIHelpers.showToast('Đã xóa vị trí', 'success');
        } catch (error) {
            UIHelpers.showToast(error.message, 'error');
        }
    }

    async function showWeatherForLocation(id, lat, lng) {
        try {
            const weather = await WeatherApi.getCurrentWeather(lat, lng);
            const location = state.locations.find(l => l.id === id);
            
            const content = UIHelpers.createWeatherPopupContent({
                lat, lng, weather,
                name: location ? location.name : null
            }, { isAuthenticated: state.isAuthenticated, showActions: false });

            // Find and update the marker popup
            state.markerGroup.eachLayer(marker => {
                const markerLatLng = marker.getLatLng();
                if (Math.abs(markerLatLng.lat - lat) < 0.0001 && 
                    Math.abs(markerLatLng.lng - lng) < 0.0001) {
                    marker.setPopupContent(content);
                }
            });
        } catch (error) {
            UIHelpers.showToast(error.message, 'error');
        }
    }    function addToCompare(lat, lng) {
        // Store in sessionStorage for compare page
        const compareList = JSON.parse(sessionStorage.getItem('compareLocations') || '[]');
        compareList.push({ lat, lng, timestamp: Date.now() });
        sessionStorage.setItem('compareLocations', JSON.stringify(compareList));
        UIHelpers.showToast('Đã thêm vào danh sách so sánh. Vào trang So sánh để xem.', 'success');
    }

    function useForRoute(lat, lng) {
        // Store in sessionStorage for route page
        const routePoints = JSON.parse(sessionStorage.getItem('routePoints') || '[]');
        if (routePoints.length >= 2) {
            routePoints.shift(); // Remove first point if already have 2
        }
        routePoints.push({ lat, lng });
        sessionStorage.setItem('routePoints', JSON.stringify(routePoints));
        UIHelpers.showToast('Đã thêm vào tuyến đường. Vào trang Tuyến đường để tiếp tục.', 'success');
    }

    // ========================================
    // Initialize on DOM ready
    // ========================================
    document.addEventListener('DOMContentLoaded', init);
})();
