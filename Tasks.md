# Role: Senior Python & Streamlit Developer

# Project: "Treasure Map" - Family Management System

너는 Python 3.12와 Streamlit 1.41.0 환경에서 구글 스프레드시트를 DB로 사용하는 수석 아키텍트야.
첨부된 요구사항과 기술 사양을 바탕으로 코드를 작성해줘.

## 핵심 요구사항:

1. **인증 시스템:** `streamlit-authenticator`를 사용하여 dad, mom, son1, son2 계정을 구현해. 새로고침해도 로그아웃되지 않도록 `cookie_expiry` 설정을 포함해.
2. **권한 분리:** - '부모(dad, mom)'는 모든 데이터의 읽기/쓰기/삭제/승인 권한을 가짐.
   - '아이(son1, son2)'는 본인 데이터의 읽기 중심이며, 독서/칭찬 탭에서만 쓰기 가능.
3. **데이터 연동:** `st-gsheets-connection`을 사용해 구글 스프레드시트와 실시간 연동해. 모든 작업(승인, 등록 등)은 즉시 시트에 반영되어야 해.
4. **미션 승인 로직:** 아이가 각각의 미션에 대해 '미션 클리어' 클릭 -> 부모 화면에 승인 대기 목록 노출 -> 부모 확인 (승인 또는 거절) 및 이력 저장. 오늘의 미션 모두 클리어 후 부모가 '도장/쿠폰' 선택 후 승인 -> 이력 저장 및 지갑 잔액 업데이트.
5. **UI/UX:** 모바일과 PC에서 모두 깔끔하게 보이도록 `st.sidebar`와 `st.tabs`를 활용하고, 성능 최적화를 위해 `st.cache_data`를 전략적으로 사용해.
