import streamlit as st
import google.generativeai as genai
import pandas as pd
from datetime import datetime, timedelta, timezone
import requests
import urllib3

# 關閉 SSL 憑證警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 🌟 氣象署授權碼
CWA_API_KEY = "CWA-BCF9370E-EC0E-4B1A-B9B4-8DF41AEE71E6"

from record_engine import get_worksheet, _get_cloud_dataframe

# 🌟 台灣時區 (UTC+8)
TW_TZ = timezone(timedelta(hours=8))

def init_ai():
    try:
        api_key = st.secrets["gemini_api_key"]
        genai.configure(api_key=api_key)
        return True
    except Exception:
        return False

@st.cache_data(ttl=3600, show_spinner=False)
def get_tomorrow_weather(city_name="臺中市", district_name="北屯區"):
    url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-073"
    params = {"Authorization": CWA_API_KEY, "locationName": district_name, "format": "JSON"}
    
    try:
        response = requests.get(url, params=params, timeout=5, verify=False)
        response.raise_for_status()
        
        tw_now = datetime.now(TW_TZ)
        tomorrow_str = (tw_now + timedelta(days=1)).strftime("%Y-%m-%d")
        
        data = response.json()
        records = data.get("records", data.get("Records", {}))
        locations_arr = records.get("locations", records.get("Locations", []))
        if not locations_arr: return ""
            
        loc_list = locations_arr[0].get("location", locations_arr[0].get("Location", []))
        target_loc = loc_list[0] 
        for loc in loc_list:
            if loc.get("locationName", "") == district_name:
                target_loc = loc
                break
                
        weather_elements = target_loc.get("weatherElement", [])
        desc_element = next((we for we in weather_elements if we.get("elementName", "") == "天氣預報綜合描述"), None)
                
        if not desc_element: return ""
            
        time_list = desc_element.get("time", desc_element.get("Time", []))
        day_weather = ""
        night_weather = ""
        
        tomorrow_forecasts = []
        for t in time_list:
            start_time = t.get("startTime", t.get("StartTime", ""))
            if tomorrow_str in start_time:
                val_list = t.get("elementValue", t.get("ElementValue", []))
                if val_list:
                    tomorrow_forecasts.append(val_list[0].get("value", val_list[0].get("WeatherDescription", "")))
        
        if len(tomorrow_forecasts) >= 1: day_weather = tomorrow_forecasts[0]
        if len(tomorrow_forecasts) >= 2: night_weather = tomorrow_forecasts[1]
        
        if not day_weather: day_weather = "依氣象署網站為準"
        if not night_weather: night_weather = "依氣象署網站為準"
                
        return f"☀️［白天］{day_weather}\n🌙［晚上］{night_weather}"

    except Exception:
        return ""

def get_recent_7_days_history(dept_name):
    try:
        sheet = get_worksheet()
        if not sheet: return "無雲端資料庫連線。"
        
        df = _get_cloud_dataframe(sheet)
        if df is None or df.empty: return "資料庫目前尚無歷史紀錄。"
        
        tw_now = datetime.now(TW_TZ)
        past_7_days = [(tw_now - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, 11)]
        
        if dept_name == "總管理處":
            history_df = df[df['date'].isin(past_7_days)].copy()
        else:
            history_df = df[(df['cat'] == dept_name) & (df['date'].isin(past_7_days))].copy()
        
        if history_df.empty: return "過去近期尚無營業紀錄可供分析。"
        
        history_df['ordered_qty'] = pd.to_numeric(history_df['ordered_qty'], errors='coerce').fillna(0)
        history_df['pos_qty'] = pd.to_numeric(history_df['pos_qty'], errors='coerce').fillna(0)
        history_df['waste_qty'] = history_df['ordered_qty'] - history_df['pos_qty']
        
        analysis_df = history_df.groupby(['cat', 'name'] if 'cat' in history_df.columns else 'name').agg(
            總銷售量=('pos_qty', 'sum'),
            最高單日銷售=('pos_qty', 'max'),
            平均每日銷售=('pos_qty', 'mean'),
            總報廢或短少=('waste_qty', 'sum')
        ).reset_index()
        
        report_text = "【過去 10 天真實營運數據分析】：\n"
        for _, row in analysis_df.iterrows():
            waste_status = ""
            waste_val = row['總報廢或短少']
            if waste_val > 0: waste_status = f"⚠️做太多，累積報廢 {int(waste_val)} 份"
            elif waste_val < 0: waste_status = f"🔥做太少，缺貨 {int(abs(waste_val))} 份"
            else: waste_status = "✅抓得剛剛好"
                
            cat_prefix = f"[{row['cat']}] " if 'cat' in row else ""
            report_text += f"🔹 {cat_prefix}{row['name']}: 近期均銷 {row['平均每日銷售']:.1f} 份 (最高曾賣 {int(row['最高單日銷售'])} 份)。耗損狀況：{waste_status}。\n"
            
        return report_text
    except Exception as e:
        return f"調閱歷史資料失敗：{e}"

