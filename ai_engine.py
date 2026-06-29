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
        
        # 計算過去 7 天的日期區間
        today = datetime.now()
        past_7_days = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, 8)]
        
        # 過濾出該部門、且在過去 7 天內的紀錄
        history_df = df[(df['cat'] == dept_name) & (df['date'].isin(past_7_days))].copy()
        
        if history_df.empty: return "過去 7 天尚無營業紀錄可供分析。"
        
        # 轉換為數字格式以便計算
        history_df['ordered_qty'] = pd.to_numeric(history_df['ordered_qty'], errors='coerce').fillna(0)
        history_df['pos_qty'] = pd.to_numeric(history_df['pos_qty'], errors='coerce').fillna(0)
        
        # 計算「差異 (耗損或短少)」: 預估出餐 - POS真實銷售
        history_df['waste_qty'] = history_df['ordered_qty'] - history_df['pos_qty']
        
        # 將資料按商品進行壓縮加總 (類似機器學習的特徵工程)
        analysis_df = history_df.groupby('name').agg(
            總銷售量=('pos_qty', 'sum'),
            最高單日銷售=('pos_qty', 'max'),
            平均每日銷售=('pos_qty', 'mean'),
            總報廢或短少=('waste_qty', 'sum')  # 正數代表做太多(報廢)，負數代表做太少(賣到缺貨)
        ).reset_index()
        
        # 將分析結果轉成文字報告給 AI 看
        report_text = "【過去 7 天真實營運數據分析】：\n"
        for _, row in analysis_df.iterrows():
            waste_status = ""
            waste_val = row['總報廢或短少']
            if waste_val > 0:
                waste_status = f"⚠️做太多，累積報廢 {int(waste_val)} 份"
            elif waste_val < 0:
                waste_status = f"🔥做太少，累積缺貨/少賣 {int(abs(waste_val))} 份"
            else:
                waste_status = "✅抓得剛剛好"
                
            report_text += f"🔹 {row['name']}: 7天均銷 {row['平均每日銷售']:.1f} 份 (最高曾賣 {int(row['最高單日銷售'])} 份)。耗損狀況：{waste_status}。\n"
            
        return report_text
    except Exception as e:
        return f"調閱歷史資料失敗：{e}"

def render_ai_assistant(dept_name, display_df):
    """
    渲染 AI 聊天室模組
    dept_name: 所在部門 (例如 "生魚片")
    display_df: 該部門今天的出餐計畫表 DataFrame (包含品名、單價等)
    """
    if not init_ai():
        st.info("🤖 AI 數據顧問正在休假中 (尚未設定有效金鑰)。")
        return

    st.divider()
    
    # 🌟 流量控制
    if "ai_query_count" not in st.session_state: st.session_state.ai_query_count = 0
    if "ai_chat_history" not in st.session_state: st.session_state.ai_chat_history = []

    remaining_quota = 3 - st.session_state.ai_query_count
    
    st.markdown(f"#### 🤖 {dept_name}部 - AI 首席資料分析師 (聯網+大數據版)")
    st.markdown(f"<p style='font-size:12px; color:#888;'>💡 支援搜尋天氣預報，並會自動調閱過去7天 POS 歷史報廢紀錄給予精準備料建議！(剩餘額度: <span style='color:#f37021;font-weight:bold;'>{remaining_quota}</span> 次)</p>", unsafe_allow_html=True)

    with st.container(border=True):
        for msg in st.session_state.ai_chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if st.session_state.ai_query_count >= 3:
            st.warning("✋ 您本次的 AI 詢問額度已達上限。若需繼續提問，請重新登入！")
            return

        prompt = st.chat_input("例：幫我查明天台中天氣，並根據過去7天歷史紀錄，建議我鮭魚跟甜蝦該備多少量？")
        
        if prompt:
            with st.chat_message("user"):
                st.markdown(prompt)
            st.session_state.ai_chat_history.append({"role": "user", "content": prompt})

            # 🌟 讀取今日菜單報價
            today_str = datetime.now().strftime("%Y-%m-%d")
            menu_info = ""
            for _, row in display_df.iterrows():
                item_price = int(row.get('price', 0))
                menu_info += f"- {row['name']} (單價: {item_price}元)\n"

            with st.chat_message("assistant"):
                with st.spinner("🤖 AI 正在調閱雲端歷史紀錄與查詢氣象中..."):
                    try:
                        # 🌟 觸發外掛大腦：抓取過去 7 天歷史分析
                        history_report = get_recent_7_days_history(dept_name)
                        
                        system_instruction = f"""
                        你現在是阿布潘水產【{dept_name}部】的首席 AI 資料分析師。
                        今天是 {today_str}，你的地點在台灣台中市。
                        
                        【最高權限與安全隔離限制】：
                        1. 只能處理【{dept_name}部】的業務。嚴禁跨部門回答。
                        2. 絕對禁止回答政治、寫程式等無關話題。

                        【今日 {dept_name}部 菜單資料庫 (包含長期平均實力)】：
                        {menu_info}
                        
                        【⚠️ 雲端資料庫傳回的過去 7 天真實營運紀錄 (近期脈搏)】：
                        {history_report}

                        【你的專業分析任務指南 (極度重要)】：
                        1. 員工詢問備料建議時，你必須先運用 Google 搜尋工具，查詢「台灣交通部中央氣象署 台中市 明日天氣預報」。
                        2. 【雙軌交叉比對】：你必須結合「長期平日均銷」與「過去 7 天真實耗損」來精算！
                           - 基準線：以菜單資料庫中的「歷史平日均銷」為出發點。
                           - 近期微調：如果過去 7 天紀錄顯示「⚠️做太多，累積報廢」，代表近期買氣衰退，請勇敢將建議數量砍低於歷史均銷。
                           - 天氣微調：若預報為下雨，再往下調降 10%~20%。若為好天氣，則可維持或微幅上調。
                        3. 如果員工請你算出營業額，請確實將你建議的數量乘上菜單裡的單價，加總並加上千分位逗號。
                        4. 回答要展現出「資料分析師」的專業，明確告訴員工你是如何綜合「長期均銷 + 近期報廢狀況 + 明日天氣」得出這個數字的。
                        """

                        # 呼叫 Google Gemini AI 並開啟「搜尋引擎」
                        model = genai.GenerativeModel(
                            model_name='gemini-1.5-flash',
                            system_instruction=system_instruction,
                            tools='google_search_retrieval' 
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
                        st.error(f"❌ AI 發生異常: {e}。請確認您的 API 金鑰額度與設定。")
