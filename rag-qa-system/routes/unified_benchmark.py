from flask import Blueprint, jsonify, request
from services.enhanced_rag_chain import EnhancedRAGChain
from services.chunking_strategies import get_chunking_strategy, benchmark_chunking_strategies
from models.vectorstore import get_vectorstore, get_dual_vectorstore
from models.dual_llm import DualLLMManager
from config import Config
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
        dual_vectorstore = get_dual_vectorstore()
        enhanced_rag_chain = EnhancedRAGChain(dual_vectorstore)
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

def process_query_with_similarity_check(query, mode, summarize, local_model=None):
    """유사도 기준 질문 처리 플로우"""
    
    try:
        print(f"[UNIFIED] process_query_with_similarity_check 시작")
        print(f"[UNIFIED] 입력 파라미터 - mode: {mode}, query: '{query[:50]}...', summarize: {summarize}, local_model: {local_model}")
        
        # 1. 질문 전처리 (LLM을 통한 질문 가공)
        print(f"[UNIFIED] 1단계: 질문 전처리 시작")
        processed_query = preprocess_question(query)
        print(f"[UNIFIED] 1단계 완료: 전처리된 쿼리 '{processed_query[:50]}...'")
    
        # 2. 벡터 DB 유사도 검색 (모드별 청킹 타입 분리)
        print(f"[UNIFIED] 2단계: 벡터 DB 검색 시작")
        rag_chain = get_enhanced_rag_chain()
        print(f"[UNIFIED] EnhancedRAGChain 인스턴스 획득 완료")
        
        # 모드에 따른 청킹 타입 결정
        if 'basic' in mode:
            chunking_type = 'basic'
        elif 'custom' in mode:
            chunking_type = 'custom'
        else:
            chunking_type = None  # dual_search 사용
        
        print(f"[UNIFIED] 청킹 타입 결정: {chunking_type} (모드: {mode})")
        print(f"[UNIFIED] _search_documents 호출 시작: query='{processed_query}', k=5, chunking_type={chunking_type}")
        
        search_results = rag_chain._search_documents(processed_query, 5, chunking_type)
        
        print(f"[UNIFIED] 2단계 완료: 벡터 DB 검색 결과 {len(search_results) if search_results else 0}개")
        if search_results:
            for i, (doc, score) in enumerate(search_results[:3]):
                print(f"[UNIFIED] 검색결과 {i+1}: score={score:.3f}, 내용='{doc.page_content[:100]}...'")
        else:
            print(f"[UNIFIED] ⚠️ 검색 결과가 없습니다!")
        
        if not search_results:
            print(f"[UNIFIED] 검색 결과 없음")
            return {
                'type': 'single',
                'answer': '관련 문서를 찾을 수 없습니다.',
                'response_time': 0,
                'model': mode
            }
        
        # 3. 유사도 분석 및 중복 제거 (Top 3 추출)
        print(f"[UNIFIED] 3단계: 유사도 분석 시작")
        unique_results = []
        seen_content = set()
        
        for i, (doc, score) in enumerate(search_results[:5]):
            # 내용 기반 중복 체크 (첫 100자로 비교)
            content_key = doc.page_content[:100].strip()
            print(f"[UNIFIED] 검색결과 {i+1}: 점수={score:.3f}, 내용={content_key[:50]}...")
            if content_key not in seen_content:
                unique_results.append((doc, score))
                seen_content.add(content_key)
                print(f"[UNIFIED] → 고유 결과로 추가됨")
            else:
                print(f"[UNIFIED] → 중복으로 제외됨")
            
            # 최대 3개까지만
            if len(unique_results) >= 3:
                break
        
        top_3_results = unique_results
        high_similarity_results = [
            (doc, score) for doc, score in top_3_results if score >= 0.45
        ]
        print(f"[UNIFIED] 3단계 완료: 고유사도 결과 {len(high_similarity_results)}개 (0.45 이상)")
        print(f"[UNIFIED] 전체 유니크 결과: {len(top_3_results)}개")
        
        # 4. 유사도 기준 분기
        print(f"[UNIFIED] 4단계: 유사도 기준 분기 시작")
        if high_similarity_results:
            # 0.45 이상인 경우 바로 답변 생성
            print(f"[UNIFIED] 고유사도 경로: generate_answer_for_mode 호출")
            print(f"[UNIFIED] 답변 생성 파라미터: query='{query[:30]}...', results={len(high_similarity_results)}개, mode={mode}")
            
            result = generate_answer_for_mode(query, high_similarity_results, mode, summarize, local_model)
            
            print(f"[UNIFIED] 답변 생성 완료: type={result.get('type', 'unknown')}")
            return result
        else:
            # 0.45 미만인 경우 선택 옵션 제공
            print(f"[UNIFIED] 저유사도 경로: 선택 옵션 제공")
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
            
            print(f"[UNIFIED] 선택 옵션 생성 완료: {len(options)}개 옵션")
            return {
                'type': 'similarity_choice',
                'options': options,
                'cache_key': cache_key
            }
        
    except Exception as e:
        import traceback
        print(f"[UNIFIED ERROR] process_query_with_similarity_check 오류: {str(e)}")
        print(f"[UNIFIED ERROR] 트레이스백:")
        traceback.print_exc()
        
        return {
            'type': 'single',
            'answer': f'질문 처리 중 오류가 발생했습니다: {str(e)}',
            'response_time': 0,
            'model': mode,
            'success': False,
            'error': str(e)
        }

