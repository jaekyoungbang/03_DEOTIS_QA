#!/usr/bin/env python3
"""
단기카드대출 관련 전체 내용 확인
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.embeddings import EmbeddingManager
from models.vectorstore import VectorStoreManager

def check_all_content():
    """단기카드대출 키워드가 포함된 모든 내용 찾기"""
    
    # 초기화
    embedding_manager = EmbeddingManager()
    vectorstore_manager = VectorStoreManager(embedding_manager.get_embeddings())
    
    print("="*60)
    print("📝 '단기카드대출' 키워드가 포함된 모든 내용")
    print("="*60)
    
    # 모든 문서에서 단기카드대출 검색
    results = vectorstore_manager.similarity_search("단기카드대출", k=10)
    
    found_contents = []
    for doc in results:
        if "단기카드대출" in doc.page_content or "단기 카드 대출" in doc.page_content:
            found_contents.append(doc)
    
    if found_contents:
        for i, doc in enumerate(found_contents, 1):
            print(f"\n[내용 {i}]")
            print(f"출처: {doc.metadata.get('filename', 'Unknown')}")
            print("-"*50)
            print(doc.page_content)
            print("-"*50)
    else:
        print("❌ '단기카드대출' 키워드가 직접 포함된 내용을 찾지 못했습니다.")
    
    # 현금서비스 관련 내용도 확인
    print("\n" + "="*60)
    print("💰 '현금서비스' 관련 내용")
    print("="*60)
    
    cash_results = vectorstore_manager.similarity_search("현금서비스", k=5)
    for i, doc in enumerate(cash_results, 1):
        if "현금" in doc.page_content or "서비스" in doc.page_content:
            print(f"\n[내용 {i}]")
            print(f"출처: {doc.metadata.get('filename', 'Unknown')}")
            print("-"*30)
            print(doc.page_content[:500])
            print("...")

if __name__ == "__main__":
    check_all_content()