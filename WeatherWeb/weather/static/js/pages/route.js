/**
 * Route Page – Road route + weather analysis
 * Uses backend bulk endpoint /api/route/ for geometry + sampled weather points.
 */

(function () {
    'use strict';

    var state = {
        map: null,
        routePolyline: null,
        segmentLayers: [],
        markerGroup: null,
        locations: [],
        routes: [],
        isAuthenticated: false,
        currentRoute: null
    };

    function init() {
        loadInitialData();
        loadFromSession();
        initializeMap();
        bindEvents();
    }

    function loadInitialData() {
        var data = UIHelpers.parseInitialData('initial-data');
        if (data) {
            state.locations = data.locations || [];
            state.routes = data.routes || [];
            state.isAuthenticated = data.isAuthenticated || false;
        }
    }

    function loadFromSession() {
        try {
            var pts = JSON.parse(sessionStorage.getItem('routePoints') || '[]');
            if (pts.length >= 2) {
                pts.forEach(function (point, i) {
                    var matched = state.locations.find(function (l) {
                        return Math.abs(l.latitude - point.lat) < 0.0001 && Math.abs(l.longitude - point.lng) < 0.0001;
                    });
                    if (matched) {
                        var sel = document.getElementById(i === 0 ? 'start-location' : 'end-location');
                        if (sel) {
                            sel.value = matched.id;
                        }
                    }
                });
            }
        } catch (e) {
            // Ignore session parse errors
        }
        sessionStorage.removeItem('routePoints');
    }

    function initializeMap() {
        state.map = MapCore.initMap('map', { center: [16.0, 106.0], zoom: 6 });
        state.markerGroup = MapCore.createMarkerGroup(state.map);
    }

    function bindEvents() {
        document.getElementById('route-form').addEventListener('submit', handleFormSubmit);
        document.getElementById('start-location').addEventListener('change', handleLocationChange);
        document.getElementById('end-location').addEventListener('change', handleLocationChange);
        document.getElementById('point-count').addEventListener('input', handlePointCountChange);
        document.getElementById('route-list').addEventListener('click', handleRouteClick);
        document.getElementById('save-route-btn').addEventListener('click', handleSaveRoute);
    }

    function handleLocationChange(e) {
        var select = e.target;
        var option = select.options[select.selectedIndex];
        var coordId = select.id === 'start-location' ? 'start-coords' : 'end-coords';
        var which   = select.id === 'start-location' ? 'start' : 'end';

        if (option && option.value === '__gps__') {
            var gps = window._gpsCoords && window._gpsCoords[which];
            if (gps) {
                document.getElementById(coordId).textContent = 'GPS: ' + gps.lat.toFixed(5) + ', ' + gps.lng.toFixed(5);
            } else {
                document.getElementById(coordId).textContent = 'Chờ GPS...';
            }
        } else if (option && option.dataset.lat) {
            document.getElementById(coordId).textContent = UIHelpers.formatCoords(parseFloat(option.dataset.lat), parseFloat(option.dataset.lng));
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

        var startSel = document.getElementById('start-location');
        var endSel = document.getElementById('end-location');
        var pointCount = parseInt(document.getElementById('point-count').value, 10);

        if (!startSel.value || !endSel.value) {
            UIHelpers.showToast('Vui lòng chọn cả điểm xuất phát và điểm đích', 'error');
            return;
        }
        if (startSel.value !== '__gps__' && endSel.value !== '__gps__' && startSel.value === endSel.value) {
            UIHelpers.showToast('Điểm xuất phát và điểm đích phải khác nhau', 'error');
            return;
        }

        // Build route payload — use raw lat/lng for GPS selections
        var payload = { point_count: pointCount };

        if (startSel.value === '__gps__') {
            var sg = window._gpsCoords && window._gpsCoords.start;
            if (!sg) {
                UIHelpers.showToast('Vui lòng nhấn 📍 để lấy vị trí GPS trước', 'error');
                return;
            }
            payload.start_lat = sg.lat;
            payload.start_lng = sg.lng;
        } else {
            payload.start_id = parseInt(startSel.value, 10);
        }

        if (endSel.value === '__gps__') {
            var eg = window._gpsCoords && window._gpsCoords.end;
            if (!eg) {
                UIHelpers.showToast('Vui lòng nhấn 📍 để lấy vị trí GPS cho điểm đích', 'error');
                return;
            }
            payload.end_lat = eg.lat;
            payload.end_lng = eg.lng;
        } else {
            payload.end_id = parseInt(endSel.value, 10);
        }

        showResultsPanel();
        UIHelpers.showLoading(document.getElementById('route-tbody'));
        setAnalyzeLoading(true);
        setRouteStatus('Đang phân tích tuyến đường và thời tiết...', 'info');

        try {
            var analysis = await WeatherApi.analyzeRouteWeather(payload);

            state.currentRoute = {
                startId: payload.start_id || null,
                endId: payload.end_id || null,
                startLat: payload.start_lat || null,
                startLng: payload.start_lng || null,
                endLat: payload.end_lat || null,
                endLng: payload.end_lng || null,
                pointCount: pointCount,
                analysis: analysis
            };


            setRouteStatus('Đang hiển thị tuyến đường...', 'info');
            clearRouteLayers();
            renderBaseRoute(analysis.geometry.coordinates);

            await waitNextFrame();
            setRouteStatus('Đang hiển thị lớp thời tiết...', 'info');
            renderWeatherSegments(analysis.segments || [], analysis.geometry.coordinates || []);
            renderWeatherMarkers(analysis.route_points || []);
            renderRouteTable(analysis.route_points || []);
            renderSummary(analysis.summary || {}, analysis.distance, analysis.duration);

            setRouteStatus(formatDistance(analysis.distance) + ' · ' + formatDuration(analysis.duration), 'ok');
        } catch (err) {
            setRouteStatus('Lỗi: ' + err.message, 'error');
            UIHelpers.showError(document.getElementById('route-tbody'), err.message || 'Không thể phân tích tuyến đường');
            UIHelpers.showToast(err.message, 'error');
        } finally {
            setAnalyzeLoading(false);
        }
    }

    function handleRouteClick(e) {
        var item = e.target.closest('.route-item');
        if (!item) {
            return;
        }
        document.getElementById('start-location').value = item.dataset.start;
        document.getElementById('end-location').value = item.dataset.end;
        document.getElementById('start-location').dispatchEvent(new Event('change'));
        document.getElementById('end-location').dispatchEvent(new Event('change'));
    }

    async function handleSaveRoute() {
        if (!state.isAuthenticated) {
            UIHelpers.showToast('Vui lòng đăng nhập để lưu', 'error');
            return;
        }
        if (!state.currentRoute) {
            UIHelpers.showToast('Không có tuyến đường để lưu', 'error');
            return;
        }

        var name = prompt('Nhập tên cho tuyến đường này:');
        if (!name) {
            return;
        }

        try {
            await WeatherApi.post('/api/routes/', {
                name: name,
                start_id: state.currentRoute.startId,
                end_id: state.currentRoute.endId,
                start_lat: state.currentRoute.startLat,
                start_lng: state.currentRoute.startLng,
                end_lat: state.currentRoute.endLat,
                end_lng: state.currentRoute.endLng
            });
            UIHelpers.showToast('Đã lưu tuyến đường!', 'success');
            location.reload();
        } catch (err) {
            UIHelpers.showToast(err.message, 'error');
        }
    }

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
        return data;
    }

    async function updateMapPreview() {
        clearRouteLayers();

        var startSel = document.getElementById('start-location');
        var endSel = document.getElementById('end-location');
        var points = [];

        if (startSel.value) {
            var s = startSel.options[startSel.selectedIndex];
            var sLat = parseFloat(s.dataset.lat);
            var sLng = parseFloat(s.dataset.lng);
            state.markerGroup.addLayer(L.marker([sLat, sLng], { icon: markerIcon('start') }).bindPopup('<strong>Điểm xuất phát (A)</strong>'));
            points.push({ lat: sLat, lng: sLng });
        }

        if (endSel.value) {
            var en = endSel.options[endSel.selectedIndex];
            var eLat = parseFloat(en.dataset.lat);
            var eLng = parseFloat(en.dataset.lng);
            state.markerGroup.addLayer(L.marker([eLat, eLng], { icon: markerIcon('end') }).bindPopup('<strong>Điểm đích (B)</strong>'));
            points.push({ lat: eLat, lng: eLng });
        }

        if (points.length === 2) {
            setRouteStatus('Đang tải đường giao thông...', 'info');
            fetchOsrmRoute(points[0], points[1])
                .then(function (osrm) {
                    state.routePolyline = drawRoadPolyline(osrm.geometry.coordinates, {
                        dashArray: '8 5',
                        opacity: 0.65,
                        color: '#3b82f6',
                        weight: 4
                    });
                    MapCore.fitBounds(state.map, osrm.geometry.coordinates.map(function (c) { return [c[1], c[0]]; }));
                    setRouteStatus('Chọn "Phân tích" để lấy dữ liệu thời tiết.', 'info');
                })
                .catch(function (err) {
                    setRouteStatus('Không tải đường được: ' + err.message, 'error');
                    MapCore.fitBounds(state.map, [[points[0].lat, points[0].lng], [points[1].lat, points[1].lng]]);
                });
        } else if (points.length === 1) {
            state.map.setView([points[0].lat, points[0].lng], 10);
        }
    }

    function clearRouteLayers() {
        MapCore.clearMarkerGroup(state.markerGroup);
        if (state.routePolyline) {
            state.map.removeLayer(state.routePolyline);
            state.routePolyline = null;
        }
        state.segmentLayers.forEach(function (layer) {
            state.map.removeLayer(layer);
        });
        state.segmentLayers = [];
    }

    function renderBaseRoute(coordinates) {
        state.routePolyline = drawRoadPolyline(coordinates, {
            color: '#94a3b8',
            weight: 6,
            opacity: 0.5
        });

        MapCore.fitBounds(state.map, coordinates.map(function (c) { return [c[1], c[0]]; }));
    }

    function renderWeatherSegments(segments, geometryCoordinates) {
        segments.forEach(function (segment, segmentIndex) {
            var weather = segment.weather || {};
            var severity = Number(weather.severity_score || 0);
            var latLngs = buildGeometrySegmentLatLngs(geometryCoordinates, segments.length, segmentIndex);

            if (!latLngs.length) {
                latLngs = [
                    [segment.start.latitude, segment.start.longitude],
                    [segment.end.latitude, segment.end.longitude]
                ];
            }

            var polyline = L.polyline(latLngs, {
                color: severityColor(severity, weather.status),
                weight: 7,
                opacity: 0.9
            }).addTo(state.map);

            var tooltip = 'Đoạn ' + (segment.start_index + 1) + ' → ' + (segment.end_index + 1)
                + '<br>Chỉ số: ' + severity.toFixed(2)
                + '<br>Mưa: ' + formatOptional(weather.rain_1h, ' mm')
                + '<br>Gió: ' + formatOptional(weather.wind_speed, ' m/s');

            polyline.bindTooltip(tooltip, { sticky: true, opacity: 0.95 });
            state.segmentLayers.push(polyline);
        });
    }

    function buildGeometrySegmentLatLngs(coords, segmentCount, segmentIndex) {
        if (!Array.isArray(coords) || coords.length < 2 || segmentCount < 1) {
            return [];
        }

        var cumulative = [0];
        var totalDistance = 0;
        for (var i = 1; i < coords.length; i++) {
            var prev = coords[i - 1];
            var curr = coords[i];
            totalDistance += haversineMeters(prev[1], prev[0], curr[1], curr[0]);
            cumulative.push(totalDistance);
        }

        if (totalDistance <= 0) {
            return coords.map(function (c) { return [c[1], c[0]]; });
        }

        var startTarget = (segmentIndex / segmentCount) * totalDistance;
        var endTarget = ((segmentIndex + 1) / segmentCount) * totalDistance;
        var startPoint = interpolatePointAtDistance(coords, cumulative, startTarget);
        var endPoint = interpolatePointAtDistance(coords, cumulative, endTarget);

        var path = [startPoint];
        for (var j = 1; j < cumulative.length - 1; j++) {
            if (cumulative[j] > startTarget && cumulative[j] < endTarget) {
                path.push([coords[j][1], coords[j][0]]);
            }
        }
        path.push(endPoint);

        return path;
    }

    function interpolatePointAtDistance(coords, cumulative, targetDistance) {
        if (targetDistance <= 0) {
            return [coords[0][1], coords[0][0]];
        }

        var lastIdx = cumulative.length - 1;
        if (targetDistance >= cumulative[lastIdx]) {
            return [coords[lastIdx][1], coords[lastIdx][0]];
        }

        var segmentIdx = 1;
        while (segmentIdx < cumulative.length && cumulative[segmentIdx] < targetDistance) {
            segmentIdx += 1;
        }

        var prevDistance = cumulative[segmentIdx - 1];
        var nextDistance = cumulative[segmentIdx];
        var ratio = (targetDistance - prevDistance) / Math.max(nextDistance - prevDistance, 1e-9);

        var start = coords[segmentIdx - 1];
        var end = coords[segmentIdx];
        var lng = start[0] + (end[0] - start[0]) * ratio;
        var lat = start[1] + (end[1] - start[1]) * ratio;
        return [lat, lng];
    }

    function haversineMeters(lat1, lon1, lat2, lon2) {
        var r = 6371000;
        var toRad = Math.PI / 180;
        var dLat = (lat2 - lat1) * toRad;
        var dLon = (lon2 - lon1) * toRad;
        var a = Math.sin(dLat / 2) * Math.sin(dLat / 2)
            + Math.cos(lat1 * toRad) * Math.cos(lat2 * toRad)
            * Math.sin(dLon / 2) * Math.sin(dLon / 2);
        var c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return r * c;
    }

    function renderWeatherMarkers(points) {
        points.forEach(function (pt, i) {
            var isStart = i === 0;
            var isEnd = i === points.length - 1;
            var icon = isStart ? markerIcon('start') : (isEnd ? markerIcon('end') : markerIcon('waypoint'));
            var label = isStart ? 'Xuất phát (A)' : (isEnd ? 'Đích (B)' : 'Điểm ' + i);
            var weather = pt.weather || {};

            var popup = '<div class="gis-popup">'
                + '<div class="popup-header">' + label + '</div>'
                + '<div class="popup-coords">' + UIHelpers.formatCoords(pt.latitude, pt.longitude) + '</div>'
                + '<div class="weather-info">';

            if (pt.weather) {
                popup += '<p>Nhiệt độ: <strong>' + formatValue(weather.temperature, '°C') + '</strong></p>'
                    + '<p>Độ ẩm: <strong>' + formatOptional(weather.humidity, ' %') + '</strong></p>'
                    + '<p>Gió: <strong>' + formatValue(weather.wind_speed, 'm/s') + '</strong></p>'
                    + '<p>Mưa 1h: <strong>' + formatOptional(weather.rain_1h, ' mm') + '</strong></p>'
                    + '<p>Nguồn: <strong>' + (pt.source || weather.source || 'N/A') + '</strong></p>'
                    + '<p>Trạng thái: <strong>' + pointStatusLabel(pt.status) + '</strong></p>'
                    + '<p>' + (weather.description || '--') + '</p>';
            } else {
                popup += '<p class="route-warning-text">Không có dữ liệu thời tiết</p>';
                if (pt.error) {
                    popup += '<p>' + pt.error + '</p>';
                }
            }

            popup += '</div></div>';

            state.markerGroup.addLayer(L.marker([pt.latitude, pt.longitude], { icon: icon }).bindPopup(popup));
        });
    }

    function renderSummary(summary, distance, duration) {
        var worstEl = document.getElementById('summary-worst');
        var tempEl = document.getElementById('summary-temp');
        var windEl = document.getElementById('summary-wind');
        var successEl = document.getElementById('summary-success');

        tempEl.textContent = summary.average_temperature !== null && summary.average_temperature !== undefined
            ? UIHelpers.formatTemp(summary.average_temperature)
            : '--';

        windEl.textContent = summary.average_wind_speed !== null && summary.average_wind_speed !== undefined
            ? UIHelpers.formatWind(summary.average_wind_speed)
            : '--';

        successEl.textContent = (summary.successful_points || 0) + '/' + (summary.total_points || 0)
            + ' điểm · ' + formatDistance(distance)
            + ' · ' + formatDuration(duration);

        if (summary.worst_segment && summary.worst_segment.weather) {
            var worst = summary.worst_segment;
            worstEl.textContent = 'Đoạn ' + (worst.start_index + 1) + ' → ' + (worst.end_index + 1)
                + ' (chỉ số ' + Number(worst.weather.severity_score || 0).toFixed(2) + ')';
        } else {
            worstEl.textContent = '--';
        }
    }

    function renderRouteTable(points) {
        var tbody = document.getElementById('route-tbody');
        if (!points || !points.length) {
            tbody.innerHTML = '<tr><td colspan="9" class="route-cell-empty">Không có điểm nào</td></tr>';
            return;
        }

        tbody.innerHTML = points.map(function (pt, i) {
            var label = i === 0 ? 'A (Xuất phát)' : (i === points.length - 1 ? 'B (Đích)' : 'Điểm ' + i);
            var weather = pt.weather || {};

            return '<tr>'
                + '<td>' + label + '</td>'
                + '<td>' + UIHelpers.formatCoords(pt.latitude, pt.longitude) + '</td>'
                + '<td>' + formatValue(weather.temperature, '°C') + '</td>'
                + '<td>' + formatValue(weather.humidity, '%') + '</td>'
                + '<td>' + formatValue(weather.wind_speed, 'm/s') + '</td>'
                + '<td>' + formatValue(weather.rain_1h, 'mm') + '</td>'
                + '<td>' + (pt.source || weather.source || '--') + '</td>'
                + '<td>' + pointStatusLabel(pt.status) + '</td>'
                + '<td>' + (weather.description || '--') + '</td>'
                + '</tr>';
        }).join('');
    }

    function drawRoadPolyline(coords, opts) {
        var latLngs = coords.map(function (c) { return [c[1], c[0]]; });
        var defaults = { color: '#3b82f6', weight: 4, opacity: 0.85 };
        var options = Object.assign({}, defaults, opts || {});
        return L.polyline(latLngs, options).addTo(state.map);
    }

    function setRouteStatus(msg, type) {
        var el = document.getElementById('route-status');
        if (!el) {
            return;
        }
        el.textContent = msg;
        el.className = 'route-status route-status--' + (type || 'info');
    }

    function setAnalyzeLoading(isLoading) {
        var btn = document.getElementById('analyze-route-btn');
        if (!btn) {
            return;
        }

        if (!btn.dataset.defaultLabel) {
            btn.dataset.defaultLabel = btn.textContent;
        }

        btn.disabled = !!isLoading;
        btn.textContent = isLoading ? 'Đang phân tích...' : btn.dataset.defaultLabel;
    }

    function showResultsPanel() {
        var panel = document.getElementById('route-results');
        if (panel) {
            panel.classList.remove('route-results--hidden');
        }
    }

    function markerIcon(type) {
        var markerClass = 'route-marker-waypoint';
        if (type === 'start') {
            markerClass = 'route-marker-start';
        } else if (type === 'end') {
            markerClass = 'route-marker-end';
        }

        return L.divIcon({
            className: 'custom-marker',
            html: '<div class="route-marker ' + markerClass + '"></div>',
            iconSize: type === 'waypoint' ? [12, 12] : [22, 22],
            iconAnchor: type === 'waypoint' ? [6, 6] : [11, 11],
            popupAnchor: [0, -10]
        });
    }

    function severityColor(score, status) {
        if (status === 'missing') {
            return '#6b7280';
        }
        if (score >= 8) {
            return '#dc2626';
        }
        if (score >= 4) {
            return '#d97706';
        }
        return '#16a34a';
    }

    function formatValue(value, suffix) {
        if (value === null || value === undefined || value === '') {
            return '--';
        }
        var str = Number.isFinite(Number(value)) ? Number(value).toFixed(1) : String(value);
        return suffix ? str + ' ' + suffix : str;
    }

    function formatOptional(value, suffix) {
        if (value === null || value === undefined) {
            return '--';
        }
        return Number(value).toFixed(1) + suffix;
    }

    function pointStatusLabel(status) {
        if (status === 'ok') {
            return 'Đầy đủ';
        }
        if (status === 'failed') {
            return 'Thiếu dữ liệu';
        }
        return status || '--';
    }

    function waitNextFrame() {
        return new Promise(function (resolve) {
            window.requestAnimationFrame(function () {
                resolve();
            });
        });
    }

    function formatDistance(metres) {
        if (!Number.isFinite(Number(metres))) {
            return '--';
        }
        return metres >= 1000 ? (metres / 1000).toFixed(1) + ' km' : Math.round(metres) + ' m';
    }

    function formatDuration(seconds) {
        if (!Number.isFinite(Number(seconds))) {
            return '--';
        }
        var h = Math.floor(seconds / 3600);
        var m = Math.floor((seconds % 3600) / 60);
        if (h > 0) {
            return h + ' giờ ' + m + ' phút';
        }
        return m + ' phút lái xe';
    }

    document.addEventListener('DOMContentLoaded', init);
})();
