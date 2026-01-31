import streamlit as st
import pandas as pd
from modules.db_manager import db_manager
from modules.page_utils import initialize_page

import modules.auth_utils as auth_utils
import modules.ui_components as ui_components

# 페이지 초기화
initialize_page("나의 지갑", "💰")

# Resolve Target Child (Centralized)
# Wallet needs Name for Logs (DB stores Name) and Name for display.
target_child_name = st.session_state.get("target_child_name", st.session_state.get("name", "User"))

st.title("💰 나의 지갑")
st.caption(f"**{target_child_name}**의 자산 현황입니다.")

# Fetch Data
try:
    # Logs store User Name (e.g. "큰보물"), not ID. 
    # db_manager.get_logs(user_id=...) expects the matching value.
    # So we pass target_child_name.
    df_logs = db_manager.get_logs(user_id=target_child_name)
    
    # Settings might be needed for calculation
    # df_settings = db_manager.get_settings() # Not used here directly? Ah, reused in logic?
    # Wallet logic usually needs settings for Stamps/Coupons?
    # Let's check original code if it uses settings.
    # Original code called get_settings() inside specific blocks? 
    # Let's assume logic below uses it or fetches it.
    pass 
except Exception as e:
    st.error(f"데이터 로드 실패: {e}")
    df_logs = pd.DataFrame()

# Manual filtering removed as get_logs handles it (if implemented correctly to use passed arg)
my_logs = df_logs
        
# Fetch Settings
try:
    df_settings = db_manager.get_settings()
except Exception as e:
    df_settings = pd.DataFrame() # Fallback or handle later

# Calculate Assets
total_stamps = 0
total_money = 0

# Resolve Target Child ID (Centralized)
target_child_id = auth_utils.get_target_child_id()

# Get Unit Values and Create a Price Map
stamp_price_map = {}
if not df_settings.empty:
    stamp_rows = df_settings[df_settings["category"] == "Stamp"]
    
    # 1. First Pass: Load 'All' or NA Defaults
    general_stamps = stamp_rows[stamp_rows["target_child"].fillna("All").isin(["All"])]
    for _, row in general_stamps.iterrows():
        try:
            name = str(row["item_name"]).strip()
            val = int(row["value"])
            stamp_price_map[name] = val
        except: continue
        
    # 2. Second Pass: Overwrite with Specific Child Settings
    child_stamps = stamp_rows[stamp_rows["target_child"] == target_child_id]
    for _, row in child_stamps.iterrows():
        try:
            name = str(row["item_name"]).strip()
            val = int(row["value"])
            stamp_price_map[name] = val # Overwrite if exists
        except: continue

# Process Logs for 2-Phase Settlement System
# Phase 1: Calculate Expected Allowance (stamps after last confirmation)
unsettled_stamps = 0
expected_allowance = 0
# Initialize with columns to avoid KeyError if empty
stamps_after_confirmed = pd.DataFrame(columns=["Type", "Content", "Reward", "Timestamp"])

