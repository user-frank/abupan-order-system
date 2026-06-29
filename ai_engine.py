import streamlit as st
import google.generativeai as genai
import pandas as pd
from datetime import datetime, timedelta

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

def get_recent_7_days_history(dept_name):
    """🧠 AI 的外掛大腦：自動調閱過去 7 天的真實銷售與耗損紀錄"""
    try:
        sheet = get_worksheet()
        if not sheet: return "無雲端資料庫連線。"
        
        df = _get_cloud_dataframe(sheet)
        if df is None or df.empty: return "資料庫目前尚無歷史紀錄。"
        
        today = datetime.now()
        past_7_days = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, 8)]
        
        # 🌟 【最高權限解鎖】：如果老闆呼叫，就不限制部門，全部調閱！
        if dept_name == "總管理處":
            history_df = df[df['date'].isin(past_7_days)].copy()
        else:
            history_df = df[(df['cat'] == dept_name) & (df['date'].isin(past_7_days))].copy()
        
        if history_df.empty: return "過去 7 天尚無營業紀錄可供分析。"
        
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
        
        report_text = "【過去 7 天真實營運數據分析】：\n"
        for _, row in analysis_df.iterrows():
            waste_status = ""
            waste_val = row['總報廢或短少']
            if waste_val > 0: waste_status = f"⚠️做太多，累積報廢 {int(waste_val)} 份"
            elif waste_val < 0: waste_status = f"🔥做太少，缺貨 {int(abs(waste_val))} 份"
            else: waste_status = "✅抓得剛剛好"
                
            cat_prefix = f"[{row['cat']}] " if 'cat' in row else ""
            report_text += f"🔹 {cat_prefix}{row['name']}: 7天均銷 {row['平均每日銷售']:.1f} 份 (最高曾賣 {int(row['最高單日銷售'])} 份)。耗損狀況：{waste_status}。\n"
            
        return report_text
    except Exception as e:
        return f"調閱歷史資料失敗：{e}"

def render_ai_assistant(dept_name, display_df):
    if not init_ai():
        st.info("🤖 AI 數據顧問正在休假中 (尚未設定有效金鑰)。")
        return

    st.divider()
    
    if "ai_query_count" not in st.session_state: st.session_state.ai_query_count = 0
    if "ai_chat_history" not in st.session_state: st.session_state.ai_chat_history = []

    remaining_quota = 5 - st.session_state.ai_query_count
    
    # 🌟 根據權限渲染不同的 UI 標題
    if dept_name == "總管理處":
        st.markdown(f"#### 👑 總管理處 - 首席 AI 營運戰略幕僚")
        st.markdown(f"<p style='font-size:12px; color:#888;'>💡 擁有全公司最高讀取權限！支援跨部門營運分析與戰略建議。(本次登入剩餘額度: <span style='color:#f37021;font-weight:bold;'>{remaining_quota}</span> 次)</p>", unsafe_allow_html=True)
        placeholder_text = "例：幫我比較各部門最近哪項商品報廢最嚴重？並給出調整建議。"
    else:
        st.markdown(f"#### 🤖 {dept_name}部 - AI 首席資料分析師 (大數據版)")
        st.markdown(f"<p style='font-size:12px; color:#888;'>💡 自動調閱過去7天歷史報廢紀錄給予精準備料建議！(剩餘額度: <span style='color:#f37021;font-weight:bold;'>{remaining_quota}</span> 次)</p>", unsafe_allow_html=True)
        placeholder_text = "例：根據過去7天歷史紀錄，建議我鮭魚跟甜蝦該備多少量？"

    with st.container(border=True):
        for msg in st.session_state.ai_chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if st.session_state.ai_query_count >= 5:
            st.warning("✋ 您本次的 AI 詢問額度已達上限。若需繼續提問，請重新登入！")
            return

        prompt = st.chat_input(placeholder_text)
        
        if prompt:
            with st.chat_message("user"):
                st.markdown(prompt)
            st.session_state.ai_chat_history.append({"role": "user", "content": prompt})

            today_str = datetime.now().strftime("%Y-%m-%d")
            menu_info = ""
            for _, row in display_df.iterrows():
                item_price = int(row.get('price', 0))
                wd_avg = row.get('wd_avg', 0) 
                cat_prefix = f"[{row.get('cat', dept_name)}] " if dept_name == "總管理處" else ""
                menu_info += f"- {cat_prefix}{row['name']} (單價: {item_price}元, 歷史長期平日均銷: {wd_avg}份)\n"

            with st.chat_message("assistant"):
                with st.spinner("🤖 AI 正在調閱雲端歷史紀錄與精算中..."):
                    try:
                        history_report = get_recent_7_days_history(dept_name)
                        
                        # 🌟 根據權限進行不同的 AI 靈魂洗腦
                        if dept_name == "總管理處":
                            system_instruction = f"""
                            你現在是阿布潘水產的【總管理處首席 AI 營運戰略幕僚】。
                            今天是 {today_str}。
                            
                            【最高權限解鎖】：
                            1. 你擁有全公司所有部門的最高讀取權限，可以針對跨部門的業績、耗損、商品單價進行綜合分析與比較。
                            2. 你的回答層次必須具備「老闆視角」，以提升營收、降低報廢、優化跨部門資源為主。
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
                        
                        【⚠️ 雲端資料庫傳回的過去 7 天真實營運紀錄 (近期脈搏)】：
                        {history_report}

                        【你的專業分析任務指南 (極度重要)】：
                        1. 【雙軌交叉比對】：你必須結合「長期平日均銷」與「過去 7 天真實耗損(做太多/做太少)」精算建議。
                           - 基準線：以菜單資料庫中的「歷史長期平日均銷」為出發點。
                           - 近期微調：如果過去 7 天紀錄顯示「⚠️做太多，累積報廢」，代表近期買氣衰退，請勇敢將建議數量砍低於歷史均銷。
                           - 近期微調：如果過去 7 天紀錄顯示「🔥做太少，缺貨」，請建議增加備料。
                        2. 如果員工請你算出營業額，請確實將你建議的數量乘上菜單裡的單價，加總並加上千分位逗號。
                        3. 回答要專業、有說服力（必須引述你看到的歷史耗損數據，或是你算出的營業額），並加上 Emoji 讓排版好讀。
                        """

                        # 🌟 徹底修復：回歸最穩定、支援系統指令的標準模型，拔除容易報錯的聯網套件
                        model = genai.GenerativeModel(
                            model_name='gemini-2.5-flash', 
                            system_instruction=system_instruction
                        )
                        
                        history = []
                        for m in st.session_state.ai_chat_history[:-1]:
                            role = "user" if m["role"] == "user" else "model"
                            history.append({"role": role, "parts": [m["content"]]})
                            
                        chat = model.start_chat(history=history)
                        response = chat.send_message(prompt)
                        
                        st.markdown(response.text)
                        
                        st.session_state.ai_chat_history.append({"role": "assistant", "content": response.text})
                        st.session_state.ai_query_count += 1
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ AI 發生異常: {e}。請確認您的 Streamlit Secrets 金鑰是否正確！")
