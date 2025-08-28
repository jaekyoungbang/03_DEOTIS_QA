#!/bin/bash
set -e

# RAG QA 시스템 백업 스크립트
echo "💾 RAG QA 시스템 백업 시작"

# 설정
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="rag-qa-backup_$TIMESTAMP"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"

# 백업 디렉토리 생성
mkdir -p "$BACKUP_PATH"

echo "📋 백업 정보:"
echo "  - 백업 경로: $BACKUP_PATH"
echo "  - 타임스탬프: $TIMESTAMP"

# 1. 데이터베이스 백업
echo "🗃️ 데이터베이스 백업 중..."
mkdir -p "$BACKUP_PATH/databases"

# SQLite 백업
if [ -f "./data/users.db" ]; then
    cp "./data/users.db" "$BACKUP_PATH/databases/users.db"
    echo "✅ Users DB 백업 완료"
fi

if [ -f "./data/feedback.db" ]; then
    cp "./data/feedback.db" "$BACKUP_PATH/databases/feedback.db"
    echo "✅ Feedback DB 백업 완료"
fi

if [ -f "./data/security.db" ]; then
    cp "./data/security.db" "$BACKUP_PATH/databases/security.db"
    echo "✅ Security DB 백업 완료"
fi

# MySQL 백업 (실행 중인 경우)
if docker ps | grep -q "rag-mysql"; then
    echo "📊 MySQL 백업 중..."
    docker exec rag-mysql mysqldump -u qa_user -pqa_password qa_system > "$BACKUP_PATH/databases/mysql_qa_system.sql"
    echo "✅ MySQL 백업 완료"
fi

# 2. 벡터 데이터베이스 백업
echo "🔍 벡터 DB 백업 중..."
mkdir -p "$BACKUP_PATH/vectordb"

if [ -d "./chroma_db" ]; then
    cp -r "./chroma_db" "$BACKUP_PATH/vectordb/"
    echo "✅ ChromaDB 백업 완료"
fi

# 3. 설정 파일 백업
echo "⚙️ 설정 파일 백업 중..."
mkdir -p "$BACKUP_PATH/config"

# 환경 변수 파일들
for env_file in .env.*; do
    if [ -f "$env_file" ]; then
        cp "$env_file" "$BACKUP_PATH/config/"
    fi
done

# Docker 설정
cp docker/docker-compose.yml "$BACKUP_PATH/config/"
cp docker/Dockerfile "$BACKUP_PATH/config/"

# Nginx 설정
if [ -f "docker/nginx.conf" ]; then
    cp docker/nginx.conf "$BACKUP_PATH/config/"
fi

echo "✅ 설정 파일 백업 완료"

# 4. 문서 및 데이터 백업
echo "📚 문서 및 데이터 백업 중..."
mkdir -p "$BACKUP_PATH/documents"

# S3 폴더들
for folder in s3 s3-chunking s3-common; do
    if [ -d "./$folder" ] && [ "$(ls -A ./$folder 2>/dev/null)" ]; then
        cp -r "./$folder" "$BACKUP_PATH/documents/"
        echo "✅ $folder 백업 완료"
    fi
done

# 기타 데이터
if [ -d "./data" ]; then
    mkdir -p "$BACKUP_PATH/data"
    # 민감한 정보 제외하고 백업
    rsync -av --exclude='*.log' --exclude='*.tmp' --exclude='cache' ./data/ "$BACKUP_PATH/data/"
    echo "✅ 기타 데이터 백업 완료"
fi

# 5. 로그 백업 (최근 7일간)
echo "📝 로그 백업 중..."
mkdir -p "$BACKUP_PATH/logs"

if [ -d "./logs" ]; then
    # 최근 7일간의 로그만 백업
    find ./logs -type f -mtime -7 -name "*.log" -exec cp {} "$BACKUP_PATH/logs/" \;
    echo "✅ 로그 백업 완료 (최근 7일)"
fi

# 6. 백업 압축
echo "🗜️ 백업 압축 중..."
cd "$BACKUP_DIR"
tar -czf "$BACKUP_NAME.tar.gz" "$BACKUP_NAME"
rm -rf "$BACKUP_NAME"

