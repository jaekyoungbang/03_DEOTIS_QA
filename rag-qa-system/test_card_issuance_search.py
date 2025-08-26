#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
카드발급기준 A-2 섹션 검색 문제 분석
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.rag_chain import RAGChain
from models.vectorstore import DualVectorStoreManager
from models.embeddings import EmbeddingManager

def search_for_a2_section():
    print("=== 카드발급기준 A-2 섹션 검색 분석 ===\n")
    
    # RAGChain 초기화
    rag = RAGChain()
    
    # 테스트할 검색어들
    test_queries = [
        "카드발급기준",
        "A-2",
        "A-2. [카드발급기준]",
        "금융당국에서 마련한 신용카드 발급",
        "월 가처분 소득 50만원",
        "개인신용평점의 상위 누적구성비가 93%",
        "장기연체가능성이 0.65%",
        "소득 안정성 직업 안정성",
        "복수카드 사용",
        "카드발급업무는 신용대출심사의 성격"
    ]
    
    print("1. 다양한 검색어로 A-2 섹션 찾기:\n")
    
    # DualVectorStoreManager 사용
    embedding_manager = EmbeddingManager()
    dual_manager = DualVectorStoreManager(embedding_manager.get_embeddings())
    
    for query in test_queries:
        print(f"\n검색어: '{query}'")
        print("-" * 50)
        
        # basic 컬렉션 검색
        basic_results = dual_manager.similarity_search_with_score(query, "basic", k=5)
        print(f"\n[기본 청킹 결과]")
        
        found_a2 = False
        for i, (doc, score) in enumerate(basic_results, 1):
            content = doc.page_content
            if "A-2" in content or "카드발급업무는 신용대출심사" in content:
                found_a2 = True
                print(f"\n✅ 순위 {i}: 점수 {score:.2%}")
                print(f"파일: {doc.metadata.get('source', 'Unknown')}")
                print(f"청킹 전략: {doc.metadata.get('chunking_strategy', 'Unknown')}")
                
                # A-2 섹션 전체가 포함되어 있는지 확인
                if "A-2. [카드발급기준]" in content:
                    print("🎯 A-2 섹션 제목 발견!")
                if "카드발급업무는 신용대출심사의 성격" in content:
                    print("🎯 A-2 섹션 시작 부분 발견!")
                if "1) 카드발급절차" in content:
                    print("🎯 A-2 섹션 마지막 부분 발견!")
                    
                print(f"\n내용 미리보기 (처음 500자):")
                print(content[:500])
                print(f"\n전체 길이: {len(content)}자")
                
                # A-2 섹션의 전체 내용이 포함되어 있는지 확인
                key_phrases = [
                    "카드발급업무는 신용대출심사의 성격",
                    "금융당국에서 마련한",
                    "월 가처분 소득 50만원",
                    "개인신용평점의 상위 누적구성비가 93%",
                    "소득 안정성",
                    "복수카드 사용",
                    "카드발급절차"
                ]
                
                print("\n핵심 문구 포함 여부:")
                for phrase in key_phrases:
                    if phrase in content:
                        print(f"  ✅ {phrase}")
                    else:
                        print(f"  ❌ {phrase}")
        
        if not found_a2:
            print(f"\n❌ A-2 섹션을 찾지 못했습니다.")
        
        # custom 컬렉션도 확인
        custom_results = dual_manager.similarity_search_with_score(query, "custom", k=5)
        print(f"\n[커스텀 청킹 결과]")
        
        for i, (doc, score) in enumerate(custom_results, 1):
            content = doc.page_content
            if "A-2" in content or "카드발급업무는 신용대출심사" in content:
                print(f"\n✅ 순위 {i}: 점수 {score:.2%}")
                print(f"파일: {doc.metadata.get('source', 'Unknown')}")
                print(f"구분자: {doc.metadata.get('delimiter_used', 'Unknown')}")
                print(f"전체 길이: {len(content)}자")
    
    # 2. 원본 파일에서 A-2 섹션 확인
    print("\n\n2. 원본 파일에서 A-2 섹션 존재 여부 확인:")
    print("-" * 50)
    
    # s3 폴더에서 직접 파일 읽기
    s3_path = "/mnt/d/99_DEOTIS_QA_SYSTEM/03_DEOTIS_QA/rag-qa-system/s3"
    target_file = "BC카드(신용카드 업무처리 안내).docx"
    
    # DOCX 파일 읽기
    try:
        from docx import Document
        import os
        
        file_path = os.path.join(s3_path, target_file)
        if os.path.exists(file_path):
            doc = Document(file_path)
            full_text = ""
            for para in doc.paragraphs:
                full_text += para.text + "\n"
            
            # A-2 섹션 찾기
            if "A-2. [카드발급기준]" in full_text:
                print(f"✅ 원본 파일에 A-2 섹션이 존재합니다!")
                
                # A-2 섹션 추출
                start_idx = full_text.find("A-2. [카드발급기준]")
                end_idx = full_text.find("1) 카드발급절차", start_idx)
                if end_idx == -1:
                    end_idx = start_idx + 2000  # 대략적인 길이
                
                a2_section = full_text[start_idx:end_idx]
                print(f"\nA-2 섹션 전체 내용 ({len(a2_section)}자):")
                print("=" * 50)
                print(a2_section)
                print("=" * 50)
            else:
                print(f"❌ 원본 파일에서 A-2 섹션을 찾을 수 없습니다.")
                
                # 비슷한 내용 찾기
                if "카드발급업무는 신용대출심사" in full_text:
                    idx = full_text.find("카드발급업무는 신용대출심사")
                    print(f"\n💡 '카드발급업무는 신용대출심사'로 시작하는 부분 발견:")
                    print(full_text[idx:idx+500])
                    
    except Exception as e:
        print(f"❌ 파일 읽기 실패: {e}")
    
    # 3. 청킹 문제 분석
    print("\n\n3. 청킹 문제 분석:")
    print("-" * 50)
    
    # 모든 문서 조각 확인
    all_docs = dual_manager.similarity_search("", "basic", k=100)
    
    bc_card_docs = [doc for doc in all_docs if "BC카드(신용카드 업무처리 안내)" in doc.metadata.get('source', '')]
    
    print(f"\n'BC카드(신용카드 업무처리 안내).docx' 파일의 청킹 결과:")
    print(f"총 {len(bc_card_docs)}개의 조각으로 분할됨")
    
    # 각 조각의 크기 확인
    for i, doc in enumerate(bc_card_docs[:10], 1):
        content = doc.page_content
        print(f"\n조각 {i}: {len(content)}자")
        print(f"시작: {content[:100]}...")
        if "A-2" in content:
            print("🎯 A-2 포함!")
        if "카드발급업무는 신용대출심사" in content:
            print("🎯 A-2 섹션 내용 포함!")

if __name__ == "__main__":
    search_for_a2_section()