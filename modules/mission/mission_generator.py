"""미션 자동 생성 모듈

오늘의 미션을 자동으로 생성하는 로직을 담당합니다.
"""
from datetime import datetime
import uuid
import pandas as pd
from modules.db_manager import db_manager
import modules.time_utils as time_utils
import streamlit as st


class MissionGenerator:
    """일일 미션 자동 생성기"""
    
    def __init__(self):
        """초기화"""
        pass
    
    def ensure_todays_missions(self, target_child_id: str) -> None:
        """오늘의 미션이 없으면 자동 생성
        
        Args:
            target_child_id: 대상 자녀 ID
        
        Note:
            세션 상태를 사용하여 중복 생성 방지
        """
        if "todays_missions_checked" not in st.session_state:
            st.session_state["todays_missions_checked"] = {}
        
        today_str = time_utils.get_today_str()
        check_key = f"{target_child_id}_{today_str}"
        
        if st.session_state["todays_missions_checked"].get(check_key):
            return

        try:
            defs_df = db_manager.get_mission_definitions(assignee=target_child_id)
            if defs_df.empty:
                return

            missions_df = db_manager.get_missions(assignee=target_child_id)
            existing_titles = []
            if not missions_df.empty:
                existing_today = missions_df[missions_df["date"] == today_str]
                existing_titles = existing_today["title"].tolist()

            new_missions = []
            today_date = time_utils.get_now()
            weekday_map = ["월", "화", "수", "목", "금", "토", "일"]
            today_weekday = weekday_map[today_date.weekday()]

            for _, row in defs_df.iterrows():
                if not row.get("active", True):
                    continue
                
                title = row["title"]
                def_type = row["type"]
                freq = row["frequency"]
                note = row.get("note", "")

                should_create = self._should_create_mission(
                    def_type, freq, today_weekday, today_str
                )
                
                if should_create and title not in existing_titles:
                    new_missions.append({
                        "mission_id": str(uuid.uuid4()),
                        "date": today_str,
                        "assignee": target_child_id,
                        "title": title,
                        "status": "Assigned", 
                        "rejection_reason": note
                    })
                    existing_titles.append(title)
            
            if new_missions:
                all_missions = db_manager.get_missions()
                added_df = pd.DataFrame(new_missions)
                if all_missions.empty:
                    final_df = added_df
                else:
                    final_df = pd.concat([all_missions, added_df], ignore_index=True)
                
                if db_manager.update_data("Missions", final_df):
                    st.session_state["todays_missions_checked"][check_key] = True
        
        except Exception as e:
            st.error(f"미션 생성 중 오류: {e}")
    
    def _should_create_mission(self, def_type: str, freq: str, 
                               today_weekday: str, today_str: str) -> bool:
        """미션 생성 여부 판단
        
        Args:
            def_type: 미션 타입 (Routine/OneTime)
            freq: 빈도 (요일 또는 날짜)
            today_weekday: 오늘 요일
            today_str: 오늘 날짜 문자열
        
        Returns:
            생성 여부
        """
        if def_type == "Routine":
            return today_weekday in str(freq)
        elif def_type == "OneTime":
            return str(freq) == today_str
        
        return False
