import streamlit as st
import pandas as pd
from datetime import datetime
import time
from modules.db_manager import db_manager
import modules.auth_utils as auth_utils
import modules.ui_components as ui_components

st.set_page_config(page_title="주간 시간표", page_icon="📅", layout="wide")

# Sidebar (Render first for UI consistency, but checking login might rerender)
# Actually, better to check login first, then render sidebar if valid? 
# Sidebar renders content based on session state. check_login ensures session state.
# But check_login MIGHT show login widget.
# Strategy: Call check_login. If True, render sidebar and content.
# If False, login widget is shown by check_login (if we configured it so? No, check_login calls authenticator.login() which shows widget).

# Initialize Authenticator
authenticator = auth_utils.get_authenticator()

# Check Login
auth_status = auth_utils.check_login(authenticator)

if auth_status:
    ui_components.inject_mobile_css()
    # Sidebar
    ui_components.render_sidebar(authenticator)
else:
    # Login failed or not logged in
    # authenticator.login() inside check_login already rendered the form? 
    # Yes.
    st.stop()

st.title("📅 주간 시간표 (Weekly Schedule)")

# Resolve Target Child ID (Centralized)
target_child_id = auth_utils.get_target_child_id()
# For display, we might want the name too.
# We can get it from session state or reverse map, but session state 'target_child_name' is reliable for Admin.
target_child_name = st.session_state.get("target_child_name", st.session_state.get("name", "User"))

st.caption(f"**{target_child_name}**의 주간 시간표입니다.")

import re

# Constants
DAYS_ORDER = ["월", "화", "수", "목", "금", "토", "일"]
HOURS = range(8, 23) # Extended to cover 22:00

# Colors
BLOCK_COLORS = [
    "#FFD1DC", "#FFDAC1", "#FFF0F5", "#E6E6FA", "#F0F8FF", "#E0FFFF", "#F0FFF0", "#F5F5DC",
    "#FFB6C1", "#ADD8E6", "#90EE90", "#FFE4B5" # Added more colors
]

def get_color_for_title(title):
    # Simple deterministic hash
    hash_val = sum(ord(c) for c in title)
    return BLOCK_COLORS[hash_val % len(BLOCK_COLORS)]

