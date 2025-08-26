#!/usr/bin/env python3
"""Backend debugging script to identify where processes are hanging"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.rag_chain import RAGChain
from models.llm import LLMManager
import traceback
import time

def test_vectorstore_search():
    """Test vectorstore search functionality"""
    print("[TEST] Testing vectorstore search...")
    try:
        chain = RAGChain()
        question = "테스트 질문"
        
        print(f"[TEST] Chain initialized: {chain}")
        print(f"[TEST] Has dual_vectorstore_manager: {hasattr(chain, 'dual_vectorstore_manager')}")
        
        if hasattr(chain, 'dual_vectorstore_manager') and chain.dual_vectorstore_manager:
            print("[TEST] Testing basic vectorstore search...")
            start_time = time.time()
            search_results = chain.dual_vectorstore_manager.similarity_search_with_score(question, "basic", k=3)
            end_time = time.time()
            print(f"[TEST] Basic search completed in {end_time - start_time:.2f}s: {len(search_results)} results")
            
            print("[TEST] Testing custom vectorstore search...")
            start_time = time.time()
            search_results = chain.dual_vectorstore_manager.similarity_search_with_score(question, "custom", k=3)
            end_time = time.time()
            print(f"[TEST] Custom search completed in {end_time - start_time:.2f}s: {len(search_results)} results")
        else:
            print("[TEST] Using fallback vectorstore...")
            start_time = time.time()
            search_results = chain.vectorstore_manager.similarity_search_with_score(question, k=3)
            end_time = time.time()
            print(f"[TEST] Fallback search completed in {end_time - start_time:.2f}s: {len(search_results)} results")
            
        return True
    except Exception as e:
        print(f"[ERROR] Vectorstore search failed: {str(e)}")
        traceback.print_exc()
        return False

def test_llm_calls():
    """Test LLM API calls"""
    print("[TEST] Testing LLM calls...")
    try:
        # Test OpenAI
        print("[TEST] Testing OpenAI API...")
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'), timeout=10.0)
        
        start_time = time.time()
        stream = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[{"role": "user", "content": "안녕하세요"}],
            stream=True,
            temperature=0.1
        )
        
        answer_text = ""
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                answer_text += chunk.choices[0].delta.content
        
        end_time = time.time()
        print(f"[TEST] OpenAI call completed in {end_time - start_time:.2f}s: {len(answer_text)} chars")
        
        # Test Local LLM
        print("[TEST] Testing Local LLM...")
        try:
            llm_manager = LLMManager()
            llm = llm_manager.get_llm(model_name='gpt-4o-mini')
            start_time = time.time()
            response = llm.invoke("안녕하세요")
            end_time = time.time()
            print(f"[TEST] Local LLM call completed in {end_time - start_time:.2f}s")
        except Exception as e:
            print(f"[TEST] Local LLM not available: {str(e)}")
        
        return True
    except Exception as e:
        print(f"[ERROR] LLM calls failed: {str(e)}")
        traceback.print_exc()
        return False

def test_single_process():
    """Test a single process execution"""
    print("[TEST] Testing single process execution...")
    try:
        from concurrent.futures import ThreadPoolExecutor
        from queue import Queue
        import uuid
        
        chain = RAGChain()
        question = "테스트 질문"
        llm_model = 'gpt-4o-mini'
        session_id = str(uuid.uuid4())
        result_queue = Queue()
        
        # Test process info
        process_info = {"llm_type": "openai", "chunking": "basic", "name": "테스트 프로세스", "process_id": 1}
        
        def test_process():
            print("[PROCESS] Starting test process...")
            start_time = time.time()
            
            try:
                # Simulate process start
                result_queue.put({
                    'type': 'process_start',
                    'process_name': process_info["name"],
                    'process_id': process_info["process_id"],
                    'session_id': session_id
                })
                print("[PROCESS] Process start event queued")
                
                # Test search
                print("[PROCESS] Testing search...")
                if hasattr(chain, 'dual_vectorstore_manager') and chain.dual_vectorstore_manager:
                    search_results = chain.dual_vectorstore_manager.similarity_search_with_score(question, "basic", k=3)
                else:
                    search_results = chain.vectorstore_manager.similarity_search_with_score(question, k=3)
                print(f"[PROCESS] Search completed: {len(search_results)} results")
                
                if search_results:
                    doc, score = search_results[0]
                    context = doc.page_content[:1000] if len(doc.page_content) > 1000 else doc.page_content
                    prompt = f"문서: {context}\n\n질문: {question}\n\n답변:"
                    
                    # Test LLM call
                    print("[PROCESS] Testing LLM call...")
                    from openai import OpenAI
                    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'), timeout=10.0)
                    stream = client.chat.completions.create(
                        model=llm_model,
                        messages=[{"role": "user", "content": prompt}],
                        stream=True,
                        temperature=0.1
                    )
                    
                    answer_text = ""
                    for chunk in stream:
                        if chunk.choices[0].delta.content is not None:
                            answer_text += chunk.choices[0].delta.content
                    print(f"[PROCESS] LLM call completed: {len(answer_text)} chars")
                    
                    # Success
                    end_time = time.time()
                    result_queue.put({
                        'type': 'process_complete',
                        'process_name': process_info["name"],
                        'process_id': process_info["process_id"],
                        'session_id': session_id,
                        'rank_answers': [{'rank': 1, 'score': f'{score:.1%}', 'answer': answer_text[:200]}],
                        'total_time': round(end_time - start_time, 2),
                        'status': 'success'
                    })
                    print("[PROCESS] Process complete event queued")
                else:
                    print("[PROCESS] No search results")
                    result_queue.put({
                        'type': 'process_error',
                        'process_name': process_info["name"],
                        'process_id': process_info["process_id"],
                        'session_id': session_id,
                        'error': 'no_results',
                        'status': 'failed'
                    })
                    
            except Exception as e:
                print(f"[PROCESS] Process failed: {str(e)}")
                traceback.print_exc()
                result_queue.put({
                    'type': 'process_error',
                    'process_name': process_info["name"],
                    'process_id': process_info["process_id"],
                    'session_id': session_id,
                    'error': str(e),
                    'status': 'failed'
                })
        
        # Run process in thread
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(test_process)
            
            # Monitor results
            completed = False
            timeout = 30
            start_time = time.time()
            
            while not completed and (time.time() - start_time) < timeout:
                try:
                    result = result_queue.get(timeout=1.0)
                    print(f"[MONITOR] Received: {result['type']} - {result.get('process_name')}")
                    
                    if result['type'] in ['process_complete', 'process_error']:
                        completed = True
                        print(f"[MONITOR] Process completed: {result.get('status')}")
                        
                except:
                    continue
            
            if not completed:
                print("[ERROR] Process timed out")
                return False
                
            future.result(timeout=1)
        
        return True
    except Exception as e:
        print(f"[ERROR] Single process test failed: {str(e)}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== Backend Debugging ===")
    
    print("\n1. Testing vectorstore search...")
    vectorstore_ok = test_vectorstore_search()
    
    print("\n2. Testing LLM calls...")
    llm_ok = test_llm_calls()
    
    print("\n3. Testing single process...")
    process_ok = test_single_process()
    
    print(f"\n=== Results ===")
    print(f"Vectorstore: {'✓' if vectorstore_ok else '✗'}")
    print(f"LLM calls: {'✓' if llm_ok else '✗'}")
    print(f"Process: {'✓' if process_ok else '✗'}")
    
    if vectorstore_ok and llm_ok and process_ok:
        print("\n✓ All tests passed - backend should be working")
    else:
        print("\n✗ Some tests failed - check logs above")