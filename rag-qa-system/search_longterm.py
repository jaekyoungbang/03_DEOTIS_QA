#!/usr/bin/env python3
"""
장기카드대출 관련 내용 검색 테스트
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.embeddings import EmbeddingManager
from models.vectorstore import VectorStoreManager

def search_longterm_loan():
    """장기카드대출 관련 내용 검색"""
    
    # 초기화
    embedding_manager = EmbeddingManager()
    vectorstore_manager = VectorStoreManager(embedding_manager.get_embeddings())
    
    # 검색 쿼리들
    queries = [
        "장기카드대출",
        "카드론",
        "장기 카드 대출",
        "BC바로카드",
        "페이북APP",
        "5000만원",
        "60개월"
    ]
    
    print("="*60)
    print("🔍 장기카드대출(카드론) 관련 검색 테스트")
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
                print(f"내용: {doc.page_content[:300]}...")
                
                # 장기카드대출이나 카드론 키워드가 직접 포함된 경우 강조
                if "장기카드대출" in doc.page_content or "카드론" in doc.page_content:
                    print("⭐ 직접 키워드 매칭!")
        else:
            print("❌ 검색 결과 없음")
    
    print("\n" + "="*60)
    print("📊 전체 문서 수:", vectorstore_manager.get_document_count())
    print("="*60)

if __name__ == "__main__":
    search_longterm_loan()