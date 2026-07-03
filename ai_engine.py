import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import requests
import urllib3

# 🌟 導入 Google 最新的官方 AI 套件
from google import genai
from google.genai import types

# 關閉 SSL 憑證警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 🌟 氣象署授權碼
CWA_API_KEY = "CWA-BCF9370E-EC0E-4B1A-B9B4-8DF41AEE71E6"

from record_engine import get_worksheet, _get_cloud_dataframe
from config_engine import load_subcategories

# 🌟 台灣時區 (UTC+8)
TW_TZ = timezone(timedelta(hours=8))

def check_ai_key():
    """檢查 API Key 是否存在"""
    try:
        api_key = st.secrets["gemini_api_key"]
        if not api_key: return False
        return True
    except Exception:
        return False

@st.cache_data(ttl=3600, show_spinner=False)
def get_tomorrow_weather(city_name="臺中市", district_name="北屯區"):
    url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-073"
    params = {"Authorization": CWA_API_KEY, "locationName": district_name, "format": "JSON"}
    
    try:
        response = requests.get(url, params=params, timeout=15, verify=False)
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

def get_recent_history_report(dept_name):
    """🧠 終極 AI 大腦：提供過去 30 天逐日明細、打折偵測、與【每日總產能報表】"""
    try:
        sheet = get_worksheet()
        if not sheet: return "無雲端資料庫連線。"
        
        df = _get_cloud_dataframe(sheet)
        if df is None or df.empty: return "資料庫目前尚無歷史紀錄。"
        
        tw_now = datetime.now(TW_TZ)
        past_days = [(tw_now - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, 31)]
        
        if dept_name == "總管理處":
            history_df = df[df['date'].isin(past_days)].copy()
        else:
            history_df = df[(df['cat'] == dept_name) & (df['date'].isin(past_days))].copy()
        
        if history_df.empty: return "過去 30 天內尚無營業紀錄可供分析。"
        
        for col in ['ordered_qty', 'actual_qty', 'pos_qty', 'pos_revenue', 'price']:
            if col not in history_df.columns: history_df[col] = 0
            history_df[col] = pd.to_numeric(history_df[col], errors='coerce').fillna(0).astype(int)
        
        history_df = history_df.sort_values(by='date', ascending=False)
        
        subcat_dict = load_subcategories(dept_name) if dept_name != "總管理處" else {}
        if dept_name != "總管理處":
            history_df['subcat'] = history_df['item_id'].astype(str).map(lambda x: subcat_dict.get(x.split('_')[0], "未分類"))
        
        weekdays_tw = ["一", "二", "三", "四", "五", "六", "日"]
        report_text = "【過去 30 天各單品真實營運數據 (供趨勢與星期分析)】：\n"
        
        grouped = history_df.groupby(['cat', 'name'] if 'cat' in history_df.columns else 'name')
        for group_keys, item_df in grouped:
            item_name = group_keys[1] if isinstance(group_keys, tuple) else group_keys
            cat_prefix = f"[{group_keys[0]}] " if isinstance(group_keys, tuple) and dept_name == "總管理處" else ""
            
            report_text += f"\n🔹 {cat_prefix}{item_name}:\n"
            for _, row in item_df.iterrows():
                d_str = row['date']
                d_obj = datetime.strptime(d_str, "%Y-%m-%d")
                wd_str = weekdays_tw[d_obj.weekday()]
                
                o_qty = row['ordered_qty']
                a_qty = row['actual_qty']
                p_qty = row['pos_qty']
                p_rev = row['pos_revenue']
                price = row['price']
                
                status = ""
                if o_qty > 0 and a_qty == 0:
                    status = "(⏸️ 臨時取消出餐)"
                elif a_qty > o_qty and p_qty >= o_qty:
                    status = "(🔥 現場緊急追加)"
                elif a_qty > p_qty:
                    status = f"(⚠️ 報廢 {a_qty - p_qty} 份)"
                elif a_qty < p_qty:
                    status = f"(🚨 缺貨/超賣 {p_qty - a_qty} 份)"
                else:
                    status = "(✅ 完銷相符)"
                    
                discount_status = ""
                if p_qty > 0 and price > 0:
                    full_price_revenue = p_qty * price
                    if p_rev < full_price_revenue * 0.95:
                        discount_rate = int((p_rev / full_price_revenue) * 10)
                        discount_status = f" [📉打折出清,平均約{discount_rate}折]"
                    
                report_text += f"   - {d_str}(週{wd_str}): 預估 {o_qty}, 實際 {a_qty}, POS賣出 {p_qty} {status}{discount_status}\n"
        
        report_text += "\n【過去 30 天各區總產能與總銷量參考 (用以控制建議總數)】：\n"
        daily_summary = history_df.groupby('date').agg(總實際出餐=('actual_qty', 'sum'), 總POS銷售=('pos_qty', 'sum')).reset_index()
        for _, row in daily_summary.iterrows():
            d_str = row['date']
            d_obj = datetime.strptime(d_str, "%Y-%m-%d")
            wd_str = weekdays_tw[d_obj.weekday()]
            
            day_sub_df = history_df[history_df['date'] == d_str]
            if dept_name == "總管理處":
                sub_group = day_sub_df.groupby('cat')['actual_qty'].sum().to_dict()
            else:
                sub_group = day_sub_df.groupby('subcat')['actual_qty'].sum().to_dict()
                
            sub_details = ", ".join([f"{k}:{v}份" for k, v in sub_group.items() if v > 0])
            report_text += f"📅 {d_str}(週{wd_str}) 總出餐: {row['總實際出餐']} 份 (明細: {sub_details}) | 總POS銷售: {row['總POS銷售']} 份\n"

        return report_text
    except Exception as e:
        return f"調閱歷史資料失敗：{e}"

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
    if not check_ai_key():
        st.info("🤖 AI 數據顧問正在休假中 (尚未設定有效金鑰)。")
        return

    st.divider()
    
    if "ai_query_count" not in st.session_state: st.session_state.ai_query_count = 0
    if "ai_chat_history" not in st.session_state: st.session_state.ai_chat_history = []

    remaining_quota = 5 - st.session_state.ai_query_count
    
    if dept_name == "總管理處":
        st.markdown(f"#### 👑 阿布潘老闆-專屬AI助手")
        st.markdown(f"<p style='font-size:12px; color:#888;'>💡 擁有全公司最高讀取權限！支援跨部門營運分析與戰略建議。(本次登入剩餘額度: <span style='color:#f37021;font-weight:bold;'>{remaining_quota}</span> 次)</p>", unsafe_allow_html=True)
        placeholder_text = "例：最近適合做活動嗎？並給出調整建議。"
    else:
        st.markdown(f"#### 🤖 {dept_name}部 - AI 首席資料分析師 ")
        st.markdown(f"<p style='font-size:12px; color:#888;'>💡 自動調閱過去 30 天歷史紀錄，給予最精準的備料建議！(剩餘額度: <span style='color:#f37021;font-weight:bold;'>{remaining_quota}</span> 次)</p>", unsafe_allow_html=True)
        placeholder_text = "例：幫我預估明天的出餐量？"

    with st.container(border=True):
        for msg in st.session_state.ai_chat_history:
            if msg["role"] == "user" and "【隱藏系統資料】" in msg["content"]:
                display_text = msg["content"].split("【使用者提問】\n")[-1]
                with st.chat_message("user"): st.markdown(display_text)
            else:
                with st.chat_message(msg["role"]): st.markdown(msg["content"])

        if st.session_state.ai_query_count >= 5:
            st.warning("✋ 您本次的 AI 詢問額度已達上限。若需繼續提問，請充值 ！")
            return

        prompt = st.chat_input(placeholder_text)
        
        if prompt:
            with st.chat_message("user"):
                st.markdown(prompt)

            tw_now_str = datetime.now(TW_TZ).strftime("%Y-%m-%d")
            tomorrow_wd = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"][(datetime.now(TW_TZ) + timedelta(days=1)).weekday()]
            
            menu_info = ""
            for _, row in display_df.iterrows():
                item_price = int(row.get('price', 0))
                cat_prefix = f"[{row.get('cat', dept_name)}] " if dept_name == "總管理處" else ""
                menu_info += f"- {cat_prefix}{row['name']} (單價: {item_price}元)\n"

            with st.chat_message("assistant"):
                with st.spinner("🤖 思考回覆中 ..."):
                    try:
                        weather_info = ""
                        weather_keywords = ["天氣", "下雨", "氣象", "雨", "晴", "颱風", "預估", "備料", "建議", "安排", "明天"]
                        if any(kw in prompt for kw in weather_keywords):
                            weather_data = get_tomorrow_weather()
                            if weather_data:
                                weather_info = f"\n【☁️ 氣象署 明日台中北屯區預報】\n{weather_data}\n"

                        history_report = get_recent_history_report(dept_name)
                        current_plan_report = get_current_plans(dept_name)
                        
                        if dept_name == "總管理處":
                            system_instruction = f"""
                            你現在是阿布潘水產的【總管理處首席 AI 營運戰略幕僚】。
                            今天是 {tw_now_str}，明天是 {tomorrow_wd}。
                            
                            【最高權限解鎖】：
                            1. 擁有跨部門最高分析權限。回答須具備「老闆視角」，以提升毛利、降低報廢為主。
                            2. 絕對禁止回答政治、寫程式等與阿布潘水產無關的話題。
                            """
                        else:
                            system_instruction = f"""
                            你現在是阿布潘水產【{dept_name}部】的首席 AI 資料分析師。
                            今天是 {tw_now_str}，明天是 {tomorrow_wd}。
                            
                            【安全隔離限制】：
                            1. 只能處理【{dept_name}部】業務。嚴禁跨部門回答。
                            2. 絕對禁止回答無關話題。
                            """

                        system_instruction += f"""
                        【今日全商品庫 (僅提供商品與最新單價)】：
                        {menu_info}
                        
                        【⚠️ 過去 30 天每日真實營運數據 (你的唯一決策依據！)】：
                        {history_report}

                        【你的專業分析任務指南 (極度重要，請嚴格遵守)】：
                        1. 【基線確立 - 尋找同星期的規律】：由於現在沒有提供長期均銷，你必須【完全依賴】上面提供的 30 天真實營運數據！當你給出明天({tomorrow_wd})的備料建議時，必須自己去數據庫找出過去 4 週內所有的 {tomorrow_wd}，算出它們的平均 POS 銷量，當作你的基準線！
                        2. 【總產能天花板限制 (防超量)】：你在給出備料建議時，必須參考報表下方的「過去 30 天各區總產能與總銷量參考」。你的「建議總數量」絕對不可以無故大幅超過「歷史同星期」的各區總出餐量。必須在合理的總產能限制內進行分配。
                        3. 【現場動態決策微調】：
                           - 狀態為(🔥 現場緊急追加)：代表市場熱度高，即使有報廢，也建議在基準線上提高備料。
                           - 狀態為(⏸️ 臨時取消出餐)：為人員排程問題，不代表該商品滯銷，不扣減銷量評估。
                           - 狀態為(⚠️ 報廢)：真正供過於求，需下調備料。
                        4. 🌟【打折標籤認知與毛利保護】：報表中的「📉打折出清，平均約 X 折」，是因為系統使用 (總營收/原價總營收) 計算的數學平均值。這代表「可能只有晚間少部分商品半價出清」，並非代表該商品全天都賣不掉。請綜合「報廢/缺貨」狀況客觀評估，不要看到打折就過度大砍備料；但若頻繁出現此標籤且伴隨大量報廢，請警告使用者控制報廢以保住毛利。
                        5. 若有【天氣預報】，天氣資訊與歷史數據都是由「系統後台自動抓取並塞入隱藏提示中」提供給你的。當使用者詢問天氣或出餐建議時，請【直接讀取並應用】隱藏資料中的天氣預報，絕對不要回答「我無法連網」或「你沒給我資料」。如果隱藏資料顯示連線失敗，請如實回報「系統暫時無法連線氣象署」請務必納入考量（如下雨調降，晴朗調升）。
                        6. 若要求計算營業額，務必將建議數量乘上單價加總。
                        7. 嚴禁虛構數據！如果 30 天內查無該商品紀錄，請直言「無歷史數據可供分析」。
                        """

                        # 🌟 使用 Google 最新官方寫法呼叫 AI！
                        client = genai.Client(api_key=st.secrets["gemini_api_key"])
                        config = types.GenerateContentConfig(
                            system_instruction=system_instruction
                        )
                        
                        hidden_context = f"【隱藏系統資料】\n{weather_info}\n{current_plan_report}\n【使用者提問】\n"
                        full_prompt = hidden_context + prompt

                        # 轉換歷史訊息格式為新版要求
                        formatted_history = []
                        for m in st.session_state.ai_chat_history:
                            role = "user" if m["role"] == "user" else "model"
                            formatted_history.append(
                                types.Content(role=role, parts=[types.Part.from_text(text=m["content"])])
                            )
                            
                        chat = client.chats.create(model='gemini-2.5-flash', config=config, history=formatted_history)
                        response = chat.send_message(full_prompt)
                        
                        st.markdown(response.text)
                        
                        st.session_state.ai_chat_history.append({"role": "user", "content": full_prompt})
                        st.session_state.ai_chat_history.append({"role": "assistant", "content": response.text})
                        st.session_state.ai_query_count += 1
                        st.rerun()
                        
                    except Exception as e:
                        error_msg = str(e)
                        if "429" in error_msg or "Quota exceeded" in error_msg:
                            st.warning("⏳ 喔喔！您問得太快了！免費額度限制為「每分鐘 5 次」。請稍等 1 分鐘後再試一次喔！")
                        else:
                            st.error(f"❌ AI 發生異常: {e}")
