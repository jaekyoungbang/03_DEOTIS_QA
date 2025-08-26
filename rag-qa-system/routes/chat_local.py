from flask import Blueprint, request, jsonify
from services.rag_chain import RAGChain
from models.vectorstore import get_vectorstore
import time

chat_local_bp = Blueprint('chat_local', __name__)

# 전역 RAG 체인 인스턴스
rag_chain = None

def get_rag_chain():
    """RAG Chain 인스턴스 가져오기"""
    global rag_chain
    if rag_chain is None:
        vectorstore = get_vectorstore()
        rag_chain = RAGChain(vectorstore)
    return rag_chain

@chat_local_bp.route('/local', methods=['POST'])
def chat_local():
    """로컬 LLM을 사용한 단일 질의 처리"""
    try:
        data = request.json
        question = data.get('question', '').strip()
        use_memory = data.get('use_memory', False)
        
        if not question:
            return jsonify({'error': '질문을 입력해주세요.'}), 400
        
        start_time = time.time()
        
        # RAG Chain에서 로컬 LLM만 사용
        rag_chain = get_rag_chain()
        
        # 벤치마킹 모드를 비활성화하고 로컬 LLM만 사용하도록 설정
        rag_chain.use_benchmarking = False
        
        # 로컬 LLM 체인 가져오기
        try:
            local_chain = rag_chain.dual_llm.get_local_chain()
            
            # 관련 문서 검색
            results = rag_chain._search_documents(question, 5)
            
            if not results:
                return jsonify({
                    'answer': '관련 문서를 찾을 수 없습니다.',
                    'similarity_search': [],
                    'processing_time': time.time() - start_time,
                    'model_used': 'Local LLM',
                    'error': 'no_documents'
                })
            
            # 컨텍스트 생성
            context = rag_chain._format_context([doc for doc, score in results])
            
            # 로컬 LLM으로 답변 생성
            response = local_chain.invoke({
                "question": question,
                "context": context
            })
            
            # 응답 텍스트 추출
            if hasattr(response, 'content'):
                answer = response.content
            else:
                answer = str(response)
            
            processing_time = time.time() - start_time
            
            # 유사도 검색 결과 포맷
            similarity_search = []
            for doc, score in results:
                similarity_search.append({
                    'content': doc.page_content[:200] + '...' if len(doc.page_content) > 200 else doc.page_content,
                    'score': float(score),
                    'metadata': doc.metadata
                })
            
            return jsonify({
                'answer': answer,
                'similarity_search': similarity_search,
                'processing_time': processing_time,
                'model_used': 'Local LLM (LLaMA)',
                'chunk_info': {
                    'chunk_size': 1000,
                    'chunk_overlap': 200,
                    'total_chunks': len(results)
                }
            })
            
        except Exception as llm_error:
            return jsonify({
                'answer': f'로컬 LLM을 사용할 수 없습니다. Ollama가 설치되고 실행 중인지 확인하세요. 오류: {str(llm_error)}',
                'similarity_search': [],
                'processing_time': time.time() - start_time,
                'model_used': 'Local LLM (Error)',
                'error': 'local_llm_unavailable'
            })
        
    except Exception as e:
        return jsonify({
            'error': f'처리 중 오류 발생: {str(e)}',
            'processing_time': 0,
            'model_used': 'Error'
        }), 500