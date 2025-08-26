from flask import Blueprint, jsonify, request
from services.enhanced_rag_chain import EnhancedRAGChain
from models.vectorstore import get_vectorstore, get_dual_vectorstore
from routes.unified_benchmark import process_query_with_similarity_check
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from flask import Response
import json

multi_benchmark_bp = Blueprint('multi_benchmark', __name__)

# 전역 인스턴스들
enhanced_rag_chain = None
executor = ThreadPoolExecutor(max_workers=4)

def get_enhanced_rag_chain():
    """Enhanced RAG Chain 인스턴스 가져오기"""
    global enhanced_rag_chain
    if enhanced_rag_chain is None:
        dual_vectorstore = get_dual_vectorstore()
        enhanced_rag_chain = EnhancedRAGChain(dual_vectorstore)
    return enhanced_rag_chain

@multi_benchmark_bp.route('/multi-query-stream', methods=['POST'])
def multi_benchmark_query_stream():
    """실시간 스트리밍 멀티 벤치마킹 - Phase 1,2 병렬 실행"""
    
    print(f"[STREAM] 🎯 multi_benchmark_query_stream 엔드포인트 호출됨")
    print(f"[STREAM] Request method: {request.method}")
    print(f"[STREAM] Request headers: {dict(request.headers)}")
    
    # 스트리밍 밖에서 request 데이터를 먼저 가져오기
    try:
        data = request.get_json()
        print(f"[STREAM] 요청 데이터 파싱 완료: {data}")
        
        query = data.get('query', '').strip()
        summarize = data.get('summarize', False) 
        local_model = data.get('local_model', './models/kanana8b')
        
        print(f"[STREAM] 파라미터 추출: query='{query[:50]}...', summarize={summarize}, local_model={local_model}")
        
    except Exception as json_error:
        print(f"[STREAM] ❌ JSON 파싱 오류: {json_error}")
        return Response(f"data: {json.dumps({'type': 'error', 'message': f'JSON 파싱 오류: {str(json_error)}'})}\n\n", 
                       mimetype='text/event-stream')
    
    def generate_stream():
        try:
            print(f"[STREAM] 🚀 generate_stream 시작")
            
            if not query:
                print(f"[STREAM] ❌ 질문이 비어있음")
                yield f"data: {json.dumps({'type': 'error', 'message': '질문을 입력해주세요.'})}\n\n"
                return
            
            
            # 사용 가능한 모드 확인
            print(f"[STREAM] 🔍 모델 가용성 확인 시작")
            try:
                from models.dual_llm import DualLLMManager
                from config import Config
                
                print(f"[STREAM] DualLLMManager 생성 중...")
                dual_llm = DualLLMManager()
                print(f"[STREAM] get_available_models 호출...")
                available_models = dual_llm.get_available_models()
                print(f"[STREAM] 모델 가용성: {available_models}")
                
                yield f"data: {json.dumps({'type': 'models_check', 'available': available_models})}\n\n"
                
            except Exception as e:
                print(f"[STREAM] ❌ 모델 확인 오류: {str(e)}")
                available_models = {'api': True, 'local': False}
                yield f"data: {json.dumps({'type': 'models_error', 'error': str(e)})}\n\n"
            
            # Phase 1 모드 설정
            phase1_modes = []
            if available_models.get('local'):
                phase1_modes.append('local-basic')
            if available_models.get('api'):
                phase1_modes.append('chatgpt-basic')
            
            # Phase 2 모드 설정
            phase2_modes = []
            if available_models.get('local'):
                phase2_modes.append('local-custom')
            if available_models.get('api'):
                phase2_modes.append('chatgpt-custom')
            
            yield f"data: {json.dumps({'type': 'phase_info', 'phase1': phase1_modes, 'phase2': phase2_modes})}\n\n"
            
            # === PHASE 1: 병렬 실행 (local-basic + chatgpt-basic) ===
            yield f"data: {json.dumps({'type': 'phase_start', 'phase': 1, 'modes': phase1_modes})}\n\n"
            
            with ThreadPoolExecutor(max_workers=2) as executor:
                # Phase 1 병렬 실행
                phase1_futures = {}
                for mode in phase1_modes:
                    if mode.startswith('local') and available_models.get('local'):
                        future = executor.submit(execute_single_mode, mode, query, summarize, local_model, "PHASE1")
                        phase1_futures[future] = mode
                    elif mode.startswith('chatgpt') and available_models.get('api'):
                        future = executor.submit(execute_single_mode, mode, query, summarize, local_model, "PHASE1")
                        phase1_futures[future] = mode
                
                # Phase 1 결과 실시간 전송
                for future in as_completed(phase1_futures):
                    mode = phase1_futures[future]
                    try:
                        result = future.result()
                        yield f"data: {json.dumps({'type': 'result', 'phase': 1, 'mode': mode, 'result': result})}\n\n"
                    except Exception as e:
                        error_result = create_error_result_stream(mode, str(e))
                        yield f"data: {json.dumps({'type': 'result', 'phase': 1, 'mode': mode, 'result': error_result})}\n\n"
            
            yield f"data: {json.dumps({'type': 'phase_complete', 'phase': 1})}\n\n"
            
            # === PHASE 2: 병렬 실행 (local-custom + chatgpt-custom) ===
            yield f"data: {json.dumps({'type': 'phase_start', 'phase': 2, 'modes': phase2_modes})}\n\n"
            
            with ThreadPoolExecutor(max_workers=2) as executor:
                # Phase 2 병렬 실행
                phase2_futures = {}
                for mode in phase2_modes:
                    if mode.startswith('local') and available_models.get('local'):
                        future = executor.submit(execute_single_mode, mode, query, summarize, local_model, "PHASE2")
                        phase2_futures[future] = mode
                    elif mode.startswith('chatgpt') and available_models.get('api'):
                        future = executor.submit(execute_single_mode, mode, query, summarize, local_model, "PHASE2")
                        phase2_futures[future] = mode
                
                # Phase 2 결과 실시간 전송
                for future in as_completed(phase2_futures):
                    mode = phase2_futures[future]
                    try:
                        result = future.result()
                        yield f"data: {json.dumps({'type': 'result', 'phase': 2, 'mode': mode, 'result': result})}\n\n"
                    except Exception as e:
                        error_result = create_error_result_stream(mode, str(e))
                        yield f"data: {json.dumps({'type': 'result', 'phase': 2, 'mode': mode, 'result': error_result})}\n\n"
            
            yield f"data: {json.dumps({'type': 'phase_complete', 'phase': 2})}\n\n"
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"
            
        except Exception as e:
            print(f"[STREAM] ❌ generate_stream 전체 오류: {str(e)}")
            import traceback
            print(f"[STREAM] 오류 트레이스:")
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return Response(generate_stream(), mimetype='text/event-stream',
                   headers={'Cache-Control': 'no-cache', 'Connection': 'keep-alive'})

