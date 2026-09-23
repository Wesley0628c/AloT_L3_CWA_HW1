# API probe 實測結果

檢查時間：2026-09-23T12:37:44.609276+00:00

執行：`python scripts/probe_apis.py`。除了 HTTP 狀態，也檢查資料結構、影像位元組與 GRIB 風場解碼；無活動颱風／警報不等於 API 不支援。

| 來源 | 保留 | HTTP | 驗證內容 |
|---|---|---|---|
| automatic | 是 | 200 | 839 筆／影格 |
| bureau | 是 | 200 | 351 筆／影格 |
| rainfall | 是 | 200 | 1342 筆／影格 |
| forecast | 是 | 200 | 42 筆／影格 |
| typhoon | 是 | 200 | 1 筆／影格 |
| warnings | 是 | 200 | 0 筆／影格 |
| radar | 是 | 200 | 影像與格式有效 |
| dark_map | 是 | 200 | 影像與格式有效 |
| street_map | 是 | 200 | 影像與格式有效 |
| boundaries | 是 | 200 | 影像與格式有效 |
| rainviewer | 是 | 200 | 13 筆／影格 |
| gfs_wind | 是 | 200 | GRIB2 decoded: 10 m U/V |
| windy | 否 | — | Removed: no verified Windy Map Forecast credential; NOAA GFS supplies the supported wind model. |

探測結果反映檢查當下，不能保證上游永遠可用。執行期也會檢查資料是否可用並標示過期狀態。

來源定義：`backend/app/sources.py`。金鑰只從 `.env` 讀取，不會寫入報告。
