# RAG QA System 설치 및 실행 가이드

## 📋 개요

D:\99_DEOTIS_QA_SYSTEM\03_DEOTIS_QA\rag-qa-system 디렉토리에 위치한 RAG (Retrieval Augmented Generation) 기반 질의응답 시스템의 설치 및 실행 방법을 안내합니다.

## 📦 시스템 구성

- **웹 프레임워크**: Flask + Flask-RESTX (Swagger API)
- **LLM 통합**: LangChain + OpenAI API / 로컬 vLLM 서버
- **벡터 데이터베이스**: ChromaDB (문서 임베딩 저장)
- **문서 처리**: PDF, DOCX, TXT, MD 파일 지원
- **UI**: HTML/CSS/JavaScript + 실시간 스트리밍 채팅

## 🔧 사전 요구사항

### 1. Python 환경
```bash
Python 3.8 이상 필요
```

### 2. 시스템 패키지 (옵션)
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install default-jdk tesseract-ocr tesseract-ocr-kor redis-server

# CentOS/RHEL  
sudo yum install java-1.8.0-openjdk-devel tesseract-ocr redis

# Windows
# - Java JDK 설치: https://adoptopenjdk.net/
# - Tesseract OCR: https://github.com/tesseract-ocr/tesseract/wiki
# - Redis: https://redis.io/download
```

## 🚀 설치 과정

### 1단계: 가상환경 생성
```bash
# 프로젝트 디렉토리로 이동
cd D:\99_DEOTIS_QA_SYSTEM\03_DEOTIS_QA\rag-qa-system

# 가상환경 생성
python -m venv venv

# 가상환경 활성화
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 2단계: 필수 패키지 설치
```bash
# pip 업그레이드
pip install --upgrade pip wheel setuptools

# 핵심 웹 프레임워크
pip install flask==2.3.2 flask-cors==4.0.0 flask-restx==1.2.0

# LangChain 생태계
pip install langchain>=0.1.0 langchain-community>=0.0.38 langchain-core>=0.1.52
pip install langchain-openai==0.0.5

# LLM 제공자
pip install openai==1.8.0 ollama==0.1.7

# 벡터 데이터베이스
pip install chromadb==0.4.22

# 임베딩 모델
pip install sentence-transformers==2.2.2 transformers==4.36.2

# 문서 처리
pip install pypdf==3.17.4 python-docx==1.1.0 unstructured==0.11.6
pip install pytesseract==0.3.10 Pillow==10.1.0

# 유틸리티 라이브러리
pip install pydantic==2.5.3 python-dotenv==1.0.0
pip install numpy==1.24.3 pandas==2.1.4 tqdm==4.66.1
pip install requests aiofiles==23.2.1

# 캐싱 시스템
pip install redis==4.5.4

# 한국어 NLP (선택사항)
pip install konlpy==0.6.0 soynlp==0.0.493
```

### 3단계: PyTorch 설치 (임베딩 모델용)
```bash
# GPU 사용 가능한 경우 (CUDA 11.8)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# CPU만 사용하는 경우
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

### 4단계: 환경 변수 설정
```bash
# .env 파일 생성 (프로젝트 루트에)
# Windows에서는 메모장으로 생성
notepad .env

# Linux/Mac에서는
nano .env
```

**.env 파일 내용:**
```env
# OpenAI API 설정
OPENAI_API_KEY=your_openai_api_key_here

# 로컬 LLM 서버 (옵션)
VLLM_BASE_URL=http://192.168.0.224:8412
OLLAMA_BASE_URL=http://192.168.0.224:11434

# 벡터 데이터베이스 설정
CHROMA_PERSIST_DIRECTORY=./data/vectordb
CHROMA_COLLECTION_NAME=rag_documents

# 임베딩 모델 설정
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

# 기타 설정
FLASK_ENV=development
FLASK_DEBUG=True
```

### 5단계: 디렉토리 구조 확인
```
rag-qa-system/
├── app.py                 # 메인 Flask 애플리케이션
├── config.py              # 설정 파일
├── .env                   # 환경 변수 (새로 생성)
├── models/                # AI 모델 관련
├── services/              # 비즈니스 로직  
├── routes/                # API 라우트
├── templates/             # HTML 템플릿
├── static/                # 정적 파일
├── data/                  # 데이터 저장소
│   ├── documents/         # 업로드된 문서
│   ├── vectordb/          # 벡터 DB
│   └── cache/             # 캐시 데이터
├── s3/                    # 기본 문서 저장소
└── s3-chunking/           # 청킹된 문서 저장소
```

## ▶️ 실행 방법

### 1. 기본 실행
```bash
# 가상환경 활성화 상태에서
cd D:\99_DEOTIS_QA_SYSTEM\03_DEOTIS_QA\rag-qa-system
python app.py
```

### 2. 고급 실행 (포트 지정)
```bash
# 특정 포트로 실행
python app.py --port 5001

