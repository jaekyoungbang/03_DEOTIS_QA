# Redis CMD 접속 및 조회 가이드 (순서대로)

## 🚀 1단계: Redis 서버 실행

### 방법 1: 배치 파일 사용 (권장)
```cmd
cd D:\99_DEOTIS_QA_SYSTEM\03_DEOTIS_QA\rag-qa-system
start_redis.bat
```

### 방법 2: 직접 실행
```cmd
cd D:\99_DEOTIS_QA_SYSTEM\03_DEOTIS_QA\rag-qa-system\redis
redis-server.exe ..\redis\redis.conf
```

**✅ 성공 시 출력:**
```
[PID] Server initialized
[PID] Ready to accept connections
```

---

## 🔌 2단계: Redis CLI 접속

### **새로운 CMD 창 열기** (중요: 서버는 계속 실행상태)
```cmd
cd D:\99_DEOTIS_QA_SYSTEM\03_DEOTIS_QA\rag-qa-system\redis
redis-cli.exe
```

**✅ 성공 시 프롬프트:**
```
127.0.0.1:6379>
```

### 연결 테스트
```redis
127.0.0.1:6379> PING
PONG
```

---

## 📊 3단계: 기본 조회 명령어 (순서대로)

### 3-1. 전체 현황 파악
```redis
# 현재 저장된 모든 키 개수
127.0.0.1:6379> DBSIZE
(integer) 15

# 메모리 사용량 확인
127.0.0.1:6379> INFO memory
# used_memory_human:2.51M
# used_memory_peak_human:2.51M
```

### 3-2. RAG 관련 데이터 확인
```redis
# 모든 RAG 관련 키 보기
127.0.0.1:6379> KEYS rag:*
1) "rag:query:a1b2c3d4e5f6..."
2) "rag:hits:a1b2c3d4e5f6..."
3) "rag:query:f6e5d4c3b2a1..."
4) "rag:hits:f6e5d4c3b2a1..."

# 질문 캐시만 보기
127.0.0.1:6379> KEYS rag:query:*
1) "rag:query:a1b2c3d4e5f6..."
2) "rag:query:f6e5d4c3b2a1..."

# 조회수 데이터만 보기
127.0.0.1:6379> KEYS rag:hits:*
1) "rag:hits:a1b2c3d4e5f6..."
2) "rag:hits:f6e5d4c3b2a1..."
```

---

## 🔍 4단계: 상세 데이터 조회 (순서대로)

### 4-1. 특정 질문의 조회수 확인
```redis
# 조회수 확인 (5회 미만이면 Redis에 있음)
127.0.0.1:6379> GET rag:hits:a1b2c3d4e5f6...
"3"
```

### 4-2. 특정 질문의 캐시 내용 확인
```redis
# 캐시된 답변 내용 보기
127.0.0.1:6379> GET rag:query:a1b2c3d4e5f6...
"{\"answer\":\"장기카드대출은 카드론과 같은 의미로...\",\"similarity_search\":{\"query\":\"장기카드대출\",\"total_results\":8}}"
```

### 4-3. TTL (남은 시간) 확인
```redis
# 캐시 만료까지 남은 시간 (초 단위)
127.0.0.1:6379> TTL rag:query:a1b2c3d4e5f6...
85634  # 약 23.7시간 남음

# 조회수 TTL 확인
127.0.0.1:6379> TTL rag:hits:a1b2c3d4e5f6...
604634  # 약 7일 남음
```

---

## 📈 5단계: 실시간 모니터링

### 5-1. 실시간 명령어 모니터링
```redis
127.0.0.1:6379> MONITOR
OK
# 이후 모든 Redis 명령어가 실시간으로 출력됨
# 중지하려면 Ctrl+C
```

### 5-2. 새 CMD 창에서 통계 모니터링
```cmd
cd D:\99_DEOTIS_QA_SYSTEM\03_DEOTIS_QA\rag-qa-system\redis
redis-cli.exe --stat
```

