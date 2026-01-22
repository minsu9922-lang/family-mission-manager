"""쿠폰 관련 유틸리티 함수

쿠폰 파싱, 시간 계산 등의 공통 로직을 제공합니다.
"""
import re
from typing import Optional


def parse_coupon_name(content: str) -> Optional[str]:
    """로그 Content에서 쿠폰명 추출
    
    Args:
        content: "쿠폰: 게임쿠폰 20분" 형식의 문자열
    
    Returns:
        쿠폰명 또는 None
        
    Examples:
        >>> parse_coupon_name("쿠폰: 게임쿠폰 20분")
        '게임쿠폰 20분'
        >>> parse_coupon_name("도장: 참 잘했어요")
        None
    """
    if "쿠폰:" in content:
        return content.split("쿠폰:", 1)[1].strip()
    return None


def extract_minutes_from_coupon(coupon_name: str) -> int:
    """쿠폰명에서 분 단위 시간 추출
    
    Args:
        coupon_name: "게임쿠폰 20분" 형식의 문자열
    
    Returns:
        분 단위 시간 (추출 실패 시 0)
        
    Examples:
        >>> extract_minutes_from_coupon("게임쿠폰 20분")
        20
        >>> extract_minutes_from_coupon("보너스쿠폰")
        0
    """
    match = re.search(r'(\d+)\s*분', coupon_name)
    return int(match.group(1)) if match else 0


def format_minutes(total_minutes: int) -> str:
    """분을 읽기 쉬운 형식으로 변환
    
    Args:
        total_minutes: 총 분
    
    Returns:
        "1시간 30분" 또는 "45분" 형식의 문자열
        
    Examples:
        >>> format_minutes(90)
        '1시간 30분'
        >>> format_minutes(60)
        '1시간'
        >>> format_minutes(45)
        '45분'
    """
    if total_minutes >= 60:
        hours = total_minutes // 60
        mins = total_minutes % 60
        if mins > 0:
            return f"{hours}시간 {mins}분"
        return f"{hours}시간"
    return f"{total_minutes}분"
