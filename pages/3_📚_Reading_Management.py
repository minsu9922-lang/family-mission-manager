import streamlit as st
import pandas as pd
from datetime import datetime
from modules.db_manager import db_manager
from modules.page_utils import initialize_page

import modules.auth_utils as auth_utils
import modules.ui_components as ui_components

# 페이지 초기화
initialize_page("독서 관리", "📚")

# Resolve Target Child ID (Centralized)
target_id = auth_utils.get_target_child_id()
target_child_name = st.session_state.get("target_child_name", st.session_state.get("name", "User"))
user_role = st.session_state.get("role", "user")

st.title("📚 독서 관리 (Reading Log)")
st.caption(f"**{target_child_name}**의 독서 기록입니다.")

# Fetch Data
try:
    # Use centralized filtering
    df_reading = db_manager.get_reading_logs(user_id=target_id)
except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.stop()

# Sorting
if not df_reading.empty and "read_date" in df_reading.columns:
    df_reading = df_reading.sort_values(by="read_date", ascending=False)

# Navigation Radio for Persistence
current_tab = st.radio(
    "Navigation", 
    ["독서 기록장", "독서 기록하기"], 
    horizontal=True, 
    label_visibility="collapsed",
    key="reading_nav"
)
st.divider()

if current_tab == "독서 기록장":
    st.subheader(f"📖 {target_child_name} 어린이가 읽은 책들")
    
    if df_reading.empty:
        st.info("아직 등록된 독서 기록이 없습니다.")
    else:
        # Determine starting number based on child
        from modules.constants import READING_START_NUMBERS, DEFAULT_START_NUMBER
        start_number = READING_START_NUMBERS.get(target_id, DEFAULT_START_NUMBER)
        
        # Ensure pages_read column exists in the source dataframe
        if "pages_read" not in df_reading.columns:
            df_reading["pages_read"] = ""
        
        # Columns to display - Include reading_id for identity preservation
        display_df = df_reading[["reading_id", "read_date", "book_type", "book_title", "pages_read", "author", "one_line_review"]].copy()
        
        # Handle missing values in pages_read
        display_df["pages_read"] = display_df["pages_read"].fillna("")
        
        # Add sequential number column at the beginning (reversed - latest book has highest number)
        # Since df is sorted by date descending, first row is newest
        total_books = len(display_df)
        display_df.insert(1, "번호", range(start_number + total_books - 1, start_number - 1, -1))
        
        display_df.columns = ["reading_id", "번호", "읽은 날짜", "구분", "책 제목", "읽은 쪽수", "지은이", "감상평"]
        
        # Ensure Text Columns are strings
        display_df["책 제목"] = display_df["책 제목"].astype(str)
        display_df["읽은 쪽수"] = display_df["읽은 쪽수"].astype(str)
        display_df["지은이"] = display_df["지은이"].astype(str)
        display_df["감상평"] = display_df["감상평"].astype(str)
        
        # Ensure Date Column is datetime for Editor
        # Force string conversion first to handle potential mixed types or objects
        display_df["읽은 날짜"] = pd.to_datetime(display_df["읽은 날짜"].astype(str), errors='coerce')
        
        # Recover NaT (invalid dates) with Today (Normalized to midnight for stability)
        # CRITICAL: Must use normalize() to ensure the dataframe content doesn't change every microsecond,
        # otherwise st.data_editor will reset and lose edits (deletions)!
        display_df["읽은 날짜"] = display_df["읽은 날짜"].fillna(pd.Timestamp.now().normalize())
        
        display_df.reset_index(drop=True, inplace=True) # Reset index to handle deletion safely

        # Editor for Reading Logs (Available to All Users)
        edited_readings = st.data_editor(
            display_df,
            column_config={
                "reading_id": None, # Hidden ID
                "번호": st.column_config.NumberColumn("번호", disabled=True, width="small"),
                "읽은 날짜": st.column_config.DateColumn("읽은 날짜"),
                "구분": st.column_config.SelectboxColumn("구분", options=["만화", "줄글만화", "줄글", "기타"]),
                "책 제목": st.column_config.TextColumn("책 제목", required=True),
                "읽은 쪽수": st.column_config.TextColumn("읽은 쪽수", width="small"),
                "지은이": st.column_config.TextColumn("지은이"),
                "감상평": st.column_config.TextColumn("감상평", required=True)
            },
            hide_index=True,
            width="stretch",
            key="reading_editor",
            num_rows="dynamic"
        )
        
        st.caption("💡 내용을 수정한 후 하단의 **[변경사항 저장]** 버튼을 눌러주세요.")
        
        import time 
        import uuid 
        
        if st.button("💾 변경사항 저장 (Save Changes)", type="primary", key="save_reading"):
            def save_reading_action():
                # Strategy: Robust Replacement for User
                # 1. Get ALL logs
                all_logs = db_manager.get_reading_logs(user_id=None)
                
                # 2. Filter out this user's old logs
                if not all_logs.empty and "user_name" in all_logs.columns:
                    # CLEANUP: Remove BOTH ID-based and Name-based records
                    # 1. Get all aliases for the current target_id
                    user_map = auth_utils.get_user_id_map()
                    aliases = [name for name, uid in user_map.items() if uid == target_id]
                    candidates = [str(target_id).strip()] + [str(alias).strip() for alias in aliases]
                    
                    # 2. Filter out rows matching ANY candidate
                    # formatting as string and stripping to be safe
                    other_logs = all_logs[~all_logs["user_name"].astype(str).str.strip().isin(candidates)]
                else:
                    other_logs = pd.DataFrame()
        
                # 3. Process Editor Data
                saved_df = edited_readings.copy()
                
                # Remove the 번호 column (display only, not stored)
                if "번호" in saved_df.columns:
                    saved_df = saved_df.drop(columns=["번호"])
                
                # Rename Back
                saved_df.columns = ["reading_id", "read_date", "book_type", "book_title", "pages_read", "author", "one_line_review"]
                saved_df["user_name"] = target_id
                
                # Fill Missing IDs for New Rows
                if not saved_df.empty:
                    def ensure_id(x):
                        if pd.isna(x) or str(x).strip() == "":
                            return str(uuid.uuid4())
                        return str(x)
                    saved_df["reading_id"] = saved_df["reading_id"].apply(ensure_id)
                
                # 4. Combine
                final_logs = pd.concat([other_logs, saved_df], ignore_index=True)
                
                # 5. Save
                return db_manager.update_data("Reading", final_logs)

            ui_components.handle_submission(save_reading_action, success_msg="독서 기록이 저장되었습니다!")

