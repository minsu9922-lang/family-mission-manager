import streamlit as st
import streamlit_authenticator as stauth

def render_sidebar(authenticator=None):
    """
    Renders the shared sidebar component with Child Selector, Custom CSS, and Auth status.
    Must be called on every page.
    """
    # 1. Inject Custom CSS (Bold Sidebar)
    st.markdown("""
    <style>
    /* Make Sidebar Links Bold and Larger */
    section[data-testid="stSidebar"] a {
        font-weight: bold !important;
        font-size: 1.15em !important; /* Increased from 1.05em */
    }
    
    /* Bold all links logic override */
    [data-testid="stSidebarNav"] a {
        font-weight: bold !important;
    }

    /* Helper: Increase Sidebar Widget Labels (e.g. Child Selector) */
    [data-testid="stSidebar"] label {
        font-size: 1.1em !important;
        font-weight: bold !important;
    }
    
    /* Helper: Increase Sidebar Text (e.g. Welcome message) */
    [data-testid="stSidebar"] p {
        font-size: 1.05em !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 2. Check Auth
    if "authentication_status" not in st.session_state or not st.session_state["authentication_status"]:
        # If not logged in, usually we don't show much, but pages might redirect.
        return

    # 3. Sidebar Content
    # 3. Sidebar Content
    with st.sidebar:
        st.write(f"환영합니다, **{st.session_state.get('name', 'Guest')}**님! 👋")
        
        st.divider()
        
        # Child Selector Logic
        # Robust Role Deduction
        if "role" not in st.session_state and "username" in st.session_state:
            curr_user = st.session_state["username"]
            if curr_user in ["dad", "mom"]:
                st.session_state["role"] = "admin"
            elif curr_user in ["son1", "son2"]:
                st.session_state["role"] = "user"
        
        user_role = st.session_state.get("role", "user")
        
        if user_role == "admin":
             # Default to son1 (큰보물)
            if "selected_child" not in st.session_state:
                st.session_state["selected_child"] = "큰보물"
                
            child_options = ["큰보물", "작은보물"]
            
            # Use callback to force rerun on change if needed, but simple selectbox auto-reruns.
            selected = st.selectbox(
                "자녀 선택 (현재 적용중)", 
                child_options, 
                index=child_options.index(st.session_state.get("selected_child", "큰보물")),
                key="sidebar_child_selector" 
            )
            
            # Sync selection to session state (though key does this, explicit assignment ensures it)
            st.session_state["selected_child"] = selected
            st.session_state["target_child_name"] = selected
            
            st.caption(f"현재 **{selected}**의 데이터를 보고 있습니다.")
        else:
            # Child Role
            st.session_state["target_child_name"] = st.session_state.get("name")
            st.caption(f"**{st.session_state.get('name')}**의 보물지도")

        st.divider()
        
        # Logout
        if authenticator:
            try:
                authenticator.logout('로그아웃', 'sidebar')
            except:
                pass
        
        # Version Info
        st.divider()
        st.markdown("""
        <div style='text-align: center; color: #666; font-size: 0.85em;'>
            <strong>Family Mission Manager</strong><br>
            v1.0 (2026.01.10)
        </div>
        """, unsafe_allow_html=True)


def handle_submission(action_func, success_msg="저장되었습니다.", error_msg="저장 실패", delay=0.7):
    """
    Executes an action with a spinner, shows toast, and reruns.
    This prevents 'ghost screens' caused by rendering artifacts during long operations.
    Standardized flow: Spinner -> Action -> Toast -> Sleep -> Rerun.
    """
    import time
    with st.spinner("처리 중..."):
        try:
            success = action_func()
        except Exception as e:
            st.error(f"오류 발생: {e}")
            return

    if success:
        st.toast(f"✅ {success_msg}")
        time.sleep(delay)
        st.rerun()
    else:
        st.error(f"❌ {error_msg}")


def inject_mobile_css():
    """
    Inject responsive CSS for mobile optimization.
    This preserves PC/desktop experience while enhancing mobile usability.
    Only applies optimizations on screens below 768px.
    """
    st.markdown("""
    <style>
    /* ========================================
       MOBILE RESPONSIVE STYLES
       Only applies to screens below 768px
       ======================================== */
    
    @media (max-width: 768px) {
        /* General Layout */
        .main .block-container {
            padding: 1rem 0.5rem !important;
            max-width: 100% !important;
        }
        
        /* Buttons - Touch Friendly */
        .stButton button {
            min-height: 44px !important;
            font-size: 0.9rem !important;
            padding: 0.6rem 1rem !important;
        }
        
        /* Text Inputs */
        .stTextInput input,
        .stTextArea textarea {
            font-size: 16px !important; /* Prevents zoom on iOS */
            min-height: 44px !important;
        }
        
        /* Data Frames & Tables */
        .stDataFrame {
            font-size: 0.85rem !important;
        }
        
        .stDataFrame [data-testid="stDataFrameResizable"] {
            max-width: 100% !important;
            overflow-x: auto !important;
        }
        
        /* Data Editor */
        .stDataEditor {
            font-size: 0.85rem !important;
        }
        
        /* Headers */
        h1 {
            font-size: 1.75rem !important;
        }
        
        h2 {
            font-size: 1.5rem !important;
        }
        
        h3 {
            font-size: 1.25rem !important;
        }
        
        /* Selectbox - Touch Friendly */
        .stSelectbox select {
            min-height: 44px !important;
            font-size: 16px !important;
        }
        
        /* Radio Buttons - Larger Touch Targets */
        .stRadio [role="radiogroup"] label {
            padding: 0.75rem 1rem !important;
            min-height: 44px !important;
        }
        
        /* Sidebar */
        section[data-testid="stSidebar"] {
            font-size: 0.9rem !important;
        }
        
        /* Form Inputs */
        .stForm {
            padding: 0.5rem !important;
        }
        
        /* Dividers - Thinner on Mobile */
        hr {
            margin: 1rem 0 !important;
        }
        
        /* Info/Warning/Success Boxes */
        .stAlert {
            font-size: 0.9rem !important;
            padding: 0.75rem !important;
        }
        
        /* Captions */
        .stCaption {
            font-size: 0.8rem !important;
        }
        
        /* Metric Cards */
        [data-testid="stMetricValue"] {
            font-size: 1.5rem !important;
        }
        
        /* Expander */
        .streamlit-expanderHeader {
            font-size: 0.95rem !important;
        }
        
        /* Number Input */
        .stNumberInput input {
            font-size: 16px !important;
            min-height: 44px !important;
        }
        
        /* Date Input */
        .stDateInput input {
            font-size: 16px !important;
            min-height: 44px !important;
        }
    }
    
    /* ========================================
       TABLET RESPONSIVE STYLES (768px - 1024px)
       ======================================== */
    
    @media (min-width: 769px) and (max-width: 1024px) {
        .main .block-container {
            padding: 2rem 1.5rem !important;
        }
        
        .stButton button {
            font-size: 0.95rem !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)
