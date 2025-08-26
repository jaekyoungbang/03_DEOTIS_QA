from flask import Blueprint, request, jsonify, stream_with_context, Response
from services.rag_chain import RAGChain
import json

chat_bp = Blueprint('chat', __name__)

# Initialize RAG chain (consider using app context or dependency injection in production)
rag_chain = None

def get_rag_chain():
    global rag_chain
    if rag_chain is None:
        rag_chain = RAGChain()
    return rag_chain

@chat_bp.route('/query', methods=['POST'])
@chat_bp.route('/../rag/chat', methods=['POST'])
def query():
    """Handle chat queries"""
    try:
        data = request.get_json()
        question = data.get('question')
        use_memory = data.get('use_memory', False)
        llm_model = data.get('llm_model', 'gpt-4o-mini')
        search_mode = data.get('search_mode', 'basic')
        
        if not question:
            return jsonify({"error": "Question is required"}), 400
        
        # Get RAG chain instance
        chain = get_rag_chain()
        
        # Query the RAG system with search mode
        response = chain.query(
            question, 
            use_memory=use_memory, 
            llm_model=llm_model,
            search_mode=search_mode
        )
        
        return jsonify(response)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@chat_bp.route('/stream', methods=['POST'])
def stream_query():
    """Handle streaming chat queries with real-time progress"""
    try:
        data = request.get_json()
        question = data.get('question')
        use_memory = data.get('use_memory', False)
        llm_model = data.get('llm_model', 'gpt-4o-mini')
        search_mode = data.get('search_mode', 'basic')
        summarize = data.get('summarize', False)
        
        if not question:
            return jsonify({"error": "Question is required"}), 400
        
        def generate():
            import time
            
            try:
                chain = get_rag_chain()
                
                # Step 4: 4개 별도 프로세스로 비동기 처리
                from models.llm import LLMManager
                from openai import OpenAI
                import os
                import platform
                from queue import Queue, Empty
                from concurrent.futures import ThreadPoolExecutor, as_completed
                import uuid
                
                # 프로세스별 폴더 경로 설정
                if platform.system() == "Windows":
                    s3_folder = "D:\\99_DEOTIS_QA_SYSTEM\\03_DEOTIS_QA\\s3"
                    s3_chunking_folder = "D:\\99_DEOTIS_QA_SYSTEM\\03_DEOTIS_QA\\s3-chunking"
                else:
                    s3_folder = "/mnt/d/99_DEOTIS_QA_SYSTEM/03_DEOTIS_QA/s3"
                    s3_chunking_folder = "/mnt/d/99_DEOTIS_QA_SYSTEM/03_DEOTIS_QA/s3-chunking"
                
                # 4개 프로세스 정의
                processes = [
                    {"llm_type": "openai", "chunking": "basic", "folder": s3_folder, "name": "ChatGPT + s3기본", "process_id": 1},
                    {"llm_type": "openai", "chunking": "custom", "folder": s3_chunking_folder, "name": "ChatGPT + s3-chunking", "process_id": 2},
                    {"llm_type": "local", "chunking": "basic", "folder": s3_folder, "name": "로컬LLM + s3기본", "process_id": 3},
                    {"llm_type": "local", "chunking": "custom", "folder": s3_chunking_folder, "name": "로컬LLM + s3-chunking", "process_id": 4}
                ]
                
                # Create a queue for streaming results from multiple processes
                result_queue = Queue()
                
                def process_single_search_task(process_info, question, llm_model, chain, session_id, summarize=False):
                    """단일 검색 프로세스 처리 - 완전 독립적 실행"""
                    start_time = time.time()  # 시작 시간 기록
                    try:
                        process_name = process_info["name"]
                        chunking_type = process_info["chunking"]
                        llm_type = process_info["llm_type"]
                        process_id = process_info["process_id"]
                        
                        print(f"[PROCESS] Starting {process_name} (ID: {process_id})")
                        
                        # 프로세스 시작 신호
                        result_queue.put({
                            'type': 'process_start',
                            'process_name': process_name,
                            'process_id': process_id,
                            'session_id': session_id
                        })
                        
                        # 로컬 LLM 사용 불가능 시 오류 처리
                        if llm_type == "local":
                            try:
                                # 로컬 LLM 연결 테스트
                                from models.llm import LLMManager
                                llm_manager = LLMManager()
                                llm_manager.get_llm(model_name=llm_model)
                            except Exception as e:
                                result_queue.put({
                                    'type': 'process_error',
                                    'process_name': process_name,
                                    'process_id': process_id,
                                    'session_id': session_id,
                                    'error': 'vllm_not_running',
                                    'message': '사내서버 vLLM이 실행되지 않았습니다. 해결방법: 1. vLLM 서버 상태 확인: 192.168.0.224:8412 2. kanana8b 모델 로딩 확인 3. 서버 재시작 필요시 연락',
                                    'similarity_info': [],  # 오류 시 빈 유사도 정보
                                    'total_time': 0.0,
                                    'status': 'failed'
                                })
                                return
                        
                        # 해당 청킹 타입으로 검색 수행
                        print(f"[DEBUG] {process_name} 검색 시작 - 청킹타입: {chunking_type}")
                        print(f"[DEBUG] Chain object: {chain}")
                        print(f"[DEBUG] Has dual_vectorstore_manager: {hasattr(chain, 'dual_vectorstore_manager')}")
                        
                        if hasattr(chain, 'dual_vectorstore_manager') and chain.dual_vectorstore_manager:
                            if chunking_type == "custom":
                                print(f"[DEBUG] custom 벡터스토어에서 검색")
                                search_results = chain.dual_vectorstore_manager.similarity_search_with_score(question, "custom", k=3)
                            else:
                                print(f"[DEBUG] basic 벡터스토어에서 검색")
                                search_results = chain.dual_vectorstore_manager.similarity_search_with_score(question, "basic", k=3)
                        else:
                            # 폴백: 기본 벡터스토어 사용
                            print(f"[DEBUG] 폴백: 기본 벡터스토어 사용")
                            search_results = chain.vectorstore_manager.similarity_search_with_score(question, k=3)
                        
                        print(f"[DEBUG] {process_name} 검색 결과: {len(search_results)}개, 첫번째 점수: {search_results[0][1]:.2%}" if search_results else "검색 결과 없음")
                        
                        if not search_results:
                            print(f"[WARNING] {process_name} - No search results found")
                            result_queue.put({
                                'type': 'process_error',
                                'process_name': process_name,
                                'process_id': process_id,
                                'session_id': session_id,
                                'error': 'no_results',
                                'message': '검색 결과가 없습니다.',
                                'total_time': round(time.time() - start_time, 2),
                                'status': 'failed',
                                'similarity_info': []
                            })
                            return
                        
                        # 각 순위별로 개별 답변 생성
                        rank_answers = []
                        
                        # 검색된 문서들을 유사도별로 처리 (Top 3)
                        for rank, (doc, score) in enumerate(search_results[:3], 1):
                            try:
                                # 개별 문서에 대한 최적화된 프롬프트 생성 (chunking optimization)
                                # Truncate overly long documents to reduce LLM input length
                                max_doc_length = 2000  # Optimal length per document
                                if len(doc.page_content) > max_doc_length:
                                    individual_context = doc.page_content[:max_doc_length-3] + "..."
                                    print(f"[CHUNKING OPT] Document truncated from {len(doc.page_content)} to {len(individual_context)} chars")
                                else:
                                    individual_context = doc.page_content
                                # 요약 모드에 따른 프롬프트 조정
                                if summarize:
                                    individual_prompt = f"""주어진 문서를 기반으로 질문에 대한 답변을 간결하게 요약하여 제공하세요.
핵심 내용만 포함하고 불필요한 세부사항은 제외하세요.

문서 내용:
{individual_context}

질문: {question}

답변:"""
                                else:
                                    individual_prompt = chain.prompt_template.format(context=individual_context, question=question)
                                
                                answer_text = ""
                                
                                if llm_type == "openai":
                                    # OpenAI API 호출 (타임아웃 30초)
                                    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'), timeout=30.0)
                                    stream = client.chat.completions.create(
                                        model=llm_model,
                                        messages=[{"role": "user", "content": individual_prompt}],
                                        stream=True,
                                        temperature=0.1
                                    )
                                    
                                    # 전체 답변을 수집
                                    for chunk in stream:
                                        if chunk.choices[0].delta.content is not None:
                                            answer_text += chunk.choices[0].delta.content
                                
                                else:
                                    # 로컬 LLM 처리
                                    llm_manager = LLMManager()
                                    llm = llm_manager.get_llm(model_name='local')  # 로컬 LLM 사용
                                    full_response = llm.invoke(individual_prompt)
                                    
                                    # vLLM 응답에서 content 추출
                                    if hasattr(full_response, 'content'):
                                        answer_text = full_response.content
                                    elif isinstance(full_response, str):
                                        answer_text = full_response
                                    else:
                                        answer_text = str(full_response)
                                
                                # 완성된 답변을 저장
                                rank_answers.append({
                                    'rank': rank,
                                    'score': f'{score:.1%}',
                                    'answer': answer_text,
                                    'source': doc.metadata.get('source_file', 'Unknown')
                                })
                                
                            except Exception as doc_error:
                                rank_answers.append({
                                    'rank': rank,
                                    'score': f'{score:.1%}',
                                    'answer': f'오류 발생: {str(doc_error)}',
                                    'source': doc.metadata.get('source_file', 'Unknown')
                                })
                        
                        # 프로세스 완료 - 순위별 답변들과 시간 정보 전송
                        end_time = time.time()
                        total_time = end_time - start_time
                        
                        # 유사도 Top 3 정보 생성
                        similarity_info = []
                        for i, (doc, score) in enumerate(search_results[:3], 1):
                            similarity_info.append({
                                'rank': i,
                                'score': f'{score:.1%}',
                                'source': doc.metadata.get('source_file', 'Unknown'),
                                'content_preview': doc.page_content[:100] + '...' if len(doc.page_content) > 100 else doc.page_content
                            })
                        
                        print(f"[SUCCESS] Process {process_name} completed successfully")
                        print(f"[SUCCESS] Generated {len(rank_answers)} answers")
                        
                        result_queue.put({
                            'type': 'process_complete',
                            'process_name': process_name,
                            'process_id': process_id,
                            'session_id': session_id,
                            'rank_answers': rank_answers,
                            'similarity_info': similarity_info,
                            'total_time': round(total_time, 2),
                            'status': 'success',
                            'chunking_type': process_info["chunking"]  # chunking_type 추가
                        })
                        print(f"[SUCCESS] Complete event queued for process {process_id}")
                        
                    except Exception as e:
                        end_time = time.time()
                        total_time = end_time - start_time
                        print(f"[ERROR] Process {process_info['name']} failed: {str(e)}")
                        import traceback
                        print(f"[ERROR] Traceback: {traceback.format_exc()}")
                        
                        result_queue.put({
                            'type': 'process_error',
                            'process_name': process_info["name"],
                            'process_id': process_info["process_id"],
                            'session_id': session_id,
                            'error': str(e),
                            'message': f'프로세스 실행 중 오류: {str(e)}',
                            'total_time': round(total_time, 2),
                            'status': 'failed',
                            'similarity_info': []  # 오류 시 빈 유사도 정보
                        })
                        print(f"[ERROR] Error event queued for process {process_info['process_id']}")
                
                # 세션 ID 생성
                session_id = str(uuid.uuid4())
                
                # 4개 프로세스 시작 알림
                yield f"data: {json.dumps({'type': 'all_processes_start', 'total_processes': len(processes), 'session_id': session_id})}\n\n"
                
                # 4개 프로세스를 병렬로 시작
                with ThreadPoolExecutor(max_workers=4) as executor:
                    futures = []
                    
                    for process_info in processes:
                        print(f"[DEBUG] Starting process: {process_info['name']} (ID: {process_info['process_id']})")
                        future = executor.submit(
                            process_single_search_task,
                            process_info, question, llm_model, chain, session_id, summarize
                        )
                        futures.append(future)
                    
                    print(f"[DEBUG] All {len(futures)} processes submitted")
                    
                    # 결과를 실시간으로 스트리밍 (개별 프로세스 완료 즉시 표시)
                    completed_processes = 0
                    total_processes = len(processes)
                    
                    while completed_processes < total_processes:
                        try:
                            # 큐에서 결과 가져오기 (타임아웃을 짧게 설정하여 실시간성 향상)
                            result = result_queue.get(timeout=0.05)
                            
                            # 결과 즉시 스트리밍 (각 프로세스가 완료되는 순간 바로 화면에 표시)
                            yield f"data: {json.dumps(result)}\n\n"
                            
                            # 완료된 프로세스 카운트
                            if result['type'] in ['process_complete', 'process_error']:
                                completed_processes += 1
                                print(f"[STREAM] 프로세스 완료: {result.get('process_name', 'Unknown')} ({completed_processes}/{total_processes})")
                                
                        except Empty:
                            # 결과가 없으면 아주 짧은 시간 대기 후 계속 폴링
                            time.sleep(0.01)
                            continue
                    
                    # 모든 futures 정리
                    for future in as_completed(futures, timeout=30):
                        try:
                            future.result()
                        except Exception as e:
                            print(f"프로세스 완료 오류: {e}")
                
                # 최종 완료 메시지
                yield f"data: {json.dumps({'type': 'all_complete', 'message': '모든 프로세스 완료'})}\n\n"
                
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                yield "data: [DONE]\n\n"
        
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'X-Accel-Buffering': 'no'  # Disable nginx buffering
            }
        )
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@chat_bp.route('/chatgpt-basic', methods=['POST'])
def chatgpt_basic():
    """ChatGPT + s3기본 개별 처리"""
    try:
        data = request.get_json()
        question = data.get('question')
        
        if not question:
            return jsonify({"error": "Question is required"}), 400
        
        chain = get_rag_chain()
        
        # 기본 검색 수행
        import time
        start_time = time.time()
        
        try:
            if hasattr(chain, 'dual_vectorstore_manager') and chain.dual_vectorstore_manager:
                search_results = chain.dual_vectorstore_manager.similarity_search_with_score(question, "basic", k=5)
            else:
                search_results = chain.vectorstore_manager.similarity_search_with_score(question, k=5)
            
            # s3 폴더 문서만 필터링 (s3-chunking 제외)
            s3_results = [(doc, score) for doc, score in search_results if doc.metadata.get('source') == 's3']
            
            if not s3_results:
                return jsonify({
                    'success': False,
                    'answer': 's3 폴더의 문서가 없습니다. s3 폴더에서 문서를 먼저 로드해주세요.',
                    'similarity_info': [],
                    'total_time': 0.0,
                    'process_name': 'ChatGPT + s3기본',
                    'chunking_type': 'basic'
                })
            
            # 첫 번째 결과로 최적화된 답변 생성 (chunking optimization)
            if s3_results:
                doc, score = s3_results[0]
                # Optimize context length for better LLM performance
                max_context_length = 2500  # Optimal length for single document processing
                if len(doc.page_content) > max_context_length:
                    context = doc.page_content[:max_context_length-3] + "..."
                    print(f"[CHUNKING OPT] ChatGPT-basic context truncated from {len(doc.page_content)} to {len(context)} chars")
                else:
                    context = doc.page_content
                prompt = chain.prompt_template.format(context=context, question=question)
                
                # OpenAI API 호출
                from openai import OpenAI
                import os
                client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'), timeout=30.0)
                stream = client.chat.completions.create(
                    model='gpt-4o-mini',
                    messages=[{"role": "user", "content": prompt}],
                    stream=True,
                    temperature=0.1
                )
                
                answer_text = ""
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        answer_text += chunk.choices[0].delta.content
                
                # 유사도 정보 생성 (s3 결과만 사용)
                similarity_info = []
                for i, (doc, score) in enumerate(s3_results[:3], 1):
                    similarity_info.append({
                        'rank': i,
                        'score': f'{score:.1%}',
                        'source': doc.metadata.get('source', 's3'),
                        'content_preview': doc.page_content[:100] + '...' if len(doc.page_content) > 100 else doc.page_content
                    })
                
                end_time = time.time()
                total_time = end_time - start_time
                
                return jsonify({
                    'success': True,
                    'answer': answer_text,
                    'similarity_info': similarity_info,
                    'total_time': round(total_time, 2),
                    'process_name': 'ChatGPT + s3기본',
                    'chunking_type': 'basic'
                })
            else:
                return jsonify({
                    'success': False,
                    'answer': '관련 문서를 찾을 수 없습니다.',
                    'similarity_info': [],
                    'total_time': 0.0,
                    'process_name': 'ChatGPT + s3기본',
                    'chunking_type': 'basic'
                })
                
        except Exception as e:
            end_time = time.time()
            total_time = end_time - start_time
            return jsonify({
                'success': False,
                'answer': f'오류 발생: {str(e)}',
                'similarity_info': [],
                'total_time': round(total_time, 2),
                'process_name': 'ChatGPT + s3기본',
                'chunking_type': 'basic'
            })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@chat_bp.route('/chatgpt-custom', methods=['POST'])