if current_tab == "독서 기록하기":
    st.subheader("✨ 새로운 책을 읽었어요!")
    
    with st.form("add_reading_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            r_date = st.date_input("읽은 날짜", value=datetime.today())
            r_type = st.selectbox("책 구분", ["만화", "줄글만화", "줄글", "기타"])
            r_title = st.text_input("책 제목", placeholder="예: 해리포터와 마법사의 돌")
        with col2:
            r_author = st.text_input("지은이", placeholder="예: J.K. 롤링")
            r_pages = st.text_input("읽은 쪽수", placeholder="예: 350 (선택사항)")
            
        r_review = st.text_input("감상평", placeholder="재미있었던 점이나 느낀 점을 짧게 적어보세요!")
        
        submitted = st.form_submit_button("등록")
        
    if submitted:
        if not r_title:
            st.error("책 제목을 입력해주세요!")
        elif not r_review:
            st.error("감상평을 짧게라도 남겨주세요!")
        else:
            def add_reading_action():
                 db_manager.add_reading_log(
                    r_date.strftime("%Y-%m-%d"),
                    r_type,
                    r_title,
                    r_author,
                    r_review,
                    target_id,
                    r_pages
                )
                 return True

            ui_components.handle_submission(add_reading_action, success_msg="독서 기록이 등록되었습니다! 📚")
