# AloT_L3_CWA_HW1

台灣即時氣象地圖，整合中央氣象署測站、雨量、雷達、颱風、警特報與六區一週預報，並提供 NOAA GFS 風場模型。介面以 [taiwan-weather-map.vercel.app](https://taiwan-weather-map.vercel.app) 的全螢幕地圖、浮動摘要與圖層控制方式為參考。

所有外部來源先以 probe 驗證 HTTP、資料格式、圖片或 GRIB 解碼；只啟用已驗證的功能。網站直接使用官方／供應者來源，不依賴參考網站的私人後端。

![台灣氣象地圖](assets/preview.png)

[查看各功能電腦版截圖](#電腦版功能截圖)

## 快速啟動

建議 Python 3.11+。從專案根目錄執行：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

在 `.env` 設定自己的 `CWA_API_KEY`，再執行：

```bash
python scripts/probe_apis.py
./start_server.sh
```

開啟 **http://127.0.0.1:8000**。Windows 啟用虛擬環境後執行 `start_server.bat`，或使用跨平台指令：

```bash
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

不需要 Streamlit、npm build 或 Windy key。背景更新可能需要數秒，介面會逐項顯示已取得的資料。

## 單一專案結構

```text
AloT_L3_CWA_HW1/
├── backend/app/
│   ├── main.py             # FastAPI 與背景更新
│   ├── config.py           # 環境設定
│   ├── sources.py          # API 來源與能力清單讀取
│   ├── database.py         # SQLite 資料存取
│   ├── routers/            # API 路由
│   └── services/           # 觀測、預報、雷達、颱風、風場解析／快取
├── frontend/
│   ├── index.html          # 地圖與浮動面板
│   ├── css/style.css
│   └── js/
│       ├── app.js          # 頁面狀態與互動
│       ├── api.js          # 請求、格式與共用資料
│       ├── map.js          # 地圖圖層
│       └── wind.js         # GFS 取樣與粒子視覺化
├── scripts/probe_apis.py   # 可重跑的來源實測
├── config/api_capabilities.json
├── tests/                  # 離線測試與瀏覽器 smoke test
├── docs/                   # 架構、API、驗證、遷移與 probe 報告
├── assets/                 # README 截圖
├── data/                   # 執行資料，不提交 Git
│   ├── weather.db          # 唯一運作中的 SQLite
│   ├── cache/              # 雷達影像快取
│   └── archive/            # 本機舊版備份
├── .env                    # 本機金鑰，不提交 Git
├── requirements.txt        # 執行依賴的唯一清單
├── requirements-dev.txt
├── start_server.sh
└── start_server.bat
```

舊版根目錄與巢狀儲存庫已合併，不再保留第二套可執行網站。Git 歷史保留；舊版程式、Notebook、設定及資料的本機備份放在 `data/archive/`，不會上傳 GitHub。見 [遷移紀錄](docs/migration.md)。

## 功能與來源

| 功能 | 已驗證來源 | 呈現方式 |
|---|---|---|
| 氣溫、濕度、天氣、測站 | CWA `O-A0001-001`、`O-A0003-001` | 圓點、數字與天氣圖示；Popup 顯示觀測時間 |
| 本日累積雨量 | CWA `O-A0002-001` | 獨立雨量測站圖層，缺值不當作零 |
| 即時雷達 | CWA `O-A0058-006` | 依官方經緯度範圍疊加透明 PNG |
| 雷達歷程 | RainViewer | 已驗證圖磚的過去影格與時間滑桿 |
| 颱風／熱帶低壓 | CWA `W-C0034-005` | 分析／預報路徑、時間滑桿及來源提供的機率／風圈半徑 |
| 風速風向 | NOAA GFS 10 m U/V、CWA 測站 | 模型粒子動畫＋測站風向箭頭，分別標示時間 |
| 官方天氣特報 | CWA `W-C0033-002` | 只顯示尚未到期的公告，區分生效中與即將生效 |
| 縣市界線 | 國土測繪中心 CITY WMTS | 官方圖磚疊圖 |
| 深色／街道底圖 | Esri／OpenStreetMap | 已驗證圖片回應 |
| 六區一週預報 | CWA `F-C0032-003` | 地區／日期選單、七天圖表、表格與 CSV |

此外保留測站搜尋、縣市篩選、最高／最低溫、最大雨量／風速摘要、瀏覽器定位、歷史觀測快照、唯讀 SQL 與手機面板。

**已取消**：未取得有效授權並完成驗證的 Windy 分支，以及原先名稱與資料不符的海圖「風場」。本版沒有假氣象圖層或等待使用者補 key 的空按鈕。

氣溫等圓點與標籤表示實際測站值，沒有將測站值冒充連續氣象模型。GFS 粒子動畫是加速視覺化，並非實際物件移動軌跡；箭頭表示風吹往的方向，Popup 另列氣象風向的來向角度。颱風圈只使用官方提供的半徑，不自行捏造預測錐。

## 電腦版功能截圖

以下為電腦版實際操作畫面，資料以截圖當下為準。

### 氣溫總覽與天氣特報

![氣溫總覽與天氣特報](assets/features/01-overview.png)

### 一週預報

![一週預報](assets/features/forecast-chart.png)

### 六區預報表格與 CSV 下載

![六區預報表格與 CSV 下載](assets/features/forecast-table-csv.png)

### 雨量

![雨量](assets/features/layer-rainfall.png)

### 即時雷達

![即時雷達](assets/features/radar-current.png)

### 雷達歷程

![雷達歷程](assets/features/radar-history.png)

### 颱風路徑與預報

![颱風路徑與預報](assets/features/typhoon.png)

### 風速風向

![風速風向](assets/features/layer-wind.png)

### 濕度

![濕度](assets/features/layer-humidity.png)

### 天氣

![天氣](assets/features/layer-weather.png)

### 測站點位

![測站點位](assets/features/layer-stations.png)

### 測站詳細資料

![測站詳細資料](assets/features/station-details.png)

### 縣市篩選與測站搜尋

![縣市篩選與測站搜尋](assets/features/station-filter.png)

### 觀測 CSV 下載與自動刷新

![觀測 CSV 下載與自動刷新](assets/features/data-tools.png)

### 歷史觀測

![歷史觀測](assets/features/observation-history.png)

### 唯讀 SQL 查詢

![唯讀 SQL 查詢](assets/features/sql-query.png)

### 街道底圖

![街道底圖](assets/features/street-map.png)

### 數字標籤與縣市界線切換

![數字標籤與縣市界線切換](assets/features/map-controls.png)

## API probe

```bash
python scripts/probe_apis.py
```

輸出至 `config/api_capabilities.json` 與 [API probe 報告](docs/reports/api-probe.md)。無活動颱風或無警報表示當下沒有事件，不代表 API 不支援。HTTP 200 若回傳錯誤 HTML、缺少必要欄位或無法解碼，仍不算通過。

修改能力清單後重新啟動服務。探測結果代表當下可用性；執行時仍檢查資料回應並標示過期快取。金鑰不會輸出到探測報告。

## 更新、快取與設定

後端啟動後抓取，觀測與預報每 10 分鐘更新；GFS 最多每小時重新取得一次。前端每 5 分鐘刷新，可手動更新。成功更新的測站快照保留七天；歷史資料從開始使用後才累積。更新失敗保留原成功時間，不會把舊資料偽裝成新資料。

| 變數 | 用途 |
|---|---|
| `CWA_API_KEY` | 必填，僅後端使用 |
| `CACHE_TTL_SECONDS` | 預設 600，最小 60 秒 |
| `BACKGROUND_REFRESH` | 預設 true，測試時可關閉 |
| `DATABASE_PATH` | 預設專案內 `data/weather.db` |

先讀根目錄 `.env`，既有環境變數優先。請勿提交 `.env`、資料庫或備份。

## 驗證與文件

```bash
pip install -r requirements-dev.txt
python -m pytest tests -q
```

[驗證紀錄](docs/validation.md)包含瀏覽器實測範圍。更多內容：[架構](docs/architecture.md)、[API 路徑](docs/api.md)、[進度](docs/roadmap.md)。GitHub Actions 執行離線後端測試與前端模組語法檢查。

GitHub 儲存庫負責版本管理，不會自動部署公開網站；FastAPI 需要持續運作的 Python 服務及持久化磁碟。本版未整合 Redis 或 PostgreSQL，採單程序 SQLite 部署。
