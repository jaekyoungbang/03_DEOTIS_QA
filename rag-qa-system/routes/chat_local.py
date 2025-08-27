from flask import Blueprint, request, jsonify
from services.rag_chain import RAGChain
from models.vectorstore import get_vectorstore
from services.card_manager import process_user_card_query
import time
import os

chat_local_bp = Blueprint('chat_local', __name__)

# 전역 RAG 체인 인스턴스
rag_chain = None

def get_rag_chain():
    """RAG Chain 인스턴스 가져오기"""
    global rag_chain
    if rag_chain is None:
        rag_chain = RAGChain()
    return rag_chain

def load_user_profile(user_name):
    """사용자 개인정보 파일 로드"""
    try:
        # s3-chunking 폴더에서 사용자 정보 파일 찾기
        profile_path = os.path.join(os.path.dirname(__file__), '../../s3-chunking', f'{user_name}_개인정보.txt')
        if os.path.exists(profile_path):
            with open(profile_path, 'r', encoding='utf-8') as f:
                return f.read()
    except Exception as e:
        print(f"사용자 프로필 로드 오류: {e}")
    return None

def detect_user_and_enhance_query(question):
    """사용자 감지 및 쿼리 개선 (일반화된 버전)"""
    # 다양한 사용자명 패턴 감지
    user_patterns = ['김명정', '이영희', '박철수', '최영수']  # 확장 가능
    detected_user = None
    
    for user in user_patterns:
        if user in question:
            detected_user = user
            break
    
    if detected_user:
        print(f"🔍 {detected_user} 고객 감지 - 개인정보 연동 처리")
        
        # 카드 관련 질문인지 확인
        card_keywords = ['카드', '발급', '회원은행', '은행별']
        if any(keyword in question for keyword in card_keywords):
            print("💳 카드 관련 질의 감지 - 동적 카드 분류 처리")
            
            # BC카드 발급안내 MD 파일 경로
            md_file_path = '/mnt/d/99_DEOTIS_QA_SYSTEM/03_DEOTIS_QA/s3-chunking/BC카드(카드이용안내).md'
            
            try:
                # 동적으로 카드 정보 처리
                card_summary = process_user_card_query(detected_user, md_file_path)
                
                enhanced_query = f"""
질문: {question}

{card_summary}

위 {detected_user} 고객의 카드 현황을 바탕으로 맞춤형 답변을 제공해주세요.
보유 카드와 미보유 카드를 구분하여 이미지와 함께 안내해주세요.
"""
                return enhanced_query, True, card_summary
                
            except Exception as e:
                print(f"❌ 동적 카드 처리 오류: {e}")
                # 오류 시 기본 처리
                user_profile = load_user_profile(detected_user)
                if user_profile:
                    enhanced_query = f"""
질문: {question}

{detected_user} 고객 개인정보:
{user_profile}

위 고객 정보를 바탕으로 맞춤형 카드 발급 정보를 제공해주세요.
"""
                    return enhanced_query, True, None
    
    return question, False, None