def execute_single_mode(mode, query, summarize, local_model, phase_info):
    """단일 모드 실행 함수 (스트리밍용)"""
    try:
        start_time = time.time()
        print(f"[{phase_info}] {mode} 모드 시작 - 쿼리: '{query[:50]}...'")
        print(f"[{phase_info}] {mode} 매개변수: summarize={summarize}, local_model={local_model}")
        
        print(f"[{phase_info}] {mode} process_query_with_similarity_check 호출 시작")
        result = process_query_with_similarity_check(query, mode, summarize, local_model)
        print(f"[{phase_info}] {mode} process_query_with_similarity_check 완료")
        
        end_time = time.time()
        print(f"[{phase_info}] {mode} 모드 완료 ({end_time - start_time:.2f}초)")
        print(f"[{phase_info}] {mode} 결과 타입: {result.get('type', 'unknown')}")
        print(f"[{phase_info}] {mode} 결과 성공 여부: {result.get('success', 'unknown')}")
        
        if 'response_time' not in result:
            result['response_time'] = end_time - start_time
            
        return {
            'mode': mode,
            'result': result,
            'success': True,
            'processing_time': end_time - start_time
        }
    except Exception as e:
        print(f"[{phase_info}] {mode} 모드 오류: {str(e)}")
        import traceback
        print(f"[{phase_info}] {mode} 오류 트레이스:")
        traceback.print_exc()
        return {
            'mode': mode,
            'result': {
                'type': 'single',
                'answer': f'처리 중 오류 발생: {str(e)}',
                'response_time': 0,
                'model': mode,
                'success': False,
                'error_reason': 'processing_error',
                'timestamp': datetime.now().isoformat()
            },
            'success': False,
            'error': str(e)
        }

