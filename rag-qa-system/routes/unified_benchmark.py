from flask import Blueprint, jsonify, request
from services.enhanced_rag_chain import EnhancedRAGChain
from services.chunking_strategies import get_chunking_strategy, benchmark_chunking_strategies
from models.vectorstore import get_vectorstore
from models.dual_llm import DualLLMManager
import time
import json
import os
from datetime import datetime

unified_bp = Blueprint('unified', __name__)

# 전역 인스턴스들
enhanced_rag_chain = None
similarity_cache = {}

def get_enhanced_rag_chain():
    """Enhanced RAG Chain 인스턴스 가져오기"""
    global enhanced_rag_chain
    if enhanced_rag_chain is None:
        vectorstore = get_vectorstore()
        enhanced_rag_chain = EnhancedRAGChain(vectorstore)
    return enhanced_rag_chain

@unified_bp.route('/unified-query', methods=['POST'])
def unified_query():
    """통합 벤치마킹 질의 처리"""
    try:
        data = request.json
        query = data.get('query', '').strip()
        mode = data.get('mode', '')
        summarize = data.get('summarize', False)
        
        if not query:
            return jsonify({'error': '질문을 입력해주세요.'}), 400
        
        if not mode:
            return jsonify({'error': '벤치마킹 모드를 선택해주세요.'}), 400
        
        # 유사도 검색 및 질문 처리 플로우
        result = process_query_with_similarity_check(query, mode, summarize)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': f'처리 중 오류 발생: {str(e)}'}), 500

def process_query_with_similarity_check(query, mode, summarize):
    """유사도 기준 질문 처리 플로우"""
    
    # 1. 질문 전처리 (LLM을 통한 질문 가공)
    processed_query = preprocess_question(query)
    
    # 2. 벡터 DB 유사도 검색
    rag_chain = get_enhanced_rag_chain()
    search_results = rag_chain._search_documents(processed_query, 5)
    
    if not search_results:
        return {
            'type': 'single',
            'answer': '관련 문서를 찾을 수 없습니다.',
            'response_time': 0,
            'model': mode
        }
    
    # 3. 유사도 분석 (Top 3 추출)
    top_3_results = search_results[:3]
    high_similarity_results = [
        (doc, score) for doc, score in top_3_results if score >= 0.8
    ]
    
    # 4. 유사도 기준 분기
    if high_similarity_results:
        # 0.8 이상인 경우 바로 답변 생성
        return generate_answer_for_mode(query, high_similarity_results, mode, summarize)
    else:
        # 0.8 미만인 경우 선택 옵션 제공
        global similarity_cache
        cache_key = f"{query}_{mode}_{int(time.time())}"
        similarity_cache[cache_key] = {
            'query': query,
            'results': top_3_results,
            'mode': mode,
            'summarize': summarize
        }
        
        options = []
        for i, (doc, score) in enumerate(top_3_results):
            options.append({
                'similarity': score,
                'preview': doc.page_content[:100],
                'index': i
            })
        
        return {
            'type': 'similarity_choice',
            'options': options,
            'cache_key': cache_key
        }

def preprocess_question(query):
    """LLM을 통한 질문 전처리"""
    try:
        rag_chain = get_enhanced_rag_chain()
        if rag_chain.dual_llm.get_available_models()['api']:
            api_chain = rag_chain.dual_llm.get_api_chain()
            
            prompt = f"""다음 질문을 벡터 검색에 최적화된 키워드와 문장으로 변환하세요.
            핵심 키워드를 중심으로 간결하게 재구성하세요.
            
            원본 질문: {query}
            
            최적화된 검색 쿼리:"""
            
            response = api_chain.invoke({"question": prompt, "context": ""})
            if hasattr(response, 'content'):
                return response.content.strip()
            else:
                return str(response).strip()
        else:
            return query
    except:
        return query

@unified_bp.route('/similarity-choice', methods=['POST'])
def similarity_choice():
    """유사도 선택 처리"""
    try:
        data = request.json
        choice = data.get('choice', 0)
        cache_key = data.get('cache_key', '')
        
        global similarity_cache
        if cache_key not in similarity_cache:
            return jsonify({'error': '선택 세션이 만료되었습니다.'}), 400
        
        cached_data = similarity_cache[cache_key]
        selected_result = [cached_data['results'][choice]]
        
        result = generate_answer_for_mode(
            cached_data['query'],
            selected_result,
            cached_data['mode'],
            cached_data['summarize']
        )
        
        # 캐시 정리
        del similarity_cache[cache_key]
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': f'처리 중 오류 발생: {str(e)}'}), 500

def generate_answer_for_mode(query, results, mode, summarize):
    """모드별 답변 생성"""
    
    start_time = time.time()
    
    # 모드 분석
    llm_type, chunking_type = mode.split('-')  # 예: 'chatgpt-basic'
    
    # 청킹 전략 적용 (커스텀인 경우)
    if chunking_type == 'custom':
        # 여기서 커스텀 청킹 로직 적용
        results = apply_custom_chunking(results)
    
    # LLM 선택 및 실행
    if llm_type == 'chatgpt':
        result = execute_chatgpt_query(query, results, summarize)
    else:  # local
        result = execute_local_query(query, results, summarize)
    
    # 벤치마킹 점수 계산
    benchmark_score = calculate_benchmark_score(result, time.time() - start_time)
    result['benchmark_score'] = benchmark_score
    result['mode'] = mode
    result['chunking_type'] = chunking_type
    
    # 조회 횟수 기록 (Redis/RDB 정책)
    record_query_usage(query, result)
    
    return {
        'type': 'single',
        **result
    }