# 🌟【全新雷達】：讓 AI 知道員工今天/明天建檔了什麼預估數量！
def get_current_plans(dept_name):
    try:
        sheet = get_worksheet()
        if not sheet: return ""
        df = _get_cloud_dataframe(sheet)
        if df is None or df.empty: return ""
        
        tw_now = datetime.now(TW_TZ)
        today_str = tw_now.strftime("%Y-%m-%d")
        tomorrow_str = (tw_now + timedelta(days=1)).strftime("%Y-%m-%d")
        
        if dept_name == "總管理處":
            target_df = df[df['date'].isin([today_str, tomorrow_str])].copy()
        else:
            target_df = df[(df['cat'] == dept_name) & (df['date'].isin([today_str, tomorrow_str]))].copy()
            
        target_df['ordered_qty'] = pd.to_numeric(target_df['ordered_qty'], errors='coerce').fillna(0)
        target_df = target_df[target_df['ordered_qty'] > 0]
        
        if target_df.empty: return "目前資料庫中尚未填寫今日或明日的預估出餐數量。"
        
        report = "【目前資料庫中已建檔的出餐計畫】：\n"
        for d_str in [today_str, tomorrow_str]:
            day_df = target_df[target_df['date'] == d_str]
            if not day_df.empty:
                day_label = "今日" if d_str == today_str else "明日"
                report += f"\n📅 {day_label} ({d_str}) 的預估出餐表：\n"
                for _, r in day_df.iterrows():
                    cat_prefix = f"[{r['cat']}] " if dept_name == "總管理處" else ""
                    report += f"- {cat_prefix}{r['name']}: 預計製作 {int(r['ordered_qty'])} 份\n"
        return report
    except Exception:
        return ""

