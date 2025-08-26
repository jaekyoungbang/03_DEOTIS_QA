#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.rag_chain import RAGChain

def check_vectordb_chunks():
    """벡터 DB에 저장된 청크들을 분석"""
    
    rag = RAGChain()
    
    print("=== BC카드(카드이용안내).docx 파일의 청크 분석 ===\n")
    
    # BC카드(카드이용안내).docx 파일의 모든 청크 검색
    all_docs = rag.vectorstore_manager.vectorstore.similarity_search("", k=1000)
    
    bc_card_chunks = []
    for doc in all_docs:
        if doc.metadata.get('filename') == 'BC카드(카드이용안내).docx':
            bc_card_chunks.append(doc)
    
    print(f"BC카드(카드이용안내).docx 파일의 총 청크 수: {len(bc_card_chunks)}")
    
    # 회원제 업소 관련 청크 찾기
    membership_chunks = []
    thrifty_chunks = []
    tip_chunks = []
    
    for i, chunk in enumerate(bc_card_chunks):
        content = chunk.page_content
        
        if "회원제" in content and "업소" in content:
            membership_chunks.append((i, chunk))
        
        if "신용카드알뜰이용법" in content:
            thrifty_chunks.append((i, chunk))
            
        if "신용카드 TIP" in content or "/. 신용카드 TIP" in content:
            tip_chunks.append((i, chunk))
    
    print(f"\n회원제 업소 관련 청크: {len(membership_chunks)}개")
    print(f"신용카드알뜰이용법 관련 청크: {len(thrifty_chunks)}개")
    print(f"신용카드 TIP 관련 청크: {len(tip_chunks)}개")
    
    # 각 청크의 내용 출력
    print("\n=== 회원제 업소 관련 청크 내용 ===")
    for idx, (chunk_num, chunk) in enumerate(membership_chunks[:3]):  # 처음 3개만
        print(f"\n청크 #{chunk_num}:")
        print(f"내용: {chunk.page_content[:300]}...")
        print(f"메타데이터: {chunk.metadata}")
    
    print("\n\n=== 신용카드알뜰이용법 관련 청크 내용 ===")
    for idx, (chunk_num, chunk) in enumerate(thrifty_chunks[:3]):  # 처음 3개만
        print(f"\n청크 #{chunk_num}:")
        print(f"내용: {chunk.page_content[:300]}...")
        print(f"메타데이터: {chunk.metadata}")
    
    # 청킹 전략 확인
    print("\n\n=== 청킹 전략 분석 ===")
    # 연속된 청크인지 확인
    if membership_chunks and thrifty_chunks:
        membership_nums = [num for num, _ in membership_chunks]
        thrifty_nums = [num for num, _ in thrifty_chunks]
        
        print(f"회원제 업소 청크 번호: {membership_nums}")
        print(f"알뜰이용법 청크 번호: {thrifty_nums}")
        
        # 두 내용이 같은 청크에 있는지 확인
        same_chunk = set(membership_nums) & set(thrifty_nums)
        if same_chunk:
            print(f"\n⚠️ 회원제 업소와 알뜰이용법이 같은 청크에 포함됨: {same_chunk}")
            for chunk_num in same_chunk:
                chunk = bc_card_chunks[chunk_num]
                print(f"\n문제 청크 #{chunk_num} 전체 내용:")
                print(chunk.page_content)
                print(f"\n청크 크기: {len(chunk.page_content)} 문자")

if __name__ == "__main__":
    check_vectordb_chunks()