import sys
sys.path.append('.')

from app import app, get_rag_chain
from services.cache_factory import CacheFactory
import json

# 테스트 요청
test_query = "장기카드대출이란?"

print("🔍 디버그 시작...")

# 캐시 매니저 확인
cache_manager = CacheFactory.get_cache_manager()
print(f"📌 캐시 매니저 타입: {type(cache_manager)}")

# RAG 체인 확인
rag_chain = get_rag_chain()
print(f"📌 RAG 체인: {rag_chain is not None}")

# 캐시에서 직접 조회
try:
    cached = cache_manager.get(test_query, "gpt-4o-mini")
    if cached:
        print(f"✅ 캐시 조회 성공")
        print(f"   - 캐시 소스: {cached.get('_cache_source')}")
        print(f"   - 조회수: {cached.get('_hit_count')}")
    else:
        print("❌ 캐시에 없음")
except Exception as e:
    print(f"❌ 캐시 조회 에러: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

# API 엔드포인트 직접 테스트
print("\n🔍 API 엔드포인트 테스트...")
with app.test_client() as client:
    response = client.post('/api/rag/chat', 
        json={'message': test_query},
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"📌 응답 코드: {response.status_code}")
    if response.status_code == 500:
        print(f"❌ 에러 응답: {response.get_data(as_text=True)}")
    else:
        data = response.get_json()
        print(f"✅ 정상 응답: {data.get('_cache_source')}")