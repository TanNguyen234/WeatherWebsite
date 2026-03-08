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
        searchMarker: null,        // dedicated marker for geocoding search results
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
        // Place search
        initPlaceSearch();

        // Group filter change
        const groupFilter = document.getElementById('group-filter');
        if (groupFilter) {
            groupFilter.addEventListener('change', handleGroupFilterChange);
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
    } function createLoadingPopup(lat, lng) {
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
    } function renderMapMarkers() {
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
    } function addToCompare(lat, lng) {
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
    // Place Search  (proxy → fallback to direct Nominatim)
    // ========================================
    function initPlaceSearch() {
        var input = document.getElementById('place-search');
        var results = document.getElementById('search-results');
        var clearBtn = document.getElementById('place-search-clear');
        var searchBtn = document.getElementById('place-search-btn');

        if (!input || !results) return;

        var debounceTimer = null;

        function triggerSearch() {
            var q = input.value.trim();
            if (q.length < 2) {
                showSearchMsg(results, 'Nhập ít nhất 2 ký tự để tìm kiếm', 'empty');
                console.log("Searching for:", q);
                return;
            }
            searchPlaces(q, results);
        }

        // Debounced auto-suggest while typing
        input.addEventListener('input', function () {
            var q = this.value.trim();
            if (clearBtn) clearBtn.style.display = q ? 'block' : 'none';
            clearTimeout(debounceTimer);
            if (q.length < 2) { hideSearchResults(results); return; }
            debounceTimer = setTimeout(triggerSearch, 400);
        });

        // Enter key
        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                clearTimeout(debounceTimer);
                triggerSearch();
            }
        });

        // Search button – stopPropagation so document mousedown doesn't close dropdown
        if (searchBtn) {
            searchBtn.addEventListener('click', function (e) {
                e.stopPropagation();
                console.log("Click");
                clearTimeout(debounceTimer);
                triggerSearch();
                input.focus();
            });
        }

        // Clear button
        if (clearBtn) {
            clearBtn.addEventListener('click', function (e) {
                e.stopPropagation();
                input.value = '';
                clearBtn.style.display = 'none';
                hideSearchResults(results);
                input.focus();
            });
        }

        // Close on outside mousedown
        document.addEventListener('mousedown', function (e) {
            if (!e.target.closest('.map-search-overlay')) {
                hideSearchResults(results);
            }
        });
    }

    function searchPlaces(query, resultsEl) {
        showSearchMsg(resultsEl, 'Đang tìm…', 'loading');

        // Primary: Django proxy (avoids CORS headers issue)
        fetch('/api/geocode/?q=' + encodeURIComponent(query))
            .then(function (res) {
                if (!res.ok) throw new Error('proxy-' + res.status);
                console.log("Query key search: ", query);
                return res.json();
            })
            .then(function (data) {
                if (data && data.error) throw new Error('proxy-error');
                renderSearchResults(data, resultsEl);
            })
            .catch(function () {
                // Fallback: call Nominatim directly (plain GET = no preflight = no CORS issue)
                fetch('https://nominatim.openstreetmap.org/search?q=' +
                    encodeURIComponent(query) +
                    '&format=json&limit=6&addressdetails=0&accept-language=vi')
                    .then(function (res) {
                        if (!res.ok) throw new Error('HTTP ' + res.status);
                        return res.json();
                    })
                    .then(function (data) { renderSearchResults(data, resultsEl); })
                    .catch(function (err) { showSearchMsg(resultsEl, '⚠ ' + err.message, 'error'); });
            });
    }

    function renderSearchResults(items, resultsEl) {
        if (!items || items.length === 0) {
            showSearchMsg(resultsEl, 'Không tìm thấy địa điểm', 'empty');
            return;
        }

        var html = items.map(function (item) {
            var lat = parseFloat(item.lat);
            var lng = parseFloat(item.lon);
            var name = (item.display_name || '').replace(/</g, '&lt;');
            return '<li class="map-search-item" data-lat="' + lat + '" data-lng="' + lng + '">'
                + '<span class="map-search-item-name">' + name + '</span>'
                + '<span class="map-search-item-coords">' + lat.toFixed(4) + ', ' + lng.toFixed(4) + '</span>'
                + '</li>';
        }).join('');

        resultsEl.innerHTML = html;
        resultsEl.style.display = 'block';

        resultsEl.querySelectorAll('.map-search-item[data-lat]').forEach(function (li) {
            li.addEventListener('mousedown', function (e) {
                e.preventDefault();
                e.stopPropagation(); // prevent document mousedown from closing list first
                var lat = parseFloat(li.dataset.lat);
                var lng = parseFloat(li.dataset.lng);
                var nameEl = li.querySelector('.map-search-item-name');
                var inp = document.getElementById('place-search');
                var clrBtn = document.getElementById('place-search-clear');

                if (inp && nameEl) inp.value = nameEl.textContent;
                if (clrBtn) clrBtn.style.display = 'block';
                hideSearchResults(resultsEl);

                var placeName = nameEl ? nameEl.textContent : '';
                state.map.flyTo([lat, lng], 14, { animate: true, duration: 1 });
                showSearchResultMarker(lat, lng, placeName);
            });
        });
    }

    // ========================================
    // Search Result Marker – shows place name popup
    // ========================================
    /**
     * Place a dedicated marker for the geocoding result.
     * Popup shows: place name, coordinates, and action buttons.
     * A separate "Xem thời tiết" button loads weather on demand
     * without blocking the initial name display.
     *
     * Geocoding API: Nominatim (OpenStreetMap)
     *   Primary:  GET /api/geocode/?q=…  (Django proxy → nominatim.openstreetmap.org/search)
     *   Fallback: GET https://nominatim.openstreetmap.org/search?q=…&format=json  (direct)
     * Both are FREE and require no API key.
     */
    function showSearchResultMarker(lat, lng, placeName) {
        // Remove previous search marker
        if (state.searchMarker) {
            state.map.removeLayer(state.searchMarker);
            state.searchMarker = null;
        }

        var shortName = placeName || (UIHelpers.formatCoords(lat, lng));
        // Truncate very long display names for the popup header
        var displayName = shortName.length > 80 ? shortName.substring(0, 77) + '…' : shortName;

        var popupContent = '<div class="gis-popup search-result-popup">'
            + '<div class="popup-header">📍 ' + displayName.replace(/</g, '&lt;') + '</div>'
            + '<div class="popup-coords">' + UIHelpers.formatCoords(lat, lng) + '</div>'
            + '<div class="popup-actions">'
            + '<button class="btn-popup" data-action="load-weather-search" data-lat="' + lat + '" data-lng="' + lng + '">🌤 Xem thời tiết</button>'
            + (state.isAuthenticated
                ? '<button class="btn-popup btn-outline" data-action="save" data-lat="' + lat + '" data-lng="' + lng + '">💾 Lưu vị trí</button>'
                : '')
            + '</div>'
            + '</div>';

        // Use a distinct search-result icon (blue circle)
        var searchIcon = L.divIcon({
            className: 'search-result-marker',
            html: '<div style="background:#2563eb;width:20px;height:20px;border-radius:50%;border:3px solid #fff;box-shadow:0 2px 8px rgba(37,99,235,.55);"></div>',
            iconSize: [20, 20],
            iconAnchor: [10, 10],
            popupAnchor: [0, -12]
        });

        state.searchMarker = L.marker([lat, lng], { icon: searchIcon })
            .bindPopup(popupContent, { maxWidth: 320 })
            .addTo(state.map);
        state.searchMarker.openPopup();
    }

    // ── "Xem thời tiết" button inside the search-result popup ───────────────
    // We handle this via the existing handlePopupAction dispatcher.
    // Add a case for 'load-weather-search':
    // (The existing switch already covers 'save', so we just add this one below.)
    // Override is done by hooking into document click delegation (already active).
    document.addEventListener('click', function (e) {
        var btn = e.target.closest('[data-action="load-weather-search"]');
        if (!btn) return;
        var lat = parseFloat(btn.dataset.lat);
        var lng = parseFloat(btn.dataset.lng);
        if (isNaN(lat) || isNaN(lng)) return;

        btn.disabled = true;
        btn.textContent = '⏳ Đang tải…';

        WeatherApi.getCurrentWeather(lat, lng)
            .then(function (weather) {
                // Replace the popup content with full weather details
                var weatherContent = UIHelpers.createWeatherPopupContent(
                    { lat, lng, weather, name: null },
                    { isAuthenticated: state.isAuthenticated }
                );
                if (state.searchMarker) {
                    state.searchMarker.setPopupContent(weatherContent);
                    state.searchMarker.openPopup();
                }
            })
            .catch(function (err) {
                if (btn) { btn.disabled = false; btn.textContent = '🌤 Xem thời tiết'; }
                UIHelpers.showToast('Không lấy được thời tiết: ' + err.message, 'error');
            });
    });

    function showSearchMsg(resultsEl, msg, type) {
        resultsEl.innerHTML =
            '<li class="map-search-item map-search-item--' + (type || 'empty') + '">' + msg + '</li>';
        resultsEl.style.display = 'block';
    }

    function hideSearchResults(resultsEl) {
        if (!resultsEl) return;
        resultsEl.style.display = 'none';
        resultsEl.innerHTML = '';
    }

    // ========================================
    // Initialize on DOM ready
    // ========================================
    document.addEventListener('DOMContentLoaded', init);
})();