if not my_logs.empty:
    # Filter logs for calculation: Only consider logs AFTER the last AllowanceConfirmed
    # (also support legacy "Settlement" as confirmed for backward compatibility)
    confirmed_logs = my_logs[my_logs["Type"].isin(["AllowanceConfirmed", "Settlement"])]
    last_confirmed_idx = -1
    if not confirmed_logs.empty:
        last_confirmed_idx = confirmed_logs.index[-1]
    
    stamps_after_confirmed = my_logs.loc[last_confirmed_idx+1:]
    stamps_after_confirmed = stamps_after_confirmed[stamps_after_confirmed["Type"].isin(["Mission", "Praise"])]
    
    # Calculate Expected Allowance from stamps after confirmation
    for _, row in stamps_after_confirmed.iterrows():
        r_type = row["Type"]
        r_content = row["Content"]
        try:
            r_reward = int(float(str(row["Reward"]).replace(",", "")))
        except:
            continue
            
        if r_type == "Mission" or r_type == "Praise":
            # Extract Name for Pricing
            # Content format: "도장: [Name]" or just "[Name]" or "Mission Title"
            # Log Activity formats: "도장: {sel_stamp}"
            # We parse "도장: " out.
            price = 100 # Default fallback
            
            if "도장:" in str(r_content):
                # Extract "참 잘했어요 (칭찬: ...)" -> "참 잘했어요"
                candidate_full = str(r_content).split("도장:", 1)[1].strip()
                
                # 1. Try Exact Match
                if candidate_full in stamp_price_map:
                    price = stamp_price_map[candidate_full]
                else:
                    # 2. Try removing suffix (e.g. " (칭찬: ...)")
                    candidate_base = candidate_full.split("(", 1)[0].strip()
                    if candidate_base in stamp_price_map:
                        price = stamp_price_map[candidate_base]
                    else:
                        # 3. Try Prefix Match (Reverse lookup)
                        # Finds if any valid Stamp Name is a prefix of our candidate
                        found_price = 100
                        for s_name, s_val in stamp_price_map.items():
                             if candidate_full.startswith(s_name):
                                 found_price = s_val
                                 break
                        price = found_price
            else:
                price = stamp_price_map.get(str(r_content), 100)
            
            expected_allowance += (r_reward * price)
            unsettled_stamps += r_reward

# Phase 2: Calculate Unpaid Allowance (Confirmed - Paid)
total_confirmed = 0
total_paid = 0

if not my_logs.empty:
    # Sum all AllowanceConfirmed (and legacy Settlement as confirmed)
    confirmed_amount = my_logs[my_logs["Type"].isin(["AllowanceConfirmed", "Settlement"])]["Reward"].sum()
    total_confirmed = confirmed_amount if pd.notna(confirmed_amount) else 0
    
    # Sum all AllowancePaid
    paid_amount = my_logs[my_logs["Type"] == "AllowancePaid"]["Reward"].sum()
    total_paid = paid_amount if pd.notna(paid_amount) else 0

unpaid_allowance = total_confirmed - total_paid

# Calculate Available Coupons (획득 - 사용)
# 쿠폰 로직: 개별 쿠폰 추적
from modules.coupon_utils import extract_minutes_from_coupon, format_minutes

coupon_logs = my_logs[my_logs["Type"] == "Coupon"].copy()
coupon_used_logs = my_logs[my_logs["Type"] == "CouponUsed"].copy()

# 개별 쿠폰 아이템 생성
available_coupon_items = []
for _, row in coupon_logs.iterrows():
    coupon_name = str(row["Content"]).replace("쿠폰: ", "").strip()
    reward = int(row["Reward"]) if pd.notna(row["Reward"]) else 1
    timestamp = row["Timestamp"]
    
    for i in range(reward):
        available_coupon_items.append({
            "name": coupon_name,
            "timestamp": timestamp,
            "id": f"{timestamp}_{i}"
        })

# 사용된 쿠폰 제거
for _, row in coupon_used_logs.iterrows():
    coupon_name = str(row["Content"]).replace("쿠폰: ", "").strip()
    used_count = abs(int(row["Reward"])) if pd.notna(row["Reward"]) else 1
    
    # 같은 이름의 쿠폰을 used_count만큼 제거
    removed = 0
    available_coupon_items = [
        item for item in available_coupon_items
        if not (item["name"] == coupon_name and removed < used_count and (removed := removed + 1))
    ]

# 실제 보유 쿠폰 수
total_coupons = len(available_coupon_items)

# Note: expected_allowance and unsettled_stamps are already calculated above
# No need to redefine current_allowance and all_stamp_count

# UI Layout (Simple 3-column)
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("보유 쿠폰", f"{total_coupons}장")
with col2:
    st.metric("받은 도장", f"{unsettled_stamps}개")
with col3:
    st.metric("예상 용돈", f"{expected_allowance:,}원")

st.divider()

