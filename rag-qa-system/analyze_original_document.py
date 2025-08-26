#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import docx
import os

def analyze_document_structure():
    """BC카드(카드이용안내).docx 문서의 구조를 분석"""
    
    doc_path = '../s3/BC카드(카드이용안내).docx'
    if not os.path.exists(doc_path):
        print(f"파일을 찾을 수 없습니다: {doc_path}")
        return
    
    doc = docx.Document(doc_path)
    
    # 전체 텍스트를 리스트로 수집
    all_texts = []
    for para in doc.paragraphs:
        if para.text.strip():
            all_texts.append(para.text.strip())
    
    print(f"총 문단 수: {len(all_texts)}")
    
    # "신용카드 TIP" 섹션 찾기
    print("\n=== 신용카드 TIP 섹션 구조 ===")
    tip_start = None
    tip_end = None
    
    for i, text in enumerate(all_texts):
        if text == "/. 신용카드 TIP":
            tip_start = i
            print(f"신용카드 TIP 시작 위치: {i}번째 줄")
        elif tip_start is not None and text.startswith("/") and i > tip_start:
            tip_end = i
            print(f"신용카드 TIP 종료 위치: {i}번째 줄")
            break
    
    if tip_start is not None:
        print(f"\n신용카드 TIP 섹션 내용 ({tip_start} ~ {tip_end or len(all_texts)}):")
        for i in range(tip_start, min(tip_end or len(all_texts), tip_start + 30)):
            print(f"{i}: {all_texts[i]}")
    
    # "회원제 업소" 관련 내용 위치 확인
    print("\n\n=== 회원제 업소 관련 내용 위치 ===")
    for i, text in enumerate(all_texts):
        if "회원제" in text and "업소" in text:
            print(f"\n위치 {i}: {text}")
            # 앞뒤 문맥 확인
            if i > 0:
                print(f"  이전({i-1}): {all_texts[i-1]}")
            if i < len(all_texts) - 1:
                print(f"  다음({i+1}): {all_texts[i+1]}")
    
    # 섹션 간 거리 확인
    print("\n\n=== 섹션 간 거리 분석 ===")
    membership_line = None
    thrifty_line = None
    
    for i, text in enumerate(all_texts):
        if "10) 회원제 업소 등의 경우 신용카드 할부 이용" in text:
            membership_line = i
        if "1) 신용카드알뜰이용법" in text:
            thrifty_line = i
    
    if membership_line is not None and thrifty_line is not None:
        print(f"회원제 업소 섹션: {membership_line}번째 줄")
        print(f"신용카드알뜰이용법 섹션: {thrifty_line}번째 줄")
        print(f"두 섹션 간 거리: {abs(thrifty_line - membership_line)} 줄")
        
        # 두 섹션이 같은 상위 섹션에 속하는지 확인
        print("\n두 섹션 사이의 내용:")
        start = min(membership_line, thrifty_line)
        end = max(membership_line, thrifty_line)
        for i in range(start, end + 1):
            print(f"{i}: {all_texts[i][:100]}...")

if __name__ == "__main__":
    analyze_document_structure()