def create_error_result_stream(mode, error_msg):
    """스트리밍용 오류 결과 생성"""
    if mode.startswith('local'):
        error_detail = 'vLLM 서버 연결 오류'
    else:
        error_detail = 'ChatGPT API 오류'
    
    return {
        'mode': mode,
        'result': {
            'type': 'single',
            'answer': f'{error_detail}: {error_msg}',
            'response_time': 0,
            'model': mode,
            'success': False,
            'timestamp': datetime.now().isoformat()
        },
        'success': False,
        'error': error_msg
    }

@multi_benchmark_bp.route('/multi-query', methods=['POST'])
def multi_benchmark_query():
    """4가지 모드 순차적 벤치마킹 질의 처리 - Phase 1, 2로 분리하여 서버 과부하 방지"""
    try:
        data = request.json
        query = data.get('query', '').strip()
        summarize = data.get('summarize', False)
        local_model = data.get('local_model', 'Qwen/Qwen3-32B-AWQ')  # 사용자가 선택한 로컬 모델
        
        if not query:
            return jsonify({'error': '질문을 입력해주세요.'}), 400
        
        # 사용 가능한 모드 확인
        try:
            from models.dual_llm import DualLLMManager
            from config import Config
            
            # OpenAI API 키 상태 체크
            api_key = Config.OPENAI_API_KEY
            print(f"[DEBUG] OpenAI API Key 상태: {'설정됨' if api_key else '미설정'} (길이: {len(api_key) if api_key else 0})")
            
            dual_llm = DualLLMManager()
            available_models = dual_llm.get_available_models()
            print(f"[DEBUG] 모델 가용성: {available_models}")
            
            # 로컬 LLM 활성화 (사용자 요청)
            # available_models['local'] = False  # 로컬 LLM 비활성화  
            print(f"[INFO] 로컬 LLM 활성화됨 - kanana8b 모델 사용")
            
        except Exception as e:
            print(f"[ERROR] 모드 확인 중 오류: {e}")
            import traceback
            traceback.print_exc()
            # 기본적으로 ChatGPT 모드만 시도
            available_models = {'api': True, 'local': False}
        
        # Phase 1: 기본 방법들 - 순차 실행
        phase1_modes = []
        if available_models.get('local'):
            phase1_modes.append('local-basic')
        if available_models.get('api'):
            phase1_modes.append('chatgpt-basic')
        
        # Phase 2: 커스텀 방법들 - Phase 1 완료 후 실행  
        phase2_modes = []
        if available_models.get('local'):
            phase2_modes.append('local-custom')
        if available_models.get('api'):
            phase2_modes.append('chatgpt-custom')
        
        print(f"[INFO] 순차적 실행 시작 - Phase 1: {phase1_modes}, Phase 2: {phase2_modes}")
        
        # 처리 함수 정의
        def process_single_mode(mode, phase_info="", local_model_override=None):
            try:
                start_time = time.time()
                print(f"[{phase_info}] {mode} 모드 시작")
                
                # 로컬 LLM 모드인 경우 추가 체크
                if mode.startswith('local'):
                    try:
                        result = process_query_with_similarity_check(query, mode, summarize, local_model_override or local_model)
                    except Exception as local_error:
                        # 로컬 LLM 오류 시 유사도 정보 포함한 기본 응답 제공
                        rag_chain = get_enhanced_rag_chain()
                        search_results = rag_chain._search_documents(query, 3)
                        
                        # 유사도 정보 추출
                        similarity_info = []
                        if search_results:
                            for i, (doc, score) in enumerate(search_results[:3]):
                                similarity_info.append({
                                    'rank': i + 1,
                                    'score': round(score, 3),
                                    'content': doc.page_content[:100] + '...'
                                })
                        
                        end_time = time.time()
                        
                        return {
                            'mode': mode,
                            'result': {
                                'type': 'single',
                                'answer': f'사내서버 vLLM 사용 불가: {str(local_error)}\n\nvLLM 서버에 연결할 수 없습니다.\n해결방법: vLLM 서버(192.168.0.224:8412)가 실행 중인지 확인하고 ./models/kanana8b 모델이 로드되었는지 확인하세요.',
                                'response_time': round(end_time - start_time, 3),
                                'model': mode,
                                'success': False,
                                'similarity_scores': similarity_info,
                                'error_reason': 'local_llm_unavailable',
                                'timestamp': datetime.now().isoformat()
                            },
                            'success': False,
                            'error': f'Local LLM Error: {str(local_error)}'
                        }
                else:
                    print(f"[{phase_info}] {mode} ChatGPT API 호출 시작")
                    result = process_query_with_similarity_check(query, mode, summarize, local_model)
                    print(f"[{phase_info}] {mode} ChatGPT API 호출 완료: {result.get('success', False)}")
                
                end_time = time.time()
                print(f"[{phase_info}] {mode} 모드 완료 ({end_time - start_time:.2f}초)")
                
                # 처리 시간 추가
                if 'response_time' not in result:
                    result['response_time'] = end_time - start_time
                
                return {
                    'mode': mode,
                    'result': result,
                    'success': True,
                    'processing_time': end_time - start_time
                }
            except Exception as e:
                error_msg = str(e) if str(e) else type(e).__name__
                print(f"[{phase_info}] {mode} 모드 오류: {error_msg}")
                import traceback
                print(f"[{phase_info}] {mode} 상세 오류:")
                traceback.print_exc()
                print(f"[{phase_info}] {mode} 오류 타입: {type(e).__name__}")
                print(f"[{phase_info}] {mode} 오류 세부사항: {repr(e)}")
                
                # 더 자세한 오류 메시지 생성
                if hasattr(e, 'args') and e.args:
                    error_detail = f"{type(e).__name__}: {e.args[0]}"
                else:
                    error_detail = f"{type(e).__name__}: {error_msg}"
                
                return {
                    'mode': mode,
                    'result': {
                        'type': 'single',
                        'answer': f'처리 중 오류 발생: {error_detail}',
                        'response_time': 0,
                        'model': mode,
                        'success': False,
                        'similarity_scores': [],
                        'error_reason': 'processing_error',
                        'error_detail': error_detail,
                        'timestamp': datetime.now().isoformat()
                    },
                    'success': False,
                    'error': error_detail
                }

        # 오류 결과 생성 함수
        def create_error_result(mode, phase_info=""):
            if mode.startswith('local'):
                error_msg = '로컬 LLM(vLLM) 서버가 연결되지 않습니다.\n\n해결방법:\n1. vLLM 서버가 192.168.0.224:8412에서 실행 중인지 확인\n2. 네트워크 연결 상태 확인\n3. ./models/kanana8b 모델이 로드되었는지 확인'
                error_reason = 'vllm_not_available'
            else:
                error_msg = 'ChatGPT API 키가 설정되지 않았거나 잘못되었습니다.\n\n해결방법: .env 파일의 OPENAI_API_KEY를 확인하세요.'
                error_reason = 'api_key_missing'
            
            print(f"[{phase_info}] {mode} 모드 오류 생성: {error_reason}")
            return {
                'mode': mode,
                'result': {
                    'type': 'single',
                    'answer': error_msg,
                    'response_time': 0,
                    'model': mode,
                    'success': False,
                    'similarity_scores': [],
                    'error_reason': error_reason,
                    'timestamp': datetime.now().isoformat()
                },
                'success': False,
                'error': f'{mode} unavailable',
                'processing_time': 0
            }
        
        all_results = []
        
        # === PHASE 1 실행: ChatGPT 기본 (순차 실행) ===
        print(f"[PHASE 1] 시작 - ChatGPT 기본 순차 실행")
        phase1_start_time = time.time()
        
        # Phase 1 순차 실행
        for mode in phase1_modes:
            # ChatGPT 모드 실행 조건
            if mode.startswith('chatgpt') and available_models.get('api', False):
                print(f"[PHASE 1] {mode} 실행 시작")
                result = process_single_mode(mode, "PHASE 1", local_model)
                all_results.append(result)
                print(f"[PHASE 1] {mode} 완료: 성공={result.get('success', False)}")
            # 로컬 모드 실행 조건
            elif mode.startswith('local') and available_models.get('local', False):
                print(f"[PHASE 1] {mode} 실행 시작")
                result = process_single_mode(mode, "PHASE 1", local_model)
                all_results.append(result)
                print(f"[PHASE 1] {mode} 완료: 성공={result.get('success', False)}")
            else:
                # 오류 결과 생성
                error_result = create_error_result(mode, "PHASE 1")
                all_results.append(error_result)
                print(f"[PHASE 1] {mode} 스킵: 사용 불가능")
        
        phase1_duration = time.time() - phase1_start_time
        print(f"[PHASE 1] 모든 모드 완료 ({phase1_duration:.2f}초)")
        
        # === PHASE 2 실행: ChatGPT 커스텀 (순차 실행) ===
        print(f"[PHASE 2] 시작 - ChatGPT 커스텀 순차 실행")
        phase2_start_time = time.time()
        
        # Phase 2 순차 실행
        for mode in phase2_modes:
            # ChatGPT 모드 실행 조건
            if mode.startswith('chatgpt') and available_models.get('api', False):
                print(f"[PHASE 2] {mode} 실행 시작")
                result = process_single_mode(mode, "PHASE 2", local_model)
                all_results.append(result)
                print(f"[PHASE 2] {mode} 완료: 성공={result.get('success', False)}")
            # 로컬 모드 실행 조건
            elif mode.startswith('local') and available_models.get('local', False):
                print(f"[PHASE 2] {mode} 실행 시작")
                result = process_single_mode(mode, "PHASE 2", local_model)
                all_results.append(result)
                print(f"[PHASE 2] {mode} 완료: 성공={result.get('success', False)}")
            else:
                # 오류 결과 생성
                error_result = create_error_result(mode, "PHASE 2")
                all_results.append(error_result)
                print(f"[PHASE 2] {mode} 스킵: 사용 불가능")
        
        phase2_duration = time.time() - phase2_start_time
        print(f"[PHASE 2] 모든 모드 완료 ({phase2_duration:.2f}초)")
        
        # 전체 처리 통계
        total_processing_time = sum(r.get('processing_time', 0) for r in all_results)
        successful_modes = sum(1 for r in all_results if r.get('success', False))
        actual_modes_count = len(all_results)
        
        response = {
            'type': 'multi_benchmark_sequential',
            'query': query,
            'results': all_results,
            'execution_phases': {
                'phase1': {
                    'description': '기본 방법들 (동시 실행)',
                    'modes': phase1_modes,
                    'duration': phase1_duration,
                    'emoji': '🏠🤖'
                },
                'phase2': {
                    'description': '청킹 방법들 (순차 실행)',
                    'modes': phase2_modes,
                    'duration': phase2_duration,
                    'emoji': '🔧🧠'
                }
            },
            'summary': {
                'total_modes': actual_modes_count,
                'successful_modes': successful_modes,
                'failed_modes': actual_modes_count - successful_modes,
                'total_processing_time': total_processing_time,
                'average_processing_time': total_processing_time / actual_modes_count if actual_modes_count else 0,
                'phase1_time': phase1_duration,
                'phase2_time': phase2_duration,
                'total_execution_time': phase1_duration + phase2_duration
            },
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"[COMPLETE] 순차적 멀티 벤치마킹 완료 - 총 소요 시간: {phase1_duration + phase2_duration:.2f}초")
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({
            'error': f'순차적 멀티 벤치마킹 처리 중 오류 발생: {str(e)}',
            'type': 'error'
        }), 500

