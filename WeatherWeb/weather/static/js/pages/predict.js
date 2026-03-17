(function () {
    'use strict';

    const state = {
        map: null,
        marker: null,
        chart: null,
        locations: [],
        selectedPoint: null,
        activeMetric: 'temperature',
        lastApiHourly: [],
        lastAiSeries: []
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
            document.getElementById('location-select').value = '';
            setSelection(lat, lng, 'Điểm chọn trên bản đồ');
        });

        bindEvents();
    }

    function bindEvents() {
        document.getElementById('location-select').addEventListener('change', onLocationChange);
        document.getElementById('predict-form').addEventListener('submit', onSubmit);
        document.getElementById('chart-metric').addEventListener('change', onMetricChange);
    }

    function onMetricChange(e) {
        state.activeMetric = e.target.value;
        if (!state.lastApiHourly || state.lastApiHourly.length === 0) {
            return;
        }
        renderChart(state.lastApiHourly, state.lastAiSeries);
    }

    function onLocationChange(e) {
        const option = e.target.options[e.target.selectedIndex];
        if (!option.value) {
            return;
        }

        const lat = parseFloat(option.dataset.lat);
        const lng = parseFloat(option.dataset.lng);
        const name = option.textContent.split('(')[0].trim();
        setSelection(lat, lng, name);
    }

    function setSelection(lat, lng, name) {
        state.selectedPoint = {
            latitude: lat,
            longitude: lng,
            name: name || 'Vị trí tùy chỉnh'
        };

        if (state.marker) {
            state.map.removeLayer(state.marker);
        }
        state.marker = MapCore.addMarker(state.map, lat, lng);
        state.map.setView([lat, lng], 10);

        document.getElementById('selected-info').innerHTML = `
            <p><strong>${state.selectedPoint.name}</strong></p>
            <p>${UIHelpers.formatCoords(lat, lng)}</p>
        `;
    }

    async function onSubmit(e) {
        e.preventDefault();

        const selectEl = document.getElementById('location-select');
        const horizonHours = parseInt(document.getElementById('horizon-hours').value, 10);
        const submitBtn = document.getElementById('predict-submit-btn');

        let payload = { horizon_hours: horizonHours };
        let lat = null;
        let lng = null;
        let selectionName = null;

        if (selectEl.value) {
            payload.location_id = parseInt(selectEl.value, 10);
            const option = selectEl.options[selectEl.selectedIndex];
            lat = parseFloat(option.dataset.lat);
            lng = parseFloat(option.dataset.lng);
            selectionName = option.textContent.split('(')[0].trim();
        } else {
            if (!state.selectedPoint) {
                UIHelpers.showToast('Vui lòng chọn vị trí đã lưu hoặc click lên bản đồ', 'error');
                return;
            }
            lat = state.selectedPoint.latitude;
            lng = state.selectedPoint.longitude;
            selectionName = state.selectedPoint.name;
            payload.latitude = lat;
            payload.longitude = lng;
        }

        setSelection(lat, lng, selectionName);

        try {
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.classList.add('is-loading');
                submitBtn.textContent = 'Đang xử lý dự đoán...';
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
                submitBtn.textContent = 'Phân tích dự đoán';
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
        const apiHourly = result.api_hourly || [];
        const aiSeries = ai && Array.isArray(ai.series) ? ai.series : [];
        state.lastApiHourly = apiHourly;
        state.lastAiSeries = aiSeries;

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

            updateAiRuntime(ai.source, false);
            updateMeters(ai.prediction_score, confidencePercent);
            updateAiStatusPanel(aiStatus, false);
            renderChart(apiHourly, aiSeries);
        } else {
            document.getElementById('prediction-score').textContent = '--';
            document.getElementById('confidence-level').textContent = '--';
            document.getElementById('model-name').textContent = 'Model cục bộ không khả dụng';

            document.getElementById('ai-temp').textContent = '--';
            document.getElementById('ai-humidity').textContent = '--';
            document.getElementById('ai-wind').textContent = '--';
            document.getElementById('ai-description').textContent = '--';

            updateAiRuntime('model-error', true);
            updateMeters(0, 0);
            updateAiStatusPanel(aiStatus, true);
            renderChart(apiHourly, []);
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

        if (!Array.isArray(ai.series) || ai.series.length === 0) {
            throw new Error('AI output không hợp lệ: thiếu chuỗi dự đoán theo giờ');
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

    function updateAiRuntime(source, isError) {
        const badge = document.getElementById('ai-runtime-badge');
        const sourceEl = document.getElementById('ai-source');
        if (!badge || !sourceEl) {
            return;
        }
        const isLocal = String(source || '').includes('chronos') || String(source || '').includes('local');

        badge.classList.remove('local', 'external', 'error');
        if (isError) {
            badge.textContent = 'LỖI MODEL';
            badge.classList.add('error');
            sourceEl.textContent = 'Không có dữ liệu AI từ local model';
            return;
        }

        if (isLocal) {
            badge.textContent = 'AI CỤC BỘ';
            badge.classList.add('local');
        } else {
            badge.textContent = 'MODEL NGOÀI';
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

    function renderChart(apiHourly, aiSeries) {
        const ctx = document.getElementById('predict-chart').getContext('2d');
        if (state.chart) {
            state.chart.destroy();
        }

        if (!Array.isArray(apiHourly) || apiHourly.length === 0) {
            state.chart = null;
            return;
        }

        const metricConfig = {
            temperature: {
                key: 'temperature',
                label: 'Nhiệt độ',
                unit: '°C',
                min: null,
                max: null,
            },
            humidity: {
                key: 'humidity',
                label: 'Độ ẩm',
                unit: '%',
                min: 0,
                max: 100,
            },
            wind_speed: {
                key: 'wind_speed',
                label: 'Tốc độ gió',
                unit: 'm/s',
                min: 0,
                max: null,
            }
        };
        const selected = metricConfig[state.activeMetric] || metricConfig.temperature;

        const labels = apiHourly.map((item) => formatHourLabel(item.timestamp, item.hour_offset));
        const apiData = apiHourly.map((item) => Number(item[selected.key]));

        const datasets = [
            {
                label: `API ${selected.label} (${selected.unit})`,
                data: apiData,
                borderColor: 'rgba(37, 99, 235, 1)',
                backgroundColor: 'rgba(37, 99, 235, 0.2)',
                tension: 0.35,
                borderWidth: 2,
                pointRadius: 2
            },
        ];

        if (aiSeries.length > 0) {
            datasets.push(
                {
                    label: `AI ${selected.label} (${selected.unit})`,
                    data: aiSeries.map((item) => Number(item[selected.key])),
                    borderColor: 'rgba(16, 185, 129, 1)',
                    backgroundColor: 'rgba(16, 185, 129, 0.2)',
                    tension: 0.35,
                    borderWidth: 2,
                    borderDash: [5, 4],
                    pointRadius: 2
                }
            );
        }

        state.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels,
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
                        type: 'linear',
                        beginAtZero: selected.min === 0,
                        min: selected.min,
                        max: selected.max,
                        title: {
                            display: true,
                            text: `${selected.label} (${selected.unit})`
                        },
                        grid: {
                            color: 'rgba(148, 163, 184, 0.22)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Mốc thời gian theo giờ đã chọn'
                        },
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    }

    function formatHourLabel(timestamp, hourOffset) {
        if (!timestamp) {
            return `+${hourOffset}h`;
        }

        const date = new Date(timestamp);
        if (Number.isNaN(date.getTime())) {
            return `+${hourOffset}h`;
        }
        const hour = `${date.getHours()}`.padStart(2, '0');
        const minute = `${date.getMinutes()}`.padStart(2, '0');
        return `${hour}:${minute}`;
    }

    document.addEventListener('DOMContentLoaded', init);
})();
