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
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    try:
        if os.path.exists("google-credentials.json"):
            creds = Credentials.from_service_account_file("google-credentials.json", scopes=scopes)
        else:
            try:
                if "gcp_service_account" in st.secrets:
                    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
                else:
                    st.error("❌ 找不到雲端保險箱 (gcp_service_account) 設定！")
                    return None
            except Exception:
                st.error("❌ 找不到任何有效的憑證來源！")
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
    try:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        expected_cols = ['date', 'cart_key', 'item_id', 'name', 'cat', 'ordered_qty', 'actual_qty', 'pos_qty', 'pos_revenue', 'price', 'plan_operator', 'plan_time', 'report_operator', 'report_time']
        
        if df.empty:
            headers = sheet.row_values(1)
            if not headers:
                headers = expected_cols
                sheet.append_row(headers)
            df = pd.DataFrame(columns=headers)
            
        for col in ['plan_operator', 'plan_time', 'report_operator', 'report_time']:
            if col not in df.columns: df[col] = "未記錄"
        for col in ['pos_revenue', 'price']:
            if col not in df.columns: df[col] = 0
                
        if 'cart_key' in df.columns: df['cart_key'] = df['cart_key'].astype(str)
        if 'date' in df.columns: df['date'] = df['date'].astype(str)
            
        return df
    except Exception as e:
        # 🚨 【核心防護修復】：發生錯誤時，回傳 None 而不是空的表單！
        st.error(f"❌ 讀取雲端資料發生異常: {e}")
        return None

def _sync_to_cloud(sheet, df):
    try:
        sheet.clear()
        df_safe = df.fillna("")
        headers = df_safe.columns.astype(str).values.tolist()
        body = df_safe.astype(str).values.tolist()
        data_to_upload = [headers] + body
        
        try:
            sheet.update(data_to_upload)
        except Exception:
            sheet.update('A1', data_to_upload)
            
    except Exception as e:
        print(f"\n❌ [系統警告] 雲端同步失敗，原因：{e}\n")
        st.error(f"❌ 雲端同步失敗：{e}")

# ==========================================
# 系統核心存取功能
# ==========================================
def load_daily_record(date_str):
    sheet = get_worksheet()
    if not sheet: return pd.DataFrame()
    
    df = _get_cloud_dataframe(sheet)
    
    # 防護：如果回傳 None，代表讀取失敗，回傳空表給前端顯示，但絕不覆寫
    if df is None or df.empty: 
        return pd.DataFrame()
    
    df_filtered = df[df['date'] == str(date_str)].copy()
    if 'cart_key' not in df_filtered.columns and 'item_id' in df_filtered.columns:
        df_filtered['cart_key'] = df_filtered['item_id'].astype(str) + "_" + df_filtered['name']
        
    return df_filtered

def save_ordered_data(date_str, cart_items):
    sheet = get_worksheet()
    if not sheet: return
    
    df = _get_cloud_dataframe(sheet)
    
    # 🛡️ 【絕對防護鎖】：如果讀取失敗，強制攔截存檔動作，保護歷史資料！
    if df is None:
        st.error("🚨 雲端資料庫連線不穩！為保護歷史資料安全，已自動攔截本次存檔。請稍後再試！")
        return
    
    for cart_key, item in cart_items.items():
        mask = (df['date'] == str(date_str)) & (df['cart_key'] == str(cart_key))
        if mask.any():
            idx = df[mask].index[0]
            df.at[idx, 'ordered_qty'] = int(item['qty'])
            df.at[idx, 'plan_operator'] = str(item.get('operator', '未記錄'))
            df.at[idx, 'plan_time'] = str(item.get('update_time', '未記錄'))
            df.at[idx, 'price'] = int(item.get('price', 0))
        else:
            new_row = {
                'date': str(date_str),
                'cart_key': str(cart_key),
                'item_id': str(item['item_id']),
                'name': str(item['name']),
                'cat': str(item['cat']),
                'ordered_qty': int(item['qty']),
                'actual_qty': 0,
                'pos_qty': 0,
                'pos_revenue': 0, 
                'price': int(item.get('price', 0)), 
                'plan_operator': str(item.get('operator', '未記錄')),
                'plan_time': str(item.get('update_time', '未記錄')),
                'report_operator': "未記錄",
                'report_time': "未記錄"
            }
            if df.empty:
                df = pd.DataFrame([new_row])
            else:
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                
    _sync_to_cloud(sheet, df)

def update_record_qty(date_str, cart_key, field, new_qty):
    sheet = get_worksheet()
    if not sheet: return
    df = _get_cloud_dataframe(sheet)
    
    if df is None: return # 🛡️ 防護鎖
    
    mask = (df['date'] == str(date_str)) & (df['cart_key'] == str(cart_key))
    if mask.any():
        idx = df[mask].index[0]
        df.at[idx, field] = int(new_qty)
        _sync_to_cloud(sheet, df)

def delete_order_item(date_str, cart_key):
    sheet = get_worksheet()
    if not sheet: return
    df = _get_cloud_dataframe(sheet)
    
    if df is None: return # 🛡️ 防護鎖
    
    mask = (df['date'] == str(date_str)) & (df['cart_key'] == str(cart_key))
    if mask.any():
        df = df[~mask]
        _sync_to_cloud(sheet, df)

def batch_update_record_qty(date_str, updates_dict, current_user="", current_time=""):
    sheet = get_worksheet()
    if not sheet: return
    df = _get_cloud_dataframe(sheet)
    
    # 🛡️ 絕對防護鎖
    if df is None:
        st.error("🚨 雲端資料庫連線不穩！為保護歷史資料安全，已自動攔截本次回報。請稍後再試！")
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
            
    if updated:
        _sync_to_cloud(sheet, df)
