import time
import os
import sys
import pandas as pd
from datetime import datetime

# 프로젝트 루트 경로 추가
sys.path.append(os.getcwd())

from modules.db_manager import db_manager

def run_stress_test_v2(iterations=100, interval=3):
    print(f"==================================================")
    print(f"REWARD STRESS TEST V2 START")
    print(f"Target: {iterations} iterations with {interval}s interval")
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"==================================================")
    
    success_count = 0
    fail_count = 0
    results = []

    test_user = "StressTester"
    
    for i in range(1, iterations + 1):
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            content = f"Stress Test Reward #{i}"
            reward = 100
            
            # 보상 지급 (로그 기록)
            # log_activity(user_name, activity_type, content, reward=0)
            db_manager.log_activity(test_user, "Mission", content, reward=reward)
            
            success_count += 1
            print(f"[{i}/{iterations}] SUCCESS: {content} at {timestamp}")
            results.append({"iter": i, "status": "Success", "time": timestamp})
            
        except Exception as e:
            fail_count += 1
            print(f"[{i}/{iterations}] FAILED: {e}", flush=True)
            results.append({"iter": i, "status": "Failed", "error": str(e), "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
        
        # Always sleep 3 seconds as per user instruction
        if i < iterations:
            time.sleep(interval)
            
    print(f"\n==================================================")
    print(f"📊 TEST SUMMARY")
    print(f"Total Iterations: {iterations}")
    print(f"Success: {success_count}")
    print(f"Failed: {fail_count}")
    print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 최종 데이터 무결성 검증 (백업 파일 확인)
    print(f"\nSEARCHING FOR DATA INTEGRITY...")
    try:
        backup_file = "data/backups/Logs_latest.csv"
        if os.path.exists(backup_file):
            df = pd.read_csv(backup_file)
            test_logs = df[df["User"] == test_user]
            count_in_file = len(test_logs)
            
            print(f"File: {backup_file}")
            print(f"Columns: {list(df.columns)}")
            print(f"Records for {test_user}: {count_in_file}")
            
            if count_in_file == iterations:
                print("PASSED: All 100 records found in backup with correct structure!")
            else:
                print(f"WARNING: Found {count_in_file}/{iterations} records.")
        else:
            print(f"FILE NOT FOUND: {backup_file}")
    except Exception as e:
        print(f"ERROR: Verification failed: {e}")
    print(f"==================================================")

if __name__ == "__main__":
    # 100회 테스트 실행 (간격 3초)
    # 실제 환경에서는 시간이 오래 걸리므로 (약 300초), 보고를 위해 실행 시작을 알림
    run_stress_test_v2(100, 3)
