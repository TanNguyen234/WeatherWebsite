/**
 * filepath: d:\Projects\WeatherWebsite\WeatherWeb\weather\static\js\modules\mapCore.js
 * Core map functionality - reusable across all pages
 * GIS Pattern: Single map instance with configurable behaviors
 */

const MapCore = (function () {
    'use strict';

    const DEFAULT_CENTER = [21.0285, 105.8542]; // Hanoi
    const DEFAULT_ZOOM = 6;
    const TILE_URL = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
    const TILE_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';

    /**
     * Initialize a Leaflet map
     * @param {string} containerId - DOM element ID
     * @param {Object} options - Map options
     * @returns {L.Map} Leaflet map instance
     */
    function initMap(containerId, options = {}) {
        const center = options.center || DEFAULT_CENTER;
        const zoom = options.zoom || DEFAULT_ZOOM;

        const map = L.map(containerId, {
            center: center,
            zoom: zoom,
            zoomControl: options.zoomControl !== false
        });

        L.tileLayer(TILE_URL, {
            attribution: TILE_ATTRIBUTION,
            maxZoom: 19
        }).addTo(map);

        return map;
    }

    /**
     * Setup click handler for map
     * @param {L.Map} map - Leaflet map instance
     * @param {Function} onClick - Callback function(lat, lng, event)
     */
    function setupMapClick(map, onClick) {
        map.on('click', function (e) {
            const lat = e.latlng.lat;
            const lng = e.latlng.lng;
            onClick(lat, lng, e);
        });
    }

    /**
     * Add a marker to the map
     * @param {L.Map} map - Leaflet map instance
     * @param {number} lat - Latitude
     * @param {number} lng - Longitude
     * @param {Object} options - Marker options
     * @returns {L.Marker} Marker instance
     */
    function addMarker(map, lat, lng, options = {}) {
        const marker = L.marker([lat, lng], options).addTo(map);
        return marker;
    }

    /**
     * Add marker with popup
     * @param {L.Map} map - Leaflet map instance
     * @param {number} lat - Latitude
     * @param {number} lng - Longitude
     * @param {string} popupContent - HTML content for popup
     * @param {Object} options - Marker options
     * @returns {L.Marker} Marker instance
     */
    function addMarkerWithPopup(map, lat, lng, popupContent, options = {}) {
        const marker = addMarker(map, lat, lng, options);
        marker.bindPopup(popupContent, { maxWidth: 300 });
        return marker;
    }

    /**
     * Create a marker group for managing multiple markers
     * @param {L.Map} map - Leaflet map instance
     * @returns {L.LayerGroup} Layer group instance
     */
    function createMarkerGroup(map) {
        const group = L.layerGroup().addTo(map);
        return group;
    }

    /**
     * Clear all markers from a group
     * @param {L.LayerGroup} group - Layer group
     */
    function clearMarkerGroup(group) {
        group.clearLayers();
    }

    /**
     * Draw a polyline (route) on the map
     * @param {L.Map} map - Leaflet map instance
     * @param {Array} points - Array of [lat, lng] pairs
     * @param {Object} options - Polyline options
     * @returns {L.Polyline} Polyline instance
     */
    function drawRoute(map, points, options = {}) {
        const defaultOptions = {
            color: '#2563eb',
            weight: 4,
            opacity: 0.8
        };
        const polyline = L.polyline(points, { ...defaultOptions, ...options }).addTo(map);
        return polyline;
    }

    /**
     * Draw a circle (area) on the map
     * @param {L.Map} map - Leaflet map instance
     * @param {number} lat - Center latitude
     * @param {number} lng - Center longitude
     * @param {number} radiusKm - Radius in kilometers
     * @param {Object} options - Circle options
     * @returns {L.Circle} Circle instance
     */
    function drawCircle(map, lat, lng, radiusKm, options = {}) {
        const defaultOptions = {
            color: '#2563eb',
            fillColor: '#2563eb',
            fillOpacity: 0.2,
            weight: 2
        };
        const circle = L.circle([lat, lng], {
            radius: radiusKm * 1000, // Convert km to meters
            ...defaultOptions,
            ...options
        }).addTo(map);
        return circle;
    }

    /**
     * Fit map bounds to show all markers
     * @param {L.Map} map - Leaflet map instance
     * @param {Array} markers - Array of markers or [lat, lng] pairs
     */
    function fitBounds(map, markers) {
        if (markers.length === 0) return;

        const bounds = L.latLngBounds(markers.map(m => {
            if (m.getLatLng) return m.getLatLng();
            return L.latLng(m[0], m[1]);
        }));

        map.fitBounds(bounds, { padding: [50, 50] });
    }

    /**
     * Pan map to specific location
     * @param {L.Map} map - Leaflet map instance
     * @param {number} lat - Latitude
     * @param {number} lng - Longitude
     * @param {number} zoom - Optional zoom level
     */
    function panTo(map, lat, lng, zoom) {
        if (zoom) {
            map.setView([lat, lng], zoom);
        } else {
            map.panTo([lat, lng]);
        }
    }

    /**
     * Create custom icon
     * @param {Object} options - Icon options
     * @returns {L.Icon} Custom icon
     */
    function createIcon(options = {}) {
        return L.icon({
            iconUrl: options.iconUrl || 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
            iconSize: options.iconSize || [25, 41],
            iconAnchor: options.iconAnchor || [12, 41],
            popupAnchor: options.popupAnchor || [1, -34]
        });
    }

    // Public API
    return {
        initMap,
        setupMapClick,
        addMarker,
        addMarkerWithPopup,
        createMarkerGroup,
        clearMarkerGroup,
        drawRoute,
        drawCircle,
        fitBounds,
        panTo,
        createIcon,
        DEFAULT_CENTER,
        DEFAULT_ZOOM
    };
})();