def render_ai_assistant(dept_name, display_df):
    if not init_ai():
        st.info("🤖 AI 數據顧問正在休假中 (尚未設定有效金鑰)。")
        return

    st.divider()
    
    if "ai_query_count" not in st.session_state: st.session_state.ai_query_count = 0
    if "ai_chat_history" not in st.session_state: st.session_state.ai_chat_history = []

    remaining_quota = 5 - st.session_state.ai_query_count
    
    if dept_name == "總管理處":
        st.markdown(f"#### 👑 阿布潘老闆-專屬AI助手")
        st.markdown(f"<p style='font-size:12px; color:#888;'>💡 擁有全公司最高讀取權限！支援跨部門營運分析與戰略建議。(本次登入剩餘額度: <span style='color:#f37021;font-weight:bold;'>{remaining_quota}</span> 次)</p>", unsafe_allow_html=True)
        placeholder_text = "例：你看我明天壽司部的出餐表安排合適嗎？幫我算營業額！"
    else:
        st.markdown(f"#### 🤖 {dept_name}部 - AI 首席資料分析師 ")
        st.markdown(f"<p style='font-size:12px; color:#888;'>💡 自動調閱歷史報廢紀錄給予精準備料建議！(剩餘額度: <span style='color:#f37021;font-weight:bold;'>{remaining_quota}</span> 次)</p>", unsafe_allow_html=True)
        placeholder_text = "例：根據過去歷史紀錄，建議我鮭魚跟甜蝦該備多少量？"

    with st.container(border=True):
        for msg in st.session_state.ai_chat_history:
            if msg["role"] == "user" and "【隱藏系統資料】" in msg["content"]:
                display_text = msg["content"].split("【使用者提問】\n")[-1]
                with st.chat_message("user"): st.markdown(display_text)
            else:
                with st.chat_message(msg["role"]): st.markdown(msg["content"])

        if st.session_state.ai_query_count >= 5:
            st.warning("✋ 您本次的 AI 詢問額度已達上限。若需繼續提問，請充值！")
            return

        prompt = st.chat_input(placeholder_text)
        
        if prompt:
            with st.chat_message("user"):
                st.markdown(prompt)

            tw_now_str = datetime.now(TW_TZ).strftime("%Y-%m-%d")
            menu_info = ""
            for _, row in display_df.iterrows():
                item_price = int(row.get('price', 0))
                wd_avg = row.get('wd_avg', 0) 
                cat_prefix = f"[{row.get('cat', dept_name)}] " if dept_name == "總管理處" else ""
                menu_info += f"- {cat_prefix}{row['name']} (單價: {item_price}元, 歷史長期平日均銷: {wd_avg}份)\n"

            with st.chat_message("assistant"):
                with st.spinner("🤖 思考回覆中 ..."):
                    try:
                        weather_info = ""
                        weather_keywords = ["天氣", "下雨", "氣象", "雨", "晴", "颱風", "預估", "備料", "建議", "安排", "明天"]
                        if any(kw in prompt for kw in weather_keywords):
                            weather_data = get_tomorrow_weather()
                            if weather_data:
                                weather_info = f"\n【☁️ 氣象署 明日台中北屯區預報】\n{weather_data}\n"

                        history_report = get_recent_7_days_history(dept_name)
                        
                        # 🌟 啟動新外掛：抓取員工已經建好的計畫表！
                        current_plan_report = get_current_plans(dept_name)
                        
                        if dept_name == "總管理處":
                            system_instruction = f"""
                            你現在是阿布潘水產的【總管理處首席 AI 營運戰略幕僚】。
                            今天是 {tw_now_str}。
                            
                            【最高權限解鎖】：
                            1. 你擁有全公司所有部門的最高讀取權限，可以針對跨部門的業績、耗損、商品單價進行綜合分析與比較。
                            2. 你的回答層次必須具備「老闆視角」，以提升營收、商品搭配活動建議、優化跨部門資源為主。
                            3. 絕對禁止回答政治、寫程式等與阿布潘水產無關的話題。
                            """
                        else:
                            system_instruction = f"""
                            你現在是阿布潘水產【{dept_name}部】的首席 AI 資料分析師。
                            今天是 {tw_now_str}。
                            
                            【安全隔離限制】：
                            1. 只能處理【{dept_name}部】的業務。嚴禁跨部門回答。
                            2. 絕對禁止回答政治、寫程式等無關話題。遇到無關話題請嚴格拒絕。
                            """

                        system_instruction += f"""
                        【今日全商品庫 (包含單價與長期平均實力)】：
                        {menu_info}
                        
                        【⚠️ 雲端資料庫傳回的過去 10 天真實營運紀錄 (近期脈搏)】：
                        {history_report}

                        【你的專業分析任務指南 (極度重要)】：
                        1. 如果老闆問「明天的出餐表合適嗎」，請直接從隱藏資料中讀取【已建檔的出餐計畫】，拿它去跟【過去 10 天真實營運紀錄】做比較，告訴老闆哪幾項備太多或備太少。
                        2. 【雙軌交叉比對】：你必須結合「長期平日均銷」與「過去 10 天真實耗損」精算建議。
                           - 如果過去 10 天紀錄顯示「⚠️做太多，浪費」，請勇敢建議數量砍低。
                           - 如果過去 10 天紀錄顯示「🔥做太少，缺貨」，請建議增加備料。
                        3. 如果有提供【天氣預報】，請務必納入考量（如下雨調降，好天氣調升）。
                        4. 如果被要求算營業額，請用提供的單價乘上數量加總。
                        5. 回答要專業、有說服力，並加上 Emoji 讓排版好讀。
                        """

                        model = genai.GenerativeModel(
                            model_name='gemini-2.5-flash', 
                            system_instruction=system_instruction
                        )
                        
                        # 🌟 把所有情報打包進去
                        hidden_context = f"【隱藏系統資料】\n{weather_info}\n{current_plan_report}\n【使用者提問】\n"
                        full_prompt = hidden_context + prompt

                        history = []
                        for m in st.session_state.ai_chat_history:
                            role = "user" if m["role"] == "user" else "model"
                            history.append({"role": role, "parts": [m["content"]]})
                            
                        chat = model.start_chat(history=history)
                        response = chat.send_message(full_prompt)
                        
                        st.markdown(response.text)
                        
                        st.session_state.ai_chat_history.append({"role": "user", "content": full_prompt})
                        st.session_state.ai_chat_history.append({"role": "assistant", "content": response.text})
                        st.session_state.ai_query_count += 1
                        st.rerun()
                        
                    except Exception as e:
                        error_msg = str(e)
                        if "429" in error_msg or "Quota exceeded" in error_msg:
                            st.warning("⏳ 喔喔！您問得太快了！ 的免費額度限制為「每分鐘 5 次」。請稍等 1 分鐘後再試一次喔！")
                        else:
                            st.error(f"❌ AI 發生異常: {e}")
