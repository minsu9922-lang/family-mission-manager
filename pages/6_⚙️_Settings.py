import streamlit as st
import pandas as pd
from modules.db_manager import db_manager
from modules.page_utils import initialize_page
import modules.auth_utils as auth_utils

# 페이지 초기화
initialize_page("설정 관리", "⚙️")
    
st.title("⚙️ 설정 (Settings)")

# Determine Role (Safety Check)
user_role = st.session_state.get("role")
if not user_role and st.session_state.get("username") in ["dad", "mom"]:
    user_role = "admin"

# Fetch Data (Only needed for Admins usually, but let's fetch safely)
from modules.data_utils import load_dataframe_safely

df_settings = pd.DataFrame()
if user_role == "admin":
    try:
        df_settings = db_manager.get_settings()
        df_settings = load_dataframe_safely(
            df_settings,
            required_columns=["category", "item_name", "value", "unit", "target_child"],
            default_values={"target_child": "All"},
            empty_columns=["category", "item_name", "value", "unit", "target_child"]
        )
        
        # Normalize category
        if "category" in df_settings.columns:
            df_settings["category"] = df_settings["category"].astype(str).str.strip()
            
    except Exception as e:
        st.error(f"설정을 불러오는 중 오류가 발생했습니다: {e}")
        df_settings = pd.DataFrame(columns=["category", "item_name", "value", "unit", "target_child"])


# Define Tabs based on Role (Using st.radio for state persistence)
if user_role == "admin":
    tab_options = ["🏷️ 도장 관리", "🎟️ 쿠폰 관리", "⚙️ 기타 설정", "🔑 비밀번호 변경"]
else:
    tab_options = ["🔑 비밀번호 변경"]

current_tab = st.radio(
    "설정 메뉴",
    tab_options,
    horizontal=True,
    label_visibility="collapsed",
    key="settings_tab_selection"
)
st.divider()

