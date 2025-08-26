from langchain_openai import OpenAIEmbeddings
from config import Config
import os

class EmbeddingManager:
    def __init__(self):
        self.embeddings = None
        self.initialize_embeddings()
    
    def initialize_embeddings(self):
        """Initialize embedding model based on configuration"""
        # Ollama BGE-M3 사용 활성화 (192.168.0.224:11434 서버 사용)
        use_ollama_bge_m3 = True
        
        if use_ollama_bge_m3:
            try:
                from models.ollama_embeddings import OllamaEmbeddings
                self.embeddings = OllamaEmbeddings(
                    model="bge-m3:latest",
                    base_url=os.getenv('OLLAMA_BASE_URL', 'http://192.168.0.224:11434')
                )
                # 연결 테스트
                if self.embeddings.test_connection():
                    print("✅ BGE-M3 임베딩 모델 사용 (192.168.0.224:11434)")
                    return
                else:
                    print("⚠️ BGE-M3 연결 실패, OpenAI로 폴백")
            except Exception as e:
                print(f"⚠️ BGE-M3 로드 실패, OpenAI로 폴백: {e}")
        
        if not Config.OPENAI_API_KEY:
            raise ValueError("OpenAI API key is required for embeddings")
        
        # OpenAI 임베딩만 사용 (안정성을 위해)
        embedding_config = Config.EMBEDDING_MODELS['openai']
        
        try:
            # Try new version format first
            self.embeddings = OpenAIEmbeddings(
                openai_api_key=Config.OPENAI_API_KEY,
                model=embedding_config['model_name']
            )
        except Exception as e:
            # Fallback to older version format
            try:
                self.embeddings = OpenAIEmbeddings(
                    api_key=Config.OPENAI_API_KEY,
                    model=embedding_config['model_name']
                )
            except Exception as e2:
                # Last resort - minimal parameters
                os.environ["OPENAI_API_KEY"] = Config.OPENAI_API_KEY
                self.embeddings = OpenAIEmbeddings(
                    model=embedding_config['model_name']
                )
    
    def get_embeddings(self):
        """Get the initialized embeddings instance"""
        if self.embeddings is None:
            self.initialize_embeddings()
        return self.embeddings
    
    def embed_text(self, text):
        """Embed a single text"""
        return self.embeddings.embed_query(text)
    
    def embed_documents(self, documents):
        """Embed multiple documents"""
        return self.embeddings.embed_documents(documents)
    
    def get_embedding_info(self):
        """임베딩 모델 정보 반환"""
        if hasattr(self.embeddings, 'model') and 'bge-m3' in self.embeddings.model:
            return {
                'type': 'bge-m3',
                'model_name': 'bge-m3:latest',
                'dimension': 1024,
                'server': '192.168.0.224:11434',
                'status': 'ready' if self.embeddings else 'error'
            }
        else:
            config = Config.EMBEDDING_MODELS['openai']
            return {
                'type': 'openai',
                'model_name': config['model_name'],
                'dimension': config['dimension'],
                'status': 'ready' if self.embeddings else 'error'
            }