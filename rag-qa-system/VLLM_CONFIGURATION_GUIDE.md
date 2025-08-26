# vLLM 서버 연동 설정 가이드

## 📋 설정 완료된 변경사항

### 1. 🏠 로컬LLM + s3기본 시스템 변경사항

#### A. Yanolja LLM 모델 (`models/yanolja_llm.py`)
- **변경 전**: Ollama API (`http://192.168.0.224:11434/api/generate`)
- **변경 후**: vLLM OpenAI 호환 API (`http://192.168.0.224:8701/v1/chat/completions`)
- **모델명**: `yanolja/EEVE-Korean-Instruct-10.8B-v1.0`

#### B. 설정 파일 (`config.py`)
- **local LLM provider**: `ollama` → `vllm`
- **base_url**: `http://192.168.0.224:8701`
- **embedding**: 기본값을 `bge-m3`로 변경

### 2. 🔧 로컬LLM + s3-chunking 시스템 변경사항

#### A. Yanolja 특화 설정 (`yanolja_config.py`)
- **모든 모델 타입**을 vLLM 서버로 변경:
  - Travel AI
  - Hotel AI  
  - Customer Service AI
  - General AI
- **base_url 추가**: 각 모델에 `http://192.168.0.224:8701` 설정

### 3. 🎯 임베딩 모델 설정 (`models/embeddings.py`)
- **BGE-M3 기본 사용**: `USE_OLLAMA_BGE_M3=true` (기본값)
- **서버**: `http://192.168.0.224:11434` (Ollama 서버 사용)
- **모델**: `bge-m3:latest`
- **차원**: 1024

## 🚀 사용법

### 1. 환경 변수 설정
```bash
# .env.vllm 파일을 .env로 복사하여 사용
cp .env.vllm .env
```

### 2. 서버 확인
vLLM 서버가 실행 중인지 확인:
```bash
curl http://192.168.0.224:8701/v1/models
```

Ollama 서버 (임베딩용) 확인:
```bash
curl http://192.168.0.224:11434/api/tags
```

### 3. 시스템 실행
```bash
# 기본 시스템
python app.py

# Yanolja 특화 시스템  
python yanolja_app.py
```

## 📊 모델 정보

### LLM 모델
- **이름**: `yanolja/EEVE-Korean-Instruct-10.8B-v1.0`
- **서버**: vLLM (192.168.0.224:8701)
- **API**: OpenAI 호환 (`/v1/chat/completions`)

### 임베딩 모델  
- **이름**: `bge-m3:latest`
- **서버**: Ollama (192.168.0.224:11434)
- **API**: Ollama 임베딩 API (`/api/embeddings`)
- **차원**: 1024

## 🔧 주요 설정 파일들

| 파일 | 역할 | 변경 내용 |
|------|------|-----------|
| `models/yanolja_llm.py` | vLLM API 연동 | Ollama → vLLM API 변경 |
| `models/ollama_embeddings.py` | BGE-M3 임베딩 | IP 주소 업데이트 |
| `models/embeddings.py` | 임베딩 관리자 | BGE-M3 기본 사용 |
| `config.py` | 기본 설정 | vLLM provider 추가 |
| `yanolja_config.py` | Yanolja 특화 설정 | 모든 모델 vLLM 연동 |
| `.env.vllm` | 환경 변수 | vLLM 서버 설정 |

## 🔍 테스트 방법

### 1. LLM 연결 테스트
```python
from models.yanolja_llm import YanoljaLLM

llm = YanoljaLLM()
if llm.test_connection():
    print("✅ vLLM 연결 성공")
    response = llm.invoke("안녕하세요")
    print(f"응답: {response.content}")
```

### 2. 임베딩 연결 테스트
```python
from models.embeddings import EmbeddingManager

em = EmbeddingManager()
info = em.get_embedding_info()
print(f"임베딩 정보: {info}")

# 임베딩 테스트
embedding = em.embed_text("테스트 텍스트")
print(f"임베딩 차원: {len(embedding)}")
```

## ⚠️ 주의사항

1. **서버 순서**: vLLM 서버와 Ollama 서버 모두 실행되어야 함
2. **포트 분리**: 
   - vLLM: 8701 (LLM)
   - Ollama: 11434 (임베딩)
3. **모델 확인**: 각 서버에 필요한 모델이 로드되어 있는지 확인
4. **방화벽**: 192.168.0.224 서버의 포트가 열려있는지 확인

## 📝 적용된 위치

### 🏠 로컬LLM + s3기본
- `/03_DEOTIS_QA/rag-qa-system/` 디렉토리의 모든 관련 파일

### 🔧 로컬LLM + s3-chunking  
- 동일한 디렉토리에서 `yanolja_config.py` 기반 설정

모든 설정이 소스코드에서 변경 가능한 구조로 되어 있어, 필요시 환경변수나 설정 파일을 통해 쉽게 수정할 수 있습니다.