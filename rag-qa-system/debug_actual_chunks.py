#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
실제 저장된 청크 내용 확인
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.vectorstore import DualVectorStoreManager
from models.embeddings import EmbeddingManager

def debug_actual_chunks():
    """실제 저장된 청크들 확인"""
    
    print("=== 실제 저장된 청크 내용 확인 ===\n")
    
    # 초기화
    embedding_manager = EmbeddingManager()
    dual_manager = DualVectorStoreManager(embedding_manager.get_embeddings())
    
    # Basic 컬렉션의 모든 청크 확인
    print("1. Basic 컬렉션 청크 분석:")
    all_basic = dual_manager.similarity_search("", "basic", k=100)  # 빈 검색어로 모든 청크 가져오기
    
    title_only_chunks = []
    normal_chunks = []
    
    for i, doc in enumerate(all_basic):
        content = doc.page_content.strip()
        if len(content) < 50:
            title_only_chunks.append((i, content, len(content)))
        else:
            normal_chunks.append((i, content[:100], len(content)))
    
    print(f"총 청크 수: {len(all_basic)}")
    print(f"짧은 청크 (50자 미만): {len(title_only_chunks)}개")
    print(f"일반 청크 (50자 이상): {len(normal_chunks)}개")
    
    print("\n📋 짧은 청크들:")
    for i, content, length in title_only_chunks[:10]:  # 상위 10개만
        print(f"  {i+1}: [{length}자] {repr(content)}")
    
    print("\n📋 일반 청크들 (상위 5개):")
    for i, content, length in normal_chunks[:5]:
        print(f"  {i+1}: [{length}자] {repr(content)}...")
    
    # 특정 키워드 검색
    print("\n" + "="*50)
    print("2. '민원접수' 키워드 포함 청크 상세 분석:")
    
    complaint_chunks = [doc for doc in all_basic if "민원접수" in doc.page_content]
    print(f"'민원접수' 포함 청크: {len(complaint_chunks)}개")
    
    for i, doc in enumerate(complaint_chunks, 1):
        content = doc.page_content
        print(f"\n청크 {i}: [{len(content)}자]")
        print(f"내용: {repr(content[:200])}...")
        
        # 정확히 '[민원접수방법 안내]'인지 확인
        if content.strip() == "[민원접수방법 안내]":
            print("  🎯 정확히 제목 전용 청크!")
        elif content.startswith("[민원접수방법 안내]"):
            print("  🔍 제목으로 시작하는 청크")
        else:
            print("  📄 내용 포함 청크")

if __name__ == "__main__":
    debug_actual_chunks()