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
        lastAiSeries: [],
        lastPayload: null,
        lastRows: [],
        lastDisplayRows: []
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
        document.getElementById('download-csv-btn').addEventListener('click', () => exportPrediction('csv'));
        document.getElementById('download-image-btn').addEventListener('click', () => exportPrediction('image'));
    }

    function onMetricChange(e) {
        state.activeMetric = e.target.value;
        if (!state.lastDisplayRows || state.lastDisplayRows.length === 0) {
            return;
        }
        renderChart(state.lastDisplayRows);
        renderChartImageFromCanvas();
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
        state.marker = MapCore.addMarker(state.map, lat, lng, { draggable: true });
        state.marker.on('dragend', onPredictMarkerDragged);
        state.map.setView([lat, lng], 10);

        document.getElementById('selected-info').innerHTML = `
            <p><strong>${state.selectedPoint.name}</strong></p>
            <p>${UIHelpers.formatCoords(lat, lng)}</p>
        `;
    }

    function onPredictMarkerDragged(event) {
        const moved = event.target.getLatLng();
        state.selectedPoint = {
            latitude: moved.lat,
            longitude: moved.lng,
            name: 'Điểm kéo trên bản đồ'
        };

        const locationSelect = document.getElementById('location-select');
        if (locationSelect) {
            locationSelect.value = '';
        }

        document.getElementById('selected-info').innerHTML = `
            <p><strong>${state.selectedPoint.name}</strong></p>
            <p>${UIHelpers.formatCoords(moved.lat, moved.lng)}</p>
        `;
    }

    async function onSubmit(e) {
        e.preventDefault();

        const selectEl = document.getElementById('location-select');
        const horizonSelection = parseHorizonSelection(document.getElementById('horizon-hours').value);
        const submitBtn = document.getElementById('predict-submit-btn');

        let payload = { metric: state.activeMetric };
        if (horizonSelection.type === 'day') {
            payload.forecast_days = horizonSelection.value;
        } else {
            payload.horizon_hours = horizonSelection.value;
        }
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
            state.lastPayload = payload;
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

    function parseHorizonSelection(rawValue) {
        const value = String(rawValue || '').trim();
        if (!value) {
            return { type: 'hour', value: 12 };
        }

        const [prefix, numericPart] = value.split(':');
        if (!numericPart) {
            const fallbackHour = parseInt(prefix, 10);
            return { type: 'hour', value: Number.isFinite(fallbackHour) ? fallbackHour : 12 };
        }

        const parsedValue = parseInt(numericPart, 10);
        if (prefix === 'd') {
            return { type: 'day', value: Number.isFinite(parsedValue) ? parsedValue : 3 };
        }
        return { type: 'hour', value: Number.isFinite(parsedValue) ? parsedValue : 12 };
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
        state.lastRows = Array.isArray(result.rows) ? result.rows : buildRows(apiHourly, aiSeries);
        state.lastDisplayRows = buildDisplayRowsByMode(state.lastRows, state.lastPayload);

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
            renderChart(state.lastDisplayRows);
            renderRowsTable(state.lastDisplayRows);
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
            renderChart(state.lastDisplayRows);
            renderRowsTable(state.lastDisplayRows);
        }

        renderChartImage(null);

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

    function buildRows(apiHourly, aiSeries) {
        const maxLen = Math.max(apiHourly.length, aiSeries.length);
        const rows = [];
        for (let i = 0; i < maxLen; i += 1) {
            const api = apiHourly[i] || {};
            const ai = aiSeries[i] || {};
            rows.push({
                timestamp: api.timestamp || null,
                hour_offset: i + 1,
                api_temperature: api.temperature,
                api_humidity: api.humidity,
                api_wind_speed: api.wind_speed,
                ai_temperature: ai.temperature,
                ai_humidity: ai.humidity,
                ai_wind_speed: ai.wind_speed
            });
        }
        return rows;
    }

    function buildDisplayRowsByMode(rows, payload) {
        if (!Array.isArray(rows) || rows.length === 0) {
            return [];
        }

        const isDailyMode = payload && Number.isFinite(Number(payload.forecast_days));
        if (!isDailyMode) {
            return rows;
        }

        const grouped = new Map();
        rows.forEach((row, index) => {
            const parsed = parseTimestamp(row.timestamp);
            const key = parsed
                ? `${parsed.getFullYear()}-${parsed.getMonth() + 1}-${parsed.getDate()}`
                : `fallback-${Math.floor(index / 24) + 1}`;

            if (!grouped.has(key)) {
                grouped.set(key, []);
            }
            grouped.get(key).push(row);
        });

        const dailyRows = [];
        Array.from(grouped.entries()).forEach(([, dayRows], idx) => {
            const firstTimestamp = dayRows.find((r) => r.timestamp)?.timestamp || null;
            dailyRows.push({
                timestamp: firstTimestamp,
                hour_offset: (idx + 1) * 24,
                api_temperature: averageNumeric(dayRows, 'api_temperature'),
                api_humidity: averageNumeric(dayRows, 'api_humidity'),
                api_wind_speed: averageNumeric(dayRows, 'api_wind_speed'),
                ai_temperature: averageNumeric(dayRows, 'ai_temperature'),
                ai_humidity: averageNumeric(dayRows, 'ai_humidity'),
                ai_wind_speed: averageNumeric(dayRows, 'ai_wind_speed')
            });
        });

        return dailyRows;
    }

    function averageNumeric(rows, key) {
        const values = rows
            .map((row) => Number(row[key]))
            .filter((value) => Number.isFinite(value));

        if (values.length === 0) {
            return null;
        }

        const sum = values.reduce((acc, value) => acc + value, 0);
        return Number((sum / values.length).toFixed(1));
    }

    function renderRowsTable(rows) {
        const tbody = document.getElementById('predict-table-body');
        if (!tbody) {
            return;
        }

        if (!Array.isArray(rows) || rows.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7">Không có dữ liệu dự báo theo giờ.</td></tr>';
            return;
        }

        const horizonHours = state.lastPayload && Number(state.lastPayload.horizon_hours);
        const showDate = shouldShowDateInLabel(rows, horizonHours);
        const granularity = detectTimeGranularity(rows);

        tbody.innerHTML = rows
            .map((row) => {
                return `
                    <tr>
                        <td>${formatHourLabel(row.timestamp, row.hour_offset, showDate, granularity)}</td>
                        <td>${formatValue(row.api_temperature)}</td>
                        <td>${formatValue(row.ai_temperature)}</td>
                        <td>${formatValue(row.api_humidity)}</td>
                        <td>${formatValue(row.ai_humidity)}</td>
                        <td>${formatValue(row.api_wind_speed)}</td>
                        <td>${formatValue(row.ai_wind_speed)}</td>
                    </tr>
                `;
            })
            .join('');
    }

    function formatValue(value) {
        if (value === null || value === undefined || Number.isNaN(Number(value))) {
            return '--';
        }
        return `${value}`;
    }

    function renderChartImage(base64Image) {
        const box = document.getElementById('chart-image-box');
        const image = document.getElementById('predict-chart-image');
        if (!box || !image) {
            return;
        }

        if (base64Image) {
            image.src = `data:image/png;base64,${base64Image}`;
            box.classList.remove('is-hidden');
            return;
        }

        renderChartImageFromCanvas();
    }

    function renderChartImageFromCanvas() {
        const box = document.getElementById('chart-image-box');
        const image = document.getElementById('predict-chart-image');
        if (!box || !image || !state.chart) {
            return;
        }
        image.src = state.chart.toBase64Image('image/png', 1);
        box.classList.remove('is-hidden');
    }

    async function exportPrediction(type) {
        if (!state.lastPayload) {
            UIHelpers.showToast('Hãy chạy dự đoán trước khi tải dữ liệu', 'error');
            return;
        }

        const payload = {
            ...state.lastPayload,
            metric: state.activeMetric
        };
        try {
            if (type === 'image') {
                if (!state.chart) {
                    UIHelpers.showToast('Chưa có biểu đồ để tải ảnh', 'error');
                    return;
                }
                const dataUrl = state.chart.toBase64Image('image/png', 1);
                downloadDataUrl(dataUrl, 'predict_chart.png');
                return;
            }

            if (type === 'csv') {
                const blob = await WeatherApi.exportPredictionCsv(payload);
                downloadBlob(blob, 'predict_result.csv');
                return;
            }
        } catch (error) {
            UIHelpers.showToast(error.message, 'error');
        }
    }

    function downloadDataUrl(dataUrl, filename) {
        const anchor = document.createElement('a');
        anchor.href = dataUrl;
        anchor.download = filename;
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
    }

    function downloadBlob(blob, filename) {
        const url = window.URL.createObjectURL(blob);
        const anchor = document.createElement('a');
        anchor.href = url;
        anchor.download = filename;
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
        window.URL.revokeObjectURL(url);
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

    function renderChart(rows) {
        const ctx = document.getElementById('predict-chart').getContext('2d');
        if (state.chart) {
            state.chart.destroy();
        }

        if (!Array.isArray(rows) || rows.length === 0) {
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
        const horizonHours = state.lastPayload && Number(state.lastPayload.horizon_hours);
        const showDate = shouldShowDateInLabel(rows, horizonHours);
        const granularity = detectTimeGranularity(rows);

        const apiField = `api_${selected.key}`;
        const aiField = `ai_${selected.key}`;
        const labels = rows.map((item) => formatHourLabel(item.timestamp, item.hour_offset, showDate, granularity));
        const apiData = rows.map((item) => Number(item[apiField]));

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

        if (rows.some((item) => item[aiField] !== null && item[aiField] !== undefined)) {
            datasets.push(
                {
                    label: `AI ${selected.label} (${selected.unit})`,
                    data: rows.map((item) => {
                        const numeric = Number(item[aiField]);
                        return Number.isFinite(numeric) ? numeric : null;
                    }),
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
                            text: 'Mốc thời gian dự báo'
                        },
                        ticks: {
                            maxRotation: 0,
                            autoSkip: false,
                            callback(value, index) {
                                const count = labels.length;
                                if (count <= 12) {
                                    return labels[index];
                                }

                                const step = count <= 24 ? 2 : Math.ceil(count / 12);
                                return index % step === 0 ? labels[index] : '';
                            }
                        },
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    }

    function shouldShowDateInLabel(series, horizonHours = null) {
        if (!Array.isArray(series) || series.length === 0) {
            return false;
        }

        const horizon = Number(horizonHours);
        if (Number.isFinite(horizon) && horizon >= 24) {
            return true;
        }

        if (series.length >= 24) {
            return true;
        }

        let firstDateKey = null;
        const hourMinuteSeen = new Set();
        for (const item of series) {
            const parsed = parseTimestamp(item && item.timestamp);
            if (!parsed) {
                continue;
            }

            const hourMinuteKey = `${parsed.getHours()}:${parsed.getMinutes()}`;
            if (hourMinuteSeen.has(hourMinuteKey)) {
                return true;
            }
            hourMinuteSeen.add(hourMinuteKey);

            const dateKey = `${parsed.getFullYear()}-${parsed.getMonth()}-${parsed.getDate()}`;
            if (firstDateKey === null) {
                firstDateKey = dateKey;
                continue;
            }
            if (dateKey !== firstDateKey) {
                return true;
            }
        }

        return false;
    }

    function detectTimeGranularity(series) {
        if (!Array.isArray(series) || series.length < 2) {
            return 'hourly';
        }

        const parsedTimes = series
            .map((item) => parseTimestamp(item && item.timestamp))
            .filter((item) => item instanceof Date)
            .sort((a, b) => a.getTime() - b.getTime());

        if (parsedTimes.length < 2) {
            return 'hourly';
        }

        const oneHourMs = 60 * 60 * 1000;
        const dayDiffThreshold = 23 * oneHourMs;
        let minDiff = Number.POSITIVE_INFINITY;

        for (let i = 1; i < parsedTimes.length; i += 1) {
            const diff = parsedTimes[i].getTime() - parsedTimes[i - 1].getTime();
            if (diff > 0 && diff < minDiff) {
                minDiff = diff;
            }
        }

        if (!Number.isFinite(minDiff)) {
            return 'hourly';
        }

        return minDiff >= dayDiffThreshold ? 'daily' : 'hourly';
    }

    function parseTimestamp(timestamp) {
        if (!timestamp) {
            return null;
        }

        let normalized = String(timestamp);
        if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(normalized)) {
            normalized = `${normalized}:00`;
        }

        const date = new Date(normalized);
        if (Number.isNaN(date.getTime())) {
            return null;
        }
        return date;
    }

    function formatHourLabel(timestamp, hourOffset, withDate = false, granularity = 'hourly') {
        if (!timestamp) {
            return `+${hourOffset}h`;
        }

        const date = parseTimestamp(timestamp);
        if (!date) {
            return `+${hourOffset}h`;
        }

        const day = `${date.getDate()}`.padStart(2, '0');
        const month = `${date.getMonth() + 1}`.padStart(2, '0');
        const hour = `${date.getHours()}`.padStart(2, '0');
        const minute = `${date.getMinutes()}`.padStart(2, '0');

        if (granularity === 'daily') {
            return `${day}/${month}`;
        }

        if (withDate) {
            return `${day}/${month} ${hour}:${minute}`;
        }
        return `${hour}:${minute}`;
    }

    document.addEventListener('DOMContentLoaded', init);
})();
