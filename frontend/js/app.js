'use strict';
const $ = id => document.getElementById(id);
const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const formatTime = value => value ? new Date(value).toLocaleString('zh-TW', {timeZone:'Asia/Taipei', hour12:false}) : '尚未取得';
const regionCoords = {'北部地區':[25.03,121.56],'中部地區':[24.15,120.68],'南部地區':[22.63,120.30],'東北部地區':[24.75,121.75],'東部地區':[23.99,121.61],'東南部地區':[22.75,121.15]};
const state = {view:'stations', mode:'markers', stations:[], latest:null, forecast:null, snapshots:[], historical:null, sequence:0};
let map, layer, tile, windy, chart, timer, refreshInFlight = false, forecastSequence = 0;

async function getJson(url) {
    const response = await fetch(url, {signal:AbortSignal.timeout(65000)});
    if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${response.status}`);
    }
    return response.json();
}
function options(select, values, preferred) {
    const previous = select.value || preferred;
    select.replaceChildren(...values.map(value => new Option(value, value)));
    if (values.includes(previous)) select.value = previous;
}
function showMapMessage(text) {
    $('map-message').textContent = text;
    $('map-message').hidden = !text;
}
async function initMap() {
    const config = await getJson('/api/config').catch(() => ({}));
    if (config.windy_api_key) {
        try {
            await new Promise((resolve,reject) => {
                const script = document.createElement('script');
                script.src = 'https://api.windy.com/assets/map-forecast/libBoot.js';
                script.onload = resolve; script.onerror = reject;
                document.head.appendChild(script);
            });
            windy = await new Promise((resolve,reject) => {
                const timeout = setTimeout(() => reject(new Error('Windy timeout')), 20000);
                window.windyInit({key:config.windy_api_key, lat:23.7, lon:121, zoom:7}, api => {clearTimeout(timeout); resolve(api);});
            });
            map = windy.map;
            $('weather-controls').hidden = false;
            $('base-controls').hidden = true;
            $('map-note').textContent = 'Windy 為天氣模型背景；CWA 圓點為測站觀測或區域預報，時間不一定相同。';
        } catch (_) {
            // Recreate the container if a failed SDK left a partially initialized map.
            $('windy').replaceWith(Object.assign(document.createElement('div'), {id:'windy', className:'map-container'}));
            $('map-note').textContent = 'Windy 無法載入，目前使用一般底圖。';
        }
    }
    if (!map) {
        map = L.map('windy', {center:[23.7,121], zoom:7, minZoom:5});
        setBase('dark');
    }
    layer = L.layerGroup().addTo(map);
    map.on('zoomend', renderMap);
    if (window.matchMedia('(max-width:760px)').matches) {
        $('sidebar').classList.add('collapsed');
        $('toggle-sidebar-btn').setAttribute('aria-expanded','false');
    }
}
function setBase(name) {
    if (windy) return;
    if (tile) map.removeLayer(tile);
    tile = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom:19, className:name==='dark'?'dark-map-tiles':''
    }).addTo(map);
    document.querySelectorAll('[data-base]').forEach(b => b.classList.toggle('active', b.dataset.base===name));
}
function filteredStations() {
    const county = $('county-select').value;
    const query = $('search-input').value.trim().toLowerCase();
    return state.stations.filter(s => (county==='ALL' || s.county===county) && (!query || [s.station_id,s.station_name,s.county,s.town].some(x => String(x || '').toLowerCase().includes(query))));
}
function popup(s) {
    const measure = (value,unit) => value == null ? '無資料' : `${escapeHtml(value)} ${unit}`;
    return `<div class="popup-card"><h4>${escapeHtml(s.station_name)} (${escapeHtml(s.station_id)})</h4><div>${escapeHtml(s.county)} ${escapeHtml(s.town)}</div><div class="temp-large" style="color:${colorByTemperature(s.temperature_c)}">${s.temperature_c} °C</div><div>濕度：${measure(s.humidity_percent,'%')}<br>風速：${measure(s.wind_speed_mps,'m/s')}<br>雨量：${measure(s.precipitation_mm,'mm')}<br>觀測：${formatTime(s.observed_at)}</div></div>`;
}
function renderMap() {
    if (!layer) return;
    layer.clearLayers();
    if (state.view==='forecast') {
        const rows = (state.forecast?.forecasts || []).filter(r => r.dataDate===$('forecast-date').value);
        for (const r of rows) {
            const selected = r.regionName===$('forecast-region').value;
            const color = colorByTemperature(r.avgT);
            L.circleMarker(regionCoords[r.regionName], {radius:selected?17:12, color:selected?'#fff':color, weight:3, fillColor:color, fillOpacity:.9})
                .bindPopup(`<strong>${escapeHtml(r.regionName)}</strong><br>${escapeHtml(r.dataDate)}<br>最低 ${r.minT}°C／最高 ${r.maxT}°C<br>高低溫均值 ${r.avgT}°C`)
                .bindTooltip(`${r.regionName} ${r.minT}–${r.maxT}°C`).addTo(layer);
        }
        showMapMessage(rows.length ? '六區預報｜顏色依最高與最低溫均值' : '目前沒有可用的未來七天預報');
        return;
    }
    const stations = filteredStations();
    $('station-count').textContent = `${stations.length} / ${state.stations.length} 站`;
    showMapMessage(state.historical ? `歷史快照：${formatTime(state.historical)}` : stations.length ? '' : '目前篩選條件下沒有可用測站');
    if (state.mode==='heatmap' && L.heatLayer) {
        L.heatLayer(stations.map(s => [s.lat,s.lon,Math.max(.1,Math.min(1,(s.temperature_c-10)/25))]),
            {radius:25,blur:15,maxZoom:18,gradient:{.2:'#2b6cb0',.4:'#38a169',.6:'#ecc94b',.8:'#ed8936',1:'#e53e3e'}}).addTo(layer);
        if (!state.historical) showMapMessage('熱力圖呈現測站氣溫權重與密度，非連續氣溫等值面');
    } else {
        const group = state.mode==='cluster' && L.markerClusterGroup ? L.markerClusterGroup({disableClusteringAtZoom:12}) : L.layerGroup();
        for (const s of stations) {
            const color = colorByTemperature(s.temperature_c);
            const marker = L.circleMarker([s.lat,s.lon], {radius:getMarkerRadius(s.temperature_c), color:'#fff',weight:1,fillColor:color,fillOpacity:.9}).bindPopup(popup(s));
            if ($('toggle-labels').checked && map.getZoom()>=8) marker.bindTooltip(`${s.temperature_c}°`, {permanent:true,direction:'top'});
            group.addLayer(marker);
        }
        group.addTo(layer);
    }
    $('hottest-list').innerHTML = [...stations].sort((a,b) => b.temperature_c-a.temperature_c).slice(0,5)
        .map(s => `<li>${escapeHtml(s.county)} ${escapeHtml(s.station_name)} <strong>${s.temperature_c}°C</strong></li>`).join('');
    const hot = stations.filter(s => s.temperature_c>=33), cold = stations.filter(s => s.temperature_c<=15);
    $('alert-content').textContent = stations.length ? `≥33°C：${hot.length} 站；≤15°C：${cold.length} 站` : '沒有可判讀的觀測資料。';
}
function renderStatus() {
    const data = state.view==='forecast' ? state.forecast : state.latest;
    const stale = !data || data.stale;
    $('status-text').textContent = stale ? '資料待更新或暫用快取' : data.partial ? '部分資料尚未齊全' : '資料已同步';
    $('update-time').textContent = state.historical && state.view==='stations' ? `歷史資料：${formatTime(state.historical)}` : `${stale?'⚠ ':''}資料更新：${formatTime(data?.updated_at)}${data?.stale?'（可能已過期）':''}`;
}
function renderForecast() {
    const data = state.forecast;
    const rows = (data?.forecasts || []).filter(r => r.regionName===$('forecast-region').value);
    $('forecast-status').textContent = !rows.length ? '沒有未來七天的可用資料，請更新或確認 CWA 設定。' : `${data.stale?'⚠ 更新失敗或資料已過期，顯示保留的預報。 ':''}${data.partial?'目前僅有 '+data.dates.length+' 天預報。':'顯示今天起七天的預報。'}`;
    $('chart-title').textContent = `${$('forecast-region').value} 高低溫走勢`;
    if (chart) {
        chart.data.labels = rows.map(r => r.dataDate.slice(5));
        chart.data.datasets[0].data = rows.map(r => r.maxT);
        chart.data.datasets[1].data = rows.map(r => r.minT);
        chart.update();
    }
    $('forecast-table').innerHTML = rows.map(r => `<tr><td>${r.dataDate}</td><td>${r.minT}°</td><td>${r.maxT}°</td><td>${r.avgT}°</td></tr>`).join('');
    $('daily-table').innerHTML = (data?.forecasts || []).filter(r => r.dataDate===$('forecast-date').value).map(r => `<tr><td>${escapeHtml(r.regionName)}</td><td>${r.minT}°</td><td>${r.maxT}°</td></tr>`).join('');
    $('forecast-export').href = '/api/forecasts/export/csv?region='+encodeURIComponent($('forecast-region').value);
    if (state.view==='forecast') {renderMap();renderStatus();}
}
async function loadForecast(force=false) {
    const sequence = ++forecastSequence;
    try {
        const data = await getJson('/api/forecasts/chart?refresh='+force);
        if (sequence!==forecastSequence) return;
        state.forecast=data;
        options($('forecast-date'),data.dates);
        renderForecast();
    } catch (_) {
        if (state.forecast) state.forecast.stale=true;
        $('forecast-status').textContent='預報更新失敗，稍後可再次更新。';
        renderStatus();
    }
}
function populateCounties() {
    const previous = $('county-select').value;
    const names = [...new Set(state.stations.map(s => s.county).filter(Boolean))].sort();
    $('county-select').replaceChildren(new Option('全台灣','ALL'),...names.map(s => new Option(s,s)));
    if (names.includes(previous)) $('county-select').value=previous;
}
async function loadStations(force=false) {
    try {
        const data = await getJson('/api/temperature/latest?refresh='+force);
        state.latest=data;
        if (!state.historical) {state.stations=data.stations;populateCounties();renderMap();}
    } catch (_) {
        if (state.latest) state.latest.stale=true;
        else $('status-text').textContent='尚無觀測資料，請確認 CWA 設定';
    }
    renderStatus();
}
async function loadHistory() {
    try {
        const {snapshots} = await getJson('/api/temperature/history');
        state.snapshots=snapshots.slice().reverse();
        const range=$('history-range');
        range.max=Math.max(0,snapshots.length-1);
        range.disabled=!snapshots.length;
        if (!state.historical) {
            range.value=range.max;
            $('history-label').textContent=snapshots.length ? `${snapshots.length} 份快照・目前為最新觀測` : '尚無歷史快照';
        } else range.value=Math.max(0,state.snapshots.findIndex(s => s.captured_at===state.historical));
    } catch (_) {$('history-label').textContent='歷史快照載入失敗';}
}
async function selectHistory() {
    const captured=state.snapshots[Number($('history-range').value)]?.captured_at;
    if (!captured) return;
    const sequence=++state.sequence;
    try {
        const data=await getJson('/api/temperature/snapshot?at='+encodeURIComponent(captured));
        if (sequence!==state.sequence) return;
        state.historical=captured;state.stations=data.stations;
        $('history-label').textContent=formatTime(captured);
        populateCounties();renderMap();renderStatus();
    } catch (_) {$('history-label').textContent='此快照無法載入，請重新選取';}
}
async function refreshAll(force=false) {
    if (refreshInFlight) return;
    refreshInFlight=true;$('refresh-btn').disabled=true;
    try {await Promise.allSettled([loadStations(force),loadForecast(force)]);await loadHistory();}
    finally {refreshInFlight=false;$('refresh-btn').disabled=false;}
}
function switchView(view) {
    state.view=view;
    $('sidebar').scrollTop=0;
    $('station-controls').hidden=view!=='stations';$('forecast-controls').hidden=view!=='forecast';
    document.querySelectorAll('[data-view]').forEach(b => {b.classList.toggle('active',b.dataset.view===view);b.setAttribute('aria-pressed',String(b.dataset.view===view));});
    renderStatus();renderForecast();renderMap();
    setTimeout(() => {map.invalidateSize();chart?.resize();},50);
}
function setup() {
    options($('forecast-region'),Object.keys(regionCoords),'中部地區');
    document.querySelectorAll('[data-view]').forEach(b => b.onclick=() => switchView(b.dataset.view));
    document.querySelectorAll('[data-mode]').forEach(b => b.onclick=() => {
        state.mode=b.dataset.mode;
        document.querySelectorAll('[data-mode]').forEach(x => x.classList.toggle('active',x===b));renderMap();
    });
    document.querySelectorAll('[data-base]').forEach(b => b.onclick=() => setBase(b.dataset.base));
    document.querySelectorAll('[data-overlay]').forEach(b => b.onclick=() => {
        windy?.store.set('overlay',b.dataset.overlay);
        document.querySelectorAll('[data-overlay]').forEach(x => x.classList.toggle('active',x===b));
    });
    ['county-select','toggle-labels'].forEach(id => $(id).onchange=renderMap);
    $('search-input').oninput=renderMap;
    ['forecast-region','forecast-date'].forEach(id => $(id).onchange=renderForecast);
    $('refresh-btn').onclick=() => refreshAll(true);
    $('toggle-auto-refresh').onchange=() => {clearInterval(timer);if ($('toggle-auto-refresh').checked) timer=setInterval(() => refreshAll(),300000);};
    $('toggle-auto-refresh').onchange();
    $('history-range').oninput=selectHistory;
    $('history-live').onclick=() => {++state.sequence;state.historical=null;state.stations=state.latest?.stations || [];populateCounties();loadHistory();renderMap();renderStatus();};
    $('toggle-sidebar-btn').onclick=() => {
        $('sidebar').classList.toggle('collapsed');$('toggle-sidebar-btn').setAttribute('aria-expanded',String(!$('sidebar').classList.contains('collapsed')));
        setTimeout(() => map.invalidateSize(),320);
    };
    $('btn-run-sql').onclick=async () => {
        $('sql-result-output').textContent='查詢中…';
        try {const data=await getJson('/api/forecasts/sql-query?query='+encodeURIComponent($('sql-input-query').value));$('sql-result-output').textContent=`${data.count} 筆（上限 ${data.limit}）\n`+JSON.stringify(data.results,null,2);}
        catch(e) {$('sql-result-output').textContent=e.message;}
    };
    const bands=[[-1,'< 10'],[10,'10–<15'],[15,'15–<20'],[20,'20–<25'],[25,'25–<30'],[30,'30–<35'],[35,'≥ 35']];
    $('legend-items').innerHTML=bands.map(([t,label]) => `<div class="legend-item"><span class="color-box" style="background:${colorByTemperature(t)}"></span>${label}</div>`).join('');
    if (window.Chart) chart=new Chart($('tempLineChart'),{type:'line',data:{labels:[],datasets:[{label:'最高溫 °C',data:[],borderColor:'#ef4444',tension:.2},{label:'最低溫 °C',data:[],borderColor:'#60a5fa',tension:.2}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#cbd5e1'}}},scales:{x:{ticks:{color:'#94a3b8'}},y:{ticks:{color:'#94a3b8'}}}}});
}
document.addEventListener('DOMContentLoaded',async () => {
    try {await initMap();setup();await refreshAll();}
    catch (_) {$('status-text').textContent='地圖元件載入失敗';showMapMessage('請確認網路連線後重新整理頁面');}
});
