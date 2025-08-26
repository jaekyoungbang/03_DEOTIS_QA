# RAG QA System

LangChain과 ChromaDB를 활용한 문서 기반 질의응답 시스템

## 기능

- 📄 다양한 문서 포맷 지원 (PDF, TXT, DOCX, Markdown)
- 🔍 벡터 검색 기반 관련 문서 검색
- 💬 대화형 QA 인터페이스
- 🧠 대화 기록 메모리 옵션
- 🎯 소스 문서 참조 표시

## 설치 방법

1. 가상환경 생성 및 활성화:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate  # Windows
```

2. 의존성 설치:
```bash
pip install -r requirements.txt
```

3. 환경 변수  설정:  
`.env` 파일을 편집하여 API 키 설정:
```
OPENAI_API_KEY=your_openai_api_key_here
```

## 실행 방법

```bash
python app.py
```

브라우저에서 `http://localhost:5000` 접속진행

## 사용 방법

1. **문서 업로드**: PDF, TXT, DOCX, MD 파일을 업로드하거나 텍스트 직접 입력
2. **질문하기**: 업로드한 문서와 관련된 질문 입력
3. **답변 확인**: AI가 문서를 기반으로 답변 생성

## API 엔드포인트

### Chat API
- `POST /api/chat/query` - 질문에 대한 답변 생성
- `POST /api/chat/stream` - 스트리밍 답변 (SSE)
- `POST /api/chat/clear-memory` - 대화 기록 초기화

### Document API
- `POST /api/document/upload` - 파일 업로드
- `POST /api/document/upload-text` - 텍스트 직접 입력
- `GET /api/document/list` - 문서 목록 조회
- `DELETE /api/document/delete/<filename>` - 특정 문서 삭제
- `DELETE /api/document/clear-all` - 모든 문서 삭제

## 프로젝트 구조

```
rag-qa-system/
├── app.py                 # Flask 메인 애플리케이션
├── config.py              # 설정 관리
├── models/                # AI 모델 관련
│   ├── llm.py            # LLM 관리
│   ├── embeddings.py     # 임베딩 모델
│   └── vectorstore.py    # 벡터 DB 관리
├── services/              # 비즈니스 로직
│   ├── rag_chain.py      # RAG 파이프라인
│   └── document_processor.py # 문서 처리
├── routes/                # API 라우트
│   ├── chat.py           # 채팅 API
│   └── document.py       # 문서 API
├── templates/             # HTML 템플릿
└── data/                  # 데이터 저장
    ├── documents/         # 업로드된 문서
    └── vectordb/          # 벡터 DB 저장소
```

## 주의사항

- OpenAI API 키가 필요합니다 (GPT 모델 사용 시)
- 대용량 파일은 처리 시간이 오래 걸릴 수 있습니다
- 벡터 DB는 로컬에 저장되며, 재시작 시에도 유지됩니다