**출력 예시:**
```
------- data ------ --------------------- load -------------------- - child -
keys       mem      clients blocked requests            connections
15         2.51M    1       0       1547 (+47)          7
```

---

## 🎯 6단계: 5회 미만 데이터 찾기

### 방법 1: 수동 검색
```redis
# 모든 조회수 키 순회
127.0.0.1:6379> KEYS rag:hits:*
1) "rag:hits:a1b2c3d4e5f6..."
2) "rag:hits:f6e5d4c3b2a1..."

# 각각의 조회수 확인
127.0.0.1:6379> GET rag:hits:a1b2c3d4e5f6...
"3"  # 5회 미만!

127.0.0.1:6379> GET rag:hits:f6e5d4c3b2a1...
"7"  # 5회 이상 (이미 인기 질문 DB로 이동됨)
```

### 방법 2: Lua 스크립트 사용
```redis
127.0.0.1:6379> EVAL "
local keys = redis.call('KEYS', 'rag:hits:*')
local result = {}
for i=1, #keys do
    local hits = redis.call('GET', keys[i])
    if tonumber(hits) < 5 then
        local query_key = string.gsub(keys[i], 'rag:hits:', 'rag:query:')
        local ttl = redis.call('TTL', query_key)
        table.insert(result, {key=keys[i], hits=hits, ttl=ttl})
    end
end
return result
" 0
```

---

## 🗑️ 7단계: 데이터 관리 (필요시)

### 특정 데이터 삭제
```redis
# 특정 질문 캐시 삭제
127.0.0.1:6379> DEL rag:query:a1b2c3d4e5f6...
(integer) 1

# 특정 조회수 삭제
127.0.0.1:6379> DEL rag:hits:a1b2c3d4e5f6...
(integer) 1
```

### 패턴별 삭제 (주의!)
```redis
# RAG 관련 모든 데이터 삭제 (신중히!)
127.0.0.1:6379> EVAL "
local keys = redis.call('KEYS', 'rag:*')
for i=1, #keys do
    redis.call('DEL', keys[i])
end
return #keys
" 0
```

---

## 🚪 8단계: 종료

### Redis CLI 종료
```redis
127.0.0.1:6379> EXIT
```
또는 `Ctrl+C`

### Redis 서버 종료
```cmd
# Redis 서버 실행 중인 CMD 창에서 Ctrl+C
# 또는 작업 관리자에서 redis-server.exe 종료
```

---

## 🚨 트러블슈팅

### Redis 연결 안됨
```cmd
# 포트 6379 사용 중인지 확인
netstat -an | findstr :6379

# Redis 프로세스 확인
tasklist | findstr redis

# 프로세스 강제 종료
taskkill /f /im redis-server.exe
```

### 데이터가 안 보임
```redis
# 올바른 데이터베이스 선택 확인
127.0.0.1:6379> SELECT 0
OK

# 현재 DB 확인
127.0.0.1:6379> INFO keyspace
# db0:keys=15,expires=15,avg_ttl=82634891
```

---

## 📝 CMD에서 사용할 스크립트

### check_redis.bat 생성
```batch
@echo off
echo ============================================
echo Redis 5회 미만 데이터 체크
echo ============================================
echo.

cd /d D:\99_DEOTIS_QA_SYSTEM\03_DEOTIS_QA\rag-qa-system\redis

echo 1. Redis 연결 테스트...
redis-cli.exe ping

echo.
echo 2. 전체 키 개수...
redis-cli.exe DBSIZE

echo.
echo 3. RAG 관련 키 목록...
redis-cli.exe KEYS rag:*

echo.
echo 4. 조회수 5회 미만 질문 찾기...
redis-cli.exe EVAL "local keys = redis.call('KEYS', 'rag:hits:*'); local result = {}; for i=1, #keys do local hits = redis.call('GET', keys[i]); if tonumber(hits) < 5 then table.insert(result, {key=keys[i], hits=hits}); end; end; return result" 0

echo.
pause
```

**이제 순서대로 따라하면 Redis의 5회 미만 데이터를 완벽하게 확인할 수 있습니다!**