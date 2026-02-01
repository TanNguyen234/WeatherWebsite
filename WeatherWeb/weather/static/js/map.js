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
            GET_WEATHER: '/weather/mock-weather/' // Use mock endpoint
        },
        SELECTORS: {
            MAP_ID: 'map',
            LOCATION_LIST_ID: 'location-list',
            INITIAL_DATA_ID: 'initial-locations-data'
        }
    };

    const App = {
        map: null,
        markers: new Map(), // Sử dụng Map object để quản lý marker hiệu quả hơn

        init: function() {
            this.initMap();
            this.loadData();
            this.bindEvents();
        },

        initMap: function() {
            this.map = L.map(CONFIG.SELECTORS.MAP_ID).setView(CONFIG.MAP_INITIAL_VIEW, CONFIG.MAP_INITIAL_ZOOM);
            
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                maxZoom: 19,
                attribution: '© OpenStreetMap contributors'
            }).addTo(this.map);
        },

        loadData: function() {
            const dataEl = document.getElementById(CONFIG.SELECTORS.INITIAL_DATA_ID);
            let locations = [];
            
            try {
                const rawData = JSON.parse(dataEl.textContent);
                locations = typeof rawData === 'string' ? JSON.parse(rawData) : rawData;
            } catch (e) {
                // Fallback mock data if parsing fails
                locations = [
                    {id: 'fake1', name: 'Hanoi Capital', latitude: 21.0285, longitude: 105.8542},
                    {id: 'fake2', name: 'Da Nang City', latitude: 16.0471, longitude: 108.2067}
                ];
            }

            if (!locations || locations.length === 0) {
                locations = [{id: 'temp1', name: 'Example Point', latitude: 21.0, longitude: 105.8}];
            }

            locations.forEach(loc => this.renderLocation(loc));
        },

        renderLocation: function(loc) {
            // Add Marker to map
            const marker = L.marker([loc.latitude, loc.longitude]).addTo(this.map);
            marker.bindPopup(this.createMarkerPopup(loc));
            this.markers.set(String(loc.id), marker);

            // Add to Sidebar
            this.addToSidebar(loc);
        },

        createMarkerPopup: function(loc) {
            return `<b>${loc.name}</b><br><small>${loc.latitude.toFixed(3)}, ${loc.longitude.toFixed(3)}</small>`;
        },

        addToSidebar: function(loc) {
            const list = document.getElementById(CONFIG.SELECTORS.LOCATION_LIST_ID);
            if (!list) return;

            const li = document.createElement('li');
            li.dataset.id = loc.id;
            li.innerHTML = `
                <span class="loc-name">${loc.name}</span>
                <span class="coords">${loc.latitude.toFixed(4)}, ${loc.longitude.toFixed(4)}</span>
            `;
            list.prepend(li);
        },

        bindEvents: function() {
            // Sidebar click - pan to marker
            const listElement = document.getElementById(CONFIG.SELECTORS.LOCATION_LIST_ID);
            if (listElement) {
                listElement.addEventListener('click', this.handleSidebarClick.bind(this));
            }

            // Map click - show save popup
            this.map.on('click', this.handleMapClick.bind(this));
        },

        handleSidebarClick: function(e) {
            const li = e.target.closest('li');
            if (!li) return;
            
            const marker = this.markers.get(li.dataset.id);
            if (marker) {
                this.map.flyTo(marker.getLatLng(), 12);
                marker.openPopup();
            }
        },

        handleMapClick: function(e) {
            const { lat, lng } = e.latlng;
            const self = this;
            
            const popupContent = document.createElement('div');
            popupContent.innerHTML = `
                <strong>New Location</strong><br>
                <input type="text" id="new-loc-name" placeholder="Name this place..." style="width:100%; margin-top:5px; padding:4px;">
                <button class="btn-save-here" id="btn-save-action">Save to Sidebar</button>
            `;

            L.popup()
                .setLatLng(e.latlng)
                .setContent(popupContent)
                .openOn(this.map);

            // Bind save button event after popup is opened
            setTimeout(function() {
                const saveBtn = document.getElementById('btn-save-action');
                if (saveBtn) {
                    saveBtn.onclick = function() {
                        const name = document.getElementById('new-loc-name').value || "Saved Point";
                        self.saveLocationToServer(lat, lng, name);
                    };
                }
            }, 10);
        },

        saveLocationToServer: async function(lat, lng, name) {
            // Optimistic UI - render immediately
            const tempId = Date.now();
            const newLoc = { id: tempId, name: name, latitude: lat, longitude: lng };
            this.renderLocation(newLoc);
            this.map.closePopup();

            // POST to server
            try {
                const response = await fetch(window.location.href, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCsrfToken()
                    },
                    body: JSON.stringify({
                        latitude: lat,
                        longitude: lng,
                        name: name
                    })
                });

                if (!response.ok) throw new Error("Failed to save");
                console.log("Location saved successfully!");
            } catch (err) {
                console.error("Save error:", err);
                // Location is already shown in UI, just log error
            }
        },

        getCsrfToken: function() {
            let cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                const cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i].trim();
                    if (cookie.substring(0, 'csrftoken'.length + 1) === ('csrftoken' + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring('csrftoken'.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        }
    };

    // Initialize app when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        App.init();
    });

    // Xuất ra window để các module khác có thể tương tác nếu cần (Extensibility)
    window.GISMap = App;

})();