def chatgpt_custom():
    """ChatGPT + s3-chunking 개별 처리"""
    try:
        data = request.get_json()
        question = data.get('question')
        
        if not question:
            return jsonify({"error": "Question is required"}), 400
        
        chain = get_rag_chain()
        
        # 커스텀 검색 수행
        import time
        start_time = time.time()
        
        try:
            if hasattr(chain, 'dual_vectorstore_manager') and chain.dual_vectorstore_manager:
                search_results = chain.dual_vectorstore_manager.similarity_search_with_score(question, "custom", k=3)
            else:
                search_results = chain.vectorstore_manager.similarity_search_with_score(question, k=3)
            
            # 첫 번째 결과로 최적화된 답변 생성 (chunking optimization)
            if search_results:
                doc, score = search_results[0]
                # Optimize context length for better LLM performance  
                max_context_length = 2500  # Optimal length for single document processing
                if len(doc.page_content) > max_context_length:
                    context = doc.page_content[:max_context_length-3] + "..."
                    print(f"[CHUNKING OPT] ChatGPT-custom context truncated from {len(doc.page_content)} to {len(context)} chars")
                else:
                    context = doc.page_content
                prompt = chain.prompt_template.format(context=context, question=question)
                
                # OpenAI API 호출
                from openai import OpenAI
                import os
                client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'), timeout=30.0)
                stream = client.chat.completions.create(
                    model='gpt-4o-mini',
                    messages=[{"role": "user", "content": prompt}],
                    stream=True,
                    temperature=0.1
                )
                
                answer_text = ""
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        answer_text += chunk.choices[0].delta.content
                
                # 유사도 정보 생성
                similarity_info = []
                for i, (doc, score) in enumerate(search_results[:3], 1):
                    similarity_info.append({
                        'rank': i,
                        'score': f'{score:.1%}',
                        'source': doc.metadata.get('source_file', 'Unknown'),
                        'content_preview': doc.page_content[:100] + '...' if len(doc.page_content) > 100 else doc.page_content
                    })
                
                end_time = time.time()
                total_time = end_time - start_time
                
                return jsonify({
                    'success': True,
                    'answer': answer_text,
                    'similarity_info': similarity_info,
                    'total_time': round(total_time, 2),
                    'process_name': 'ChatGPT + s3-chunking',
                    'chunking_type': 'custom'
                })
            else:
                return jsonify({
                    'success': False,
                    'answer': '관련 문서를 찾을 수 없습니다.',
                    'similarity_info': [],
                    'total_time': 0.0,
                    'process_name': 'ChatGPT + s3-chunking',
                    'chunking_type': 'custom'
                })
                
        except Exception as e:
            end_time = time.time()
            total_time = end_time - start_time
            return jsonify({
                'success': False,
                'answer': f'오류 발생: {str(e)}',
                'similarity_info': [],
                'total_time': round(total_time, 2),
                'process_name': 'ChatGPT + s3-chunking',
                'chunking_type': 'custom'
            })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@chat_bp.route('/local-basic', methods=['POST'])
