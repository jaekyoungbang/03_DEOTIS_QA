#!/usr/bin/env python3
"""
캐시 데이터 확인 스크립트
"""

import sqlite3
import os
import json

def check_popular_cache():
    """popular_questions 테이블 확인"""
    print("=== 인기 질문 캐시 (RDB) 확인 ===")
    
    db_path = 'data/cache/popular_cache.db'
    
    if not os.path.exists(db_path):
        print(f"❌ 데이터베이스 파일이 없습니다: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 전체 테이블 목록
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"📋 테이블 목록: {[table[0] for table in tables]}")
        
        # popular_questions 테이블 확인
        if ('popular_questions',) in tables:
            cursor.execute("SELECT COUNT(*) FROM popular_questions")
            total_count = cursor.fetchone()[0]
            print(f"📊 총 인기 질문 수: {total_count}개")
            
            # 장기카드대출 관련 검색
            cursor.execute("""
                SELECT question, hit_count, last_accessed 
                FROM popular_questions 
                WHERE question LIKE '%장기%' OR question LIKE '%카드대출%'
                ORDER BY hit_count DESC
            """)
            
            card_loan_results = cursor.fetchall()
            if card_loan_results:
                print("\n🎯 '장기카드대출' 관련 질문:")
                for i, (question, hit_count, last_accessed) in enumerate(card_loan_results, 1):
                    print(f"  {i}. {question[:50]}...")
                    print(f"     조회수: {hit_count}, 마지막 접근: {last_accessed}")
            else:
                print("\n❌ '장기카드대출' 관련 질문 없음")
            
            # 상위 인기 질문 5개
            cursor.execute("""
                SELECT question, hit_count, last_accessed 
                FROM popular_questions 
                ORDER BY hit_count DESC 
                LIMIT 5
            """)
            
            top_questions = cursor.fetchall()
            if top_questions:
                print("\n🔥 인기 질문 TOP 5:")
                for i, (question, hit_count, last_accessed) in enumerate(top_questions, 1):
                    print(f"  {i}. {question[:50]}... (조회수: {hit_count})")
        else:
            print("❌ popular_questions 테이블이 없습니다")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 데이터베이스 조회 오류: {e}")

def check_query_cache():
    """query_cache 테이블 확인"""
    print("\n=== 일반 쿼리 캐시 (RDB) 확인 ===")
    
    db_path = 'data/cache/popular_cache.db'
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # query_cache 테이블 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='query_cache';")
        if cursor.fetchone():
            cursor.execute("SELECT COUNT(*) FROM query_cache")
            cache_count = cursor.fetchone()[0]
            print(f"📊 일반 캐시 항목 수: {cache_count}개")
        else:
            print("❌ query_cache 테이블이 없습니다")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 쿼리 캐시 조회 오류: {e}")

def check_cache_structure():
    """캐시 시스템 구조 분석"""
    print("\n=== 캐시 시스템 구조 분석 ===")
    
    print("💡 하이브리드 캐시 시스템:")
    print("  1. Redis (임시) - 24시간 TTL")
    print("  2. RDB popular_questions (영구) - 5회 이상 조회")
    print("  3. RDB query_cache (일반) - 365일 TTL")
    
    print("\n🔍 '전체 캐시 초기화' 동작:")
    print("  - Redis: 모든 키 삭제")
    print("  - popular_questions: 테이블 유지 (영구 저장)")
    print("  - query_cache: 모든 항목 삭제")
    
    print("\n❓ '장기카드대출'이 바로 나오는 이유:")
    print("  → popular_questions 테이블에 저장되어 있음 (영구)")

if __name__ == "__main__":
    print("캐시 데이터 분석 시작...")
    print("=" * 50)
    
    check_popular_cache()
    check_query_cache() 
    check_cache_structure()
    
    print("\n" + "=" * 50)
    print("분석 완료!")
    
    input("\n계속하려면 Enter를 누르세요...")