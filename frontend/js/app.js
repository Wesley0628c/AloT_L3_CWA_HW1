import {$,escapeHtml as e,formatTime,getJson,options,regions} from './api.js';
import {WeatherMap,palettes} from './map.js';

const state={layer:'temperature',latest:null,stations:[],products:{},forecast:null,region:'中部地區',forecastDate:'',labels:true,windArrows:true,
 radarSource:'cwa',radarIndex:0,stormIndex:0,stormTime:0,historical:null,snapshots:[],capabilities:{supported:{}}};
let weatherMap,chart,timer,busy=false,historySequence=0,needsStormFit=false;
const layerNames={temperature:'氣溫',rainfall:'本日累積雨量',radar:'雷達',typhoon:'颱風',wind:'風速風向',humidity:'濕度',weather:'天氣',stations:'測站點位',forecast:'一週預報'};

function selectedStations() {
 const points=state.layer==='rainfall'?(state.products.rainfall?.stations || []):state.stations;
 const county=$('county').value,query=$('search').value.trim().toLowerCase();
 return points.filter(s=>(county==='ALL'||s.county===county)&&(!query||[s.station_id,s.station_name,s.county,s.town].some(v=>String(v||'').toLowerCase().includes(query))));
}
function note(text){$('map-note').textContent=text;$('map-note').hidden=!text;}
function metric(id,points,field,unit,minimum=false) {
 const sorted=points.filter(s=>Number.isFinite(s[field])).sort((a,b)=>minimum?a[field]-b[field]:b[field]-a[field]);
 $(''+id).innerHTML=sorted.length?`${sorted[0][field]}<i>${unit}</i>`:'—';
 $(id+'-name').textContent=sorted[0]?.station_name || '無資料';
}
function renderSummary() {
 const data=state.latest;
 const points=state.stations;
 metric('max-temp',points,'temperature_c','°C');metric('min-temp',points,'temperature_c','°C',true);
 metric('max-wind',points,'wind_speed_mps','m/s');metric('max-rain',state.historical?points:(state.products.rainfall?.stations||points),'precipitation_mm','mm');
 const times=points.map(s=>s.observed_at).filter(Boolean).sort();
 $('observed-time').textContent=times.length?formatTime(times[times.length-1]):'尚無資料';
 $('station-count').textContent=`測站數量：${selectedStations().length} 站（依目前篩選）`;
 $('connection-badge').textContent=state.historical?'歷史':data?.stale?'快取':points.length?'已同步':'無資料';
 $('data-status').textContent=state.historical?'正在查看歷史測站快照':data?.stale?'更新失敗或部分觀測已過期':data?.partial?'部分來源暫不可用':'各測站觀測時間可能不同';
 $('source-text').textContent=state.layer==='rainfall'?'資料來源：CWA 雨量觀測站':'資料來源：CWA 自動站與局屬站';
 const product=state.products[state.layer==='wind'?'gfs_wind':state.layer==='radar'?(state.radarSource==='history'?'rainviewer':'radar'):state.layer];
 const updated=state.layer==='forecast'?state.forecast?.updated_at:state.historical || product?.updated_at || data?.updated_at;
 const stale=state.layer==='forecast'?state.forecast?.stale:product?product.stale:data?.stale;
 $('updated-time').textContent=`${stale?'⚠ 快取 ':''}更新於 ${formatTime(updated)}`;
}
function renderLegend() {
 const mode=state.layer,p=palettes[mode==='forecast'?'temperature':mode];
 if(p) {
   $('legend').innerHTML=`<strong>${p.unit}</strong><div class="legend-bar" style="background:linear-gradient(to right,${p.colors.join(',')})"></div><div class="legend-labels">${p.stops.map(x=>`<span>${x}</span>`).join('')}</div><p>${mode==='forecast'?'六區高低溫均值':mode==='rainfall'?'本日 00:00 起累積雨量':mode==='wind'?'GFS 模型動畫・CWA 測站箭頭':'CWA 測站觀測值'}</p>`;
 } else if(mode==='radar') $('legend').innerHTML='<strong>雷達回波強度</strong><div class="legend-bar" style="background:linear-gradient(to right,#79cae6,#56ce73,#fbda66,#ef814d,#d24668)"></div><div class="legend-labels"><span>弱</span><span>強</span></div>';
 else if(mode==='weather') $('legend').innerHTML='☀️ 晴　⛅ 多雲　☁️ 陰<br>🌧️ 雨　⛈️ 雷雨　🌫️ 霧';
 else if(mode==='typhoon') $('legend').innerHTML='實線：分析路徑<br>虛線：官方預報路徑<br>淡色圈：官方機率／風圈半徑';
 else $('legend').innerHTML='📍 CWA 測站<br><small>點擊測站查看觀測資料</small>';
}
function renderMap() {
 if(!weatherMap)return;
 weatherMap.render(state,selectedStations());renderLegend();renderSummary();
 let text='';
 if(state.historical)text=`歷史測站快照：${formatTime(state.historical)}`;
 else if(state.layer==='wind') {
   const wind=state.products.gfs_wind;
   text=wind?.available?`${wind.stale?'⚠ 快取 ':''}GFS 有效時間 ${formatTime(wind.valid_at)}｜動畫速度為視覺化縮放`:'僅顯示 CWA 測站風向風速';
 } else if(state.layer==='forecast')text='六區一週預報｜圓點顏色依高低溫均值';
 else if(state.layer==='typhoon'&&!state.products.typhoon?.count)text='目前沒有有效的活動中熱帶氣旋資料';
 else if(!['radar','typhoon'].includes(state.layer)&&!selectedStations().length)text='目前篩選條件下沒有測站資料';
 note(text);
}
function renderWarnings() {
 const data=state.products.warnings;
 $('warnings-panel').hidden=!data?.available;
 if(!data?.available)return;
 $('warning-count').textContent=`${data.count} 則`;
 $('warning-source').textContent=`來源：中央氣象署${data.stale?'（快取可能過期）':''}`;
 $('warning-items').innerHTML=data.count?data.warnings.map(w=>`<article class="warning-item"><header><b>${e(w.title)}</b><span>${w.active?'生效中':'即將生效'}</span></header><small>${formatTime(w.starts_at)} ～ ${formatTime(w.ends_at)}</small><details><summary>${e(w.text.split('\n').find(x=>x.trim())?.slice(0,85)||'查看內容')}</summary><p>${e(w.text)}</p></details></article>`).join(''):'<p class="panel-credit">目前來源沒有尚未到期的特報。</p>';
}
function renderForecast() {
 const rows=(state.forecast?.forecasts||[]).filter(r=>r.regionName===state.region);
 if(chart) {chart.data.labels=rows.map(r=>r.dataDate.slice(5));chart.data.datasets[0].data=rows.map(r=>r.maxT);chart.data.datasets[1].data=rows.map(r=>r.minT);chart.update();}
 $('forecast-status').textContent=!rows.length?'目前沒有未來七天的可用預報。':`${state.forecast.stale?'⚠ 預報資料可能已過期。 ':''}${state.forecast.partial?'目前僅有 '+state.forecast.dates.length+' 天資料。':'顯示今天起七天預報。'}`;
 $('forecast-table').innerHTML=rows.map(r=>`<tr><td>${r.dataDate}</td><td>${r.minT}°</td><td>${r.maxT}°</td><td>${r.avgT}°</td></tr>`).join('');
 $('daily-table').innerHTML=(state.forecast?.forecasts||[]).filter(r=>r.dataDate===state.forecastDate).map(r=>`<tr><td>${e(r.regionName)}</td><td>${r.minT}°</td><td>${r.maxT}°</td></tr>`).join('');
 $('forecast-export').href='/api/forecasts/export/csv?region='+encodeURIComponent(state.region);
}
function renderTimeline() {
 const radar=state.layer==='radar',storm=state.layer==='typhoon';
 $('timeline-panel').hidden=!radar&&!storm;$('radar-timeline').hidden=!radar;$('storm-timeline').hidden=!storm;
 if(radar) {
   const history=state.radarSource==='history';const frames=state.products.rainviewer?.frames||[];
   $('radar-range').hidden=!history;$('radar-range').max=Math.max(0,frames.length-1);$('radar-range').value=state.radarIndex;
   const product=state.products[history?'rainviewer':'radar'];
   $('radar-time').textContent=`${product?.stale?'⚠ 快取 ':''}${history?'RainViewer':'中央氣象署'}：${formatTime(history?frames[state.radarIndex]?.time*1000:product?.observed_at)}`;
 }
 if(storm) {
   const storms=state.products.typhoon?.typhoons||[];
   const selected=storms[state.stormIndex];const points=selected?[...selected.analysis,...selected.forecast]:[];
   $('storm-range').disabled=!points.length;$('storm-range').max=Math.max(0,points.length-1);$('storm-range').value=state.stormTime;
   const p=points[state.stormTime];
   $('storm-time').textContent=p?`${p.forecast?'官方預報':'分析位置'} ${formatTime(p.time)}｜${p.wind_mps ?? '—'} m/s・${p.pressure_hpa ?? '—'} hPa`:'目前無活動中熱帶氣旋';
 }
}
function capabilityButtons() {
 const support=state.capabilities.supported;
 const possible={temperature:support.automatic||support.bureau,humidity:support.automatic||support.bureau,weather:support.automatic||support.bureau,stations:support.automatic||support.bureau,
 rainfall:support.rainfall&&state.products.rainfall?.available,radar:(support.radar&&state.products.radar?.available)||(support.rainviewer&&state.products.rainviewer?.available),typhoon:support.typhoon&&state.products.typhoon?.available,wind:support.gfs_wind&&state.products.gfs_wind?.available||!!state.stations.length};
 document.querySelectorAll('[data-layer]').forEach(b=>b.hidden=!possible[b.dataset.layer]);
 $('radar-source').querySelector('[value=history]').hidden=!state.products.rainviewer?.available;
 $('radar-source').querySelector('[value=cwa]').hidden=!state.products.radar?.available;
 if(state.radarSource==='cwa'&&!state.products.radar?.available&&state.products.rainviewer?.available){state.radarSource='history';$('radar-source').value='history';}
 $('boundaries-control').hidden=!support.boundaries;
}
function setLayer(layer) {
 if(['rainfall','radar','typhoon','forecast'].includes(layer)&&state.historical){state.historical=null;state.stations=state.latest?.stations||[];++historySequence;}
 state.layer=layer;
 document.querySelectorAll('[data-layer]').forEach(b=>{b.classList.toggle('active',b.dataset.layer===layer);b.setAttribute('aria-pressed',String(b.dataset.layer===layer));});
 $('labels-control').hidden=!['temperature','humidity','rainfall'].includes(layer);$('wind-control').hidden=layer!=='wind';
 if(layer==='typhoon'){needsStormFit=true;const storms=state.products.typhoon?.typhoons||[];if(storms.length){weatherMap.fitStorms(storms);needsStormFit=false;}}
 renderTimeline();renderMap();
}
function openDrawer(kind) {
 $('data-drawer').hidden=false;$('drawer-title').textContent=kind==='forecast'?'六區一週預報':'篩選與資料';
 $('forecast-panel').hidden=kind!=='forecast';$('tools-panel').hidden=kind!=='tools';
 if(kind==='forecast'){setLayer('forecast');renderForecast();setTimeout(()=>chart?.resize(),50);}
 else if(state.layer==='forecast')setLayer('temperature');
}
function populateCounties() {
 const previous=$('county').value;
 const names=[...new Set([...state.stations,...(state.products.rainfall?.stations||[])].map(s=>s.county).filter(Boolean))].sort();
 $('county').replaceChildren(new Option('全台灣','ALL'),...names.map(n=>new Option(n,n)));
 if(names.includes(previous))$('county').value=previous;
}
async function loadStations(force) {
 try {const data=await getJson('/api/temperature/latest?refresh='+force);state.latest=data;if(!state.historical)state.stations=data.stations;populateCounties();}
 catch(_){if(state.latest)state.latest.stale=true;}
 capabilityButtons();renderMap();
}
async function loadForecast(force) {
 try {state.forecast=await getJson('/api/forecasts/chart?refresh='+force);options($('forecast-date'),state.forecast.dates);state.forecastDate=$('forecast-date').value;}
 catch(_){if(state.forecast)state.forecast.stale=true;}
 renderForecast();if(state.layer==='forecast')renderMap();
}
async function loadProduct(name,force) {
 if(!state.capabilities.supported[name])return;
 try {
   const data=await getJson('/api/weather/'+name+'?refresh='+force);state.products[name]=data;
   if(name==='rainviewer')state.radarIndex=Math.max(0,(data.frames?.length||1)-1);
   if(name==='typhoon') {
     const storms=data.typhoons||[];$('storm-select').replaceChildren(...storms.map((s,i)=>new Option(s.name,String(i))));
     state.stormIndex=Math.min(state.stormIndex,Math.max(0,storms.length-1));$('storm-select').value=String(state.stormIndex);
     state.stormTime=Math.max(0,(storms[state.stormIndex]?.analysis.length||1)-1);
     if(needsStormFit&&storms.length){weatherMap.fitStorms(storms);needsStormFit=false;}
   }
 } catch(_){if(state.products[name])state.products[name].stale=true;}
 if(name==='rainfall')populateCounties();
 capabilityButtons();renderWarnings();renderTimeline();renderMap();
}
async function loadHistory() {
 try {
   state.snapshots=(await getJson('/api/temperature/history')).snapshots.reverse();
   $('history-range').disabled=!state.snapshots.length;$('history-range').max=Math.max(0,state.snapshots.length-1);
   if(!state.historical){$('history-range').value=$('history-range').max;$('history-label').textContent=`${state.snapshots.length} 份快照，保留最近 7 天。`;}
 } catch(_){$('history-label').textContent='歷史資料暫時無法取得。';}
}
async function refresh(force=false) {
 if(busy)return;busy=true;$('refresh').disabled=true;
 try {await Promise.allSettled([loadStations(force),loadForecast(force),...['rainfall','warnings','radar','rainviewer','typhoon','gfs_wind'].map(n=>loadProduct(n,force))]);await loadHistory();}
 finally{busy=false;$('refresh').disabled=false;}
}
function setup() {
 options($('forecast-region'),Object.keys(regions),state.region);
 document.querySelectorAll('[data-layer]').forEach(b=>b.onclick=()=>setLayer(b.dataset.layer));
 document.querySelectorAll('[data-base]').forEach(b=>b.onclick=()=>{weatherMap.setBase(b.dataset.base);document.querySelectorAll('[data-base]').forEach(x=>x.classList.toggle('active',x===b));});
 $('boundaries').onchange=()=>weatherMap.setBoundaries($('boundaries').checked);
 $('labels').onchange=()=>{state.labels=$('labels').checked;renderMap();};
 $('wind-arrows').onchange=()=>{state.windArrows=$('wind-arrows').checked;renderMap();};
 $('forecast-open').onclick=()=>openDrawer('forecast');$('tools-open').onclick=()=>openDrawer('tools');
 $('drawer-close').onclick=()=>{$('data-drawer').hidden=true;if(state.layer==='forecast')setLayer('temperature');};
 $('forecast-region').onchange=()=>{state.region=$('forecast-region').value;renderForecast();renderMap();};
 $('forecast-date').onchange=()=>{state.forecastDate=$('forecast-date').value;renderForecast();renderMap();};
 $('county').onchange=renderMap;$('search').oninput=renderMap;
 $('refresh').onclick=()=>refresh(true);$('home').onclick=()=>weatherMap.home();
 $('locate').onclick=()=>weatherMap.locate(()=>note('已定位'),()=>note('無法取得位置，請確認瀏覽器定位權限。'));
 $('auto-refresh').onchange=()=>{clearInterval(timer);if($('auto-refresh').checked)timer=setInterval(()=>refresh(),300000);};$('auto-refresh').onchange();
 $('warnings-toggle').onclick=()=>{const hidden=!$('warning-items').hidden;$('warning-items').hidden=hidden;$('warnings-toggle').textContent=hidden?'展開':'收合';$('warnings-toggle').setAttribute('aria-expanded',String(!hidden));};
 for(const [button,panel,other] of [['toggle-info','info-panel','layer-panel'],['toggle-layers','layer-panel','info-panel']])$(button).onclick=()=>{$(panel).classList.toggle('mobile-open');$(other).classList.remove('mobile-open');$(button).setAttribute('aria-expanded',String($(panel).classList.contains('mobile-open')));};
 $('radar-source').onchange=()=>{state.radarSource=$('radar-source').value;renderTimeline();renderMap();};
 $('radar-range').oninput=()=>{state.radarIndex=Number($('radar-range').value);renderTimeline();renderMap();};
 $('storm-select').onchange=()=>{state.stormIndex=Number($('storm-select').value);state.stormTime=state.products.typhoon.typhoons[state.stormIndex].analysis.length-1;renderTimeline();renderMap();};
 $('storm-range').oninput=()=>{state.stormTime=Number($('storm-range').value);renderTimeline();renderMap();};
 $('history-range').oninput=async()=>{
   const captured=state.snapshots[Number($('history-range').value)]?.captured_at;if(!captured)return;
   const sequence=++historySequence;
   try {const data=await getJson('/api/temperature/snapshot?at='+encodeURIComponent(captured));if(sequence!==historySequence)return;state.historical=captured;state.stations=data.stations;$('history-label').textContent=formatTime(captured);populateCounties();setLayer('temperature');}
   catch(_){$('history-label').textContent='無法讀取此快照。';}
 };
 $('history-live').onclick=()=>{++historySequence;state.historical=null;state.stations=state.latest?.stations||[];populateCounties();loadHistory();renderMap();};
 $('sql-run').onclick=async()=>{try {const data=await getJson('/api/forecasts/sql-query?query='+encodeURIComponent($('sql-query').value));$('sql-result').textContent=`${data.count} 筆（上限 ${data.limit}）\n`+JSON.stringify(data.results,null,2);}catch(_){$('sql-result').textContent='查詢失敗：僅允許有效的 SELECT，最多 500 筆。';}};
 if(window.Chart)chart=new Chart($('forecast-chart'),{type:'line',data:{labels:[],datasets:[{label:'最高溫 °C',data:[],borderColor:'#f78d79',tension:.25},{label:'最低溫 °C',data:[],borderColor:'#67c6ed',tension:.25}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#c8d2e3'}}},scales:{x:{ticks:{color:'#94a3b8',font:{size:10}}},y:{ticks:{color:'#94a3b8'}}}}});
}
async function init() {
 try {
   state.capabilities=await getJson('/api/weather/capabilities');
   weatherMap=new WeatherMap(state.capabilities,()=>renderMap());setup();capabilityButtons();
   if(state.capabilities.supported.boundaries)weatherMap.setBoundaries(true);
   await refresh();
 } catch(_){$('connection-badge').textContent='連線失敗';note('無法載入地圖或資料服務，請確認網路後重新整理。');}
}
init();
