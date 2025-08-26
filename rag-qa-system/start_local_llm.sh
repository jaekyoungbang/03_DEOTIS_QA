#!/bin/bash

# 로컬 LLM 서버 시작 스크립트

echo "🤖 로컬 LLM 서버 시작 중..."

# 기존 프로세스 체크
if pgrep -f "local_llm_server.py" > /dev/null; then
    echo "⚠️  로컬 LLM 서버가 이미 실행 중입니다."
    echo "📍 상태 확인: curl http://localhost:11434/api/version"
    exit 0
fi

# Python 환경 확인
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3가 설치되지 않았습니다."
    exit 1
fi

# 필요한 라이브러리 확인
python3 -c "import transformers, torch, flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ 필요한 라이브러리가 설치되지 않았습니다."
    echo "💡 설치 명령: pip install transformers torch flask"
    exit 1
fi

# 서버 시작
echo "🚀 로컬 LLM 서버를 백그라운드에서 시작합니다..."
cd "$(dirname "$0")"
python3 local_llm_server.py > local_llm.log 2>&1 &

# PID 저장
echo $! > local_llm.pid

echo "✅ 로컬 LLM 서버가 시작되었습니다!"
echo "📍 주소: http://localhost:11434"
echo "📋 로그: tail -f local_llm.log"
echo "⏹️  종료: kill \$(cat local_llm.pid)"

# 잠시 기다린 후 상태 확인
sleep 3
curl -s http://localhost:11434/api/version > /dev/null
if [ $? -eq 0 ]; then
    echo "🎉 로컬 LLM 서버 실행 성공!"
else
    echo "⚠️  서버가 아직 시작 중입니다. 잠시 후 다시 확인해보세요."
fi