import sys
sys.path.append('.')

from services.hybrid_cache_manager import HybridCacheManager
import json

# 하이브리드 캐시 매니저 생성
cache = HybridCacheManager()

# 테스트 질문
test_query = "장기카드대출이란?"
test_llm_model = "gpt-4o-mini"

print(f"🔍 테스트 질문: {test_query}")
print(f"🔍 LLM 모델: {test_llm_model}")

# 1. Redis에서 현재 조회수 확인
cache_key = cache._generate_cache_key(test_query, test_llm_model)
redis_hit_key = cache._generate_redis_hit_key(test_query, test_llm_model)

print(f"\n📌 캐시 키: {cache_key}")
print(f"📌 Redis 조회수 키: {redis_hit_key}")

# Redis 조회수 확인
if cache.redis_cache.connected:
    current_hits = cache.redis_cache.redis_client.get(redis_hit_key)
    print(f"\n🔴 Redis 현재 조회수: {current_hits}")
    
    # Redis 캐시 데이터 확인
    redis_data = cache.redis_cache.get(test_query, test_llm_model)
    if redis_data:
        print(f"🔴 Redis 캐시 데이터 존재: {type(redis_data)}")
        print(f"   - 답변 길이: {len(redis_data.get('answer', ''))}")
        print(f"   - 키 목록: {list(redis_data.keys())}")
else:
    print("❌ Redis 연결 안됨")

# 2. SQLite popular_questions 확인
import sqlite3
conn = sqlite3.connect('data/cache/popular_cache.db')
cursor = conn.cursor()

# 테이블 확인
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print(f"\n📊 SQLite 테이블: {tables}")

# popular_questions에서 확인
cursor.execute('''
    SELECT query_hash, hit_count, SUBSTR(question, 1, 50) 
    FROM popular_questions 
    WHERE query_hash = ?
''', (cache_key,))
result = cursor.fetchone()

if result:
    print(f"\n✅ SQLite popular_questions에 존재:")
    print(f"   - 조회수: {result[1]}")
    print(f"   - 질문: {result[2]}...")
else:
    print(f"\n❌ SQLite popular_questions에 없음")

conn.close()

# 3. 수동으로 SQLite로 이동 테스트
if redis_data and current_hits and int(current_hits) >= 5:
    print(f"\n🚀 수동으로 SQLite 이동 시도...")
    try:
        cache._promote_to_popular(test_query, redis_data, test_llm_model, int(current_hits))
        print("✅ SQLite 이동 성공")
        
        # Redis에서 삭제
        removed = cache._remove_from_redis(test_query, test_llm_model)
        print(f"✅ Redis 삭제: {removed}")
    except Exception as e:
        print(f"❌ 에러 발생: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()