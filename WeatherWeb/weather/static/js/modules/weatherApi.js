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
     * Make a POST request and return binary blob response
     * @param {string} url - API endpoint
     * @param {Object} data - Request body
     * @returns {Promise<Blob>} Response blob
     */
    async function postBlob(url, data = {}) {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken(),
                'Accept': '*/*'
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ error: 'Request failed' }));
            throw new Error(error.error || 'Request failed');
        }

        return response.blob();
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
     * Compare multiple locations
     * @param {Array} locationIds - Array of location IDs
     * @returns {Promise} Comparison data
     */
    async function compareLocations(locationIds) {
        return post('/api/compare/', { location_ids: locationIds });
    }

    /**
     * Compare current API result and AI prediction
     * @param {Object} payload - {location_id}|{latitude,longitude} + horizon_hours
     * @returns {Promise} Prediction comparison payload
     */
    async function getPredictionComparison(payload) {
        return post('/api/predict/', payload);
    }

    async function exportPredictionCsv(payload) {
        return postBlob('/predict/export/csv/', payload);
    }

    async function exportPredictionImage(payload) {
        return postBlob('/predict/export/image/', payload);
    }

    // Public API
    return {
        get,
        post,
        del,
        postBlob,
        getCSRFToken,
        getCurrentWeather,
        saveLocation,
        deleteLocation,
        compareLocations,
        getPredictionComparison,
        exportPredictionCsv,
        exportPredictionImage
    };
})();
