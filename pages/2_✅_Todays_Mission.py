import streamlit as st
import pandas as pd
from datetime import datetime
import time
from modules.db_manager import db_manager
from modules.page_utils import initialize_page
import modules.time_utils as time_utils
import modules.auth_utils as auth_utils
import modules.ui_components as ui_components

# 미션 모듈
from modules.mission import MissionGenerator, MissionManager, RewardHandler, ui_helpers

# 페이지 초기화
initialize_page("오늘의 미션", "✅")

# Custom CSS for smaller button text
st.markdown("""
<style>
    /* Make mission action buttons have smaller text */
    div[data-testid="stVerticalBlock"] button[kind="primary"],
    div[data-testid="stVerticalBlock"] button:disabled {
        font-size: 0.85rem !important;
        padding: 0.4rem 0.6rem !important;
    }
</style>
""", unsafe_allow_html=True)

# Resolve Target Child ID (Centralized)
target_child_id = auth_utils.get_target_child_id()
target_child_name = st.session_state.get("target_child_name", st.session_state.get("name", "User"))
user_role = st.session_state.get("role", "user")

st.title("✅ 오늘의 미션")

# 미션 인스턴스 생성
mission_gen = MissionGenerator()
mission_mgr = MissionManager()
reward_handler = RewardHandler()

# 상태 매핑
status_map, status_map_inv = ui_helpers.get_status_maps()
approval_map = ui_helpers.get_approval_request_maps()

# 자동 미션 생성
mission_gen.ensure_todays_missions(target_child_id)

from modules.data_utils import load_dataframe_safely, safe_filter_dataframe

# Fetch Data
try:
    # 1. Missions - DB Manager now returns safe DF
    missions_df = db_manager.get_missions(assignee=target_child_id)
    
    # 2. Settings - DB Manager now returns safe DF
    settings_df = db_manager.get_settings()
    
    # [STRICT DEFENSE] Ensure Settings always has required structure
    required_settings_cols = ["category", "item_name", "value", "unit", "target_child"]
    settings_df = load_dataframe_safely(
        settings_df,
        required_columns=required_settings_cols,
        default_values={"target_child": "All", "category": ""},
        empty_columns=required_settings_cols
    )
    
    # In case load_dataframe_safely is bypassed or fails to add columns
    for col in required_settings_cols:
        if col not in settings_df.columns:
            settings_df[col] = "" if col != "value" else 0
    
    # category 컬럼 정리 (값의 공백 제거)
    settings_df["category"] = settings_df["category"].fillna("").astype(str).str.strip()
        
except Exception as e:
    st.error(f"데이터 로드 중 오류가 발생했습니다: {e}")
    missions_df = pd.DataFrame()
    settings_df = pd.DataFrame()
    
    # In case load_dataframe_safely is bypassed or fails to add columns
    required_settings_cols = ["category", "item_name", "value", "unit", "target_child"]
    for col in required_settings_cols:
        if col not in settings_df.columns:
            settings_df[col] = "" if col != "value" else 0
    
    st.stop()

status_map = {"Assigned": "할 일", "Pending": "검사 대기", "Approved": "완료", "Rejected": "반려"}
status_map_inv = {v: k for k, v in status_map.items()}

# Updated Tabs -> Navigation Radio for Persistence
# st.tabs does not persist selection on rerun (save), so we use st.radio.
current_tab = st.radio(
    "Navigation", 
    ["✅ 오늘의 미션", "🛠️ 미션 통합 관리", "📜 이력 관리"], 
    horizontal=True, 
    label_visibility="collapsed",
    key="tm_nav_selection"
)
st.divider()

today_str = time_utils.get_today_str()

