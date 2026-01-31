/**
 * GIS Map Controller Module
 * Tuân thủ quy tắc: Không biến toàn cục, logic module hóa, không inline JS.
 */
(function() {
    'use strict';

    const CONFIG = {
        MAP_INITIAL_VIEW: [21.0285, 105.8542], // Mặc định tại Hà Nội
        MAP_INITIAL_ZOOM: 6,
        API_ENDPOINTS: {
            SAVE_LOCATION: '', // Tự động nhận URL hiện tại hoặc chỉ định cụ thể
            GET_WEATHER: '/weather/mock-weather/' // Use mock endpoint
        },
        SELECTORS: {
            MAP_ID: 'map',
            LOCATION_LIST_ID: 'location-list'
        }
    };

    const mapController = {
        map: null,
        markers: new Map(), // Sử dụng Map object để quản lý marker hiệu quả hơn

        init: function() {
            this.initMap();
            this.loadInitialData();
            this.bindEvents();
        },

        initMap: function() {
            this.map = L.map(CONFIG.SELECTORS.MAP_ID).setView(CONFIG.MAP_INITIAL_VIEW, CONFIG.MAP_INITIAL_ZOOM);
            
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                maxZoom: 19,
                attribution: '© OpenStreetMap contributors'
            }).addTo(this.map);
        },

        loadInitialData: function() {
            // Quy tắc 4.2: Sử dụng dữ liệu được truyền an toàn qua json_script
            const initialData = window.initialLocations || [];
            initialData.forEach(loc => this.addMarker(loc));
        },

        bindEvents: function() {
            // Quy tắc 3: Click bất kỳ đâu trên bản đồ đều phải hợp lệ
            this.map.on('click', this.handleMapClick.bind(this));
            
            // Xử lý sự kiện Sidebar
            const listElement = document.getElementById(CONFIG.SELECTORS.LOCATION_LIST_ID);
            if (listElement) {
                listElement.addEventListener('click', this.handleSidebarClick.bind(this));
            }
        },

        addMarker: function(loc) {
            const marker = L.marker([loc.latitude, loc.longitude]).addTo(this.map);
            
            // Quy tắc 3: Thời tiết được lấy on-demand, không lưu trong DB
            marker.on('click', () => this.fetchAndShowWeather(loc, marker));
            
            this.markers.set(String(loc.id), marker);
            return marker;
        },

        handleMapClick: function(e) {
            const { lat, lng } = e.latlng;
            // Show popup with mock weather data
            const popupContent = this.mockWeatherPopup(lat, lng);
            L.popup()
                .setLatLng([lat, lng])
                .setContent(popupContent)
                .openOn(this.map);
        },

        mockWeatherPopup: function(lat, lng) {
            // Pseudo CK mock data
            return `
                <strong>Weather at (${lat.toFixed(4)}, ${lng.toFixed(4)})</strong><br>
                Temp: 25.2°C<br>
                Rain: 0 mm<br>
                Wind: 2.8 m/s<br>
                Desc: Clear sky
            `;
        },

        fetchAndShowWeather: async function(loc, marker) {
            marker.bindPopup("Fetching weather data...").openPopup();

            try {
                const url = `${CONFIG.API_ENDPOINTS.GET_WEATHER}?lat=${loc.latitude}&lng=${loc.longitude}`;
                const response = await fetch(url);
                
                if (!response.ok) throw new Error();
                
                const weatherData = await response.json();
                marker.setPopupContent(this.createPopupHtml(loc, weatherData));
                
            } catch (err) {
                marker.setPopupContent(`<b>${loc.name || 'Point'}</b><br>Weather service unavailable.`);
            }
        },

        createPopupHtml: function(loc, weather) {
            // Quy tắc 4.3: Professional UI, functional clarity
            return `
                <div class="gis-popup">
                    <strong>${loc.name || 'Selected Location'}</strong><hr>
                    <small>Lat: ${loc.latitude.toFixed(4)}, Lng: ${loc.longitude.toFixed(4)}</small>
                    <div class="weather-info" style="margin-top: 8px;">
                        <div>Temp: <b>${weather.temperature}°C</b></div>
                        <div>Desc: ${weather.description}</div>
                        <div>Wind: ${weather.wind_speed} m/s</div>
                    </div>
                </div>
            `;
        },

        updateSidebar: function(loc) {
            const ul = document.getElementById(CONFIG.SELECTORS.LOCATION_LIST_ID);
            if (!ul) return;

            const li = document.createElement('li');
            li.dataset.id = loc.id;
            li.className = 'location-item';
            li.innerHTML = `
                ${loc.name || '(Unnamed Point)'}<br>
                <span class="coords">(${loc.latitude.toFixed(3)}, ${loc.longitude.toFixed(3)})</span>
            `;
            ul.prepend(li);
        },

        handleSidebarClick: function(e) {
            const li = e.target.closest('li[data-id]');
            if (li) {
                const marker = this.markers.get(String(li.dataset.id));
                if (marker) {
                    this.map.panTo(marker.getLatLng());
                    marker.fire('click');
                }
            }
        },

        getCsrfToken: function() {
            return document.cookie.split('; ')
                .find(row => row.startsWith('csrftoken='))
                ?.split('=')[1] || '';
        }
    };

    // Khởi tạo khi DOM sẵn sàng
    document.addEventListener('DOMContentLoaded', () => mapController.init());

    // Xuất ra window để các module khác có thể tương tác nếu cần (Extensibility)
    window.GISMap = mapController;

})();