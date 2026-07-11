import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import requests
import urllib3
import re


# 🌟 徹底拔除舊版，只保留 Google 最新的官方 AI 套件
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
    try:
        api_key = st.secrets["gemini_api_key"]
        if not api_key: return False
        return True
    except Exception:
        return False

@st.cache_data(ttl=1800, show_spinner=False)
def get_tomorrow_weather(city_name="臺中市", district_name="北屯區"):

    url = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-073"

    params = {
        "Authorization": CWA_API_KEY,
        "locationName": district_name,
        "format": "JSON"
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=15,
            verify=False
        )

        if response.status_code != 200:
            return {
                "status": "error",
                "msg": f"HTTP {response.status_code}\n{response.text}"
            }

        data = response.json()

        records = data.get("records") or data.get("Records") or {}

        locations = (
            records.get("locations")
            or records.get("Locations")
            or []
        )

        if len(locations) == 0:
            return {
                "status": "error",
                "msg": "找不到 locations"
            }

        location_list = (
            locations[0].get("location")
            or locations[0].get("Location")
            or []
        )

        target = None

        for loc in location_list:
            if loc.get("locationName") == district_name:
                target = loc
                break

        if target is None:
            return {
                "status": "error",
                "msg": f"找不到 {district_name}"
            }

        weather_elements = (
            target.get("weatherElement")
            or target.get("WeatherElement")
            or []
        )

        weather_dict = {}

        for item in weather_elements:
            weather_dict[item.get("elementName")] = item

        tomorrow = (
            datetime.now(TW_TZ)
            + timedelta(days=1)
        ).strftime("%Y-%m-%d")

        def get_value(element_name, period):

            try:

                element = weather_dict[element_name]

                times = element.get("time", [])

                target_times = [
                    t
                    for t in times
                    if t.get("startTime", "").startswith(tomorrow)
                ]

                if len(target_times) == 0:
                    return "未知"

                if period >= len(target_times):
                    period = -1

                values = target_times[period].get("elementValue", [])

                if len(values) == 0:
                    return "未知"

                return values[0].get("value", "未知")

            except Exception:
                return "未知"

        return {

            "status": "success",

            "location": f"{city_name}{district_name}",

            "date": tomorrow,

            "day": {
                "weather": get_value("天氣現象", 0),
                "temp": get_value("溫度", 0),
                "pop": get_value("12小時降雨機率", 0)
            },

            "night": {
                "weather": get_value("天氣現象", 1),
                "temp": get_value("溫度", 1),
                "pop": get_value("12小時降雨機率", 1)
            },

            "source": "中央氣象署 OpenData"

        }

    except Exception as e:

        return {
            "status": "error",
            "msg": str(e)
        }

