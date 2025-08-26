# RAG QA System - 전체 시스템 문서

## 📊 시스템 개요

### 🏗 Architecture
- **Framework**: Flask + LangChain + ChromaDB
- **Vector DB**: ChromaDB (Persistent Storage)
- **LLM Models**: 
  - API: ChatGPT (gpt-4o-mini)
  - Local: Ollama (llama3.2 / 야놀자 커스텀)
- **Cache**: Redis + SQLite hybrid
- **Frontend**: HTML/JS (No Framework)
- **Chunking**: Basic (1000/200) + Custom (/$$/)

### 🎯 주요 기능
1. **4카드 비동기 UI**: 검색 시 즉시 로딩 영역 표시 → 완료 순서대로 결과 표시
2. **이중 벡터DB**: 기본청킹 vs 커스텀청킹 비교
3. **하이브리드 LLM**: ChatGPT API + 로컬LLM 동시 비교
4. **실시간 스트리밍**: Server-Sent Events로 각 프로세스 독립 처리
5. **캐시 시스템**: Redis + SQLite 하이브리드 캐싱

## 📁 전체 소스 코드 구조

```
📁 RAG-QA-SYSTEM/
├── 🚀 메인 애플리케이션
│   ├── app.py                    # 메인 Flask 앱 + Swagger API
│   ├── config.py                 # 전역 설정 (API키, DB경로, LLM모델)
│   └── requirements.txt          # 패키지 의존성
│
├── 🛣 라우팅 레이어 (routes/)
│   ├── chat.py                   # 💬 채팅 API (통합 4개 모드)
│   ├── chat_local.py             # 🏠 로컬 LLM 전용 채팅
│   ├── unified_benchmark.py      # 📊 통합 벤치마킹 (스트리밍)
│   ├── multi_benchmark.py        # 🔄 멀티 프로세스 벤치마킹
│   ├── document.py               # 📄 문서 업로드/관리
│   ├── admin_restored.py         # ⚙️ 관리자 패널
│   └── settings.py               # 🔧 시스템 설정
│
├── 🧠 모델 레이어 (models/)
│   ├── llm.py                    # 🤖 LLM 통합 (OpenAI + Ollama)
│   ├── dual_llm.py               # 🔀 이중 LLM 비교 시스템
│   ├── embeddings.py             # 🔢 임베딩 관리 (OpenAI)
│   ├── vectorstore.py            # 🗄 벡터 DB (ChromaDB 이중)
│   └── dual_vectorstore.py       # 🔁 기본/커스텀 벡터 스토어
│
├── 🔧 서비스 레이어 (services/)
│   ├── rag_chain.py              # 🔗 RAG 체인 로직
│   ├── enhanced_rag_chain.py     # ⚡ 향상된 RAG 체인
│   ├── document_processor.py     # 📑 문서 파싱/전처리
│   ├── chunking_strategies.py    # ✂️ 청킹 전략 (기본/커스텀)
│   ├── hybrid_cache_manager.py   # 💾 하이브리드 캐시
│   └── benchmarking.py           # 📈 성능 측정
│
├── 🎨 프론트엔드 (templates/)
│   ├── main_rag_system.html      # 🖥 메인 UI (4개 카드 비교)
│   ├── enhanced_index.html       # 📊 관리자 대시보드
│   ├── unified_deotisrag.html    # 🔄 통합 벤치마킹 UI
│   └── benchmark.html            # 📈 성능 측정 UI
│
├── 💾 데이터 저장소 (data/)
│   ├── vectordb/                 # 🗄 ChromaDB 영구 저장소
│   ├── documents/                # 📁 업로드된 문서들
│   ├── cache/                    # 🔄 쿼리 캐시 (SQLite)
│   └── config/                   # ⚙️ 런타임 설정
│
└── 🔧 유틸리티
    ├── load_documents.py         # 📥 S3 문서 일괄 로드
    ├── debug_*.py               # 🐛 디버깅 스크립트들
    └── test_*.py                # 🧪 테스트 스크립트들
```

## 🌐 주요 API 엔드포인트

### 🎯 메인 채팅 API
- `POST /api/chat/stream` - 4개 프로세스 스트리밍 (현재 사용중)
- `POST /api/chat/chatgpt-basic` - ChatGPT + 기본청킹
- `POST /api/chat/chatgpt-custom` - ChatGPT + 커스텀청킹
- `POST /api/chat/local` - 로컬LLM (Ollama)