def generate_html_timetable(schedules):
    # Base Constants
    START_HOUR = 8
    END_HOUR = 23 # Up to 23:00 (Last slot 22:00-23:00)
    PIXELS_PER_HOUR = 50
    TOTAL_HOURS = END_HOUR - START_HOUR
    TOTAL_HEIGHT = TOTAL_HOURS * PIXELS_PER_HOUR
    
    # Pre-process Data
    # Structure: events_by_day = { "월": [ {title, start_min, duration_min, color}, ... ], "화": ... }
    events_by_day = {d: [] for d in DAYS_ORDER}
    
    if not schedules.empty:
        schedules = schedules.copy()
        # Regex normalize
        schedules["title"] = schedules["title"].apply(lambda x: re.sub(r'\s*\(.*?\)', '', str(x)).strip())
        schedules = schedules.drop_duplicates(subset=["title", "days", "start_time", "end_time"])
        
        for _, row in schedules.iterrows():
            # Safe parsing
            try:
                # 1. Day List
                days_str = str(row["days"]).replace("[", "").replace("]", "").replace("'", "").replace('"', "")
                day_list = [d.strip() for d in days_str.split(",")]
                
                # 2. Time Parsing Helper
                def parse_time(val):
                    # Case A: datetime.time object
                    if hasattr(val, 'hour') and hasattr(val, 'minute'):
                        return val.hour, val.minute
                    
                    # Case B: String (HH:MM or HH:MM:SS)
                    s_val = str(val).strip()
                    parts = s_val.split(':')
                    if len(parts) >= 2:
                        return int(parts[0]), int(parts[1])
                    return None, None

                sh, sm = parse_time(row["start_time"])
                eh, em = parse_time(row["end_time"])
                
                # Check validity
                if sh is None or eh is None:
                    # Skip invalid rows
                    continue

                # 3. Calculate Minutes
                start_total_min = (sh - START_HOUR) * 60 + sm
                end_total_min = (eh - START_HOUR) * 60 + em
                
                # 4. Filter out-of-bounds
                if end_total_min <= 0 or start_total_min >= (TOTAL_HOURS * 60):
                    continue
                    
                # 5. Clamp for Display
                display_start = max(0, start_total_min)
                display_end = min(TOTAL_HOURS * 60, end_total_min)
                
                display_duration = display_end - display_start
                if display_duration <= 0: continue

                # 6. Create Event Object
                color = get_color_for_title(row["title"])
                disp_start = f"{sh:02d}:{sm:02d}"
                disp_end = f"{eh:02d}:{em:02d}"
                
                evt_obj = {
                    "title": row["title"],
                    "time_str": f"{disp_start}~{disp_end}",
                    "top_px": (display_start / 60) * PIXELS_PER_HOUR,
                    "height_px": (display_duration / 60) * PIXELS_PER_HOUR,
                    "color": color
                }
                
                for d in day_list:
                    if d in events_by_day:
                        events_by_day[d].append(evt_obj)
                        
            except Exception as e:
                # Log error but don't break page
                print(f"Calendar Logic Error [Row]: {e}")
                continue

    # Generate HTML
    # We use a Flex layout: [TimeCol] [DayCol] [DayCol] ...
    
    # 1. Header Row
    header_html = f"""
    <div style="display: flex; border-bottom: 2px solid #dee2e6; margin-bottom: 0;">
        <div style="width: 50px; flex-shrink: 0; background: #f8f9fa;"></div> <!-- Spacer -->
    """
    for d in DAYS_ORDER:
        header_html += f"""
        <div style="flex: 1; text-align: center; font-weight: bold; padding: 10px 0; background: #f8f9fa; border-left: 1px solid #dee2e6;">
            {d}
        </div>
        """
    header_html += "</div>"
    
    # 2. Body (Scrollable Container)
    body_html = f'<div style="display: flex; position: relative; height: {TOTAL_HEIGHT}px; border-bottom: 1px solid #dee2e6;">'
    
    # 2.1 Time Column
    body_html += '<div style="width: 50px; flex-shrink: 0; background: #fafafa; border-right: 1px solid #dee2e6;">'
    first_loop = True
    for h in range(START_HOUR, END_HOUR):
        # Time label logic (08, 09...)
        # border-bottom should match grid lines.
        # box-sizing: border-box ensures height includes padding/border
        # height: 50px
        body_html += f"""
        <div style="
            height: {PIXELS_PER_HOUR}px; 
            border-bottom: 1px solid #e0e0e0; 
            text-align: center; 
            font-size: 0.8em; 
            color: #666; 
            padding-top: 5px; 
            box-sizing: border-box;
        ">
            {h:02d}
        </div>
        """
    body_html += "</div>"
    
    # 2.2 Day Columns
    for d in DAYS_ORDER:
        events_html = ""
        for evt in events_by_day[d]:
            # Event Block
            events_html += f"""
            <div style="
                position: absolute;
                top: {evt['top_px']}px;
                height: {max(20, evt['height_px'])}px; 
                left: 2px;
                right: 2px;
                background-color: {evt['color']};
                border-radius: 4px;
                padding: 2px 4px;
                font-size: 0.75em;
                line-height: 1.1;
                box-shadow: 1px 1px 2px rgba(0,0,0,0.15);
                overflow: hidden;
                z-index: 10;
                border: 1px solid rgba(0,0,0,0.05);
                box-sizing: border-box;
            " title="{evt['title']} ({evt['time_str']})">
                <div style="font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{evt['title']}</div>
                <div style="font-size: 0.8em; opacity: 0.8;">{evt['time_str']}</div>
            </div>
            """
            
        # Grid Lines for this day column
        grid_lines = ""
        for h in range(START_HOUR, END_HOUR):
            grid_lines += f"""
            <div style="height: {PIXELS_PER_HOUR}px; border-bottom: 1px solid #f0f0f0; box-sizing: border-box;"></div>
            """
            
        body_html += f"""
        <div style="flex: 1; position: relative; border-left: 1px solid #dee2e6; background-color: white;">
            {grid_lines}
            {events_html}
        </div>
        """
        
    body_html += "</div>"
    
    # Debug Collection
    parse_errors = []

    # Generate HTML
    # We use a Flex layout: [TimeCol] [DayCol] [DayCol] ...
    
    # ... (skipping unchanged parts of layout generation to focus on parsing loop) ...

    # Combined Layout with Mobile Responsive Wrapper
    full_html = f"""
    <style>
        .calendar-wrapper {{
            font-family: 'Arial', sans-serif; 
            border: 1px solid #dee2e6; 
            border-radius: 8px; 
            overflow-x: auto; 
            overflow-y: hidden;
            background: white;
        }}
        
        .calendar-container {{
            min-width: 100%;
        }}
        
        /* Mobile: Widen day columns for better readability */
        @media (max-width: 768px) {{
            .calendar-container {{
                min-width: 220%; /* Show ~3.5 days */
            }}
            
            .calendar-wrapper {{
                -webkit-overflow-scrolling: touch; /* Smooth scroll on iOS */
            }}
        }}
    </style>
    <div class="calendar-wrapper">
        <div class="calendar-container">
            {header_html}
            {body_html}
        </div>
    </div>
    """
    
    return full_html, parse_errors

# Fetch Data
try:
    # Use centralized filtering
    df_schedule = db_manager.get_weekly_schedule(assignee=target_child_id)
        
except Exception as e:
    st.error(f"데이터 로드 실패: {e}")
    df_schedule = pd.DataFrame()

