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
        
        # Ensure minimal structure for streamlit-authenticator v0.3.0+
        if "usernames" not in credentials:
            credentials = {"usernames": {}}
            
        # Get cookie settings from secrets (not in DB for security)
        cookie_config = {
            "expiry_days": st.secrets.get("auth", {}).get("cookie_expiry_days", 30),
            "key": st.secrets.get("auth", {}).get("cookie_key", "random_signature_key"),
            "name": st.secrets.get("auth", {}).get("cookie_name", "family_app_cookie")
        }
            
        # Structure for authenticator (v0.3.0+ expects credentials, cookie, preauthorized)
        return {
            "credentials": credentials,
            "cookie": cookie_config,
            "preauthorized": {"emails": []}
        }
    except Exception as e:
        st.error(f"Error loading auth config from DB: {e}")
        # Fallback: try to read from secrets.toml or predefined
        return {
            "credentials": {"usernames": {}},
            "cookie": {"expiry_days": 30, "key": "fallback", "name": "fallback"},
            "preauthorized": {"emails": []}
        }

def get_authenticator():
    """
    Initializes and returns the authenticator object.
    Updated for streamlit-authenticator 0.4.2+
    """
    config = get_auth_config()
    
    authenticator = stauth.Authenticate(
        credentials=config['credentials'],
        cookie_name=config['cookie']['name'],
        cookie_key=config['cookie']['key'],
        cookie_expiry_days=config['cookie']['expiry_days'],
        preauthorized=config.get('preauthorized', {'emails': []})
    )
    return authenticator

def check_login(authenticator):
    """
    Checks current login status. 
    Updated for streamlit-authenticator 0.4.2+
    """
    if st.session_state.get("authentication_status") is not True:
        # Cleanup session on first load or failed status
        if "authentication_status" not in st.session_state or st.session_state.get("authentication_status") is None:
            for k in ["role", "target_child_name", "selected_child"]:
                if k in st.session_state: del st.session_state[k]
        
        try:
            # v0.4.x login() renders the widget in place
            authenticator.login()
        except Exception as e:
            st.error(f"인증 위젯 오류: {e}")
            return None

        if st.session_state.get("authentication_status") is False:
            st.error("❌ 아이디 또는 비밀번호가 올바르지 않습니다.")
            
        if st.session_state.get("authentication_status") is True:
             # Success! 
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
    try:
        # 1. Hash Password
        hashed_bytes = bcrypt.hashpw(new_password_plain.encode('utf-8'), bcrypt.gensalt())
        hashed_pw = hashed_bytes.decode('utf-8')
        
        # 2. Update Database
        if db_manager.update_user_password(username, hashed_pw):
            return True, "비밀번호가 변경되었습니다. (모든 기기에 즉시 적용됨)"
        else:
            return False, "사용자를 찾을 수 없습니다."
            
    except Exception as e:
        return False, f"오류 발생: {e}"
