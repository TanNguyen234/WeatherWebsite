(function () {
    'use strict';

    const state = {
        map: null,
        marker: null,
        chart: null,
        locations: []
    };

    function init() {
        const data = UIHelpers.parseInitialData('initial-data');
        state.locations = (data && data.locations) || [];

        state.map = MapCore.initMap('predict-map', {
            center: [16.0, 106.0],
            zoom: 5,
            zoomControl: false
        });

        MapCore.setupMapClick(state.map, (lat, lng) => {
            document.getElementById('lat-input').value = lat.toFixed(4);
            document.getElementById('lng-input').value = lng.toFixed(4);
            document.getElementById('location-select').value = '';
            setSelection(lat, lng, null);
        });

        bindEvents();
    }

    function bindEvents() {
        document.getElementById('location-select').addEventListener('change', onLocationChange);
        document.getElementById('predict-form').addEventListener('submit', onSubmit);
    }

    function onLocationChange(e) {
        const option = e.target.options[e.target.selectedIndex];
        if (!option.value) {
            return;
        }

        const lat = parseFloat(option.dataset.lat);
        const lng = parseFloat(option.dataset.lng);
        const name = option.textContent.split('(')[0].trim();
        document.getElementById('lat-input').value = '';
        document.getElementById('lng-input').value = '';
        setSelection(lat, lng, name);
    }

    function setSelection(lat, lng, name) {
        if (state.marker) {
            state.map.removeLayer(state.marker);
        }
        state.marker = MapCore.addMarker(state.map, lat, lng);
        state.map.setView([lat, lng], 10);

        document.getElementById('selected-info').innerHTML = `
            <p><strong>${name || 'Vị trí tùy chỉnh'}</strong></p>
            <p>${UIHelpers.formatCoords(lat, lng)}</p>
        `;
    }

    async function onSubmit(e) {
        e.preventDefault();

        const selectEl = document.getElementById('location-select');
        const horizonHours = parseInt(document.getElementById('horizon-hours').value, 10);
        const submitBtn = document.getElementById('predict-submit-btn');

        let payload = { horizon_hours: horizonHours };
        let lat;
        let lng;

        if (selectEl.value) {
            payload.location_id = parseInt(selectEl.value, 10);
            const option = selectEl.options[selectEl.selectedIndex];
            lat = parseFloat(option.dataset.lat);
            lng = parseFloat(option.dataset.lng);
        } else {
            lat = parseFloat(document.getElementById('lat-input').value);
            lng = parseFloat(document.getElementById('lng-input').value);
            if (isNaN(lat) || isNaN(lng)) {
                UIHelpers.showToast('Vui lòng chọn vị trí hoặc nhập tọa độ hợp lệ', 'error');
                return;
            }
            payload.latitude = lat;
            payload.longitude = lng;
        }

        setSelection(lat, lng, null);

        try {
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.classList.add('is-loading');
                submitBtn.textContent = 'Đang phân tích...';
            }

            const result = await WeatherApi.getPredictionComparison(payload);
            renderResult(result);
            document.getElementById('result-location').textContent = UIHelpers.formatCoords(
                result.location.latitude,
                result.location.longitude
            );
        } catch (error) {
            UIHelpers.showToast(error.message, 'error');
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.classList.remove('is-loading');
                submitBtn.textContent = 'Phân tích Predict';
            }
        }
    }

    function renderResult(result) {
        document.getElementById('empty-state').classList.add('is-hidden');
        document.getElementById('predict-results').classList.remove('is-hidden');

        const api = result.api_result;
        let aiStatus = result.ai_status || { available: false, message: 'Unknown AI status', error: 'Missing ai_status' };
        let ai = null;
        if (aiStatus.available) {
            try {
                ai = validateAiResult(result.ai_result);
            } catch (error) {
                aiStatus = {
                    available: false,
                    message: 'AI output không hợp lệ',
                    error: error.message || 'Invalid ai_result format'
                };
                ai = null;
            }
        }
        const cmp = result.comparison;

        document.getElementById('api-temp').textContent = UIHelpers.formatTemp(api.temperature);
        document.getElementById('api-humidity').textContent = UIHelpers.formatHumidity(api.humidity);
        document.getElementById('api-wind').textContent = UIHelpers.formatWind(api.wind_speed);
        document.getElementById('api-description').textContent = api.description;

        if (ai) {
            const confidencePercent = Math.round(ai.confidence * 100);
            document.getElementById('prediction-score').textContent = `${ai.prediction_score}`;
            document.getElementById('confidence-level').textContent = `${confidencePercent}%`;
            document.getElementById('model-name').textContent = ai.model;

            document.getElementById('ai-temp').textContent = UIHelpers.formatTemp(ai.temperature);
            document.getElementById('ai-humidity').textContent = UIHelpers.formatHumidity(ai.humidity);
            document.getElementById('ai-wind').textContent = UIHelpers.formatWind(ai.wind_speed);
            document.getElementById('ai-description').textContent = ai.description;

            setDeltaValue('delta-temp', cmp.temperature_delta, '°C');
            setDeltaValue('delta-humidity', cmp.humidity_delta, '%');
            setDeltaValue('delta-wind', cmp.wind_speed_delta, ' m/s');

            updateAiRuntime(ai.source, false);
            updateMeters(ai.prediction_score, confidencePercent);
            updateAiStatusPanel(aiStatus, false);
            renderChart(api, ai);
        } else {
            document.getElementById('prediction-score').textContent = '--';
            document.getElementById('confidence-level').textContent = '--';
            document.getElementById('model-name').textContent = 'Local model unavailable';

            document.getElementById('ai-temp').textContent = '--';
            document.getElementById('ai-humidity').textContent = '--';
            document.getElementById('ai-wind').textContent = '--';
            document.getElementById('ai-description').textContent = '--';

            document.getElementById('delta-temp').textContent = '--';
            document.getElementById('delta-humidity').textContent = '--';
            document.getElementById('delta-wind').textContent = '--';
            clearDeltaState('delta-temp');
            clearDeltaState('delta-humidity');
            clearDeltaState('delta-wind');

            updateAiRuntime('model-error', true);
            updateMeters(0, 0);
            updateAiStatusPanel(aiStatus, true);
            renderChart(api, null);
        }

        if (state.marker) {
            state.marker.bindPopup(`
                <div class="gis-popup">
                    <div class="popup-header">API vs AI</div>
                    <p>API: ${UIHelpers.formatTemp(api.temperature)} / ${UIHelpers.formatHumidity(api.humidity)}</p>
                    <p>AI: ${ai ? `${UIHelpers.formatTemp(ai.temperature)} / ${UIHelpers.formatHumidity(ai.humidity)}` : 'Model lỗi - không có kết quả AI'}</p>
                    <p>Confidence: ${ai ? `${Math.round(ai.confidence * 100)}%` : '--'}</p>
                </div>
            `).openPopup();
        }
    }

    function validateAiResult(ai) {
        if (!ai || typeof ai !== 'object') {
            throw new Error('Thiếu ai_result từ backend');
        }

        const requiredNumeric = ['temperature', 'humidity', 'wind_speed', 'confidence', 'prediction_score'];
        for (const field of requiredNumeric) {
            const value = Number(ai[field]);
            if (!Number.isFinite(value)) {
                throw new Error(`AI output không hợp lệ: thiếu ${field}`);
            }
        }

        const requiredText = ['description', 'model', 'source'];
        for (const field of requiredText) {
            if (!ai[field]) {
                throw new Error(`AI output không hợp lệ: thiếu ${field}`);
            }
        }

        return ai;
    }

    function updateMeters(score, confidencePercent) {
        const scoreFill = document.getElementById('score-meter-fill');
        const confidenceFill = document.getElementById('confidence-meter-fill');
        if (!scoreFill || !confidenceFill) {
            return;
        }

        scoreFill.style.width = `${Math.max(0, Math.min(100, Number(score) || 0))}%`;
        confidenceFill.style.width = `${Math.max(0, Math.min(100, Number(confidencePercent) || 0))}%`;
    }

    function setDeltaValue(elementId, value, unit) {
        const el = document.getElementById(elementId);
        if (!el) {
            return;
        }

        const numeric = Number(value);
        if (!Number.isFinite(numeric)) {
            el.textContent = '--';
            clearDeltaState(elementId);
            return;
        }

        const sign = numeric > 0 ? '+' : '';
        el.textContent = `${sign}${numeric}${unit}`;
        el.classList.remove('delta-positive', 'delta-negative', 'delta-neutral');

        if (numeric > 0) {
            el.classList.add('delta-positive');
            return;
        }

        if (numeric < 0) {
            el.classList.add('delta-negative');
            return;
        }

        el.classList.add('delta-neutral');
    }

    function clearDeltaState(elementId) {
        const el = document.getElementById(elementId);
        if (!el) {
            return;
        }
        el.classList.remove('delta-positive', 'delta-negative', 'delta-neutral');
    }

    function updateAiRuntime(source, isError) {
        const badge = document.getElementById('ai-runtime-badge');
        const sourceEl = document.getElementById('ai-source');
        if (!badge || !sourceEl) {
            return;
        }
        const isLocal = String(source || '').includes('chronos') || String(source || '').includes('local');

        badge.classList.remove('local', 'external', 'error');
        if (isError) {
            badge.textContent = 'MODEL ERROR';
            badge.classList.add('error');
            sourceEl.textContent = 'Không có dữ liệu AI từ local model';
            return;
        }

        if (isLocal) {
            badge.textContent = 'LOCAL AI';
            badge.classList.add('local');
        } else {
            badge.textContent = 'EXTERNAL MODEL';
            badge.classList.add('external');
        }

        sourceEl.textContent = source || '--';
    }

    function updateAiStatusPanel(aiStatus, isError) {
        const panel = document.getElementById('ai-status-panel');
        const msg = document.getElementById('ai-status-message');
        const err = document.getElementById('ai-status-error');
        if (!panel || !msg || !err) {
            return;
        }

        if (!isError) {
            panel.classList.add('is-hidden');
            return;
        }

        panel.classList.remove('is-hidden');
        msg.textContent = aiStatus.message || 'Local model unavailable';
        err.textContent = aiStatus.error || 'Unknown model runtime error';
    }

    function renderChart(api, ai) {
        const ctx = document.getElementById('predict-chart').getContext('2d');
        if (state.chart) {
            state.chart.destroy();
        }

        const datasets = [
            {
                label: 'API',
                data: [api.temperature, api.humidity, api.wind_speed],
                backgroundColor: 'rgba(37, 99, 235, 0.8)'
            }
        ];

        if (ai) {
            datasets.push(
                {
                    label: 'AI',
                    data: [ai.temperature, ai.humidity, ai.wind_speed],
                    backgroundColor: 'rgba(16, 185, 129, 0.8)'
                },
                {
                    label: 'Delta (AI-API)',
                    data: [
                        ai.temperature - api.temperature,
                        ai.humidity - api.humidity,
                        ai.wind_speed - api.wind_speed
                    ],
                    backgroundColor: 'rgba(245, 158, 11, 0.85)'
                }
            );
        }

        state.chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Nhiệt độ', 'Độ ẩm', 'Gió'],
                datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            usePointStyle: true,
                            boxWidth: 10,
                            padding: 14
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(148, 163, 184, 0.22)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    }

    document.addEventListener('DOMContentLoaded', init);
})();
