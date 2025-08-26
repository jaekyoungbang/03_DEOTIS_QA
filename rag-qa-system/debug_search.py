#!/usr/bin/env python3
"""
RAG 검색 문제 디버깅 스크립트
"""

from services.rag_chain import RAGChain
from models.vectorstore import VectorStoreManager
from models.embeddings import EmbeddingManager

def debug_search():
    """RAG 검색 문제를 디버깅합니다."""
    
    print("=== RAG 검색 디버깅 시작 ===\n")
    
    # Initialize
    rag = RAGChain()
    query = '신용카드 업무처리 안내'
    
    print(f"검색 쿼리: {query}")
    print(f"RAG 체인 vectorstore 주소: {id(rag.vectorstore_manager.vectorstore)}")
    print(f"RAG 체인 collection 이름: {rag.vectorstore_manager.vectorstore._collection.name}")
    print(f"RAG 체인 문서 수: {rag.vectorstore_manager.get_document_count()}")
    
    # Test vectorstore_manager directly from RAG chain
    print("\n=== RAG 체인 내부 vectorstore_manager 직접 테스트 ===")
    results = rag.vectorstore_manager.similarity_search_with_score(query, k=3)
    for i, (doc, score) in enumerate(results):
        filename = doc.metadata.get('filename', 'Unknown')
        content_preview = doc.page_content[:100].replace('\n', ' ')
        print(f'{i+1}. 점수: {score:.4f} ({score*100:.2f}%) | 파일: {filename}')
        print(f'   내용: {content_preview}...')
    
    # Test RAG query method manually step by step
    print("\n=== RAG query 메소드 단계별 테스트 ===")
    
    # Mock the RAG query process
    search_mode = "basic"
    
    # Step 1: Get similarity search results (line 294 in rag_chain.py)
    print("1. similarity_search_with_score 호출...")
    similarity_results = rag.vectorstore_manager.similarity_search_with_score(query, k=8)
    print(f"   결과 수: {len(similarity_results)}")
    
    if similarity_results:
        top_result = similarity_results[0]
        doc, score = top_result
        filename = doc.metadata.get('filename', 'Unknown')
        content_preview = doc.page_content[:100].replace('\n', ' ')
        print(f"   최상위 결과: {score:.4f} ({score*100:.2f}%) | 파일: {filename}")
        print(f"   내용: {content_preview}...")
    
    # Step 2: Check what gets put into the response (line 368-378)
    print("\n2. 응답 포맷팅에 사용되는 similarity_results 확인...")
    for i, (doc, score) in enumerate(similarity_results[:3], 1):
        similarity_info = {
            "rank": i,
            "similarity_score": round(score, 4),
            "similarity_percentage": round(score * 100, 2),
            "content_preview": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
            "metadata": doc.metadata,
            "document_source": doc.metadata.get("source", "Unknown"),
            "document_title": doc.metadata.get("title", doc.metadata.get("filename", "Unknown"))
        }
        print(f"   순위 {i}: {similarity_info['similarity_score']} ({similarity_info['similarity_percentage']}%)")
        print(f"   파일: {similarity_info['document_title']}")
        print(f"   내용: {similarity_info['content_preview'][:100]}...")
        
        if '신용카드 업무처리 안내' in similarity_info['content_preview']:
            print("   *** 정확한 매치! ***")

if __name__ == "__main__":
    debug_search()