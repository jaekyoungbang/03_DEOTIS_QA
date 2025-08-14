#!/usr/bin/env python3
"""
단기 카드 대출 관련 내용 검색 테스트
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.embeddings import EmbeddingManager
from models.vectorstore import VectorStoreManager

def search_test():
    """단기 카드 대출 관련 검색 테스트"""
    
    # 초기화
    embedding_manager = EmbeddingManager()
    vectorstore_manager = VectorStoreManager(embedding_manager.get_embeddings())
    
    # 검색 쿼리들
    queries = [
        "단기 카드 대출 이용방법",
        "단기카드대출",
        "카드대출",
        "현금서비스",
        "단기대출",
        "신용카드 대출"
    ]
    
    print("="*60)
    print("🔍 단기 카드 대출 관련 검색 테스트")
    print("="*60)
    
    for query in queries:
        print(f"\n📌 검색어: '{query}'")
        print("-"*50)
        
        # 검색 수행
        results = vectorstore_manager.similarity_search_with_score(query, k=3)
        
        if results:
            for i, (doc, score) in enumerate(results, 1):
                print(f"\n[결과 {i}] 관련도: {score:.4f}")
                print(f"출처: {doc.metadata.get('filename', 'Unknown')}")
                print(f"내용: {doc.page_content[:200]}...")
        else:
            print("❌ 검색 결과 없음")
    
    print("\n" + "="*60)
    print("✅ 검색 테스트 완료")
    print("="*60)

if __name__ == "__main__":
    search_test()