"""미션 관리 모듈

미션 CRUD (생성, 조회, 수정, 삭제) 로직을 담당합니다.
"""
import pandas as pd
from modules.db_manager import db_manager


class MissionManager:
    """미션 상태 및 정의 관리"""
    
    def __init__(self):
        """초기화"""
        pass
    
    def save_pending_changes(self, edited_pending: pd.DataFrame, 
                            status_map_inv: dict) -> bool:
        """대기 중 미션 변경사항 저장
        
        Args:
            edited_pending: 편집된 대기 중 미션 DataFrame
            status_map_inv: 상태 한글→영어 매핑
        
        Returns:
            성공 여부
        """
        try:
            all_raw = db_manager.get_missions(assignee=None) 
            changes = 0
            
            for r in edited_pending.to_dict('records'):
                mid = r['mission_id']
                kor_s = r['상태']
                reas = r['rejection_reason']
                eng_s = status_map_inv.get(kor_s, "Pending")
                
                idx = all_raw[all_raw['mission_id'] == mid].index
                if not idx.empty:
                    if all_raw.loc[idx[0], 'status'] != eng_s or str(all_raw.loc[idx[0], 'rejection_reason']) != str(reas):
                        all_raw.loc[idx[0], 'status'] = eng_s
                        all_raw.loc[idx[0], 'rejection_reason'] = str(reas) if reas else ""
                        changes += 1
            
            if changes > 0:
                return db_manager.update_data("Missions", all_raw)
            return False
        except Exception as e:
            print(f"대기 중 미션 저장 오류: {e}")
            return False
    
    def save_definitions(self, edited_defs: pd.DataFrame, target_child_id: str) -> bool:
        """미션 정의 저장
        
        Args:
            edited_defs: 편집된 미션 정의 DataFrame
            target_child_id: 대상 자녀 ID
        
        Returns:
            성공 여부
        """
        try:
            import uuid
            
            # 1. Fetch RAW ALL
            all_raw = db_manager.get_mission_definitions(assignee=None)
            
            # 2. Filter out current child's OLD data
            if not all_raw.empty:
                if "assignee" not in all_raw.columns:
                    all_raw["assignee"] = "son1"
                others = all_raw[all_raw["assignee"] != target_child_id]
            else:
                others = pd.DataFrame()
            
            # 3. Process Editor Data
            saved_df = edited_defs.copy()
            
            # Rename Back
            saved_df.columns = ["def_id", "assignee", "active", "title", "type", "frequency", "note"]
            saved_df["assignee"] = target_child_id
            
            # Fill Missing IDs for New Rows
            if not saved_df.empty:
                def ensure_id(x):
                    if pd.isna(x) or str(x).strip() == "":
                        return str(uuid.uuid4())
                    return str(x)
                saved_df["def_id"] = saved_df["def_id"].apply(ensure_id)
            
            # 4. Combine
            final_defs = pd.concat([others, saved_df], ignore_index=True)
            
            # 5. Save
            return db_manager.update_data("Mission_Definitions", final_defs)
        except Exception as e:
            print(f"미션 정의 저장 오류: {e}")
            return False
    
    def save_history(self, edited_history: pd.DataFrame, status_map_inv: dict) -> bool:
        """미션 이력 저장
        
        Args:
            edited_history: 편집된 이력 DataFrame
            status_map_inv: 상태 한글→영어 매핑
        
        Returns:
            성공 여부
        """
        try:
            current_ids = [r['mission_id'] for r in edited_history.to_dict('records')]
            original_ids = edited_history['mission_id'].tolist()
            deleted_ids = set(original_ids) - set(current_ids)
            
            all_raw = db_manager.get_missions(assignee=None)
            
            # Handle Deletions
            if deleted_ids:
                all_raw = all_raw[~all_raw['mission_id'].isin(deleted_ids)]
            
            # Handle Updates
            for r in edited_history.to_dict('records'):
                mid = r['mission_id']
                kor_s = r['상태']
                reas = r.get('rejection_reason', '')
                eng_s = status_map_inv.get(kor_s, "Assigned")
                
                idx = all_raw[all_raw['mission_id'] == mid].index
                if not idx.empty:
                    all_raw.loc[idx[0], 'status'] = eng_s
                    all_raw.loc[idx[0], 'rejection_reason'] = str(reas) if reas else ""
            
            return db_manager.update_data("Missions", all_raw)
        except Exception as e:
            print(f"미션 이력 저장 오류: {e}")
            return False