def local_basic():
    """로컬LLM + s3기본 개별 처리"""
    try:
        data = request.get_json()
        question = data.get('question')
        session_id = data.get('session_id', str(uuid.uuid4()))
        
        if not question:
            return jsonify({'error': '질문이 필요합니다'}), 400
        
        def generate_response():
            try:
                start_time = time.time()
                
                # 벡터 검색 수행 (basic 컬렉션에서 검색 - s3 문서만)
                from models.dual_vectorstore import get_dual_vectorstore
                dual_vectorstore = get_dual_vectorstore()
                search_results = dual_vectorstore.similarity_search_with_score(question, "basic", k=5)
                
                if not search_results:
                    yield f"data: {json.dumps({'type': 'process_error', 'process_name': '로컬LLM + s3기본', 'process_id': 3, 'session_id': session_id, 'error': 'no_documents', 'message': '검색된 문서가 없습니다. s3 폴더에서 문서를 먼저 로드해주세요.', 'similarity_info': [], 'total_time': 0.0, 'status': 'failed'}, ensure_ascii=False)}\n\n"
                    return

                # basic 컬렉션에는 이미 s3 문서만 있으므로 필터링 불필요
                s3_results = search_results
                
                if not s3_results:
                    yield f"data: {json.dumps({'type': 'process_error', 'process_name': '로컬LLM + s3기본', 'process_id': 3, 'session_id': session_id, 'error': 'no_s3_documents', 'message': 's3 폴더의 문서가 없습니다. s3 폴더에서 문서를 먼저 로드해주세요.', 'similarity_info': [], 'total_time': 0.0, 'status': 'failed'}, ensure_ascii=False)}\n\n"
                    return

                # 컨텍스트 생성 (매우 짧게, 로컬 LLM 토큰 제한)
                s3_context = ""
                max_context_length = 200  # 더 짧게 제한
                for doc, score in s3_results[:2]:  # 2개만 사용
                    content = doc.page_content[:max_context_length]
                    s3_context += f"{content}\n\n"
                    if len(s3_context) > 400:  # 매우 짧은 전체 길이
                        break

                # 로컬 LLM 호출 (매우 짧은 프롬프트)
                from models.llm import LLMManager
                llm_manager = LLMManager()
                local_llm = llm_manager.get_llm(model_name='local')
                
                prompt = f"""다음 정보로 답변: {s3_context[:300]}

질문: {question}

답변:"""

                try:
                    response = local_llm.invoke(prompt)
                    answer = str(response) if response else '로컬 LLM 응답 없음'
                except Exception as e:
                    # 로컬 LLM 에러 시 컨텍스트 기반 간단 답변
                    answer = f"검색된 정보: {s3_context[:200]}... (로컬 LLM 서버 에러: {str(e)[:50]})"
                
                end_time = time.time()
                total_time = end_time - start_time
                
                # 유사도 정보 생성 (s3 결과만 사용)
                similarity_info = []
                for i, (doc, score) in enumerate(s3_results[:3], 1):
                    similarity_info.append({
                        'rank': i,
                        'score': f'{score:.1%}',
                        'source': doc.metadata.get('source', 's3'),
                        'content_preview': doc.page_content[:100] + '...' if len(doc.page_content) > 100 else doc.page_content
                    })
                
                yield f"data: {json.dumps({'type': 'process_complete', 'process_name': '로컬LLM + s3기본', 'process_id': 3, 'session_id': session_id, 'answer': answer, 'similarity_info': similarity_info, 'total_time': total_time, 'status': 'success', 'chunking_type': 'basic'}, ensure_ascii=False)}\n\n"
                
            except Exception as e:
                print(f"로컬LLM 기본 처리 오류: {e}")
                yield f"data: {json.dumps({'type': 'process_error', 'process_name': '로컬LLM + s3기본', 'process_id': 3, 'session_id': session_id, 'error': 'connection_error', 'message': f'로컬 LLM 연결 오류: {str(e)}. 로컬 LLM 서버를 시작해주세요.', 'similarity_info': [], 'total_time': 0.0, 'status': 'failed'}, ensure_ascii=False)}\n\n"

        return Response(
            generate_response(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'
            }
        )
        
    except Exception as e:
        return jsonify({
            'error': f'로컬LLM + s3기본 처리 실패: {str(e)}',
            'status': 'failed'
        }), 500

