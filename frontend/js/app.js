// Global Application State
let map;
let baseTileLayer;
let activeWeatherTileLayer = null;
let stationLayerGroup;
let heatmapLayer = null;
let clusterGroup = null;
let allStations = [];
let autoRefreshTimer = null;
let activeOverlay = "temp";
let activeViewMode = "markers"; // "markers" | "heatmap" | "cluster"

// Verified Public Weather Tile Overlay URLs (Zero Auth Required, maxZoom 18)
const WEATHER_TILE_LAYERS = {
    wind: {
        base: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        overlayUrl: 'https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png',
        attribution: '&copy; Esri World Imagery & OpenSeaMap Wind'
    },
    temp: {
        base: 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
        overlayUrl: null, // Pure dark base for temperature visualization
        attribution: '&copy; Esri Canvas & CWA Temperature'
    },
    rain: {
        base: 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
        overlayUrl: 'https://tilecache.rainviewer.com/v2/radar/nowcast/256/{z}/{x}/{y}/2/1_1.png',
        attribution: '&copy; RainViewer Real-time Rain Radar'
    },
    clouds: {
        base: 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
        overlayUrl: 'https://tilecache.rainviewer.com/v2/satellite/latest/256/{z}/{x}/{y}/0/0_0.png',
        attribution: '&copy; RainViewer Infrared Satellite Clouds'
    }
};

document.addEventListener("DOMContentLoaded", () => {
    initMap();
    fetchTemperatureData();
    setupEventListeners();
});

/**
 * Initialize Leaflet Map centered on Taiwan with explicit min/max zoom bounds
 */
function initMap() {
    map = L.map('map', {
        center: [23.7, 120.95],
        zoom: 8,
        minZoom: 6,
        maxZoom: 18,
        zoomControl: true
    });

    baseTileLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ',
        minZoom: 6,
        maxZoom: 18
    }).addTo(map);

    stationLayerGroup = L.layerGroup().addTo(map);
    switchWeatherOverlay('temp');
}

/**
 * Switch Weather Overlay (Wind, Temp, Rain, Clouds)
 * NOTE: Weather overlay choice ONLY affects the map background, NEVER overrides activeViewMode!
 */
