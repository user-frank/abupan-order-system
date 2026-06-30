import streamlit as st
import google.generativeai as genai
import pandas as pd
from datetime import datetime, timedelta
import requests
import urllib3

# 關閉 SSL 憑證警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 🌟 氣象署授權碼
CWA_API_KEY = "CWA-BCF9370E-EC0E-4B1A-B9B4-8DF41AEE71E6"

# 🌟 導入雲端資料庫工具，讓 AI 有能力調閱歷史紀錄！
from record_engine import get_worksheet, _get_cloud_dataframe

def init_ai():
    """初始化並檢查 API Key"""
    try:
        api_key = st.secrets["gemini_api_key"]
        genai.configure(api_key=api_key)
        return True
    except Exception:
        return False

# 🌟 【新增】：天氣查詢引擎 (帶有 1 小時快取，極速秒回)
@st.cache_data(ttl=14400, show_spinner=False)
def get_tomorrow_weather(city_name="臺中市", district_name="北屯區"):
    url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-073"
    params = {"Authorization": CWA_API_KEY, "locationName": district_name, "format": "JSON"}
    
    try:
        response = requests.get(url, params=params, timeout=5, verify=False)
        response.raise_for_status()
        
        tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
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
        
        day_weather = "查無資料"
        night_weather = "查無資料"
        
        for t in time_list:
            start_time = t.get("startTime", t.get("StartTime", ""))
            val_list = t.get("elementValue", t.get("ElementValue", []))
            if not val_list: continue
            
            desc = val_list[0].get("value", val_list[0].get("WeatherDescription", ""))
            
            if start_time.startswith(f"{tomorrow_str}T12"):
                day_weather = desc
            elif start_time.startswith(f"{tomorrow_str}T18"):
                night_weather = desc
                
        return f"☀️［白天］{day_weather}\n🌙［晚上］{night_weather}"

    except Exception:
        return ""

def get_recent_7_days_history(dept_name):
    """🧠 AI 的外掛大腦：自動調閱過去 10 天的真實銷售與耗損紀錄"""
    try:
        sheet = get_worksheet()
        if not sheet: return "無雲端資料庫連線。"
        
        df = _get_cloud_dataframe(sheet)
        if df is None or df.empty: return "資料庫目前尚無歷史紀錄。"
        
        today = datetime.now()
        # 老闆修改：抓取 10 天數據
        past_7_days = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, 11)]
        
        # 🌟 【最高權限解鎖】：如果老闆呼叫，就不限制部門，全部調閱！
        if dept_name == "總管理處":
            history_df = df[df['date'].isin(past_7_days)].copy()
        else:
            history_df = df[(df['cat'] == dept_name) & (df['date'].isin(past_7_days))].copy()
        
        if history_df.empty: return "過去近期尚無營業紀錄可供分析。"
        
        history_df['ordered_qty'] = pd.to_numeric(history_df['ordered_qty'], errors='coerce').fillna(0)
        history_df['pos_qty'] = pd.to_numeric(history_df['pos_qty'], errors='coerce').fillna(0)
        history_df['waste_qty'] = history_df['ordered_qty'] - history_df['pos_qty']
        
        # 進行大數據特徵壓縮
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

def render_ai_assistant(dept_name, display_df):
    if not init_ai():
        st.info("🤖 AI 數據顧問正在休假中 。")
        return

    st.divider()
    
    if "ai_query_count" not in st.session_state: st.session_state.ai_query_count = 0
    if "ai_chat_history" not in st.session_state: st.session_state.ai_chat_history = []

    remaining_quota = 5 - st.session_state.ai_query_count
    
    # 🌟 根據權限渲染不同的 UI 標題
    if dept_name == "總管理處":
        st.markdown(f"#### 👑 阿布潘老闆-專屬AI助手")
        st.markdown(f"<p style='font-size:12px; color:#888;'>💡 擁有全公司最高讀取權限！支援跨部門營運分析與戰略建議。(本次登入剩餘額度: <span style='color:#f37021;font-weight:bold;'>{remaining_quota}</span> 次)</p>", unsafe_allow_html=True)
        placeholder_text = "例：最近適合做活動嗎？並給出調整建議。"
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

            today_str = datetime.now().strftime("%Y-%m-%d")
            menu_info = ""
            for _, row in display_df.iterrows():
                item_price = int(row.get('price', 0))
                wd_avg = row.get('wd_avg', 0) 
                cat_prefix = f"[{row.get('cat', dept_name)}] " if dept_name == "總管理處" else ""
                menu_info += f"- {cat_prefix}{row['name']} (單價: {item_price}元, 歷史長期平日均銷: {wd_avg}份)\n"

            with st.chat_message("assistant"):
                with st.spinner("🤖 思考回覆中 ..."):
                    try:
                        # 🌟 意圖辨識：只有問到天氣或備料建議，才去抓氣象署資料！
                        weather_info = ""
                        weather_keywords = ["天氣", "下雨", "氣象", "雨", "晴", "颱風", "預估", "備料", "建議", "安排"]
                        if any(kw in prompt for kw in weather_keywords):
                            weather_data = get_tomorrow_weather()
                            if weather_data:
                                weather_info = f"\n【☁️ 氣象署 明日台中北屯區預報】\n{weather_data}\n"

                        history_report = get_recent_7_days_history(dept_name)
                        
                        # 🌟 根據權限進行不同的 AI 靈魂洗腦
                        if dept_name == "總管理處":
                            system_instruction = f"""
                            你現在是阿布潘水產的【總管理處首席 AI 營運戰略幕僚】。
                            今天是 {today_str}。
                            
                            【最高權限解鎖】：
                            1. 你擁有全公司所有部門的最高讀取權限，可以針對跨部門的業績、耗損、商品單價進行綜合分析與比較。
                            2. 你的回答層次必須具備「老闆視角」，以提升營收、商品搭配活動建議、優化跨部門資源為主。
                            3. 絕對禁止回答政治、寫程式等與阿布潘水產無關的話題。
                            """
                        else:
                            system_instruction = f"""
                            你現在是阿布潘水產【{dept_name}部】的首席 AI 資料分析師。
                            今天是 {today_str}。
                            
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
                        1. 【雙軌交叉比對】：你必須結合「長期平日均銷」與「過去 10 天真實耗損(做太多/做太少)」精算建議。
                           - 基準線：以菜單資料庫中的「歷史長期平日均銷」為出發點。
                           - 近期微調：如果過去 10 天紀錄顯示「⚠️做太多，累積報廢」，代表近期買氣衰退，請勇敢將建議數量砍低於歷史均銷。
                           - 近期微調：如果過去 10 天紀錄顯示「🔥做太少，缺貨」，請建議增加備料。
                        2. 如果使用者有提供天氣資訊，請務必將「天氣預報」納入備料考量（例如：下雨調降數量，好天氣調升數量）。
                        3. 如果員工請你算出營業額，請確實將你建議的數量乘上菜單裡的單價，加總並加上千分位逗號。
                        4. 回答要專業、有說服力（必須引述你看到的歷史耗損數據，或是你算出的營業額），並加上 Emoji 讓排版好讀。
                        """

                        # 🌟 你要求的 2.5 模型
                        model = genai.GenerativeModel(
                            model_name='gemini-2.5-flash', 
                            system_instruction=system_instruction
                        )
                        
                        hidden_context = f"【隱藏系統資料】\n{weather_info}\n【使用者提問】\n"
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
                        st.error(f"❌ AI 發生異常: {e}。請確認您的 Streamlit Secrets 金鑰是否正確！")