# --- ADMIN ONLY CONTENT ---
if user_role == "admin":
    # Helper: User Options (Safe Access)
    credentials = auth_utils.get_auth_config().get('credentials', {})
    usernames = credentials.get('usernames', {}) if isinstance(credentials, dict) else {}
    child_options = ["All"] + [u for u in usernames.keys() if u.startswith("son")]

    # --- TAB 1: STAMPS ---
    if current_tab == "🏷️ 도장 관리":
        st.subheader("🏷️ 칭찬 도장 관리")
        st.caption("자녀별 도장 종류와 금액을 설정합니다. `target_child`를 지정하면 해당 자녀에게만 보입니다.")
        
        df_stamp = df_settings[df_settings["category"] == "Stamp"].copy()
        df_stamp_view = df_stamp.drop(columns=["category"], errors="ignore").reset_index(drop=True)
        if "unit" in df_stamp_view.columns:
            df_stamp_view["unit"] = df_stamp_view["unit"].astype(str)
        
        with st.form(key="form_stamp", clear_on_submit=False):
            edited_stamp_view = st.data_editor(
                df_stamp_view,
                column_config={
                    "item_name": st.column_config.TextColumn("도장 이름", required=False),
                    "value": st.column_config.NumberColumn("금액 (원)", required=False, step=10),
                    "unit": st.column_config.TextColumn("단위 (예: 개)"),
                    "target_child": st.column_config.SelectboxColumn("대상 자녀 (All=모두)", options=child_options, required=False)
                },
                width="stretch", num_rows="dynamic", key="editor_stamp"
            )
            if st.form_submit_button("💾 도장 설정 저장", type="primary", width="stretch"):
                import time
                try:
                    df_others = df_settings[df_settings["category"] != "Stamp"]
                    edited_stamp = edited_stamp_view.copy()
                    edited_stamp["category"] = "Stamp"
                    if "target_child" not in edited_stamp.columns: edited_stamp["target_child"] = "All"
                    edited_stamp["target_child"] = edited_stamp["target_child"].fillna("All")
                    edited_stamp = edited_stamp[edited_stamp["item_name"].astype(str).str.strip().ne("")]
                    final_df = pd.concat([df_others, edited_stamp], ignore_index=True)
                    if db_manager.update_data("Settings", final_df):
                        st.toast("✅ 도장 설정이 저장되었습니다!"); time.sleep(1.0); st.rerun()
                    else: st.error("저장 실패 (DB Error)")
                except Exception as e: st.error(f"오류: {e}")

    # --- TAB 2: COUPONS ---
    if current_tab == "🎟️ 쿠폰 관리":
        st.subheader("🎟️ 게임/보너스 쿠폰 관리")
        st.caption("쿠폰 이름과 사용 시간(분)을 설정합니다.")
        
        df_coupon = df_settings[df_settings["category"] == "Coupon"].copy()
        df_coupon_view = df_coupon.drop(columns=["category"], errors="ignore").reset_index(drop=True)
        if "unit" in df_coupon_view.columns:
             df_coupon_view["unit"] = df_coupon_view["unit"].astype(str)
        
        with st.form(key="form_coupon", clear_on_submit=False):
            edited_coupon_view = st.data_editor(
                df_coupon_view,
                column_config={
                    "item_name": st.column_config.TextColumn("쿠폰 이름", required=False),
                    "value": st.column_config.NumberColumn("시간 (분)", required=False, step=10),
                    "unit": st.column_config.TextColumn("단위 (예: 분)"),
                    "target_child": st.column_config.SelectboxColumn("대상 자녀 (All=모두)", options=child_options, required=False)
                },
                width="stretch", num_rows="dynamic", key="editor_coupon"
            )
            if st.form_submit_button("💾 쿠폰 설정 저장", type="primary", width="stretch"):
                import time
                try:
                    df_others = df_settings[df_settings["category"] != "Coupon"]
                    edited_coupon = edited_coupon_view.copy()
                    edited_coupon["category"] = "Coupon"
                    if "target_child" not in edited_coupon.columns: edited_coupon["target_child"] = "All"
                    edited_coupon["target_child"] = edited_coupon["target_child"].fillna("All")
                    edited_coupon = edited_coupon[edited_coupon["item_name"].astype(str).str.strip().ne("")]
                    final_df = pd.concat([df_others, edited_coupon], ignore_index=True)
                    if db_manager.update_data("Settings", final_df):
                        st.toast("✅ 쿠폰 설정이 저장되었습니다!"); time.sleep(1.0); st.rerun()
                    else: st.error("저장 실패 (DB Error)")
                except Exception as e: st.error(f"오류: {e}")

    # --- TAB 3: GENERAL ---
    if current_tab == "⚙️ 기타 설정":
        st.subheader("⚙️ 기타 설정")
        df_general = df_settings[~df_settings["category"].isin(["Stamp", "Coupon"])].copy().reset_index(drop=True)
        
        with st.form(key="form_general", clear_on_submit=False):
            edited_general = st.data_editor(
                df_general,
                column_config={
                     "category": st.column_config.SelectboxColumn("카테고리", options=["Reward", "General"], required=False),
                     "item_name": st.column_config.TextColumn("항목명", required=False),
                     "value": st.column_config.NumberColumn("값", required=False),
                     "target_child": st.column_config.TextColumn("대상 (옵션)")
                },
                width="stretch", num_rows="dynamic", key="editor_general"
            )
            if st.form_submit_button("💾 기타 설정 저장", type="primary", width="stretch"):
                import time
                try:
                    df_reserved = df_settings[df_settings["category"].isin(["Stamp", "Coupon"])]
                    edited_general = edited_general[edited_general["item_name"].astype(str).str.strip() != ""]
                    final_df = pd.concat([df_reserved, edited_general], ignore_index=True)
                    if db_manager.update_data("Settings", final_df):
                        st.toast("✅ 설정이 저장되었습니다!"); time.sleep(2.0); st.rerun()
                    else: st.error("저장 실패 (DB Error)")
                except Exception as e: st.error(f"오류: {e}")

# --- TAB 4: PASSWORD CHANGE (Available to All) ---
if current_tab == "🔑 비밀번호 변경":
    st.subheader("🔑 비밀번호 변경")
    st.write("새로운 비밀번호를 입력해주세요.")
    
    # Target User Logic
    # 1. Fetch all users from config for Admin
    # 2. Restrict to current user for Non-Admin
    
    target_username = st.session_state["username"] # Default to self
    
    if user_role == "admin":
        auth_conf = auth_utils.get_auth_config()
        all_users = list(auth_conf['credentials']['usernames'].keys())
        target_username = st.selectbox("변경할 사용자 선택 (관리자 권한)", all_users, index=all_users.index(target_username) if target_username in all_users else 0)
    else:
        st.info(f"사용자: **{target_username}**")
        
    with st.form("pwd_change_form"):
        new_pwd = st.text_input("새 비밀번호", type="password")
        confirm_pwd = st.text_input("새 비밀번호 확인", type="password")
        
        submitted_pwd = st.form_submit_button("비밀번호 변경", type="primary")
        
        if submitted_pwd:
            if not new_pwd:
                st.error("비밀번호를 입력해주세요.")
            elif new_pwd != confirm_pwd:
                st.error("비밀번호가 일치하지 않습니다.")
            else:
                success, msg = auth_utils.change_password(target_username, new_pwd)
                if success:
                    st.success(msg)
                    st.info("⚠️ 변경된 비밀번호는 다음 로그인부터 적용됩니다.")
                else:
                    st.error(f"오류 발생: {msg}")

