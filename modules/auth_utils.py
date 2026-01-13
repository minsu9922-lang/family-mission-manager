import streamlit as st
import streamlit_authenticator as stauth
import toml
import os
import bcrypt
from modules.db_manager import db_manager

def get_auth_config():
    """
    Constructs the authentication configuration dictionary.
    Now reads from Google Sheets 'Users' table via db_manager (DB-based).
    Cookie settings still from st.secrets for security.
    """
    try:
        # Get user credentials from DB
        credentials = db_manager.get_user_dict()
        
        # Get cookie settings from secrets (not in DB for security)
        cookie_config = {
            "expiry_days": st.secrets.get("auth", {}).get("cookie_expiry_days", 30),
            "key": st.secrets.get("auth", {}).get("cookie_key", "random_signature_key"),
            "name": st.secrets.get("auth", {}).get("cookie_name", "family_app_cookie")
        }
            
        # Structure for authenticator
        return {
            "credentials": credentials,
            "cookie": cookie_config
        }
    except Exception as e:
        st.error(f"Error loading auth config from DB: {e}")
        # Fallback: try to read from secrets.toml
        return st.secrets

def get_authenticator():
    """
    Initializes and returns the authenticator object.
    """
    config = get_auth_config()
    
    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days'],
    )
    return authenticator

def check_login(authenticator):
    """
    Checks current login status. 
    """
    if st.session_state.get("authentication_status") is not True:
        # Cleanup session
        for k in ["role", "target_child_name", "selected_child"]:
            if k in st.session_state: del st.session_state[k]
        
        try:
            authenticator.login(location="main")
        except Exception as e:
            st.error(f"Login Widget Error: {e}")
            return None

        if st.session_state.get("authentication_status") is False:
            st.error("❌ 아이디 또는 비밀번호가 올바르지 않습니다.")
            
        if st.session_state.get("authentication_status") is True:
             import time
             time.sleep(0.5)
             st.rerun()
             
    return st.session_state.get("authentication_status")

def get_user_id_map():
    return {
        "큰보물": "son1",
        "작은보물": "son2",
        "아빠": "dad",
        "엄마": "mom"
    }

def get_target_child_id():
    target_name = st.session_state.get("target_child_name", st.session_state.get("name", "User"))
    user_map = get_user_id_map()
    return user_map.get(target_name, "son1")

def change_password(username, new_password_plain):
    """
    Updates the password in Google Sheets 'Users' table (DB-based).
    Changes are immediately reflected across all devices.
    """
    import traceback
    try:
        st.write(f"[DEBUG] Starting password change for: {username}")
        
        # 1. Hash Password
        st.write("[DEBUG] Step 1: Hashing password...")
        hashed_bytes = bcrypt.hashpw(new_password_plain.encode('utf-8'), bcrypt.gensalt())
        hashed_pw = hashed_bytes.decode('utf-8')
        st.write(f"[DEBUG] Hash created: {hashed_pw[:15]}...")
        
        # 2. Update Database
        st.write("[DEBUG] Step 2: Calling db_manager.update_user_password()...")
        result = db_manager.update_user_password(username, hashed_pw)
        st.write(f"[DEBUG] DB update result: {result}")
        
        if result:
            return True, "비밀번호가 변경되었습니다. (모든 기기에 즉시 적용됨)"
        else:
            return False, "사용자를 찾을 수 없습니다."
            
    except Exception as e:
        st.error(f"[DEBUG] Exception caught: {type(e).__name__}")
        st.error(f"[DEBUG] Exception message: {str(e)}")
        st.code(traceback.format_exc())
        return False, f"오류 발생: {e}"
