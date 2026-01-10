import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

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

# Initialize Authenticator
authenticator = auth_utils.get_authenticator()

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

if not st.session_state["authentication_status"]:
    st.stop()
