# [보물지도: Family Hub] 기술 사양서 (TRD.md)

## 권장 스택

- **Framework**: Python 3.12 + Streamlit 1.41.0 (최신 안정 버전)
- **Database**: Google Sheets (via st-gsheets-connection)
- **Authentication**: streamlit-authenticator (Cookie 기반 세션 관리)
- **Deployment**: GitHub + Render Cloud (Private Web Service)

## 선정 이유

- **AI 협업 효율**: Streamlit은 코드 구조가 직관적이어서 비개발자가 AI에게 수정을 요청할 때 오류 발생률이 가장 낮습니다.
- **반응형 UI**: 추가 디자인 작업 없이도 모바일, 태블릿, PC 환경에 맞는 최적의 레이아웃을 제공합니다.
- **데이터 접근성**: 코드를 몰라도 부모님이 구글 시트를 직접 열어 데이터를 백업하거나 관리할 수 있습니다.

## 핵심 아키텍처 및 스타일 가이드

### 데이터 스키마 (Google Sheets Tabs)

1. **Users**: ID, PW, 이름, 역할, 아이별 도장 금액 설정.
2. **Missions**: 오늘의 미션 리스트, 상태(대기/승인/완료), 대상자.
3. **Logs**: 모든 활동 이력 (시간, 유형, 내용, 보상 금액).
4. **Settings**: 게임 쿠폰 종류(이름, 시간), 도장 종류(이름, 금액).

### 디렉토리 구조 (Modular)

```
/
├── .streamlit/          # secrets.toml (API 키, 쿠키 정보 저장)
├── app.py               # 로그인 처리 및 메인 라우팅
├── modules/             # 데이터베이스 연동 로직 (CRUD)
├── pages/               # 탭별 독립 모듈 (Schedule, Mission, Wallet, Settings)
└── requirements.txt     # 필수 라이브러리 목록
```

### 개인정보 보호 방안

- `st.secrets`를 사용하여 구글 시트 URL과 인증 정보를 코드와 분리.
- 로그인되지 않은 사용자의 접근을 원천 차단하는 가드 로직 적용.
