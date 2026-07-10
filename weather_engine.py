import requests
import urllib3
import streamlit as st
from datetime import datetime, timedelta, timezone

# 關閉 SSL 憑證警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 🌟 氣象署授權碼
CWA_API_KEY = "CWA-BCF9370E-EC0E-4B1A-B9B4-8DF41AEE71E6"

# 🌟 台灣時區 (UTC+8)
TW_TZ = timezone(timedelta(hours=8))

@st.cache_data(ttl=1800, show_spinner=False)
def get_tomorrow_weather(city_name="臺中市", district_name="北屯區"):
    """
    取得中央氣象署精準天氣指標 (包含降雨、溫度、體感)
    回傳格式：成功回傳整理好的字串，失敗回傳 "ERROR: 原因"
    """
    url = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-073"
    params = {
        "Authorization": CWA_API_KEY,
        "locationName": district_name,
        "format": "JSON"
    }

    try:
        response = requests.get(url, params=params, timeout=10, verify=False)
        response.raise_for_status()
        data = response.json()

        records = data.get("records", {})
        locations = records.get("locations", [])
        if not locations: return "ERROR：找不到 records.locations"

        location_list = locations[0].get("location", [])
        if not location_list: return "ERROR：沒有任何行政區資料"

        target = None
        for loc in location_list:
            if loc.get("locationName") == district_name:
                target = loc
                break

        if target is None: return f"ERROR：找不到行政區：{district_name}"

        weather_elements = target.get("weatherElement", [])
        
        # 🌟 建立一個小字典，方便抓取各種需要的指標
        elements_map = {item.get("elementName"): item for item in weather_elements}
        
        tomorrow_str = (datetime.now(TW_TZ) + timedelta(days=1)).strftime("%Y-%m-%d")

        def extract_value(element_name, time_index):
            """輔助函數：從氣象署複雜的結構中安全抽出值"""
            try:
                el = elements_map.get(element_name)
                if not el: return "未知"
                times = el.get("time", [])
                
                # 找明天的資料
                target_times = [t for t in times if t.get("startTime", "").startswith(tomorrow_str)]
                if not target_times: return "未知"
                
                # 防呆：確保索引不超界
                t_data = target_times[time_index] if len(target_times) > time_index else target_times[-1]
                vals = t_data.get("elementValue", [])
                if not vals: return "未知"
                return vals[0].get("value", "")
            except:
                return "未知"

        # 🌟 分別抓取白天 (index 0 或 1) 與晚上 (index 2 或 3) 的指標
        # 氣象局資料通常：0=今晚, 1=明早, 2=明午, 3=明晚 (依當下查詢時間會變動)
        # 所以我們直接依賴 datetime 去過濾出 tomorrow_str 的資料，0是明天的第一筆(白天)，1是第二筆(晚上)
        
        day_desc = extract_value("天氣預報綜合描述", 0)
        day_pop = extract_value("12小時降雨機率", 0)
        day_temp = extract_value("溫度", 0)
        day_feel = extract_value("體感溫度", 0)
        
        night_desc = extract_value("天氣預報綜合描述", 1)
        night_pop = extract_value("12小時降雨機率", 1)
        night_temp = extract_value("溫度", 1)
        night_feel = extract_value("體感溫度", 1)
        
        # 🌟 整理成非常結構化、AI 絕對看得懂的營運指標
        report = (
            f"【明日 ({tomorrow_str}) 台中北屯區 氣象營運指標】\n"
            f"====================\n"
            f"☀️ ［白天營運時段］\n"
            f"• 氣象描述：{day_desc}\n"
            f"• 降雨機率：{day_pop}%\n"
            f"• 實際溫度：{day_temp}℃ (體感 {day_feel}℃)\n\n"
            f"🌙 ［晚間營運時段］\n"
            f"• 氣象描述：{night_desc}\n"
            f"• 降雨機率：{night_pop}%\n"
            f"• 實際溫度：{night_temp}℃ (體感 {night_feel}℃)\n"
            f"===================="
        )
        return report

    except requests.exceptions.Timeout:
        return "ERROR：中央氣象署連線逾時"
    except requests.exceptions.ConnectionError:
        return "ERROR：無法連線中央氣象署"
    except Exception as e:
        return f"ERROR：{str(e)}"
