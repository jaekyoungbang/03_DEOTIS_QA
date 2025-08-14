# Redis 사용 가이드 - 5회 미만 데이터 확인 방법

## Redis 실행 및 연결

### 1. Redis 서버 실행
```cmd
# rag-qa-system 폴더에서
start_redis.bat
```

### 2. Redis CLI 접속
```cmd
# 새로운 CMD 창에서
cd rag-qa-system/redis
redis-cli.exe

# 또는 직접 경로로
redis-cli -h 127.0.0.1 -p 6379
```

## 캐시 데이터 확인 명령어

### 1. 전체 키 목록 보기
```redis
# 모든 키 보기
KEYS *

# RAG 관련 키만 보기
KEYS rag:*

# 질문 캐시만 보기
KEYS rag:query:*

# 조회수 데이터만 보기
KEYS rag:hits:*
```

### 2. 특정 질문 데이터 확인
```redis
# 특정 질문의 캐시 내용 보기
GET rag:query:해시값

# 특정 질문의 조회수 보기
GET rag:hits:해시값

# 키의 TTL (남은 시간) 확인
TTL rag:query:해시값
```

### 3. 데이터베이스 통계
```redis
# Redis 정보 보기
INFO

# 키 개수 확인
DBSIZE

# 메모리 사용량
INFO memory
```

## 실제 사용 예시

### 질문별 데이터 확인 방법

1. **모든 질문 캐시 보기**:
```redis
127.0.0.1:6379> KEYS rag:query:*
1) "rag:query:a1b2c3d4e5f6..."
2) "rag:query:f6e5d4c3b2a1..."
```

2. **특정 질문 내용 확인**:
```redis
127.0.0.1:6379> GET rag:query:a1b2c3d4e5f6...
"{\"answer\":\"장기카드대출은...\",\"similarity_search\":{...}}"
```

3. **조회수 확인**:
```redis
127.0.0.1:6379> GET rag:hits:a1b2c3d4e5f6...
"3"
```

4. **TTL 확인 (초 단위)**:
```redis
127.0.0.1:6379> TTL rag:query:a1b2c3d4e5f6...
85634  # 약 23.7시간 남음
```

## 데이터 관리 명령어

### 1. 특정 데이터 삭제
```redis
# 특정 질문 캐시 삭제
DEL rag:query:해시값

# 특정 조회수 데이터 삭제
DEL rag:hits:해시값
```

### 2. 전체 캐시 삭제
```redis
# 주의: 모든 데이터 삭제됨
FLUSHALL

# 현재 DB만 삭제
FLUSHDB
```

### 3. 패턴별 삭제
```redis
# RAG 관련 모든 데이터 삭제 (Linux/Mac)
redis-cli --scan --pattern rag:* | xargs redis-cli del

# Windows에서는 PowerShell 사용
redis-cli KEYS rag:* | ForEach-Object { redis-cli DEL $_ }
```

## 실시간 모니터링

### 1. 실시간 명령어 모니터링
```redis
MONITOR
```

### 2. 실시간 통계 보기
```redis
# 1초마다 INFO 출력
redis-cli --stat
```

## 5회 미만 데이터 확인 스크립트

### Windows용 배치 파일 (check_redis.bat)
```batch
@echo off
echo Redis 5회 미만 데이터 확인...
echo.

redis-cli --eval lua_scripts/check_cache.lua
pause
```

### Lua 스크립트 (lua_scripts/check_cache.lua)
```lua
local keys = redis.call('KEYS', 'rag:hits:*')
local result = {}

for i=1, #keys do
    local hits = redis.call('GET', keys[i])
    if tonumber(hits) < 5 then
        local query_key = string.gsub(keys[i], 'rag:hits:', 'rag:query:')
        local query_data = redis.call('GET', query_key)
        local ttl = redis.call('TTL', query_key)
        
        table.insert(result, {
            key = keys[i],
            hits = hits,
            ttl = ttl,
            has_data = query_data and "YES" or "NO"
        })
    end
end

return result
```

## 주의사항

1. **Redis CLI 종료**: `EXIT` 또는 `Ctrl+C`
2. **데이터 백업**: 중요한 데이터는 `BGSAVE` 명령으로 백업
3. **메모리 모니터링**: `INFO memory`로 메모리 사용량 확인
4. **TTL 설정**: 24시간(86400초) 후 자동 삭제됨

## 트러블슈팅

### Redis 연결 실패 시
```cmd
# Redis 서버 상태 확인
tasklist | findstr redis

# 포트 사용 확인
netstat -an | findstr :6379

# Redis 서비스 재시작
taskkill /f /im redis-server.exe
start_redis.bat
```