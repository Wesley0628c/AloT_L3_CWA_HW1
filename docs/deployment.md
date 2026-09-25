# GitHub Pages 公開部署

- Repository：https://github.com/Wesley0628c/AloT_L3_CWA_HW1
- Live Website：https://wesley0628c.github.io/AloT_L3_CWA_HW1/

## 架構

GitHub Pages 不執行 Python。GitHub Actions 使用既有 Python 服務取得資料，由 `scripts/build_pages.py` 匯出到 `dist/`，再透過官方 Pages Actions 發布。`dist/` 不提交 Git。

前端依公開版設定使用相對路徑讀取 JSON、雷達 PNG、CSV 與公開預報 SQLite，因此支援 `/AloT_L3_CWA_HW1/` 子路徑。SQL 使用 sql.js 1.13.0 在獨立 Worker 執行，僅允許 SELECT，最多 500 筆，超過 10 秒停止 Worker。公開預報庫僅包含 WeeklyForecasts，不複製本機資料庫。

## 更新

推送 main、手動執行 Publish weather map，或每小時第 7、17、27、37、47、57 分鐘排程觸發發布。GitHub 排程可能延遲；頁面保留資料來源時間，超過一小時未更新標為快取。頁面上的重新整理只讀取已發布資料，不觸發 GitHub 工作流程。

歷史資料透過 Actions cache 跨執行保留。公開輸出保留最近七天最多 168 份取樣快照；快取被清除後會重新累積。無可用觀測或預報時終止建置，保留上次成功的網站。

## GitHub 設定

1. Repository → Settings → Pages → Source 選 GitHub Actions。
2. Settings → Secrets and variables → Actions 中設定 `CWA_API_KEY` repository secret。
3. Actions → Publish weather map → Run workflow。

金鑰只存在 Secret 和建置程序環境，不寫入前端、JSON 或公開資料庫。匯出流程會掃描產物，若發現金鑰則拒絕發布。

## 本機驗證

```bash
python scripts/build_pages.py
python -m http.server 8011 --directory dist
```

正式發布前也需測試專案子路徑、預報 CSV、雷達圖片、SQL 與歷史快照。本機 FastAPI 的原有啟動方式不變。

參考：[GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)、[Pages Actions](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)、[sql.js](https://github.com/sql-js/sql.js)。
