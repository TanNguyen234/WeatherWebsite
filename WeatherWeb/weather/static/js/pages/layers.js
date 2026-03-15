/**
 * Layers Page – GIS weather layer control panel
 *
 * Behaviour:
 *  - Reads layer config from server-rendered JSON block (#initial-data).
 *  - When an OWM API key is present it adds real raster tile overlays via the
 *    OpenWeatherMap tile endpoint.
 *  - Falls back to value-labelled circle markers fetched from /api/layers/points/
 *    for instances without an API key (still shows real approximated data).
 *  - Opacity sliders, expand/collapse, basemap switching, chip bar, legend panel
 *    and coordinate infobar are fully wired up.
 */

(function () {
    'use strict';

    // ─── Constants ─────────────────────────────────────────────────────────────
    var VIETNAM_BOUNDS   = [[8.18, 102.14], [23.39, 109.46]];
    var VIETNAM_CENTER   = [16.0, 106.0];
    var DEFAULT_ZOOM     = 6;
    var REFRESH_MS       = 600000; // 10 minutes

    var BASEMAP_URLS = {
        osm:       'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        satellite: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        dark:      'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
    };

    var BASEMAP_ATTR = {
        osm:       '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        satellite: 'Tiles &copy; Esri',
        dark:      '&copy; OpenStreetMap &copy; CARTO'
    };

    // ─── State ─────────────────────────────────────────────────────────────────
    var state = {
        map:            null,
        baseTile:       null,
        layerConfig:    {},
        tileLayers:     {},
        markerGroups:   {},
        activeLayerIds: new Set(),
        apiKey:         '',
        labelsVisible:  true,
        refreshTimer:   null
    };

    // ─── Bootstrap ─────────────────────────────────────────────────────────────
    function init() {
        var raw = document.getElementById('initial-data');
        if (!raw) { console.error('[layers] #initial-data not found'); return; }

        var initialData    = JSON.parse(raw.textContent);
        state.layerConfig  = initialData.layers   || {};
        state.apiKey       = initialData.api_key  || '';

        initMap();
        populateSidebar();
        bindSidebarEvents();
        bindToolbarEvents();
        bindBasemapEvents();
        bindMapEvents();
        loadInitialLayers();
        scheduleRefresh();
    }

    // ─── Map init ──────────────────────────────────────────────────────────────
    function initMap() {
        state.map = MapCore.initMap('map', { center: VIETNAM_CENTER, zoom: DEFAULT_ZOOM });

        state.baseTile = L.tileLayer(BASEMAP_URLS.osm, {
            attribution: BASEMAP_ATTR.osm,
            maxZoom: 18
        }).addTo(state.map);
    }

    // ─── Sidebar ───────────────────────────────────────────────────────────────
    function populateSidebar() {
        document.querySelectorAll('.layer-card').forEach(function (card) {
            var body = card.querySelector('.layer-card-body');
            if (body && !body.classList.contains('collapsed')) {
                card.classList.add('expanded');
            }
        });
    }

    function bindSidebarEvents() {
        document.querySelectorAll('.layer-card').forEach(function (card) {
            var layerId    = card.dataset.layerId;
            var checkbox   = card.querySelector('#toggle-' + layerId);
            var expandBtn  = card.querySelector('.layer-expand-btn');
            var body       = card.querySelector('.layer-card-body');
            var header     = card.querySelector('.layer-card-header');

            if (header) {
                header.addEventListener('click', function (e) {
                    if (e.target.closest('.layer-toggle') || e.target.closest('.layer-expand-btn')) return;
                    toggleCardExpand(card, body);
                });
            }

            if (expandBtn) {
                expandBtn.addEventListener('click', function (e) {
                    e.stopPropagation();
                    toggleCardExpand(card, body);
                });
            }

            if (checkbox) {
                checkbox.addEventListener('change', function () {
                    handleLayerToggle(layerId, checkbox.checked, card, body);
                });
            }
        });

        document.querySelectorAll('.range-slider').forEach(function (slider) {
            slider.addEventListener('input', function () {
                var layerId = slider.dataset.layer;
                var pct     = parseInt(slider.value, 10);
                var output  = document.getElementById('opacity-output-' + layerId);
                if (output) output.textContent = pct + '%';
                applyLayerOpacity(layerId, pct / 100);
            });
        });
    }

    function toggleCardExpand(card, body) {
        if (!body) return;
        var collapsed = body.classList.contains('collapsed');
        body.classList.toggle('collapsed', !collapsed);
        card.classList.toggle('expanded', collapsed);
    }

    // ─── Toolbar ───────────────────────────────────────────────────────────────
    function bindToolbarEvents() {
        var btnFit = document.getElementById('btn-fit-vietnam');
        if (btnFit) {
            btnFit.addEventListener('click', function () {
                state.map.fitBounds(VIETNAM_BOUNDS, { padding: [20, 20] });
            });
        }

        var btnRefresh = document.getElementById('btn-refresh-layers');
        if (btnRefresh) {
            btnRefresh.addEventListener('click', function () {
                refreshAllActiveLayers(true);
            });
        }

        var btnLabels = document.getElementById('btn-toggle-labels');
        if (btnLabels) {
            btnLabels.addEventListener('click', function () {
                state.labelsVisible = !state.labelsVisible;
                btnLabels.classList.toggle('active', state.labelsVisible);
                Object.keys(state.markerGroups).forEach(function (id) {
                    var group = state.markerGroups[id];
                    if (!group) return;
                    group.eachLayer(function (m) {
                        if (state.labelsVisible) {
                            m.openTooltip && m.openTooltip();
                        } else {
                            m.closeTooltip && m.closeTooltip();
                        }
                    });
                });
            });
        }

        var btnCloseLegend = document.getElementById('btn-close-legend');
        if (btnCloseLegend) {
            btnCloseLegend.addEventListener('click', function () {
                var legend = document.getElementById('map-legend');
                if (legend) legend.style.display = 'none';
            });
        }
    }

    // ─── Basemap ───────────────────────────────────────────────────────────────
    function bindBasemapEvents() {
        document.querySelectorAll('input[name="basemap"]').forEach(function (radio) {
            radio.addEventListener('change', function () {
                if (!state.baseTile) return;
                var key = this.value;
                state.baseTile.setUrl(BASEMAP_URLS[key] || BASEMAP_URLS.osm);
                state.baseTile.setAttribution(BASEMAP_ATTR[key] || '');
            });
        });
    }

    // ─── Map mouse events ──────────────────────────────────────────────────────
    function bindMapEvents() {
        var coordsEl = document.getElementById('infobar-coords');
        if (!coordsEl) return;

        state.map.on('mousemove', function (e) {
            coordsEl.textContent =
                'Lat: ' + e.latlng.lat.toFixed(5) + ',  Lng: ' + e.latlng.lng.toFixed(5);
        });

        state.map.on('mouseout', function () {
            coordsEl.textContent = 'Di chuyển chuột trên bản đồ…';
        });
    }

    // ─── Layer toggle ──────────────────────────────────────────────────────────
    function handleLayerToggle(layerId, enabled, card, body) {
        card.classList.toggle('active', enabled);

        if (enabled) {
            state.activeLayerIds.add(layerId);
            if (body) {
                body.classList.remove('collapsed');
                card.classList.add('expanded');
            }
            activateLayer(layerId);
        } else {
            state.activeLayerIds.delete(layerId);
            deactivateLayer(layerId);
        }

        updateChips();
        updateLegendPanel();
    }

    // ─── Activation / deactivation ─────────────────────────────────────────────
    function loadInitialLayers() {
        Object.values(state.layerConfig).forEach(function (cfg) {
            if (cfg.enabled_by_default) {
                state.activeLayerIds.add(cfg.id);
                activateLayer(cfg.id);
            }
        });
        updateChips();
        updateLegendPanel();
    }

    function activateLayer(layerId) {
        showLoading(true);
        var cfg = state.layerConfig[layerId];
        if (!cfg) { showLoading(false); return; }

        var opSlider = document.getElementById('opacity-' + layerId);
        var opacity  = opSlider ? parseInt(opSlider.value, 10) / 100 : cfg.default_opacity;

        // OWM raster tile overlay (requires API key)
        if (state.apiKey && cfg.tile_url) {
            if (!state.tileLayers[layerId]) {
                var tileUrl = cfg.tile_url + '?appid=' + state.apiKey;
                state.tileLayers[layerId] = L.tileLayer(tileUrl, {
                    opacity:     opacity,
                    maxZoom:     18,
                    tileSize:    256,
                    zIndex:      10,
                    attribution: '&copy; OpenWeatherMap'
                });
            }
            state.tileLayers[layerId].addTo(state.map);
            state.tileLayers[layerId].setOpacity(opacity);
        }

        // Value-point markers (always loaded for numeric labels)
        loadLayerPoints(layerId, opacity);
    }

    function deactivateLayer(layerId) {
        if (state.tileLayers[layerId]) {
            state.map.removeLayer(state.tileLayers[layerId]);
        }
        if (state.markerGroups[layerId]) {
            state.map.removeLayer(state.markerGroups[layerId]);
        }
        clearLayerStats(layerId);
        showLoading(false);
    }

    // ─── Point markers from API ─────────────────────────────────────────────────
    function loadLayerPoints(layerId, opacity) {
        WeatherApi.get('/api/layers/points/', { layer: layerId })
            .then(function (data) {
                if (state.markerGroups[layerId]) {
                    state.map.removeLayer(state.markerGroups[layerId]);
                }

                var cfg    = state.layerConfig[layerId];
                var group  = L.layerGroup();
                var values = data.points.map(function (p) { return p.value; });
                var minVal = Math.min.apply(null, values);
                var maxVal = Math.max.apply(null, values);
                var avgVal = values.reduce(function (s, v) { return s + v; }, 0) / values.length;
                // Radius is smaller when raster tile already fills the area
                var radius = state.apiKey ? 10 : 22;

                data.points.forEach(function (pt) {
                    var color = interpolateLayerColor(cfg, pt.value);

                    var marker = L.circleMarker([pt.lat, pt.lng], {
                        radius:      radius,
                        fillColor:   color,
                        color:       'rgba(255,255,255,0.85)',
                        weight:      1.5,
                        opacity:     1,
                        fillOpacity: state.apiKey ? 0.88 : opacity
                    });

                    var valDisplay = formatValue(pt.value, cfg);

                    marker.bindTooltip(valDisplay, {
                        permanent:  true,
                        direction:  'center',
                        className:  'layer-value-tooltip'
                    });

                    marker.bindPopup(buildPointPopup(pt, cfg, color), {
                        maxWidth:  220,
                        className: 'layer-popup'
                    });

                    group.addLayer(marker);
                });

                group.addTo(state.map);
                state.markerGroups[layerId] = group;

                updateLayerStats(layerId, minVal, maxVal, avgVal, cfg);
            })
            .catch(function (err) {
                console.error('[layers] Failed to load points for ' + layerId + ':', err);
            })
            .finally(function () {
                showLoading(false);
            });
    }

    // ─── Colour helpers ────────────────────────────────────────────────────────
    function interpolateLayerColor(cfg, value) {
        var range = cfg.range;
        var t     = Math.max(0, Math.min(1, (value - range.min) / (range.max - range.min)));
        var cols  = cfg.colors;
        if (t <= 0.5) return lerpHex(cols[0], cols[1], t * 2);
        return lerpHex(cols[1], cols[2], (t - 0.5) * 2);
    }

    function lerpHex(hex1, hex2, t) {
        var a  = hexToRgb(hex1);
        var b  = hexToRgb(hex2);
        var r  = Math.round(a.r + (b.r - a.r) * t);
        var g  = Math.round(a.g + (b.g - a.g) * t);
        var bl = Math.round(a.b + (b.b - a.b) * t);
        return 'rgb(' + r + ',' + g + ',' + bl + ')';
    }

    function hexToRgb(hex) {
        var m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return m
            ? { r: parseInt(m[1], 16), g: parseInt(m[2], 16), b: parseInt(m[3], 16) }
            : { r: 128, g: 128, b: 128 };
    }

    // ─── Formatting ────────────────────────────────────────────────────────────
    function formatValue(value, cfg) {
        if (value === null || value === undefined) return '—';
        return Number(value).toFixed(1) + ' ' + cfg.unit;
    }

    // ─── Popup HTML ────────────────────────────────────────────────────────────
    function buildPointPopup(pt, cfg, dotColor) {
        return '<div class="gis-popup">' +
            '<div class="popup-location-name">' +
                '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;' +
                      'background:' + dotColor + ';margin-right:5px;vertical-align:middle;"></span>' +
                pt.name +
            '</div>' +
            '<div class="popup-grid">' +
                '<div class="popup-field">' +
                    '<span class="popup-field-label">' + cfg.name + '</span>' +
                    '<span class="popup-field-value">' + formatValue(pt.value, cfg) + '</span>' +
                '</div>' +
                '<div class="popup-field">' +
                    '<span class="popup-field-label">Tọa độ</span>' +
                    '<span class="popup-field-value" style="font-size:0.73rem">' +
                        pt.lat.toFixed(3) + ', ' + pt.lng.toFixed(3) +
                    '</span>' +
                '</div>' +
            '</div>' +
        '</div>';
    }

    // ─── Opacity ───────────────────────────────────────────────────────────────
    function applyLayerOpacity(layerId, opacity) {
        if (state.tileLayers[layerId]) {
            state.tileLayers[layerId].setOpacity(opacity);
        }
        if (state.markerGroups[layerId]) {
            state.markerGroups[layerId].eachLayer(function (m) {
                if (m.setStyle) m.setStyle({ fillOpacity: state.apiKey ? 0.88 : opacity });
            });
        }
    }

    // ─── Layer stats ───────────────────────────────────────────────────────────
    function updateLayerStats(layerId, min, max, avg, cfg) {
        var setEl = function (id, val) {
            var el = document.getElementById(id);
            if (el) el.textContent = val;
        };
        setEl('stat-min-' + layerId, formatValue(min, cfg));
        setEl('stat-avg-' + layerId, formatValue(avg, cfg));
        setEl('stat-max-' + layerId, formatValue(max, cfg));
    }

    function clearLayerStats(layerId) {
        ['min', 'avg', 'max'].forEach(function (k) {
            var el = document.getElementById('stat-' + k + '-' + layerId);
            if (el) el.textContent = '—';
        });
    }

    // ─── Chip bar ──────────────────────────────────────────────────────────────
    function updateChips() {
        var container = document.getElementById('layer-chips');
        if (!container) return;

        if (state.activeLayerIds.size === 0) {
            container.innerHTML = '';
            return;
        }

        var html = '';
        state.activeLayerIds.forEach(function (id) {
            var cfg = state.layerConfig[id];
            if (!cfg) return;
            html += '<span class="layer-chip" data-layer="' + id + '" title="Nhấn để tắt lớp">' +
                '<span class="chip-dot" style="background:linear-gradient(135deg,' + cfg.colors[0] + ',' + cfg.colors[2] + ')"></span>' +
                cfg.name +
            '</span>';
        });
        container.innerHTML = html;

        container.querySelectorAll('.layer-chip').forEach(function (chip) {
            chip.addEventListener('click', function () {
                var id       = chip.dataset.layer;
                var checkbox = document.getElementById('toggle-' + id);
                if (checkbox) {
                    checkbox.checked = false;
                    checkbox.dispatchEvent(new Event('change'));
                }
            });
        });
    }

    // ─── Legend panel ──────────────────────────────────────────────────────────
    function updateLegendPanel() {
        var body  = document.getElementById('legend-body');
        var panel = document.getElementById('map-legend');
        if (!body || !panel) return;

        panel.style.display = '';

        if (state.activeLayerIds.size === 0) {
            body.innerHTML = '<p class="legend-empty">Không có lớp nào đang bật</p>';
            return;
        }

        var html = '';
        state.activeLayerIds.forEach(function (id) {
            var cfg = state.layerConfig[id];
            if (!cfg) return;
            var ticks = (cfg.legend_labels || []).join('</span><span>');
            html += '<div class="legend-row">' +
                '<div class="legend-row-header">' +
                    '<span class="legend-row-title">' + cfg.name + '</span>' +
                    '<small class="legend-row-unit">' + cfg.unit + '</small>' +
                '</div>' +
                '<div class="legend-row-gradient" style="background:linear-gradient(to right,' +
                    cfg.colors[0] + ',' + cfg.colors[1] + ',' + cfg.colors[2] + ')"></div>' +
                '<div class="legend-row-ticks"><span>' + ticks + '</span></div>' +
            '</div>';
        });
        body.innerHTML = html;
    }

    // ─── Refresh ───────────────────────────────────────────────────────────────
    function refreshAllActiveLayers(forceUI) {
        if (forceUI) showLoading(true);
        state.activeLayerIds.forEach(function (id) {
            var opSlider = document.getElementById('opacity-' + id);
            var opacity  = opSlider
                ? parseInt(opSlider.value, 10) / 100
                : (state.layerConfig[id] ? state.layerConfig[id].default_opacity : 0.7);
            loadLayerPoints(id, opacity);
        });
        updateDataSourceBadge(true);
    }

    function scheduleRefresh() {
        if (state.refreshTimer) clearInterval(state.refreshTimer);
        state.refreshTimer = setInterval(function () {
            refreshAllActiveLayers(false);
        }, REFRESH_MS);
    }

    // ─── Data source badge ─────────────────────────────────────────────────────
    function updateDataSourceBadge(loaded) {
        var badge = document.getElementById('data-source-badge');
        if (!badge) return;

        if (!loaded) {
            badge.textContent = 'Đang tải…';
            badge.classList.add('loading');
            return;
        }

        badge.classList.remove('loading');
        badge.textContent = state.apiKey ? 'OpenWeatherMap Live' : 'Dữ liệu ước tính';
    }

    // ─── Loading ───────────────────────────────────────────────────────────────
    function showLoading(visible) {
        var el = document.getElementById('map-loading');
        if (el) el.classList.toggle('hidden', !visible);
    }

    // ─── Entry point ───────────────────────────────────────────────────────────
    document.addEventListener('DOMContentLoaded', function () {
        updateDataSourceBadge(false);
        init();
        updateDataSourceBadge(true);
    });

})();
