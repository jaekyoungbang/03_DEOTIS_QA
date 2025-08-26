#!/usr/bin/env python3
"""
Ollama 원격 서버 연결 테스트
"""
import os
import sys
import requests

# 환경변수 설정
os.environ['OLLAMA_BASE_URL'] = 'http://192.168.0.224:11434'
os.environ['USE_OLLAMA_BGE_M3'] = 'true'

print("=" * 60)
print("Ollama 원격 서버 연결 테스트")
print("=" * 60)

# 1. 서버 연결 테스트
print("\n1. 서버 연결 테스트...")
try:
    response = requests.get('http://192.168.0.224:11434/api/tags', timeout=5)
    if response.status_code == 200:
        print("✅ 서버 연결 성공!")
        models = response.json().get('models', [])
        print(f"\n사용 가능한 모델 ({len(models)}개):")
        for model in models:
            print(f"  - {model['name']}")
    else:
        print(f"❌ 서버 응답 오류: {response.status_code}")
        sys.exit(1)
except Exception as e:
    print(f"❌ 서버 연결 실패: {e}")
    sys.exit(1)

# 2. BGE-M3 임베딩 테스트
print("\n2. BGE-M3 임베딩 테스트...")
try:
    from models.ollama_embeddings import OllamaEmbeddings
    embeddings = OllamaEmbeddings()
    
    test_text = "BC카드 민원접수 방법"
    result = embeddings.embed_query(test_text)
    print(f"✅ 임베딩 성공!")
    print(f"   텍스트: {test_text}")
    print(f"   벡터 차원: {len(result)}")
    print(f"   첫 5개 값: {result[:5]}")
except Exception as e:
    print(f"❌ 임베딩 실패: {e}")

# 3. Yanolja LLM 테스트
print("\n3. Yanolja LLM 테스트...")
try:
    from models.yanolja_llm import YanoljaLLM
    llm = YanoljaLLM()
    
    if llm.test_connection():
        print("✅ Yanolja LLM 연결 성공!")
        
        # 간단한 생성 테스트
        test_prompt = "안녕하세요. BC카드입니다. 무엇을 도와드릴까요?"
        print(f"\n테스트 프롬프트: {test_prompt}")
        response = llm.invoke(test_prompt)
        print(f"응답: {response.content[:100]}...")
    else:
        print("❌ Yanolja LLM 모델을 찾을 수 없습니다.")
except Exception as e:
    print(f"❌ Yanolja LLM 테스트 실패: {e}")

# 4. 전체 시스템 테스트
print("\n4. 전체 RAG 시스템 테스트...")
try:
    from services.rag_chain import RAGChain
    
    # 환경변수로 Yanolja 설정
    os.environ['DEFAULT_LLM_MODEL'] = 'yanolja'
    
    rag = RAGChain()
    
    test_question = "민원접수방법 안내"
    print(f"\n테스트 질문: {test_question}")
    print("검색 중...")
    
    result = rag.query(test_question, llm_model='yanolja', search_mode='custom')
    
    if 'error' not in result:
        print("✅ RAG 시스템 작동 성공!")
        print(f"답변 첫 200자: {result['answer'][:200]}...")
    else:
        print(f"❌ RAG 시스템 오류: {result.get('message')}")
except Exception as e:
    print(f"❌ RAG 시스템 테스트 실패: {e}")

print("\n" + "=" * 60)
print("테스트 완료!")
print("=" * 60)