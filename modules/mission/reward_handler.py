"""보상 처리 모듈

도장 및 쿠폰 지급 로직을 담당합니다.
"""
from modules.db_manager import db_manager


class RewardHandler:
    """보상 지급 및 관리"""
    
    def __init__(self):
        """초기화"""
        pass
    
    def grant_final_approval_rewards(self, user_name: str, stamp_type: str, stamp_qty: int,
                                     coupon_type: str, coupon_qty: int) -> bool:
        """최종 승인 보상 일괄 지급
        
        Args:
            user_name: 사용자 이름
            stamp_type: 도장 종류
            stamp_qty: 도장 개수
            coupon_type: 쿠폰 종류
            coupon_qty: 쿠폰 장수
        
        Returns:
            성공 여부
        """
        try:
            if stamp_qty > 0:
               db_manager.log_activity(user_name, "Mission", f"도장: {stamp_type}", stamp_qty)
            
            if coupon_qty > 0:
                db_manager.log_activity(user_name, "Coupon", f"쿠폰: {coupon_type}", coupon_qty)
            
            return True
        except Exception as e:
            print(f"보상 지급 오류: {e}")
            return False
    
    def grant_stamp(self, user_name: str, stamp_type: str, quantity: int) -> bool:
        """도장 지급
        
        Args:
            user_name: 사용자 이름
            stamp_type: 도장 종류
            quantity: 개수
        
        Returns:
            성공 여부
        """
        try:
            db_manager.log_activity(user_name, "Mission", f"도장: {stamp_type}", quantity)
            return True
        except Exception as e:
            print(f"도장 지급 오류: {e}")
            return False
    
    def grant_coupon(self, user_name: str, coupon_type: str, quantity: int) -> bool:
        """쿠폰 지급
        
        Args:
            user_name: 사용자 이름
            coupon_type: 쿠폰 종류
            quantity: 장수
        
        Returns:
            성공 여부
        """
        try:
            db_manager.log_activity(user_name, "Coupon", f"쿠폰: {coupon_type}", quantity)
            return True
        except Exception as e:
            print(f"쿠폰 지급 오류: {e}")
            return False