def preprocess_question(query):
    """LLM을 통한 질문 전처리 - 간단한 키워드 추출만 수행"""
    try:
        # 원본 쿼리가 충분히 간단한 경우 그대로 사용
        if len(query) <= 30:
            print(f"[PREPROCESS] 원본 쿼리 사용: {query}")
            return query
            
        rag_chain = get_enhanced_rag_chain()
        if rag_chain.dual_llm.get_available_models()['api']:
            api_chain = rag_chain.dual_llm.get_api_chain()
            
            prompt = f"""다음 질문에서 핵심 키워드만 추출하여 5단어 이내로 간결하게 답변하세요.
            
            원본 질문: {query}
            
            키워드:"""
            
            response = api_chain.invoke({"question": prompt, "context": ""})
            processed = ""
            if hasattr(response, 'content'):
                processed = response.content.strip()
            else:
                processed = str(response).strip()
            
            # 응답이 너무 길면 원본 쿼리 사용
            if len(processed) > 50:
                print(f"[PREPROCESS] 전처리 결과가 너무 길어서 원본 사용: {query}")
                return query
            
            # 빈 응답이면 원본 쿼리 사용
            if not processed:
                print(f"[PREPROCESS] 전처리 결과가 비어서 원본 사용: {query}")
                return query
                
            print(f"[PREPROCESS] 키워드 추출: '{query}' → '{processed}'")
            return processed
        else:
            print(f"[PREPROCESS] API 없어서 원본 사용: {query}")
            return query
    except Exception as e:
        print(f"[PREPROCESS] 오류로 인해 원본 사용: {query}, 오류: {e}")
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

def generate_answer_for_mode(query, results, mode, summarize, local_model=None):
    """모드별 답변 생성"""
    
    start_time = time.time()
    print(f"[ANSWER_GEN] generate_answer_for_mode 시작")
    print(f"[ANSWER_GEN] 파라미터: query='{query[:30]}...', results={len(results)}개, mode={mode}, summarize={summarize}")
    
    # 모드 분석
    llm_type, chunking_type = mode.split('-')  # 예: 'chatgpt-basic'
    print(f"[ANSWER_GEN] 모드 분석: {mode} → LLM={llm_type}, 청킹={chunking_type}")
    
    # 유사도 점수 추출 (Top 3)
    similarity_scores = []
    for i, (doc, score) in enumerate(results[:3]):
        similarity_scores.append({
            'rank': i + 1,
            'score': round(score, 3),
            'content_preview': doc.page_content[:100] + '...' if doc.page_content else ''
        })
    print(f"[ANSWER_GEN] 유사도 점수 추출 완료: {len(similarity_scores)}개")
    
    # 청킹 전략 적용 (s3 vs s3-chunking 폴더 구분)
    print(f"[ANSWER_GEN] 청킹 전략 적용 시작")
    processed_results = results
    if chunking_type == 'custom':
        # s3-chunking 커스텀 청킹 적용
        print(f"[ANSWER_GEN] apply_s3_custom_chunking 호출")
        processed_results = apply_s3_custom_chunking(results)
        print(f"[ANSWER_GEN] s3-chunking 커스텀 청킹 적용: {len(results)} -> {len(processed_results)} 청크")
    else:
        # s3 기본 청킹 적용
        print(f"[ANSWER_GEN] apply_s3_basic_chunking 호출")
        processed_results = apply_s3_basic_chunking(results)
        print(f"[ANSWER_GEN] s3 기본 청킹 사용: {len(results)} -> {len(processed_results)} 청크")
    
    # LLM 선택 및 실행
    print(f"[ANSWER_GEN] LLM 실행 시작: {llm_type}")
    if llm_type == 'chatgpt':
        print(f"[ANSWER_GEN] execute_chatgpt_query 호출")
        result = execute_chatgpt_query(query, processed_results, summarize, chunking_type)
        print(f"[ANSWER_GEN] execute_chatgpt_query 완료")
    else:  # local
        print(f"[ANSWER_GEN] execute_local_query 호출")
        result = execute_local_query(query, processed_results, summarize, chunking_type, local_model)
        print(f"[ANSWER_GEN] execute_local_query 완료")
    
    # 벤치마킹 점수 계산
    benchmark_score = calculate_benchmark_score(result, time.time() - start_time)
    result['benchmark_score'] = benchmark_score
    result['mode'] = mode
    result['chunking_type'] = chunking_type
    result['chunks_used'] = len(processed_results)
    result['similarity_scores'] = similarity_scores
    result['timestamp'] = datetime.now().isoformat()
    
    # 조회 횟수 기록 (Redis/RDB 정책)
    record_query_usage(query, result)
    
    return {
        'type': 'single',
        **result
    }