# --- TAB 1: Today's Mission ---
if current_tab == "✅ 오늘의 미션":
    if not missions_df.empty:
        today_missions = missions_df[missions_df['date'] == today_str].copy()
    else:
        today_missions = pd.DataFrame()

    st.subheader(f"🗓️ 오늘의 미션 리스트")
    
    if not today_missions.empty:
        # Interactive Mission Table with Approval Buttons for Children
        if user_role != 'admin':
            # Prepare display dataframe for editing
            display_missions = today_missions.copy()
            
            # Add icon to mission title
            display_missions['미션 내용'] = display_missions.apply(
                lambda row: f"{'📝' if row['status'] == 'Assigned' else '⏳' if row['status'] == 'Pending' else '✅' if row['status'] == 'Approved' else '❌'} {row['title']}", 
                axis=1
            )
            
            # Map status to Korean (updated labels)
            display_missions['상태'] = display_missions['status'].map({
                'Assigned': '할 일',
                'Pending': '승인 대기',
                'Approved': '승인',  # Changed from '완료'
                'Rejected': '반려'   # Changed from '반려됨'
            })
            
            # Add approval request column
            # - Assigned: 미요청 (can request)
            # - Pending: 요청됨 (already requested, read-only)
            # - Approved: 완료 (completed, disabled)
            # - Rejected: 미요청 (can re-request)
            display_missions['승인 요청'] = display_missions['status'].apply(
                lambda s: '미요청' if s in ['Assigned', 'Rejected'] else '요청됨' if s == 'Pending' else '완료'
            )
            
            # Show editable table
            st.markdown("완료한 미션을 선택하여 부모님께 승인을 요청하세요. 반려된 미션은 다시 요청할 수 있습니다.")
            
            # Create disabled mask for approval request column
            # Disable for Approved (승인) and Pending (요청됨) missions
            disabled_rows = display_missions['status'].isin(['Approved', 'Pending'])
            
            edited_missions = st.data_editor(
                display_missions[['mission_id', '미션 내용', '상태', '승인 요청']],
                column_config={
                    "mission_id": None,  # Hidden
                    "미션 내용": st.column_config.TextColumn("미션 내용", disabled=True),
                    "상태": st.column_config.TextColumn("상태", disabled=True),
                    "승인 요청": st.column_config.SelectboxColumn(
                        "승인 요청",
                        options=["미요청", "요청", "요청됨", "완료"],
                        required=True,
                        help="완료한 미션을 '요청'으로 변경하고 저장 버튼을 누르세요"
                    )
                },
                hide_index=True,
                width="stretch",
                disabled=["미션 내용", "상태"],
                key="mission_editor"
            )
            
            # Save button
            if st.button("💾 승인 요청 저장", type="primary", width="content"):
                # Check which missions changed from 미요청 to 요청
                changes = 0
                all_missions = db_manager.get_missions(assignee=None)
                
                for idx, row in edited_missions.iterrows():
                    mission_id = row['mission_id']
                    edited_approval = row['승인 요청']
                    
                    # Find the original approval request value
                    original_row = display_missions[display_missions['mission_id'] == mission_id]
                    if original_row.empty:
                        continue
                    
                    original_approval = original_row.iloc[0]['승인 요청']
                    original_status = original_row.iloc[0]['status']
                    
                    # If changed from 미요청 to 요청
                    # Allow for both Assigned and Rejected missions
                    if edited_approval == '요청' and original_approval == '미요청' and original_status in ['Assigned', 'Rejected']:
                        # Update to Pending
                        mission_idx = all_missions[all_missions['mission_id'] == mission_id].index
                        if not mission_idx.empty:
                            all_missions.loc[mission_idx, 'status'] = 'Pending'
                            # Clear rejection reason when re-requesting
                            if original_status == 'Rejected':
                                all_missions.loc[mission_idx, 'rejection_reason'] = ''
                            changes += 1
                
                if changes > 0:
                    if db_manager.update_data("Missions", all_missions):
                        st.toast(f"✅ {changes}개 미션의 승인 요청이 전송되었습니다! 🙏")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("저장 실패")
                else:
                    st.info("변경된 내용이 없습니다.")
        else:
            # Admin View - Show table with approval editor for pending missions
            st.markdown("#### 전체 미션 현황")
            
            # Show all missions in a simple table
            display_df = today_missions[["title", "status"]].copy()
            display_df["상태"] = display_df["status"].map(status_map).fillna("할 일")
            
            st.dataframe(
                display_df[["title", "상태"]],
                column_config={
                    "title": st.column_config.TextColumn("미션 내용"),
                    "상태": st.column_config.TextColumn("상태"),
                },
                hide_index=True,
                width="stretch"
            )
            
            # Show pending missions for approval
            pending_missions = today_missions[today_missions['status'] == 'Pending'].copy()
            if not pending_missions.empty:
                st.divider()
                st.markdown("#### ⏳ 승인 대기 중인 미션")
                
                pending_missions["상태"] = pending_missions["status"].map(status_map).fillna("검사 대기")
                pending_missions["rejection_reason"] = pending_missions["rejection_reason"].fillna("").astype(str)
                
                edited_pending = st.data_editor(
                    pending_missions[["mission_id", "title", "상태", "rejection_reason"]],
                    column_config={
                        "mission_id": None,
                        "title": st.column_config.TextColumn("미션 내용", disabled=True),
                        "상태": st.column_config.SelectboxColumn("상태 변경", options=["검사 대기", "완료", "반려"], required=True),
                        "rejection_reason": st.column_config.TextColumn("비고/반려사유")
                    },
                    hide_index=True,
                    width="stretch",
                    key="editor_pending"
                )
                
                if st.button("💾 승인 처리 저장", type="primary", key="save_pending"):
                    def save_pending_action():
                        return mission_mgr.save_pending_changes(edited_pending, status_map_inv)
                    
                    ui_components.handle_submission(save_pending_action, success_msg="저장되었습니다!")
    else:
        st.info("오늘의 미션이 없습니다.")

    st.divider()
    
    # Final Approve (Reward) - HIDDEN for children
    if user_role == 'admin':
        st.subheader("🏅 오늘의 미션 최종 승인 (일일 보상)")
        with st.container(border=True):
            st.info("💡 보상 지급 시 'Reward' 장부에 안전하게 기록되며, 버튼을 여러 번 눌러도 데이터가 유실되지 않습니다.")
            col_r1, col_r2, col_r3 = st.columns([2, 2, 1])
            try:
                with col_r1:
                    # [SAFE DEFENSE] 도장 종류 매핑
                    stamps = safe_filter_dataframe(settings_df, 'category', 'Stamp')
                    if not stamps.empty:
                         stamps['target_child'] = stamps['target_child'].fillna('All')
                         mask = stamps['target_child'].isin(['All', target_child_id])
                         stamps = stamps[mask]
                    
                    s_opts = stamps['item_name'].tolist() if not stamps.empty else ["참 잘했어요(S)"]
                    sel_stamp = st.selectbox("도장 크기 선택", s_opts, key="admin_sel_stamp")
                    qty_stamp = st.number_input("도장 개수", min_value=0, max_value=10, value=1, key="admin_qty_stamp")
                
                with col_r2:
                    # [SAFE DEFENSE] 쿠폰 종류 매핑
                    coupons = safe_filter_dataframe(settings_df, 'category', 'Coupon')
                    if not coupons.empty:
                         coupons['target_child'] = coupons['target_child'].fillna('All')
                         mask = coupons['target_child'].isin(['All', target_child_id])
                         coupons = coupons[mask]
                    
                    c_opts = coupons['item_name'].tolist() if not coupons.empty else ["게임쿠폰(20분)"]
                    sel_coupon = st.selectbox("보너스 쿠폰 선택", c_opts, key="admin_sel_coupon")
                    qty_coupon = st.number_input("쿠폰 장수", min_value=0, max_value=5, value=1, key="admin_qty_coupon")
                
                with col_r3:
                    st.write("") # 간격 조정
                    st.write("")
                    if st.button("🧧 보상 지급 실행", type="primary", use_container_width=True):
                        if qty_stamp == 0 and qty_coupon == 0:
                            st.warning("지급할 보상 수량을 입력하세요.")
                        else:
                            def final_approval_action():
                                # RewardHandler를 통해 정규화된 장부에 기록
                                return reward_handler.grant_final_approval_rewards(
                                    target_child_name, sel_stamp, qty_stamp, sel_coupon, qty_coupon
                                )
                            ui_components.handle_submission(final_approval_action, success_msg="축하합니다! 보상이 정상 지급되었습니다.")
            except Exception as e:
                st.error(f"보상 UI 렌더링 오류: {e}")

