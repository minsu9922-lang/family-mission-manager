"""보상 처리 모듈

도장 및 쿠폰 지급 로직을 담당합니다.
"""
from modules.db_manager import db_manager


class RewardHandler:
    """보상 지급 및 관리"""
    
    def __init__(self):
        """초기화"""
        pass
    
    def _get_reward_metadata(self, category: str, item_name: str) -> tuple:
        """아이템명에서 단위 정보와 단가를 추출"""
        try:
            settings_df = db_manager.get_settings()
            # 1. 사이즈/단위 추출
            sub_type = "Normal"
            if "(" in item_name and ")" in item_name:
                sub_type = item_name.split("(")[-1].split(")")[0]
            
            # 2. 단가 조회
            unit_price = 0
            match = settings_df[(settings_df["category"] == category) & (settings_df["item_name"] == item_name)]
            if not match.empty:
                unit_price = int(match.iloc[0]["value"])
            else:
                # 기본값 설정
                if category == "Stamp": unit_price = 100
                elif category == "Coupon": unit_price = 0
            
            return sub_type, unit_price
        except:
            return "Normal", 0

    def grant_final_approval_rewards(self, user_name: str, stamp_type: str, stamp_qty: int,
                                     coupon_type: str, coupon_qty: int) -> bool:
        """최종 승인 보상 일괄 지급 (정산 대기 상태로 기록)"""
        try:
            # 1. 도장 지급
            if stamp_qty > 0:
                sub_type, unit_price = self._get_reward_metadata("Stamp", stamp_type)
                db_manager.log_reward(
                    user_name=user_name,
                    category="Stamp",
                    sub_type=sub_type,
                    item_name=stamp_type,
                    quantity=stamp_qty,
                    unit_price=unit_price,
                    status="Earned", # 보유/정산대기 상태
                    note="오늘의 미션 최종 승인 보상"
                )
            
            # 2. 쿠폰 지급
            if coupon_qty > 0:
                sub_type, unit_price = self._get_reward_metadata("Coupon", coupon_type)
                db_manager.log_reward(
                    user_name=user_name,
                    category="Coupon",
                    sub_type=sub_type,
                    item_name=coupon_type,
                    quantity=coupon_qty,
                    unit_price=0, # 쿠폰은 단가 0원 고정
                    status="Earned",
                    note="오늘의 미션 최종 승인 보너스"
                )
            
            return True
        except Exception as e:
            print(f"보상 지급 오류: {e}")
            return False
    
    def grant_stamp(self, user_name: str, stamp_type: str, quantity: int) -> bool:
        """도장 지급 (정규화된 Reward 시트 기록)"""
        try:
            sub_type, unit_price = self._get_reward_metadata("Stamp", stamp_type)
            return db_manager.log_reward(user_name, "Stamp", sub_type, stamp_type, quantity, unit_price, "Earned")
        except Exception as e:
            print(f"도장 지급 오류: {e}")
            return False
    
    def grant_coupon(self, user_name: str, coupon_type: str, quantity: int) -> bool:
        """쿠폰 지급 (정규화된 Reward 시트 기록)"""
        try:
            sub_type, unit_price = self._get_reward_metadata("Coupon", coupon_type)
            return db_manager.log_reward(user_name, "Coupon", sub_type, coupon_type, quantity, unit_price, "Earned")
        except Exception as e:
            print(f"쿠폰 지급 오류: {e}")
            return False
