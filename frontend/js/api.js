export const $ = id => document.getElementById(id);
export const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const formatTime = value => value ? new Date(value).toLocaleString('zh-TW',{timeZone:'Asia/Taipei',hour12:false}) : '尚無資料';
export async function getJson(path) {
    const response = await fetch(path,{signal:AbortSignal.timeout(90000)});
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
}
export function options(select, values, preferred) {
    const previous=select.value || preferred;
    select.replaceChildren(...values.map(v => new Option(v,v)));
    if (values.includes(previous)) select.value=previous;
}
export const regions={'北部地區':[25.03,121.56],'中部地區':[24.15,120.68],'南部地區':[22.63,120.30],'東北部地區':[24.75,121.75],'東部地區':[23.99,121.61],'東南部地區':[22.75,121.15]};
