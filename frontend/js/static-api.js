// GitHub Pages adapter; the normal FastAPI website keeps its original endpoints.
const root = new URL('../', import.meta.url);
let pending, fetchedAt = 0;
async function snapshot() {
    if (!pending || Date.now() - fetchedAt > 30000) {
        fetchedAt = Date.now();
        pending = fetch(new URL('data/weather.json', root), {cache:'no-store', signal:AbortSignal.timeout(30000)})
            .then(r => {if (!r.ok) throw new Error('公開資料暫時無法讀取'); return r.json();})
            .catch(e => {pending = null; throw e;});
    }
    return structuredClone(await pending);
}
function dated(data) {
    return {...data, stale: Boolean(data.stale || (data.updated_at && Date.now()-Date.parse(data.updated_at)>3600000))};
}
function sqlQuery(query) {
    if (!/^SELECT\b/i.test(query.trim()) || query.length>4000) return Promise.reject(new Error('僅允許 SELECT 查詢（最多 4000 字）'));
    return new Promise((resolve,reject)=>{
        const worker = new Worker(new URL('./static-sql-worker.js',import.meta.url));
        const finish = (error,result) => {clearTimeout(timer);worker.terminate();error?reject(new Error(error)):resolve(result);};
        const timer = setTimeout(()=>finish('查詢超時，請縮小查詢範圍'),10000);
        worker.onmessage = e=>finish(e.data.error,e.data.result);
        worker.onerror = ()=>finish('SQL 引擎載入失敗');
        worker.postMessage({query, database:new URL('data/forecasts.sqlite',root).href});
    });
}
export async function staticJson(path) {
    const url = new URL(path,location.origin);
    if (url.pathname==='/api/forecasts/sql-query') return sqlQuery(url.searchParams.get('query')||'');
    const data = await snapshot();
    switch (url.pathname) {
        case '/api/weather/capabilities': return data.capabilities;
        case '/api/temperature/latest': return dated(data.latest);
        case '/api/temperature/history': return data.history;
        case '/api/temperature/snapshot': {
            const row = data.history.snapshots.find(s=>s.captured_at===url.searchParams.get('at'));
            if (!row) throw new Error('找不到此觀測快照');
            const response = await fetch(new URL(row.file,root));
            if (!response.ok) throw new Error('歷史快照無法讀取');
            return {...await response.json(),historical:true};
        }
        case '/api/forecasts/regions': return {regions:[...new Set(data.forecast.forecasts.map(r=>r.regionName))]};
        case '/api/forecasts/chart':
        case '/api/forecasts/table': return dated(data.forecast);
        default: {
            const product = data.products[url.pathname.replace('/api/weather/','')];
            if (!product) throw new Error('不支援的公開資料');
            if (product.warnings) {
                product.warnings=product.warnings.filter(w=>Date.parse(w.ends_at)>Date.now());
                for (const w of product.warnings) w.active=!w.starts_at||Date.parse(w.starts_at)<=Date.now();
                product.count=product.warnings.length;
            }
            if (product.typhoons) {
                product.typhoons=product.typhoons.filter(s=>Date.now()-Date.parse(s.current.time)<86400000);
                product.count=product.typhoons.length;
            }
            return dated(product);
        }
    }
}
if (window.CWA_STATIC) document.addEventListener('click',event=>{
    const link=event.target.closest('a[href]');
    if (!link) return;
    const url=new URL(link.href);
    let file,filename;
    if (url.pathname==='/api/forecasts/export/csv') {
        file='forecast-'+(url.searchParams.get('region')||'ALL')+'.csv';filename='weekly_forecasts.csv';
    } else if (url.pathname==='/api/temperature/export/csv') {
        file='stations.csv';filename='cwa_temperatures.csv';
    } else return;
    event.preventDefault();
    const download=document.createElement('a');
    download.href=new URL('data/'+encodeURIComponent(file),root);download.download=filename;
    document.body.append(download);download.click();download.remove();
});
