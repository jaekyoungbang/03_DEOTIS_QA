#!/usr/bin/env python3
"""
정확한 RAG 이슈 재현 테스트
"""

import time
from services.rag_chain import RAGChain

def test_rag_query_multiple_times():
    """RAG 쿼리를 여러번 실행하여 일관성 확인"""
    
    rag = RAGChain()
    query = '신용카드 업무처리 안내'
    
    print(f"쿼리: {query}")
    print("=" * 50)
    
    # Test multiple times
    for i in range(5):
        print(f"\n=== 테스트 {i+1} ===")
        
        # Test basic mode
        result = rag.query(query, use_memory=False, use_cache=False, search_mode='basic')
        
        if 'similarity_search' in result and result['similarity_search']['top_matches']:
            top_match = result['similarity_search']['top_matches'][0]
            score = top_match['similarity_score']
            percentage = top_match['similarity_percentage']
            filename = top_match.get('document_title', 'Unknown')
            content_preview = top_match['content_preview'][:100]
            
            print(f"최고 점수: {score:.4f} ({percentage:.2f}%)")
            print(f"파일: {filename}")
            print(f"내용: {content_preview}...")
            
            if '신용카드 업무처리 안내' in content_preview:
                print("*** 정확한 매치! ***")
            else:
                print("*** 잘못된 결과! ***")
        else:
            print("검색 결과 없음")
        
        # Small delay
        time.sleep(0.1)

def test_with_original_vectorstore():
    """원본 vectorstore로 직접 테스트"""
    
    from models.vectorstore import get_vectorstore
    from models.embeddings import EmbeddingManager
    
    em = EmbeddingManager()
    vs = get_vectorstore()
    
    query = '신용카드 업무처리 안내'
    
    print(f"\n=== 원본 전역 vectorstore 테스트 ===")
    print(f"Vectorstore 주소: {id(vs)}")
    
    # Test similarity search with score
    results = vs.similarity_search_with_relevance_scores(query, k=3)
    
    for i, (doc, score) in enumerate(results):
        filename = doc.metadata.get('filename', 'Unknown')
        content_preview = doc.page_content[:100].replace('\n', ' ')
        
        print(f'{i+1}. 점수: {score:.4f} ({score*100:.2f}%) | 파일: {filename}')
        print(f'   내용: {content_preview}...')
        
        if '신용카드 업무처리 안내' in doc.page_content[:50]:
            print('   *** 정확한 매치! ***')

if __name__ == "__main__":
    test_rag_query_multiple_times()
    test_with_original_vectorstore()