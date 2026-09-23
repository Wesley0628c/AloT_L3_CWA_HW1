# 驗證紀錄

日期：2026-09-23。以下為本機實測，並非正式雲端部署驗收。

## 自動測試

- `python -m pytest tests -q`：33 passed。
- 所有 `frontend/js/*.js` 通過 `node --input-type=module --check`。
- 測試使用暫存 SQLite 與模擬回應，不需要 CWA key 或外網。
- 涵蓋七天預報範圍、並行更新、零值／缺值、快取與重啟備援、歷史保留、SQL 限制、CSV、HTTP 路由。
- 新增雨量負值、警報有效時間、颱風路徑與時效、雷達來源白名單、RainViewer 影格、產品獨立快取、GRIB U/V 解碼與網格方向、GFS 跨日週期、HTTP 200 偽圖片拒絕等驗證。

## 實際來源 probe

12 個來源均通過 HTTP 與內容檢查，詳細時間、資料集與筆數見 [API probe 報告](reports/api-probe.md)。

- CWA 自動站與局屬站成功取得，瀏覽器合併去重後顯示 840 站。
- 六區 × 七天，共 42 筆預報。
- 雨量來源 1,342 站、活動熱帶系統 1 筆、未到期警報 0 筆。
- CWA 雷達 PNG 實際下載並驗證，3600 × 3600 像素。
- RainViewer 13 個過去影格，實際圖磚可讀。
- NOAA GFS 區域 GRIB 實際下載並解碼，141 × 89 格點的 10 m U/V 風場。
- Esri、OpenStreetMap、國土測繪中心縣市界線均實際取得圖片。

以上筆數會隨上游更新改變。零警報或零颱風是正常資料狀態，不代表來源不可用。未驗證授權的 Windy 整合已移除。

## Chromium 瀏覽器

已驗證八種圖層切換、風場粒子與控制項、CWA 雷達影像、RainViewer 歷程滑桿、颱風預報時間滑桿，以及：

- 臺北市篩選、測站搜尋與無搜尋結果狀態。
- 六區七天圖表／表格、當日六區總覽、CSV 實際下載。
- 唯讀 SQL 查詢得到 42 筆預報計數。
- 歷史快照切換與返回最新觀測。
- 桌面 1440 × 1000、手機 390 × 844；無水平溢出。
- 瀏覽器無 JavaScript page error。
- 人工查看底圖、風場與手機面板截圖；地圖縮放後等待圖磚完成載入再檢視。

截圖：`assets/preview.png`（地圖）、`assets/forecast.png`（預報）。

在已啟動且有完整即時資料的網站上重跑：

```bash
pip install playwright
python -m playwright install chromium
python tests/browser_smoke.py
```

預設網址 `http://127.0.0.1:8000`，可用 `CWA_TEST_URL` 覆寫。此 smoke test 需要外部圖磚／CDN、完整七天資料、歷史快照與至少一個有預報點的活動颱風／熱帶低壓；不屬於離線 CI。無活動系統時不適用其中的颱風互動斷言。截圖輸出至忽略提交的 `artifacts/`。

## 驗證範圍

- 七天歷史保留使用測試資料驗證，實際歷史從服務開始使用後累積。
- 氣溫等圖層表示測站量測值；GFS 為模型風場，兩者分別標示來源與時間。
- 尚未進行正式雲端部署或多實例負載測試。
