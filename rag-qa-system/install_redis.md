# Redis 설치 가이드

## Windows용 Redis 설치

### 방법 1: 직접 다운로드 (권장)

1. **Redis 다운로드**:
   - https://github.com/tporadowski/redis/releases 방문
   - 최신 버전의 `Redis-x64-X.X.XX.zip` 다운로드

2. **압축 해제**:
   - 다운로드한 파일을 `rag-qa-system/redis/` 폴더에 압축 해제
   - 다음 파일들이 있어야 함:
     - `redis-server.exe`
     - `redis-cli.exe`
     - `redis.windows.conf`

3. **Redis 실행**:
   ```cmd
   # rag-qa-system 폴더에서 실행
   start_redis.bat
   ```

### 방법 2: PowerShell로 자동 다운로드

```powershell
# rag-qa-system 폴더에서 실행 (관리자 권한)
cd redis
Invoke-WebRequest -Uri "https://download.redis.io/redis-stable/src/redis-7.2.0.tar.gz" -OutFile "redis.tar.gz"
# 압축 해제 후 빌드 필요
```

### 방법 3: WSL Ubuntu에서 설치

```bash
# WSL에서 실행
sudo apt update
sudo apt install redis-server

# Redis 시작
sudo service redis-server start

# 상태 확인
redis-cli ping
```

## 설치 확인

Redis가 정상 설치되면:

```cmd
# Redis 서버 실행
start_redis.bat

# 다른 CMD 창에서 테스트
redis-cli ping
# 응답: PONG
```

## Flask 앱에서 Redis 사용

Redis 설치 후 Flask 앱을 재시작하면 자동으로 Redis를 감지하고 사용합니다:

```
✅ Using Hybrid Cache System (Redis + RDB)
   - Redis TTL: 24시간
   - 인기 질문 기준: 5회 이상
   - 문서 변경 감지: 24시간 간격
```