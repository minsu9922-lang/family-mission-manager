import streamlit as st
import pandas as pd
import time
from modules.db_manager import db_manager
from modules.page_utils import initialize_page
import modules.auth_utils as auth_utils
import modules.ui_components as ui_components

# 페이지 초기화
initialize_page("칭찬합니다", "💌")

# Resolve Target Child ID (Centralized)
target_id = auth_utils.get_target_child_id()
target_child_name = st.session_state.get("target_child_name", st.session_state.get("name", "User"))
user_role = st.session_state.get("role", "user")

st.title("💌 칭찬합니다 (Praise)")
st.caption(f"**{target_child_name}**의 칭찬 공간입니다.")

# Fetch Data
try:
    df_praise = db_manager.get_praise_logs(user_id=target_id)
    
    if df_praise is not None:
        df_praise = df_praise.copy()
        df_praise.columns = [str(c).strip() for c in df_praise.columns]
    else:
        df_praise = pd.DataFrame()

    if df_praise.empty:
        df_praise = pd.DataFrame(columns=["praise_id", "date", "content", "status", "user_name"])
        
    # Ensure required columns
    for col in ["praise_id", "date", "content", "status", "user_name"]:
        if col not in df_praise.columns:
            df_praise[col] = ""

except Exception as e:
    st.error(f"데이터 로드 실패: {e}")
    df_praise = pd.DataFrame(columns=["praise_id", "date", "content", "status", "user_name"])

# --- Load Settings for Reward Options ---
from modules.data_utils import load_dataframe_safely

try:
    df_settings = db_manager.get_settings()
    df_settings = load_dataframe_safely(
        df_settings,
        required_columns=["category", "item_name", "value", "unit", "target_child"],
        default_values={"target_child": "All"}
    )
    
    # Normalize category column
    if "category" in df_settings.columns:
        df_settings["category"] = df_settings["category"].astype(str).str.strip()
    
    # Filter for Stamps only
    if not df_settings.empty and "category" in df_settings.columns:
        # Filter Logic: Category='Stamp' AND (target_child='All' OR target_child=target_id)
        mask = (df_settings["category"] == "Stamp") & \
               ((df_settings["target_child"].fillna("All") == "All") | (df_settings["target_child"] == target_id))
        
        stamp_options = df_settings[mask]["item_name"].tolist()
        stamp_options = [s for s in stamp_options if str(s).strip() != ""]
    else:
        stamp_options = []
except Exception as e:
    st.error(f"설정 로드 실패: {e}")
    stamp_options = []

# Sorting Logic & Migration
if not df_praise.empty:
    # Migration: Map Pending->대기 중, Completed->승인
    # This handles legacy data display
    status_map = {
        "Pending": "대기 중",
        "Completed": "승인"
    }
    # Apply mapping only if English values exist
    if df_praise["status"].isin(["Pending", "Completed"]).any():
        df_praise["status"] = df_praise["status"].replace(status_map)

    # map status to sort order: 대기 중=0, 나머지=1
    df_praise["sort_key"] = df_praise["status"].apply(lambda x: 0 if x == "대기 중" else 1)
    df_praise = df_praise.sort_values(by=["sort_key", "date"], ascending=[True, False])

# Navigation (Radio Buttons)
# Requested Order: 1. Approval/Check, 2. Registration
current_tab = st.radio(
    "Navigation",
    ["👑 칭찬 승인/확인", "🙏 칭찬/선행 등록"],
    horizontal=True,
    label_visibility="collapsed",
    key="praise_nav"
)
st.divider()

