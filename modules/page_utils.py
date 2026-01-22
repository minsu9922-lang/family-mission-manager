"""페이지 공통 유틸리티

모든 Streamlit 페이지에서 반복되는 초기화 로직을 통합 관리합니다.
"""
import streamlit as st
import modules.auth_utils as auth_utils
import modules.ui_components as ui_components


def initialize_page(title: str, icon: str, layout: str = "wide"):
    """페이지 공통 초기화
    
    Args:
        title: 페이지 제목
        icon: 페이지 아이콘 (이모지)
        layout: 레이아웃 ("wide" 또는 "centered")
    
    Returns:
        authenticator: 인증 객체 (필요 시 사용)
    """
    # 페이지 설정
    st.set_page_config(page_title=title, page_icon=icon, layout=layout)
    
    # 인증 확인
    authenticator = auth_utils.get_authenticator()
    auth_status = auth_utils.check_login(authenticator)
    
    if not auth_status:
        st.stop()
    
    # UI 설정
    ui_components.inject_mobile_css()
    ui_components.render_sidebar(authenticator)
    
    return authenticator
