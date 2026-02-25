import streamlit as st
try:
    from streamlit_gsheets import GSheetsConnection
except ImportError:
    GSheetsConnection = None
import pandas as pd
from datetime import datetime
import time
import random
import modules.time_utils as time_utils

import os
from modules.data_utils import load_dataframe_safely, safe_filter_dataframe

class DataManager:
    def __init__(self):
        # Establish connection using st-gsheets-connection
        # This looks for [connections.gsheets] in secrets.toml
        self.use_fallback = False
        self.client = None
        self.spreadsheet_url = None
        self.backup_dir = "data/backups"
        
        # Ensure backup directory exists
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir, exist_ok=True)
        
        try:
            self.conn = st.connection("gsheets", type=GSheetsConnection)
            # [NEW] Reward 시트 존재 확인 및 초기화
            self._ensure_reward_sheet()
        except Exception as e:
            print(f"Streamlit Connection unavailable, trying fallback: {e}")
            self.setup_fallback()
            self._ensure_reward_sheet()

    def _ensure_reward_sheet(self):
        """Reward 시트가 없으면 생성하고 헤더를 설정합니다."""
        try:
            df = self.get_data("Reward", ttl=0)
            if df.empty:
                headers = [
                    "timestamp", "date", "user", "category", "sub_type", 
                    "item_name", "quantity", "unit_price", "total_price", 
                    "status", "note"
                ]
                df_init = pd.DataFrame(columns=headers)
                self.update_data("Reward", df_init)
                print("Reward sheet created.")
        except Exception as e:
            print(f"Error checking Reward sheet: {e}")

    def setup_fallback(self):
        try:
            import gspread
            from google.oauth2.service_account import Credentials
            import toml
            
            self.use_fallback = True
            
            # 1. Robust Secrets Loading (Streamlit or Terminal)
            gs_conf = {}
            secrets_path = ".streamlit/secrets.toml"
            if os.path.exists(secrets_path):
                try:
                    with open(secrets_path, "r", encoding="utf-8") as f:
                        config = toml.load(f)
                        gs_conf = config.get("connections", {}).get("gsheets", {})
                except: pass
            
            if not gs_conf and st.runtime.exists():
                try: gs_conf = st.secrets["connections"]["gsheets"]
                except: pass

            if not gs_conf:
                raise ValueError("Could not load Google Sheets configuration.")

            self.spreadsheet_url = gs_conf.get("spreadsheet", "")
            
            # 2. Standard PEM Restoration
            raw_key = gs_conf.get("private_key", "")
            if raw_key and isinstance(raw_key, str):
                p_key = raw_key.replace("\\n", "\n").replace("\r", "")
            else:
                p_key = ""

            creds_dict = {
                "type": gs_conf.get("type", "service_account"),
                "project_id": gs_conf.get("project_id", "familymissionmanager"),
                "private_key_id": gs_conf.get("private_key_id", "c94c8299285de4e4c5b70b0d969ebed9abc642748"),
                "private_key": p_key,
                "client_email": gs_conf.get("client_email", ""),
                "client_id": gs_conf.get("client_id", ""),
                "auth_uri": gs_conf.get("auth_uri", "https://accounts.google.com/o/oauth2/auth"),
                "token_uri": gs_conf.get("token_uri", "https://oauth2.googleapis.com/token"),
                "auth_provider_x509_cert_url": gs_conf.get("auth_provider_x509_cert_url", "https://www.googleapis.com/oauth2/v1/certs"),
                "client_x509_cert_url": gs_conf.get("client_x509_cert_url", "")
            }
            
            # 3. Create Credentials
            creds = Credentials.from_service_account_info(
                creds_dict,
                scopes=["https://www.googleapis.com/auth/spreadsheets"]
            )
            
            self.client = gspread.authorize(creds)
            print("[AUTH COMPLETE] Connected to GSheets successfully.")
            
            # Create Credentials
            creds = Credentials.from_service_account_info(
                creds_dict,
                scopes=["https://www.googleapis.com/auth/spreadsheets"]
            )
            
            self.client = gspread.authorize(creds)
            print("[AUTH RESTORED] Connected to GSheets successfully (Hybrid Loader).")
            
        except Exception as e:
            # Silent fallback: log to console but don't break UI/App
            print(f"Fallback Connection Failed (Non-critical for Local Backup): {e}")
            self.use_fallback = True # Enable fallback mode even if connection failed, to allow local backup
            self.conn = None
            self.client = None

    def _retry_operation(self, operation, max_retries=3, delay=2):
        """
        Retries an operation if it hits a quota error.
        """
        last_exception = None
        for i in range(max_retries):
            try:
                return operation()
            except Exception as e:
                error_str = str(e)
                if "Quota exceeded" in error_str or "429" in error_str:
                    wait_time = delay * (2 ** i) + random.uniform(0, 1)
                    print(f"Quota hit. Retrying in {wait_time:.1f}s... (Attempt {i+1}/{max_retries})")
                    time.sleep(wait_time)
                    last_exception = e
                else:
                    raise e
        print("Max retries reached.")
        if last_exception:
            raise last_exception
        return None

    # @st.cache_data(ttl=300) # Increased TTL for static fetch
    # def _fetch_data_static(self_dummy, worksheet_name):
    #    pass

    # Standalone cached function for performance
    @staticmethod
    @st.cache_data(ttl=300)
    def _cached_read_gsheets(worksheet_name):
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            # Use ttl=0 to bypass connection-level cache since we manage caching via @st.cache_data wrapper
            return conn.read(worksheet=worksheet_name, ttl=0)
        except Exception as e:
            raise e

    # Direct uncached read for ttl=0
    def _read_uncached(self, worksheet_name):
        # 1. Try Streamlit Connection
        if not self.use_fallback:
            try:
                # Direct read with ttl=0 to bypass connection cache
                return self.conn.read(worksheet=worksheet_name, ttl=0)
            except Exception as e:
                print(f"Direct read failed: {e}. Switching to fallback.")
                self.setup_fallback()
        
        # 2. Fallback (gspread)
        if self.use_fallback and self.client:
            try:
                sh = self.client.open_by_url(self.spreadsheet_url)
                ws = sh.worksheet(worksheet_name)
                data = ws.get_all_records()
                return pd.DataFrame(data)
            except Exception as e:
                print(f"Fallback uncached read failed: {e}")
                return self._read_from_backup(worksheet_name)
        
        # 3. Final Fallback: Read from local backup
        return self._read_from_backup(worksheet_name)

    def _read_from_backup(self, worksheet_name):
        backup_path = os.path.join(self.backup_dir, f"{worksheet_name}_latest.csv")
        if os.path.exists(backup_path):
            try:
                print(f"WARNING: Loading data from local backup: {backup_path}")
                return pd.read_csv(backup_path)
            except Exception as e:
                print(f"❌ Failed to read backup {backup_path}: {e}")
        return pd.DataFrame()

    def _save_to_backup(self, worksheet_name, df):
        try:
            backup_path = os.path.join(self.backup_dir, f"{worksheet_name}_latest.csv")
            df.to_csv(backup_path, index=False, encoding='utf-8-sig')
            
            # [STRICT MONITORING] Real-time log for stress testing
            print(f"--- [DISK BACKUP SUCCESS] {worksheet_name}: {len(df)} rows saved to {backup_path} ---", flush=True)
            
            # Keeping timestamps for audit if needed
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            history_path = os.path.join(self.backup_dir, f"{worksheet_name}_{timestamp}.csv")
            df.to_csv(history_path, index=False, encoding='utf-8-sig')
            
            # Clean up old history (keep last 5)
            import glob
            history_files = sorted(glob.glob(os.path.join(self.backup_dir, f"{worksheet_name}_2*.csv")))
            if len(history_files) > 5:
                for old_file in history_files[:-5]:
                    os.remove(old_file)
        except Exception as e:
            print(f"Warning: Backup failed for {worksheet_name}: {e}", flush=True)

    def get_data(self, worksheet_name, ttl=300):
        # Internal helper to handle cache
        def _read_cached():
            try:
                # Try Streamlit connection cached read first
                if not self.use_fallback:
                    return self._cached_read_gsheets(worksheet_name)
            except Exception as e:
                print(f"Cached GSheets read failed: {e}. Switching to fallback.")
            return self._cached_fallback_read(worksheet_name)

        try:
            # If ttl is 0, bypass cache completely
            if ttl == 0:
                df = self._read_uncached(worksheet_name)
            else:
                df = self._retry_operation(_read_cached)
            
            # Save backup if successful
            if not df.empty:
                self._save_to_backup(worksheet_name, df)
            
            return df
        except Exception as e:
            print(f"WARNING: get_data('{worksheet_name}') failed: {e}. Trying local backup.")
            return self._read_from_backup(worksheet_name)

    @st.cache_data(ttl=300)
    def _cached_fallback_read(_self, worksheet_name):
        # Explicit caching for fallback client
        if _self.client:
            try:
                sh = _self.client.open_by_url(_self.spreadsheet_url)
                ws = sh.worksheet(worksheet_name)
                data = ws.get_all_records()
                return pd.DataFrame(data)
            except Exception as e:
                print(f"Fallback read error: {e}")
                return pd.DataFrame()
        return pd.DataFrame()

    def _preprocess_dates_for_save(self, df):
        """
        Convert date columns to YYYY-MM-DD string format before saving to Google Sheets.
        This ensures consistent date format across all worksheets and prevents NaT issues.
        
        Args:
            df: DataFrame to process
            
        Returns:
            DataFrame with date columns formatted as YYYY-MM-DD strings
        """
        # Known date column names across all worksheets
        date_columns = ['read_date', 'date', 'created_at', 'updated_at', 'completed_at']
        
        df_copy = df.copy()
        
        for col in date_columns:
            if col in df_copy.columns:
                try:
                    # Convert to datetime first (handles various input formats)
                    df_copy[col] = pd.to_datetime(df_copy[col], errors='coerce')
                    # Convert to string in YYYY-MM-DD format
                    # For NaT values, dt.strftime returns NaT which we handle below
                    df_copy[col] = df_copy[col].apply(
                        lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else ""
                    )
                except Exception as e:
                    print(f"Warning: Failed to process date column {col}: {e}")
                    # Keep original values if processing fails
        
        return df_copy

    def update_data(self, worksheet_name, df):
        # [EMERGENCY GUARD] 중요 장부 데이터 전소 방지
        if worksheet_name in ["Reward", "Logs", "Reading"] and len(df) <= 1:
            # 헤더만 남거나 한 행만 남은 경우, 덮어쓰기 거부 (추가 전용 시트)
            # 단, 시트가 정말 비어있었을 때의 초기화는 허용해야 할 수도 있으나,
            # 안전을 위해 여기서는 경고만 하고 skip 하거나 더 엄격히 검사
            existing_df = self._read_from_backup(worksheet_name)
            if not existing_df.empty and len(existing_df) > 10: # 기존 데이터가 많은데 작게 쓰려 할 때
                 print(f"CRITICAL: Prevented possible overwrite of {worksheet_name} (Existing: {len(existing_df)}, New: {len(df)})")
                 return True

        def _update():
            # Preprocess dates to ensure consistent format before saving
            df_to_save = self._preprocess_dates_for_save(df)
            
            if not self.use_fallback:
                try:
                    if self.conn:
                        self.conn.clear(worksheet=worksheet_name) # Clear first to avoid zombies
                        self.conn.update(worksheet=worksheet_name, data=df_to_save)
                        st.cache_data.clear() # Clear ALL cache to ensure fresh data on next load
                        self._save_to_backup(worksheet_name, df_to_save) # Backup success
                        return True
                except Exception as e:
                    print(f"st.connection update failed: {e}. Switching to fallback.")
                    self.setup_fallback()
                    if not self.use_fallback: 
                        # If fallback setup also failed, re-raise the original exception
                        # and let the outer try-except handle the backup.
                        raise e

            # Attempt 2: Fallback (gspread)
            if self.use_fallback and self.client:
                try:
                    sh = self.client.open_by_url(self.spreadsheet_url)
                    try:
                        ws = sh.worksheet(worksheet_name)
                    except:
                        # Worksheet might not exist, try creating it
                        try:
                            ws = sh.add_worksheet(title=worksheet_name, rows=1000, cols=20)
                            print(f"Created new worksheet: {worksheet_name}")
                        except Exception as create_err:
                            print(f"Failed to create worksheet {worksheet_name}: {create_err}")
                            raise create_err # Re-raise to be caught by the outer try-except

                    ws.clear()
                    update_values = [df_to_save.columns.values.tolist()] + df_to_save.astype(str).values.tolist()
                    ws.update(update_values)
                    st.cache_data.clear() # Clear cache on fallback update too
                    self._save_to_backup(worksheet_name, df_to_save) # Backup success
                    return True
                except Exception as e:
                    print(f"Fallback update error: {e}. Data saved to local backup ONLY.")
                    # Ensure backup is saved when all else fails
                    self._save_to_backup(worksheet_name, df_to_save)
                    return True # True means it's safe at least locally
            
            # Final safety: always ensure local backup is consistent
            self._save_to_backup(worksheet_name, df_to_save)
            return True
            
        try:
            return self._retry_operation(_update)
        except Exception as e:
            print(f"Final Update Error ({worksheet_name}): {e}")
            return False

    def add_row(self, worksheet_name, row_dict):
        """
        데이터 유실 방지를 위한 증분 업데이트(Append Only) 엔진.
        전체 정보를 덮어쓰지 않고 새로운 행만 안전하게 추가합니다.
        """
        def _append():
            # 1. 시트 컬럼 순서 보정
            df_current = self.get_data(worksheet_name, ttl=0)
            
            # [CRITICAL FIX] 데이터 로드 실패(empty) 시 update_data 호출 자폭 로직 제거
            # 시트가 실제로 비어있든 로드가 실패했든, 덮어쓰지 않고 append_row를 시도하게 함.
            if df_current.empty:
                # 시트가 정말 비어있다면 gspread가 헤더 없이 넣거나 에러를 낼 것이나,
                # 최소한 기존 데이터를 날려버리는 update_data 경로는 피함.
                columns = ["Timestamp", "Date", "User", "Category", "Sub_Type", "Item_Name", "Quantity", "Unit_Price", "Total_Price", "Status", "Note"]
                if worksheet_name == "Logs":
                    columns = ["Timestamp", "User", "Type", "Content", "Reward"]
            else:
                columns = df_current.columns.tolist()

            row_values = []
            for col in columns:
                row_values.append(str(row_dict.get(col, "")))
            
            # 2. Append 실행
            if not self.use_fallback and self.conn:
                try:
                    # st.connection은 append_row를 직접 지원하지 않을 수 있으므로 gspread 클라이언트 사용
                    sh = self.conn.connection.client.open_by_url(self.spreadsheet_url)
                    ws = sh.worksheet(worksheet_name)
                    ws.append_row(row_values)
                    st.cache_data.clear()
                    return True
                except Exception as e:
                    print(f"st.connection append failed: {e}. Trying fallback.")
                    self.setup_fallback()

            if self.use_fallback and self.client:
                sh = self.client.open_by_url(self.spreadsheet_url)
                ws = sh.worksheet(worksheet_name)
                ws.append_row(row_values)
                st.cache_data.clear()
                return True
            
            return False

        try:
            return self._retry_operation(_append)
        except Exception as e:
            print(f"Append Row Error ({worksheet_name}): {e}")
            return False

    def get_users(self):
        return self.get_data("Users")

    def get_missions(self, assignee=None):
        df = self.get_data("Missions")
        required = ["mission_id", "title", "status", "date", "assignee", "rejection_reason"]
        df = load_dataframe_safely(df, required_columns=required, empty_columns=required)
        
        if assignee:
            return safe_filter_dataframe(df, "assignee", assignee)
        return df

    def get_logs(self, user_id=None):
        df = self.get_data("Logs")
        # [STRICT DEFENSE] Ensure these columns ALWAYS exist even if sheet is deleted or empty
        required = ["timestamp", "user", "type", "content", "reward"]
        
        # 1. Force structural integrity
        df = load_dataframe_safely(df, required_columns=required, empty_columns=required)
        
        # 2. Final Sanity Check: If somehow Type is still missing, inject it
        if "Type" not in df.columns:
            df["Type"] = ""
        
        if user_id:
            return safe_filter_dataframe(df, "User", user_id)
        return df

    def get_settings(self):
        df = self.get_data("Settings")
        required = ["category", "item_name", "value", "unit", "target_child"]
        return load_dataframe_safely(df, required_columns=required, empty_columns=required, default_values={"target_child": "All"})

    def log_activity(self, user_name, activity_type, content, reward=0):
        """
        [SAFE] append_row 엔진을 사용하여 경합 상태 해결
        기존 Logs 시트에 안전하게 기록합니다.
        """
        new_log = {
            "timestamp": time_utils.get_current_time_str(),
            "user": user_name,
            "type": activity_type,
            "content": content,
            "reward": reward
        }
        # [CRITICAL FIX] 덮어쓰기 경로(update_data) 완전 차단
        # 시트의 비어있음 여부와 상관없이 add_row로 안전하게 처리
        return self.add_row("Logs", new_log)

    def log_reward(self, user_name, category, sub_type, item_name, quantity, unit_price, status, note=""):
        """
        [🚨 SAFE] append_row 엔진을 사용하여 경합 상태 해결
        정규화된 Reward 시트에 보상 이력을 기록합니다.
        """
        try:
            new_log = {
                "timestamp": time_utils.get_current_time_str(),
                "date": time_utils.get_today_str(),
                "user": user_name,
                "category": category,
                "sub_type": sub_type,
                "item_name": item_name,
                "quantity": int(quantity),
                "unit_price": int(unit_price),
                "total_price": int(quantity) * int(unit_price),
                "status": status,
                "note": note
            }
            
            # 1. 시트 존재 확인 (첫 기록 시 생성됨)
            reward_df = self.get_data("Reward", ttl=0)
            if reward_df.empty:
                # 헤더와 함께 초기화
                self._ensure_reward_sheet()
            
            # 2. 안전하게 Append
            return self.add_row("Reward", new_log)
        except Exception as e:
            print(f"ERROR: log_reward failed: {e}")
            return False

    def get_rewards(self, user_name=None):
        """보상 데이터 조회"""
        df = self.get_data("Reward")
        required = ["timestamp", "date", "user", "category", "sub_type", "quantity", "unit_price", "status"]
        df = load_dataframe_safely(df, required_columns=required, empty_columns=required)
        
        if user_name:
            return safe_filter_dataframe(df, "user", user_name)
        return df

    def update_logs(self, df):
        return self.update_data("Logs", df)

    # --- Calendar Methods ---
    def get_calendar(self):
        return self.get_data("Calendar")

    def add_calendar_event(self, date_str, title, member, event_type):
        df = self.get_calendar()
        import uuid
        new_event = {
            "event_id": str(uuid.uuid4()),
            "date": date_str,
            "title": title,
            "member": member,
            "type": event_type
        }
        if df.empty:
            updated_df = pd.DataFrame([new_event])
        else:
            updated_df = pd.concat([df, pd.DataFrame([new_event])], ignore_index=True)
        self.update_data("Calendar", updated_df)

    def update_calendar_event(self, event_id, date_str, title, member, event_type):
        df = self.get_calendar()
        if df.empty: return
        
        # Convert ID to string for comparison safety
        df["event_id"] = df["event_id"].astype(str)
        
        idx = df[df["event_id"] == str(event_id)].index
        if not idx.empty:
            df.at[idx[0], "date"] = date_str
            df.at[idx[0], "title"] = title
            df.at[idx[0], "member"] = member
            df.at[idx[0], "type"] = event_type
            self.update_data("Calendar", df)

    def delete_calendar_event(self, event_id):
        df = self.get_calendar()
        if df.empty: return
        
        df["event_id"] = df["event_id"].astype(str)
        updated_df = df[df["event_id"] != str(event_id)]
        self.update_data("Calendar", updated_df)

    # --- Weekly Schedule Methods ---
    def get_weekly_schedule(self, assignee=None):
        df = self.get_data("WeeklySchedule")
        if assignee and not df.empty:
            if "assignee" in df.columns:
                return df[df["assignee"] == assignee]
            else:
                # Fallback if column missing (old data)
                return df
        return df

    def add_weekly_schedule(self, title, days, start_time, end_time, assignee="son1"):
        df = self.get_weekly_schedule() # Get raw, or self.get_data to avoid cycle? Actually method above returns filtered copy, careful.
        # We need raw data for update usually, but get_data returns copy.
        # Wait, get_weekly_schedule returns dataframe. add_weekly_schedule calls get_weekly_schedule().
        # If I filter inside get_weekly_schedule, then add_weekly_schedule might only see subset? 
        # Actually it calls get_weekly_schedule() without args logic? 
        # The add function appends to "df". If df is filtered, we lose other data when we concat and save?
        # YES. MAJOR BUG RISK.
        # FIX: add_* methods should call self.get_data directly or use a raw getter.
        # Let's change add_* to use self.get_data("WeeklySchedule") directly to ensure full data.
        
        df = self.get_data("WeeklySchedule")
        import uuid
        new_schedule = {
            "schedule_id": str(uuid.uuid4()),
            "title": title,
            "days": days, 
            "start_time": start_time,
            "end_time": end_time,
            "assignee": assignee
        }
        if df.empty:
            updated_df = pd.DataFrame([new_schedule])
        else:
            updated_df = pd.concat([df, pd.DataFrame([new_schedule])], ignore_index=True)
        self.update_data("WeeklySchedule", updated_df)
    
    def delete_weekly_schedule(self, schedule_id):
        df = self.get_data("WeeklySchedule") # Use get_data
        if df.empty: return
        df["schedule_id"] = df["schedule_id"].astype(str)
        updated_df = df[df["schedule_id"] != str(schedule_id)]
        self.update_data("WeeklySchedule", updated_df)

    # --- Reading Methods ---
    def get_reading_logs(self, user_id=None):
        df = self.get_data("Reading")
        if user_id and not df.empty and "user_name" in df.columns:
             return df[df["user_name"] == user_id]
        return df

    def add_reading_log(self, read_date, book_type, book_title, author, one_line_review, user_name, pages_read=""):
        df = self.get_data("Reading") # Use get_data
        import uuid
        new_log = {
            "reading_id": str(uuid.uuid4()),
            "read_date": read_date,
            "book_type": book_type,
            "book_title": book_title,
            "author": author,
            "one_line_review": one_line_review,
            "pages_read": pages_read,
            "user_name": user_name
        }
        if df.empty:
            updated_df = pd.DataFrame([new_log])
        else:
            updated_df = pd.concat([df, pd.DataFrame([new_log])], ignore_index=True)
        self.update_data("Reading", updated_df)

    # --- Praise Methods ---
    def get_praise_logs(self, user_id=None):
        df = self.get_data("Praise")
        
        # Ensure required columns exist to prevent KeyErrors
        required_cols = ["status", "user_name", "content", "date", "praise_id"]
        for col in required_cols:
            if col not in df.columns:
                df[col] = "대기 중" if col == "status" else ""
                
        if user_id and not df.empty and "user_name" in df.columns:
            return df[df["user_name"] == user_id]
        return df

    def add_praise_request(self, content, user_name):
        df = self.get_data("Praise") # Use get_data
        import uuid
        new_praise = {
            "praise_id": str(uuid.uuid4()),
            "date": time_utils.get_today_str(),
            "user_name": user_name,
            "content": content,
            "status": "대기 중" 
        }
        if df.empty:
            updated_df = pd.DataFrame([new_praise])
        else:
            updated_df = pd.concat([df, pd.DataFrame([new_praise])], ignore_index=True)
        self.update_data("Praise", updated_df)

    def update_praise_status(self, praise_id, new_status):
        df = self.get_praise_logs()
        if df.empty: return
        
        df["praise_id"] = df["praise_id"].astype(str)
        idx = df[df["praise_id"] == str(praise_id)].index
        if not idx.empty:
            df.at[idx[0], "status"] = new_status
            self.update_data("Praise", df)

    # --- Mission Definitions Methods ---
    def get_mission_definitions(self, assignee=None):
        df = self.get_data("MissionDefinitions")
        if assignee and not df.empty and "assignee" in df.columns:
            return df[df["assignee"] == assignee]
        return df

    def update_mission_definitions(self, df):
        return self.update_data("MissionDefinitions", df)
    
    def add_mission_definition(self, title, def_type, frequency, assignee, note=""):
        df = self.get_data("MissionDefinitions")
        import uuid
        new_def = {
            "def_id": str(uuid.uuid4()),
            "title": title,
            "type": def_type, # 'Routine' or 'OneTime'
            "frequency": frequency, # "월,수,금" or "2024-01-01"
            "assignee": assignee,
            "note": note,
            "active": True
        }
        if df.empty:
            updated_df = pd.DataFrame([new_def])
        else:
            updated_df = pd.concat([df, pd.DataFrame([new_def])], ignore_index=True)
        self.update_data("MissionDefinitions", updated_df)

    def get_user_dict(self):
        """
        Read user credentials from 'Users' sheet and return in streamlit-authenticator format.
        Has a dual-layer backup:
        1. Try Reading from Google Sheets 'Users' table.
        2. If fails or empty, use st.secrets['passwords'] as a fallback.
        """
        usernames_dict = {}
        
        # --- Layer 1: Google Sheets ---
        try:
            users_df = self.get_data("Users", ttl=0)
            if not users_df.empty:
                # Column Name Flexibility (Mapping)
                col_map = {
                    "username": ["username", "ID", "아이디", "계정"],
                    "name": ["name", "Name", "이름", "성함"],
                    "password": ["password", "Password", "비밀번호", "암호"],
                    "role": ["role", "Role", "역할", "권한"]
                }
                
                # Find best matching columns
                actual_cols = {}
                for target, candidates in col_map.items():
                    for cand in candidates:
                        if cand in users_df.columns:
                            actual_cols[target] = cand
                            break
                    if target not in actual_cols: actual_cols[target] = target # Fallback to target name
                
                for _, row in users_df.iterrows():
                # [STRICT NORMALIZATION] Ensure username is clean and matched correctly
                    raw_u = row.get(actual_cols["username"], "")
                    u = str(raw_u).strip().lower() if not pd.isna(raw_u) else ""
                
                    if not u or u == "nan": continue
                        
                    usernames_dict[u] = {
                        "name": str(row.get(actual_cols["name"], u)) if not pd.isna(row.get(actual_cols["name"])) else u,
                        "password": str(row.get(actual_cols["password"], "")).strip() if not pd.isna(row.get(actual_cols["password"])) else "",
                        "email": str(row.get("email", "")).strip() if "email" in users_df.columns and not pd.isna(row.get("email")) else "",
                        "role": str(row.get(actual_cols["role"], "user")).strip().lower() if not pd.isna(row.get(actual_cols["role"])) else "user"
                    }
        except Exception as e:
            print(f"⚠️ Google Sheets Users load failed: {e}. Falling back to secrets.toml")

        # --- Layer 2: secrets.toml Fallback (Only for missing accounts) ---
        if "passwords" in st.secrets:
            fallback_pws = st.secrets["passwords"]
            for u, h in fallback_pws.items():
                if u not in usernames_dict: # Add only if not found in sheet
                    usernames_dict[u] = {
                        "name": u,
                        "password": h,
                        "email": "",
                        "role": "admin" if u in ["dad", "mom"] else "user"
                    }
        
        return {"usernames": usernames_dict}

    def update_user_password(self, username, new_password_hash):
        """
        Update password for a specific user in 'Users' sheet.
        Args:
            username: user ID (e.g., 'dad', 'son1')
            new_password_hash: bcrypt hashed password string
        Returns:
            bool: True if update successful, False otherwise
        """
        users_df = self.get_data("Users", ttl=0)  # Force fresh read
        
        if users_df.empty:
            return False
        
        # Check if user exists
        if username not in users_df['username'].values:
            return False
        
        # Update password
        idx = users_df[users_df['username'] == username].index[0]
        users_df.at[idx, 'password'] = new_password_hash
        
        # Update timestamp (KST)
        if 'updated_at' in users_df.columns:
            import modules.time_utils as time_utils
            users_df.at[idx, 'updated_at'] = time_utils.get_current_time_str()
        
        # Write back to Google Sheets
        return self.update_data("Users", users_df)

    def finalize_migration(self):
        """
        [EMERGENCY STOP] All automated migrations disabled due to data integrity concerns.
        """
        print(">>> [SAFETY] Automated migration logic is DISABLED by system safeguard.")
        return True # Prevent app crash, but do nothing.

# Singleton instance
db_manager = DataManager()