# --- Tab 1: Approval / Check (칭찬 승인 및 확인) ---
if current_tab == "👑 칭찬 승인/확인":
    # 1. ADMIN VIEW (Approval Interface)
    if user_role == "admin":
        st.subheader("👑 승인 대기 목록")
        
        # filtered df_praise is already target-specific
        pending_list = df_praise[df_praise["status"] == "대기 중"]
        
        if pending_list.empty:
            st.info(f"{target_child_name}의 대기 중인 승인 요청이 없습니다.")
        else:
            # Batch Approval Interface
            editor_df = pending_list[["praise_id", "date", "content", "status"]].copy()
            
            # Add a Reward Column for selection in the editor
            # We initialize it with None or first stamp? Let's Initial with None
            editor_df["보상 선택"] = None 

            edited_praise = st.data_editor(
                editor_df,
                column_config={
                    "praise_id": None,
                    "date": "날짜",
                    "content": st.column_config.TextColumn("내용", disabled=True),
                    "status": st.column_config.SelectboxColumn(
                        "승인 상태", 
                        options=["대기 중", "승인", "거절"],
                        required=True
                    ),
                    "보상 선택": st.column_config.SelectboxColumn(
                        "보상 (승인 시 지급)",
                        options=stamp_options,
                        required=False,
                        help="승인 시 지급할 도장을 선택하세요."
                    )
                },
                hide_index=True,
                width="stretch",
                key="praise_editor"
            )
            
            st.caption("💡 상태를 **'승인'**으로 변경하고 **보상**을 선택한 뒤 **[승인 내역 저장]**을 누르면 도장이 지급됩니다.")
            
            import time
            if st.button("💾 승인 내역 저장 (Save Approvals)", type="primary"):
                def save_approvals_action():
                    # 1. Get ALL praises
                    all_praises = db_manager.get_praise_logs(user_id=None)
                    
                    # 2. Iterate and Update
                    changes = 0
                    rewards_issued = 0
                    new_records = edited_praise.to_dict('records')
                    
                    for r in new_records:
                        pid = r['praise_id']
                        new_status = r['status']
                        selected_reward = r['보상 선택']
                        
                        # Update Logic
                        idx = all_praises[all_praises['praise_id'] == pid].index
                        
                        if not idx.empty:
                            original_status = all_praises.loc[idx[0], 'status']
                            
                            # Update Status to DB
                            if original_status != new_status:
                                all_praises.loc[idx, 'status'] = new_status
                                changes += 1
                                
                                # Reward Logic: Only if Approved AND Reward Selected
                                if new_status == "승인" and selected_reward:
                                    # Issue Reward Log
                                    reward_val = 1
                                    
                                    # 2. Log Activity
                                    # Note: target_id is the child.
                                    db_manager.log_activity(
                                        user_name=target_child_name, 
                                        activity_type="Praise", 
                                        content=f"도장: {selected_reward} (칭찬: {r['content'][:10]}...)", 
                                        reward=reward_val
                                    )
                                    rewards_issued += 1
                    
                    if changes > 0:
                        return db_manager.update_data("Praise", all_praises)
                    
                    # No changes
                    st.info("변경된 내역이 없습니다.")
                    return True # Return True to trigger 'Saved' toast or prevent error, implies 'Success in doing nothing'

                ui_components.handle_submission(save_approvals_action, success_msg="저장 확인 완료")
        
        st.divider()
        st.subheader("📜 전체 기록 이력 (수정/삭제 가능)")
        # Show all non-peding (Approved or Rejected)
        history_list = df_praise[df_praise["status"] != "대기 중"]
        
        if not history_list.empty:
            # History Editor for Admin
            history_editor_df = history_list[["praise_id", "date", "content", "status"]].copy().reset_index(drop=True)
            
            edited_history = st.data_editor(
                history_editor_df,
                column_config={
                    "praise_id": None,
                    "date": "날짜",
                    "content": st.column_config.TextColumn("내용"), # Editable content
                    "status": st.column_config.SelectboxColumn("상태", options=["대기 중", "승인", "거절"]) # Can revert
                },
                hide_index=True,
                width="stretch",
                key="praise_history_editor",
                num_rows="dynamic" # Allow Deletion
            )

            if st.button("💾 완료 기록 저장 (Save History)", key="save_praise_history"):
                def save_praise_history_action():
                    all_praises = db_manager.get_praise_logs(user_id=None)
                    
                    original_ids = history_list["praise_id"].tolist()
                    surviving_ids = edited_history["praise_id"].tolist()
                    
                    # 1. Updates
                    surviving_map = edited_history.set_index("praise_id").to_dict('index')
                    
                    for pid, updates in surviving_map.items():
                        idx = all_praises[all_praises['praise_id'] == pid].index
                        if not idx.empty:
                            all_praises.loc[idx, 'content'] = updates['content']
                            all_praises.loc[idx, 'status'] = updates['status']
                            all_praises.loc[idx, 'date'] = updates['date']
                            
                    # 2. Deletions
                    ids_to_delete = set(original_ids) - set(surviving_ids)
                    if ids_to_delete:
                        all_praises = all_praises[~all_praises['praise_id'].isin(ids_to_delete)]
                    
                    return db_manager.update_data("Praise", all_praises)

                ui_components.handle_submission(save_praise_history_action, success_msg="완료 기록이 수정되었습니다!")
        else:
            st.info("완료된 기록이 없습니다.")
            


    # 2. USER VIEW (My Praise History) - Only for children
    else:
        st.subheader("📜 나의 칭찬 기록 확인")
        if not df_praise.empty:
            # Consistent Table View for Children
            st.dataframe(
                df_praise[["date", "content", "status"]],
                column_config={
                    "date": st.column_config.TextColumn("날짜"),
                    "content": st.column_config.TextColumn("칭찬 내용"),
                    "status": st.column_config.TextColumn("상태")
                },
                width="stretch",
                hide_index=True
            )
        else:
            st.info("아직 등록된 칭찬 기록이 없습니다. '등록' 탭에서 착한 일을 자랑해보세요!")
    
    # 3. Reward Logs Section (Visible to All Users)
    st.divider()
    st.subheader("💰 칭찬 보상 지급 이력 (Logs)")
    
    try:
        all_logs_raw = db_manager.get_logs(user_id=None)
        
        # Filter for Current Child AND Type='Praise'
        reward_mask = (all_logs_raw['User'] == target_child_name) & (all_logs_raw['Type'] == 'Praise')
        reward_logs_view = all_logs_raw[reward_mask].copy()
        
        if reward_logs_view.empty:
            st.info("지급된 칭찬 보상 이력이 없습니다.")
        else:
            if user_role == 'admin':
                # Admin: Editable view
                st.caption("승인 시 지급된 도장(Praise Type) 이력을 직접 수정하거나 취소할 수 있습니다.")
                
                all_logs_raw = all_logs_raw.reset_index(drop=True)
                all_logs_raw['__id'] = all_logs_raw.index
                reward_mask = (all_logs_raw['User'] == target_child_name) & (all_logs_raw['Type'] == 'Praise')
                reward_logs_view = all_logs_raw[reward_mask].copy()
                
                edited_rewards = st.data_editor(
                    reward_logs_view[["__id", "Timestamp", "Content", "Reward"]].reset_index(drop=True),
                    column_config={
                        "__id": None,
                        "Timestamp": st.column_config.TextColumn("일시", disabled=True),
                        "Content": st.column_config.TextColumn("내용 (보상명)"),
                        "Reward": st.column_config.NumberColumn("보상 (개수)")
                    },
                    hide_index=True,
                    width="stretch",
                    key="praise_reward_logs_admin",
                    num_rows="dynamic"
                )
                
                if st.button("💾 보상 이력 저장", key="save_reward_logs_admin"):
                    def save_rewards_action():
                        df_others = all_logs_raw[~reward_mask]
                        original_ids = reward_logs_view['__id'].tolist()
                        current_ids = edited_rewards['__id'].dropna().astype(int).tolist()
                        ids_to_delete = set(original_ids) - set(current_ids)
                        
                        all_logs_final = all_logs_raw.copy()
                        if ids_to_delete:
                            all_logs_final = all_logs_final[~all_logs_final['__id'].isin(ids_to_delete)]
                        
                        for _, row in edited_rewards.iterrows():
                            if pd.notna(row['__id']):
                                rid = int(row['__id'])
                                if rid in all_logs_final['__id'].values:
                                    idx_map = all_logs_final.index[all_logs_final['__id'] == rid].tolist()
                                    if idx_map:
                                        real_idx = idx_map[0]
                                        all_logs_final.at[real_idx, 'Content'] = row['Content']
                                        all_logs_final.at[real_idx, 'Reward'] = row['Reward']
                        
                        if "__id" in all_logs_final.columns:
                            del all_logs_final["__id"]
                        
                        return db_manager.update_logs(all_logs_final)
                    
                    ui_components.handle_submission(save_rewards_action, success_msg="보상 이력이 수정되었습니다!")
            else:
                # Child: Read-only view
                st.dataframe(
                    reward_logs_view[["Timestamp", "Content", "Reward"]],
                    column_config={
                        "Timestamp": "일시",
                        "Content": "내용 (보상명)",
                        "Reward": "보상 (개수)"
                    },
                    hide_index=True,
                    width="stretch"
                )
    except Exception as e:
        st.error(f"보상 이력 로드 오류: {e}")

# --- Tab 2: Registration (칭찬/선행 등록) ---
if current_tab == "🙏 칭찬/선행 등록":
    st.subheader(f"✨ {target_child_name}의 착한 일을 자랑해보세요!")
    
    with st.form("praise_request_form", clear_on_submit=True):
        p_content = st.text_area("어떤 착한 일을 했나요?", placeholder="예: 동생에게 장난감을 양보했어요.")
        submitted = st.form_submit_button("부모님께 승인 요청하기")
        
    if submitted:
        if not p_content:
            st.error("내용을 입력해주세요!")
        else:
            def request_praise_action():
                 # Add request for target_id
                 db_manager.add_praise_request(p_content, target_id)
                 return True

            ui_components.handle_submission(request_praise_action, success_msg="승인 요청이 등록되었습니다! 부모님의 확인을 기다려주세요. 🙏")
