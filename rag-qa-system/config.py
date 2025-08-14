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
            'model_name': os.getenv('API_LLM_MODEL', 'gpt-3.5-turbo'),
            'temperature': 0,  # 창의성 0으로 고정
            'max_tokens': 2000,
            'system_prompt': """당신은 정확한 정보를 제공하는 전문가입니다. 
                             주어진 문서를 기반으로만 답변하고, 추측하지 마세요.""",
            'display_name': 'OpenAI GPT-3.5'
        },
        'local': {
            'provider': 'ollama',
            'model_name': os.getenv('LOCAL_LLM_MODEL', 'llama3.2'),
            'temperature': 0,
            'max_tokens': 2000,
            'system_prompt': """You are a helpful assistant that provides accurate information 
                             based on the given documents. Do not make assumptions.""",
            'display_name': 'Local LLaMA 3.2',
            'base_url': os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
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
        }
    }
    CURRENT_EMBEDDING = os.getenv('EMBEDDING_MODEL', 'openai')
    
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