import {escapeHtml as e,formatTime,regions} from './api.js';
import {WindParticles} from './wind.js';
export const palettes={
 temperature:{stops:[5,10,15,20,24,28,32,36],colors:['#246a9a','#398fc1','#77c6d4','#b6dfd8','#f9e6a0','#ffbf77','#f98246','#da352f'],unit:'°C'},
 rainfall:{stops:[0,1,5,10,20,40,80,130],colors:['#8fa1b6','#96dafb','#62bae3','#3c94d5','#3265c5','#7965d3','#ba62ca','#ed5384'],unit:'mm'},
 humidity:{stops:[0,40,60,75,90,100],colors:['#e3d39b','#aad9c8','#64bed4','#3498d0','#4d68bc','#805dc2'],unit:'%'},
 wind:{stops:[0,2,5,8,11,14,17],colors:['#b3d9df','#7ecbd4','#55bdd6','#3e99c0','#ead676','#f3a268','#e56869'],unit:'m/s'},
};
export function colorFor(mode,value) {
 const p=palettes[mode] || palettes.temperature;
 let i=p.stops.findIndex(x=>value<x)-1;if(i===-2)i=p.stops.length-1;if(i<0)i=0;
 return p.colors[i];
}
const weatherIcon=s=>/雷/.test(s)?'⛈️':/雨/.test(s)?'🌧️':/霧|靄/.test(s)?'🌫️':/陰/.test(s)?'☁️':/多雲/.test(s)?'⛅':/晴/.test(s)?'☀️':'·';
export function popup(s) {
 const m=(v,u)=>v==null?'無資料':`${e(v)} ${u}`;
 return `<div class="popup"><h3>${e(s.station_name)} <small>${e(s.station_id)}</small></h3><p>${e(s.county)} ${e(s.town)}</p><strong>${m(s.temperature_c,'°C')}</strong><dl><dt>本日累積雨量</dt><dd>${m(s.precipitation_mm,'mm')}</dd><dt>相對濕度</dt><dd>${m(s.humidity_percent,'%')}</dd><dt>風速</dt><dd>${m(s.wind_speed_mps,'m/s')}</dd><dt>風向（來向）</dt><dd>${m(s.wind_direction_deg,'°')}</dd><dt>天氣</dt><dd>${e(s.weather)||'無資料'}</dd></dl><small>觀測：${formatTime(s.observed_at)}</small></div>`;
}
export class WeatherMap {
 constructor(config,onMove) {
    this.map=L.map('map',{center:[23.65,121],zoom:8,zoomControl:false,preferCanvas:true,minZoom:4});
    L.control.zoom({position:'bottomleft'}).addTo(this.map);
    this.tiles=config.map_tiles;this.group=L.layerGroup().addTo(this.map);this.setBase('dark');
    this.map.on('moveend',onMove);this.error=null;
 }
 setBase(name) {
    if(this.base)this.map.removeLayer(this.base);
    const url=this.tiles[name];
    this.base=L.tileLayer(url,{maxZoom:18,attribution:name==='dark'?'Tiles © Esri — Esri, DeLorme, NAVTEQ':'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}).addTo(this.map);
 }
 setBoundaries(show) {
    if(this.boundaries)this.map.removeLayer(this.boundaries);
    if(show)this.boundaries=L.tileLayer(this.tiles.boundaries,{maxZoom:18,opacity:.65,attribution:'縣市界 © 內政部國土測繪中心'}).addTo(this.map);
 }
 clear(){this.group.clearLayers();if(this.wind){this.wind.remove();this.wind=null;}}
 render(state,points) {
    this.clear();const mode=state.layer;
    if(mode==='forecast') {this.forecast(state);return;}
    if(mode==='radar') {this.radar(state);return;}
    if(mode==='typhoon') {this.typhoons(state);return;}
    if(mode==='wind' && !state.historical && state.products.gfs_wind?.available && !window.matchMedia('(prefers-reduced-motion:reduce)').matches) this.wind=new WindParticles(this.map,state.products.gfs_wind);
    const metric={temperature:'temperature_c',rainfall:'precipitation_mm',humidity:'humidity_percent',wind:'wind_speed_mps'}[mode];
    const eligible=points.filter(s=>metric ? Number.isFinite(s[metric]) : mode==='weather'?!!s.weather:true);
    const labels=new Set();
    const sorted=[...eligible].sort((a,b)=>Number(/^\d/.test(b.station_id))-Number(/^\d/.test(a.station_id)));
    for(const s of sorted) {
       const value=s[metric],color=metric?colorFor(mode,value):'#7bc5e4';
       const coord=[s.lat,s.lon];
       const dot=L.circleMarker(coord,{radius:mode==='stations'?5:3,color,weight:1,fillColor:color,fillOpacity:.85}).bindPopup(popup(s)).addTo(this.group);
       if(!this.map.getBounds().contains(coord))continue;
       const screen=this.map.latLngToContainerPoint(coord);
       const cell=`${Math.floor(screen.x/65)}:${Math.floor(screen.y/55)}`;
       if(labels.has(cell))continue;
       const labelWanted=mode==='weather' || (mode==='wind' && state.windArrows) || (['temperature','rainfall','humidity'].includes(mode)&&state.labels);
       if(!labelWanted)continue;
       labels.add(cell);
       let html;
       if(mode==='weather')html=`<div class="weather-label">${weatherIcon(s.weather)}<small>${e(s.station_name)}</small></div>`;
       else if(mode==='wind') {
         if(!Number.isFinite(s.wind_direction_deg))continue;
         html=`<div class="wind-label"><span style="transform:rotate(${s.wind_direction_deg+180}deg)">↑</span><small>${s.wind_speed_mps}</small></div>`;
       } else html=`<div class="value-label" style="--value-color:${color}">${Math.round(value)}${mode==='temperature'?'°':mode==='humidity'?'%':''}</div>`;
       L.marker(coord,{icon:L.divIcon({className:'map-label',html,iconSize:[40,26],iconAnchor:[20,13]})}).bindPopup(popup(s)).addTo(this.group);
    }
 }
 forecast(state) {
    for(const r of (state.forecast?.forecasts || []).filter(r=>r.dataDate===state.forecastDate)) {
       const color=colorFor('temperature',r.avgT);
       L.circleMarker(regions[r.regionName],{radius:r.regionName===state.region?17:12,color:'#fff',weight:2,fillColor:color,fillOpacity:.95}).bindPopup(`<b>${e(r.regionName)}</b><br>${r.dataDate}<br>最低 ${r.minT}°C／最高 ${r.maxT}°C`).addTo(this.group);
    }
 }
 radar(state) {
    if(state.radarSource==='history') {
       const frame=state.products.rainviewer?.frames?.[state.radarIndex];
       if(frame)L.tileLayer(frame.tiles,{opacity:.72,maxNativeZoom:7,maxZoom:18,attribution:'雷達 © RainViewer'}).addTo(this.group);
    } else {
       const data=state.products.radar;
       if(data?.available)L.imageOverlay(`${data.image_url}?t=${encodeURIComponent(data.updated_at)}`,data.bounds,{opacity:.72,attribution:'雷達 © 中央氣象署'}).addTo(this.group);
    }
 }
 typhoons(state) {
    const storms=state.products.typhoon?.typhoons || [];
    for(let n=0;n<storms.length;n++) {
       const storm=storms[n],past=storm.analysis.map(p=>[p.lat,p.lon]),future=[storm.current,...storm.forecast].map(p=>[p.lat,p.lon]);
       L.polyline(past,{color:'#cdd6e5',weight:2}).addTo(this.group);
       L.polyline(future,{color:'#ffb76a',weight:3,dashArray:'7 7'}).addTo(this.group);
       const all=[...storm.analysis,...storm.forecast];
       const selected=n===state.stormIndex?all[state.stormTime] || storm.current:storm.current;
       for(const p of all)L.circleMarker([p.lat,p.lon],{radius:p===selected?8:3,color:p.forecast?'#ffbc78':'#d7e3f0',fillOpacity:1}).bindPopup(`${e(storm.name)}<br>${p.forecast?'官方預報':'分析位置'}：${formatTime(p.time)}<br>${p.wind_mps ?? '—'} m/s・${p.pressure_hpa ?? '—'} hPa`).addTo(this.group);
       if(selected.uncertainty_km>0)L.circle([selected.lat,selected.lon],{radius:selected.uncertainty_km*1000,color:'#e2bd80',weight:1,fillOpacity:.08}).bindTooltip('官方 70% 機率半徑').addTo(this.group);
       for(const [field,color] of [['radius_15ms_km','#ffae6d'],['radius_25ms_km','#f17065']])if(selected[field]>0)L.circle([selected.lat,selected.lon],{radius:selected[field]*1000,color,weight:1,fillOpacity:.1}).addTo(this.group);
       L.marker([selected.lat,selected.lon],{icon:L.divIcon({className:'storm-marker',html:`🌀<span>${e(storm.name)}</span>`,iconSize:[150,36],iconAnchor:[18,18]})}).addTo(this.group);
    }
 }
 fitStorms(storms) {
    const points=[[25.3,121],[21.9,120.8],...storms.flatMap(s=>[...s.analysis,...s.forecast].map(p=>[p.lat,p.lon]))];
    this.map.fitBounds(points,{padding:[60,60],maxZoom:7});
 }
 home(){this.map.setView([23.65,121],8);}
 locate(success,failure){this.map.once('locationfound',e=>{L.circleMarker(e.latlng,{radius:8,color:'#fff',fillColor:'#1ca9e5',fillOpacity:1}).addTo(this.map).bindPopup('你的位置').openPopup();success();});this.map.once('locationerror',failure);this.map.locate({setView:true,maxZoom:12});}
}
