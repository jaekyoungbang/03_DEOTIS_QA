from langchain_openai import OpenAIEmbeddings
from config import Config

class EmbeddingManager:
    def __init__(self):
        self.embeddings = None
        self.initialize_embeddings()
    
    def initialize_embeddings(self):
        """Initialize embedding model based on configuration"""
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
                import os
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
        config = Config.EMBEDDING_MODELS['openai']
        return {
            'type': 'openai',
            'model_name': config['model_name'],
            'dimension': config['dimension'],
            'status': 'ready' if self.embeddings else 'error'
        }