def execute_chatgpt_query(query, results, summarize, chunking_type):
    """ChatGPT API로 질의 실행"""
    try:
        print(f"[CHATGPT] execute_chatgpt_query 시작")
        print(f"[CHATGPT] 파라미터: query='{query[:30]}...', results={len(results)}개, summarize={summarize}, chunking_type={chunking_type}")
        
        rag_chain = get_enhanced_rag_chain()
        print(f"[CHATGPT] EnhancedRAGChain 인스턴스 획득 완료")
        
        api_chain = rag_chain.dual_llm.get_api_chain()
        print(f"[CHATGPT] API 체인 획득 완료")
        
        context = rag_chain._format_context([doc for doc, score in results])
        print(f"[CHATGPT] 컨텍스트 포맷 완료: {len(context)} 글자")
        
        # 청킹 전략에 따른 프롬프트 조정
        chunking_info = ""
        if chunking_type == 'custom':
            chunking_info = " (커스텀 청킹 전략으로 처리된 문서 기반)"
        else:
            chunking_info = " (기본 청킹 전략으로 처리된 문서 기반)"
        
        print(f"[CHATGPT] 청킹 정보: {chunking_info}")
        
        # 개선된 프롬프트 - 체계적이고 정리된 답변 생성
        if summarize:
            system_prompt = f"""당신은 BC카드 업무처리 전문가입니다{chunking_info}.

주어진 문서를 기반으로 질문에 대해 다음과 같은 형식으로 간결하게 요약하여 답변하세요:

1. **핵심 절차나 내용을 단계별로 정리** (번호나 단계 사용)
2. **중요한 주의사항이나 추가 정보** 포함
3. **관련 조건이나 요구사항** 명시
4. 필요시 **표 형식**으로 정보 정리

답변은 명확하고 실무에 도움이 되도록 구성하세요."""
        else:
            system_prompt = f"""당신은 BC카드 업무처리 전문가입니다{chunking_info}.

주어진 문서를 기반으로 질문에 대해 다음과 같은 형식으로 체계적이고 상세한 답변을 제공하세요:

**답변 구조:**
1. **개요**: 질문에 대한 간단한 소개
2. **상세 절차**: 단계별로 번호를 매겨서 설명 (1), 2), 3)... 형식)
3. **중요 포인트**: 주의사항, 조건, 요구사항 등을 명시
4. **추가 안내**: 관련 정보나 참고사항
5. **표 형식**: 복잡한 정보는 표로 정리 (| 구분자 사용)

**작성 원칙:**
- 실무진이 바로 활용할 수 있도록 구체적으로 작성
- 단계별 절차는 명확한 순서로 제시
- 중요한 내용은 **굵게** 표시
- 참조 문서명을 언급하여 신뢰성 확보

답변은 전문적이면서도 이해하기 쉽게 작성하세요."""
        
        print(f"[LLM_LOG] 🤖 ChatGPT API 호출 시작: OpenAI GPT-4")
        start_time = time.time()
        response = api_chain.invoke({
            "question": query,
            "context": context
        })
        response_time = time.time() - start_time
        print(f"[LLM_LOG] ✅ ChatGPT API 응답 완료: {response_time:.2f}초, {len(str(response))}자")
        
        answer = response.content if hasattr(response, 'content') else str(response)
        print(f"[CHATGPT] 응답 처리 완료: {len(answer)} 글자")
        
        result = {
            'answer': answer,
            'response_time': response_time,
            'model': f'ChatGPT API ({chunking_type} 청킹)',
            'estimated_tokens': len(answer.split()) * 1.3,
            'sources': [doc.metadata.get('source', 'Unknown') for doc, score in results],
            'success': True
        }
        
        print(f"[CHATGPT] 결과 생성 완료: success={result['success']}")
        return result
        
    except Exception as e:
        # 상세 오류 로깅
        import traceback
        print(f"[ChatGPT ERROR] 상세 오류: {str(e)}")
        print(f"[ChatGPT ERROR] 트레이스백: {traceback.format_exc()}")
        
        # 오류 원인 분석
        error_reason = 'unknown_error'
        error_detail = str(e)
        
        if 'api key' in str(e).lower() or 'unauthorized' in str(e).lower():
            error_reason = 'api_key_error'
            error_detail = 'ChatGPT API 키가 설정되지 않았거나 잘못되었습니다. .env 파일의 OPENAI_API_KEY를 확인하세요.'
        elif 'rate limit' in str(e).lower():
            error_reason = 'rate_limit'
            error_detail = 'API 요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요.'
        elif 'timeout' in str(e).lower():
            error_reason = 'timeout'
            error_detail = '응답 시간이 초과되었습니다. 네트워크 상태를 확인하세요.'
        
        return {
            'answer': f'ChatGPT API 오류: {error_detail}',
            'response_time': 0,
            'model': f'ChatGPT API (Error - {chunking_type} 청킹)',
            'estimated_tokens': 0,
            'sources': [],
            'success': False,
            'error_reason': error_reason,
            'error_detail': str(e),
            'timestamp': datetime.now().isoformat()
        }

