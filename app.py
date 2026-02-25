import streamlit as st
# Force Reload: v1.0.2 fixes Recursive KeyError in Todays_Mission
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

# Force KST timezone for entire application
import os
os.environ['TZ'] = 'Asia/Seoul'
try:
    import time
    time.tzset()  # Unix/Linux only - applies timezone
except AttributeError:
    pass  # Windows doesn't have tzset()

# Page Configuration
st.set_page_config(
    page_title="보물지도: Family Hub",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load secrets for authentication
import modules.auth_utils as auth_utils
import modules.ui_components as ui_components
from modules.db_manager import db_manager

# Initialize Authenticator
authenticator = auth_utils.get_authenticator()

# [SAFETY LOCK] Automated migration is temporarily disabled for data recovery.
# Please follow the instructions in the chat to recover data and restore credentials.
# if "migration_done" not in st.session_state:
#     with st.status("🛠️ **시스템 데이터 구조 개편 (Reward 전면 적용)**", expanded=True) as status:
#         ...

# Check Login (Recovery & Widget)
# Check Login (Recovery & Widget)
# Check Login (Recovery & Widget)
auth_status = auth_utils.check_login(authenticator)

# Session State Logic
if auth_status:
    
    # Inject Mobile Responsive CSS
    ui_components.inject_mobile_css()
    
    # Sidebar
    ui_components.render_sidebar(authenticator)
    
    # Main Content
    st.title("🗺️ 보물지도: Family Hub")
    
    # Role-based Dashboard
    if st.session_state.get("role") == 'admin':
        # target_child is set by sidebar now
        target = st.session_state.get("target_child_name", "Unknown")
        st.info(f"🔧 관리자 모드 (보고 있는 자녀: **{target}**)")
        st.markdown("""
        ### 👨‍👩‍👦 부모님 대시보드
        - **일정 관리**: 주간 일정표에서 우리 가족의 시간을 확인하세요.
        - **미션 승인**: 아이들의 미션과 독서 기록을 칭찬해주세요.
        """)
    else:
        st.success(f"🚀 **{st.session_state['name']}**의 보물 탐험 시작!")
        st.markdown("""
        ### 👦 아이들 대시보드
        - **오늘의 미션**: 매일매일 미션을 수행하고 도장을 모으세요.
        - **나의 지갑**: 내가 모은 용돈과 쿠폰을 확인해보세요.
        """)
        
elif auth_status is None:
    st.warning("로그인이 필요합니다.")

if st.session_state["authentication_status"] is False:
    # Login Failed - Reset session pieces to prevent sticky failures
    if "logout" not in st.session_state:
        st.session_state["logout"] = True
    
    with st.expander("🚨 로그인 문제 해결 (Debug Info)", expanded=True):
        st.error("아이디 또는 비밀번호가 올바르지 않습니다.")
        
        try:
            # Force refresh user dict to ensure no stale cache
            users_data = db_manager.get_user_dict()
            usernames = users_data.get('usernames', {})
            st.write(f"**시스템 상태:** 인증 엔진 정상 (계정 {len(usernames)}개 로드됨)")
            
            if "dad" in usernames:
                st.info("💡 'dad' 계정이 시스템에 등록되어 있습니다. 대문자/소문자 구분을 확인해주세요.")
            
            if st.button("세션 강제 초기화 (로그인 에러 지속 시 클릭)"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
                
        except Exception as e:
            st.error(f"디버그 정보 로드 실패: {e}")

    st.stop()
