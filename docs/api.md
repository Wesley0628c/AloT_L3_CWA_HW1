# API 路徑

互動文件位於 `/docs`。所有路徑由同一 FastAPI 程式提供。

| 路徑 | 內容 |
|---|---|
| `/api/health` | 服務及觀測快取狀態 |
| `/api/weather/capabilities` | probe 通過的來源及底圖設定 |
| `/api/weather/rainfall` | 雨量測站 |
| `/api/weather/warnings` | 尚未到期的 CWA 特報 |
| `/api/weather/typhoon` | 有效熱帶氣旋、分析與預報位置 |
| `/api/weather/radar` | 官方雷達時間、範圍及本機圖片路徑 |
| `/api/weather/radar/image` | 經驗證的雷達 PNG |
| `/api/weather/rainviewer` | 已驗證來源的歷史雷達圖磚清單 |
| `/api/weather/gfs_wind` | GFS 10 m U/V 規則格點、批次及有效時間 |
| `/api/temperature/latest` | 最新測站觀測 |
| `/api/temperature/geojson` | 測站 GeoJSON |
| `/api/temperature/stations/{station_id}` | 單站觀測 |
| `/api/temperature/export/csv` | 最新測站 CSV |
| `/api/temperature/history` | 最近七天快照索引，最多 1008 份 |
| `/api/temperature/snapshot?at=...` | 指定時間快照 |
| `/api/forecasts/regions` | 六大地區 |
| `/api/forecasts/chart?region=中部地區` | 今天起七天預報 |
| `/api/forecasts/table` | 同一預報資料 |
| `/api/forecasts/export/csv?region=中部地區` | 所選地區預報下載 |
| `/api/forecasts/sql-query?query=SELECT...` | 唯讀 SQL |

更新產品／預報／觀測可加 `refresh=true`。`updated_at` 是最後成功取得時間；`observed_at` 或 `valid_at` 才是產品觀測／模型有效時間。`available=false` 表示沒有可用資料，`stale=true` 表示更新失敗或資料過期。特報／颱風的 `count=0` 是有效的無事件結果，不能當成請求失敗。
