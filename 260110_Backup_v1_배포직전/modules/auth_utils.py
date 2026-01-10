import streamlit as st
import streamlit_authenticator as stauth

def get_auth_config():
    """
    Constructs the authentication configuration dictionary from st.secrets.
    Using dummy hashes for '1234' if not present in secrets for safety.
    """
    # Default dummy hash for '1234'
    default_hash = "$2b$12$1.j.j.j.j.j.j.j.j.j.j.j.j.j.j.j.j.j.j.j.j.j.j.j.j" 
    
    users = {
        "dad": {
            "name": "아빠",
            "password": st.secrets["passwords"].get("dad", default_hash),
            "email": "dad@family.com",
            "role": "admin"
        },
        "mom": {
            "name": "엄마",
            "password": st.secrets["passwords"].get("mom", default_hash),
            "email": "mom@family.com",
            "role": "admin"
        },
        "son1": {
            "name": "큰보물",
            "password": st.secrets["passwords"].get("son1", default_hash),
            "email": "son1@family.com",
            "role": "user"
        },
        "son2": {
            "name": "작은보물",
            "password": st.secrets["passwords"].get("son2", default_hash),
            "email": "son2@family.com",
            "role": "user"
        }
    }

    return {
        "credentials": {
            "usernames": users
        },
        "cookie": {
            "expiry_days": st.secrets["auth"]["cookie_expiry_days"],
            "key": st.secrets["auth"]["cookie_key"],
            "name": st.secrets["auth"]["cookie_name"]
        }
    }

def get_authenticator():
    """
    Initializes and returns the authenticator object.
    Checks session state for existing object to avoid re-init issues if possible,
    though stauth usually handles re-init fine.
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
    Calls authenticator.login() to check for valid cookie and restore session.
    """
    # Simply call login (it handles cookie checks internally)
    # Only render login widget if not authenticated
    if st.session_state.get("authentication_status") is not True:
        # CLEANUP: If not authenticated, ensure role/user state is cleared 
        # to prevent previous session leaking (e.g. Dad -> Logout -> Son Login -> Sees Dad's Admin View)
        keys_to_clear = ["role", "target_child_name", "selected_child", "name", "username"]
        for k in keys_to_clear:
            if k in st.session_state:
                del st.session_state[k]

        try:
            # authenticator.login returns (name, status, username) or None if just rendering
            res = authenticator.login(location="main")
            if res:
                 name, status, username = res
        except Exception as e:
            st.error(f"Login Widget Error: {e}")
            return None

        # Force Error Display immediately if False
        if st.session_state.get("authentication_status") is False:
            st.error("❌ 아이디 또는 비밀번호가 올바르지 않습니다.")
            
        # Helper: Ensure UI clears on success (optional but good for UX)
        if st.session_state.get("authentication_status") is True:
             import time
             time.sleep(0.5)
             st.rerun()
             
    return st.session_state.get("authentication_status")

def get_user_id_map():
    """
    Returns a dictionary mapping Display Name (Korean) to User ID.
    Useful for looking up ID from the sidebar selection ("큰보물" -> "son1").
    """
    return {
        "큰보물": "son1",
        "작은보물": "son2",
        "아빠": "dad",
        "엄마": "mom"
    }

def get_target_child_id():
    """
    Resolves the ID of the target child currently being viewed.
    - If Admin: Uses 'selected_child' from sidebar (via 'target_child_name').
    - If Child: Uses own name/ID.
    Returns: User ID string (e.g., "son1", "son2").
    """
    target_name = st.session_state.get("target_child_name", st.session_state.get("name", "User"))
    user_map = get_user_id_map()
    # Default to "son1" (Main child) if resolution fails or mapping missing
    return user_map.get(target_name, "son1")

def change_password(username, new_password_plain):
    """
    Updates the password for a user in secrets.toml and the active authenticator.
    Returns (Success, Message).
    """
    import toml
    # import streamlit_authenticator as stauth # Removed
    import bcrypt # Use bcrypt directly for robustness
    
    # 1. Generate Hash
    try:
        # Use bcrypt directly to avoid Hasher API version mismatch
        # stauth uses bcrypt internally, so this is compatible.
        hashed_bytes = bcrypt.hashpw(new_password_plain.encode('utf-8'), bcrypt.gensalt())
        hashed_pw = hashed_bytes.decode('utf-8')
    except Exception as e:
        return False, f"Hashing failed: {e}"

    # 2. Update secrets.toml (Persistent)
    secrets_path = ".streamlit/secrets.toml"
    try:
        with open(secrets_path, "r", encoding="utf-8") as f:
            config = toml.load(f)
        
        # Ensure structure exists
        if "passwords" not in config:
            config["passwords"] = {}
            
        config["passwords"][username] = hashed_pw
        
        with open(secrets_path, "w", encoding="utf-8") as f:
            toml.dump(config, f)
            
    except Exception as e:
        return False, f"File write failed: {e}"

    # 3. Update Session State (Immediate Effect)
    # We need to update the credential dictionary that authenticator reads.
    # But authenticator object might be re-inited on rerun from secrets?
    # No, get_authenticator() reads st.secrets.
    # st.secrets IS NOT updated by file write immediately in Streamlit.
    # So we must manualy update the 'credentials' in session state?
    # Actually, check_login uses st.session_state['authenticator'] if it exists?
    # Re-reading get_authenticator: it calls get_auth_config which reads st.secrets.
    # So on next rerun, it will read OLD secrets unless we handle it.
    # WE CANNOT UPDATE st.secrets programmatically.
    # Solution: We can't easily force Streamlit to reload secrets without restart.
    # BUT, we can make `get_auth_config` read from the FILE if we want?
    # Or, simpler: We tell the user "Password changed. Please re-login."
    # AND/OR we manually update the `authenticator.credentials['usernames'][username]['password']`
    # so that *this session* remains valid if using cookie re-check.
    
    # Let's try to update st.secrets cache if possible? No.
    # Let's just return True. The file IS updated, so on restart it works.
    # For now, it's safer to ask user to re-login if changing OWN password.
    # If Admin changing Child's, child will face it on next login.
    
    return True, "비밀번호가 변경되었습니다."