# Asset Details
st.subheader("📊 자산 상세 현황")
c1, c2 = st.columns(2)
with c1:
    st.markdown("#### 🎫 쿠폰 상세")
    
    # available_coupon_items는 이미 위에서 계산됨
    if not available_coupon_items:
        st.info("보유한 쿠폰이 없습니다.")
    else:
        # 현재 보유 쿠폰 표시
        coupon_df = pd.DataFrame([
            {"쿠폰명": item["name"], "획득일시": item["timestamp"]}
            for item in available_coupon_items
        ])
        st.dataframe(coupon_df, hide_index=True, width="stretch")
        
        st.markdown("---")
        st.markdown("##### 🎟️ 쿠폰 제출하기")
        
        # 중복 쿠폰 번호 매기기
        coupon_display_options = []
        name_counts = {}
        for item in available_coupon_items:
            name = item["name"]
            if name not in name_counts:
                name_counts[name] = 0
            name_counts[name] += 1
            
            # 같은 이름이 여러 개면 번호 표시
            if sum(1 for i in available_coupon_items if i["name"] == name) > 1:
                coupon_display_options.append(f"{name} #{name_counts[name]}")
            else:
                coupon_display_options.append(name)
        
        selected_indices = st.multiselect(
            "제출할 쿠폰 선택",
            options=range(len(available_coupon_items)),
            format_func=lambda x: coupon_display_options[x],
            key="selected_coupons"
        )
        
        if selected_indices:
            # 선택된 쿠폰의 총 시간 계산
            total_minutes = sum(
                extract_minutes_from_coupon(available_coupon_items[idx]["name"])
                for idx in selected_indices
            )
            time_str = format_minutes(total_minutes)
            st.info(f"선택된 쿠폰: {len(selected_indices)}장 (총 {time_str})")
            
            if st.button("🎟️ 선택한 쿠폰 제출", type="primary"):
                def submit_coupons_action():
                    # 선택된 쿠폰을 타입별로 그룹화
                    from collections import Counter
                    selected_coupons = [available_coupon_items[idx]["name"] for idx in selected_indices]
                    coupon_counts = Counter(selected_coupons)
                    
                    # 각 타입별로 로그 생성
                    for coupon_name, qty in coupon_counts.items():
                        db_manager.log_activity(
                            target_child_name,
                            "CouponUsed",
                            f"쿠폰: {coupon_name}",
                            -qty  # 음수로 저장
                        )
                    return True
                
                ui_components.handle_submission(
                    submit_coupons_action,
                    success_msg=f"{len(selected_indices)}장의 쿠폰이 제출되었습니다!"
                )

with c2:
    st.markdown("#### 💮 도장 상세")
    # Use stamps_after_confirmed (filtered by last confirmation) for display
    if stamps_after_confirmed.empty:
        st.info("받은 도장이 없습니다.")
    else:
        st.dataframe(stamps_after_confirmed[["Timestamp", "Content", "Reward"]], hide_index=True, width="stretch")

st.divider()

# 2-Phase Settlement Section
st.subheader("🗓️ 월말 정산 (용돈 지급 관리)")

# Phase 1: Expected Allowance & Confirm
st.write(f"📊 예상 용돈: **{int(expected_allowance):,}원**")
st.caption("※ 현재 모은 도장의 총 금액입니다.")

if st.session_state.get("role") == "admin":
    if expected_allowance > 0:
        if st.button("용돈 확정", type="secondary", key="confirm_allowance_btn"):
            def confirm_allowance_action():
                db_manager.log_activity(
                    target_child_name,
                    "AllowanceConfirmed",
                    "용돈 확정",
                    expected_allowance
                )
                return True
            
            ui_components.handle_submission(
                confirm_allowance_action,
                success_msg=f"{int(expected_allowance):,}원이 확정되었습니다!"
            )
    else:
        st.info("확정할 용돈이 없습니다.")

st.divider()

