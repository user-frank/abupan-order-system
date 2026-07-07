import streamlit as st
import pandas as pd
from datetime import datetime
import io
import base64
import requests
from PIL import Image, ImageOps
from record_engine import get_gspread_client, SHEET_NAME

# ==========================================
# ⚙️ 設定區
# ==========================================
# 🌟 1. 貼上你剛剛部署成功的 Apps Script 網址 (Web app URL)
GAS_URL = "https://script.google.com/macros/s/AKfycbzJVbW4al2ficgAX_5ac5H3OlLKkE_yIRqzCkZY2UTTxzq9zP2hcmk_rKHJAyZ-AvjBOw/exec"

# 🌟 2. 貼上你 Google Drive 建立的「阿布潘現場回報照片」資料夾 ID
FOLDER_ID = "1axu-8dPpCkYLjNqOvc6rYeTO2rDcbM7n"

# ==========================================
# 📸 影像處理與上傳引擎
# ==========================================
def compress_image(uploaded_file):
    """將高畫質照片壓縮，並修復 PNG 格式當機問題"""
    img = Image.open(uploaded_file)
    img = ImageOps.exif_transpose(img)
    
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
        
    img.thumbnail((1024, 1024))
    output = io.BytesIO()
    img.save(output, format="JPEG", quality=85)
    return output.getvalue()

def upload_photo_to_drive(file_bytes, filename):
    """🌟 升級版隧道：帶有強效除錯照妖鏡"""
    try:
        b64_str = base64.b64encode(file_bytes).decode('utf-8')
        
        payload = {
            "folder_id": FOLDER_ID,
            "file_name": filename,
            "mime_type": "image/jpeg",
            "image_base64": b64_str
        }
        
        # 呼叫專屬接應員
        res = requests.post(GAS_URL, json=payload, timeout=30)
        
        # 🌟 照妖鏡：如果 Google 回傳的不是 JSON，直接把 Google 說的話印出來！
        try:
            data = res.json()
        except Exception as e:
            st.error(f"❌ 解析失敗！Google 伺服器回傳了未知的內容。")
            st.code(res.text, language="html") # 把 Google 擋人的畫面印出來看
            return None
        
        if data.get("status") == "success":
            return f"https://drive.google.com/uc?id={data['file_id']}"
        else:
            st.error(f"❌ 上傳失敗 (Apps Script 錯誤)：{data.get('message')}")
            return None
            
    except Exception as e:
        st.error(f"❌ 隧道連線發生嚴重異常：{e}")
        return None

def save_photo_record_to_sheet(records):
    client = get_gspread_client()
    if not client: return False
    try:
        spreadsheet = client.open(SHEET_NAME)
        try:
            sheet = spreadsheet.worksheet("photo_records")
        except:
            sheet = spreadsheet.add_worksheet(title="photo_records", rows="1000", cols="10")
            sheet.append_row(["date", "dept", "category", "uploader", "time", "photo_url"])
            
        rows_to_add = [[r["date"], r["dept"], r["category"], r["uploader"], r["time"], r["photo_url"]] for r in records]
        sheet.append_rows(rows_to_add)
        return True
    except Exception as e:
        st.error(f"寫入試算表失敗：{e}")
        return False

# ==========================================
# 🏢 網頁主介面
# ==========================================
def show():
    current_user = st.session_state.get("user_name", "測試員")
    DEPT_NAME = "測試部"
    today_str = datetime.today().strftime("%Y-%m-%d")

    st.markdown("### 📸 現場紀實與照片回報測試")
    test_role = st.radio("👀 切換測試視角：", ["🧑‍🍳 現場員工 (只能看本月)", "👑 老闆 (可看全部)"], horizontal=True)

    tab_upload, tab_view = st.tabs(["📤 1. 上傳照片", "🖼️ 2. 檢視歷史相簿"])

    with tab_upload:
        with st.container(border=True):
            categories = ["分類_廢品紀錄", "分類_客訴處理", "分類_進貨驗收", "分類_環境清潔", "分類_其他"]
            selected_cat = st.selectbox("📌 請選擇照片分類：", categories)
            
            st.divider()
            
            uploaded_files = st.file_uploader(
                "📸 請點擊拍照或從相簿選擇 (支援多選)", 
                type=['png', 'jpg', 'jpeg'], 
                accept_multiple_files=True
            )
            
            if uploaded_files:
                if st.button("🚀 確認上傳至雲端", type="primary", use_container_width=True):
                    
                    new_records = []
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    for i, file in enumerate(uploaded_files):
                        status_text.text(f"正在壓縮與上傳第 {i+1} 張照片...")
                        
                        compressed_bytes = compress_image(file)
                        filename = f"{today_str}_{DEPT_NAME}_{selected_cat}_{i}.jpg"
                        
                        # 🌟 呼叫全新上傳隧道
                        drive_url = upload_photo_to_drive(compressed_bytes, filename)
                        
                        if drive_url:
                            new_records.append({
                                "date": today_str,
                                "dept": DEPT_NAME,
                                "category": selected_cat,
                                "uploader": current_user,
                                "time": datetime.now().strftime("%H:%M:%S"),
                                "photo_url": drive_url
                            })
                        
                        progress_bar.progress((i + 1) / len(uploaded_files))
                    
                    if new_records:
                        status_text.text("正在寫入資料庫...")
                        if save_photo_record_to_sheet(new_records):
                            status_text.text("✅ 所有照片上傳完畢！")
                            st.success(f"成功將 {len(uploaded_files)} 張照片存入雲端資料庫！")
                        else:
                            status_text.text("❌ 資料庫寫入失敗。")

    with tab_view:
        client = get_gspread_client()
        db = pd.DataFrame()
        if client:
            try:
                sheet = client.open(SHEET_NAME).worksheet("photo_records")
                db = pd.DataFrame(sheet.get_all_records())
            except:
                pass
        
        if db.empty:
            st.info("資料庫中尚無任何照片紀錄。")
        else:
            st.markdown("#### 🔍 歷史影像調閱")
            
            if "老闆" in test_role:
                date_filter = st.date_input("🗓️ 選擇調閱日期：", value=datetime.today())
            else:
                min_date = datetime.today().replace(day=1)
                max_date = datetime.today()
                date_filter = st.date_input("🗓️ 選擇調閱日期 (限本月)：", value=max_date, min_value=min_date, max_value=max_date)
            
            cat_filter = st.selectbox("📌 選擇分類：", ["顯示全部"] + categories)
            
            view_db = db[db["date"] == date_filter.strftime("%Y-%m-%d")]
            if cat_filter != "顯示全部":
                view_db = view_db[view_db["category"] == cat_filter]
                
            st.markdown(f"**共找到 {len(view_db)} 張相片**")
            st.divider()
            
            if not view_db.empty:
                cols = st.columns(2) 
                for idx, row in view_db.iterrows():
                    with cols[idx % 2]:
                        with st.container(border=True):
                            st.image(row["photo_url"], use_container_width=True)
                            st.markdown(f"""
                            <div style='font-size:13px; color:#ddd;'>
                                🏷️ <b>分類：</b>{row['category']}<br>
                                👤 <b>上傳者：</b>{row['uploader']} ({row['time']})
                            </div>
                            """, unsafe_allow_html=True)
