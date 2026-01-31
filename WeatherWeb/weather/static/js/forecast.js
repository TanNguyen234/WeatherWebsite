// forecast.js – Handles forecast form and table rendering (mock data only)

document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('forecast-form');
    const tableWrap = document.getElementById('forecast-table-wrap');
    const tableBody = document.querySelector('#forecast-table tbody');
    const noData = document.getElementById('no-data');

    // Pseudo CK mock data (structure matches time-based forecast)
    const MOCK_FORECAST = {
        hour: [
            { time: '2026-01-31 09:00', temp: 22.5, rain: 0, wind: 2.1, desc: 'Clear sky' },
            { time: '2026-01-31 12:00', temp: 25.2, rain: 0, wind: 2.8, desc: 'Few clouds' },
            { time: '2026-01-31 15:00', temp: 27.0, rain: 0.2, wind: 3.0, desc: 'Light rain' },
            { time: '2026-01-31 18:00', temp: 24.8, rain: 0, wind: 2.5, desc: 'Clear sky' },
            { time: '2026-01-31 21:00', temp: 21.3, rain: 0, wind: 1.9, desc: 'Clear sky' },
        ],
        day: [
            { time: '2026-01-31', temp: 25.0, rain: 0.5, wind: 2.5, desc: 'Partly cloudy' },
            { time: '2026-02-01', temp: 26.2, rain: 0, wind: 2.7, desc: 'Clear sky' },
            { time: '2026-02-02', temp: 24.8, rain: 1.2, wind: 3.1, desc: 'Showers' },
            { time: '2026-02-03', temp: 23.5, rain: 0, wind: 2.0, desc: 'Clear sky' },
            { time: '2026-02-04', temp: 22.9, rain: 0, wind: 1.8, desc: 'Clear sky' },
        ]
    };

    form.addEventListener('submit', function (e) {
        e.preventDefault();
        // Always use mock data
        const range = form.range.value;
        const data = MOCK_FORECAST[range] || [];
        renderTable(data);
    });

    function renderTable(data) {
        tableBody.innerHTML = '';
        if (!data.length) {
            tableWrap.style.display = 'none';
            noData.style.display = '';
            return;
        }
        data.forEach(row => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${row.time}</td>
                <td class="temp">${row.temp.toFixed(1)}</td>
                <td class="rain">${row.rain}</td>
                <td class="wind">${row.wind}</td>
                <td class="desc">${row.desc}</td>
            `;
            tableBody.appendChild(tr);
        });
        noData.style.display = 'none';
        tableWrap.style.display = '';
    }

    // Initial state
    tableWrap.style.display = 'none';
    noData.style.display = '';
});
