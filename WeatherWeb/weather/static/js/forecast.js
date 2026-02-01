/**
 * Forecast Page Controller Module
 * Handles forecast form submission and table rendering
 * Tuân thủ quy tắc: Không biến toàn cục, logic module hóa, không inline JS.
 */
(function() {
    'use strict';

    const CONFIG = {
        SELECTORS: {
            FORM_ID: 'forecast-form',
            TABLE_WRAP_ID: 'forecast-table-wrap',
            TABLE_BODY: '#forecast-table tbody',
            NO_DATA_ID: 'no-data',
            RANGE_SELECT: 'range'
        }
    };

    // Mock forecast data (structure matches time-based forecast)
    const MOCK_DATA = {
        hour: [
            { time: 'Today 12:00', temp: 25.2, rain: '0mm', wind: '2.8m/s', desc: 'Clear sky' },
            { time: 'Today 15:00', temp: 27.0, rain: '0.2mm', wind: '3.0m/s', desc: 'Light rain' },
            { time: 'Today 18:00', temp: 24.8, rain: '0mm', wind: '2.5m/s', desc: 'Few clouds' },
            { time: 'Today 21:00', temp: 21.3, rain: '0mm', wind: '1.9m/s', desc: 'Clear sky' },
        ],
        day: [
            { time: 'Feb 01, 2026', temp: 25.0, rain: '0.5mm', wind: '2.5m/s', desc: 'Partly cloudy' },
            { time: 'Feb 02, 2026', temp: 26.2, rain: '0mm', wind: '2.7m/s', desc: 'Clear sky' },
            { time: 'Feb 03, 2026', temp: 24.8, rain: '1.2mm', wind: '3.1m/s', desc: 'Showers' },
            { time: 'Feb 04, 2026', temp: 23.5, rain: '0mm', wind: '2.0m/s', desc: 'Sunny' },
        ]
    };

    const ForecastApp = {
        form: null,
        tableWrap: null,
        tableBody: null,
        noData: null,

        init: function() {
            this.cacheElements();
            this.bindEvents();
            this.setInitialState();
        },

        cacheElements: function() {
            this.form = document.getElementById(CONFIG.SELECTORS.FORM_ID);
            this.tableWrap = document.getElementById(CONFIG.SELECTORS.TABLE_WRAP_ID);
            this.tableBody = document.querySelector(CONFIG.SELECTORS.TABLE_BODY);
            this.noData = document.getElementById(CONFIG.SELECTORS.NO_DATA_ID);
        },

        bindEvents: function() {
            if (this.form) {
                this.form.addEventListener('submit', this.handleSubmit.bind(this));
            }
        },

        setInitialState: function() {
            // Show no-data message initially
            if (this.noData) this.noData.style.display = '';
            if (this.tableWrap) this.tableWrap.style.display = 'none';
        },

        handleSubmit: function(e) {
            e.preventDefault();
            
            const rangeSelect = document.getElementById(CONFIG.SELECTORS.RANGE_SELECT);
            const range = rangeSelect ? rangeSelect.value : 'hour';
            const data = MOCK_DATA[range] || [];
            
            this.renderTable(data);
        },

        renderTable: function(data) {
            if (!this.tableBody) return;

            this.tableBody.innerHTML = '';
            
            if (!data || data.length === 0) {
                this.showNoData();
                return;
            }

            data.forEach(row => {
                const tr = document.createElement('tr');
                tr.innerHTML = this.createRowHtml(row);
                this.tableBody.appendChild(tr);
            });
            
            this.showTable();
        },

        createRowHtml: function(row) {
            const temp = typeof row.temp === 'number' ? row.temp.toFixed(1) : row.temp;
            return `
                <td><b>${row.time}</b></td>
                <td><span class="temp-val">${temp}°C</span></td>
                <td class="rain-val">${row.rain}</td>
                <td class="wind-val">${row.wind}</td>
                <td><span class="desc-tag">${row.desc}</span></td>
            `;
        },

        showTable: function() {
            if (this.noData) this.noData.style.display = 'none';
            if (this.tableWrap) this.tableWrap.style.display = 'block';
        },

        showNoData: function() {
            if (this.tableWrap) this.tableWrap.style.display = 'none';
            if (this.noData) this.noData.style.display = '';
        }
    };

    // Initialize app when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        ForecastApp.init();
    });
})();
