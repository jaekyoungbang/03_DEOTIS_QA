from langchain_openai import OpenAIEmbeddings
from config import Config

try:
    from langchain_community.embeddings import HuggingFaceEmbeddings
except ImportError:
    HuggingFaceEmbeddings = None

class EmbeddingManager:
    def __init__(self, embedding_type=None):
        self.embedding_type = embedding_type or Config.CURRENT_EMBEDDING
        self.embeddings = None
        self.initialize_embeddings()
    
    def initialize_embeddings(self):
        """Initialize embedding model based on configuration"""
        
        if self.embedding_type == 'openai':
            self._initialize_openai_embeddings()
        elif self.embedding_type == 'sentence-transformers':
            self._initialize_sentence_transformers()
        else:
            # 기본값으로 OpenAI 사용
            self._initialize_openai_embeddings()
    
    def _initialize_openai_embeddings(self):
        """OpenAI 임베딩 초기화"""
        if not Config.OPENAI_API_KEY:
            raise ValueError("OpenAI API key is required for OpenAI embeddings")
        
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
                import os
                os.environ["OPENAI_API_KEY"] = Config.OPENAI_API_KEY
                self.embeddings = OpenAIEmbeddings(
                    model=embedding_config['model_name']
                )
    
    def _initialize_sentence_transformers(self):
        """Sentence Transformers 임베딩 초기화"""
        if HuggingFaceEmbeddings is None:
            print("HuggingFace 임베딩을 사용할 수 없습니다. OpenAI 임베딩으로 대체합니다.")
            self._initialize_openai_embeddings()
            return
            
        try:
            embedding_config = Config.EMBEDDING_MODELS['sentence-transformers']
            self.embeddings = HuggingFaceEmbeddings(
                model_name=embedding_config['model_name']
            )
        except Exception as e:
            print(f"Sentence Transformers 초기화 실패: {e}")
            print("OpenAI 임베딩으로 대체합니다.")
            self._initialize_openai_embeddings()
    
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
        if self.embedding_type in Config.EMBEDDING_MODELS:
            config = Config.EMBEDDING_MODELS[self.embedding_type]
            return {
                'type': self.embedding_type,
                'model_name': config['model_name'],
                'dimension': config['dimension'],
                'status': 'ready' if self.embeddings else 'error'
            }
        return {
            'type': 'unknown',
            'status': 'error'
        }