#!/usr/bin/env python3
"""
새로운 캐시 시스템 테스트
"""

import requests
import json
import time

def test_cache_system():
    """캐시 시스템 테스트"""
    base_url = "http://localhost:5001"
    test_question = "장기카드대출이란 무엇인가요?"
    
    print("=" * 60)
    print("🧪 새로운 캐시 시스템 테스트")
    print("=" * 60)
    
    # 1. 전체 캐시 초기화
    print("\n1️⃣ 전체 캐시 초기화 (Redis + RDB)")
    try:
        response = requests.post(f"{base_url}/api/admin/clear-cache")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 캐시 초기화 성공: {data}")
        else:
            print(f"❌ 캐시 초기화 실패: {response.status_code}")
    except Exception as e:
        print(f"❌ 캐시 초기화 오류: {e}")
    
    print("\n" + "-" * 40)
    
    # 2. 5번 연속 검색으로 Redis → RDB 이동 테스트
    for i in range(1, 8):  # 7번까지 테스트
        print(f"\n{i}️⃣ {i}번째 검색: {test_question}")
        
        try:
            start_time = time.time()
            response = requests.post(
                f"{base_url}/api/rag/chat",
                json={"question": test_question, "llm_model": "gpt-4o-mini"},
                headers={"Content-Type": "application/json"}
            )
            end_time = time.time()
            
            if response.status_code == 200:
                data = response.json()
                
                # 검색 정보 출력
                cache_source = data.get('_cache_source', 'Unknown')
                search_count = data.get('_search_count', 0)
                from_cache = data.get('_from_cache', False)
                note = data.get('_note', '')
                
                print(f"   📍 검색 경로: {cache_source}")
                print(f"   🔢 총 검색 횟수: {search_count}번")
                print(f"   💾 캐시 사용: {'예' if from_cache else '아니오'}")
                print(f"   ⏱️ 응답 시간: {(end_time - start_time)*1000:.0f}ms")
                print(f"   📝 노트: {note}")
                
                # 특별한 이벤트 표시
                if i == 1:
                    print("   🎉 첫 검색 - RAG에서 실시간 검색")
                elif i == 5:
                    print("   🔄 5회 도달 - Redis → RDB 이동!")
                elif i > 5:
                    print("   🎯 인기 질문 - RDB에서 응답")
                
                # 답변 미리보기
                answer_preview = data.get('answer', '')[:100] + "..." if len(data.get('answer', '')) > 100 else data.get('answer', '')
                print(f"   💬 답변 미리보기: {answer_preview}")
                
            else:
                print(f"   ❌ 검색 실패: {response.status_code}")
                print(f"   📄 응답: {response.text}")
                
        except Exception as e:
            print(f"   ❌ 검색 오류: {e}")
        
        # 잠시 대기
        if i < 7:
            time.sleep(1)
    
    print("\n" + "=" * 60)
    print("✅ 테스트 완료!")
    print("=" * 60)
    
    print("\n📊 예상 결과:")
    print("1~4번째: RAG → Redis → Redis → Redis")
    print("5번째: Redis → RDB 이동")
    print("6~7번째: RDB에서 직접 응답")

if __name__ == "__main__":
    print("서버가 실행 중인지 확인하세요 (http://localhost:5001)")
    input("계속하려면 Enter를 누르세요...")
    
    test_cache_system()
    
    input("\n계속하려면 Enter를 누르세요...")