def execute_local_query(query, results, summarize, chunking_type, local_model=None):
    """로컬 LLM으로 질의 실행"""
    try:
        print(f"[LOCAL] execute_local_query 시작")
        print(f"[LOCAL] 파라미터: query='{query[:30]}...', results={len(results)}개, chunking_type={chunking_type}, local_model={local_model}")
        
        rag_chain = get_enhanced_rag_chain()
        print(f"[LOCAL] EnhancedRAGChain 인스턴스 획득 완료")
        
        local_chain = rag_chain.dual_llm.get_local_chain(local_model)
        print(f"[LOCAL] 로컬 체인 획득 완료")
        
        context = rag_chain._format_context([doc for doc, score in results])
        print(f"[LOCAL] 컨텍스트 포맷 완료: {len(context)} 글자")
        
        start_time = time.time()
        print(f"[LOCAL] 로컬 LLM 호출 시작 (60초 타임아웃)")
        
        # 60초 타임아웃으로 로컬 LLM 호출 (Windows 호환)
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
        
        # 로컬 모델명 설정
        selected_model = local_model if local_model else Config.LLM_MODELS['local']['model_name']
        local_config = Config.LLM_MODELS['local']
        
        def call_local_llm():
            print(f"[LLM_LOG] 🏠 사내서버 vLLM 호출 시작: {selected_model}@{local_config['base_url']}")
            result = local_chain.invoke({
                "question": query,
                "context": context
            })
            print(f"[LLM_LOG] ✅ 사내서버 vLLM 응답 완료: {len(str(result))}자")
            print(f"[LOCAL] call_local_llm 함수 내부: LLM 응답 받음")
            return result
        
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(call_local_llm)
                print(f"[LOCAL] ThreadPoolExecutor 실행 중...")
                response = future.result(timeout=60)  # 60초 타임아웃
                print(f"[LOCAL] ThreadPoolExecutor 완료")
                
            response_time = time.time() - start_time
            print(f"[LOCAL] 로컬 LLM 호출 완료: {response_time:.2f}초")
            
        except FutureTimeoutError:
            response_time = time.time() - start_time
            print(f"[LOCAL] 타임아웃 발생: {response_time:.2f}초")
            raise TimeoutError(f"로컬 LLM 응답 시간 초과 (60초): kanana8b 모델이 응답하지 않습니다")
        except Exception as e:
            response_time = time.time() - start_time
            print(f"[LOCAL] 예외 발생: {str(e)} ({response_time:.2f}초)")
            raise e
        
        answer = response.content if hasattr(response, 'content') else str(response)
        print(f"[LOCAL] 응답 처리 완료: {len(answer)} 글자")
        
        # 요약 처리 (로컬 LLM의 경우 후처리)
        if summarize:
            print(f"[LOCAL] 요약 처리 시작")
            answer = summarize_answer(answer)
            print(f"[LOCAL] 요약 처리 완료")
        
        result = {
            'answer': answer,
            'response_time': response_time,
            'model': f'Local LLM ({chunking_type} 청킹)',
            'estimated_tokens': len(answer.split()) * 1.3,
            'sources': [doc.metadata.get('source', 'Unknown') for doc, score in results],
            'success': True
        }
        
        print(f"[LOCAL] 결과 생성 완료: success={result['success']}")
        return result
        
    except Exception as e:
        # 오류 원인 분석
        error_reason = 'unknown_error'
        error_detail = str(e)
        
        if 'connection' in str(e).lower() or 'refused' in str(e).lower() or 'reach' in str(e).lower():
            error_reason = 'vllm_connection_failed'
            error_detail = 'vLLM 서버(192.168.0.224:8412)에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.'
        elif 'model' in str(e).lower() and 'not found' in str(e).lower():
            error_reason = 'model_not_found'
            error_detail = './models/kanana8b 모델을 찾을 수 없습니다. vLLM 서버에서 모델이 로드되었는지 확인하세요.'
        elif 'timeout' in str(e).lower() or '60초' in str(e):
            error_reason = 'timeout'
            error_detail = '로컬 LLM 응답 시간이 60초를 초과했습니다. kanana8b 모델이 응답하지 않거나 처리 시간이 너무 깁니다.'
        
        return {
            'answer': f'사내서버 vLLM 사용 불가: {error_detail}',
            'response_time': 0,
            'model': f'Local LLM (Error - {chunking_type} 청킹)',
            'estimated_tokens': 0,
            'sources': [],
            'success': False,
            'error_reason': error_reason,
            'error_detail': str(e),
            'timestamp': datetime.now().isoformat()
        }

