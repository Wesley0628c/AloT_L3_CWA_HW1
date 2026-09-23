# AIoT L3 - 中央氣象署 (CWA) 氣象資料 API 串接與應用 (HW1)

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![CWA API](https://img.shields.io/badge/API-CWA%20Open%20Data-orange.svg)](https://opendata.cwa.gov.tw/)
[![Email](https://img.shields.io/badge/Email-Wesleycho0628%40gmail.com-red.svg)](mailto:Wesleycho0628@gmail.com)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

本專案為 **AIoT L3 課程 Homework 1**，旨在透過交通部中央氣象署（Central Weather Administration, CWA）開放資料平臺 API，進行物聯網與邊緣設備的即時氣象資料擷取、資料解析與智慧應用監控。

---

## 📌 目錄 (Table of Contents)

- [專案簡介 (Overview)](#-專案簡介-overview)
- [功能特點 (Features)](#-功能特點-features)
- [快速開始 (Quick Start)](#-快速開始-quick-start)
  - [環境需求 (Prerequisites)](#環境需求-prerequisites)
  - [API 授權碼申請 (CWA API Key)](#api-授權碼申請-cwa-api-key)
  - [專案安裝與設定 (Setup)](#專案安裝與設定-setup)
- [專案架構 (Project Structure)](#-專案架構-project-structure)
- [API 常用端點說明 (CWA API Reference)](#-api-常用端點說明-cwa-api-reference)
- [執行範例 (Usage Example)](#-執行範例-usage-example)
- [授權與貢獻 (License & Author)](#-授權與貢獻-license--author)

---

## 📖 專案簡介 (Overview)

在物聯網（AIoT）應用場景中，環境氣象數據（如溫度、濕度、降雨機率、紫外線指數、天氣現象）是智慧農業、智慧城市、防颱警報與能源調度重要的參考依據。

本專案提供規範化的 Python 開發介面，自動對接 CWA API，實現：
1. **即時天氣預報數據擷取** (如 今明 36 小時天氣預報 `F-C0032-001`)。
2. **自動化 JSON 欄位解析與結構化轉換**。
3. **AIoT 邊緣終端應用整合** (如 警報觸發、終端液晶螢幕顯示或控制邏輯)。

---

## 🚀 功能特點 (Features)

- 🔒 **安全金鑰管理**：使用 `.env` 檔案管理 API 授權金鑰，避免敏感資訊外洩。
- 🌤️ **多縣市氣象查詢**：支援指定縣市（如 臺北市、新北市、臺中市、高雄市等）天氣查詢。
- 📊 **結構化解析**：自動解析 Wx (天氣現象)、PoP (降雨機率)、MinT (最低溫)、MaxT (最高溫)、CI (舒適度) 等指標。
- ⚙️ **AIoT 模組化介面**：代碼結構符合高可擴充性，易於串接 MQTT, MicroPython 或 Raspberry Pi/Arduino 邊緣運算節點。

---

## 🛠️ 快速開始 (Quick Start)

### 環境需求 (Prerequisites)

- **Python**: 3.8 或以上版本
- **Pip**: 最新版本

### API 授權碼申請 (CWA API Key)

1. 前往 [中央氣象署氣象資料開放平臺](https://opendata.cwa.gov.tw/)。
2. 註冊並登入會員。
3. 點選 **會員中心** -> **個人設定** / **取得授權碼**。
4. 複製您的 **Authorization Key** (格式通常為 `CWA-XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX`)。

### 專案安裝與設定 (Setup)

1. **複製本專案 repository**：
   ```bash
   git clone https://github.com/Wesley0628c/AloT_L3_CWA_HW1.git
   cd AloT_L3_CWA_HW1
   ```

2. **建立並啟動虛擬環境 (可選但推薦)**：
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # macOS / Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **安裝依賴套件**：
   ```bash
   pip install -r requirements.txt
   ```

4. **設定環境變數**：
   複製 `.env.example` 為 `.env` 並填入您的 CWA API 金鑰：
   ```bash
   # Windows (CMD / PowerShell)
   copy .env.example .env

   # Linux / macOS
   cp .env.example .env
   ```

   修改 `.env` 檔案內容：
   ```env
   CWA_API_KEY=CWA-YOUR-AUTHORIZATION-KEY-HERE
   LOCATION_NAME=臺北市
   ```

---

## 📁 專案架構 (Project Structure)

```text
AloT_L3_CWA_HW1/
│
├── .env.example        # 環境變數範本檔 (含 API Key 範例)
├── .gitignore          # Git 忽略檔案設定 (忽略 .env 與 venv)
├── README.md           # 專案說明文件
├── requirements.txt    # Python 依賴套件清單
└── main.py             # 氣象 API 串接與測試主程式
```

---

## 📡 API 常用端點說明 (CWA API Reference)

本專案主要使用的 CWA API 端點：

| API 代號 | 資料集名稱 | 說明 |
| :--- | :--- | :--- |
| **`F-C0032-001`** | 一般天氣預報-今明36小時天氣預報 | 包含全台 22 縣市之天氣現象、降雨機率、高低溫、舒適度 |
| **`F-D0047-091`** | 鄉鎮天氣預報-臺灣未來2天天氣預報 | 提供更細緻之鄉鎮等級預報 |
| **`O-A0001-001`** | 自動氣象站氣象資料 | 即時觀測數據（如即時氣溫、風速、雨量等） |

*預設端點 URL*:
`https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001`

---

## 💻 執行範例 (Usage Example)

執行主程式來擷取並印出當前氣象預報：

```bash
python main.py
```

**預期主機輸出範例**：

```text
==================================================
🌤️ 中央氣象署 (CWA) 今明 36 小時天氣預報
📍 查詢地區: 臺北市
==================================================
[時段 1] 2026-09-23 12:00:00 ~ 2026-09-23 18:00:00
  - 天氣現象 (Wx) : 多雲短暫陣雨
  - 降雨機率 (PoP): 30%
  - 最低溫度 (MinT): 26 °C
  - 最高溫度 (MaxT): 32 °C
  - 舒適程度 (CI) : 舒適至悶熱
--------------------------------------------------
```

---

## 📜 授權與貢獻 (License & Author)

- **作者 (Author)**: [Wesley0628c](https://github.com/Wesley0628c)
- **聯絡 Email**: [Wesleycho0628@gmail.com](mailto:Wesleycho0628@gmail.com)
- **課程 (Course)**: AIoT Level 3 Course
- **授權條款 (License)**: 本專案採用 [MIT License](LICENSE) 授權方式。
