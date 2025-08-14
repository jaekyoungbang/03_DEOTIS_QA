# RAG QA 시스템 실행 가이드

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 가상환경 생성
python -m venv venv_new

# 가상환경 활성화
# Windows:
venv_new\Scripts\activate
# Linux/Mac:
source venv_new/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 환경변수 설정

`.env` 파일 생성:
```bash
cp .env.example .env
```

`.env` 파일 편집:
```env
# OpenAI API 키 (필수)
OPENAI_API_KEY=your_openai_api_key_here

# 포트 설정
FLASK_PORT=5000

# 벤치마킹 모드 활성화
BENCHMARKING_MODE=True

# LLM 모델 설정
API_LLM_MODEL=gpt-3.5-turbo
LOCAL_LLM_MODEL=llama3.2

# Ollama 설정 (로컬 LLM 사용 시)
OLLAMA_BASE_URL=http://localhost:11434
```

### 3. 로컬 LLM 설정 (선택사항)

로컬 LLM 사용을 원한다면:

```bash
# Ollama 설치 (https://ollama.ai/)
# Windows/Mac: 공식 사이트에서 다운로드
# Linux:
curl -fsSL https://ollama.ai/install.sh | sh

# LLaMA 모델 다운로드
ollama pull llama3.2
```

### 4. 시스템 실행

```bash
python app.py
```

## 🎯 접속 방법

시스템이 실행되면 다음 주소로 접속:

- **벤치마킹 페이지**: http://localhost:5000/benchmark
- **일반 QA 페이지**: http://localhost:5000/deotisrag
- **API 문서**: http://localhost:5000/swagger/

## 📊 벤치마킹 모드 사용법

### 화면 구성
- **좌측**: API LLM (OpenAI GPT) 결과
- **우측**: 로컬 LLM (LLaMA) 결과
- **하단**: 성능 비교 결과

### 측정 항목
1. **응답 시간**: 각 LLM의 답변 생성 시간
2. **토큰 수**: 생성된 토큰 수 (추정)
3. **유사도**: 두 답변 간의 유사도
4. **승자**: 더 빠른 모델 표시

### 질문 예시
```
- "BC카드 발급 절차는 어떻게 되나요?"
- "연체 시 벌금은 얼마인가요?"
- "카드 분실 시 어떻게 해야 하나요?"
- "이용 한도는 어떻게 설정하나요?"
```

## ⚙️ 시스템 정보

### 현재 설정 확인
시스템 정보 섹션에서 확인 가능:
- Python 버전
- 포트 번호
- 임베딩 모델
- 청킹 전략
- LLM 모델 상태

### API 엔드포인트

#### 벤치마킹 API
- `POST /api/benchmark/query` - 듀얼 LLM 질의
- `GET /api/benchmark/system-info` - 시스템 정보
- `GET /api/benchmark/results` - 벤치마킹 결과 조회
- `DELETE /api/benchmark/clear-results` - 결과 초기화

#### 문서 관리 API
- `POST /api/document/upload` - 파일 업로드
- `GET /api/document/list` - 문서 목록
- `DELETE /api/document/clear-all` - 모든 문서 삭제

## 🔧 문제 해결

### 1. API LLM이 사용 불가한 경우
- OpenAI API 키가 올바른지 확인
- 계정에 충분한 크레딧이 있는지 확인

### 2. 로컬 LLM이 사용 불가한 경우
- Ollama가 설치되고 실행 중인지 확인:
  ```bash
  ollama list  # 설치된 모델 확인
  ollama serve  # Ollama 서버 실행
  ```

### 3. 문서가 로드되지 않은 경우
- `/deotisrag` 페이지에서 관리자 로그인 (비밀번호: Kbfcc!23)
- S3에서 문서 로드 버튼 클릭

### 4. 포트 충돌 문제
```bash
# 다른 포트 사용
export FLASK_PORT=5001
python app.py
```

## 📈 성능 최적화

### 청킹 전략 변경
`.env` 파일에서:
```env
CHUNKING_STRATEGY=basic    # 기본 (빠름)
CHUNKING_STRATEGY=semantic # 의미 기반 (정확함)
CHUNKING_STRATEGY=hybrid   # 하이브리드 (균형)
```

### 임베딩 모델 변경
```env
EMBEDDING_MODEL=openai              # OpenAI (정확함)
EMBEDDING_MODEL=sentence-transformers # 로컬 (빠름)
```

## 🎯 벤치마킹 결과 해석

### 속도 비교
- **API LLM**: 일반적으로 안정적인 속도
- **로컬 LLM**: 하드웨어에 따라 차이

### 답변 품질
- **유사도 70% 이상**: 두 모델이 비슷한 답변
- **유사도 50% 미만**: 다른 관점의 답변

### 최적 모델 선택
- **정확성 우선**: API LLM 사용
- **비용 절약**: 로컬 LLM 사용
- **하이브리드**: 상황에 따라 선택

## 📝 추가 기능

### 다중 답변 시스템
유사도가 비슷한 여러 답변이 있을 때:
- 상위 3개 답변 표시
- 각 답변의 유사도 점수 표시
- 사용자가 원하는 답변 선택 가능

### 자연어 질문 처리
시스템이 처리 가능한 질문 유형:
- 사실 질문: "BC카드 수수료는 얼마인가요?"
- 절차 질문: "카드 발급은 어떻게 하나요?"
- 비교 질문: "신용카드와 체크카드의 차이점은?"

Redis 없이도 완전히 동작하며, 파일 기반 캐싱을 사용합니다.