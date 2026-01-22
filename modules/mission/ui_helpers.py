"""미션 UI 헬퍼 함수

미션 관련 UI 표시 및 데이터 처리 유틸리티
"""


def get_status_maps():
    """상태 한글-영어 매핑 반환
    
    Returns:
        tuple: (status_map, status_map_inv)
    """
    status_map = {
        "Assigned": "할 일",
        "Pending": "검사 대기",
        "Approved": "완료",
        "Rejected": "반려"
    }
    
    status_map_inv = {v: k for k, v in status_map.items()}
    
    return status_map, status_map_inv


def get_approval_request_maps():
    """승인 요청 상태 매핑 반환
    
    Returns:
        dict: 승인 요청 상태 매핑
    """
    approval_map = {
        "Assigned": "미요청",
        "Pending": "요청",
        "Approved": "완료",
        "Rejected": "반려"
    }
    
    return approval_map