# --- TAB 2: Mission Integration Management ---
if current_tab == "🛠️ 미션 통합 관리":
    st.subheader("📝 미션 통합 관리")
    st.caption("주간 반복 미션과 일회성 미션을 통합 관리합니다.")
    
    # 1. Load Definitions
    try:
        defs_df = db_manager.get_mission_definitions(assignee=target_child_id)
    except:
        defs_df = pd.DataFrame()

    # Initialize Session State Buffer for New Items if not exists
    if "new_def_buffer" not in st.session_state:
        st.session_state["new_def_buffer"] = []

    # Display Table (DB + Buffer)
    base_df = defs_df.copy()
    if st.session_state["new_def_buffer"]:
        buffer_df = pd.DataFrame(st.session_state["new_def_buffer"])
        combined_df = pd.concat([base_df, buffer_df], ignore_index=True)
    else:
        combined_df = base_df

    # Type Safety (Unconditional to ensure dtypes are object/string for Editor)
    if combined_df.empty:
        # Ensure correct dtypes if empty
        combined_df = pd.DataFrame(columns=["def_id", "title", "type", "frequency", "note", "assignee", "active"])
        combined_df = combined_df.astype(str)
    else:
        combined_df["title"] = combined_df["title"].fillna("").astype(str)
        combined_df["type"] = combined_df["type"].fillna("Routine").astype(str)
        combined_df["frequency"] = combined_df["frequency"].fillna("").astype(str)
        combined_df["note"] = combined_df["note"].fillna("").astype(str)

    is_admin = (user_role == 'admin')
    
    # Read-Only for Children
    edited_defs = st.data_editor(
        combined_df.reset_index(drop=True),
        column_config={
            "def_id": None,
            "assignee": None,
            "active": None, 
            "title": st.column_config.TextColumn("미션 이름", required=True),
            "type": st.column_config.TextColumn("구분", disabled=True),
            "frequency": st.column_config.TextColumn("요일/날짜", disabled=True),
            "note": st.column_config.TextColumn("비고")
        },
        num_rows="dynamic" if is_admin else "fixed",
        disabled=not is_admin,
        width="stretch",
        key="mission_def_editor_v2"
    )

    if is_admin:
        # Save Button (Top/Right or Bottom of Table?) 
        if st.button("💾 설정 저장 (Save Settings)", type="primary"):
            def save_settings_action():
                import uuid
                # 1. Fetch RAW ALL
                all_raw = db_manager.get_mission_definitions(assignee=None)
                
                # 2. Filter out current child's OLD data (We overwrite current child's data with Editor data)
                #    BUT we must preserve data from other children.
                if not all_raw.empty:
                    if "assignee" not in all_raw.columns: all_raw["assignee"] = "son1"
                    others = all_raw[all_raw["assignee"] != target_child_id]
                else:
                    others = pd.DataFrame()
        
                # 3. Process Editor Data
                new_records = edited_defs.to_dict('records')
                cleaned_records = []
                for r in new_records:
                    # Generate ID if missing (from buffer)
                    if not r.get("def_id") or pd.isna(r.get("def_id")):
                        r["def_id"] = str(uuid.uuid4())
                    r["assignee"] = target_child_id
                    if "active" not in r: r["active"] = True # Default
                    cleaned_records.append(r)
                
                new_child_df = pd.DataFrame(cleaned_records)
                final_defs = pd.concat([others, new_child_df], ignore_index=True)
                
                if db_manager.update_mission_definitions(final_defs):
                    st.session_state["new_def_buffer"] = [] # Clear buffer
                    
                    # Force Re-gen of Today's Missions
                    today_str = time_utils.get_today_str()
                    check_key = f"{target_child_id}_{today_str}"
                    if "todays_missions_checked" in st.session_state:
                        st.session_state["todays_missions_checked"][check_key] = False
                    return True
                return False

            ui_components.handle_submission(save_settings_action, success_msg="저장되었습니다. 오늘의 미션이 갱신됩니다.", delay=1.0)
    
        st.divider()
        
        # 2. New Mission Registration Form (Bottom)
        st.subheader("➕ 새 미션 등록")
        with st.container(border=True):
            col_new1, col_new2 = st.columns(2)
            with col_new1:
                n_title = st.text_input("미션 이름 (예: 방 청소)", key="new_def_title")
            with col_new2:
                n_note = st.text_input("비고 (선택 사항)", key="new_def_note")
            
            n_type = st.radio("반복 유형", ["주간 반복 (Routine)", "1회성 (OneTime)"], horizontal=True)
            
            n_freq = ""
            if "Routine" in n_type:
                # Pills for Days
                days_kr = ["월", "화", "수", "목", "금", "토", "일"]
                sel_days = st.pills("반복 요일 선택", days_kr, selection_mode="multi", key="new_def_pills")
                if sel_days:
                    # Sort days?
                    sorter = {d: i for i, d in enumerate(days_kr)}
                    sel_days.sort(key=lambda d: sorter.get(d, 99))
                    n_freq = ",".join(sel_days)
            else:
                # Date Input
                sel_date = st.date_input("날짜 선택", key="new_def_date")
                n_freq = sel_date.strftime("%Y-%m-%d")
    
            if st.button("미션 등록 (Add to List)"):
                if not n_title:
                    st.error("미션 이름을 입력하세요.")
                elif "Routine" in n_type and not n_freq:
                    st.error("요일을 선택하세요.")
                else:
                    # Add to Session State Buffer
                    new_item = {
                        "def_id": None, # Will be gen largely on Save
                        "title": n_title,
                        "type": "Routine" if "Routine" in n_type else "OneTime",
                        "frequency": n_freq,
                        "note": n_note,
                        "active": True,
                        "assignee": target_child_id
                    }
                    st.session_state["new_def_buffer"].append(new_item)
                    st.success("리스트에 추가되었습니다. '설정 저장'을 눌러 확정하세요.")
                    st.rerun()

