import pandas as pd
import sys
import os

# 모듈 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.data_utils import load_dataframe_safely, safe_filter_dataframe

def test_keyerror_scenarios():
    print("--- Todays_Mission KeyError 시나리오 테스트 시작 ---")
    
    # 시나리오 1: Settings 시트가 완전히 비어있거나 'category' 컬럼이 없는 경우
    df_empty = pd.DataFrame(columns=["아이디", "값"]) # 잘못된 컬럼명
    print("\n[테스트 1] 컬럼명 불일치 및 데이터 부재 상황")
    
    # db_manager.get_settings() 내부 로직 모사
    required = ["category", "item_name", "value", "unit", "target_child"]
    df_safe = load_dataframe_safely(df_empty, required_columns=required, empty_columns=required)
    
    print(f"1-1. safe_load 적용 후 컬럼: {df_safe.columns.tolist()}")
    
    # 231라인의 필터링 로직 모사 (문제가 된 지점)
    # stamps = df_safe[df_safe['category'] == 'Stamp'].copy() # <- 이 방식이 위험함
    
    # 개선된 필터링 방식 테스트
    stamps = safe_filter_dataframe(df_safe, 'category', 'Stamp')
    print(f"1-2. safe_filter 적용 결과: 결측치 없이 처리됨 (Row count: {len(stamps)})")
    
    # 시나리오 2: category 컬럼은 있으나 데이터가 없는 경우
    df_no_data = pd.DataFrame(columns=required)
    print("\n[테스트 2] 필수 컬럼은 있으나 데이터가 없는 상황")
    stamps_2 = safe_filter_dataframe(df_no_data, 'category', 'Stamp')
    print(f"2-1. Row count: {len(stamps_2)}")
    
    print("\n--- 모든 시나리오 테스트 통과 (KeyError 발생 없음) ---")

if __name__ == "__main__":
    test_keyerror_scenarios()
