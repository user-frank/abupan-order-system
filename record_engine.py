import pandas as pd
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import os
import time

# ==========================================
# ☁️ 雲端資料庫設定
# ==========================================
SHEET_NAME = "阿布潘出餐系統_雲端資料庫"
WORKSHEET_NAME = "daily_records"

@st.cache_resource
def get_gspread_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        if os.path.exists("google-credentials.json"):
            creds = Credentials.from_service_account_file("google-credentials.json", scopes=scopes)
        else:
            try:
                if "gcp_service_account" in st.secrets:
                    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
                else:
                    st.error("❌ 找不到雲端保險箱設定！")
                    return None
            except Exception:
                st.error("❌ 找不到任何有效的憑證來源！")
                return None
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ 資料庫連線失敗: {e}")
        return None

# 🌟 升級 1：快取工作表物件，減少 open() 造成的請求浪費
@st.cache_resource(ttl=3600)
def get_worksheet():
    client = get_gspread_client()
    if client:
        try:
            return client.open(SHEET_NAME).worksheet(WORKSHEET_NAME)
        except Exception as e:
            st.error(f"❌ 找不到指定的試算表: {e}")
            return None
    return None

# 🌟 升級 2：超級快取核心！30秒內無論系統要讀幾次，都不消耗 Google 額度！
@st.cache_data(ttl=30, show_spinner=False)
def get_cached_all_records():
    sheet = get_worksheet()
    if not sheet: return None
    try:
        return sheet.get_all_records()
    except Exception:
        return None

# 加入 sheet=None 參數，維持向下相容，不讓 ai_engine 報錯
def _get_cloud_dataframe(sheet=None):
    try:
        # 改從記憶體拿資料
        data = get_cached_all_records()
        if data is None:
            return None
            
        df = pd.DataFrame(data)
        
        expected_cols = ['date', 'cart_key', 'item_id', 'name', 'cat', 'ordered_qty', 'actual_qty', 'pos_qty', 'pos_revenue', 'price', 'plan_operator', 'plan_time', 'report_operator', 'report_time']
        
        if df.empty:
            sheet_obj = get_worksheet()
            if sheet_obj:
                headers = sheet_obj.row_values(1)
                if not headers:
                    headers = expected_cols
                    sheet_obj.append_row(headers)
            else:
                headers = expected_cols
            df = pd.DataFrame(columns=headers)
            
        for col in ['plan_operator', 'plan_time', 'report_operator', 'report_time']:
            if col not in df.columns: df[col] = "未記錄"
        for col in ['pos_revenue', 'price']:
            if col not in df.columns: df[col] = 0
                
        if 'cart_key' in df.columns: df['cart_key'] = df['cart_key'].astype(str)
        if 'date' in df.columns: df['date'] = df['date'].astype(str)
        
        if not df.empty and 'date' in df.columns:
            df = df[df['date'] != 'date'].copy()
            
        if not df.empty and 'date' in df.columns and 'cart_key' in df.columns:
            df = df.drop_duplicates(subset=['date', 'cart_key'], keep='last')
            
        return df
    except Exception as e:
        st.error(f"❌ 讀取雲端資料發生異常: {e}")
        return None

def _sync_to_cloud(sheet, df):
    df_safe = df.fillna("")
    headers = df_safe.columns.astype(str).values.tolist()
    body = df_safe.astype(str).values.tolist()
    data_to_upload = [headers] + body
    
    max_retries = 5
    for attempt in range(max_retries):
        try:
            sheet.clear()
            try:
                sheet.update(data_to_upload)
            except Exception:
                sheet.update('A1', data_to_upload)
                
            # 🌟 升級 3：成功寫入後，立刻清除快取！確保大家下一秒看到的都是最新資料！
            get_cached_all_records.clear()
            return 
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt) 
            else:
                st.error(f"❌ 雲端同步失敗，請稍後重試：{e}")