@chat_local_bp.route('/local', methods=['POST'])
def chat_local():
    """로컬 LLM을 사용한 단일 질의 처리"""
    try:
        data = request.json
        question = data.get('question', '').strip()
        use_memory = data.get('use_memory', False)
        
        if not question:
            return jsonify({'error': '질문을 입력해주세요.'}), 400
        
        # 사용자 감지 및 쿼리 개선
        enhanced_question, is_personalized, card_summary = detect_user_and_enhance_query(question)
        
        start_time = time.time()
        
        # RAG Chain에서 로컬 LLM만 사용
        rag_chain = get_rag_chain()
        
        # 벤치마킹 모드를 비활성화하고 로컬 LLM만 사용하도록 설정
        rag_chain.use_benchmarking = False
        
        # 로컬 LLM 체인 가져오기
        try:
            local_chain = rag_chain.dual_llm.get_local_chain()
            
            # 관련 문서 검색 (원본 질문 또는 향상된 질문 사용)
            search_query = enhanced_question if is_personalized else question
            results = rag_chain._search_documents(search_query, 7)  # 개인화된 경우 더 많은 문서 검색
            
            if not results:
                return jsonify({
                    'answer': '관련 문서를 찾을 수 없습니다.',
                    'similarity_search': [],
                    'processing_time': time.time() - start_time,
                    'model_used': 'Local LLM',
                    'error': 'no_documents',
                    'is_personalized': is_personalized
                })
            
            # 컨텍스트 생성
            context = rag_chain._format_context([doc for doc, score in results])
            
            # 개인화된 경우 추가 컨텍스트 정보 제공
            if is_personalized:
                print("📝 개인화된 질의 처리 중...")
            
            # 로컬 LLM으로 답변 생성 (향상된 질문 사용)
            response = local_chain.invoke({
                "question": enhanced_question,
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
            
            response_data = {
                'answer': answer,
                'similarity_search': similarity_search,
                'processing_time': processing_time,
                'model_used': 'Local LLM (LLaMA)',
                'chunk_info': {
                    'chunk_size': 1000,
                    'chunk_overlap': 200,
                    'total_chunks': len(results)
                },
                'is_personalized': is_personalized
            }
            
            # 카드 요약 정보가 있으면 추가
            if card_summary:
                response_data['card_summary'] = card_summary
                response_data['dynamic_card_processing'] = True
                print("📋 동적 카드 정보가 응답에 포함됨")
            
            return jsonify(response_data)
            
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

@chat_local_bp.route('/custom', methods=['POST'])
def chat_custom():
    """s3-chunking 커스텀 검색을 사용한 질의 처리"""
    try:
        data = request.json
        question = data.get('question', '').strip()
        use_s3_chunking = data.get('use_s3_chunking', True)
        
        if not question:
            return jsonify({'error': '질문을 입력해주세요.'}), 400
        
        # 사용자 감지 및 쿼리 개선 (김명정 등)
        enhanced_question, is_personalized, card_summary = detect_user_and_enhance_query(question)
        
        start_time = time.time()
        
        # RAG Chain 가져오기
        rag_chain = get_rag_chain()
        
        # custom 컬렉션에서 검색하도록 설정
        rag_chain.use_benchmarking = False
        
        # 로컬 LLM 체인 가져오기
        try:
            local_chain = rag_chain.dual_llm.get_local_chain()
            
            # custom 컬렉션에서 문서 검색
            # s3-chunking 폴더의 문서를 사용
            search_query = enhanced_question if is_personalized else question
            results = rag_chain._search_documents(search_query, 7)  # 더 많은 문서 검색
            
            if not results:
                return jsonify({
                    'answer': '관련 문서를 찾을 수 없습니다.',
                    'similarity_search': [],
                    'processing_time': time.time() - start_time,
                    'model_used': 'Local LLM',
                    'error': 'no_documents',
                    'chunking_type': 'custom'
                })
            
            # 컨텍스트 생성
            context = rag_chain._format_context([doc for doc, score in results])
            
            # 개인화된 경우 로그
            if is_personalized:
                print(f"📝 개인화된 질의 처리 중... (s3-chunking)")
                print(f"🔍 향상된 쿼리 길이: {len(enhanced_question)}자")
            
            # 로컬 LLM으로 답변 생성 (향상된 질문 사용)
            response = local_chain.invoke({
                "question": enhanced_question,
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
            
            response_data = {
                'answer': answer,
                'similarity_search': similarity_search,
                'processing_time': processing_time,
                'model_used': 'Local LLM (s3-chunking)',
                'chunk_info': {
                    'chunk_size': 1500,
                    'chunk_overlap': 250,
                    'total_chunks': len(results)
                },
                'chunking_type': 'custom',
                'is_personalized': is_personalized
            }
            
            # 카드 요약 정보가 있으면 추가
            if card_summary:
                response_data['card_summary'] = card_summary
                response_data['dynamic_card_processing'] = True
                print("📋 동적 카드 정보가 응답에 포함됨 (s3-chunking)")
            
            return jsonify(response_data)
            
        except Exception as llm_error:
            return jsonify({
                'answer': f'로컬 LLM 오류: {str(llm_error)}',
                'similarity_search': [],
                'processing_time': time.time() - start_time,
                'model_used': 'Local LLM (Error)',
                'error': 'local_llm_error',
                'chunking_type': 'custom'
            })
        
    except Exception as e:
        return jsonify({
            'error': f'처리 중 오류 발생: {str(e)}',
            'processing_time': 0,
            'model_used': 'Error',
            'chunking_type': 'custom'
        }), 500