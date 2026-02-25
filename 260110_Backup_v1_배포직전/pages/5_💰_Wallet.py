import streamlit as st
import pandas as pd
from modules.db_manager import db_manager

import modules.auth_utils as auth_utils
import modules.ui_components as ui_components

st.set_page_config(page_title="나의 지갑", page_icon="💰", layout="wide")

# Initialize Authenticator
authenticator = auth_utils.get_authenticator()

# Check Login
auth_status = auth_utils.check_login(authenticator)

if auth_status:
    ui_components.inject_mobile_css()
    ui_components.render_sidebar(authenticator)
else:
    st.stop()

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
total_coupons = 0
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

# Process Logs
unsettled_stamps = 0
calculated_total_money = 0
# Initialize with columns to avoid KeyError if empty
active_logs = pd.DataFrame(columns=["Type", "Content", "Reward", "Timestamp"])

if not my_logs.empty:
    # [STRICT DEFENSE] Use safe_filter_dataframe to prevent KeyError
    from modules.data_utils import safe_filter_dataframe
    settlement_logs = safe_filter_dataframe(my_logs, "Type", "Settlement")
    
    last_settlement_idx = -1
    if not settlement_logs.empty:
        # Use simple tail(1) index to avoid issues
        last_settlement_idx = settlement_logs.index[-1]
    
    # Slice active logs
    # We iterate only ACTIVE logs for money calculation.
    # Total coupons can track history? Or just active? 
    # Usually wallet shows CURRENT holding. So active.
    # But code `total_coupons` tracked full history in old logic?
    # Let's align: Wallet usually shows "Current Assets".
    # So we should use active_logs for everything?
    # Wait, simple approach:
    # 1. Calculate 'total_coupons' (all time - used).
    # 2. Calculate 'current_allowance' (all time stamps - settled).
    # Logic is simpler if we iterate all logs and maintain running balance.
    
    # Re-reading old logic:
    # It iterated `my_logs` (ALL) to calc `total_stamps` and `total_coupons`.
    # It calculated `active_logs` separately for `all_stamp_count`.
    # And `current_allowance` was `all_stamp_count * stamp_value`.
    
    # New Logic:
    # 1. Iterate ALL for `total_coupons` (assuming no settlement for coupons, just accumulation? Or minus?)
    #    Actually current code `total_coupons += val` just adds. Needs logic for "Used"?
    #    "Usage" logs not mentioned yet.
    # 2. Iterate ACTIVE (post-settlement) for `current_allowance`.
    
    # Let's fix `current_allowance` logic first (User request).
    
    active_logs = my_logs.loc[last_settlement_idx+1:]
    
    # Calculate Stamps & Money from Active Logs
    for _, row in active_logs.iterrows():
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
            
            # Check price for "참 잘했어요" manually if map fails?
            # User said "Settings have 600".
            
            calculated_total_money += (r_reward * price)
            unsettled_stamps += r_reward
            
    # Calculate Coupons
    coupon_all_logs = safe_filter_dataframe(my_logs, "Type", "Coupon")
    if not coupon_all_logs.empty:
        for _, row in coupon_all_logs.iterrows():
            try:
                val = int(float(str(row.get("Reward", 0)).replace(",", "")))
                total_coupons += val
            except: pass

# Final Results
current_allowance = calculated_total_money
all_stamp_count = unsettled_stamps

# UI Layout (Simple 3-column)
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("보유 쿠폰", f"{total_coupons}장")
with col2:
    st.metric("받은 도장", f"{all_stamp_count}개")
with col3:
    st.metric("모은 용돈 (총합)", f"{current_allowance:,}원")

st.divider()

# Asset Details
st.subheader("📊 자산 상세 현황")
c1, c2 = st.columns(2)
with c1:
    st.markdown("#### 🎫 쿠폰 상세")
    coupon_view_logs = safe_filter_dataframe(my_logs, "Type", "Coupon")
    if coupon_view_logs.empty:
        st.info("보유한 쿠폰이 없습니다.")
    else:
        # Show required columns safely
        display_cols = [c for c in ["Timestamp", "Content", "Reward"] if c in coupon_view_logs.columns]
        st.dataframe(coupon_view_logs[display_cols], hide_index=True, width="stretch")

with c2:
    st.markdown("#### 💮 도장 상세")
    # Use active_logs (filtered by settlement) for display
    stamp_logs = safe_filter_dataframe(active_logs, "Type", ["Mission", "Praise"])
    if stamp_logs.empty:
        st.info("받은 도장이 없습니다.")
    else:
        display_cols = [c for c in ["Timestamp", "Content", "Reward"] if c in stamp_logs.columns]
        st.dataframe(stamp_logs[display_cols], hide_index=True, width="stretch")

st.divider()

# Settlement Section
st.subheader("🗓️ 월말 정산 (용돈 지급 관리)")
st.write(f"지급해야 할 용돈 (미정산): **{int(current_allowance):,}원**")
st.caption("※ 아이가 모은 도장 중 아직 정산되지 않은 금액입니다.")

# Wrapper container for alignment
if st.session_state.get("role") == "admin":
    col_set, _ = st.columns([1, 4])
    with col_set:
        if st.button("정산 완료 (지급 확인)", width="stretch"):
            if current_allowance > 0:
                def settlement_action():
                    # Add Settlement Log
                    db_manager.log_activity(
                        target_child_name, 
                        "Settlement", 
                        "용돈 정산 지급", 
                        current_allowance # Log the amount paid
                    )
                    return True
                
                ui_components.handle_submission(settlement_action, success_msg=f"{int(current_allowance):,}원 정산이 완료되었습니다!")
            else:
                st.warning("정산할 금액이 없습니다.")
else:
    st.info("부모님만 정산을 진행할 수 있습니다.")

st.divider()

# History
st.subheader("📜 정산 이력 (장부)")
settle_logs_view = safe_filter_dataframe(my_logs, "Type", "Settlement")

if settle_logs_view.empty:
    st.info("아직 정산 이력이 없습니다.")
else:
    # Editorial Logic for Logs
    full_logs_raw = db_manager.get_logs(user_id=None)
    full_logs_raw = full_logs_raw.reset_index(drop=True)
    full_logs_raw['__id'] = full_logs_raw.index
    
    # Filter for Current Child + Settlement Type
    view_mask = (full_logs_raw['User'] == target_child_name) & (full_logs_raw['Type'] == "Settlement")
    view_df = full_logs_raw[view_mask].copy()
    
    user_role = st.session_state.get("role", "user")
    
    if user_role == 'admin':
        edited_settlements = st.data_editor(
            view_df[["__id", "Timestamp", "Content", "Reward"]],
            column_config={
                "__id": None,
                "Timestamp": st.column_config.TextColumn("일시", disabled=True),
                "Content": st.column_config.TextColumn("내용"),
                "Reward": st.column_config.NumberColumn("정산 금액")
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
                
                # Clean ID
                if "__id" in df_updated_subset.columns: del df_updated_subset["__id"]
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
            view_df[["Timestamp", "Content", "Reward"]],
            column_config={
                "Timestamp": "일시",
                "Content": "내용",
                "Reward": "정산 금액"
            },
            width="stretch",
            hide_index=True
        )
