#!/bin/bash
set -e

# 상업화 RAG QA 시스템 배포 스크립트
echo "🚀 RAG QA 시스템 배포 시작"

# 설정
PROJECT_NAME="rag-qa-system"
DOCKER_REGISTRY="your-registry.com"  # 실제 레지스트리로 변경
VERSION=${1:-"latest"}
ENVIRONMENT=${2:-"production"}

echo "📋 배포 정보:"
echo "  - 프로젝트: $PROJECT_NAME"
echo "  - 버전: $VERSION"
echo "  - 환경: $ENVIRONMENT"
echo "  - 레지스트리: $DOCKER_REGISTRY"

# 환경 변수 파일 확인
ENV_FILE=".env.$ENVIRONMENT"
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ 환경 변수 파일이 없습니다: $ENV_FILE"
    echo "다음 내용으로 파일을 생성해주세요:"
    cat << EOF
OPENAI_API_KEY=your_openai_api_key_here
MYSQL_ROOT_PASSWORD=secure_root_password
MYSQL_PASSWORD=secure_user_password
FLASK_SECRET_KEY=your_secret_key_here
JWT_SECRET_KEY=your_jwt_secret_here
EOF
    exit 1
fi

# 환경 변수 로드
source "$ENV_FILE"
echo "✅ 환경 변수 로드 완료"

# Docker 빌드
echo "🔨 Docker 이미지 빌드 중..."
docker build -t $PROJECT_NAME:$VERSION -f docker/Dockerfile .
docker tag $PROJECT_NAME:$VERSION $DOCKER_REGISTRY/$PROJECT_NAME:$VERSION

# 이미지 푸시 (프로덕션 환경의 경우)
if [ "$ENVIRONMENT" = "production" ]; then
    echo "📤 Docker 이미지 푸시 중..."
    docker push $DOCKER_REGISTRY/$PROJECT_NAME:$VERSION
    echo "✅ 이미지 푸시 완료"
fi

# 기존 컨테이너 중지 및 제거
echo "🛑 기존 서비스 중지 중..."
docker-compose -f docker/docker-compose.yml --env-file "$ENV_FILE" down

# 볼륨 정리 (선택적)
if [ "$3" = "--clean-volumes" ]; then
    echo "🧹 볼륨 정리 중..."
    docker volume prune -f
fi

# 서비스 시작
echo "🏃 서비스 시작 중..."
docker-compose -f docker/docker-compose.yml --env-file "$ENV_FILE" up -d

# 서비스 상태 확인
echo "⏳ 서비스 시작 대기 중..."
sleep 30

# 헬스체크
echo "🏥 헬스체크 수행 중..."
for i in {1..10}; do
    if curl -f http://localhost:5001/health > /dev/null 2>&1; then
        echo "✅ 서비스가 정상적으로 시작되었습니다!"
        break
    fi
    
    if [ $i -eq 10 ]; then
        echo "❌ 서비스 시작에 실패했습니다."
        echo "로그 확인:"
        docker-compose -f docker/docker-compose.yml logs rag-qa-system
        exit 1
    fi
    
    echo "대기 중... ($i/10)"
    sleep 10
done

# 서비스 정보 출력
echo ""
echo "🎉 배포 완료!"
echo "📍 서비스 접근 정보:"
echo "  - 메인 애플리케이션: http://localhost:5001/deotisrag"
echo "  - API 문서: http://localhost:5001/swagger/"
echo "  - Grafana 대시보드: http://localhost:3000 (admin/admin123)"
echo "  - Kibana 로그: http://localhost:5601"
echo "  - Prometheus 메트릭: http://localhost:9090"

# 로그 모니터링 안내
echo ""
echo "📊 모니터링:"
echo "  - 실시간 로그: docker-compose -f docker/docker-compose.yml logs -f"
echo "  - 컨테이너 상태: docker-compose -f docker/docker-compose.yml ps"
echo "  - 리소스 사용량: docker stats"

# 백업 안내 (프로덕션 환경)
if [ "$ENVIRONMENT" = "production" ]; then
    echo ""
    echo "💾 백업 권장사항:"
    echo "  - 데이터 백업: ./scripts/backup.sh"
    echo "  - 정기 백업 설정을 고려하세요"
fi

# 완료
echo ""
echo "✨ 배포가 성공적으로 완료되었습니다!"