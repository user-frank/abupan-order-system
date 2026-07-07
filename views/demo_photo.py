import streamlit as st
import pandas as pd
from datetime import datetime
import io
from PIL import Image, ImageOps
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.service_account import Credentials
from record_engine import get_gspread_client, SHEET_NAME

# ==========================================
# ⚙️ 設定區
# ==========================================
# 🌟 請把你在 Google Drive 建立的資料夾 ID 貼在這裡！
FOLDER_ID = "1axu-8dPpCkYLjNqOvc6rYeTO2rDcbM7n"

# ==========================================
# 📸 影像處理與上傳引擎
# ==========================================
def compress_image(uploaded_file):
    """將高畫質照片壓縮到適合網頁快速讀取的大小，修復 PNG 當機問題"""
    img = Image.open(uploaded_file)
    img = ImageOps.exif_transpose(img)
    
    # 🌟 核心修復：如果圖片有透明背景(PNG)，強制轉換為 RGB，避免存成 JPEG 時當機！
    if img.mode in ("RGBA", "P"):
        img = img = img.convert("RGB")
        
    img.thumbnail((1024, 1024))
    
    output = io.BytesIO()
    img.save(output, format="JPEG", quality=85)
    return output.getvalue()

def upload_photo_to_drive(file_bytes, filename):
    """將壓縮後的圖片上傳至 Google Drive，並回傳可以直接顯示的圖片網址"""
    try:
        # 1. 驗證身分
        scopes = ['https://www.googleapis.com/auth/drive.file']
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
        service = build('drive', 'v3', credentials=creds)

        # 2. 準備上傳
        media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype='image/jpeg', resumable=True)
        file_metadata = {'name': filename, 'parents': [FOLDER_ID]}

        # 3. 執行上傳並取得檔案 ID
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        file_id = file.get('id')

        # 4. 開啟權限讓網頁可以直接讀取圖片
        service.permissions().create(fileId=file_id, body={'type': 'anyone', 'role': 'reader'}).execute()

        # 5. 回傳可以直接放在 st.image() 裡的專屬連結
        return f"https://drive.google.com/uc?id={file_id}"
    except Exception as e:
        st.error(f"上傳 Google Drive 失敗：{e}")
        return None

def save_photo_record_to_sheet(records):
    """將照片的網址與資訊寫入 Google 試算表"""
    client = get_gspread_client()
    if not client: return False
    
    try:
        spreadsheet = client.open(SHEET_NAME)
        try:
            sheet = spreadsheet.worksheet("photo_records")
        except:
            # 如果沒有這個表，自動建立
            sheet = spreadsheet.add_worksheet(title="photo_records", rows="1000", cols="10")
            sheet.append_row(["date", "dept", "category", "uploader", "time", "photo_url"])
            
        # 將資料轉成二維陣列寫入
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
    
    # 🌟 為了方便你測試，我做了一個「視角切換器」
    test_role = st.radio("👀 切換測試視角：", ["🧑‍🍳 現場員工 (只能看本月)", "👑 老闆 (可看全部)"], horizontal=True)

    tab_upload, tab_view = st.tabs(["📤 1. 上傳照片", "🖼️ 2. 檢視歷史相簿"])

    # ==========================================
    # 分頁 1：上傳照片 (現場員工視角)
    # ==========================================
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
                        
                        # 1. 壓縮照片
                        compressed_bytes = compress_image(file)
                        
                        # 2. 丟上 Google Drive
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
                    
                    # 3. 把網址紀錄寫進 Google 試算表
                    if new_records:
                        status_text.text("正在寫入資料庫...")
                        if save_photo_record_to_sheet(new_records):
                            status_text.text("✅ 所有照片上傳完畢！")
                            st.success(f"成功將 {len(uploaded_files)} 張照片存入雲端資料庫！")
                        else:
                            status_text.text("❌ 資料庫寫入失敗。")

    # ==========================================
    # 分頁 2：檢視相簿 (依角色動態顯示)
    # ==========================================
    with tab_view:
        # 去試算表把紀錄抓下來
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
            # 🌟 核心：依據角色設定日期過濾器
            st.markdown("#### 🔍 歷史影像調閱")
            
            if "老闆" in test_role:
                # 老闆可以選任何日期
                date_filter = st.date_input("🗓️ 選擇調閱日期：", value=datetime.today())
            else:
                # 員工只能選這個月的日期 (防呆限制)
                min_date = datetime.today().replace(day=1)
                max_date = datetime.today()
                date_filter = st.date_input("🗓️ 選擇調閱日期 (限本月)：", value=max_date, min_value=min_date, max_value=max_date)
            
            cat_filter = st.selectbox("📌 選擇分類：", ["顯示全部"] + categories)
            
            # 過濾資料
            view_db = db[db["date"] == date_filter.strftime("%Y-%m-%d")]
            if cat_filter != "顯示全部":
                view_db = view_db[view_db["category"] == cat_filter]
                
            st.markdown(f"**共找到 {len(view_db)} 張相片**")
            st.divider()
            
            if not view_db.empty:
                # 🌟 瀑布流照片牆
                cols = st.columns(2) 
                
                for idx, row in view_db.iterrows():
                    with cols[idx % 2]:
                        with st.container(border=True):
                            # 讀取 Google Drive 網址直接顯示
                            st.image(row["photo_url"], use_container_width=True)
                            
                            st.markdown(f"""
                            <div style='font-size:13px; color:#ddd;'>
                                🏷️ <b>分類：</b>{row['category']}<br>
                                👤 <b>上傳者：</b>{row['uploader']} ({row['time']})
                            </div>
                            """, unsafe_allow_html=True)
