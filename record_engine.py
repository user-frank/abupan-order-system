import pandas as pd
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import os

# ==========================================
# ☁️ 雲端資料庫設定
# ==========================================
SHEET_NAME = "阿布潘出餐系統_雲端資料庫"
WORKSHEET_NAME = "daily_records"

@st.cache_resource
def get_gspread_client():
    """取得 Google Sheets 連線客戶端 (升級防彈雙刀流：本機檔案優先)"""
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    try:
        # 🚦 順序對調：本機開發優先！如果有 json 檔案，直接用它，絕對不要碰 st.secrets 避免觸發系統報錯
        if os.path.exists("google-credentials.json"):
            creds = Credentials.from_service_account_file("google-credentials.json", scopes=scopes)
        
        # ☁️ 雲端環境備用：如果本機沒有實體檔案（代表未來上雲端了），才去讀取網頁後台的保險箱
        else:
            try:
                if "gcp_service_account" in st.secrets:
                    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
                else:
                    st.error("❌ 找不到雲端保險箱 (gcp_service_account) 設定！")
                    return None
            except Exception:
                st.error("❌ 找不到任何有效的憑證來源 (未偵測到 google-credentials.json 且保險箱為空)！")
                return None
                
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ 資料庫連線失敗: {e}")
        return None

def get_worksheet():
    client = get_gspread_client()
    if client:
        try:
            return client.open(SHEET_NAME).worksheet(WORKSHEET_NAME)
        except Exception as e:
            st.error(f"❌ 找不到指定的試算表或工作表: {e}")
    return None

def _get_cloud_dataframe(sheet):
    """將雲端試算表下載並轉換為 Pandas DataFrame 供系統運算"""
    try:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if df.empty:
            # 如果試算表剛建立，幫它補上表頭
            headers = sheet.row_values(1)
            if not headers:
                headers = ['date', 'cart_key', 'item_id', 'name', 'cat', 'ordered_qty', 'actual_qty', 'pos_qty']
                sheet.append_row(headers)
            df = pd.DataFrame(columns=headers)
            
        # 強制轉字串，避免數字與字串比對錯誤
        if 'cart_key' in df.columns:
            df['cart_key'] = df['cart_key'].astype(str)
        if 'date' in df.columns:
            df['date'] = df['date'].astype(str)
        return df
    except Exception as e:
        st.error(f"❌ 讀取雲端資料失敗: {e}")
        return pd.DataFrame()

def _sync_to_cloud(sheet, df):
    """將運算完的 DataFrame 覆寫回雲端試算表 (雙版本相容防彈版)"""
    try:
        sheet.clear() # 先清空舊資料
        df_safe = df.fillna("") # 填補空值
        
        # 🛡️ 確保所有資料轉為字串，避免數字型態傳給 Google 時引發崩潰
        headers = df_safe.columns.astype(str).values.tolist()
        body = df_safe.astype(str).values.tolist()
        data_to_upload = [headers] + body
        
        try:
            # 適用於最新版本的 gspread (v6.x)
            sheet.update(data_to_upload)
        except Exception:
            # 適用於較舊版本的 gspread (v5.x)
            sheet.update('A1', data_to_upload)
            
    except Exception as e:
        # 💡 印在終端機 (cmd) 裡面！這招就不會被網頁的 rerun 給刷掉
        print(f"\n❌ [系統警告] 雲端同步失敗，原因：{e}\n")
        st.error(f"❌ 雲端同步失敗：{e}")

# ==========================================
# 以下為系統核心存取功能 (已全面接軌 Google Sheets)
# ==========================================
def load_daily_record(date_str):
    sheet = get_worksheet()
    if not sheet: return pd.DataFrame()
    
    df = _get_cloud_dataframe(sheet)
    if df.empty: return df
    
    # 篩選出特定日期的單據
    df_filtered = df[df['date'] == str(date_str)].copy()
    
    # 相容性裝甲
    if 'cart_key' not in df_filtered.columns and 'item_id' in df_filtered.columns:
        df_filtered['cart_key'] = df_filtered['item_id'].astype(str) + "_" + df_filtered['name']
        
    return df_filtered

def save_ordered_data(date_str, cart_items):
    sheet = get_worksheet()
    if not sheet: return
    
    df = _get_cloud_dataframe(sheet)
    
    # 遍歷購物車，檢查要覆蓋還是新增
    for cart_key, item in cart_items.items():
        mask = (df['date'] == str(date_str)) & (df['cart_key'] == str(cart_key))
        if mask.any():
            idx = df[mask].index[0]
            df.at[idx, 'ordered_qty'] = int(item['qty'])
        else:
            new_row = {
                'date': str(date_str),
                'cart_key': str(cart_key),
                'item_id': str(item['item_id']),
                'name': str(item['name']),
                'cat': str(item['cat']),
                'ordered_qty': int(item['qty']),
                'actual_qty': 0,
                'pos_qty': 0
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            
    _sync_to_cloud(sheet, df)

def update_record_qty(date_str, cart_key, field, new_qty):
    sheet = get_worksheet()
    if not sheet: return
    
    df = _get_cloud_dataframe(sheet)
    mask = (df['date'] == str(date_str)) & (df['cart_key'] == str(cart_key))
    if mask.any():
        idx = df[mask].index[0]
        df.at[idx, field] = int(new_qty)
        _sync_to_cloud(sheet, df)

def delete_order_item(date_str, cart_key):
    sheet = get_worksheet()
    if not sheet: return
    
    df = _get_cloud_dataframe(sheet)
    mask = (df['date'] == str(date_str)) & (df['cart_key'] == str(cart_key))
    if mask.any():
        df = df[~mask] # 反向篩選，等同於刪除
        _sync_to_cloud(sheet, df)

def batch_update_record_qty(date_str, updates_dict):
    """【營運中心批次儲存專用】"""
    sheet = get_worksheet()
    if not sheet: return
    
    df = _get_cloud_dataframe(sheet)
    updated = False
    
    for cart_key, new_qty in updates_dict.items():
        mask = (df['date'] == str(date_str)) & (df['cart_key'] == str(cart_key))
        if mask.any():
            idx = df[mask].index[0]
            df.at[idx, 'actual_qty'] = int(new_qty)
            updated = True
            
    if updated:
        _sync_to_cloud(sheet, df)