# 외부 접근 허용
python app.py --host 0.0.0.0 --port 5000
```

### 3. 실행 확인
- 웹 브라우저에서 `http://localhost:5000` 접속
- Swagger API 문서: `http://localhost:5000/swagger/`
- 메인 RAG 시스템: `http://localhost:5000/deotisrag`

## 📚 주요 API 엔드포인트

### 채팅 API
- `POST /api/chat/query` - 일반 질의응답
- `POST /api/chat/stream` - 실시간 스트리밍 응답
- `POST /api/chat/vllm-dual-stream` - 로컬 vLLM 듀얼 모드

### 문서 관리 API
- `POST /api/document/upload` - 파일 업로드
- `GET /api/document/list` - 문서 목록 조회
- `DELETE /api/document/clear-all` - 모든 문서 삭제

## 🔧 선택적 설정

### 1. Redis 캐시 서버 (권장)
```bash
# Redis 서버 시작
# Windows: redis-server.exe
# Linux: sudo systemctl start redis
# Mac: brew services start redis

# Redis 연결 테스트
redis-cli ping
```

### 2. 로컬 vLLM 서버 연동 (옵션)
```bash
# 사내 vLLM 서버가 192.168.0.224:8412에서 실행 중인 경우
# .env 파일에서 VLLM_BASE_URL 설정 확인
```

### 3. 한국어 NLP 도구 (옵션)
```bash
# KoNLPy 설치 후 사용 가능
# Java JDK 설치 필요
python -c "import konlpy; print('KoNLPy 설치 완료')"
```

## 🚨 문제 해결

### 1. ImportError 발생 시
```bash
# 패키지 재설치
pip uninstall langchain langchain-community chromadb
pip install langchain>=0.1.0 langchain-community>=0.0.38 chromadb==0.4.22
```

### 2. ChromaDB 오류 시
```bash
# 벡터 DB 초기화
rm -rf data/vectordb/*  # Linux/Mac
# Windows: data\vectordb 폴더 내용 삭제
```

### 3. OpenAI API 키 오류 시
```bash
# .env 파일 확인
echo $OPENAI_API_KEY  # Linux/Mac
echo %OPENAI_API_KEY%  # Windows
```

### 4. 포트 충돌 시
```bash
# 다른 포트로 실행
python app.py --port 5001
```

### 5. 로컬 LLM 연결 실패 시
- vLLM 서버 상태 확인: `http://192.168.0.224:8412`
- 네트워크 연결 확인
- .env 파일의 VLLM_BASE_URL 확인

## 📖 사용 가이드

### 1. 문서 업로드
1. 웹 인터페이스에서 "문서 업로드" 선택
2. PDF, DOCX, TXT, MD 파일 업로드
3. 벡터화 완료 후 질의응답 가능

### 2. 질의응답
1. 채팅 인터페이스에서 질문 입력
2. LLM 모델 선택 (GPT-4o-mini, 로컬 vLLM 등)
3. 실시간 스트리밍으로 답변 확인

### 3. API 사용
```bash
# curl로 API 테스트
curl -X POST http://localhost:5000/api/chat/query \
  -H "Content-Type: application/json" \
  -d '{"question": "BC카드 발급 방법을 알려주세요"}'
```

## 🔒 보안 고려사항

- OpenAI API 키는 .env 파일에 안전하게 보관
- .env 파일은 절대 Git에 커밋하지 말 것
- 프로덕션 환경에서는 FLASK_DEBUG=False 설정
- 방화벽에서 필요한 포트만 개방

## 📞 지원

문제 발생 시 다음을 확인하세요:
1. Python 버전 (3.8 이상)
2. 가상환경 활성화 상태
3. 필수 패키지 설치 완료
4. .env 파일 설정 정확성
5. 로그 파일 확인 (app.log)

---

**설치 완료 후 `http://localhost:5000`으로 접속하여 시스템을 이용하세요!**