# --- TAB 3: History Management ---
if current_tab == "📜 이력 관리":
    st.header("📜 이력 관리")
    
    # 1. Mission History (Moved from Tab 1)
    st.subheader("✅ 미션 승인/반려 이력")
    
    history_mask = missions_df['status'].isin(['Approved', 'Rejected']) # Use total df but filter
    # missions_df is filtered by assignee initially at top: db_manager.get_missions(assignee=target_child_id)
    # So this history is only for current child. Correct.
    history_df = missions_df[history_mask].copy()
    
    if not history_df.empty:
        history_df["상태"] = history_df["status"].map(status_map)
        history_df["title"] = history_df["title"].fillna("").astype(str)
        history_df["rejection_reason"] = history_df["rejection_reason"].fillna("").astype(str)

        if user_role == 'admin':
            edited_history = st.data_editor(
                history_df[["mission_id", "date", "title", "상태", "rejection_reason"]].reset_index(drop=True),
                column_config={
                    "mission_id": None,
                    "date": st.column_config.TextColumn("날짜", disabled=True),
                    "title": st.column_config.TextColumn("미션 내용", disabled=True),
                    "상태": "결과",
                    "rejection_reason": "비고"
                },
                width="stretch",
                hide_index=True,
                num_rows="dynamic", # Allows deletion
                key="history_editor"
            )
            
            if st.button("💾 미션 이력 저장", type="primary"):
                def save_history_action():
                    current_ids = [r['mission_id'] for r in edited_history.to_dict('records')]
                    original_ids = history_df['mission_id'].tolist()
                    deleted_ids = set(original_ids) - set(current_ids)
                    
                    all_raw = db_manager.get_missions(assignee=None)
                    
                    # Handle Deletions
                    if deleted_ids:
                        all_raw = all_raw[~all_raw['mission_id'].isin(deleted_ids)]
                    
                    # Handle Updates
                    for r in edited_history.to_dict('records'):
                        mid = r['mission_id']
                        kor_s = r['상태']
                        reas = r['rejection_reason']
                        eng_s = status_map_inv.get(kor_s, "Pending")
                        
                        idx = all_raw[all_raw['mission_id'] == mid].index
                        if not idx.empty:
                            all_raw.loc[idx[0], 'status'] = eng_s
                            all_raw.loc[idx[0], 'rejection_reason'] = reas
        
                    return db_manager.update_data("Missions", all_raw)

                ui_components.handle_submission(save_history_action, success_msg="미션 이력이 저장되었습니다.")
        else:
            # Read-only History
            st.dataframe(
                history_df[["date", "title", "상태", "rejection_reason"]],
                column_config={
                    "date": "날짜",
                    "title": "미션 내용",
                    "상태": "결과",
                    "rejection_reason": "비고"
                },
                width="stretch",
                hide_index=True
            )
    else:
        st.info("미션 이력이 없습니다.")

    st.divider()

    # 2. Reward Logs (New)
    st.subheader("🎁 일일 보상 지급 이력")
    st.caption("최종 승인을 통해 지급된 도장 및 쿠폰 내역입니다.")

    # Fetch logs for this child
    # db_manager.get_logs uses user_id (target_child_id) OR name? 
    # Current helper filters by "User" column.
    # log_activity writes 'target_child_name' into "User" column. ("큰보물")
    # But get_logs(target_child_id) passes "son1".
    # Mismatch identified in db_manager analysis.
    # To fix display here, we need to pass Name if Logs store Name.
    logs_df = db_manager.get_logs(user_id=target_child_name) 
    
    if not logs_df.empty:
        # Filter for Mission(Stamp) and Coupon only
        reward_mask = logs_df['type'].isin(['Mission', 'Coupon'])
        reward_logs = logs_df[reward_mask].copy()
        
        if not reward_logs.empty:
            # We need editable logs. 
            # Logs don't have unique ID usually? 
            # Looking at db_manager.log_activity: Timestamp, User, Type, Content, Reward.
            # No Log ID. 
            # Without Log ID, editing is RISKY (duplicates might be ambiguous).
            # But we must support deletion/edit as requested.
            # We can use Index if we fetch ALL logs and then map back by index? 
            # Better: Generate a temp ID or relying on index relative to full DF is hard if we filter.
            # Workaround: Editing works best if we bring Full Logs, Filter in UI, then Re-merge.
            # But 'data_editor' needs to return specific changed rows.
            
            # Strategy:
            # 1. Fetch ALL logs for EVERYONE (raw).
            # 2. Add an original index column to track them.
            # 3. Filter for current view (Current Child + Reward Type).
            # 4. Show editor.
            # 5. On Save:
            #    a. Reconstruct Full Logs.
            #    b. Update rows that match original index.
            #    c. Delete rows whose original index is missing in editor.
            
            full_logs_raw = db_manager.get_logs(user_id=None)
            # Add explicit index if not default
            full_logs_raw = full_logs_raw.reset_index(drop=True)
            full_logs_raw['__id'] = full_logs_raw.index
            
            # Filter for View
            view_mask = (full_logs_raw['user'] == target_child_name) & (full_logs_raw['type'].isin(['Mission', 'Coupon']))
            view_df = full_logs_raw[view_mask].copy()
            
            if user_role == 'admin':
                edited_rewards = st.data_editor(
                    view_df[["__id", "timestamp", "type", "content", "reward"]].reset_index(drop=True),
                    column_config={
                        "__id": None, # Hidden ID
                        "timestamp": st.column_config.TextColumn("일시", disabled=True),
                        "type": st.column_config.SelectboxColumn("구분", options=["Mission", "Coupon"], disabled=True),
                        "content": st.column_config.TextColumn("내용"),
                        "reward": st.column_config.NumberColumn("지급 수량")
                    },
                    width="stretch",
                    hide_index=True,
                    num_rows="dynamic",
                    key="reward_editor"
                )
                
                if st.button("💾 보상 이력 저장", type="primary"):
                    def save_logs_action():
                        # 1. Identify rows to keep/update
                        df_others = full_logs_raw[~view_mask]
                        df_updated_subset = edited_rewards.copy()
                        
                        # CRITICAL: Restore User column (lost during data_editor)
                        df_updated_subset['user'] = target_child_name
                        
                        if "__id" in df_updated_subset.columns: del df_updated_subset["__id"]
                        if "__id" in df_others.columns: del df_others["__id"]
                            
                        final_logs = pd.concat([df_others, df_updated_subset], ignore_index=True)
                        
                        try: final_logs = final_logs.sort_values(by="timestamp", ascending=True)
                        except: pass
                        
                        return db_manager.update_logs(final_logs)

                    ui_components.handle_submission(save_logs_action, success_msg="보상 이력이 저장되었습니다.")
            else:
                 # Read-only Logs
                st.dataframe(
                    view_df[["timestamp", "type", "content", "reward"]],
                    column_config={
                        "timestamp": "일시",
                        "type": "구분",
                        "content": "내용",
                        "reward": "수량"
                    },
                    width="stretch",
                    hide_index=True
                )

        else:
            st.info("보상 지급 이력이 없습니다.")
    else:
        st.info("이력이 없습니다.")
