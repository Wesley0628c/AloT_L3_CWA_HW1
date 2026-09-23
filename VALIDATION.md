# 驗證紀錄

日期：2026-09-23。以下為本機實測，並非正式雲端部署驗收。

## 自動測試

- `python -m pytest tests -q`：20 passed。
- `node --check frontend/js/app.js`：通過。
- 使用暫存 SQLite 與模擬 CWA 回應，驗證預報範圍、並行更新、缺值、快取、背景排程、重啟備援、歷史保留、SQL 限制、CSV 與 HTTP 路由。

## 實際 CWA 資料

- 取得 835 個有效觀測站（兩資料來源均成功）。
- 取得六區 × 七天，共 42 筆預報。
- 預報日期：2026-09-23 至 2026-09-29。
- 最新觀測與預報均回報 `stale=false`、`partial=false`。
- 測站數與預報值會隨 CWA 更新改變，不是固定範例資料。

## Chromium 瀏覽器

已驗證：

- 全台測站呈現、臺北市篩選、無搜尋結果狀態。
- 測站標籤、熱力圖、聚類模式切換。
- 六區預報切換、七天圖表與資料表、當日六區總覽。
- 所選地區預報 CSV 實際下載。
- SQL SELECT 回傳 42 筆預報的計數。
- 歷史快照切換與返回最新觀測。
- 桌面 1440×1000、手機 390×844 畫面；無水平溢出。
- 瀏覽器未出現 JavaScript page error。
- 實際查看截圖，確認底圖可用，手機面板不被地圖控制項蓋住。

截圖：`assets/preview.png`（測站）、`assets/forecast.png`（預報）。

可在已啟動且有完整 CWA 資料的網站上重跑：

```bash
pip install playwright
python -m playwright install chromium
python tests/browser_smoke.py
```

預設測試網址為 `http://127.0.0.1:8000`，可用 `CWA_TEST_URL` 覆寫。此 smoke test 需要外部地圖／圖表 CDN 與完整七天資料；不屬於離線 CI 測試。截圖輸出至忽略提交的 `artifacts/`。

## 驗證限制

- 未提供 Windy Map Forecast key，未實際驗證 Windy 授權與模型圖層；一般 Leaflet 地圖已測試。
- 七天歷史保留以測試資料驗證；實際歷史從本次服務啟動後才開始累積。
- 未進行正式雲端部署或多實例負載測試。
