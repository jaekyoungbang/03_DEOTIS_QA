import sqlite3
import os

# popular_questions 테이블 생성 스크립트
db_path = 'data/cache/popular_cache.db'

# 기존 DB 백업
if os.path.exists(db_path):
    import shutil
    shutil.copy(db_path, db_path + '.backup')
    print(f"✅ 기존 DB 백업: {db_path}.backup")

# DB 연결
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# popular_questions 테이블 생성
cursor.execute('''
    CREATE TABLE IF NOT EXISTS popular_questions (
        query_hash TEXT PRIMARY KEY,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        similarity_data TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        hit_count INTEGER DEFAULT 5,
        llm_model TEXT,
        vector_count INTEGER
    )
''')

# 인덱스 생성
cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_hit_count 
    ON popular_questions(hit_count DESC)
''')

cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_last_accessed 
    ON popular_questions(last_accessed)
''')

# 기존 query_cache 테이블에서 5회 이상 조회된 데이터 마이그레이션
cursor.execute('''
    SELECT query_hash, query, response, similarity_data, hit_count, llm_model, vector_count
    FROM query_cache
    WHERE hit_count >= 5
''')

migrated_count = 0
for row in cursor.fetchall():
    query_hash, question, response, similarity_data, hit_count, llm_model, vector_count = row
    
    # response에서 answer 추출
    try:
        import json
        response_dict = json.loads(response)
        answer = response_dict.get('answer', response)
    except:
        answer = response
    
    cursor.execute('''
        INSERT OR IGNORE INTO popular_questions 
        (query_hash, question, answer, similarity_data, hit_count, llm_model, vector_count)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (query_hash, question, answer, similarity_data, hit_count, llm_model, vector_count))
    
    migrated_count += 1

conn.commit()

# 테이블 확인
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print(f"\n📊 테이블 목록: {tables}")

cursor.execute("SELECT COUNT(*) FROM popular_questions")
count = cursor.fetchone()[0]
print(f"✅ popular_questions 테이블 생성 완료 - {count}개 데이터")
print(f"✅ {migrated_count}개 데이터 마이그레이션 완료")

# 상위 5개 인기 질문 표시
cursor.execute('''
    SELECT question, hit_count 
    FROM popular_questions 
    ORDER BY hit_count DESC 
    LIMIT 5
''')

print("\n🔥 인기 질문 TOP 5:")
for i, (question, hit_count) in enumerate(cursor.fetchall(), 1):
    print(f"{i}. {question[:50]}... ({hit_count}회)")

conn.close()