"""데이터 로딩 유틸리티 모듈

안전한 데이터 로딩 및 검증 로직을 중앙화합니다.
"""
import pandas as pd
import streamlit as st


def load_dataframe_safely(df, required_columns=None, default_values=None, empty_columns=None):
    """DataFrame을 안전하게 로드하고 검증합니다.
    
    Args:
        df: 로드할 DataFrame (None 가능)
        required_columns: 필수 컬럼 리스트 (없으면 빈 문자열로 추가)
        default_values: 컬럼별 기본값 딕셔너리 (예: {"category": "General"})
        empty_columns: df가 비어있을 때 사용할 컬럼 리스트 (기본값: required_columns)
    
    Returns:
        검증된 DataFrame
    
    Examples:
        >>> df = load_dataframe_safely(
        ...     db_manager.get_settings(),
        ...     required_columns=["category", "item_name", "value"],
        ...     default_values={"target_child": "All"}
        ... )
    """
    # 1. None 체크 및 복사
    if df is not None and not df.empty:
        df = df.copy()
        # 컬럼 이름 정리 (공백 제거 및 소문자화)
        df.columns = [str(c).strip().lower() for c in df.columns]
    else:
        # 빈 DataFrame 생성
        cols = empty_columns if empty_columns else (required_columns if required_columns else [])
        df = pd.DataFrame(columns=cols)
    
    # 2. 빈 DataFrame 체크
    if df.empty and empty_columns:
        df = pd.DataFrame(columns=empty_columns)
    
    # 3. 필수 컬럼 확인 및 추가
    if required_columns:
        for col in required_columns:
            if col not in df.columns:
                # default_values에 정의된 값 사용, 없으면 빈 문자열
                default_val = default_values.get(col, "") if default_values else ""
                df[col] = default_val
    
    # 4. 기본값 적용 (이미 존재하는 컬럼의 NaN 값에도 적용)
    if default_values and not df.empty:
        for col, val in default_values.items():
            if col in df.columns:
                df[col] = df[col].fillna(val)
    
    return df


def validate_dataframe_columns(df, required_columns, operation_name="Data Loading"):
    """DataFrame에 필수 컬럼이 있는지 검증하고 에러 메시지를 표시합니다.
    
    Args:
        df: 검증할 DataFrame
        required_columns: 필수 컬럼 리스트
        operation_name: 작업 이름 (에러 메시지용)
    
    Returns:
        bool: 모든 필수 컬럼이 존재하면 True
    
    Raises:
        ValueError: 필수 컬럼이 누락된 경우
    """
    missing_cols = [col for col in required_columns if col not in df.columns]
    
    if missing_cols:
        error_msg = f"{operation_name} 실패: 필수 컬럼 누락 - {missing_cols}"
        st.error(error_msg)
        raise ValueError(error_msg)
    
    return True


def safe_filter_dataframe(df, column, value, fallback_empty=True):
    """안전하게 DataFrame을 필터링합니다.
    
    Args:
        df: 필터링할 DataFrame
        column: 필터 컬럼명
        value: 필터 값
        fallback_empty: 컬럼이 없을 때 빈 DataFrame 반환 여부
    
    Returns:
        필터링된 DataFrame (컬럼이 없으면 빈 DataFrame 또는 원본)
    """
    if df.empty:
        return df
    
    # 컬럼명이 리스트인 경우와 단일 문자열인 경우 분리 처리
    cols_to_check = [column] if isinstance(column, str) else column
    
    # 실제 DF 컬럼들과 대조 (소문자 기준)
    df_cols_lower = {str(c).lower(): str(c) for c in df.columns}
    
    final_cols = []
    for c in cols_to_check:
        c_lower = str(c).lower()
        if c_lower in df_cols_lower:
            final_cols.append(df_cols_lower[c_lower])
        else:
            # 필수 컬럼이 하나라도 없으면 빈 DataFrame 반환
            if fallback_empty:
                return pd.DataFrame(columns=df.columns)
            return df

    # 단일 컬럼 필터링 (가장 흔한 케이스)
    if isinstance(column, str):
        actual_col = final_cols[0]
        # [ULTIMATE] 문자열인 경우 값 비교 시 대소문자 무시 + 공백 제거
        if isinstance(value, str):
            return df[df[actual_col].astype(str).str.strip().str.lower() == value.strip().lower()].copy()
        return df[df[actual_col] == value].copy()
    
    # 멀티 컬럼 필터링
    mask = True
    for i, col_name in enumerate(final_cols):
        target_val = value[i] if isinstance(value, list) else value
        # [ULTIMATE] 멀티 컬럼에서도 문자열은 소문자 비교 + 공백 제거
        if isinstance(target_val, str):
            mask &= (df[col_name].astype(str).str.strip().str.lower() == target_val.strip().lower())
        else:
            mask &= (df[col_name] == target_val)
    
    return df[mask].copy()


def strip_dataframe_columns(df):
    """DataFrame의 모든 컬럼 이름에서 공백을 제거합니다.
    
    Args:
        df: 처리할 DataFrame
    
    Returns:
        컬럼 이름이 정리된 DataFrame
    """
    if df is None or df.empty:
        return df
    
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df
