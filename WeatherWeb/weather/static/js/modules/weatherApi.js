/**
 * filepath: d:\Projects\WeatherWebsite\WeatherWeb\weather\static\js\modules\weatherApi.js
 * Weather API communication module
 * Handles all AJAX requests to backend
 */

const WeatherApi = (function () {
    'use strict';

    /**
     * Get CSRF token from cookie
     * @returns {string} CSRF token
     */
    function getCSRFToken() {
        const name = 'csrftoken';
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [key, value] = cookie.trim().split('=');
            if (key === name) return value;
        }
        return '';
    }

    /**
     * Make a GET request
     * @param {string} url - API endpoint
     * @param {Object} params - Query parameters
     * @returns {Promise} Response data
     */
    async function get(url, params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const fullUrl = queryString ? `${url}?${queryString}` : url;

        const response = await fetch(fullUrl, {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            }
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ error: 'Request failed' }));
            throw new Error(error.error || 'Request failed');
        }

        return response.json();
    }

    /**
     * Make a POST request
     * @param {string} url - API endpoint
     * @param {Object} data - Request body
     * @returns {Promise} Response data
     */
    async function post(url, data = {}) {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken(),
                'Accept': 'application/json'
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ error: 'Request failed' }));
            throw new Error(error.error || 'Request failed');
        }

        return response.json();
    }

    /**
     * Make a DELETE request
     * @param {string} url - API endpoint
     * @returns {Promise} Response data
     */
    async function del(url) {
        const response = await fetch(url, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCSRFToken(),
                'Accept': 'application/json'
            }
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ error: 'Request failed' }));
            throw new Error(error.error || 'Request failed');
        }

        return response.json();
    }

    // ========================================
    // Weather-specific API calls
    // ========================================

    /**
     * Get current weather for coordinates
     * @param {number} lat - Latitude
     * @param {number} lng - Longitude
     * @returns {Promise} Weather data
     */
    async function getCurrentWeather(lat, lng) {
        return get('/api/weather/', { lat, lng });
    }

    /**
     * Save a new location
     * @param {number} lat - Latitude
     * @param {number} lng - Longitude
     * @param {string} name - Location name
     * @returns {Promise} Saved location data
     */
    async function saveLocation(lat, lng, name = null) {
        return post('/api/locations/', { latitude: lat, longitude: lng, name });
    }

    /**
     * Delete a location
     * @param {number} locationId - Location ID
     * @returns {Promise} Response
     */
    async function deleteLocation(locationId) {
        return del(`/api/locations/${locationId}/`);
    }

    /**
     * Get forecast data
     * @param {number} locationId - Location ID
     * @param {string} mode - 'hourly' or 'daily'
     * @returns {Promise} Forecast data
     */
    async function getForecast(locationId, mode = 'hourly') {
        return post('/api/forecast/', { location_id: locationId, mode });
    }

    /**
     * Get forecast by coordinates
     * @param {number} lat - Latitude
     * @param {number} lng - Longitude
     * @param {string} mode - 'hourly' or 'daily'
     * @returns {Promise} Forecast data
     */
    async function getForecastByCoords(lat, lng, mode = 'hourly') {
        return post('/api/forecast/', { latitude: lat, longitude: lng, mode });
    }

    /**
     * Compare multiple locations
     * @param {Array} locationIds - Array of location IDs
     * @returns {Promise} Comparison data
     */
    async function compareLocations(locationIds) {
        return post('/api/compare/', { location_ids: locationIds });
    }

    /**
     * Get route weather
     * @param {number} startId - Start location ID
     * @param {number} endId - End location ID
     * @param {number} pointCount - Number of interpolation points
     * @returns {Promise} Route weather data
     */
    async function getRouteWeather(startId, endId, pointCount = 5) {
        return post('/api/route/', { start_id: startId, end_id: endId, point_count: pointCount });
    }

    /**
     * Get location groups
     * @returns {Promise} Groups data
     */
    async function getGroups() {
        return get('/api/groups/');
    }

    /**
     * Add location to group
     * @param {number} groupId - Group ID
     * @param {number} locationId - Location ID
     * @returns {Promise} Response
     */
    async function addToGroup(groupId, locationId) {
        return post('/api/groups/add/', { group_id: groupId, location_id: locationId });
    }

    // Public API
    return {
        get,
        post,
        del,
        getCSRFToken,
        getCurrentWeather,
        saveLocation,
        deleteLocation,
        getForecast,
        getForecastByCoords,
        compareLocations,
        getRouteWeather,
        getGroups,
        addToGroup
    };
})();
