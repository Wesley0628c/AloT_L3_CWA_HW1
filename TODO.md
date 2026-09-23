# 📋 專案代辦事項與開發藍圖 (TODO List & Roadmap)

本代辦事項清單依據 `design.md` 之系統架構規劃，分為 **Phase 1 (MVP Minimum Viable Product)** 至 **Phase 4 (Production Ready)** 四個階段。

---

## 🎯 Phase 1: MVP 核心最小可行性產品

- [ ] **1. 後端 (FastAPI + CWA API 串接層)**
  - [ ] 1.1 建立 FastAPI 專案基本目錄架構 (`backend/app/...`)
  - [ ] 1.2 設定 `config.py` 與 `.env` 環境變數管理 (`CWA_API_KEY`, `CACHE_TTL_SECONDS`)
  - [ ] 1.3 實作 `cwa_client.py`：對接中央氣象署 OpenData API 擷取自動氣象站即時資料
  - [ ] 1.4 實作數據清洗與驗證邏輯 (過濾缺值 `-99`/`-999`、座標缺失或異常氣溫 `-20°C~50°C`)
  - [ ] 1.5 定義 Pydantic Data Model (`StationTemperature`)
  - [ ] 1.6 開放 API 端點 `GET /api/temperature/latest` (回傳標準化 JSON)
  - [ ] 1.7 開放 GeoJSON API 端點 `GET /api/temperature/geojson`
  - [ ] 1.8 實作基礎記憶體快取 (Memory Cache)，避免頻繁請求 CWA API
  - [ ] 1.9 開放 API 健康檢查端點 `GET /api/health`

- [ ] **2. 前端 (React / Next.js + Windy API + Leaflet 視覺化)**
  - [ ] 2.1 初始化 Next.js / Vite + React + TypeScript 專案 (`frontend/...`)
  - [ ] 2.2 引入 Leaflet 1.4.x 與 Windy Map Forecast API 腳本 (`libBoot.js`)
  - [ ] 2.3 實作 `WindyMap.tsx` 元件：初始化 Windy 地圖並定位至台灣 (Lat: 23.7, Lon: 121.0, Zoom: 7)
  - [ ] 2.4 實作 `TemperatureLayer.tsx`：利用 Leaflet `LayerGroup` 與 `L.circleMarker` 繪製氣象站圖層
  - [ ] 2.5 實作 `colorScale.ts`：根據氣溫區間（<10°C 至 >35°C）提供漸層顏色對應
  - [ ] 2.6 實作 `StationPopup.tsx`：點擊測站顯示 測站名稱、縣市、鄉鎮、氣溫、濕度、風速與觀測時間
  - [ ] 2.7 實作 `TemperatureLegend.tsx`：畫面右下角顯示氣溫色階圖例
  - [ ] 2.8 畫面頂部顯示「最新 CWA 氣象資料更新時間」

---

## 🚀 Phase 2: Dashboard 儀表板與互動功能增強

- [ ] **3. 前端互動與控制介面**
  - [ ] 3.1 實作 `LayerControlPanel.tsx`：支援切換 Windy 底圖（風場 wind、氣溫 temp、降雨 rain、雲層 clouds）
  - [ ] 3.2 新增「開關 CWA 測站標籤/數值」切換開關
  - [ ] 3.3 新增「自動重新整理」機制（前端每 5 分鐘自動刷新）與手動刷新按鈕
  - [ ] 3.4 新增縣市篩選下拉選單 (County Filter)
  - [ ] 3.5 新增測站名稱關鍵字搜尋框 (Station Search)
  - [ ] 3.6 支援顯示測站詳細資訊側邊欄 (Station Detail Panel)

- [ ] **4. 後端健壯性增強**
  - [ ] 4.1 加入 APScheduler 或 background job，每 10 分鐘自動對接 CWA API 更新快取
  - [ ] 4.2 實作 CWA API 斷線/異常時的降級處理 (Stale Cache Fallback)

---

## 🎨 Phase 3: 高級視覺化與分析功能

- [ ] **5. 進階圖層與數據呈現**
  - [ ] 5.1 實作熱力圖模式 (Heatmap Overlay Layer) 呈現全台氣溫場分佈
  - [ ] 5.2 大量測站優化：引入 `Leaflet.markercluster` 或 Canvas 渲染提升地圖效能
  - [ ] 5.3 氣溫警報閾值高亮（高溫特報/低溫特報動態閃爍標示）
  - [ ] 5.4 歷史氣溫時間軸滑桿 (Time Slider) 與回放功能
  - [ ] 5.5 手機與行動裝置 RWD 響應式介面優化

---

## 🛡️ Phase 4: Production 營運部署與營運監控

- [ ] **6. 安全與效能優化**
  - [ ] 6.1 後端引入 Redis 作為分散式快取
  - [ ] 6.2 引入 PostgreSQL / PostGIS 儲存歷史測站氣象數據
  - [ ] 6.3 設定 CORS 安全網域白名單與 API Rate Limiting 限制
  - [ ] 6.4 部署後端至 Render / Fly.io / Railway 或自建 Docker 容器
  - [ ] 6.5 部署前端至 Vercel / Netlify
  - [ ] 6.6 整合 Logging 與 Monitoring (Sentry / Prometheus)
