import sys
import os
import time
import pandas as pd

# 모듈 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.db_manager import db_manager

def run_stress_test(iterations=100):
    print(f"--- [STRESS TEST] Starting {iterations} consecutive log entries... ---")
    
    success_count = 0
    fail_count = 0
    start_time = time.time()
    
    # 테스트용 데이터
    user_name = "테스트유저"
    activity_type = "Mission"
    content = "도장: 스트레스 테스트"
    reward = 1
    
    for i in range(1, iterations + 1):
        try:
            # 실시간으로 db_manager의 log_activity를 호출하여 시트 쓰기 부하 테스트
            # 이 함수는 내부적으로 _retry_operation을 사용함
            print(f"[{i}/{iterations}] 기록 시도 중...", end="\r")
            db_manager.log_activity(user_name, activity_type, content, reward)
            success_count += 1
        except Exception as e:
            print(f"\n❌ [{i}회차] 에러 발생: {e}")
            fail_count += 1
            # 치명적인 에러(인증 등)면 중단, Quota 에러면 계속 시도될 것
            if "Invalid private key" in str(e):
                print("🛑 인증 오류로 테스트를 중단합니다.")
                break
        
        # API 제한을 고려하여 아주 약간의 간격 유지 (실제 사용자 클릭 속도 모사)
        # 만약 너무 빠르면 429 에러가 발생하며 db_manager의 리트라이 로직이 작동하는지 볼 수 있음
        time.sleep(0.1) 

    end_time = time.time()
    duration = end_time - start_time
    
    print("\n\n" + "="*50)
    print("📊 스트레스 테스트 결과 보고서")
    print("="*50)
    print(f"1. 총 시도 횟수: {iterations}회")
    print(f"2. 성공 횟수: {success_count}회")
    print(f"3. 실패 횟수: {fail_count}회")
    print(f"4. 총 소요 시간: {duration:.2f}초")
    print(f"5. 평균 처리 속도: {duration/iterations:.2f}초/건")
    print("="*50)
    
    if fail_count == 0:
        print("✅ 결과: 모든 요청이 안정적으로 처리되었습니다. (KeyError 없음, 리트라이 로직 유효)")
    else:
        print(f"⚠️ 결과: {fail_count}건의 실패가 발생했습니다. 로그를 확인하세요.")

if __name__ == "__main__":
    # 실제 시트에 직접 써야 하므로 주의가 필요하지만, 
    # 사용자님이 '보상 버튼 100번 클릭' 상황을 검증하라 하셨으므로 
    # 실제 API 레벨의 부하 테스트를 수행합니다.
    run_stress_test(100)
