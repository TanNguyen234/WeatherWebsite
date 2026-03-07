/**
 * Route Page – Real road routing via OSRM
 * Road geometry: fetched via Django proxy /api/route-geometry/ → OSRM server-side
 * Weather points: sampled evenly along the real road, fetched from our API
 */

(function () {
    'use strict';

    // ── State ──────────────────────────────────────────────────
    var state = {
        map:             null,
        routePolyline:   null,   // L.polyline of the real road
        markerGroup:     null,
        locations:       [],
        routes:          [],
        isAuthenticated: false,
        currentRoute:    null    // { startId, endId, pointCount, osrmData, weatherPoints }
    };

    // ── Init ───────────────────────────────────────────────────
    function init() {
        loadInitialData();
        loadFromSession();
        initializeMap();
        bindEvents();
    }

    function loadInitialData() {
        var data = UIHelpers.parseInitialData('initial-data');
        if (data) {
            state.locations       = data.locations       || [];
            state.routes          = data.routes          || [];
            state.isAuthenticated = data.isAuthenticated || false;
        }
    }

    function loadFromSession() {
        try {
            var pts = JSON.parse(sessionStorage.getItem('routePoints') || '[]');
            if (pts.length >= 2) {
                pts.forEach(function (point, i) {
                    var matched = state.locations.find(function (l) {
                        return Math.abs(l.latitude  - point.lat) < 0.0001 &&
                               Math.abs(l.longitude - point.lng) < 0.0001;
                    });
                    if (matched) {
                        var sel = document.getElementById(i === 0 ? 'start-location' : 'end-location');
                        if (sel) sel.value = matched.id;
                    }
                });
            }
        } catch (e) { /* ignore */ }
        sessionStorage.removeItem('routePoints');
    }

    function initializeMap() {
        state.map         = MapCore.initMap('map', { center: [16.0, 106.0], zoom: 6 });
        state.markerGroup = MapCore.createMarkerGroup(state.map);
    }

    // ── Events ─────────────────────────────────────────────────
    function bindEvents() {
        document.getElementById('route-form').addEventListener('submit', handleFormSubmit);
        document.getElementById('start-location').addEventListener('change', handleLocationChange);
        document.getElementById('end-location').addEventListener('change', handleLocationChange);
        document.getElementById('point-count').addEventListener('input', handlePointCountChange);
        document.getElementById('route-list').addEventListener('click', handleRouteClick);
        document.getElementById('save-route-btn').addEventListener('click', handleSaveRoute);
    }

    function handleLocationChange(e) {
        var select  = e.target;
        var option  = select.options[select.selectedIndex];
        var coordId = select.id === 'start-location' ? 'start-coords' : 'end-coords';
        if (option && option.value) {
            document.getElementById(coordId).textContent =
                UIHelpers.formatCoords(parseFloat(option.dataset.lat), parseFloat(option.dataset.lng));
        } else {
            document.getElementById(coordId).textContent = '';
        }
        updateMapPreview();
    }

    function handlePointCountChange(e) {
        document.getElementById('point-count-value').textContent = e.target.value + ' điểm';
    }

    async function handleFormSubmit(e) {
        e.preventDefault();

        var startSel   = document.getElementById('start-location');
        var endSel     = document.getElementById('end-location');
        var pointCount = parseInt(document.getElementById('point-count').value, 10);

        if (!startSel.value || !endSel.value) {
            UIHelpers.showToast('Vui lòng chọn cả điểm xuất phát và điểm đích', 'error');
            return;
        }
        if (startSel.value === endSel.value) {
            UIHelpers.showToast('Điểm xuất phát và điểm đích phải khác nhau', 'error');
            return;
        }

        var startId  = parseInt(startSel.value, 10);
        var endId    = parseInt(endSel.value, 10);
        var startOpt = startSel.options[startSel.selectedIndex];
        var endOpt   = endSel.options[endSel.selectedIndex];
        var startCoord = { lat: parseFloat(startOpt.dataset.lat), lng: parseFloat(startOpt.dataset.lng) };
        var endCoord   = { lat: parseFloat(endOpt.dataset.lat),   lng: parseFloat(endOpt.dataset.lng) };

        document.getElementById('route-results').style.display = 'block';
        UIHelpers.showLoading(document.getElementById('route-tbody'));
        setRouteStatus('Đang tìm đường giao thông…', 'info');

        try {
            // 1. Get actual road geometry from OSRM
            var osrm = await fetchOsrmRoute(startCoord, endCoord);
            setRouteStatus('Đang lấy dữ liệu thời tiết…', 'info');

            // 2. Sample N evenly-spaced points along the road
            var roadCoords = osrm.geometry.coordinates; // [[lng,lat], …]
            var sampled    = sampleRoutePoints(roadCoords, pointCount);

            // 3. Fetch weather for each sampled road point
            var weatherPoints = await fetchWeatherForPoints(sampled);

            state.currentRoute = { startId, endId, pointCount, osrmData: osrm, weatherPoints };

            // 4. Render map + table
            displayRouteResults(osrm, weatherPoints);
            setRouteStatus(
                formatDistance(osrm.distance) + ' · ' + formatDuration(osrm.duration),
                'ok'
            );
        } catch (err) {
            setRouteStatus('Lỗi: ' + err.message, 'error');
            UIHelpers.showToast(err.message, 'error');
        }
    }

    function handleRouteClick(e) {
        var item = e.target.closest('.route-item');
        if (!item) return;
        document.getElementById('start-location').value = item.dataset.start;
        document.getElementById('end-location').value   = item.dataset.end;
        document.getElementById('start-location').dispatchEvent(new Event('change'));
        document.getElementById('end-location').dispatchEvent(new Event('change'));
    }

    async function handleSaveRoute() {
        if (!state.isAuthenticated) { UIHelpers.showToast('Vui lòng đăng nhập để lưu', 'error'); return; }
        if (!state.currentRoute)    { UIHelpers.showToast('Không có tuyến đường để lưu', 'error'); return; }
        var name = prompt('Nhập tên cho tuyến đường này:');
        if (!name) return;
        try {
            await WeatherApi.post('/api/routes/', {
                name,
                start_id: state.currentRoute.startId,
                end_id:   state.currentRoute.endId
            });
            UIHelpers.showToast('Đã lưu tuyến đường!', 'success');
            location.reload();
        } catch (err) {
            UIHelpers.showToast(err.message, 'error');
        }
    }

    // ── OSRM Routing (via Django /api/route-geometry/ proxy) ────
    /**
     * Fetch road geometry through our backend proxy which calls OSRM.
     * Returns { geometry: GeoJSON LineString, distance, duration }.
     * Using a proxy avoids CORS issues and per-IP browser rate-limits.
     */
    async function fetchOsrmRoute(start, end) {
        var url = '/api/route-geometry/'
            + '?slat=' + start.lat.toFixed(6)
            + '&slng=' + start.lng.toFixed(6)
            + '&elat=' + end.lat.toFixed(6)
            + '&elng=' + end.lng.toFixed(6);

        var resp = await fetch(url);
        var data = await resp.json();

        if (!resp.ok) {
            throw new Error(data.error || 'Lỗi định tuyến (' + resp.status + ')');
        }
        if (!data.geometry) {
            throw new Error('Không tìm thấy đường đi giữa hai điểm đã chọn');
        }

        // cross_border is now always false from the backend (backend rejects
        // routes that exit the country with a 422 error above).  Keep this
        // guard for forward-compatibility only – it should never be reached.
        if (data.cross_border) {
            throw new Error(
                'Không tìm được đường đi hoàn toàn trong lãnh thổ giữa hai điểm này. '
                + 'Thử chọn điểm gần hơn hoặc nằm trên trục đường chính trong nước.'
            );
        }

        return data; // { geometry, distance, duration, country, cross_border }
    }

    /**
     * Return n evenly-spaced [lng,lat] pairs from the road coordinate array.
     */
    function sampleRoutePoints(coords, n) {
        if (n <= 1)             return [coords[0]];
        if (coords.length <= n) return coords.slice();
        var result = [];
        var step   = (coords.length - 1) / (n - 1);
        for (var i = 0; i < n; i++) {
            result.push(coords[Math.round(i * step)]);
        }
        return result;
    }

    /**
     * Fetch current weather for every [lng,lat] pair.
     * Returns array of { latitude, longitude, index, weather }.
     */
    async function fetchWeatherForPoints(coordPairs) {
        var promises = coordPairs.map(function (pair, idx) {
            var lat = pair[1];
            var lng = pair[0];
            return WeatherApi.getCurrentWeather(lat, lng)
                .then(function (w) { return { latitude: lat, longitude: lng, index: idx, weather: w }; })
                .catch(function ()  { return { latitude: lat, longitude: lng, index: idx, weather: null }; });
        });
        return Promise.all(promises);
    }

    // ── Map rendering ────────────────────────────────────────────
    /**
     * Preview road path when user selects locations (before form submit).
     */
    async function updateMapPreview() {
        MapCore.clearMarkerGroup(state.markerGroup);
        if (state.routePolyline) { state.map.removeLayer(state.routePolyline); state.routePolyline = null; }

        var startSel = document.getElementById('start-location');
        var endSel   = document.getElementById('end-location');
        var points   = [];

        if (startSel.value) {
            var s = startSel.options[startSel.selectedIndex];
            var sLat = parseFloat(s.dataset.lat), sLng = parseFloat(s.dataset.lng);
            state.markerGroup.addLayer(
                L.marker([sLat, sLng], { icon: colorIcon('green') })
                 .bindPopup('<strong>Điểm xuất phát (A)</strong>')
            );
            points.push({ lat: sLat, lng: sLng });
        }

        if (endSel.value) {
            var en = endSel.options[endSel.selectedIndex];
            var eLat = parseFloat(en.dataset.lat), eLng = parseFloat(en.dataset.lng);
            state.markerGroup.addLayer(
                L.marker([eLat, eLng], { icon: colorIcon('red') })
                 .bindPopup('<strong>Điểm đích (B)</strong>')
            );
            points.push({ lat: eLat, lng: eLng });
        }

        if (points.length === 2) {
            // Show dashed road preview via OSRM proxy; no straight-line fallback.
            setRouteStatus('Đang tải đường giao thông…', 'info');
            fetchOsrmRoute(points[0], points[1])
                .then(function (osrm) {
                    state.routePolyline = drawRoadPolyline(osrm.geometry.coordinates, {
                        dashArray: '8 5', opacity: 0.65, color: '#3b82f6'
                    });
                    MapCore.fitBounds(
                        state.map,
                        osrm.geometry.coordinates.map(function (c) { return [c[1], c[0]]; })
                    );
                    setRouteStatus('Chọn “Phân tích” để lấy dữ liệu thời tiết.', 'info');
                })
                .catch(function (err) {
                    setRouteStatus('⚠ Không tải đường được: ' + err.message, 'error');
                    // Fit to markers only, no polyline
                    MapCore.fitBounds(state.map, [
                        [points[0].lat, points[0].lng],
                        [points[1].lat, points[1].lng]
                    ]);
                });
        } else if (points.length === 1) {
            state.map.setView([points[0].lat, points[0].lng], 10);
        }
    }

    /**
     * Draw road path + weather markers after form submit.
     */
    function displayRouteResults(osrm, weatherPoints) {
        MapCore.clearMarkerGroup(state.markerGroup);
        if (state.routePolyline) { state.map.removeLayer(state.routePolyline); }

        // Solid road polyline
        state.routePolyline = drawRoadPolyline(osrm.geometry.coordinates, {
            color: '#2563eb', weight: 5, opacity: 0.88
        });

        // Weather markers
        weatherPoints.forEach(function (pt, i) {
            var isStart = i === 0;
            var isEnd   = i === weatherPoints.length - 1;
            var icon    = isStart ? colorIcon('green') : isEnd ? colorIcon('red') : smallIcon();
            var label   = isStart ? 'Xuất phát (A)' : isEnd ? 'Đích (B)' : 'Điểm ' + (i + 1);
            var w       = pt.weather || {};

            var popup = '<div class="gis-popup">'
                + '<div class="popup-header">' + label + '</div>'
                + '<div class="popup-coords">' + UIHelpers.formatCoords(pt.latitude, pt.longitude) + '</div>'
                + '<div class="weather-info">';
            if (pt.weather) {
                popup += '<p>🌡 ' + UIHelpers.formatTemp(w.temperature) + '</p>'
                       + '<p>💨 ' + UIHelpers.formatWind(w.wind_speed)  + '</p>'
                       + '<p>💧 ' + (w.humidity !== undefined ? w.humidity + ' %' : '–') + '</p>'
                       + '<p>' + (w.description || '') + '</p>';
            } else {
                popup += '<p style="color:var(--danger)">Không có dữ liệu thời tiết</p>';
            }
            popup += '</div></div>';

            state.markerGroup.addLayer(L.marker([pt.latitude, pt.longitude], { icon }).bindPopup(popup));
        });

        // Fit to road
        MapCore.fitBounds(state.map, osrm.geometry.coordinates.map(function (c) { return [c[1], c[0]]; }));

        renderRouteTable(weatherPoints);
    }

    /**
     * Draw L.polyline from OSRM [lng,lat] coordinate pairs.
     */
    function drawRoadPolyline(coords, opts) {
        var latLngs  = coords.map(function (c) { return [c[1], c[0]]; });
        var defaults = { color: '#3b82f6', weight: 4, opacity: 0.85 };
        var options  = Object.assign({}, defaults, opts || {});
        return L.polyline(latLngs, options).addTo(state.map);
    }

    function renderRouteTable(points) {
        var tbody = document.getElementById('route-tbody');
        if (!points || !points.length) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted)">Không có điểm nào</td></tr>';
            return;
        }
        tbody.innerHTML = points.map(function (pt, i) {
            var label = i === 0 ? 'A (Xuất phát)' : i === points.length - 1 ? 'B (Đích)' : String(i + 1);
            var w = pt.weather || {};
            return '<tr>'
                + '<td>' + label + '</td>'
                + '<td>' + UIHelpers.formatCoords(pt.latitude, pt.longitude) + '</td>'
                + '<td>' + (w.temperature !== undefined ? UIHelpers.formatTemp(w.temperature) : '–') + '</td>'
                + '<td>' + (w.humidity    !== undefined ? w.humidity + ' %' : '–') + '</td>'
                + '<td>' + (w.wind_speed  !== undefined ? UIHelpers.formatWind(w.wind_speed) : '–') + '</td>'
                + '<td>' + (w.description || '–') + '</td>'
                + '</tr>';
        }).join('');
    }

    // ── Route status bar ─────────────────────────────────────────
    function setRouteStatus(msg, type) {
        var el = document.getElementById('route-status');
        if (!el) return;
        el.textContent = msg;
        el.className   = 'route-status route-status--' + (type || 'info');
    }

    // ── Pure helper functions ─────────────────────────────────
    function colorIcon(color) {
        var palette = { green: '#10b981', red: '#ef4444', blue: '#2563eb' };
        var fill    = palette[color] || color;
        return L.divIcon({
            className: 'custom-marker',
            html: '<div style="background:' + fill + ';width:22px;height:22px;border-radius:50%;border:3px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,.35)"></div>',
            iconSize: [22, 22], iconAnchor: [11, 11], popupAnchor: [0, -12]
        });
    }

    function smallIcon() {
        return L.divIcon({
            className: 'custom-marker-small',
            html: '<div style="background:#2563eb;width:11px;height:11px;border-radius:50%;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.3)"></div>',
            iconSize: [11, 11], iconAnchor: [5, 5], popupAnchor: [0, -6]
        });
    }

    function formatDistance(metres) {
        return metres >= 1000 ? (metres / 1000).toFixed(1) + ' km' : Math.round(metres) + ' m';
    }

    function formatDuration(seconds) {
        var h = Math.floor(seconds / 3600);
        var m = Math.floor((seconds % 3600) / 60);
        if (h > 0) return h + ' giờ ' + m + ' phút';
        return m + ' phút lái xe';
    }

    // ── Boot ────────────────────────────────────────────────────
    document.addEventListener('DOMContentLoaded', init);
})();
