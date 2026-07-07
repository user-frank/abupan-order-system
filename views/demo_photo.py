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
    """透過隧道將照片傳入 5TB 雲端硬碟"""
    try:
        b64_str = base64.b64encode(file_bytes).decode('utf-8')
        
        payload = {
            "folder_id": FOLDER_ID,
            "file_name": filename,
            "mime_type": "image/jpeg",
            "image_base64": b64_str
        }
        
        res = requests.post(GAS_URL, json=payload, timeout=30)
        data = res.json()
        
        if data.get("status") == "success":
            # 🌟 破解 Google 防盜連：改用 Thumbnail API 格式！
            return f"https://drive.google.com/thumbnail?id={data['file_id']}&sz=w1000"
        else:
            st.error(f"上傳失敗：{data.get('message')}")
            return None
    except Exception as e:
        st.error(f"上傳通道發生異常：{e}")
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

    # 🌟 【影像修復黑魔法】：解除 app.py 帶來的高度封印
    st.markdown("""
    <style>
    /* 1. 讓相簿區的圖片維持真實比例，不要被壓扁成 220px */
    div[data-testid="stImage"] img {
        height: auto !important;
        max-height: 500px !important; /* 限制最高不要超過半個螢幕，方便滑動 */
        object-fit: contain !important; /* 保留完整圖片，不裁切 */
    }
    
    /* 2. 當老闆點擊「全螢幕放大」時，徹底解放高度限制，顯示超大原圖！ */
    div[data-testid="stFullScreenFrame"] img {
        height: 100vh !important;
        max-height: 100vh !important;
        object-fit: contain !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
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
            
            # 🌟 權限切換：老闆多了一個「部門篩選器」！
            if "老闆" in test_role:
                col1, col2 = st.columns(2)
                with col1:
                    date_filter = st.date_input("🗓️ 選擇調閱日期：", value=datetime.today())
                with col2:
                    # 去資料庫撈出所有有上傳過照片的部門
                    all_depts = ["顯示全部"] + list(db["dept"].astype(str).unique())
                    dept_filter = st.selectbox("🏢 選擇部門：", all_depts)
            else:
                min_date = datetime.today().replace(day=1)
                max_date = datetime.today()
                date_filter = st.date_input("🗓️ 選擇調閱日期 (限本月)：", value=max_date, min_value=min_date, max_value=max_date)
                dept_filter = DEPT_NAME # 員工強制只能看自己的部門
            
            cat_filter = st.selectbox("📌 選擇分類：", ["顯示全部"] + categories)
            
            # 依據篩選器過濾照片庫
            view_db = db[db["date"] == date_filter.strftime("%Y-%m-%d")]
            
            if dept_filter != "顯示全部":
                view_db = view_db[view_db["dept"] == dept_filter]
                
            if cat_filter != "顯示全部":
                view_db = view_db[view_db["category"] == cat_filter]
                
            st.markdown(f"**共找到 {len(view_db)} 張相片**")
            st.divider()
            
            if not view_db.empty:
                cols = st.columns(2) 
                
                for idx, row in view_db.iterrows():
                    with cols[idx % 2]:
                        with st.container(border=True):
                            
                            # 🌟 強效救援：把舊的錯誤網址自動轉成正確的 Thumbnail API 網址
                            display_url = str(row["photo_url"])
                            if "/uc?id=" in display_url:
                                display_url = display_url.replace("/uc?id=", "/thumbnail?id=") + "&sz=w1000"
                            
                            # 顯示圖片！
                            st.image(display_url, use_container_width=True)
                            
                            st.markdown(f"""
                            <div style='font-size:13px; color:#ddd;'>
                                🏢 <b>部門：</b>{row['dept']}<br>
                                🏷️ <b>分類：</b>{row['category']}<br>
                                👤 <b>上傳者：</b>{row['uploader']} ({row['time']})
                            </div>
                            """, unsafe_allow_html=True)