function switchWeatherOverlay(overlayType) {
    activeOverlay = overlayType;

    const layerInfo = WEATHER_TILE_LAYERS[overlayType];
    if (!layerInfo) return;

    // Switch Base Tile Layer if needed
    if (baseTileLayer && layerInfo.base) {
        map.removeLayer(baseTileLayer);
        baseTileLayer = L.tileLayer(layerInfo.base, {
            attribution: 'Tiles &copy; Esri &mdash; Weather Overlay',
            minZoom: 6,
            maxZoom: 18
        }).addTo(map);
    }

    // Remove existing overlay if present
    if (activeWeatherTileLayer) {
        map.removeLayer(activeWeatherTileLayer);
        activeWeatherTileLayer = null;
    }

    // Add Overlay Tile Layer
    if (layerInfo.overlayUrl) {
        activeWeatherTileLayer = L.tileLayer(layerInfo.overlayUrl, {
            opacity: 0.75,
            minZoom: 6,
            maxZoom: 18,
            attribution: layerInfo.attribution
        }).addTo(map);
    }

    // Update active button state
    document.querySelectorAll('.layer-btn').forEach(btn => {
        if (btn.dataset.overlay === overlayType) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    // Re-render current view mode without changing user's view mode selection!
    renderVisualization();
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

        renderVisualization();
        updateHottestStations();
        updateTemperatureAlerts();

    } catch (err) {
        console.error("Failed to fetch CWA data:", err);
        updateTimeElem.innerText = "⚠️ 數據擷取失敗 (使用本機快取)";
    }
}

/**
 * Master Render Switcher (Markers vs Heatmap vs Cluster)
 */
function renderVisualization() {
    // Clear previous layers
    stationLayerGroup.clearLayers();
    if (heatmapLayer) {
        map.removeLayer(heatmapLayer);
        heatmapLayer = null;
    }
    if (clusterGroup) {
        map.removeLayer(clusterGroup);
        clusterGroup = null;
    }

    const filtered = getFilteredStations();

    if (activeViewMode === "markers") {
        renderStationMarkers(filtered);
    } else if (activeViewMode === "heatmap") {
        renderHeatmapLayer(filtered);
    } else if (activeViewMode === "cluster") {
        renderClusterLayer(filtered);
    }
}

/**
 * Filter Stations based on County and Search query
 */
function getFilteredStations() {
    const selectedCounty = document.getElementById("county-select").value;
    const searchQuery = document.getElementById("search-input").value.trim().toLowerCase();

    return allStations.filter(st => {
        if (selectedCounty !== "ALL" && st.county !== selectedCounty) return false;
        if (searchQuery) {
            const matchName = st.station_name && st.station_name.toLowerCase().includes(searchQuery);
            const matchCounty = st.county && st.county.toLowerCase().includes(searchQuery);
            const matchTown = st.town && st.town.toLowerCase().includes(searchQuery);
            if (!matchName && !matchCounty && !matchTown) return false;
        }
        return true;
    });
}

/**
 * Mode 1: Render Station Markers Layer
 */
function renderStationMarkers(filtered) {
    const showLabels = document.getElementById("toggle-labels").checked;

    filtered.forEach(st => {
        const color = colorByTemperature(st.temperature_c);
        const radius = getMarkerRadius(st.temperature_c);

        const marker = L.circleMarker([st.lat, st.lon], {
            radius: radius,
            fillColor: color,
            fillOpacity: 0.85,
            color: "#ffffff",
            weight: 1.5
        });

        if (showLabels && map.getZoom() >= 8) {
            const labelIcon = L.divIcon({
                className: 'custom-temp-marker',
                html: `<div style="border-color:${color};">${st.temperature_c}°</div>`,
                iconSize: [36, 18],
                iconAnchor: [18, 9]
            });
            L.marker([st.lat, st.lon], { icon: labelIcon, interactive: false }).addTo(stationLayerGroup);
        }

        marker.bindPopup(buildPopupContent(st, color));
        marker.addTo(stationLayerGroup);
    });
}

/**
 * Mode 2: Render Temperature Heatmap Layer
 */
function renderHeatmapLayer(filtered) {
    if (typeof L.heatLayer !== 'function') return;

    const heatPoints = filtered.map(st => {
        const intensity = Math.max(0.1, Math.min(1.0, (st.temperature_c - 10) / 25));
        return [st.lat, st.lon, intensity];
    });

    heatmapLayer = L.heatLayer(heatPoints, {
        radius: 25,
        blur: 15,
        maxZoom: 18,
        gradient: {
            0.2: '#2b6cb0',
            0.4: '#38a169',
            0.6: '#ecc94b',
            0.8: '#ed8936',
            1.0: '#e53e3e'
        }
    }).addTo(map);
}

/**
 * Mode 3: Render Station Cluster Layer
 */
function renderClusterLayer(filtered) {
    if (typeof L.markerClusterGroup !== 'function') return;

    clusterGroup = L.markerClusterGroup({
        disableClusteringAtZoom: 12,
        spiderfyOnMaxZoom: true
    });

    filtered.forEach(st => {
        const color = colorByTemperature(st.temperature_c);
        const radius = getMarkerRadius(st.temperature_c);

        const marker = L.circleMarker([st.lat, st.lon], {
            radius: radius,
            fillColor: color,
            fillOpacity: 0.9,
            color: "#ffffff",
            weight: 1.5
        });

        marker.bindPopup(buildPopupContent(st, color));
        clusterGroup.addLayer(marker);
    });

    map.addLayer(clusterGroup);
}

/**
 * Build Popup Card HTML
 */
function buildPopupContent(st, color) {
    const obsTimeFormatted = st.observed_at ? new Date(st.observed_at).toLocaleString('zh-TW') : "即時";
    return `
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
}

/**
 * Update Extreme Temperature Alerts Warning Box
 */
function updateTemperatureAlerts() {
    const alertBoxContent = document.getElementById("alert-content");
    if (!allStations.length) return;

    const extremeHot = allStations.filter(st => st.temperature_c >= 33.0);
    const extremeCold = allStations.filter(st => st.temperature_c <= 15.0);

    let html = "";
    if (extremeHot.length > 0) {
        html += `<div style="color:#ef4444; font-weight:bold; margin-bottom:4px;">🔥 極端高溫特報 (${extremeHot.length}測站 ≥ 33°C):</div>`;
        html += extremeHot.slice(0, 3).map(st => `• ${st.county}${st.station_name}: <span style="color:#ef4444;">${st.temperature_c}°C</span>`).join('<br>');
    }
    if (extremeCold.length > 0) {
        if (html) html += "<br>";
        html += `<div style="color:#3b82f6; font-weight:bold; margin-top:4px; margin-bottom:4px;">❄️ 低溫特報 (${extremeCold.length}測站 ≤ 15°C):</div>`;
        html += extremeCold.slice(0, 3).map(st => `• ${st.county}${st.station_name}: <span style="color:#3b82f6;">${st.temperature_c}°C</span>`).join('<br>');
    }
    if (!html) {
        html = `<div style="color:#10b981;">✅ 目前全台各氣象站溫濕度指標皆在正常氣候範圍內。</div>`;
    }

    alertBoxContent.innerHTML = html;
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
    document.getElementById("county-select").addEventListener("change", renderVisualization);
    document.getElementById("search-input").addEventListener("input", renderVisualization);
    document.getElementById("toggle-labels").addEventListener("change", renderVisualization);
    document.getElementById("refresh-btn").addEventListener("click", () => fetchTemperatureData(true));

    // View Mode Switcher Buttons (Markers / Heatmap / Cluster)
    document.querySelectorAll('.view-mode-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            activeViewMode = e.currentTarget.dataset.mode;
            document.querySelectorAll('.view-mode-btn').forEach(b => b.classList.remove('active'));
            e.currentTarget.classList.add('active');
            renderVisualization();
        });
    });

    // Weather Layer Switcher Buttons (Wind / Temp / Rain / Clouds)
    document.querySelectorAll('.layer-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const overlayType = e.currentTarget.dataset.overlay;
            switchWeatherOverlay(overlayType);
        });
    });

    // Sidebar RWD Toggle
    document.getElementById("toggle-sidebar-btn").addEventListener("click", () => {
        document.getElementById("sidebar").classList.toggle("collapsed");
    });

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
    map.on('zoomend', renderVisualization);
}

function startAutoRefresh() {
    stopAutoRefresh();
    autoRefreshTimer = setInterval(() => fetchTemperatureData(false), 300000);
}

function stopAutoRefresh() {
    if (autoRefreshTimer) clearInterval(autoRefreshTimer);
}
