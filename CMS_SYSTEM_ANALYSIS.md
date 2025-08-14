# CMS 시스템 분석 문서

## 시스템 개요
BC카드 문서 기반 질의응답(QA) 시스템으로, LangChain과 ChromaDB를 활용한 RAG(Retrieval-Augmented Generation) 아키텍처로 구성되어 있습니다.

## 프로젝트 구조
```
03_DEOTIS_QA/
├── rag-qa-system/          # 메인 애플리케이션
│   ├── models/             # 데이터 모델
│   ├── services/           # 비즈니스 로직
│   ├── routes/             # API 라우트
│   ├── static/             # 정적 파일
│   ├── templates/          # HTML 템플릿
│   └── utils/              # 유틸리티
├── s3/                     # BC카드 문서
├── redis/                  # Redis 설정
├── data/                   # 데이터베이스 파일
└── start_redis.bat         # Redis 실행 스크립트
```

## 기술 스택
- **백엔드**: Flask 3.0.0, Flask-RESTX (Swagger UI)
- **AI/ML**: LangChain, OpenAI GPT-4, ChromaDB
- **캐시**: Redis, SQLite (하이브리드 캐시)
- **문서처리**: pypdf2, python-docx, unstructured
- **임베딩**: text-embedding-3-small

## 주요 설정
### 서버 설정
- **포트**: 5001
- **디버그**: True
- **CORS**: 활성화

### LLM 설정
- **모델**: gpt-4o-mini (기본)
- **온도**: 0.7
- **최대 토큰**: 2000

### 문서 처리
- **청크 크기**: 1000
- **오버랩**: 200
- **최대 파일 크기**: 10MB

### 캐시 설정
- **타입**: SQLite/Redis (선택 가능)
- **TTL**: 24시간
- **Redis 포트**: 6379

## API 엔드포인트
- `/api/chat` - 질의응답
- `/api/documents` - 문서 관리
- `/api/admin` - 관리자 설정
- `/api/settings` - 시스템 설정

## 데이터베이스
### SQLite
- `query_cache.db` - 쿼리 캐시
- `document_validation.db` - 문서 검증
- `popular_cache.db` - 인기 검색어
- `search_stats.db` - 검색 통계
- `chroma.sqlite3` - 벡터 DB

### Redis
- 포트: 6379
- 최대 메모리: 256MB
- LRU 캐시 정책

## 시작 방법

### 1. Redis 시작
```bash
# Windows CMD에서 실행
cd /d D:\99_DEOTIS_QA_SYSTEM\03_DEOTIS_QA
start_redis.bat
```

### 2. Flask 서버 시작
```bash
# 가상환경 활성화 (선택사항)
python -m venv venv
venv\Scripts\activate  # Windows

# 의존성 설치
pip install -r rag-qa-system/requirements.txt

# 서버 실행
cd rag-qa-system
python app.py
```

### 3. 접속 URL
- **메인 애플리케이션**: http://localhost:5001
- **Swagger UI**: http://localhost:5001/swagger

## 환경 변수 (.env)
```env
OPENAI_API_KEY=your_api_key
ANTHROPIC_API_KEY=your_api_key
CHROMA_PERSIST_DIRECTORY=./data/vectordb
FLASK_PORT=5001
LLM_MODEL=gpt-4o-mini
```

## 주요 기능
1. **문서 업로드**: PDF, DOCX, TXT, MD 지원
2. **벡터 검색**: 의미론적 유사도 기반 검색
3. **하이브리드 캐시**: SQLite/Redis 선택 가능
4. **관리자 인터페이스**: 시스템 설정 관리
5. **Swagger API 문서**: 자동 생성 API 문서

## 개발시 참고사항
- 모든 API는 Flask-RESTX로 문서화됨
- 캐시 타입은 admin_settings.json에서 변경 가능
- 문서 청킹 전략은 설정에서 조정 가능
- LLM 모델은 환경 변수로 변경 가능