BACKUP_SIZE=$(du -h "$BACKUP_NAME.tar.gz" | cut -f1)
echo "✅ 백업 압축 완료: $BACKUP_SIZE"

# 7. 백업 무결성 검증
echo "🔍 백업 무결성 검증 중..."
if tar -tzf "$BACKUP_NAME.tar.gz" > /dev/null 2>&1; then
    echo "✅ 백업 파일 무결성 확인"
else
    echo "❌ 백업 파일이 손상되었습니다!"
    exit 1
fi

# 8. 체크섬 생성
echo "🔐 체크섬 생성 중..."
md5sum "$BACKUP_NAME.tar.gz" > "$BACKUP_NAME.md5"
sha256sum "$BACKUP_NAME.tar.gz" > "$BACKUP_NAME.sha256"
echo "✅ 체크섬 생성 완료"

cd - > /dev/null

# 9. 오래된 백업 정리 (30일 이상)
echo "🧹 오래된 백업 정리 중..."
find "$BACKUP_DIR" -name "rag-qa-backup_*.tar.gz" -mtime +30 -delete
find "$BACKUP_DIR" -name "rag-qa-backup_*.md5" -mtime +30 -delete
find "$BACKUP_DIR" -name "rag-qa-backup_*.sha256" -mtime +30 -delete
echo "✅ 오래된 백업 정리 완료"

# 10. 백업 정보 생성
cat > "$BACKUP_DIR/$BACKUP_NAME.info" << EOF
RAG QA System Backup Information
================================

Backup Name: $BACKUP_NAME
Created: $(date)
Size: $BACKUP_SIZE
Hostname: $(hostname)
User: $(whoami)

Contents:
- Databases (SQLite + MySQL)
- Vector Database (ChromaDB)
- Configuration files
- Documents and data
- Recent logs (7 days)

Verification:
- MD5: $(cat "$BACKUP_DIR/$BACKUP_NAME.md5" | cut -d' ' -f1)
- SHA256: $(head -c 64 "$BACKUP_DIR/$BACKUP_NAME.sha256")

Restore Command:
  tar -xzf $BACKUP_NAME.tar.gz
  ./scripts/restore.sh $BACKUP_NAME
EOF

# 백업 완료 보고
echo ""
echo "🎉 백업이 성공적으로 완료되었습니다!"
echo "📍 백업 위치: $BACKUP_DIR/$BACKUP_NAME.tar.gz"
echo "📊 백업 크기: $BACKUP_SIZE"
echo "🔐 체크섬 파일: $BACKUP_NAME.md5, $BACKUP_NAME.sha256"
echo ""
echo "📋 복원 방법:"
echo "  1. 백업 파일을 대상 서버로 복사"
echo "  2. tar -xzf $BACKUP_NAME.tar.gz"
echo "  3. ./scripts/restore.sh $BACKUP_NAME"
echo ""
echo "⚠️ 중요: 백업 파일을 안전한 원격 저장소에 보관하는 것을 권장합니다."

# 클라우드 스토리지 업로드 (선택적)
if [ ! -z "$CLOUD_BACKUP_ENABLED" ] && [ "$CLOUD_BACKUP_ENABLED" = "true" ]; then
    echo ""
    echo "☁️ 클라우드 백업 시도 중..."
    
    if command -v aws &> /dev/null && [ ! -z "$AWS_S3_BUCKET" ]; then
        aws s3 cp "$BACKUP_DIR/$BACKUP_NAME.tar.gz" "s3://$AWS_S3_BUCKET/backups/"
        aws s3 cp "$BACKUP_DIR/$BACKUP_NAME.md5" "s3://$AWS_S3_BUCKET/backups/"
        aws s3 cp "$BACKUP_DIR/$BACKUP_NAME.info" "s3://$AWS_S3_BUCKET/backups/"
        echo "✅ AWS S3 백업 완료"
    else
        echo "⚠️ AWS CLI 또는 S3 버킷 설정이 없습니다"
    fi
fi

echo ""
echo "✨ 모든 백업 작업이 완료되었습니다!"