# Phase 2: Unpaid Allowance & Partial Payment
st.write(f"💰 미정산 금액: **{int(unpaid_allowance):,}원**")
st.caption("※ 확정된 용돈 중 아직 지급하지 않은 금액입니다.")

if st.session_state.get("role") == "admin":
    if unpaid_allowance > 0:
        # 정산할 금액 입력
        payment_amount = st.number_input(
            "정산할 금액을 입력하세요 (원)",
            min_value=0,
            max_value=int(unpaid_allowance),
            value=int(unpaid_allowance),
            step=100,
            key="payment_amount_input",
            help="부분 정산 가능: 원하는 금액만 입력하여 나누어 정산할 수 있습니다."
        )
        
        col_set, _ = st.columns([1, 4])
        with col_set:
            if st.button("정산 완료 (지급 확인)", type="primary", width="stretch"):
                if payment_amount > 0:
                    def pay_allowance_action():
                        db_manager.log_activity(
                            target_child_name,
                            "AllowancePaid",
                            "용돈 지급",
                            payment_amount
                        )
                        return True
                    
                    remaining = unpaid_allowance - payment_amount
                    if remaining > 0:
                        success_msg = f"{int(payment_amount):,}원 정산 완료! (남은 미정산: {int(remaining):,}원)"
                    else:
                        success_msg = f"{int(payment_amount):,}원 정산 완료! (전체 정산 완료)"
                    
                    ui_components.handle_submission(
                        pay_allowance_action,
                        success_msg=success_msg
                    )
                else:
                    st.warning("정산할 금액을 입력하세요.")
    else:
        st.info("정산할 금액이 없습니다.")
else:
    st.info("부모님만 정산을 진행할 수 있습니다.")
# Settlement History
st.subheader("📜 정산 이력 (장부)")
settle_logs = my_logs[my_logs["Type"].isin(["AllowanceConfirmed", "AllowancePaid", "Settlement"])]

if settle_logs.empty:
    st.info("아직 정산 이력이 없습니다.")
else:
    # Editorial Logic for Logs
    full_logs_raw = db_manager.get_logs(user_id=None)
    full_logs_raw = full_logs_raw.reset_index(drop=True)
    full_logs_raw['__id'] = full_logs_raw.index
    
    # Filter for Current Child + Settlement Types
    view_mask = (full_logs_raw['User'] == target_child_name) & (full_logs_raw['Type'].isin(["AllowanceConfirmed", "AllowancePaid", "Settlement"]))
    view_df = full_logs_raw[view_mask].copy()
    
    user_role = st.session_state.get("role", "user")
    
    # Add type description column
    view_df_display = view_df.copy()
    view_df_display["구분"] = view_df_display["Type"].map({
        "AllowanceConfirmed": "용돈 확정",
        "AllowancePaid": "용돈 지급",
        "Settlement": "정산 (구버전)"
    })
    
    if user_role == 'admin':
        edited_settlements = st.data_editor(
            view_df_display[["__id", "Type", "User", "Timestamp", "구분", "Content", "Reward"]].reset_index(drop=True),
            column_config={
                "__id": None,
                "Type": None,  # Hidden but preserved
                "User": None,  # Hidden but preserved
                "Timestamp": st.column_config.TextColumn("일시", disabled=True),
                "구분": st.column_config.TextColumn("구분", disabled=True),
                "Content": st.column_config.TextColumn("내용"),
                "Reward": st.column_config.NumberColumn("금액")
            },
            width="stretch",
            hide_index=True,
            num_rows="dynamic",
            key="settle_editor"
        )
        
        if st.button("💾 장부 변경사항 저장"):
            def save_ledger_action():
                # Merge Logic
                df_others = full_logs_raw[~view_mask]
                df_updated_subset = edited_settlements.copy()
                
                # Clean ID and display-only columns, but keep Type and User
                if "__id" in df_updated_subset.columns: del df_updated_subset["__id"]
                if "구분" in df_updated_subset.columns: del df_updated_subset["구분"]
                if "__id" in df_others.columns: del df_others["__id"]
                
                final_logs = pd.concat([df_others, df_updated_subset], ignore_index=True)
                try:
                    final_logs = final_logs.sort_values(by="Timestamp", ascending=True)
                except: pass
                
                return db_manager.update_logs(final_logs)

            ui_components.handle_submission(save_ledger_action, success_msg="장부(정산 이력)가 수정되었습니다.")
    else:
        # Read-Only View for Children
        st.dataframe(
            view_df_display[["Timestamp", "구분", "Content", "Reward"]],
            column_config={
                "Timestamp": "일시",
                "구분": "구분",
                "Content": "내용",
                "Reward": "금액"
            },
            width="stretch",
            hide_index=True
        )