# ==========================================
# 系統核心存取功能
# ==========================================
def load_daily_record(date_str):
    df = _get_cloud_dataframe()
    if df is None or df.empty: return pd.DataFrame()
    
    df_filtered = df[df['date'] == str(date_str)].copy()
    if 'cart_key' not in df_filtered.columns and 'item_id' in df_filtered.columns:
        df_filtered['cart_key'] = df_filtered['item_id'].astype(str) + "_" + df_filtered['name']
        
    return df_filtered

def save_ordered_data(date_str, cart_items):
    sheet = get_worksheet()
    if not sheet: return
    
    df = _get_cloud_dataframe()
    if df is None:
        st.error("🚨 資料庫連線不穩，已攔截本次存檔。")
        return
    
    for cart_key, item in cart_items.items():
        mask = (df['date'] == str(date_str)) & (df['cart_key'] == str(cart_key))
        if mask.any():
            idx = df[mask].index[0]
            df.at[idx, 'ordered_qty'] = int(item['qty'])
            df.at[idx, 'plan_operator'] = str(item.get('operator', '未記錄'))
            df.at[idx, 'plan_time'] = str(item.get('update_time', '未記錄'))
            df.at[idx, 'price'] = int(item.get('price', 0))
            if 'actual_qty' in item: df.at[idx, 'actual_qty'] = int(item['actual_qty'])
            if 'report_operator' in item: df.at[idx, 'report_operator'] = str(item['report_operator'])
            if 'report_time' in item: df.at[idx, 'report_time'] = str(item['report_time'])
        else:
            new_row = {
                'date': str(date_str),
                'cart_key': str(cart_key),
                'item_id': str(item['item_id']),
                'name': str(item['name']),
                'cat': str(item['cat']),
                'ordered_qty': int(item['qty']),
                'actual_qty': int(item.get('actual_qty', 0)), 
                'pos_qty': 0,
                'pos_revenue': 0, 
                'price': int(item.get('price', 0)), 
                'plan_operator': str(item.get('operator', '未記錄')),
                'plan_time': str(item.get('update_time', '未記錄')),
                'report_operator': str(item.get('report_operator', '未記錄')),
                'report_time': str(item.get('report_time', '未記錄'))
            }
            if df.empty: df = pd.DataFrame([new_row])
            else: df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                
    _sync_to_cloud(sheet, df)

def update_record_qty(date_str, cart_key, field, new_qty):
    sheet = get_worksheet()
    if not sheet: return
    df = _get_cloud_dataframe()
    if df is None: return 
    mask = (df['date'] == str(date_str)) & (df['cart_key'] == str(cart_key))
    if mask.any():
        idx = df[mask].index[0]
        df.at[idx, field] = int(new_qty)
        _sync_to_cloud(sheet, df)

def delete_order_item(date_str, cart_key):
    sheet = get_worksheet()
    if not sheet: return
    df = _get_cloud_dataframe()
    if df is None: return 
    mask = (df['date'] == str(date_str)) & (df['cart_key'] == str(cart_key))
    if mask.any():
        df = df[~mask]
        _sync_to_cloud(sheet, df)

def batch_update_record_qty(date_str, updates_dict, current_user="", current_time=""):
    sheet = get_worksheet()
    if not sheet: return
    df = _get_cloud_dataframe()
    
    if df is None:
        st.error("🚨 連線不穩已攔截回報。")
        return 
        
    updated = False
    for cart_key, new_qty in updates_dict.items():
        mask = (df['date'] == str(date_str)) & (df['cart_key'] == str(cart_key))
        if mask.any():
            idx = df[mask].index[0]
            df.at[idx, 'actual_qty'] = int(new_qty)
            if current_user: df.at[idx, 'report_operator'] = str(current_user)
            if current_time: df.at[idx, 'report_time'] = str(current_time)
            updated = True
            
    if updated: _sync_to_cloud(sheet, df)
