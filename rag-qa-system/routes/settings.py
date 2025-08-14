from flask import Blueprint, request, jsonify
from services.document_processor import DocumentProcessor
from models.embeddings import EmbeddingManager
from models.vectorstore import VectorStoreManager
from config import Config
import json

settings_bp = Blueprint('settings', __name__)

class SystemSettings:
    def __init__(self):
        self.settings = {
            'chunk_size': Config.CHUNK_SIZE,
            'chunk_overlap': Config.CHUNK_OVERLAP,
            'embedding_model': Config.CURRENT_EMBEDDING,
            'llm_model': Config.LLM_MODELS['api']['model_name'],
            'llm_temperature': Config.LLM_MODELS['api']['temperature'],
            'max_tokens': Config.LLM_MODELS['api']['max_tokens']
        }
    
    def update_settings(self, new_settings):
        """설정 업데이트"""
        self.settings.update(new_settings)
        return self.settings
    
    def get_settings(self):
        """현재 설정 반환"""
        return self.settings

# Global settings instance
system_settings = SystemSettings()

@settings_bp.route('/get', methods=['GET'])
def get_settings():
    """현재 시스템 설정 조회"""
    try:
        settings = system_settings.get_settings()
        
        # 추가 정보
        embedding_manager = EmbeddingManager()
        vectorstore_manager = VectorStoreManager(embedding_manager.get_embeddings())
        
        settings['vector_db_info'] = {
            'total_documents': vectorstore_manager.get_document_count(),
            'db_type': 'ChromaDB'
        }
        
        return jsonify({
            'settings': settings,
            'status': 'success'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@settings_bp.route('/update', methods=['POST'])
def update_settings():
    """시스템 설정 업데이트"""
    try:
        data = request.get_json()
        
        # 유효한 설정들만 업데이트
        valid_settings = {
            'chunk_size': int,
            'chunk_overlap': int,
            'embedding_model': str,
            'llm_model': str,
            'llm_temperature': float,
            'max_tokens': int
        }
        
        new_settings = {}
        for key, value in data.items():
            if key in valid_settings:
                try:
                    # 타입 변환
                    new_settings[key] = valid_settings[key](value)
                except (ValueError, TypeError):
                    return jsonify({'error': f'Invalid value for {key}'}), 400
        
        # 설정 업데이트
        updated_settings = system_settings.update_settings(new_settings)
        
        return jsonify({
            'message': 'Settings updated successfully',
            'settings': updated_settings,
            'status': 'success'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@settings_bp.route('/chunking/test', methods=['POST'])
def test_chunking():
    """청킹 설정 테스트"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        chunk_size = int(data.get('chunk_size', system_settings.settings['chunk_size']))
        chunk_overlap = int(data.get('chunk_overlap', system_settings.settings['chunk_overlap']))
        
        if not text:
            return jsonify({'error': 'Text is required for testing'}), 400
        
        # 임시 문서 프로세서로 테스트
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        from langchain.schema import Document
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # 문서 생성 및 분할
        doc = Document(page_content=text, metadata={"source": "test"})
        chunks = text_splitter.split_documents([doc])
        
        # 결과 반환
        chunk_info = []
        for i, chunk in enumerate(chunks):
            chunk_info.append({
                'index': i,
                'content': chunk.page_content[:200] + ('...' if len(chunk.page_content) > 200 else ''),
                'length': len(chunk.page_content)
            })
        
        return jsonify({
            'chunks': chunk_info,
            'total_chunks': len(chunks),
            'settings_used': {
                'chunk_size': chunk_size,
                'chunk_overlap': chunk_overlap
            },
            'status': 'success'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@settings_bp.route('/embedding/test', methods=['POST'])
def test_embedding():
    """임베딩 테스트"""
    try:
        data = request.get_json()
        texts = data.get('texts', [])
        
        if not texts or not isinstance(texts, list):
            return jsonify({'error': 'Texts array is required'}), 400
        
        # 임베딩 매니저로 테스트
        embedding_manager = EmbeddingManager()
        
        results = []
        for i, text in enumerate(texts[:5]):  # 최대 5개까지만 테스트
            try:
                embedding = embedding_manager.embed_text(text)
                results.append({
                    'index': i,
                    'text': text[:100] + ('...' if len(text) > 100 else ''),
                    'embedding_dimension': len(embedding),
                    'embedding_preview': embedding[:5]  # 처음 5개 값만 미리보기
                })
            except Exception as e:
                results.append({
                    'index': i,
                    'text': text[:100] + ('...' if len(text) > 100 else ''),
                    'error': str(e)
                })
        
        return jsonify({
            'results': results,
            'embedding_model': system_settings.settings['embedding_model'],
            'status': 'success'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500