def apply_s3_basic_chunking(results):
    """s3 폴더 기반 기본 청킹 전략"""
    from services.chunking_strategies import get_chunking_strategy
    
    try:
        s3_basic_strategy = get_chunking_strategy('s3-basic')
        processed_results = []
        
        print(f"[START] s3 기본 청킹 전략 시작: {len(results)}개 문서")
        
        for doc, score in results:
            try:
                basic_chunks = s3_basic_strategy.split_documents([doc])
                
                for chunk in basic_chunks:
                    processed_results.append((chunk, score))
                    print(f"[OK] s3 기본 청크: {len(chunk.page_content)}자, 점수: {score:.3f}")
            
            except Exception as chunk_error:
                print(f"[WARNING] s3 기본 청킹 실패: {str(chunk_error)}")
                processed_results.append((doc, score * 0.9))
        
        processed_results.sort(key=lambda x: x[1], reverse=True)
        return processed_results[:5]
        
    except Exception as e:
        print(f"[ERROR] s3 기본 청킹 오류: {str(e)}")
        return results[:3]

def apply_s3_custom_chunking(results):
    """s3-chunking 폴더 기반 커스텀 청킹 전략"""
    from services.chunking_strategies import get_chunking_strategy
    
    try:
        s3_custom_strategy = get_chunking_strategy('s3-custom')
        processed_results = []
        
        print(f"[START] s3-chunking 커스텀 청킹 시작: {len(results)}개 문서")
        
        for doc, score in results:
            try:
                enhanced_chunks = s3_custom_strategy.split_documents([doc])
                
                for enhanced_chunk in enhanced_chunks:
                    # 전랩 지식 향상 여부에 따라 점수 조정
                    if enhanced_chunk.metadata.get('enhanced_with_s3'):
                        adjusted_score = score * 1.02  # 향상된 청크는 점수 상승
                        chunk_info = "s3-chunking 향상"
                    else:
                        adjusted_score = score * 0.98
                        chunk_info = "s3-chunking 기본"
                    
                    processed_results.append((enhanced_chunk, adjusted_score))
                    print(f"[OK] {chunk_info}: {len(enhanced_chunk.page_content)}자, 점수: {adjusted_score:.3f}")
            
            except Exception as chunk_error:
                print(f"[WARNING] s3-chunking 청킹 실패: {str(chunk_error)}")
                processed_results.append((doc, score * 0.9))
        
        processed_results.sort(key=lambda x: x[1], reverse=True)
        final_results = processed_results[:5]
        
        print(f"[COMPLETE] s3-chunking 커스텀 완료: {len(final_results)}개 청크")
        return final_results
        
    except Exception as e:
        print(f"[ERROR] s3-chunking 오류: {str(e)}")
        return results[:3]

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