import streamlit as st
import pandas as pd
from modules.db_manager import db_manager
from modules.page_utils import initialize_page
import modules.ui_components as ui_components
from modules.time_utils import get_today_str
from modules.data_utils import load_dataframe_safely, safe_filter_dataframe

# 페이지 초기화
initialize_page("나의 지갑", "💰")

# 자녀 ID 및 이름 결정
target_child_name = st.session_state.get("target_child_name", st.session_state.get("name", "User"))
user_role = st.session_state.get("role", "user")

st.title("💰 나의 지갑")
st.caption(f"**{target_child_name}**님의 자산 및 정산 현황입니다.")

# 1. 최신 Reward 데이터 로드 (TTL=0으로 즉각 반영)
try:
    # [DEBUG] 데이터 로드 전 상태 기록
    raw_reward_df = db_manager.get_data("Reward", ttl=0)
    
    with st.expander("🔍 데이터 연결 진단 (문제가 있을 때만 확인하세요)", expanded=False):
        st.write(f"📂 시트 전체 데이터: {len(raw_reward_df)}행 발견")
        st.write(f"👤 현재 접속 유저명: `{target_child_name}`")
        if not raw_reward_df.empty:
            # User 컬럼 찾기 (대소문자 무시)
            user_col = next((c for c in raw_reward_df.columns if str(c).lower() == 'user'), None)
            if user_col:
                unique_users = raw_reward_df[user_col].unique()
                st.write(f"📝 시트 내 유저들: {unique_users}")
    
    reward_df = db_manager.get_rewards(user_name=target_child_name)
    
    # status 컬럼이 없는 경우를 대비한 안전 장치 (하위 호환성)
    if not reward_df.empty and "status" not in reward_df.columns and "action" in reward_df.columns:
        reward_df = reward_df.rename(columns={"action": "status"})
except Exception as e:
    st.error(f"데이터 로드 실패 (관리자에게 문의): {e}")
    reward_df = pd.DataFrame()

# 2. 자산 계산 로직 (status 기반)
current_stamps = 0
current_coupons = 0
expected_allowance = 0

if not reward_df.empty:
    # 'earned' (보유 중/정산 대기) 상태인 자산만 필터링
    earned_assets = safe_filter_dataframe(reward_df, "status", "Earned")
    
    # 도장(stamp) 계산
    stamps = safe_filter_dataframe(earned_assets, "category", "Stamp")
    current_stamps = stamps["quantity"].sum() if "quantity" in stamps.columns else 0
    expected_allowance = stamps["total_price"].sum() if "total_price" in stamps.columns else 0
    
    # 쿠폰(coupon) 계산
    coupons = safe_filter_dataframe(earned_assets, "category", "Coupon")
    current_coupons = coupons["quantity"].sum() if "quantity" in coupons.columns else 0

# 3. 메인 대시보드 UI
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("보유 쿠폰", f"{int(current_coupons)}장")
with col2:
    st.metric("보유 도장", f"{int(current_stamps)}개")
with col3:
    st.metric("예상 용돈", f"{int(expected_allowance):,}원")

st.divider()

# 4. 자산 상세 및 액션
c1, c2 = st.columns(2)

with c1:
    st.subheader("🎫 보유 쿠폰 상세")
    holding_coupons = safe_filter_dataframe(reward_df, ["category", "status"], ["Coupon", "Earned"])
    if holding_coupons.empty:
        st.info("현재 보유한 쿠폰이 없습니다.")
    else:
        st.dataframe(
            holding_coupons[["date", "item_name", "quantity"]], 
            hide_index=True, use_container_width=True
        )
        
        # 쿠폰 사용 버튼 (향후 구현 예정)
        st.caption("※ 쿠폰 사용은 서비스 준비 중입니다.")

with c2:
    st.subheader("💮 보유 도장 상세")
    holding_stamps = safe_filter_dataframe(reward_df, ["category", "status"], ["Stamp", "Earned"])
    if holding_stamps.empty:
        st.info("정산 대기 중인 도장이 없습니다.")
    else:
        st.dataframe(
            holding_stamps[["date", "item_name", "sub_type", "quantity", "total_price"]], 
            hide_index=True, use_container_width=True
        )

st.divider()

# 5. 정산 섹션 (부모님 전용)
st.subheader("🗓️ 월말 용돈 정산")
if user_role == "admin":
    if expected_allowance > 0:
        st.write(f"현재 **{target_child_name}**님에게 지급할 용돈은 총 **{int(expected_allowance):,}원**입니다.")
        st.warning("⚠️ '정산 완료' 버튼을 누르면 현재 보유한 모든 도장이 '정산 완료' 상태로 변경되며 지갑이 비워집니다.")
        
        if st.button("💰 전체 정산 완료 (지갑 비우기)", type="primary", use_container_width=True):
            def finalize_settlement():
                # Reward 시트의 Earned 도장들을 Settled로 한꺼번에 변경
                return db_manager.update_reward_status(target_child_name, "Earned", "Settled")
            
            ui_components.handle_submission(
                finalize_settlement, 
                success_msg=f"{int(expected_allowance):,}원 정산이 완료되었습니다! 지갑이 초기화되었습니다."
            )
    else:
        st.info("정산할 도장이 없습니다.")
else:
    st.info("부모님 계정으로 로그인하면 용돈 정산을 진행할 수 있습니다.")

st.divider()

# 6. 정산 및 보상 이력 (장부)
st.subheader("📜 보상 및 정산 이력")
if not reward_df.empty:
    history_df = reward_df.sort_values(by="timestamp", ascending=False)
    st.dataframe(
        history_df[["date", "category", "item_name", "quantity", "total_price", "status", "note"]],
        column_config={
            "date": "날짜",
            "category": "구분",
            "item_name": "항목",
            "quantity": "수량",
            "total_price": "금액",
            "status": "상태",
            "note": "비고"
        },
        hide_index=True,
        use_container_width=True
    )
else:
    st.info("아직 보상 이력이 없습니다.")
