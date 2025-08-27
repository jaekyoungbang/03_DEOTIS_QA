#!/usr/bin/env python3
"""
벡터DB에 특정 내용이 있는지 확인하는 스크립트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.dual_vectorstore import DualVectorStoreManager
from models.embeddings import EmbeddingManager

def check_content_in_vectordb():
    """벡터DB에서 특정 내용 검색 확인"""
    print("🔍 벡터DB 내용 확인 시작\n")
    
    # 시스템 초기화
    embedding_manager = EmbeddingManager()
    vectorstore_manager = DualVectorStoreManager(embedding_manager.get_embeddings())
    
    # 사용자가 제공한 텍스트의 핵심 키워드들로 검색
    search_queries = [
        "BC카드 고객센터 1588-4000",
        "카드 분실 도난 사고보상",
        "민원접수방법 안내",
        "서면 접수 내용증명",
        "FAX 02-500-3120",
        "인터넷 접수 전자민원",
        "카드발급 상담사",
        "미성년자 거래정지",
        "카드의 발행 배송 비용"
    ]
    
    print("="*80)
    print("🔍 사용자 제공 내용이 벡터DB에 있는지 검색")
    print("="*80)
    
    for i, query in enumerate(search_queries, 1):
        print(f"\n🔍 검색 {i}: \"{query}\"")
        print("-" * 60)
        
        # Basic 컬렉션 (s3 폴더) 검색
        print("📁 Basic 컬렉션 (s3) 검색 결과:")
        try:
            basic_results = vectorstore_manager.similarity_search_with_score(query, "basic", k=3)
            if basic_results:
                for j, (doc, score) in enumerate(basic_results, 1):
                    print(f"   {j}. 유사도: {score:.2%}")
                    print(f"      출처: {doc.metadata.get('source', 'unknown')}")
                    print(f"      미리보기: {doc.page_content[:200]}...")
                    
                    # 정확한 텍스트 매칭 확인
                    if "1588-4000" in doc.page_content:
                        print(f"      ✅ 고객센터 번호 발견!")
                    if "민원접수방법" in doc.page_content:
                        print(f"      ✅ 민원접수방법 발견!")
                    if "02-500-3120" in doc.page_content:
                        print(f"      ✅ FAX 번호 발견!")
                    if "카드발급 상담사" in doc.page_content:
                        print(f"      ✅ 카드발급 상담사 발견!")
                    print()
            else:
                print("   검색 결과 없음")
        except Exception as e:
            print(f"   오류: {e}")
        
        # Custom 컬렉션 (s3-chunking 폴더) 검색
        print("📁 Custom 컬렉션 (s3-chunking) 검색 결과:")
        try:
            custom_results = vectorstore_manager.similarity_search_with_score(query, "custom", k=3)
            if custom_results:
                for j, (doc, score) in enumerate(custom_results, 1):
                    print(f"   {j}. 유사도: {score:.2%}")
                    print(f"      출처: {doc.metadata.get('source', 'unknown')}")
                    print(f"      미리보기: {doc.page_content[:200]}...")
                    
                    # 정확한 텍스트 매칭 확인
                    if "1588-4000" in doc.page_content:
                        print(f"      ✅ 고객센터 번호 발견!")
                    if "민원접수방법" in doc.page_content:
                        print(f"      ✅ 민원접수방법 발견!")
                    if "02-500-3120" in doc.page_content:
                        print(f"      ✅ FAX 번호 발견!")
                    if "카드발급 상담사" in doc.page_content:
                        print(f"      ✅ 카드발급 상담사 발견!")
                    print()
            else:
                print("   검색 결과 없음")
        except Exception as e:
            print(f"   오류: {e}")
    
    print("\n" + "="*80)
    print("🔍 전체 텍스트 검색 (사용자 제공 내용 전체)")
    print("="*80)
    
    # 사용자가 제공한 전체 텍스트로 검색
    full_text_query = "별도의 안내가 필요하시면 BC카드 고객센터 1588-4000으로 문의해 주시기 바랍니다 카드 분실 도난 사고보상 처리 안내"
    
    print(f"🔍 전체 텍스트 검색: \"{full_text_query[:50]}...\"")
    
    # Basic에서 검색
    print("\n📁 Basic 컬렉션 전체 검색:")
    basic_full = vectorstore_manager.similarity_search_with_score(full_text_query, "basic", k=5)
    for i, (doc, score) in enumerate(basic_full, 1):
        print(f"   {i}. 유사도: {score:.2%}")
        print(f"      파일: {doc.metadata.get('filename', 'unknown')}")
        print(f"      내용: {doc.page_content[:300]}...")
        print()
    
    # Custom에서 검색  
    print("📁 Custom 컬렉션 전체 검색:")
    custom_full = vectorstore_manager.similarity_search_with_score(full_text_query, "custom", k=5)
    for i, (doc, score) in enumerate(custom_full, 1):
        print(f"   {i}. 유사도: {score:.2%}")
        print(f"      파일: {doc.metadata.get('filename', 'unknown')}")  
        print(f"      내용: {doc.page_content[:300]}...")
        print()
    
    print("\n🎯 결론:")
    
    # 최고 유사도 확인
    all_scores = []
    if basic_full:
        all_scores.extend([score for _, score in basic_full])
    if custom_full:
        all_scores.extend([score for _, score in custom_full])
    
    if all_scores:
        max_score = max(all_scores)
        print(f"   최고 유사도: {max_score:.2%}")
        if max_score >= 0.8:
            print("   ✅ 해당 내용이 벡터DB에 충분히 존재합니다!")
        elif max_score >= 0.6:
            print("   🟡 해당 내용이 벡터DB에 부분적으로 존재합니다.")
        else:
            print("   ❌ 해당 내용이 벡터DB에 없거나 매우 유사도가 낮습니다.")
    else:
        print("   ❌ 검색 결과가 없습니다.")

if __name__ == "__main__":
    check_content_in_vectordb()