@multi_benchmark_bp.route('/system-status', methods=['GET'])
def get_multi_benchmark_status():
    """멀티 벤치마킹 시스템 상태 조회"""
    try:
        rag_chain = get_enhanced_rag_chain()
        
        # 각 LLM 상태 확인
        api_available = False
        local_available = False
        
        try:
            api_models = rag_chain.dual_llm.get_available_models().get('api', False)
            api_available = bool(api_models)
        except:
            pass
        
        try:
            local_models = rag_chain.dual_llm.get_available_models().get('local', False)
            local_available = bool(local_models)
        except:
            pass
        
        # 벡터DB 상태 확인
        vectordb_available = False
        doc_count = 0
        try:
            if hasattr(rag_chain, 'vectorstore'):
                doc_count = rag_chain.vectorstore.get_document_count()
                vectordb_available = doc_count > 0
        except:
            pass
        
        status = {
            'system_ready': api_available or local_available,
            'api_llm_available': api_available,
            'local_llm_available': local_available,
            'vectordb_available': vectordb_available,
            'document_count': doc_count,
            'supported_modes': {
                'chatgpt-basic': api_available,
                'chatgpt-custom': api_available,
                'local-basic': local_available,
                'local-custom': local_available
            },
            'executor_info': {
                'max_workers': executor._max_workers,
                'thread_count': len(executor._threads) if hasattr(executor, '_threads') else 0
            }
        }
        
        return jsonify({
            'status': 'success',
            'data': status,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': f'상태 조회 실패: {str(e)}'
        }), 500