### 📊 벤치마킹 API
- `POST /api/unified-query` - 통합 벤치마킹
- `POST /api/multi-query` - 멀티 프로세스 벤치마킹

### 📄 문서 관리 API
- `POST /api/document/upload` - 파일 업로드
- `POST /api/document/load-s3` - S3 문서 일괄 로드
- `GET /api/document/list` - 문서 목록
- `DELETE /api/document/clear-all` - 전체 삭제

### ⚙️ 관리자 API
- `GET /api/admin/settings` - 시스템 설정 조회
- `POST /api/admin/settings` - 시스템 설정 변경
- `DELETE /api/admin/cache/clear-all` - 캐시 전체 삭제
- `DELETE /api/admin/vectordb/reset` - 벡터DB 리셋

### 🔍 시스템 정보
- `GET /api/rag/vectordb/info` - 벡터DB 상태
- `GET /health` - 헬스체크

## 🔄 Vector DB 임베딩 프로세스

### 🔄 임베딩 타이밍
- **사전 로드**: `python load_documents.py` 실행 시 (서버 시작 전)
- **실시간 업로드**: 관리자가 문서 업로드할 때 즉시 임베딩
- **저장 위치**: `./data/vectordb/` (영구 저장)

### 💎 커스텀 청킹
- **구분자**: `/$/` 사용
- **동작**: 문서에 `/$/`가 있으면 자동으로 커스텀 청킹 적용
- **fallback**: 구분자가 없으면 기본 청킹(1000자/200중첩) 적용

## 🏗 시스템 아키텍처 플로우

```
🌐 웹 UI → ⚡ Flask App → 🎯 요청 타입 분기
│
├── 📝 질의 처리
│   ├── 🔍 Dual Search (Basic + Custom Chunks)
│   ├── 🤖 ChatGPT API
│   ├── 🏠 Local LLM (Ollama)
│   └── 📋 Response Processing → 💾 Cache → 📊 Results
│
├── 📄 문서 업로드
│   ├── 📑 Document Processing
│   ├── 📐 Chunking (Basic/Custom)
│   ├── 🧠 OpenAI Embeddings
│   └── 🗄 ChromaDB 저장
│
└── ⚙️ 관리자 패널
    ├── 📈 System Monitoring
    ├── 🗑 Cache Management
    └── 📊 Analytics
```

## 🎭 비동기 UI 동작 순서

1. **검색어 입력** → 엔터/클릭
2. **즉시 4개 카드 영역 표시** (`loading` 클래스, 파란색 보더)
3. **로딩 스피너 애니메이션** (CSS 회전 + ⏳ 이모지)
4. **100ms 후 서버 요청 시작**
5. **각 결과 도착 순서대로**: `loading` → `success`(초록색) 또는 `error`(빨간색)

## 🎨 시각적 효과
- **로딩**: 파란색 보더 + 회전 스피너
- **성공**: 초록색 보더 + 연한 초록 배경
- **에러**: 빨간색 보더 + 연한 빨간 배경

## 📦 Dependencies (requirements.txt)

```
# Core Framework
flask==3.0.0
flask-cors==4.0.0
flask-restx==1.3.0

# LangChain & RAG
langchain==0.2.3
langchain-community==0.2.3
langchain-openai==0.1.8

# Vector Database
chromadb==0.5.0

# Embeddings
openai==1.30.5
sentence-transformers==2.2.2

# Document Processing
pypdf==4.2.0
python-docx==0.8.11

# Local LLM Support
ollama==0.1.8

# Utilities
redis==5.0.1
numpy==1.24.3
pandas==2.0.3
```

## 🚀 핵심 특징

### ✅ 완성된 시스템 특징
1. **4카드 비동기 UI**: 검색 시 즉시 로딩 영역 표시 → 완료 순서대로 결과 표시
2. **이중 벡터DB**: 기본청킹 vs 커스텀청킹(`/$/`) 비교
3. **하이브리드 LLM**: ChatGPT API + 로컬LLM(Ollama) 동시 비교
4. **실시간 스트리밍**: Server-Sent Events로 각 프로세스 독립 처리
5. **캐시 시스템**: Redis + SQLite 하이브리드 캐싱

### 📡 핵심 API
- `POST /api/chat/stream` - 메인 4개 프로세스 스트리밍
- `GET /swagger` - API 문서화
- `GET /enhanced` - 관리자 패널

---

**생성일**: 2024년 12월 19일  
**버전**: 1.0  
**시스템**: RAG QA System with Dual LLM Benchmarking