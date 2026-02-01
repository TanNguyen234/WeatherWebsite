/**
 * filepath: d:\Projects\WeatherWebsite\WeatherWeb\weather\static\js\modules\uiHelpers.js
 * UI Helper functions - reusable across all pages
 */

const UIHelpers = (function () {
    'use strict';

    /**
     * Format coordinates for display
     * @param {number} lat - Latitude
     * @param {number} lng - Longitude
     * @param {number} decimals - Decimal places
     * @returns {string} Formatted coordinates
     */
    function formatCoords(lat, lng, decimals = 4) {
        return `${lat.toFixed(decimals)}, ${lng.toFixed(decimals)}`;
    }

    /**
     * Format temperature
     * @param {number} temp - Temperature value
     * @param {string} unit - 'C' or 'F'
     * @returns {string} Formatted temperature
     */
    function formatTemp(temp, unit = 'C') {
        return `${temp.toFixed(1)}°${unit}`;
    }

    /**
     * Format wind speed
     * @param {number} speed - Wind speed
     * @param {string} unit - 'm/s' or 'km/h'
     * @returns {string} Formatted wind speed
     */
    function formatWind(speed, unit = 'm/s') {
        return `${speed.toFixed(1)} ${unit}`;
    }

    /**
     * Format humidity
     * @param {number} humidity - Humidity percentage
     * @returns {string} Formatted humidity
     */
    function formatHumidity(humidity) {
        return `${humidity}%`;
    }

    /**
     * Create weather popup HTML content
     * @param {Object} data - Weather data
     * @param {Object} options - Display options
     * @returns {string} HTML content
     */
    function createWeatherPopupContent(data, options = {}) {
        const { lat, lng, weather, name } = data;
        const showActions = options.showActions !== false;
        const isAuthenticated = options.isAuthenticated !== false;

        let html = `<div class="gis-popup">`;
        
        // Header
        html += `<div class="popup-header">${name || 'Vị trí đã chọn'}</div>`;
        html += `<div class="popup-coords">${formatCoords(lat, lng)}</div>`;
        
        // Weather info
        if (weather) {
            html += `<div class="weather-info">`;
            html += `<p>Nhiệt độ: <strong>${formatTemp(weather.temperature)}</strong></p>`;
            html += `<p>Độ ẩm: <strong>${formatHumidity(weather.humidity)}</strong></p>`;
            html += `<p>Gió: <strong>${formatWind(weather.wind_speed)}</strong></p>`;
            html += `<p>Điều kiện: ${weather.description}</p>`;
            html += `</div>`;
        }

        // Action buttons
        if (showActions && isAuthenticated) {
            html += `<div class="popup-actions">`;
            html += `<button class="btn-popup" data-action="save" data-lat="${lat}" data-lng="${lng}">Lưu vị trí</button>`;
            html += `<button class="btn-popup btn-outline" data-action="compare" data-lat="${lat}" data-lng="${lng}">Thêm vào so sánh</button>`;
            html += `<button class="btn-popup btn-outline" data-action="route" data-lat="${lat}" data-lng="${lng}">Dùng cho tuyến đường</button>`;
            html += `</div>`;
        }

        html += `</div>`;
        return html;
    }

    /**
     * Create location list item HTML
     * @param {Object} location - Location data
     * @param {Object} options - Display options
     * @returns {string} HTML content
     */
    function createLocationListItem(location, options = {}) {
        const showDelete = options.showDelete !== false;
        const showSelect = options.showSelect || false;
        
        let html = `<li class="location-item" data-id="${location.id}" data-lat="${location.latitude}" data-lng="${location.longitude}">`;
        
        if (showSelect) {
            html += `<input type="checkbox" class="location-checkbox" data-id="${location.id}">`;
        }
        
        html += `<span class="location-name">${location.name || 'Chưa đặt tên'}</span>`;
        html += `<span class="location-coords">${formatCoords(location.latitude, location.longitude)}</span>`;
        
        if (showDelete) {
            html += `<div class="location-actions">`;
            html += `<button class="btn btn-sm btn-danger" data-action="delete" data-id="${location.id}">Xóa</button>`;
            html += `</div>`;
        }
        
        html += `</li>`;
        return html;
    }

    /**
     * Render location list
     * @param {HTMLElement} container - Container element
     * @param {Array} locations - Array of location objects
     * @param {Object} options - Render options
     */
    function renderLocationList(container, locations, options = {}) {
        if (locations.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">Vị trí</div>
                    <p>Chưa có vị trí nào được lưu.<br>Click vào bản đồ để thêm vị trí mới!</p>
                </div>
            `;
            return;
        }

        const html = locations.map(loc => createLocationListItem(loc, options)).join('');
        container.innerHTML = html;
    }

    /**
     * Show loading state
     * @param {HTMLElement} container - Container element
     */
    function showLoading(container) {
        container.innerHTML = `
            <div class="loading">
                <div class="spinner"></div>
            </div>
        `;
    }

    /**
     * Show error message
     * @param {HTMLElement} container - Container element
     * @param {string} message - Error message
     */
    function showError(container, message) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">Lỗi</div>
                <p>${message}</p>
            </div>
        `;
    }

    /**
     * Show toast notification
     * @param {string} message - Message to show
     * @param {string} type - 'success', 'error', 'info'
     */
    function showToast(message, type = 'info') {
        // Remove existing toast
        const existingToast = document.querySelector('.toast-notification');
        if (existingToast) {
            existingToast.remove();
        }

        const toast = document.createElement('div');
        toast.className = `toast-notification toast-${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            padding: 12px 24px;
            background: ${type === 'error' ? '#ef4444' : type === 'success' ? '#10b981' : '#2563eb'};
            color: white;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 9999;
            animation: slideIn 0.3s ease;
        `;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    /**
     * Parse initial data from script tag
     * @param {string} scriptId - ID of script tag containing JSON
     * @returns {*} Parsed data or null
     */
    function parseInitialData(scriptId) {
        const script = document.getElementById(scriptId);
        if (!script) return null;

        try {
            return JSON.parse(script.textContent);
        } catch (e) {
            console.error('Không thể parse dữ liệu ban đầu:', e);
            return null;
        }
    }

    /**
     * Debounce function
     * @param {Function} func - Function to debounce
     * @param {number} wait - Wait time in ms
     * @returns {Function} Debounced function
     */
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    /**
     * Create dropdown select from locations
     * @param {Array} locations - Array of location objects
     * @param {Object} options - Options
     * @returns {string} HTML select element
     */
    function createLocationSelect(locations, options = {}) {
        const { id, name, placeholder, multiple } = options;
        
        let html = `<select class="form-control" id="${id || ''}" name="${name || ''}" ${multiple ? 'multiple' : ''}>`;
        html += `<option value="">${placeholder || '-- Chọn vị trí --'}</option>`;
        
        locations.forEach(loc => {
            html += `<option value="${loc.id}" data-lat="${loc.latitude}" data-lng="${loc.longitude}">`;
            html += `${loc.name || 'Chưa đặt tên'} (${formatCoords(loc.latitude, loc.longitude, 2)})`;
            html += `</option>`;
        });
        
        html += `</select>`;
        return html;
    }

    // Add CSS for toast animations
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
    `;
    document.head.appendChild(style);

    // Public API
    return {
        formatCoords,
        formatTemp,
        formatWind,
        formatHumidity,
        createWeatherPopupContent,
        createLocationListItem,
        renderLocationList,
        showLoading,
        showError,
        showToast,
        parseInitialData,
        debounce,
        createLocationSelect
    };
})();
