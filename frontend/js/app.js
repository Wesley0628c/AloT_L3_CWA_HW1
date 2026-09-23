// Global Application State
let map;
let stationLayerGroup;
let allStations = [];
let autoRefreshTimer = null;

document.addEventListener("DOMContentLoaded", () => {
    initMap();
    fetchTemperatureData();
    setupEventListeners();
});

/**
 * Initialize Leaflet Map centered on Taiwan
 */
function initMap() {
    // Taiwan Center Coordinates: 23.7, 120.95
    map = L.map('map', {
        center: [23.7, 120.95],
        zoom: 8,
        zoomControl: true
    });

    // Dark Tile Layer (CartoDB Dark Matter)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 19
    }).addTo(map);

    stationLayerGroup = L.layerGroup().addTo(map);
}

/**
 * Fetch latest CWA temperature data from FastAPI backend
 */
async function fetchTemperatureData(forceRefresh = false) {
    const updateTimeElem = document.getElementById("update-time");
    const countElem = document.getElementById("station-count");
    updateTimeElem.innerText = "資料同步中...";

    const url = forceRefresh ? "/api/temperature/latest?refresh=true" : "/api/temperature/latest";

    try {
        const response = await fetch(url);
        if (!response.ok) throw new Error("HTTP error " + response.status);
        const data = await response.json();

        allStations = data.stations || [];
        countElem.innerText = allStations.length;

        const updateTimeStr = data.updated_at ? new Date(data.updated_at).toLocaleString('zh-TW') : "最新觀測";
        updateTimeElem.innerText = `CWA 更新時間: ${updateTimeStr}`;

        renderStationMarkers();
        updateHottestStations();

    } catch (err) {
        console.error("Failed to fetch CWA data:", err);
        updateTimeElem.innerText = "⚠️ 數據擷取失敗 (使用本機快取)";
    }
}

/**
 * Render Leaflet Markers based on active filters
 */
function renderStationMarkers() {
    stationLayerGroup.clearLayers();

    const selectedCounty = document.getElementById("county-select").value;
    const searchQuery = document.getElementById("search-input").value.trim().toLowerCase();
    const showLabels = document.getElementById("toggle-labels").checked;

    const filtered = allStations.filter(st => {
        // County Filter
        if (selectedCounty !== "ALL" && st.county !== selectedCounty) {
            return false;
        }
        // Search Filter
        if (searchQuery) {
            const matchName = st.station_name && st.station_name.toLowerCase().includes(searchQuery);
            const matchCounty = st.county && st.county.toLowerCase().includes(searchQuery);
            const matchTown = st.town && st.town.toLowerCase().includes(searchQuery);
            if (!matchName && !matchCounty && !matchTown) return false;
        }
        return true;
    });

    filtered.forEach(st => {
        const color = colorByTemperature(st.temperature_c);
        const radius = getMarkerRadius(st.temperature_c);

        // Circle Marker
        const marker = L.circleMarker([st.lat, st.lon], {
            radius: radius,
            fillColor: color,
            fillOpacity: 0.85,
            color: "#ffffff",
            weight: 1.5
        });

        // Optional numeric label above marker
        if (showLabels && map.getZoom() >= 9) {
            const labelIcon = L.divIcon({
                className: 'custom-temp-marker',
                html: `<div style="border-color:${color};">${st.temperature_c}°</div>`,
                iconSize: [36, 18],
                iconAnchor: [18, 9]
            });
            L.marker([st.lat, st.lon], { icon: labelIcon, interactive: false }).addTo(stationLayerGroup);
        }

        // Popup Content
        const obsTimeFormatted = st.observed_at ? new Date(st.observed_at).toLocaleString('zh-TW') : "即時";
        const popupContent = `
            <div class="popup-card">
                <h4>${st.station_name} <small style="color:#aaa; font-weight:normal;">(${st.station_id})</small></h4>
                <div class="location">📍 ${st.county || ''} ${st.town || ''}</div>
                <div class="temp-large" style="color:${color};">${st.temperature_c} °C</div>
                <div class="popup-grid">
                    <div>💧 相對濕度: <strong>${st.humidity_percent !== null ? st.humidity_percent + '%' : 'N/A'}</strong></div>
                    <div>💨 風速: <strong>${st.wind_speed_mps !== null ? st.wind_speed_mps + ' m/s' : 'N/A'}</strong></div>
                    <div>🌧️ 累積雨量: <strong>${st.precipitation_mm !== null ? st.precipitation_mm + ' mm' : '0 mm'}</strong></div>
                    <div>⏲️ 觀測時間: <strong>${obsTimeFormatted}</strong></div>
                </div>
            </div>
        `;

        marker.bindPopup(popupContent);
        marker.addTo(stationLayerGroup);
    });
}

/**
 * Update Top 5 Hottest Stations List
 */
function updateHottestStations() {
    const listElem = document.getElementById("hottest-list");
    if (!allStations.length) return;

    const sorted = [...allStations].sort((a, b) => b.temperature_c - a.temperature_c).slice(0, 5);
    listElem.innerHTML = sorted.map(st => `
        <li>
            <strong>${st.county || ''} ${st.station_name}</strong>:
            <span style="color:${colorByTemperature(st.temperature_c)}; font-weight:bold;">${st.temperature_c}°C</span>
        </li>
    `).join('');
}

/**
 * Attach UI Event Listeners
 */
function setupEventListeners() {
    document.getElementById("county-select").addEventListener("change", renderStationMarkers);
    document.getElementById("search-input").addEventListener("input", renderStationMarkers);
    document.getElementById("toggle-labels").addEventListener("change", renderStationMarkers);

    document.getElementById("refresh-btn").addEventListener("click", () => fetchTemperatureData(true));

    // Auto Refresh Toggle
    const autoRefreshToggle = document.getElementById("toggle-auto-refresh");
    autoRefreshToggle.addEventListener("change", () => {
        if (autoRefreshToggle.checked) {
            startAutoRefresh();
        } else {
            stopAutoRefresh();
        }
    });

    startAutoRefresh();

    // Map Zoom Event
    map.on('zoomend', renderStationMarkers);
}

function startAutoRefresh() {
    stopAutoRefresh();
    // 5 minutes interval = 300,000 ms
    autoRefreshTimer = setInterval(() => fetchTemperatureData(false), 300000);
}

function stopAutoRefresh() {
    if (autoRefreshTimer) clearInterval(autoRefreshTimer);
}
