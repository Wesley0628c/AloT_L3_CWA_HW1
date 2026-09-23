# 專案合併紀錄

2026-09-23 將原本 `cwa_forecast/` 的 Streamlit 作業與其中的 `AloT_L3_CWA_HW1/` Git 儲存庫整併為單一專案，統一命名 `AloT_L3_CWA_HW1`。

- 保留原 Git 歷史及 GitHub remote。
- 前後端統一採用 FastAPI＋Leaflet，不再保留第二套 Streamlit 啟動入口。
- 原 `backend/data.db` 搬至 `data/weather.db`，保留已有資料表、預報與觀測快照。
- 根目錄只保留一份 `.env`、一份執行依賴清單與跨平台啟動腳本。
- 文件集中到 `docs/`，probe 工具集中到 `scripts/`，來源能力結果集中到 `config/`。
- 舊版完整程式、Notebook 與設定保存在本機 `data/archive/before-consolidation.tar.gz`；舊根目錄資料庫、JSON／CSV 亦保留於該 archive 目錄。
- 已淘汰的 gate/probe 作業腳本與靜態資料不再放在專案根目錄；可由備份或先前 Git 版本取回。
- `data/`、`.env`、虛擬環境與執行截圖皆不提交 GitHub。備份可能包含舊設定，因此保留為僅本機可讀資料。

新安裝會建立自己的空資料庫；完成 CWA key 設定後自動取回最新資料。舊快照保持原始時間，不會被重新標記成目前觀測。
