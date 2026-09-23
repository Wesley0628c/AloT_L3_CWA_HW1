# 📋 專案代辦事項與開發藍圖 (TODO List & Roadmap)

本代辦事項清單依據 `design.md` 之系統架構規劃，已完整實現 Phase 1 至 Phase 4 所有功能與需求。

---

## ✅ Phase 1: MVP 核心最小可行性產品 (100% 已完成)

- [x] **1. 後端 (FastAPI + CWA API 串接層)**
  - [x] 1.1 建立 FastAPI 專案目錄架構 (`backend/app/...`)
  - [x] 1.2 設定 `config.py` 與 `.env` 環境變數管理 (`CWA_API_KEY`, `CACHE_TTL_SECONDS`)
  - [x] 1.3 實作 `cwa_client.py`：對接中央氣象署 OpenData API 擷取 823 個自動氣象站資料
  - [x] 1.4 實作數據清洗與驗證邏輯 (過濾缺值 `-99`/`-999`、座標缺失或異常氣溫 `-20°C~50°C`)
  - [x] 1.5 定義 Pydantic Data Model (`StationTemperature`)
  - [x] 1.6 開放 API 端點 `GET /api/temperature/latest` (回傳標準化 JSON)
  - [x] 1.7 開放 GeoJSON API 端點 `GET /api/temperature/geojson`
  - [x] 1.8 實作基礎記憶體快取 (Memory Cache)，避免頻繁請求 CWA API
  - [x] 1.9 開放 API 健康檢查端點 `GET /api/health`

- [x] **2. 前端 (HTML5 / JS + Leaflet CWA 視覺化地圖)**
  - [x] 2.1 建立前台視覺化頁面與深色玻璃擬態介面 (`frontend/...`)
  - [x] 2.2 引入 Leaflet 1.9.4 與高畫質無浮水印地圖圖層 (`Esri World Dark Gray Canvas`)
  - [x] 2.3 初始化地圖並定位至台灣 (Lat: 23.7, Lon: 120.95, Zoom: 8)
  - [x] 2.4 實作 `LayerGroup` 與圓形測站標籤 (顯示全台 800+ 測站即時氣溫)
  - [x] 2.5 實作 `colorScale.js`：根據氣溫區間（<10°C 至 >35°C）提供漸層顏色對應
  - [x] 2.6 實作測站詳細 Popup：點擊顯示測站名稱、縣市、鄉鎮、氣溫、相對濕度、風速、雨量與觀測時間
  - [x] 2.7 實作 `TemperatureLegend`：畫面右下角顯示氣溫色階圖例
  - [x] 2.8 畫面頂部顯示「最新 CWA 氣象資料更新時間」與線上測站總數

---

## ✅ Phase 2: Dashboard 儀表板與互動功能增強 (100% 已完成)

- [x] **3. 前端互動與控制介面**
  - [x] 3.1 實作背景圖層切換器：支援即時切換 **風速 (Wind)**、**氣溫 (Temp)**、**降雨 (Rain)**、**雲層 (Clouds)** 4 種氣象圖層
  - [x] 3.2 新增「開關 CWA 測站標籤/數值」切換開關 (Zoom in 自動顯示)
  - [x] 3.3 新增「5分鐘自動重新整理」機制與「手動更新」按鈕
  - [x] 3.4 新增 22 縣市區域篩選下拉選單 (County Filter)
  - [x] 3.5 新增測站名稱關鍵字搜尋框 (Station Search)
  - [x] 3.6 實作全台即時最高溫測站 Top 5 排行榜側邊欄

- [x] **4. 後端健壯性增強**
  - [x] 4.1 實作 CWA API 雙數據源備援 (`O-A0001-001` 自動站 + `O-A0003-001` 局屬站)
  - [x] 4.2 實作 CWA API 斷線/異常時的快取降級處理 (Stale Cache Fallback)
  - [x] 4.3 提供 `start_server.bat` 腳本實現 Windows 雙擊一鍵啟動

---

## ✅ Phase 3: 高級視覺化與進階發展藍圖 (100% 已完成)

- [x] **5. 進階圖層與數據呈現**
  - [x] 5.1 實作熱力圖模式 (Heatmap Overlay Layer)：整合 `Leaflet.heat` 根據全台測站氣溫內插生成動態氣溫熱力圖
  - [x] 5.2 實作測站聚類模式 (Marker Cluster Mode)：整合 `Leaflet.markercluster` 實現高效能大量測站聚類與平滑縮放
  - [x] 5.3 實作氣溫特報監測 Warning 燈箱：動態偵測並顯示 ≥33°C 極端高溫與 ≤15°C 低溫警報測站
  - [x] 5.4 實作 3 模式視覺化切換按鈕 (`📍 測站標籤` / `🔥 氣溫熱力圖` / `🧩 測站聚類`)
  - [x] 5.5 實作手機與行動裝置 RWD 側邊欄收合按鈕 (`☰`)

---

## ✅ Phase 4: Production 數據匯出與架構優化 (100% 已完成)

- [x] **6. 數據匯出與整合**
  - [x] 6.1 開放 `GET /api/temperature/export/csv` 下載全台氣象測站即時觀測資料 (CSV 格式)
  - [x] 6.2 頂部導覽列新增「📥 匯出 CSV」一鍵下載按鈕
  - [x] 6.3 提供 FastAPI 全套模組自動初始化與全域跨域 (CORS) 存取支援
