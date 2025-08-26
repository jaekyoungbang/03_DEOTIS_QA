import os
from dotenv import load_dotenv
from typing import Dict, Any

load_dotenv()

class Config:
    # API Keys
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
    
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    PORT = int(os.getenv('FLASK_PORT', 5000))
    
    # Vector Database Configuration
    CHROMA_PERSIST_DIRECTORY = os.getenv('CHROMA_PERSIST_DIRECTORY', './data/vectordb')
    CHROMA_COLLECTION_NAME = os.getenv('CHROMA_COLLECTION_NAME', 'rag_documents')
    
    # Document Processing Configuration
    CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', 1000))
    CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', 200))
    MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 10485760))  # 10MB default
    
    # Upload Configuration
    UPLOAD_FOLDER = './data/documents'
    ALLOWED_EXTENSIONS = {'pdf', 'txt', 'docx', 'md'}
    
    # Benchmarking Mode - 두 개의 LLM 동시 비교
    BENCHMARKING_MODE = os.getenv('BENCHMARKING_MODE', 'True').lower() == 'true'
    
    # LLM Models Configuration for Benchmarking
    LLM_MODELS = {
        'api': {
            'provider': 'openai',
            'model_name': os.getenv('API_LLM_MODEL', 'gpt-4o-mini'),
            'temperature': 0.3,  # 창의성 약간 허용
            'max_tokens': 2000,
            'system_prompt': """당신은 BC카드 업무처리 전문가입니다. 

주어진 문서를 기반으로 다음과 같이 체계적이고 실용적인 답변을 제공하세요:

**답변 형식:**
1. **절차/과정이 있는 경우**: 단계별로 번호를 매겨서 명확하게 설명 (1), 2), 3)... 형식)
2. **조건/요건이 있는 경우**: 구체적인 조건과 예외사항 포함  
3. **복잡한 정보**: 가능한 한 표 형식으로 정리 (| 구분자 사용)
4. **중요사항**: **굵게** 표시하여 강조
5. **추가 안내**: 참고사항이나 관련 정보 포함

**작성 원칙:**
- 실무진이 바로 활용할 수 있도록 구체적으로 작성
- 단계별 절차는 명확한 순서로 제시
- 전문적이면서도 이해하기 쉽게 작성
- 주어진 문서에 없는 내용은 추측하지 않고, 문서 기반으로만 답변""",
            'display_name': 'ChatGPT API (gpt-4o-mini)'
        },
        'local': {
            'provider': 'vllm',
            'model_name': os.getenv('LOCAL_LLM_MODEL', './models/kanana8b'),
            'temperature': 0.3,
            'max_tokens': 2000,
            'system_prompt': """당신은 BC카드 업무처리 전문가입니다. 

주어진 문서를 기반으로 다음과 같이 체계적이고 실용적인 답변을 제공하세요:

**답변 형식:**
1. **절차/과정이 있는 경우**: 단계별로 번호를 매겨서 명확하게 설명 (1), 2), 3)... 형식)
2. **조건/요건이 있는 경우**: 구체적인 조건과 예외사항 포함  
3. **복잡한 정보**: 가능한 한 표 형식으로 정리 (| 구분자 사용)
4. **중요사항**: **굵게** 표시하여 강조
5. **추가 안내**: 참고사항이나 관련 정보 포함

**작성 원칙:**
- 실무진이 바로 활용할 수 있도록 구체적으로 작성
- 단계별 절차는 명확한 순서로 제시
- 전문적이면서도 이해하기 쉽게 작성
- 주어진 문서에 없는 내용은 추측하지 않고, 문서 기반으로만 답변""",
            'display_name': '로컬LLM (사내 vLLM 서버)',
            'base_url': os.getenv('VLLM_BASE_URL', 'http://192.168.0.224:8412')
        }
    }
    
    # Embedding Configuration
    EMBEDDING_MODELS = {
        'openai': {
            'model_name': 'text-embedding-3-small',
            'dimension': 1536
        },
        'sentence-transformers': {
            'model_name': 'sentence-transformers/all-MiniLM-L6-v2',
            'dimension': 384
        },
        'bge-m3': {
            'model_name': 'bge-m3:latest',
            'dimension': 1024,
            'base_url': os.getenv('OLLAMA_BASE_URL', 'http://192.168.0.224:11434')
        }
    }
    CURRENT_EMBEDDING = os.getenv('EMBEDDING_MODEL', 'bge-m3')
    
    # Chunking Strategies
    CHUNKING_STRATEGIES = {
        'basic': {
            'chunk_size': 1000,
            'chunk_overlap': 200,
            'separator': '\n',
            'description': '기본 청킹 전략 (문자 기반)'
        },
        'semantic': {
            'method': 'sentence_based',
            'min_chunk_size': 500,
            'max_chunk_size': 1500,
            'description': '의미 기반 청킹 전략'
        }
    }
    CURRENT_CHUNKING = os.getenv('CHUNKING_STRATEGY', 'basic')
    
    # System Information
    SYSTEM_INFO = {
        'python_version': '3.9+',
        'port': PORT,
        'benchmarking_mode': BENCHMARKING_MODE,
        'current_embedding': CURRENT_EMBEDDING,
        'current_chunking': CURRENT_CHUNKING
    }