def execute_chatgpt_query(query, results, summarize):
    """ChatGPT API로 질의 실행"""
    try:
        rag_chain = get_enhanced_rag_chain()
        api_chain = rag_chain.dual_llm.get_api_chain()
        
        context = rag_chain._format_context([doc for doc, score in results])
        
        # 요약 옵션에 따른 프롬프트 조정
        if summarize:
            system_prompt = """당신은 정확한 정보를 요약하여 제공하는 전문가입니다. 
                             주어진 문서를 기반으로 핵심 내용을 간결하게 요약하여 답변하세요."""
        else:
            system_prompt = """당신은 정확한 정보를 제공하는 전문가입니다. 
                             주어진 문서를 기반으로 상세하고 정확한 답변을 제공하세요."""
        
        start_time = time.time()
        response = api_chain.invoke({
            "question": query,
            "context": context
        })
        response_time = time.time() - start_time
        
        answer = response.content if hasattr(response, 'content') else str(response)
        
        return {
            'answer': answer,
            'response_time': response_time,
            'model': 'ChatGPT API',
            'estimated_tokens': len(answer.split()) * 1.3,
            'sources': [doc.metadata.get('source', 'Unknown') for doc, score in results],
            'success': True
        }
        
    except Exception as e:
        return {
            'answer': f'ChatGPT API 오류: {str(e)}',
            'response_time': 0,
            'model': 'ChatGPT API (Error)',
            'estimated_tokens': 0,
            'sources': [],
            'success': False
        }

def execute_local_query(query, results, summarize):
    """로컬 LLM으로 질의 실행"""
    try:
        rag_chain = get_enhanced_rag_chain()
        local_chain = rag_chain.dual_llm.get_local_chain()
        
        context = rag_chain._format_context([doc for doc, score in results])
        
        start_time = time.time()
        response = local_chain.invoke({
            "question": query,
            "context": context
        })
        response_time = time.time() - start_time
        
        answer = response.content if hasattr(response, 'content') else str(response)
        
        # 요약 처리 (로컬 LLM의 경우 후처리)
        if summarize:
            answer = summarize_answer(answer)
        
        return {
            'answer': answer,
            'response_time': response_time,
            'model': 'Local LLM (LLaMA)',
            'estimated_tokens': len(answer.split()) * 1.3,
            'sources': [doc.metadata.get('source', 'Unknown') for doc, score in results],
            'success': True
        }
        
    except Exception as e:
        return {
            'answer': f'로컬 LLM 오류: {str(e)}. Ollama가 실행 중인지 확인하세요.',
            'response_time': 0,
            'model': 'Local LLM (Error)',
            'estimated_tokens': 0,
            'sources': [],
            'success': False
        }

def apply_custom_chunking(results):
    """커스텀 청킹 적용 (사용자 구분자 기반)"""
    # 여기서는 기본적으로 문장 단위로 재분할
    # 실제로는 사용자가 지정한 구분자를 사용해야 함
    processed_results = []
    
    for doc, score in results:
        # 문장 단위로 재분할
        sentences = doc.page_content.split('.')
        for sentence in sentences:
            if len(sentence.strip()) > 50:  # 최소 길이 확인
                from langchain.schema import Document
                new_doc = Document(
                    page_content=sentence.strip(),
                    metadata=doc.metadata
                )
                processed_results.append((new_doc, score))
    
    return processed_results[:3]  # 상위 3개만 반환

def summarize_answer(answer):
    """답변 요약 (간단한 버전)"""
    # 실제로는 LLM을 다시 호출해서 요약해야 하지만,
    # 여기서는 간단히 첫 2문장만 반환
    sentences = answer.split('.')
    if len(sentences) >= 2:
        return '. '.join(sentences[:2]) + '.'
    return answer

def calculate_benchmark_score(result, processing_time):
    """벤치마킹 점수 계산"""
    if not result['success']:
        return 0.0
    
    # 점수 계산 요소들
    speed_score = max(0, 10 - processing_time)  # 빠를수록 높은 점수
    length_score = min(10, len(result['answer']) / 100)  # 적절한 길이
    token_efficiency = min(10, 1000 / (result['estimated_tokens'] + 1))
    
    total_score = (speed_score + length_score + token_efficiency) / 3
    return min(10.0, max(0.0, total_score))

def record_query_usage(query, result):
    """쿼리 사용 기록 (Redis/RDB 정책)"""
    try:
        # 간단한 파일 기반 기록 (실제로는 Redis/RDB 사용)
        usage_file = 'data/query_usage.json'
        os.makedirs(os.path.dirname(usage_file), exist_ok=True)
        
        if os.path.exists(usage_file):
            with open(usage_file, 'r', encoding='utf-8') as f:
                usage_data = json.load(f)
        else:
            usage_data = {}
        
        query_key = query.lower().strip()
        if query_key not in usage_data:
            usage_data[query_key] = {'count': 0, 'first_used': datetime.now().isoformat()}
        
        usage_data[query_key]['count'] += 1
        usage_data[query_key]['last_used'] = datetime.now().isoformat()
        
        with open(usage_file, 'w', encoding='utf-8') as f:
            json.dump(usage_data, f, indent=2, ensure_ascii=False)
            
    except Exception as e:
        print(f"사용 기록 저장 오류: {e}")