@chat_bp.route('/local-custom', methods=['POST'])
def local_custom():
    """로컬LLM + s3-chunking 개별 처리"""
    try:
        data = request.get_json()
        question = data.get('question')
        session_id = data.get('session_id', str(uuid.uuid4()))
        
        if not question:
            return jsonify({'error': '질문이 필요합니다'}), 400
        
        def generate_response():
            try:
                start_time = time.time()
                
                # 벡터 검색 수행
                vectorstore_manager = VectorStoreManager()
                search_results = vectorstore_manager.similarity_search(question, k=5)
                
                if not search_results:
                    yield f"data: {json.dumps({'type': 'process_error', 'process_name': '로컬LLM + s3-chunking', 'process_id': 4, 'session_id': session_id, 'error': 'no_documents', 'message': '검색된 문서가 없습니다. s3-chunking 폴더에서 문서를 먼저 로드해주세요.', 'similarity_info': [], 'total_time': 0.0, 'status': 'failed'}, ensure_ascii=False)}\n\n"
                    return

                # s3-chunking 문서 필터링
                s3_chunking_results = [(doc, score) for doc, score in search_results if doc.metadata.get('source') == 's3-chunking']
                
                if not s3_chunking_results:
                    yield f"data: {json.dumps({'type': 'process_error', 'process_name': '로컬LLM + s3-chunking', 'process_id': 4, 'session_id': session_id, 'error': 'no_chunking_documents', 'message': 's3-chunking 폴더의 문서가 없습니다.', 'similarity_info': [], 'total_time': 0.0, 'status': 'failed'}, ensure_ascii=False)}\n\n"
                    return

                # 컨텍스트 생성 (s3-chunking 문서만 사용, 길이 제한)
                context = ""
                max_context_length = 500  # 로컬 LLM의 토큰 제한 고려
                for doc, score in s3_chunking_results[:3]:
                    content = doc.page_content
                    if len(content) > max_context_length:
                        content = content[:max_context_length] + "..."
                    context += f"[유사도: {score:.1%}] {content}\n\n"
                    if len(context) > 1000:  # 전체 컨텍스트 길이 제한
                        break

                # 로컬 LLM 호출 (LocalLLM 클래스 사용)
                from models.llm import LLMManager
                llm_manager = LLMManager()
                local_llm = llm_manager.get_llm(model_name='local')
                
                prompt = f"""다음 정보로 답변: {context[:300]}

질문: {question}

답변:"""

                try:
                    response = local_llm.invoke(prompt)
                    answer = str(response) if response else '로컬 LLM 응답 없음'
                except Exception as e:
                    # 로컬 LLM 에러 시 컨텍스트 기반 간단 답변
                    answer = f"검색된 정보: {context[:200]}... (로컬 LLM 서버 에러: {str(e)[:50]})"
                
                end_time = time.time()
                total_time = end_time - start_time
                
                # 유사도 정보 생성
                similarity_info = []
                for i, (doc, score) in enumerate(s3_chunking_results[:3], 1):
                    similarity_info.append({
                        'rank': i,
                        'score': f'{score:.1%}',
                        'source': doc.metadata.get('source', 's3-chunking'),
                        'content_preview': doc.page_content[:100] + '...' if len(doc.page_content) > 100 else doc.page_content
                    })
                
                yield f"data: {json.dumps({'type': 'process_complete', 'process_name': '로컬LLM + s3-chunking', 'process_id': 4, 'session_id': session_id, 'answer': answer, 'similarity_info': similarity_info, 'total_time': total_time, 'status': 'success', 'chunking_type': 'custom'}, ensure_ascii=False)}\n\n"
                
            except Exception as e:
                print(f"로컬LLM 커스텀 처리 오류: {e}")
                yield f"data: {json.dumps({'type': 'process_error', 'process_name': '로컬LLM + s3-chunking', 'process_id': 4, 'session_id': session_id, 'error': 'connection_error', 'message': f'로컬 LLM 연결 오류: {str(e)}. 로컬 LLM 서버를 시작해주세요.', 'similarity_info': [], 'total_time': 0.0, 'status': 'failed'}, ensure_ascii=False)}\n\n"

        return Response(
            generate_response(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'
            }
        )
        
    except Exception as e:
        return jsonify({
            'error': f'로컬LLM + s3-chunking 처리 실패: {str(e)}',
            'status': 'failed'
        }), 500

@chat_bp.route('/clear-memory', methods=['POST'])
def clear_memory():
    """Clear conversation memory"""
    try:
        chain = get_rag_chain()
        chain.clear_memory()
        return jsonify({"message": "Memory cleared successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500