def get_recent_history_report(dept_name, target_product=None):
    try:
        sheet = get_worksheet()
        if not sheet: return "無雲端資料庫連線。"
        
        df = _get_cloud_dataframe(sheet)
        if df is None or df.empty: return "資料庫目前尚無歷史紀錄。"

        # ====== 測試 ======
        st.write("目前所有部門：", df["cat"].unique())
        st.write("目前 dept_name：", dept_name)
        # ==================
        st.write("資料最早日期:", df['date'].min())
        st.write("資料最晚日期:", df['date'].max())
        st.write("總資料筆數:", len(df))
        
        tw_now = datetime.now(TW_TZ)
        past_days = [(tw_now - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, 31)]
        
        if dept_name == "總管理處":
            history_df = df[df['date'].isin(past_days)].copy()
        else:
            history_df = df[(df['cat'] == dept_name) & (df['date'].isin(past_days))].copy()

                # ===== 商品精準篩選 =====
        if target_product:
            history_df = history_df[
                history_df['name'].str.contains(
                    target_product,
                    na=False
                )
            ]

            st.write("目前搜尋商品:", target_product)
            st.write("篩選後資料筆數:", len(history_df))
        # ======================
        
        if history_df.empty: return "過去近期尚無營業紀錄可供分析。"
        
        for col in ['ordered_qty', 'actual_qty', 'pos_qty', 'pos_revenue', 'price']:
            history_df[col] = pd.to_numeric(history_df.get(col, 0), errors='coerce').fillna(0).astype(int)
            
        history_df = history_df.sort_values(by='date', ascending=False)
        weekdays_tw = ["一", "二", "三", "四", "五", "六", "日"]
        
        report_text = "【過去 30 天各單品真實營運數據】：\n"
        grouped = history_df.groupby(['cat', 'name'] if 'cat' in history_df.columns else 'name')
        
        for group_keys, item_df in grouped:
            item_name = group_keys[1] if isinstance(group_keys, tuple) else group_keys
            cat_prefix = f"[{group_keys[0]}] " if isinstance(group_keys, tuple) and dept_name == "總管理處" else ""
            
            report_text += f"\n🔹 {cat_prefix}{item_name}:\n"
            for _, row in item_df.iterrows():
                d_str = row['date']
                wd_str = weekdays_tw[datetime.strptime(d_str, "%Y-%m-%d").weekday()]
                
                o_qty, a_qty, p_qty, p_rev, price = row['ordered_qty'], row['actual_qty'], row['pos_qty'], row['pos_revenue'], row['price']
                
                status = ""
                ignore_for_ai = False

                # ===== 臨時取消出餐 =====
                if o_qty > 0 and a_qty == 0 and p_qty == 0:
                    status = "(⏸️ 臨時取消出餐，不納入AI分析)"
                    ignore_for_ai = True

                elif a_qty > o_qty and p_qty >= o_qty:
                    status = "(🔥 現場緊急追加)"
                
                elif a_qty > p_qty:
                    status = f"(⚠️ 報廢 {a_qty - p_qty} 份)"
                
                elif a_qty < p_qty:
                    status = f"(🚨 缺貨/超賣 {p_qty - a_qty} 份)"
                
                else:
                    status = "(✅ 完銷相符)"

                # 不把臨時取消出餐送給AI
                if ignore_for_ai:
                    continue
                    
                discount_status = ""
                if p_qty > 0 and price > 0:
                    full_price_revenue = p_qty * price
                    if p_rev < full_price_revenue * 0.95:
                        discount_status = f" [📉打折出清,約{int((p_rev / full_price_revenue) * 10)}折]"
                    
                report_text += f"   - {d_str}(週{wd_str}): 預估 {o_qty}, 實際 {a_qty}, POS賣出 {p_qty} {status}{discount_status}\n"
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
        
        target_df = df[df['date'].isin([today_str, tomorrow_str])].copy() if dept_name == "總管理處" else df[(df['cat'] == dept_name) & (df['date'].isin([today_str, tomorrow_str]))].copy()
        target_df['ordered_qty'] = pd.to_numeric(target_df['ordered_qty'], errors='coerce').fillna(0)
        target_df = target_df[target_df['ordered_qty'] > 0]
        
        if target_df.empty: return "目前尚未填寫今日或明日的預估。"
        
        report = "【目前資料庫中已建檔的出餐計畫】：\n"
        for d_str in [today_str, tomorrow_str]:
            day_df = target_df[target_df['date'] == d_str]
            if not day_df.empty:
                report += f"\n📅 {'今日' if d_str == today_str else '明日'} ({d_str}) 的預估出餐表：\n"
                for _, r in day_df.iterrows():
                    cat_prefix = f"[{r['cat']}] " if dept_name == "總管理處" else ""
                    report += f"- {cat_prefix}{r['name']}: 預計製作 {int(r['ordered_qty'])} 份\n"
        return report
    except: return ""

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
        placeholder_text = "例：幫我分析各部門明日備料是否合理？"
    else:
        st.markdown(f"#### 🤖 {dept_name}部 - AI 營運決策大腦")
        st.markdown(f"<p style='font-size:12px; color:#888;'>💡 內建思維決策鏈，嚴格控制報廢率並優化備料建議！(剩餘額度: <span style='color:#f37021;font-weight:bold;'>{remaining_quota}</span> 次)</p>", unsafe_allow_html=True)
        placeholder_text = "例：依據決策框架，建議明天熱銷品該備多少量？"

    with st.container(border=True):
        for msg in st.session_state.ai_chat_history:
            if msg["role"] == "user" and "【隱藏系統資料】" in msg["content"]:
                display_text = msg["content"].split("【使用者實際提問】\n")[-1]
                with st.chat_message("user"): st.markdown(display_text)
            else:
                with st.chat_message(msg["role"]): st.markdown(msg["content"])

        if st.session_state.ai_query_count >= 5:
            st.warning("✋ 本次 AI 詢問額度已達上限，請重整網頁 (F5)！")
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
                with st.spinner("🤖 套用 Prompt 企業決策框架模型思考中 ..."):
                    try:
                        weather_info = ""
                        weather_keywords = ["天氣", "下雨", "氣象", "雨", "晴", "颱風", "預估", "備料", "建議", "安排", "明天"]
                        if any(kw in prompt for kw in weather_keywords):
                            w_data = get_tomorrow_weather()
                            if isinstance(w_data, dict) and w_data.get("status") == "success":
                                weather_info = f"""
                                【系統即時資料】
                                以下資訊來自 {w_data['source']}，屬即時真實數據，請優先採用此資訊評估天氣對營運的影響，不可自行猜測修改。
                                📍 地點：{w_data['location']} | 日期：{w_data['date']}
                                ☀️ [白天] 天氣：{w_data['day']['weather']} | 溫度：{w_data['day']['temp']}℃ | 降雨機率：{w_data['day']['pop']}%
                                🌙 [晚上] 天氣：{w_data['night']['weather']} | 溫度：{w_data['night']['temp']}℃ | 降雨機率：{w_data['night']['pop']}%
                                """
                            else:
                                weather_info = f"\n【系統警告：中央氣象署目前無法取得資料，請不要自行猜測天氣，僅依據歷史銷售資料進行分析】\n"

                        target_product = None

                        for name in display_df["name"].dropna().unique():
                            if name in prompt:
                                target_product = name
                                break
                        
                        history_report = get_recent_history_report(
                            dept_name,
                            target_product
                        )
                        
                        st.text(history_report)
                        # ⭐ 新增：避免 Prompt 過長
                        if len(history_report) > 8000:
                            history_report = history_report[:8000] + "\n...(歷史資料已摘要)..."

                        current_plan_report = get_current_plans(dept_name)

                        # ⭐ 新增：避免 Prompt 過長
                        if len(current_plan_report) > 2000:
                            current_plan_report = current_plan_report[:2000]
                        
                        if dept_name == "總管理處":
                            role_prompt = f"你現在是阿布潘水產的【總管理處首席 AI 營運戰略幕僚】。今天是 {tw_now_str}，明天是 {tomorrow_wd}。擁有跨部門最高分析權限。絕對禁止回答無關話題。"
                        else:
                            role_prompt = f"你現在是阿布潘水產【{dept_name}部】的首席 AI 營運長。今天是 {tw_now_str}，明天是 {tomorrow_wd}。只能處理本部門業務。絕對禁止回答無關話題。"

                        system_instruction = f"""
                        {role_prompt}
                        
                        【營運目標與決策優先級】
                        你的核心任務是：協助降低報廢率、提高商品周轉率、提升毛利。
                        在給出備料建議時，必須【嚴格遵守】以下決策優先順序：
                        第一：避免重大缺貨造成營業損失 (守住基本盤)
                        第二：嚴格控制報廢率 (控制耗損)
                        第三：提高銷售機會
                        第四：追求合理最大營業額 (【嚴禁】為了衝高營業額而盲目建議爆量備料，禁止只追求銷售最大化)

                        【資料可信度排序】
                        請依照以下權重判斷真實狀況，若資料矛盾，以高權重為主：
                        最高：POS實際銷售 (市場真實需求)
                        第二：實際出餐數 (廚房真實產能)
                        第三：預估出餐數 (人為預期)
                        💡 備註：若實際出餐=50且POS=50，代表「可能缺貨」，而非市場需求只有50。

                        【時間衰減原則 (Time Decay Weighting)】
                        分析歷史資料時，請賦予不同時間點不同的權重：
                        - 最近 7 天：權重最高 (反映最新市場脈動)
                        - 8~21 天：次之 (近期平穩趨勢)
                        - 22~30 天：作為長期參考
                        絕對不可單純將 30 天的資料做算術平均！

                        【商品生命週期判斷】
                        給出建議前，請先在背景判斷該商品屬於何種型態：
                        A. 穩定熱銷品：銷量穩定，可提高備料信心。
                        B. 波動商品：每日差異大，建議保守。
                        C. 滯銷商品：長期下降或頻繁出現「📉打折出清」，必須大幅降低備料以保住毛利。
                        D. 新商品：歷史紀錄不足，不可過度推估。

                        【決策分析框架】
                        回答時，請【直接輸出分析結果】，不需要展示內部推理過程。請依循以下維度：
                        1. 歷史銷售基準 (比較過去同星期銷售，套用時間衰減)
                        2. 市場需求變化 (判斷近期成長或衰退)
                        3. 庫存風險 (評估缺貨與報廢風險)
                        4. 外部因素 (天氣降雨機率)
                        5. 毛利影響 (避免低效率打折備貨)

                        【決策獨立性與風險控制】
                        1. 不可因使用者期待某答案而修改數據。若使用者希望大幅增加備料，但資料顯示風險高(如：近期常報廢、明天下大雨)，你必須【明確提出反對意見】。
                        2. 任何增加備料的建議，【正常情況下不得超過近期同星期平均銷量的 20%】。除非遇特殊事件或近期連續嚴重缺貨，才允許突破限制，但必須說明原因。

                        【系統資料庫】
                        菜單與單價：\n{menu_info}
                        過去 30 天營運數據：\n{history_report}

                        【強制輸出格式】
                        當給予特定商品建議時，請嚴格套用以下 Markdown 格式回覆（務必維持換行與條列排版，請勿把所有文字擠在同一行）：
                        
                        - **🔸 【分析商品】**：(商品名稱)
                        - **📊 【歷史基準】**：(說明同星期平均、近期趨勢與商品生命週期)
                        - **☁️ 【天氣影響】**：(說明降雨或天氣對此商品的預估影響幅度)
                        - **🎯 【AI 建議量】**：XX 份 (預估總營收: NT$ XX)
                        - **💪 【預測信心】**：XX%
                        - **⚠️ 【風險與獨立見解】**：(說明主要風險，若強烈反對使用者的提議請寫在此)
                        
                        ---
                        若資料不足，請直言「無歷史數據可供分析」，嚴禁虛構。
                        
                        【系統資料交換格式 (極度重要)】
                        若你有提供任何商品的「建議數量」，在整個回答的【最底部】，必須輸出一段 JSON 格式資料供 Python 系統抓取，並用 <AI_DATA> 與 </AI_DATA> 標籤包起來。
                        格式如下 (必須為有效 JSON Array)：
                        <AI_DATA>
                        [
                          {{"product": "商品名稱", "prediction": 建議數量(整數), "confidence": 信心分數(整數,不含%), "weather_factor": "positive/negative/neutral", "risk": "low/medium/high"}}
                        ]
                        </AI_DATA>
                        """

                        client = genai.Client(api_key=st.secrets["gemini_api_key"])
                        config = types.GenerateContentConfig(system_instruction=system_instruction)
                        
                        hidden_context = f"【隱藏系統資料】\n{weather_info}\n{current_plan_report}\n【使用者實際提問】\n"
                        full_prompt = hidden_context + prompt

                        # ⭐ 只保留最近 6 則對話，避免 Context 無限成長
                        recent_history = st.session_state.ai_chat_history[-6:]

                        formatted_history = []

                        for m in recent_history:
                            role = "user" if m["role"] == "user" else "model"
                            formatted_history.append(
                                types.Content(
                                    role=role,
                                    parts=[types.Part.from_text(text=m["content"])]
                                )
                            )
                            
                        try:

                            chat = client.chats.create(
                                model="gemini-2.5-flash",
                                config=config,
                                history=formatted_history
                            )

                            response = chat.send_message(full_prompt)

                        except Exception as e:

                            st.exception(e)

                            raise
                        
                        # 🌟 新增過濾邏輯：把給使用者的文字，和給系統的 JSON 分開
                        raw_text = response.text
                        
                        # 使用正規表達式找尋 <AI_DATA> 標籤
                        ai_data_match = re.search(r"<AI_DATA>(.*?)</AI_DATA>", raw_text, re.DOTALL)
                        
                        if ai_data_match:
                            # 如果有找到標籤，把標籤整段從要顯示的文字中清掉
                            display_text = re.sub(r"<AI_DATA>.*?</AI_DATA>", "", raw_text, flags=re.DOTALL).strip()
                            
                            # 💡 你可以在這裡拿 json_string 去寫入資料庫，目前先把它隱藏
                            # json_string = ai_data_match.group(1).strip() 
                        else:
                            # 如果沒找到，就照常顯示
                            display_text = raw_text

                        # 只顯示乾淨的文字給使用者看
                        st.markdown(display_text)
                        
                        # 對話紀錄也只存入乾淨的文字，避免未來干擾 AI 判斷
                        # ⭐ 不要把完整隱藏資料存入聊天紀錄
                        st.session_state.ai_chat_history.append({
                            "role": "user",
                            "content": prompt
                        })
                        st.session_state.ai_chat_history.append({"role": "assistant", "content": display_text})
                        
                        st.session_state.ai_query_count += 1
                        st.rerun()
                        
                    except Exception as e:
                        error_msg = str(e)
                        if "429" in error_msg or "Quota exceeded" in error_msg:
                            st.warning("⏳ 喔喔！您問得太快了！免費額度限制為「每分鐘 5 次」。請稍等 1 分鐘後再試一次喔！")
                        elif "503" in error_msg or "high demand" in error_msg:
                            st.warning("🚦 Google AI 伺服器目前全球大塞車 (高負載)！請稍等 1 到 2 分鐘後再重新發問喔！")
                        else:
                            st.error(f"❌ AI 發生異常: {e}")
