# 📋 專案代辦事項與開發藍圖 (TODO List & Roadmap)

本代辦事項清單依據 `design.md` 之系統架構規劃，記錄專案開發進度與後續藍圖。

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
  - [x] 2.2 引入 Leaflet 1.9.4 與高畫質無浮水印地圖圖層
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

## 🔮 Phase 3: 高級視覺化與進階發展藍圖 (待完成 / 進階規劃)

- [ ] **5. 進階圖層與數據呈現 (未完成項目)**
  - [ ] 5.1 熱力圖模式 (Heatmap Overlay Layer)：根據全台測站氣溫空間內插生成全台熱力分布場
  - [ ] 5.2 大量測站效能優化：引入 `Leaflet.markercluster` 進行聚類縮放
  - [ ] 5.3 氣溫警報高亮：針對 36°C 以上高溫特報區域觸發外框閃爍警報
  - [ ] 5.4 歷史氣溫時間軸滑桿 (Time Slider) 與 24 小時歷史氣溫播報回放
  - [ ] 5.5 手機與行動裝置 RWD 響應式佈局適配

---

## 🛡️ Phase 4: Production 營運部署與開源運營 (待完成 / 進階規劃)

- [ ] **6. 安全與營運部署 (未完成項目)**
  - [ ] 6.1 後端引入 Redis 分散式快取
  - [ ] 6.2 引入 PostgreSQL / PostGIS 儲存長期歷史氣象數據
  - [ ] 6.3 部署至 Vercel (前端) + Render / Fly.io / Railway (後端)
  - [ ] 6.4 設定 Sentry 錯誤監控與 API Rate Limiting 速率限制
