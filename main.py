import os
import requests
from dotenv import load_dotenv

# 載入 .env 環境變數
load_dotenv()

# 中央氣象署 API 設定
CWA_API_KEY = os.getenv("CWA_API_KEY", "")
LOCATION_NAME = os.getenv("LOCATION_NAME", "臺北市")
CWA_API_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001"

def fetch_weather_forecast(location_name: str = "臺北市"):
    """
    從中央氣象署 API 擷取指定縣市今明 36 小時天氣預報
    """
    if not CWA_API_KEY or CWA_API_KEY == "CWA-YOUR-AUTHORIZATION-KEY-HERE":
        print("⚠️ 錯誤：請先於 .env 檔案中設定正確的 CWA_API_KEY (授權碼)！")
        print("💡 授權碼請至中央氣象署氣象資料開放平臺申請: https://opendata.cwa.gov.tw/")
        return

    params = {
        "Authorization": CWA_API_KEY,
        "locationName": location_name
    }

    try:
        response = requests.get(CWA_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data.get("success") == "true":
            print("❌ API 回傳異常:", data)
            return

        location_data = data["records"]["location"]
        if not location_data:
            print(f"⚠️ 找不到地點: {location_name}")
            return

        target_loc = location_data[0]
        weather_elements = target_loc["weatherElement"]

        # 解析 36 小時預報時段
        time_slots = {}
        for elem in weather_elements:
            elem_name = elem["elementName"] # Wx, PoP, MinT, MaxT, CI
            for time_item in elem["time"]:
                start_time = time_item["startTime"]
                end_time = time_item["endTime"]
                key = f"{start_time} ~ {end_time}"

                if key not in time_slots:
                    time_slots[key] = {}

                value = time_item["parameter"]["parameterName"]
                unit = time_item["parameter"].get("parameterUnit", "")
                time_slots[key][elem_name] = f"{value} {unit}".strip()

        print("=" * 50)
        print(f"🌤️ 中央氣象署 (CWA) 今明 36 小時天氣預報")
        print(f"📍 查詢地區: {target_loc['locationName']}")
        print("=" * 50)

        for idx, (time_range, details) in enumerate(time_slots.items(), 1):
            print(f"[{idx}] 時段: {time_range}")
            print(f"  - 天氣現象 (Wx) : {details.get('Wx', 'N/A')}")
            print(f"  - 降雨機率 (PoP): {details.get('PoP', 'N/A')}%")
            print(f"  - 最低溫度 (MinT): {details.get('MinT', 'N/A')} °C")
            print(f"  - 最高溫度 (MaxT): {details.get('MaxT', 'N/A')} °C")
            print(f"  - 舒適程度 (CI) : {details.get('CI', 'N/A')}")
            print("-" * 50)

    except requests.exceptions.RequestException as e:
        print(f"❌ 網路連線或 API 請求失敗: {e}")

if __name__ == "__main__":
    fetch_weather_forecast(LOCATION_NAME)