# Navigation (Radio for Persistence)
# Replaced st.tabs with st.radio to prevent tab reset on save/rerun
current_tab = st.radio(
    "Navigation", 
    ["🗓️ 주간 시간표", "🛠️ 일정 등록/관리"], 
    horizontal=True, 
    label_visibility="collapsed",
    key="cal_nav_selection"
)
st.divider()

if current_tab == "🗓️ 주간 시간표":
    st.markdown("### 🕒 주간 시간표")
    html_code, errors = generate_html_timetable(df_schedule)
    
    if errors:
         with st.expander("⚠️ 데이터 파싱 경고", expanded=False):
              for e in errors: st.warning(e)

    # Use components.html for isolated rendering (Fixes 'Not Visible' issues with complex layout)
    import streamlit.components.v1 as components
    # Calculate approx height: Header (50) + Body (750) + Buffer
    components.html(html_code, height=850, scrolling=True)

if current_tab == "🛠️ 일정 등록/관리":
    st.subheader("📋 등록된 일정 목록")
    st.caption("💡 수정/삭제 시 **즉시 자동 저장**됩니다.")
    
    if not df_schedule.empty:
        # Prepare editor df
        # DEDUP SAFETY: Ensure editor sees unique rows only.
        edit_df = df_schedule[["schedule_id", "title", "days", "start_time", "end_time"]].copy()
        edit_df = edit_df.drop_duplicates(subset=["title", "days", "start_time", "end_time"])
        
        edited_schedule = st.data_editor(
            edit_df,
            column_config={
                "schedule_id": None, # Hide ID
                "title": st.column_config.TextColumn("일정 내용", required=True),
                "days": st.column_config.TextColumn("요일 (예: 월,수,금)", required=True),
                "start_time": st.column_config.TextColumn("시작 시간 (HH:MM)", required=True),
                "end_time": st.column_config.TextColumn("종료 시간 (HH:MM)", required=True),
            },
            num_rows="dynamic",
            width="stretch",
            key="schedule_editor"
        )
        
        st.caption("💡 수정 후 하단의 **[변경사항 저장]** 버튼을 눌러주세요.")
        
        # Batch Save Button
        # Batch Save Button
        if st.button("💾 변경사항 저장 (Save Changes)", type="primary"):
            def save_changes_action():
                import uuid
                # 1. Fetch ALL data
                all_schedules_raw = db_manager.get_weekly_schedule(assignee=None)
                if not all_schedules_raw.empty:
                    if "assignee" not in all_schedules_raw.columns:
                            all_schedules_raw["assignee"] = "son1"
                    else:
                            all_schedules_raw["assignee"] = all_schedules_raw["assignee"].fillna("son1")

                # 2. Keep others
                target_child_str = str(target_child_id)
                other_schedules = all_schedules_raw[all_schedules_raw["assignee"].astype(str) != target_child_str]
                
                # 3. New rows
                new_records = edited_schedule.to_dict('records')
                cleaned_new_records = []
                for r in new_records:
                        if not r.get("schedule_id") or pd.isna(r.get("schedule_id")):
                            r["schedule_id"] = str(uuid.uuid4())
                        r["assignee"] = target_child_id
                        cleaned_new_records.append(r)
                
                new_child_df = pd.DataFrame(cleaned_new_records)
                final_df = pd.concat([other_schedules, new_child_df], ignore_index=True)
                
                return db_manager.update_data("WeeklySchedule", final_df)

            ui_components.handle_submission(save_changes_action, success_msg="일정이 저장되었습니다!")
                 
    else:
        st.info("아직 등록된 일정이 없습니다.")

    st.divider()
    st.subheader("➕ 새 일정 등록하기 (상세)")
    
    with st.form("add_weekly_schedule_form", clear_on_submit=True):
        s_title = st.text_input("일정 내용", placeholder="예: 영어학원")
        s_days = st.pills("요일 선택", DAYS_ORDER, selection_mode="multi", default=["월", "목"])
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            s_sh = st.selectbox("시작 시", [f"{h:02d}" for h in range(7, 24)], index=5)
        with c2:
            s_sm = st.selectbox("시작 분", ["00", "10", "20", "30", "40", "50"])
        with c3:
            s_eh = st.selectbox("종료 시", [f"{h:02d}" for h in range(7, 24)], index=6)
        with c4:
            s_em = st.selectbox("종료 분", ["00", "10", "20", "30", "40", "50"])
            
        submitted = st.form_submit_button("등록")

    if submitted:
        if not s_title or not s_days:
            st.error("내용과 요일을 입력해주세요.")
        else:
            final_days = ",".join(s_days)
            final_start = f"{s_sh}:{s_sm}"
            final_end = f"{s_eh}:{s_em}"
            
            def add_schedule_action():
                 return db_manager.add_weekly_schedule(s_title, final_days, final_start, final_end, assignee=target_child_id)
            
            ui_components.handle_submission(add_schedule_action, success_msg="등록 완료!")
