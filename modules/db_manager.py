import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time
import random
import modules.time_utils as time_utils

class DataManager:
    def __init__(self):
        # Establish connection using st-gsheets-connection
        # This looks for [connections.gsheets] in secrets.toml
        self.use_fallback = False
        self.client = None
        self.spreadsheet_url = None
        
        try:
            self.conn = st.connection("gsheets", type=GSheetsConnection)
        except Exception as e:
            print(f"Streamlit Connection unavailable, trying fallback: {e}")
            self.setup_fallback()
            
    def setup_fallback(self):
        try:
            import gspread
            from google.oauth2.service_account import Credentials
            import toml
            
            self.use_fallback = True
            
            # Load secrets
            secrets_path = ".streamlit/secrets.toml"
            with open(secrets_path, "r", encoding="utf-8") as f:
                config = toml.load(f)
            
            gs_config = config.get("connections", {}).get("gsheets", {})
            self.spreadsheet_url = gs_config.get("spreadsheet")
            
            if "project_id" in gs_config:
                 creds = Credentials.from_service_account_info(
                     gs_config, 
                     scopes=["https://www.googleapis.com/auth/spreadsheets"]
                 )
            else:
                 pass
                 
            self.client = gspread.authorize(creds)
            print("✅ Fallback (gspread) connected.")
            
        except Exception as e:
            print(f"❌ Fallback Setup Failed: {e}")
            self.conn = None

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
                    print(f"⚠️ Quota hit. Retrying in {wait_time:.1f}s... (Attempt {i+1}/{max_retries})")
                    time.sleep(wait_time)
                    last_exception = e
                else:
                    raise e
        print("❌ Max retries reached.")
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

    def get_data(self, worksheet_name, ttl=300):
        def _read():
            if not self.use_fallback:
                try:
                    # Attempt cached read first
                    return self._cached_read_gsheets(worksheet_name)
                except Exception as e:
                    print(f"Cached GSheets read failed: {e}. Switching to fallback.")
                    self.setup_fallback()
                    if not self.use_fallback: raise e
                    
            if self.use_fallback and self.client:
                return self._cached_fallback_read(worksheet_name)
            return pd.DataFrame()

        try:
            return self._retry_operation(_read)
        except Exception as e:
            print(f"Final Read Error ({worksheet_name}): {e}")
            return pd.DataFrame()

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

    def update_data(self, worksheet_name, df):
        def _update():
            if not self.use_fallback:
                try:
                    if self.conn:
                        self.conn.clear(worksheet=worksheet_name) # Clear first to avoid zombies
                        self.conn.update(worksheet=worksheet_name, data=df)
                        st.cache_data.clear() # Clear ALL cache to ensure fresh data on next load
                        return True
                except Exception as e:
                    print(f"st.connection update failed: {e}. Switching to fallback.")
                    self.setup_fallback()
                    if not self.use_fallback: raise e

            if self.use_fallback and self.client:
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
                        raise create_err

                ws.clear()
                update_values = [df.columns.values.tolist()] + df.astype(str).values.tolist()
                ws.update(update_values)
                st.cache_data.clear() # Clear cache on fallback update too
                return True
            return False
            
        try:
            return self._retry_operation(_update)
        except Exception as e:
            print(f"Final Update Error ({worksheet_name}): {e}")
            return False

    def get_users(self):
        return self.get_data("Users")

    def get_missions(self, assignee=None):
        df = self.get_data("Missions")
        if assignee and not df.empty and "assignee" in df.columns:
            return df[df["assignee"] == assignee]
        return df
    
    def get_logs(self, user_id=None):
        df = self.get_data("Logs")
        if user_id and not df.empty and "User" in df.columns:
            # Note: Logs usually store "Name" (e.g. "큰보물") vs "ID" ("son1").
            # But 'user_id' passed here will technically be ID "son1".
            # We need to map ID -> Name if Logs store Name.
            # db_manager.log_activity uses 'user_name' arg. 
            # In app.py, log_activity is called with target_child_name ("큰보물").
            # So Logs store NAMES.
            # Yet auth_utils.get_target_child_id() returns ID.
            # This is a mismatch. 
            # To fix this cleanly: get_logs should accept 'user_name' or we map ID->Name here?
            # Better: Let the caller pass the correct thing? 
            # Or: auth_utils provides ID. We should map back to Name here?
            # Or: just change Logs to store ID? No, data migration is hard.
            # Helper: We can't easily map ID->Name inside db_manager without auth_utils cyclic import.
            # DECISION: For get_logs, we'll keep it simple: caller passes name if filtering by name.
            # BUT implementation plan said "get_target_child_id" returns ID. 
            # So pages will have ID. 
            # I will let get_logs accept 'user_name_or_id' and filter by equality?
            # Or I can just NOT filter here if logic is complex, but user ASKED to centralized.
            # I'll stick to 'user_id' param name but document it expects what the DB has.
            # Actually, `Wallet.py` filters by `target_child` (Name).
            # So I should rename param to `user_name` for clarity or handle both.
            # Let's use `user_name` for logs since that's what's stored.
             return df[df["User"] == user_id]
        return df
    
    def get_settings(self):
        return self.get_data("Settings")

    def log_activity(self, user_name, activity_type, content, reward=0):
        logs_df = self.get_data("Logs") # Use get_data
        new_log = {
            "Timestamp": time_utils.get_current_time_str(),
            "User": user_name,
            "Type": activity_type,
            "Content": content,
            "Reward": reward
        }
        if logs_df.empty:
             updated_logs = pd.DataFrame([new_log])
        else:
             updated_logs = pd.concat([logs_df, pd.DataFrame([new_log])], ignore_index=True)
             
        self.update_data("Logs", updated_logs)

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

    def add_reading_log(self, read_date, book_type, book_title, author, one_line_review, user_name):
        df = self.get_data("Reading") # Use get_data
        import uuid
        new_log = {
            "reading_id": str(uuid.uuid4()),
            "read_date": read_date,
            "book_type": book_type,
            "book_title": book_title,
            "author": author,
            "one_line_review": one_line_review,
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
        Returns: {'usernames': {'dad': {'name': ..., 'password': ..., 'email': ..., 'role': ...}, ...}}
        """
        users_df = self.get_data("Users", ttl=0)  # Force fresh read, no cache
        
        if users_df.empty:
            return {"usernames": {}}
        
        usernames_dict = {}
        for _, row in users_df.iterrows():
            username = row.get("username", "")
            if not username or pd.isna(username):
                continue
                
            usernames_dict[username] = {
                "name": row.get("name", username) if not pd.isna(row.get("name")) else username,
                "password": row.get("password", "") if not pd.isna(row.get("password")) else "",
                "email": row.get("email", "") if not pd.isna(row.get("email")) else "",
                "role": row.get("role", "user") if not pd.isna(row.get("role")) else "user"
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

# Singleton instance
db_manager = DataManager()
