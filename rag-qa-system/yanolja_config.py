import os
from dotenv import load_dotenv
from typing import Dict, Any

load_dotenv()

class YanoljaConfig:
    """야놀자 특화 설정 클래스"""
    
    # 야놀자 프로젝트 정보
    PROJECT_NAME = "YANOLJA_RAG_SYSTEM"
    COMPANY = "YANOLJA"
    VERSION = "1.0.0"
    
    # 기본 Flask 설정
    SECRET_KEY = os.getenv('SECRET_KEY', 'yanolja-secret-key-2024')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    PORT = int(os.getenv('FLASK_PORT', 5000))
    HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    
    # API 키 설정
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
    
    # vLLM + Ollama 설정
    VLLM_BASE_URL = os.getenv('VLLM_BASE_URL', 'http://192.168.0.224:8701')
    OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://192.168.0.224:11434')
    
    # 야놀자 LLM 모델 설정
    YANOLJA_MODELS = {
        'travel': {
            'model_name': os.getenv('YANOLJA_TRAVEL_MODEL', 'yanolja/EEVE-Korean-Instruct-10.8B-v1.0'),
            'display_name': '야놀자 여행 상담 AI (EEVE Korean)',
            'temperature': 0.7,
            'max_tokens': 2000,
            'base_url': 'http://192.168.0.224:8701',
            'system_prompt': """당신은 야놀자의 여행 전문 AI 어시스턴트입니다. 
                             한국의 여행지, 숙박, 맛집, 액티비티에 대한 정확하고 유용한 정보를 제공하세요.
                             야놀자 서비스와 연관된 추천을 우선적으로 고려하세요."""
        },
        'hotel': {
            'model_name': os.getenv('YANOLJA_HOTEL_MODEL', 'yanolja/EEVE-Korean-Instruct-10.8B-v1.0'),
            'display_name': '야놀자 숙박 추천 AI (EEVE Korean)',
            'temperature': 0.5,
            'max_tokens': 2000,
            'base_url': 'http://192.168.0.224:8701',
            'system_prompt': """당신은 야놀자의 숙박 전문 AI입니다. 
                             고객의 예산, 위치, 선호도에 맞는 최적의 숙박시설을 추천하세요.
                             야놀자 플랫폼의 숙박 상품을 우선 고려하세요."""
        },
        'customer_service': {
            'model_name': os.getenv('YANOLJA_CS_MODEL', 'yanolja/EEVE-Korean-Instruct-10.8B-v1.0'),
            'display_name': '야놀자 고객서비스 AI (EEVE Korean)',
            'temperature': 0.3,
            'max_tokens': 1500,
            'base_url': 'http://192.168.0.224:8701',
            'system_prompt': """당신은 야놀자 고객서비스 전문 AI입니다. 
                             친절하고 정확한 고객 응대를 제공하세요.
                             예약, 취소, 환불, 문의사항에 대해 정확한 안내를 해주세요."""
        },
        'general': {
            'model_name': os.getenv('YANOLJA_GENERAL_MODEL', 'yanolja/EEVE-Korean-Instruct-10.8B-v1.0'),
            'display_name': '야놀자 범용 AI (EEVE Korean)',
            'temperature': 0.6,
            'max_tokens': 1800,
            'base_url': 'http://192.168.0.224:8701',
            'system_prompt': """당신은 야놀자의 AI 어시스턴트입니다. 
                             여행과 숙박 관련 질문에 도움을 드리겠습니다."""
        }
    }
    
    # 벡터 DB 설정
    CHROMA_PERSIST_DIRECTORY = os.getenv('CHROMA_PERSIST_DIRECTORY', './data/vectordb')
    CHROMA_COLLECTION_NAME = os.getenv('CHROMA_COLLECTION_NAME', 'yanolja_documents')
    
    # 문서 처리 설정
    CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', 1000))
    CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', 200))
    MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 50485760))  # 50MB
    
    # 업로드 설정
    UPLOAD_FOLDER = './data/documents'
    ALLOWED_EXTENSIONS = {'pdf', 'txt', 'docx', 'md', 'hwp'}
    
    # 야놀자 비즈니스 로직 설정
    YANOLJA_SETTINGS = {
        'api_timeout': int(os.getenv('YANOLJA_API_TIMEOUT', 30)),
        'max_retries': int(os.getenv('YANOLJA_MAX_RETRIES', 3)),
        'cache_ttl': int(os.getenv('YANOLJA_CACHE_TTL', 3600)),
        'max_concurrent_requests': int(os.getenv('YANOLJA_MAX_CONCURRENT', 4)),
        'enable_streaming': os.getenv('YANOLJA_STREAMING', 'True').lower() == 'true'
    }
    
    # 로깅 설정
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', '/opt/yanolja/logs/yanolja-rag.log')
    
    @classmethod
    def get_model_config(cls, model_type: str = 'travel') -> Dict[str, Any]:
        """특정 모델 타입의 설정 반환"""
        return cls.YANOLJA_MODELS.get(model_type, cls.YANOLJA_MODELS['general'])
    
    @classmethod
    def get_all_models(cls) -> Dict[str, str]:
        """사용 가능한 모든 모델 목록 반환"""
        return {key: config['display_name'] for key, config in cls.YANOLJA_MODELS.items()}

# 기존 Config와 호환성 유지
Config = YanoljaConfig