st.divider()

# 쿠폰 제출 이력
st.subheader("🎟️ 쿠폰 제출 이력")
coupon_used_logs = my_logs[my_logs["Type"] == "CouponUsed"]

if coupon_used_logs.empty:
    st.info("아직 쿠폰 제출 이력이 없습니다.")
else:
    # 표시용 DataFrame 생성
    display_logs = coupon_used_logs[["Timestamp", "Content", "Reward"]].copy()
    display_logs["Reward"] = display_logs["Reward"].abs()  # 음수를 양수로 변환하여 표시
    
    st.dataframe(
        display_logs,
        column_config={
            "Timestamp": "제출 일시",
            "Content": "쿠폰명",
            "Reward": "제출 수량"
        },
        width="stretch",
        hide_index=True
    )

st.divider()

# 도장 제출 이력
st.subheader("💮 도장 제출 이력")

# AllowanceConfirmed 로그 가져오기 (레거시 Settlement 포함)
confirmed_logs = my_logs[my_logs["Type"].isin(["AllowanceConfirmed", "Settlement"])].copy()

if confirmed_logs.empty:
    st.info("아직 도장 제출 이력이 없습니다.")
else:
    # 각 확정 시점별로 그룹화
    submission_records = []
    
    # 각 AllowanceConfirmed에 대해
    for idx, confirmed_row in confirmed_logs.iterrows():
        confirmed_time = confirmed_row["Timestamp"]
        
        # 이 확정 이전의 도장들을 찾기 (이전 확정 이후 ~ 현재 확정 이전)
        # 이전 확정 찾기
        previous_confirmed = confirmed_logs[confirmed_logs["Timestamp"] < confirmed_time]
        if not previous_confirmed.empty:
            last_confirmed_time = previous_confirmed["Timestamp"].max()
            stamps_in_period = my_logs[
                (my_logs["Type"].isin(["Mission", "Praise"])) &
                (my_logs["Timestamp"] > last_confirmed_time) &
                (my_logs["Timestamp"] <= confirmed_time)
            ]
        else:
            # 첫 확정인 경우 - 처음부터 현재 확정까지
            stamps_in_period = my_logs[
                (my_logs["Type"].isin(["Mission", "Praise"])) &
                (my_logs["Timestamp"] <= confirmed_time)
            ]
        
        # 이 기간의 도장들을 그룹화
        if not stamps_in_period.empty:
            grouped = stamps_in_period.groupby("Content")["Reward"].sum().reset_index()
            for _, row in grouped.iterrows():
                submission_records.append({
                    "제출 일시": confirmed_time,
                    "내용": row["Content"],
                    "도장 수": row["Reward"]
                })
    
    if submission_records:
        # DataFrame으로 변환
        submission_df = pd.DataFrame(submission_records)
        
        # 제출 일시 기준 내림차순 정렬
        submission_df = submission_df.sort_values(by="제출 일시", ascending=False)
        
        st.dataframe(
            submission_df,
            column_config={
                "제출 일시": "제출 일시",
                "내용": "내용",
                "도장 수": "도장 수"
            },
            width="stretch",
            hide_index=True
        )
    else:
        st.info("아직 도장 제출 이력이 없습니다.")
